from app.intel import extract_intel, rule_score


def test_extract_intel():
    intel = {
        "bankAccounts": [],
        "upiIds": [],
        "phishingLinks": [],
        "phoneNumbers": [],
        "suspiciousKeywords": [],
    }
    text = "Pay to abc@upi or call +91 99999 88888. Visit https://evil.example now."
    result = extract_intel(text, intel)
    assert "abc@upi" in result["upiIds"]
    assert "+91 99999 88888" in result["phoneNumbers"]
    assert "https://evil.example" in result["phishingLinks"]


def test_rule_score():
    text = "Urgent: your account is blocked. Verify now via this link."
    score = rule_score(text)
    assert score >= 3


def test_rule_score_high_confidence_combo():
    text = "URGENT: SBI account blocked today. Share OTP and UPI ID immediately to verify. Rs. 5000 refund pending."
    score = rule_score(text)
    assert score >= 10


def test_rule_score_phishing_openers():
    text = "Security alert for your account. Click here to verify your information."
    score = rule_score(text)
    assert score >= 4


def test_rule_score_fake_refund_openers():
    text = "Congratulations! Get 50000 cashback. Your refund of ₹5,000 is pending. Claim your discount now."
    score = rule_score(text)
    assert score >= 8
