"""Tests for the workload-aware doctor assignment rule (`_least_loaded_doctor`).

WHY THIS EXISTS: assignment decides which clinician receives a patient, so its edge cases matter:
an empty roster, which doctor wins a tie, and — most importantly — that an off-duty doctor is
never handed new work and that their existing patients are rebalanced onto a colleague.

WHAT A FAILURE WOULD MEAN: a patient silently assigned to nobody, or to a doctor who has gone off
duty, or the rebalance count reported by the API disagreeing with what the database actually
holds. The tie-break test asserts the *current* behaviour rather than an assumption, so if the
tie-break ever changes, the test flags it as a deliberate change.

The unit tests run against an in-memory database (no app, no Ollama). The reassignment test drives
the real endpoint against a temp copy of the database.
"""

import os
import shutil
import sqlite3

import pytest
from fastapi.testclient import TestClient

import api
from api import _least_loaded_doctor


# --- in-memory helpers for the pure unit tests ------------------------------------------------

def _memory_cursor():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE doctors (
            doctor_name TEXT PRIMARY KEY, specialty TEXT, status TEXT DEFAULT 'available')
    """)
    cur.execute("""
        CREATE TABLE patients (
            patient_name TEXT PRIMARY KEY, sickness TEXT, priority INTEGER, doctor_name TEXT,
            status TEXT, appointment_time TEXT, ticket TEXT, confidence INTEGER)
    """)
    return cur


def _add_doctor(cur, name, status="available"):
    cur.execute(
        "INSERT INTO doctors (doctor_name, specialty, status) VALUES (?, ?, ?)",
        (name, "Test Specialty", status),
    )


def _add_patient(cur, name, doctor):
    cur.execute("INSERT INTO patients (patient_name, doctor_name) VALUES (?, ?)", (name, doctor))


# --- pure unit tests ---------------------------------------------------------------------------

def test_empty_roster_returns_none():
    """With no doctors at all there is nobody to assign — the caller must handle None."""
    assert _least_loaded_doctor(_memory_cursor()) is None


def test_single_available_doctor_is_returned():
    cur = _memory_cursor()
    _add_doctor(cur, "Dr. Solo")
    assert _least_loaded_doctor(cur) == "Dr. Solo"


def test_tie_is_broken_by_query_order():
    """Two equally-loaded available doctors: the tie goes to whichever the query yields first.

    There is no explicit tie-break column, so this documents the current behaviour (insertion
    order, i.e. the first doctor added) instead of assuming it. If this starts failing, the
    tie-break changed and that is worth knowing.
    """
    cur = _memory_cursor()
    _add_doctor(cur, "Dr. First")
    _add_doctor(cur, "Dr. Second")
    assert _least_loaded_doctor(cur) == "Dr. First"


def test_off_duty_doctor_is_excluded_even_when_least_loaded():
    """An off-duty doctor is never assigned, even if they are technically the least loaded."""
    cur = _memory_cursor()
    _add_doctor(cur, "Dr. Busy", "available")
    _add_doctor(cur, "Dr. Off", "off")
    _add_patient(cur, "existing", "Dr. Busy")  # Busy load = 1, Off load = 0 but unavailable

    assert _least_loaded_doctor(cur) == "Dr. Busy"


def test_exclude_argument_skips_the_named_doctor():
    """The `exclude` used during reassignment keeps a doctor from receiving their own patients."""
    cur = _memory_cursor()
    _add_doctor(cur, "Dr. A")
    _add_doctor(cur, "Dr. B")
    assert _least_loaded_doctor(cur, exclude="Dr. A") == "Dr. B"


# --- endpoint-level reassignment ---------------------------------------------------------------

@pytest.fixture
def temp_db(tmp_path, monkeypatch):
    """Points the app at an isolated copy of the database for the duration of one test."""
    db_path = tmp_path / "triage_test.db"
    if os.path.exists("triage.db"):
        shutil.copy("triage.db", db_path)
    monkeypatch.setattr(api, "DB_FILE", str(db_path))
    api.init_db()
    return str(db_path)


def test_going_off_duty_reassigns_patients_to_least_loaded(temp_db):
    """Setting a doctor off duty moves their patients to the least-loaded available colleague."""
    with sqlite3.connect(temp_db) as conn:
        cur = conn.cursor()
        # Isolate to exactly two doctors so the destination is deterministic.
        cur.execute("DELETE FROM patients")
        cur.execute("DELETE FROM doctors")
        cur.executemany(
            "INSERT INTO doctors (doctor_name, specialty, status) VALUES (?, 'Test', 'available')",
            [("Dr. Leaving",), ("Dr. Free",)],
        )
        cur.executemany(
            "INSERT INTO patients (patient_name, doctor_name, status) VALUES (?, 'Dr. Leaving', 'approved')",
            [("P1",), ("P2",)],
        )
        conn.commit()

    client = TestClient(api.app)
    resp = client.patch("/doctors/Dr. Leaving/status", json={"status": "off"})

    assert resp.status_code == 200
    assert resp.json()["reassigned"] == 2

    with sqlite3.connect(temp_db) as conn:
        loads = dict(conn.execute(
            "SELECT doctor_name, COUNT(*) FROM patients GROUP BY doctor_name"
        ).fetchall())

    assert loads.get("Dr. Leaving", 0) == 0
    assert loads.get("Dr. Free") == 2
