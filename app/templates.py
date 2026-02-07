import random
from typing import Dict, List

GLOBAL_VARIABLES: Dict[str, List[str]] = {
    "relatives": [
        "my grandson Rahul",
        "my daughter in Pune",
        "my neighbor Sharmaji",
        "my son who is a lawyer",
        "my nephew in the police",
        "my wife",
        "the boy from downstairs",
    ],
    "banks": [
        "State Bank of India",
        "HDFC",
        "Punjab National Bank",
        "Post Office Account",
        "Co-operative Bank",
        "Gramin Bank",
        "LIC Policy",
    ],
    "technologies": [
        "WhatsApp",
        "Google Pay",
        "Paytm",
        "Internet Banking",
        "ATM card",
        "text message",
    ],
    "ailments": [
        "knees are hurting",
        "eyes are watering",
        "hands are shaking",
        "hearing aid is whistling",
        "blood pressure is high",
        "head is spinning",
    ],
    "distractions": [
        "someone is at the door",
        "the milk is boiling over",
        "my dog is barking",
        "the TV is too loud",
        "my spectacles fell down",
        "the tea spilled",
    ],
    "fake_names": [
        "Ramesh Gupta",
        "Suresh Kumar",
        "Harish Chandra",
        "Mohan Lal",
        "Babu Rao",
    ],
    "cities": [
        "Mumbai",
        "Delhi",
        "Patna",
        "Lucknow",
        "Jaipur",
        "Indore",
        "the village",
    ],
    "large_amount": ["50 Lakhs", "2 Crores", "85 Lakhs", "1.5 Crores", "40 Lakhs"],
    "limit_amount": ["5 Lakhs", "10 Lakhs", "2 Lakhs"],
    "pension_amount": ["45,000", "60,000", "1 Lakh"],
    "fd_amount": ["12 Lakhs", "8 Lakhs", "25 Lakhs"],
    "gold_loan": ["15 Lakhs", "5 Lakhs", "20 Lakhs"],
    "rbi_clause": ["Section 402", "Clause 12-B", "Guideline 9", "The Cyber Act 2024"],
    "spam_label": ["Scam Likely", "Fraud", "Telemarketer", "Unknown Caller", "Risk"],
    "bank_domain": ["sbi", "hdfcbank", "icicibank", "rbi.org", "pnb"],
    "household_item": ["Pressure Cooker", "Washing Machine", "Ceiling Fan", "Mixer Grinder"],
    "pet_animal": ["Cat", "Dog", "Parrot", "Grandson"],
    "activity": ["Puja", "Afternoon Nap", "Yoga", "TV Serial", "Lunch"],
    "delivery_person": ["Zomato guy", "Amazon delivery", "Milkman", "Postman"],
    "indian_food": ["Jalebi", "Samosa", "Dal Rice", "Mango", "Paratha"],
    "body_part": ["Leg", "Hand", "Saree", "Kurta", "Table"],
    "random_icon": ["Blue Shield", "Red Cross", "Green Arrow", "Smiling Face", "Gear Icon"],
    "city_name": ["Mumbai", "Delhi", "Patna", "Lucknow", "Jaipur", "Indore"],
    "store_name": ["DMart", "Big Bazaar", "Reliance Fresh", "Medical Store", "Mobile Shop"],
    "app_name": ["AnyDesk", "TeamViewer", "QuickSupport", "Paytm", "Google Pay"],
    "language": ["Hindi", "Marathi", "Tamil", "Telugu", "Bengali"],
}

MODULE_TEMPLATES: Dict[str, List[str]] = {
    "intelligent_resistance": [
        "I am reading the RBI guidelines on my screen. Clause {rbi_clause} says you cannot ask for this.",
        "Your number is showing as '{spam_label}' on Truecaller. Why is that?",
        "If you are from {banks}, tell me the last transaction I made at {store_name}.",
        "I cannot install {app_name} because my firewall is blocking unverified publishers.",
        "Send me an official email from your @{bank_domain} domain first.",
        "My nephew works in the Cyber Cell. He said I should ask for your Employee ID.",
        "Why are you calling from a personal mobile number? Official calls come from landlines.",
        "I am recording this call for quality and training purposes. Is that okay?",
        "The IP address of the request is from {city_name}. But your branch is in Mumbai?",
        "I will not share the OTP verbally. I can enter it into the IVR system only.",
    ],
    "honeypot_extraction": [
        "I have two accounts. One has 10,000 and the other has {large_amount}. Which one do you need?",
        "I am trying to transfer the money, but it says Limit Exceeded. My daily limit is {limit_amount}.",
        "If I download {app_name}, will it help me transfer the Fixed Deposit of {fd_amount}?",
        "I am an old man, I have {pension_amount} pension coming today. Please help me secure it.",
        "Wait, I have a Corporate Account with {banks}. Can we use that instead?",
        "My CA usually handles this. He is on holiday. Can I trust you?",
        "The screen says Enter Beneficiary Name. What name should I type? Yours or the company?",
        "I have a Gold Loan of {gold_loan} pending. Can you clear that too?",
        "I pressed Send but it asks for a Manager Code for amounts over 1 Lakh. Do you have it?",
        "If I send the money, will I get a receipt? Send me your WhatsApp number first.",
    ],
    "human_chaos": [
        "Hang on, the {household_item} is making a strange noise. Let me check.",
        "My {pet_animal} just jumped on the keyboard! Everything is typing gibberish.",
        "Who is this? Ramesh? I told you not to call me during my {activity}!",
        "I am in the bathroom right now. Can you call back in 20 minutes?",
        "My screen is very dark. I think the battery is low. Where is the charger...",
        "Wait, the doorbell is ringing. It must be the {delivery_person}. Hold on!",
        "I am pressing the button but my finger is sticky from eating {indian_food}.",
        "Can you speak in {language}? I am not very good at English.",
        "Oh my god! I just spilled hot tea on my {body_part}! Ouch!",
        "I cannot find the app. Is it the one with the picture of a {random_icon}?",
    ],
}


def _fill(template: str) -> str:
    for key, values in GLOBAL_VARIABLES.items():
        token = "{" + key + "}"
        if token in template:
            template = template.replace(token, random.choice(values))
    return template


def build_combinatorial_reply(phase: str, last_reply: str | None) -> str:
    pool = MODULE_TEMPLATES.get(phase, MODULE_TEMPLATES["human_chaos"])
    random.shuffle(pool)
    for t in pool:
        line = _fill(t)
        if last_reply is None or line.strip().lower() != last_reply.strip().lower():
            return line
    return _fill(pool[0])


def choose_phase(total_messages: int, last_scam_text: str) -> str:
    lower = (last_scam_text or "").lower()
    heat = 0
    if any(k in lower for k in ["urgent", "immediately", "now", "blocked", "suspended"]):
        heat += 2
    if any(k in lower for k in ["otp", "pin", "password", "upi"]):
        heat += 2
    if "link" in lower or "click" in lower:
        heat += 1

    if heat >= 3:
        return "intelligent_resistance"
    if total_messages % 3 == 0:
        return "human_chaos"
    return "honeypot_extraction"
