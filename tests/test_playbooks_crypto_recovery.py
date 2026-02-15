from app.playbooks import build_reply, detect_domain


def test_detect_domain_crypto_recovery_scam() -> None:
    msg = "We are a crypto recovery team. We can trace your TXID on blockchain and recover funds. Pay recovery fee today."
    assert detect_domain(msg) == "crypto_recovery_scam"


def test_build_reply_crypto_recovery_scam_all_languages() -> None:
    convo = [
        {"sender": "scammer", "text": "We can recover your lost crypto. Our team traces blockchain transactions.", "timestamp": 0},
        {"sender": "user", "text": "Please help me recover money.", "timestamp": 1},
        {"sender": "scammer", "text": "Pay recovery fee 50000 now to start tracing.", "timestamp": 2},
    ]
    for lang in ["en", "hi", "hinglish"]:
        pb = build_reply(
            domain="crypto_recovery_scam",
            next_target="phone",
            persona="default",
            conversation=convo,
            language=lang,
            verbosity="low",
        )
        assert isinstance(pb.reply, str)
        assert len(pb.reply.strip()) > 0

