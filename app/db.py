import json
import os
import sqlite3
import time
from typing import Any

try:
    import firebase_admin
    from firebase_admin import credentials, firestore
except Exception:  # pragma: no cover - optional dependency at runtime
    firebase_admin = None
    credentials = None
    firestore = None


class FirestoreStore:
    def __init__(self, client: Any):
        self.client = client


def connect(db_path: str) -> sqlite3.Connection | FirestoreStore:
    if _is_firebase_enabled():
        return _connect_firestore()
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _connect_firestore() -> FirestoreStore:
    if firebase_admin is None or credentials is None or firestore is None:
        raise RuntimeError("firebase-admin package is required when FIREBASE_ENABLED=true")

    app_name = os.getenv("FIREBASE_APP_NAME", "agentic-honeypot")
    cred_path = os.getenv("FIREBASE_CREDENTIALS_PATH", "").strip()
    cred_json = os.getenv("FIREBASE_SERVICE_ACCOUNT_JSON", "").strip()
    project_id = os.getenv("FIREBASE_PROJECT_ID", "").strip() or None

    try:
        app = firebase_admin.get_app(app_name)
    except ValueError:
        if cred_json:
            cert_info = json.loads(cred_json)
            cert = credentials.Certificate(cert_info)
            app = firebase_admin.initialize_app(cert, {"projectId": project_id} if project_id else {}, name=app_name)
        elif cred_path:
            cert = credentials.Certificate(cred_path)
            app = firebase_admin.initialize_app(cert, {"projectId": project_id} if project_id else {}, name=app_name)
        else:
            # ADC path (e.g., GOOGLE_APPLICATION_CREDENTIALS) for managed environments.
            app = firebase_admin.initialize_app(options={"projectId": project_id} if project_id else {}, name=app_name)

    client = firestore.client(app=app)
    return FirestoreStore(client)


def _is_firebase_enabled() -> bool:
    raw = os.getenv("FIREBASE_ENABLED", "")
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def init_db(conn: sqlite3.Connection | FirestoreStore) -> None:
    if isinstance(conn, FirestoreStore):
        return
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS sessions (
            session_id TEXT PRIMARY KEY,
            scam_detected INTEGER DEFAULT 0,
            confidence REAL DEFAULT 0.0,
            total_messages INTEGER DEFAULT 0,
            api_calls INTEGER DEFAULT 0,
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
    try:
        conn.execute("ALTER TABLE sessions ADD COLUMN api_calls INTEGER DEFAULT 0")
        conn.commit()
    except sqlite3.OperationalError:
        pass
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


def get_or_create_session(conn: sqlite3.Connection | FirestoreStore, session_id: str) -> dict[str, Any] | sqlite3.Row:
    if isinstance(conn, FirestoreStore):
        return _fs_get_or_create_session(conn, session_id)

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


def _fs_get_or_create_session(store: FirestoreStore, session_id: str) -> dict[str, Any]:
    ref = store.client.collection("sessions").document(session_id)
    snap = ref.get()
    if snap.exists:
        data = snap.to_dict() or {}
        data["session_id"] = session_id
        return _fs_fill_session_defaults(data)

    now = int(time.time())
    base = _fs_fill_session_defaults(
        {
            "session_id": session_id,
            "created_at": now,
            "updated_at": now,
        }
    )
    ref.set(base)
    store.client.collection("intel").document(session_id).set(_empty_intel())
    store.client.collection("user_intel").document(session_id).set(_empty_user_intel())
    return base


def append_message(
    conn: sqlite3.Connection | FirestoreStore,
    session_id: str,
    sender: str,
    text: str,
    timestamp_ms: int,
) -> None:
    if isinstance(conn, FirestoreStore):
        now = int(time.time())
        conn.client.collection("messages").document().set(
            {
                "session_id": session_id,
                "sender": sender,
                "text": text,
                "timestamp_ms": int(timestamp_ms),
                "created_at": now,
            }
        )
        conn.client.collection("sessions").document(session_id).set(
            {
                "total_messages": firestore.Increment(1),
                "updated_at": now,
            },
            merge=True,
        )
        return

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


def increment_api_calls(conn: sqlite3.Connection | FirestoreStore, session_id: str) -> None:
    if isinstance(conn, FirestoreStore):
        conn.client.collection("sessions").document(session_id).set(
            {
                "api_calls": firestore.Increment(1),
                "updated_at": int(time.time()),
            },
            merge=True,
        )
        return

    conn.execute(
        "UPDATE sessions SET api_calls = COALESCE(api_calls, 0) + 1, updated_at = ? WHERE session_id = ?",
        (int(time.time()), session_id),
    )
    conn.commit()


def get_api_calls(conn: sqlite3.Connection | FirestoreStore, session_id: str) -> int:
    if isinstance(conn, FirestoreStore):
        snap = conn.client.collection("sessions").document(session_id).get()
        if not snap.exists:
            return 0
        data = snap.to_dict() or {}
        return int(data.get("api_calls", 0) or 0)

    row = conn.execute(
        "SELECT api_calls FROM sessions WHERE session_id = ?",
        (session_id,),
    ).fetchone()
    if not row:
        return 0
    return int(row["api_calls"] or 0)


def update_session(
    conn: sqlite3.Connection | FirestoreStore,
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
    if isinstance(conn, FirestoreStore):
        conn.client.collection("sessions").document(session_id).set(
            {
                "scam_detected": bool(scam_detected),
                "confidence": float(confidence),
                "last_reply": last_reply,
                "engagement_complete": bool(engagement_complete),
                "agent_notes": agent_notes,
                "callback_pending": bool(callback_pending),
                "conversation_summary": conversation_summary,
                "persona": persona,
                "updated_at": int(time.time()),
            },
            merge=True,
        )
        return

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


def load_intel(conn: sqlite3.Connection | FirestoreStore, session_id: str) -> dict[str, list[str]]:
    if isinstance(conn, FirestoreStore):
        snap = conn.client.collection("intel").document(session_id).get()
        if not snap.exists:
            return _empty_intel()
        return _normalize_intel_doc(snap.to_dict() or {})

    row = conn.execute(
        "SELECT * FROM intel WHERE session_id = ?",
        (session_id,),
    ).fetchone()
    if not row:
        return _empty_intel()
    return {
        "bankAccounts": json.loads(row["bank_accounts"] or "[]"),
        "upiIds": json.loads(row["upi_ids"] or "[]"),
        "phishingLinks": json.loads(row["phishing_links"] or "[]"),
        "phoneNumbers": json.loads(row["phone_numbers"] or "[]"),
        "suspiciousKeywords": json.loads(row["suspicious_keywords"] or "[]"),
    }


def save_intel(conn: sqlite3.Connection | FirestoreStore, session_id: str, intel: dict[str, list[str]]) -> None:
    if isinstance(conn, FirestoreStore):
        conn.client.collection("intel").document(session_id).set(_normalize_intel_doc(intel), merge=True)
        return

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


def load_user_intel(conn: sqlite3.Connection | FirestoreStore, session_id: str) -> dict[str, list[str]]:
    if isinstance(conn, FirestoreStore):
        snap = conn.client.collection("user_intel").document(session_id).get()
        if not snap.exists:
            return _empty_user_intel()
        return _normalize_user_intel_doc(snap.to_dict() or {})

    row = conn.execute(
        "SELECT * FROM user_intel WHERE session_id = ?",
        (session_id,),
    ).fetchone()
    if not row:
        return _empty_user_intel()
    return {
        "bankAccounts": json.loads(row["bank_accounts"] or "[]"),
        "upiIds": json.loads(row["upi_ids"] or "[]"),
        "phishingLinks": json.loads(row["phishing_links"] or "[]"),
        "phoneNumbers": json.loads(row["phone_numbers"] or "[]"),
        "suspiciousKeywords": [],
    }


def save_user_intel(conn: sqlite3.Connection | FirestoreStore, session_id: str, intel: dict[str, list[str]]) -> None:
    if isinstance(conn, FirestoreStore):
        conn.client.collection("user_intel").document(session_id).set(_normalize_user_intel_doc(intel), merge=True)
        return

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


def list_messages(conn: sqlite3.Connection | FirestoreStore, session_id: str, limit: int = 30) -> list[dict[str, Any]]:
    if isinstance(conn, FirestoreStore):
        # Avoid composite-index dependency (session_id filter + timestamp order).
        # Fetch by session_id and sort in-memory for predictable transcript order.
        docs = conn.client.collection("messages").where("session_id", "==", session_id).stream()
        out: list[dict[str, Any]] = []
        for doc in docs:
            data = doc.to_dict() or {}
            out.append(
                {
                    "sender": str(data.get("sender", "")),
                    "text": str(data.get("text", "")),
                    "timestamp": int(data.get("timestamp_ms", 0) or 0),
                }
            )
        out.sort(key=lambda m: m["timestamp"])
        if limit > 0:
            return out[-limit:]
        return out

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


def count_messages(conn: sqlite3.Connection | FirestoreStore, session_id: str) -> int:
    if isinstance(conn, FirestoreStore):
        docs = conn.client.collection("messages").where("session_id", "==", session_id).stream()
        return sum(1 for _ in docs)

    row = conn.execute(
        "SELECT COUNT(*) as cnt FROM messages WHERE session_id = ?",
        (session_id,),
    ).fetchone()
    return int(row["cnt"]) if row else 0


def _empty_intel() -> dict[str, list[str]]:
    return {
        "bankAccounts": [],
        "upiIds": [],
        "phishingLinks": [],
        "phoneNumbers": [],
        "suspiciousKeywords": [],
    }


def _empty_user_intel() -> dict[str, list[str]]:
    return {
        "bankAccounts": [],
        "upiIds": [],
        "phishingLinks": [],
        "phoneNumbers": [],
        "suspiciousKeywords": [],
    }


def _normalize_intel_doc(data: dict[str, Any]) -> dict[str, list[str]]:
    return {
        "bankAccounts": _as_str_list(data.get("bankAccounts")),
        "upiIds": _as_str_list(data.get("upiIds")),
        "phishingLinks": _as_str_list(data.get("phishingLinks")),
        "phoneNumbers": _as_str_list(data.get("phoneNumbers")),
        "suspiciousKeywords": _as_str_list(data.get("suspiciousKeywords")),
    }


def _normalize_user_intel_doc(data: dict[str, Any]) -> dict[str, list[str]]:
    return {
        "bankAccounts": _as_str_list(data.get("bankAccounts")),
        "upiIds": _as_str_list(data.get("upiIds")),
        "phishingLinks": _as_str_list(data.get("phishingLinks")),
        "phoneNumbers": _as_str_list(data.get("phoneNumbers")),
        "suspiciousKeywords": [],
    }


def _as_str_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(v) for v in value if str(v).strip()]


def _fs_fill_session_defaults(data: dict[str, Any]) -> dict[str, Any]:
    now = int(time.time())
    merged = {
        "session_id": str(data.get("session_id", "")),
        "scam_detected": bool(data.get("scam_detected", False)),
        "confidence": float(data.get("confidence", 0.0)),
        "total_messages": int(data.get("total_messages", 0) or 0),
        "api_calls": int(data.get("api_calls", 0) or 0),
        "last_reply": data.get("last_reply"),
        "engagement_complete": bool(data.get("engagement_complete", False)),
        "agent_notes": data.get("agent_notes"),
        "callback_pending": bool(data.get("callback_pending", False)),
        "conversation_summary": data.get("conversation_summary", ""),
        "persona": data.get("persona"),
        "created_at": int(data.get("created_at", now) or now),
        "updated_at": int(data.get("updated_at", now) or now),
    }
    return merged
