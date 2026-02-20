import os
import tempfile

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client():
    db_fd, db_path = tempfile.mkstemp()
    os.close(db_fd)

    os.environ["SERVICE_API_KEY"] = "test-key"
    os.environ["GROQ_API_KEYS"] = "gkey1,gkey2"
    os.environ["DB_PATH"] = db_path

    from app import main

    class StubGroq:
        async def summarize_intents(self, conversation):
            return {"intentScammer": "Get user to share banking details.", "intentUser": "Understand the claim."}

        async def classify(self, text: str, context=None, intents=None):
            return {"scamDetected": True, "confidence": 0.9, "reasons": ["urgency"], "intentCategory": "bank"}

        async def generate_reply(self, persona, conversation, intel_summary, intents=None, suspected_scammer=True):
            return {"reply": "Can you explain why my account is blocked?", "agentNotes": "Asked for details", "stopReason": None}

    with TestClient(main.app) as test_client:
        main.GROQ = StubGroq()
        yield test_client


@pytest.mark.asyncio
async def test_message_flow(client):
    payload = {
        "sessionId": "s1",
        "message": {"sender": "scammer", "text": "Your account is blocked. Verify now.", "timestamp": 1770005528731},
        "conversationHistory": [],
        "metadata": {"channel": "SMS", "language": "English", "locale": "IN"},
    }
    response = client.post("/api/message", json=payload, headers={"x-api-key": "test-key"})
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["scamDetected"] is True
    assert "reply" in data


@pytest.mark.asyncio
async def test_final_output_endpoint(client):
    payload = {
        "sessionId": "s2",
        "message": {"sender": "scammer", "text": "Share OTP and call +91-9876543210", "timestamp": 1770005528731},
        "conversationHistory": [],
        "metadata": {"channel": "SMS", "language": "English", "locale": "IN"},
    }
    first = client.post("/api/message", json=payload, headers={"x-api-key": "test-key"})
    assert first.status_code == 200

    out = client.post(
        "/api/final-output",
        json={"sessionId": "s2", "observedText": "Urgent bank OTP scam"},
        headers={"x-api-key": "test-key"},
    )
    assert out.status_code == 200
    body = out.json()
    assert body["sessionId"] == "s2"
    assert "extractedIntelligence" in body
    assert "scamType" in body
    assert "confidenceLevel" in body
