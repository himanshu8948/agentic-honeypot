from app.main import _sanitize_outgoing_reply, _tone_normalize_reply


def test_sanitize_blocks_pan() -> None:
    out = _sanitize_outgoing_reply("My PAN is ABCDE1234F and password is test123")
    assert "PAN" not in out
    assert "ABCDE1234F" not in out


def test_sanitize_blocks_aadhaar() -> None:
    out = _sanitize_outgoing_reply("Aadhaar 1234 5678 9012, please verify")
    assert "1234" not in out


def test_sanitize_blocks_card_and_cvv() -> None:
    out = _sanitize_outgoing_reply("Card 4111 1111 1111 1111 CVV 123")
    assert "4111" not in out
    assert "CVV 123" not in out


def test_tone_normalize_removes_excited_language() -> None:
    out = _tone_normalize_reply("Oh no! Arre bhagwan!! Wow!!! Please help!")
    assert "oh no" not in out.lower()
    assert "arre bhagwan" not in out.lower()
    assert "wow" not in out.lower()
    assert "!" not in out


def test_engagement_question_rotates_and_maps_targets() -> None:
    from app.main import _ensure_engagement_question

    # "phone" target must map into ask_phone pool, not generic "other".
    r1 = _ensure_engagement_question(
        "Observed.",
        "phone",
        salt="s1:1",
        recent_user_messages=["Which option should I choose next?"],
    )
    assert any(k in r1.lower() for k in ["number", "callback", "call back", "whatsapp"])
