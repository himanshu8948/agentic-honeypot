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
    assert "tactics=" in notes
    # We expect these tags to appear based on observed scammer text (not generic raw notes).
    assert "impersonation" in notes
    assert "fee_pressure" in notes
    assert "redirection" in notes
    assert "credential_grab" in notes

