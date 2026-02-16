from __future__ import annotations

import os
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

from fastapi.testclient import TestClient

# Ensure repo root is importable when running as a script.
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


@dataclass(frozen=True)
class Scenario:
    scenario_id: str
    scam_type: str
    initial_message: str
    metadata: dict
    max_turns: int
    fake_data: dict


SCENARIOS: list[Scenario] = [
    Scenario(
        scenario_id="bank_fraud",
        scam_type="bank_fraud",
        initial_message=(
            "URGENT: Your SBI account has been compromised. "
            "Your account will be blocked in 2 hours. "
            "Share your account number and OTP immediately to verify your identity."
        ),
        metadata={"channel": "SMS", "language": "English", "locale": "IN"},
        max_turns=10,
        fake_data={
            "bankAccount": "1234567890123456",
            "upiId": "scammer.fraud@fakebank",
            "phoneNumber": "+91-9876543210",
        },
    ),
    Scenario(
        scenario_id="upi_fraud",
        scam_type="upi_fraud",
        initial_message=(
            "Congratulations! You have won a cashback of Rs. 5000 from Paytm. "
            "To claim your reward, please verify your UPI details. "
            "This is from official customer support."
        ),
        metadata={"channel": "WhatsApp", "language": "English", "locale": "IN"},
        max_turns=10,
        fake_data={
            "upiId": "cashback.scam@fakeupi",
            "phoneNumber": "+91-8765432109",
        },
    ),
    Scenario(
        scenario_id="phishing_link",
        scam_type="phishing",
        initial_message=(
            "You have been selected for iPhone 15 Pro at just Rs. 999! "
            "Click here to claim: http://amaz0n-deals.fake-site.com/claim?id=12345. "
            "Offer expires in 10 minutes!"
        ),
        metadata={"channel": "Email", "language": "English", "locale": "IN"},
        max_turns=10,
        fake_data={
            "phishingLink": "http://amaz0n-deals.fake-site.com/claim?id=12345",
            "emailAddress": "offers@fake-amazon-deals.com",
        },
    ),
]


def _client() -> TestClient:
    db_fd, db_path = tempfile.mkstemp()
    os.close(db_fd)

    os.environ["SERVICE_API_KEY"] = "test-key"
    os.environ["DB_PATH"] = db_path
    os.environ["DISABLE_RATE_LIMITING"] = "1"
    os.environ["TARGET_MESSAGES_EXCHANGED"] = "600"
    os.environ["CALLBACK_MODE"] = "always"

    from app import main

    return TestClient(main.app)


def _post(client: TestClient, session_id: str, text: str, metadata: dict) -> dict:
    payload = {
        "sessionId": session_id,
        "message": {"sender": "scammer", "text": text, "timestamp": 1770005528731},
        "conversationHistory": [],
        "metadata": metadata,
    }
    resp = client.post("/analyze", json=payload, headers={"x-api-key": "test-key"})
    assert resp.status_code == 200, resp.text
    return resp.json()


def _max_repeat_run(items: list[str]) -> int:
    best = 1
    run = 1
    for i in range(1, len(items)):
        if items[i] == items[i - 1]:
            run += 1
            best = max(best, run)
        else:
            run = 1
    return best


def _build_turns(scenario: Scenario, total_turns: int) -> list[str]:
    """
    Build a turn list that rotates the scenario content while periodically injecting
    extractable fake data. This is an eval harness, not a dataset generator.
    """
    base = [
        scenario.initial_message,
        "Please respond immediately; this is time-sensitive.",
        "We need verification to avoid account action.",
        "Do not delay. This is your final reminder.",
        "Confirm you received this message.",
    ]
    turns: list[str] = []
    for i in range(total_turns):
        t = base[i % len(base)]
        if scenario.scenario_id == "bank_fraud":
            if i % 5 == 0:
                t += f" Account: {scenario.fake_data['bankAccount']}"
            if i % 7 == 0:
                t += f" UPI: {scenario.fake_data['upiId']}"
            if i % 9 == 0:
                t += f" Call: {scenario.fake_data['phoneNumber']}"
        elif scenario.scenario_id == "upi_fraud":
            if i % 4 == 0:
                t += f" UPI: {scenario.fake_data['upiId']}"
            if i % 6 == 0:
                t += f" Call: {scenario.fake_data['phoneNumber']}"
        elif scenario.scenario_id == "phishing_link":
            if i % 4 == 0:
                t += f" Link: {scenario.fake_data['phishingLink']}"
            if i % 7 == 0:
                t += f" Email: {scenario.fake_data['emailAddress']}"
        if i % 8 == 0:
            t += f" Ref:{1000+i}"
        turns.append(t)
    return turns


def _simulate_500_exchanges() -> dict:
    total_exchanges = 500
    per_scenario = total_exchanges // len(SCENARIOS)
    remainder = total_exchanges % len(SCENARIOS)

    with _client() as client:
        replies: list[str] = []
        intel_last = None

        idx = 0
        for s in SCENARIOS:
            turns = per_scenario + (1 if idx < remainder else 0)
            idx += 1
            session_id = f"eval-500-{s.scenario_id}"
            turn_texts = _build_turns(s, turns)
            for t in turn_texts:
                data = _post(client, session_id, t, metadata=s.metadata)
                replies.append(str(data.get("reply") or ""))
                intel_last = data.get("extractedIntelligence")

        uniq_ratio = len(set(replies)) / max(1, len(replies))
        max_run = _max_repeat_run(replies)
        return {
            "total_turns": len(replies),
            "uniq_ratio": uniq_ratio,
            "max_exact_repeat_run": max_run,
            "last_intel": intel_last,
            "last_reply": replies[-1] if replies else "",
        }


if __name__ == "__main__":
    metrics = _simulate_500_exchanges()
    print(metrics)

    assert metrics["total_turns"] == 500, "did not reach exactly 500 exchanges"
    assert metrics["uniq_ratio"] >= 0.1, f"reply repetition too high (uniq_ratio={metrics['uniq_ratio']:.2f})"
    assert metrics["max_exact_repeat_run"] <= 5, f"too many exact repeats in a row (run={metrics['max_exact_repeat_run']})"
