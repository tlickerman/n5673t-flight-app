"""
Lightweight SQLite log of submitted Flight Assessment Forms, so there's a
flight history over time. Matches the /data persistent-disk pattern used in
Tod's other Render apps (lickerman-finance, lickerman-calendar).
"""

import json
import os
import sqlite3
from datetime import datetime, timezone

DATA_DIR = os.environ.get("DATA_DIR", "/data")
DB_PATH = os.path.join(DATA_DIR, "flight_assessments.db") if os.path.isdir(DATA_DIR) else "flight_assessments.db"


def _connect():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True) if os.path.dirname(DB_PATH) else None
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = _connect()
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS submissions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            submitted_at TEXT NOT NULL,
            pilot_name TEXT,
            n_number TEXT,
            departure_airport TEXT,
            takeoff_weight_lb REAL,
            takeoff_pct_mac REAL,
            risk_grand_total INTEGER,
            risk_level TEXT,
            manager_approval_required INTEGER,
            wb_within_limits INTEGER,
            payload_json TEXT NOT NULL
        )
        """
    )
    conn.commit()
    conn.close()


def log_submission(form_data, wb_result, risk_result):
    conn = _connect()
    conn.execute(
        """
        INSERT INTO submissions (
            submitted_at, pilot_name, n_number, departure_airport,
            takeoff_weight_lb, takeoff_pct_mac, risk_grand_total, risk_level,
            manager_approval_required, wb_within_limits, payload_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            datetime.now(timezone.utc).isoformat(),
            form_data.get("pilot_1", ""),
            form_data.get("n_number", "N5673T"),
            form_data.get("departure_airport", ""),
            wb_result["takeoff"]["weight_lb"],
            wb_result["takeoff"]["pct_mac"],
            risk_result["grand_total"],
            risk_result["level"],
            int(risk_result["manager_approval_required"]),
            int(wb_result["within_limits"]),
            json.dumps({"form_data": form_data, "wb": wb_result, "risk": risk_result}),
        ),
    )
    conn.commit()
    conn.close()


def get_history(limit=50):
    conn = _connect()
    rows = conn.execute(
        "SELECT * FROM submissions ORDER BY submitted_at DESC LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_submission(submission_id):
    conn = _connect()
    row = conn.execute(
        "SELECT * FROM submissions WHERE id = ?", (submission_id,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None
