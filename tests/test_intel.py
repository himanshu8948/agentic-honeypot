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