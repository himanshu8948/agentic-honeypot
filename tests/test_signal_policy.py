from app.signal_policy import assess_sender_signals, normalize_sender_header, risk_to_zone


def test_assess_sender_signals_for_unknown_sms_header():
    out = assess_sender_signals(
        platform="sms",
        sender_header="ZZ-UNKNOWN",
        sender_number=None,
        in_contacts=False,
        trusted_headers={"AX-HDFCBK"},
    )
    assert out.delta >= 20
    assert "unknown_sms_header" in out.reasons
    assert "sender_not_in_contacts" in out.reasons


def test_assess_sender_signals_for_trusted_sms_header():
    out = assess_sender_signals(
        platform="sms",
        sender_header="AX-HDFCBK",
        sender_number=None,
        in_contacts=True,
        trusted_headers={"AX-HDFCBK"},
    )
    assert out.delta == 0
    assert "trusted_sms_header" in out.reasons


def test_risk_zone_mapping():
    assert risk_to_zone(10) == "observe"
    assert risk_to_zone(35) == "warn_and_confirm"
    assert risk_to_zone(55) == "block_high_risk_actions"
    assert risk_to_zone(80) == "lethal"


def test_normalize_sender_header():
    assert normalize_sender_header("VK-ABCDEF") == "ABCDEF"
    assert normalize_sender_header("abc123") == "ABC123"
