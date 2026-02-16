import os
import tempfile

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client():
    db_fd, db_path = tempfile.mkstemp()
    os.close(db_fd)

    os.environ["SERVICE_API_KEY"] = "test-key"
    os.environ["DB_PATH"] = db_path
    os.environ["DISABLE_RATE_LIMITING"] = "1"

    from app import main

    with TestClient(main.app) as test_client:
        yield test_client


def test_agent_notes_tactics_uses_observed_text(client: TestClient):
    # Message includes impersonation + fee pressure + redirection + credentials grab.
    msg = "LIC agent here. Pay premium fee via UPI to abc.pay@upi and share OTP immediately."
    payload = {
        "sessionId": "notes-1",
        "message": {"sender": "scammer", "text": msg, "timestamp": 1770005528731},
        "conversationHistory": [],
        "metadata": {"platform": "sms", "language": "", "locale": "IN"},
    }
    r = client.post("/analyze", json=payload, headers={"x-api-key": "test-key"})
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "success"
    notes = data["agentNotes"]
    # Notes should be clean: only behavior summary (no telemetry footer).
    assert notes.startswith("Scammer: ")
    assert "sid=" not in notes
    assert "turns=" not in notes
    assert "zone=" not in notes
    assert "dom=" not in notes
    # Summary should reflect observed scammer behavior (not generic).
    assert "impersonation" in notes or "authority" in notes
    assert ("payment" in notes) or ("redirect" in notes)
    assert ("otp" in notes.lower()) or ("pin" in notes.lower()) or ("password" in notes.lower())
    assert len(notes) <= 140
