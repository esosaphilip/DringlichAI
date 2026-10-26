import os
import re
import sqlite3
from contextlib import closing
from typing import List, Optional

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from priority_analyzer_agent import graph

app = FastAPI(title="DringlichAI - Hospital Triage API", version="1.0")

DB_FILE = "triage.db"
FRONTEND_DIST = os.path.join("frontend", "dist")
VALID_STATUSES = {"available", "break", "off"}


def _ensure_column(cursor, table: str, column: str, declaration: str):
    """Adds a column to an existing table when it is missing (lightweight migration)."""
    cursor.execute(f"PRAGMA table_info({table})")
    existing = {row[1] for row in cursor.fetchall()}
    if column not in existing:
        cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {declaration}")


def init_db():
    with closing(sqlite3.connect(DB_FILE)) as conn:
        with closing(conn.cursor()) as cursor:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS patients (
                    patient_name TEXT PRIMARY KEY,
                    sickness TEXT,
                    priority INTEGER,
                    doctor_name TEXT,
                    status TEXT,
                    appointment_time TEXT,
                    ticket TEXT,
                    confidence INTEGER
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS doctors (
                    doctor_name TEXT PRIMARY KEY,
                    specialty TEXT,
                    status TEXT DEFAULT 'available'
                )
            """)
            # Migrate databases created before the doctor status / queue metadata existed.
            _ensure_column(cursor, "doctors", "status", "TEXT DEFAULT 'available'")
            _ensure_column(cursor, "patients", "ticket", "TEXT")
            _ensure_column(cursor, "patients", "confidence", "INTEGER")
            cursor.execute("UPDATE doctors SET status = 'available' WHERE status IS NULL")

            cursor.execute("SELECT COUNT(*) FROM doctors")
            if cursor.fetchone()[0] == 0:
                cursor.executemany(
                    "INSERT INTO doctors (doctor_name, specialty, status) VALUES (?, ?, 'available')",
                    [
                        ("Dr. Weber", "General Medicine / Emergency"),
                        ("Dr. Fischer", "Internal Medicine / Cardiology")
                    ]
                )
            conn.commit()


init_db()


def _least_loaded_doctor(cursor, exclude: Optional[str] = None) -> Optional[str]:
    """Returns the least-loaded doctor that is not off duty, preferring 'available'."""
    cursor.execute("""
        SELECT d.doctor_name, d.status,
        (SELECT COUNT(*) FROM patients p WHERE p.doctor_name = d.doctor_name) AS load
        FROM doctors d
    """)
    rows = [
        dict(row) for row in cursor.fetchall()
        if row["doctor_name"] != exclude and row["status"] != "off"
    ]
    if not rows:
        return None
    available = [row for row in rows if row["status"] == "available"]
    pool = available or rows
    return min(pool, key=lambda row: row["load"])["doctor_name"]


def _next_ticket(cursor) -> str:
    """Generates the next queue ticket, e.g. A-031."""
    cursor.execute("SELECT ticket FROM patients WHERE ticket IS NOT NULL AND ticket != ''")
    highest = 0
    for row in cursor.fetchall():
        match = re.search(r"(\d+)", row["ticket"] or "")
        if match:
            highest = max(highest, int(match.group(1)))
    return f"A-{highest + 1:03d}"


# --- WEBSOCKET CONNECTION MANAGER ---
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(message)

manager = ConnectionManager()

class PatientRequest(BaseModel):
    patient_name: str
    sickness: str
    appointment_time: str
    thread_id: str

class NurseDecision(BaseModel):
    thread_id: str
    approved: bool
    priority_override: Optional[int] = None

class DoctorCreate(BaseModel):
    doctor_name: str
    specialty: str

class DoctorStatus(BaseModel):
    status: str

class PatientUpsert(BaseModel):
    patient_name: str
    sickness: str
    priority: int
    doctor_name: str
    status: Optional[str] = "approved"
    appointment_time: str
    ticket: Optional[str] = None
    confidence: Optional[int] = None


if os.path.isdir(os.path.join(FRONTEND_DIST, "assets")):
    app.mount(
        "/assets",
        StaticFiles(directory=os.path.join(FRONTEND_DIST, "assets")),
        name="assets"
    )


@app.get("/")
def serve_frontend():
    index_path = os.path.join(FRONTEND_DIST, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"error": "frontend build not found. Run `npm run build` inside frontend/."}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)

@app.get("/doctors")
def get_doctors():
    """Returns the list of active doctors, their duty status and current workload."""
    with closing(sqlite3.connect(DB_FILE)) as conn:
        conn.row_factory = sqlite3.Row
        with closing(conn.cursor()) as cursor:
            cursor.execute("""
                SELECT d.doctor_name, d.specialty, d.status,
                (SELECT COUNT(*) FROM patients p WHERE p.doctor_name = d.doctor_name) as active_load
                FROM doctors d
                ORDER BY d.doctor_name
            """)
            doctors = [dict(row) for row in cursor.fetchall()]
    return {"doctors": doctors}

@app.post("/doctors")
async def add_doctor(doc: DoctorCreate):
    """Adds a new doctor to the hospital staff pool."""
    with closing(sqlite3.connect(DB_FILE)) as conn:
        with closing(conn.cursor()) as cursor:
            try:
                cursor.execute(
                    "INSERT INTO doctors (doctor_name, specialty, status) VALUES (?, ?, 'available')",
                    (doc.doctor_name, doc.specialty)
                )
                conn.commit()
            except sqlite3.IntegrityError:
                raise HTTPException(status_code=400, detail="Doctor already exists.")

    await manager.broadcast("update_queue")
    return {"status": "success", "message": f"Doctor {doc.doctor_name} added successfully."}

@app.patch("/doctors/{doctor_name}/status")
async def set_doctor_status(doctor_name: str, data: DoctorStatus):
    """Changes a doctor's duty status. Going off duty reassigns their patients."""
    if data.status not in VALID_STATUSES:
        raise HTTPException(status_code=400, detail="Invalid status.")

    reassigned = 0
    with closing(sqlite3.connect(DB_FILE)) as conn:
        conn.row_factory = sqlite3.Row
        with closing(conn.cursor()) as cursor:
            cursor.execute("SELECT 1 FROM doctors WHERE doctor_name = ?", (doctor_name,))
            if cursor.fetchone() is None:
                raise HTTPException(status_code=404, detail="Doctor not found.")

            cursor.execute(
                "UPDATE doctors SET status = ? WHERE doctor_name = ?", (data.status, doctor_name)
            )

            if data.status == "off":
                cursor.execute(
                    "SELECT patient_name FROM patients WHERE doctor_name = ?", (doctor_name,)
                )
                for row in cursor.fetchall():
                    target = _least_loaded_doctor(cursor, exclude=doctor_name)
                    if not target:
                        break
                    cursor.execute(
                        "UPDATE patients SET doctor_name = ? WHERE patient_name = ?",
                        (target, row["patient_name"])
                    )
                    reassigned += 1

            conn.commit()

    await manager.broadcast("update_queue")
    return {
        "status": "success",
        "reassigned": reassigned,
        "message": f"Doctor {doctor_name} is now {data.status}."
    }

@app.get("/patients")
def get_patients_queue():
    with closing(sqlite3.connect(DB_FILE)) as conn:
        conn.row_factory = sqlite3.Row
        with closing(conn.cursor()) as cursor:
            cursor.execute("SELECT * FROM patients ORDER BY priority ASC, appointment_time ASC")
            queue = [dict(row) for row in cursor.fetchall()]
    return {"queue": queue}

@app.post("/patients")
async def restore_patient(data: PatientUpsert):
    """Re-inserts a patient that was removed from the queue (used by undo)."""
    with closing(sqlite3.connect(DB_FILE)) as conn:
        with closing(conn.cursor()) as cursor:
            cursor.execute("""
                INSERT OR REPLACE INTO patients
                (patient_name, sickness, priority, doctor_name, status, appointment_time, ticket, confidence)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                data.patient_name, data.sickness, data.priority, data.doctor_name,
                data.status, data.appointment_time, data.ticket, data.confidence
            ))
            conn.commit()

    await manager.broadcast("update_queue")
    return {"status": "success", "message": f"Patient {data.patient_name} restored."}

@app.post("/triage")
def run_triage(data: PatientRequest):
    with closing(sqlite3.connect(DB_FILE)) as conn:
        conn.row_factory = sqlite3.Row
        with closing(conn.cursor()) as cursor:
            assigned_doctor = _least_loaded_doctor(cursor)
            if not assigned_doctor:
                raise HTTPException(status_code=400, detail="No doctors available.")

    config = {"configurable": {"thread_id": data.thread_id}}
    initial_state = {
        "patient_name": data.patient_name,
        "sickness": data.sickness,
        "priority": 0,
        "doctor_name": assigned_doctor,
        "status": "pending",
        "appointment_time": data.appointment_time
    }

    graph.invoke(initial_state, config)
    current_state = graph.get_state(config)
    values = current_state.values

    return {
        "status": "pending_approval",
        "patient_name": data.patient_name,
        "assigned_doctor": assigned_doctor,
        "ai_suggested_priority": values.get("priority"),
        "ai_confidence": values.get("confidence"),
        "ai_reasoning": values.get("reasoning"),
        "ai_guideline": values.get("guideline"),
        "thread_id": data.thread_id,
        "message": f"AI triage complete. Auto-assigned to {assigned_doctor}."
    }

@app.post("/triage/decision")
async def handle_nurse_decision(data: NurseDecision):
    config = {"configurable": {"thread_id": data.thread_id}}
    state = graph.get_state(config)
    if not state.next:
        raise HTTPException(status_code=400, detail="No active paused session found.")

    if data.approved:
        graph.invoke(None, config)
        final_state = graph.get_state(config).values

        priority = final_state.get("priority")
        if data.priority_override in (1, 2, 3, 4, 5):
            priority = data.priority_override

        with closing(sqlite3.connect(DB_FILE)) as conn:
            conn.row_factory = sqlite3.Row
            with closing(conn.cursor()) as cursor:
                ticket = _next_ticket(cursor)
                cursor.execute("""
                    INSERT OR REPLACE INTO patients
                    (patient_name, sickness, priority, doctor_name, status, appointment_time, ticket, confidence)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    final_state.get("patient_name"),
                    final_state.get("sickness"),
                    priority,
                    final_state.get("doctor_name"),
                    "approved",
                    final_state.get("appointment_time"),
                    ticket,
                    final_state.get("confidence")
                ))
                conn.commit()

        await manager.broadcast("update_queue")
        return {
            "status": "success",
            "ticket": ticket,
            "priority": priority,
            "message": "Patient added and broadcasted!"
        }
    else:
        return {"status": "rejected", "message": "Triage session aborted."}

@app.delete("/patients/{patient_name}")
async def delete_treated_patient(patient_name: str):
    with closing(sqlite3.connect(DB_FILE)) as conn:
        with closing(conn.cursor()) as cursor:
            cursor.execute("DELETE FROM patients WHERE LOWER(patient_name) = LOWER(?)", (patient_name,))
            conn.commit()
            if cursor.rowcount == 0:
                raise HTTPException(status_code=404, detail="Patient not found.")

    await manager.broadcast("update_queue")
    return {"status": "success", "message": f"Patient {patient_name} removed and broadcasted."}
