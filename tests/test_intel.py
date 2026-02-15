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


def test_rule_score_fake_loan_openers():
    text = "Instant loan of ₹50,000 approved. Get loan in 5 minutes, pay ₹199 fee to activate."
    score = rule_score(text)
    assert score >= 7


def test_rule_score_otp_whatsapp_hack_openers():
    text = "Wrong number, please share the OTP. Hi, I sent you OTP by mistake."
    score = rule_score(text)
    assert score >= 6


def test_rule_score_prize_lottery_openers():
    text = "Congratulations! You've won ₹1,00,000 in WhatsApp Mega Draw. You are selected for cash prize."
    score = rule_score(text)
    assert score >= 6


def test_rule_score_fake_job_openers():
    text = "Hi, this is Ravi from HR at ACME. You've been shortlisted for remote role. Pay ₹499 as registration fee."
    score = rule_score(text)
    assert score >= 7


def test_rule_score_crypto_invest_openers():
    text = "Invest ₹10,000 and get ₹25,000 in a week. Guaranteed returns of 15%."
    score = rule_score(text)
    assert score >= 6

def test_rule_score_tech_support_scam_openers():
    text = "This is Amit from Microsoft Support. Your device has malware/virus. Please install AnyDesk and share remote access code."
    score = rule_score(text)
    assert score >= 7

def test_rule_score_sim_swap_scam_openers():
    text = "Your SIM will be deactivated today. For SIM card replacement share OTP immediately."
    score = rule_score(text)
    assert score >= 7


def test_rule_score_charity_scam_openers():
    text = "Donate now to the relief fund. Pay via UPI help@upi to support charity."
    score = rule_score(text)
    assert score >= 6


def test_rule_score_ecommerce_scam_openers():
    text = "Your parcel is on hold. Click https://track.example to verify and pay the delivery charge via UPI."
    score = rule_score(text)
    assert score >= 6


def test_rule_score_tax_refund_scam_openers():
    text = "Income tax refund pending. Verify your bank details via https://tax-refund.example now."
    score = rule_score(text)
    assert score >= 6
