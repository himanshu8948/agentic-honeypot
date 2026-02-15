from app.main import _sanitize_outgoing_reply


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

