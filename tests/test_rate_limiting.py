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
    os.environ.pop("DISABLE_RATE_LIMITING", None)
    os.environ["RL_WINDOW_SECONDS"] = "60"
    os.environ["RL_MAX_PER_SESSION"] = "1000"
    os.environ["RL_MAX_PER_IP"] = "5"

    from app import main

    with TestClient(main.app) as test_client:
        yield test_client


def test_rate_limit_per_ip(client: TestClient):
    payload = {
        "sessionId": "rl-1",
        "message": {"sender": "scammer", "text": "hi", "timestamp": 1770005528731},
        "conversationHistory": [],
        "metadata": {"platform": "sms", "language": "", "locale": "IN"},
    }
    ok = 0
    limited = 0
    for i in range(7):
        payload["sessionId"] = f"rl-{i}"
        r = client.post("/analyze", json=payload, headers={"x-api-key": "test-key"})
        if r.status_code == 429:
            limited += 1
        elif r.status_code == 200:
            ok += 1
    assert ok >= 5
    assert limited >= 1

