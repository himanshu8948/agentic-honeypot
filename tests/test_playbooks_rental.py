from app.playbooks import build_reply, detect_domain


def test_detect_domain_rental_scam() -> None:
    msg = "Flat for rent in XYZ Society. Deposit and token required. Share UPI for advance payment."
    assert detect_domain(msg) == "rental_scam"


def test_build_reply_rental_scam_all_languages() -> None:
    convo = [
        {"sender": "scammer", "text": "Hi, I am the owner. Flat for rent in ABC Society.", "timestamp": 0},
        {"sender": "user", "text": "Okay, is it available?", "timestamp": 1},
        {"sender": "scammer", "text": "Many people interested. Pay token to confirm booking.", "timestamp": 2},
    ]
    for lang in ["en", "hi", "hinglish"]:
        pb = build_reply(
            domain="rental_scam",
            next_target="address",
            persona="default",
            conversation=convo,
            language=lang,
            verbosity="low",
        )
        assert isinstance(pb.reply, str)
        assert len(pb.reply.strip()) > 0

