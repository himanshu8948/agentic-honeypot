from app.main import _build_competition_payload


def test_competition_payload_shape_and_safety() -> None:
    payload = _build_competition_payload(
        session_id="abc123",
        scam_detected=True,
        total_messages=0,
        intel={
            "bankAccounts": ["1234567890123456"],
            "upiIds": ["scammer.fraud@fakebank"],
            "phishingLinks": ["https://secure.fakebank.com/verify"],
            "phoneNumbers": ["+91-9876543210"],
            "suspiciousKeywords": ["urgent", "verify", "otp", "upi", "bank"],
        },
        agent_notes="Scammer used urgency tactics.",
    )

    assert isinstance(payload["sessionId"], str) and payload["sessionId"]
    assert payload["scamDetected"] is True
    assert payload["totalMessagesExchanged"] == 1  # normalized min
    assert set(payload["extractedIntelligence"].keys()) == {
        "bankAccounts",
        "upiIds",
        "phishingLinks",
        "phoneNumbers",
        "suspiciousKeywords",
    }
    # Top keywords are priority-limited to prevent noisy payloads.
    assert len(payload["extractedIntelligence"]["suspiciousKeywords"]) <= 4
