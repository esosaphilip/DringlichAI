"""The most important test in this repo: proof that `POST /triage` writes nothing.

WHY THIS EXISTS: the entire safety story — "the model proposes, the nurse decides" — depends on
the AI step being unable to persist a patient on its own. That guarantee comes from LangGraph's
`interrupt_before=["save_to_database"]`, and until now it lived only in the README's prose. This
test calls the real endpoint and then queries the database directly to prove no row appeared.

WHAT A FAILURE WOULD MEAN: if this ever fails, an AI suggestion reached the database without a
human approval — the one failure mode the system exists to prevent. It is a hard, non-negotiable
contract, so it is asserted against the database itself rather than the HTTP response body.

It runs the real pipeline (retrieval + LLM), so Ollama must be running. The database is a temp
copy, so the test can never corrupt real local data.
"""

import os
import shutil
import sqlite3
import uuid

import pytest
from fastapi.testclient import TestClient

import api


@pytest.fixture
def temp_db(tmp_path, monkeypatch):
    """Points the app at an isolated copy of the database for the duration of one test."""
    db_path = tmp_path / "triage_test.db"
    if os.path.exists("triage.db"):
        shutil.copy("triage.db", db_path)
    # `api` reads the module-level DB_FILE at call time, so patching it redirects every query.
    monkeypatch.setattr(api, "DB_FILE", str(db_path))
    api.init_db()  # ensure the schema (and default doctors) exist in the copy
    return str(db_path)


def test_triage_request_never_writes_to_database(temp_db):
    client = TestClient(api.app)

    patient_name = "Contract Test Patient"
    # A fresh thread_id every run: MemorySaver is a module-level singleton, and reusing an id
    # would resume an already-paused thread instead of exercising a clean triage.
    thread_id = f"contract-{uuid.uuid4().hex}"

    resp = client.post("/triage", json={
        "patient_name": patient_name,
        "sickness": "Sudden severe chest pain, collapsed and hard to rouse.",
        "appointment_time": "10:00",
        "thread_id": thread_id,
    })

    # The endpoint must have actually run the AI and returned a pending suggestion ...
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "pending_approval"
    assert body["ai_suggested_priority"] is not None

    # ... and, crucially, persisted nothing. This is the human-in-the-loop contract, asserted
    # against the database rather than trusting the response body.
    with sqlite3.connect(temp_db) as conn:
        count = conn.execute(
            "SELECT COUNT(*) FROM patients WHERE patient_name = ?", (patient_name,)
        ).fetchone()[0]

    assert count == 0, "POST /triage wrote a patient row without human approval!"
