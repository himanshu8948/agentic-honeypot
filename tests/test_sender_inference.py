import os
import tempfile

from fastapi.testclient import TestClient


def test_sender_inference_does_not_flip_benign_user_to_scammer() -> None:
    db_fd, db_path = tempfile.mkstemp()
    os.close(db_fd)

    os.environ["SERVICE_API_KEY"] = "test-key"
    os.environ["DB_PATH"] = db_path
    os.environ["DISABLE_RATE_LIMITING"] = "1"
    os.environ["USE_LLM"] = "0"

    from app.main import app

    with TestClient(app) as client:
        payload = {
            "sessionId": "s-benign",
            "message": {
                "sender": "user",
                "text": "I need help understanding my bank account statement.",
                "timestamp": 1770005528731,
            },
            "conversationHistory": [],
            "metadata": {"platform": "sms", "locale": "IN"},
        }
        resp = client.post("/analyze", json=payload, headers={"x-api-key": "test-key"})
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["shouldEngage"] is False


def test_sender_inference_can_upgrade_clear_scam_text_from_user() -> None:
    db_fd, db_path = tempfile.mkstemp()
    os.close(db_fd)

    os.environ["SERVICE_API_KEY"] = "test-key"
    os.environ["DB_PATH"] = db_path
    os.environ["DISABLE_RATE_LIMITING"] = "1"
    os.environ["USE_LLM"] = "0"

    from app.main import app

    with TestClient(app) as client:
        payload = {
            "sessionId": "s-upgrade",
            "message": {
                "sender": "user",
                "text": "URGENT: account blocked. Share OTP immediately to verify via UPI.",
                "timestamp": 1770005528731,
            },
            "conversationHistory": [],
            "metadata": {"platform": "sms", "locale": "IN"},
        }
        resp = client.post("/analyze", json=payload, headers={"x-api-key": "test-key"})
        assert resp.status_code == 200, resp.text
        data = resp.json()
        # Should be treated as scam-like content even if sender field is wrong.
        assert data["scamDetected"] is True

