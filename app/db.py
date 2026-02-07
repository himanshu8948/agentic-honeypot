import json
import sqlite3
import time
from typing import Any


def connect(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS sessions (
            session_id TEXT PRIMARY KEY,
            scam_detected INTEGER DEFAULT 0,
            confidence REAL DEFAULT 0.0,
            total_messages INTEGER DEFAULT 0,
            last_reply TEXT,
            engagement_complete INTEGER DEFAULT 0,
            agent_notes TEXT,
            callback_pending INTEGER DEFAULT 0,
            conversation_summary TEXT,
            persona TEXT,
            created_at INTEGER,
            updated_at INTEGER
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            sender TEXT NOT NULL,
            text TEXT NOT NULL,
            timestamp_ms INTEGER NOT NULL,
            FOREIGN KEY (session_id) REFERENCES sessions (session_id)
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS intel (
            session_id TEXT PRIMARY KEY,
            bank_accounts TEXT,
            upi_ids TEXT,
            phishing_links TEXT,
            phone_numbers TEXT,
            suspicious_keywords TEXT,
            FOREIGN KEY (session_id) REFERENCES sessions (session_id)
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS user_intel (
            session_id TEXT PRIMARY KEY,
            bank_accounts TEXT,
            upi_ids TEXT,
            phishing_links TEXT,
            phone_numbers TEXT,
            FOREIGN KEY (session_id) REFERENCES sessions (session_id)
        )
        """
    )
    conn.commit()
    _ensure_session_columns(conn)


def _ensure_session_columns(conn: sqlite3.Connection) -> None:
    columns = conn.execute("PRAGMA table_info(sessions)").fetchall()
    existing = {row[1] for row in columns}
    if "callback_pending" not in existing:
        conn.execute("ALTER TABLE sessions ADD COLUMN callback_pending INTEGER DEFAULT 0")
    if "conversation_summary" not in existing:
        conn.execute("ALTER TABLE sessions ADD COLUMN conversation_summary TEXT")
    if "persona" not in existing:
        conn.execute("ALTER TABLE sessions ADD COLUMN persona TEXT")
    if "api_calls" not in existing:
        conn.execute("ALTER TABLE sessions ADD COLUMN api_calls INTEGER DEFAULT 0")
    conn.commit()


def get_or_create_session(conn: sqlite3.Connection, session_id: str) -> sqlite3.Row:
    row = conn.execute(
        "SELECT * FROM sessions WHERE session_id = ?",
        (session_id,),
    ).fetchone()
    if row:
        return row

    now = int(time.time())
    conn.execute(
        """
        INSERT INTO sessions (session_id, created_at, updated_at)
        VALUES (?, ?, ?)
        """,
        (session_id, now, now),
    )
    conn.execute(
        """
        INSERT INTO intel (session_id, bank_accounts, upi_ids, phishing_links, phone_numbers, suspicious_keywords)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (session_id, "[]", "[]", "[]", "[]", "[]"),
    )
    conn.execute(
        """
        INSERT INTO user_intel (session_id, bank_accounts, upi_ids, phishing_links, phone_numbers)
        VALUES (?, ?, ?, ?, ?)
        """,
        (session_id, "[]", "[]", "[]", "[]"),
    )
    conn.commit()
    return conn.execute(
        "SELECT * FROM sessions WHERE session_id = ?",
        (session_id,),
    ).fetchone()


def append_message(
    conn: sqlite3.Connection,
    session_id: str,
    sender: str,
    text: str,
    timestamp_ms: int,
) -> None:
    conn.execute(
        """
        INSERT INTO messages (session_id, sender, text, timestamp_ms)
        VALUES (?, ?, ?, ?)
        """,
        (session_id, sender, text, timestamp_ms),
    )
    conn.execute(
        "UPDATE sessions SET total_messages = total_messages + 1, updated_at = ? WHERE session_id = ?",
        (int(time.time()), session_id),
    )
    conn.commit()


def increment_api_calls(conn: sqlite3.Connection, session_id: str) -> None:
    conn.execute(
        "UPDATE sessions SET api_calls = COALESCE(api_calls, 0) + 1, updated_at = ? WHERE session_id = ?",
        (int(time.time()), session_id),
    )
    conn.commit()


def get_api_calls(conn: sqlite3.Connection, session_id: str) -> int:
    row = conn.execute(
        "SELECT api_calls FROM sessions WHERE session_id = ?",
        (session_id,),
    ).fetchone()
    if not row:
        return 0
    return int(row["api_calls"] or 0)


def update_session(
    conn: sqlite3.Connection,
    session_id: str,
    scam_detected: bool,
    confidence: float,
    last_reply: str | None,
    engagement_complete: bool,
    agent_notes: str | None,
    callback_pending: bool,
    conversation_summary: str | None,
    persona: str | None,
) -> None:
    conn.execute(
        """
        UPDATE sessions
        SET scam_detected = ?, confidence = ?, last_reply = ?, engagement_complete = ?, agent_notes = ?, callback_pending = ?, conversation_summary = ?, persona = ?, updated_at = ?
        WHERE session_id = ?
        """,
        (
            int(scam_detected),
            float(confidence),
            last_reply,
            int(engagement_complete),
            agent_notes,
            int(callback_pending),
            conversation_summary,
            persona,
            int(time.time()),
            session_id,
        ),
    )
    conn.commit()


def load_intel(conn: sqlite3.Connection, session_id: str) -> dict[str, list[str]]:
    row = conn.execute(
        "SELECT * FROM intel WHERE session_id = ?",
        (session_id,),
    ).fetchone()
    if not row:
        return {
            "bankAccounts": [],
            "upiIds": [],
            "phishingLinks": [],
            "phoneNumbers": [],
            "suspiciousKeywords": [],
        }
    return {
        "bankAccounts": json.loads(row["bank_accounts"] or "[]"),
        "upiIds": json.loads(row["upi_ids"] or "[]"),
        "phishingLinks": json.loads(row["phishing_links"] or "[]"),
        "phoneNumbers": json.loads(row["phone_numbers"] or "[]"),
        "suspiciousKeywords": json.loads(row["suspicious_keywords"] or "[]"),
    }


def save_intel(conn: sqlite3.Connection, session_id: str, intel: dict[str, list[str]]) -> None:
    conn.execute(
        """
        UPDATE intel
        SET bank_accounts = ?, upi_ids = ?, phishing_links = ?, phone_numbers = ?, suspicious_keywords = ?
        WHERE session_id = ?
        """,
        (
            json.dumps(intel.get("bankAccounts", [])),
            json.dumps(intel.get("upiIds", [])),
            json.dumps(intel.get("phishingLinks", [])),
            json.dumps(intel.get("phoneNumbers", [])),
            json.dumps(intel.get("suspiciousKeywords", [])),
            session_id,
        ),
    )
    conn.commit()


def load_user_intel(conn: sqlite3.Connection, session_id: str) -> dict[str, list[str]]:
    row = conn.execute(
        "SELECT * FROM user_intel WHERE session_id = ?",
        (session_id,),
    ).fetchone()
    if not row:
        return {
            "bankAccounts": [],
            "upiIds": [],
            "phishingLinks": [],
            "phoneNumbers": [],
            "suspiciousKeywords": [],
        }
    return {
        "bankAccounts": json.loads(row["bank_accounts"] or "[]"),
        "upiIds": json.loads(row["upi_ids"] or "[]"),
        "phishingLinks": json.loads(row["phishing_links"] or "[]"),
        "phoneNumbers": json.loads(row["phone_numbers"] or "[]"),
        "suspiciousKeywords": [],
    }


def save_user_intel(conn: sqlite3.Connection, session_id: str, intel: dict[str, list[str]]) -> None:
    conn.execute(
        """
        UPDATE user_intel
        SET bank_accounts = ?, upi_ids = ?, phishing_links = ?, phone_numbers = ?
        WHERE session_id = ?
        """,
        (
            json.dumps(intel.get("bankAccounts", [])),
            json.dumps(intel.get("upiIds", [])),
            json.dumps(intel.get("phishingLinks", [])),
            json.dumps(intel.get("phoneNumbers", [])),
            session_id,
        ),
    )
    conn.commit()


def list_messages(conn: sqlite3.Connection, session_id: str, limit: int = 30) -> list[dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT sender, text, timestamp_ms
        FROM messages
        WHERE session_id = ?
        ORDER BY id ASC
        LIMIT ?
        """,
        (session_id, limit),
    ).fetchall()
    return [
        {"sender": row["sender"], "text": row["text"], "timestamp": row["timestamp_ms"]}
        for row in rows
    ]


def count_messages(conn: sqlite3.Connection, session_id: str) -> int:
    row = conn.execute(
        "SELECT COUNT(*) as cnt FROM messages WHERE session_id = ?",
        (session_id,),
    ).fetchone()
    return int(row["cnt"]) if row else 0
