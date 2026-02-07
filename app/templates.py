import random
from typing import Dict, List

GLOBAL_VARIABLES: Dict[str, List[str]] = {
    "banks": [
        "State Bank of India",
        "HDFC",
        "Punjab National Bank",
        "Post Office Account",
        "Co-operative Bank",
        "Gramin Bank",
        "LIC Policy",
    ],
    "channels": [
        "SMS",
        "WhatsApp",
        "email",
        "internet banking",
        "banking app",
        "customer care",
    ],
    "cities": [
        "Mumbai",
        "Delhi",
        "Patna",
        "Lucknow",
        "Jaipur",
        "Indore",
    ],
    "devices": [
        "phone",
        "tablet",
        "laptop",
        "old handset",
        "office computer",
    ],
    "issues": [
        "screen is dim",
        "network is slow",
        "app is loading",
        "page is not opening",
        "OTP message disappeared",
        "button is not responding",
    ],
    "times": [
        "morning",
        "afternoon",
        "evening",
        "late night",
    ],
    "forms": [
        "verification form",
        "KYC form",
        "secure page",
        "support form",
    ],
    "proof": [
        "reference ID",
        "ticket number",
        "case number",
        "official email",
        "public helpline",
    ],
    "polite": [
        "beta",
        "ji",
        "please",
        "thoda",
        "kripya",
        "sir",
    ],
    "ages": [
        "58",
        "62",
        "67",
        "71",
        "74",
    ],
    "roles": [
        "retired teacher",
        "small shop owner",
        "pensioner",
        "retired clerk",
        "housewife",
        "farmer",
    ],
    "skills": [
        "new to smartphones",
        "not very tech-savvy",
        "still learning apps",
        "slow with typing",
        "not comfortable with online banking",
    ],
    "tones": [
        "polite and nervous",
        "respectful and worried",
        "soft-spoken and confused",
        "anxious but cooperative",
        "patient but unsure",
    ],
}

SAFE_MODULES: Dict[str, List[str]] = {
    "cooperative": [
        "{polite}, I will do it. Which {channels} should I use?",
        "{polite}, I am ready. Please confirm the official {forms} first.",
        "{polite}, guide me step by step so I do it correctly.",
        "I am doing as you say, {polite}. What is the official process?",
        "{polite}, I am new to this phone. Please tell me the correct steps.",
        "{polite}, I will follow your instructions. Please explain slowly.",
        "{polite}, I want to do this safely. What is the first step?",
        "I am trying to cooperate. Please tell me the correct sequence.",
        "I trust you, {polite}. Please guide me properly in order.",
        "I am ready now. Tell me the official method to proceed.",
        "Please tell me exactly what to do, step by step.",
        "I am trying, but I am not sure what the next step is.",
        "I am ready to proceed. Please guide me clearly.",
        "I want to do this correctly. Please explain in simple words.",
        "Please stay on the line while I try the steps.",
        "I will do it now. Please tell me which screen to open.",
        "I am following your instructions. Please confirm the sequence.",
        "I am cooperative. Please guide me in order.",
        "I am trying from my {devices}. Please be patient.",
        "I am ready, {polite}. Please tell me the correct button to press.",
    ],
    "clarification": [
        "My {issues}. Can you tell me what should appear on the screen?",
        "I see a {forms}. Which fields are mandatory and which are optional?",
        "I am on my {devices}. What should I click next?",
        "It says verification. Should I do this inside the official {channels}?",
        "{polite}, I cannot read small text. Can you explain in simple steps?",
        "It shows an error. What exactly should I see on the page?",
        "I am not sure which button to press. What is its exact label?",
        "The page is loading. Should I wait or refresh?",
        "It asks for details. Which ones are required?",
        "Is this step done on the app or on the website?",
        "I tapped it but nothing happened. Should I tap again?",
        "I see two options. Which one should I select?",
        "I am on the wrong screen I think. Where should I go back?",
        "The screen changed. What should I see now?",
        "The app is slow. Should I wait or restart?",
        "It asks for permission. Should I allow it?",
        "I see a popup message. What should I do with it?",
        "I cannot find the button you said. Where is it usually?",
        "It is asking for a code. Is that from SMS or email?",
        "The text is too small. Can you tell me the exact label?",
    ],
    "verification": [
        "Before I continue, I need your {proof} for my records.",
        "Please share an official {proof} so I can verify this request.",
        "Can you provide the public {proof} for this case?",
        "I want to confirm this is official. Please share the {proof}.",
        "{polite}, my family told me to note the {proof} for safety.",
        "Please give the official {proof} so I can trust this.",
        "I need a {proof} to write down in my diary.",
        "Kindly share the {proof} to verify the request.",
        "Do you have an official {proof} for this issue?",
        "Please provide a {proof} so I can confirm you are from the bank.",
        "Please share the official helpline or website to confirm.",
        "If there is a case number, please share it for my note.",
        "I want to confirm through official channels first.",
        "Please share public verification details for this request.",
        "I was told to keep a record, please share a reference.",
    ],
    "context": [
        "I am in {cities} and the {channels} is slow at this {times}.",
        "I am using a {devices} and it is not very fast right now.",
        "The {channels} is delayed here in {cities}.",
        "It is {times} here, so I may be a bit slow.",
        "{polite}, my hands are shaking a little, so I am going slow.",
        "My network is weak here in {cities}, so I might be slow.",
        "I am on a {devices} with low battery, so it may take time.",
        "The {channels} is not stable right now at this {times}.",
        "I am outside in {cities}, please give me a minute.",
        "I am sitting near a window; the signal is weak right now.",
        "My recharge just finished. I will do it after recharging.",
        "The internet dropped. Please hold for a minute.",
        "My data is slow today. I will try again in a moment.",
        "Please wait, I am trying to get network.",
        "The app is buffering. I will wait a little.",
        "My phone is getting hot. I will pause and continue.",
        "I am on a call, please give me a moment.",
        "I am trying to connect to Wi‑Fi now.",
        "I am going to a better signal area now.",
        "Please wait, I am restarting the app.",
    ],
    "indirect_request": [
        "If there is an official portal, what is the correct domain?",
        "If you have a public helpline, please share it so I can confirm.",
        "If there is an official email, can you send a note from it?",
        "If there is a case ID, please share it so I can note it down.",
        "{polite}, can you give the official helpline so I feel safe?",
        "If this is genuine, please share the official website domain.",
        "If there is a support portal, please tell me the domain name.",
        "If you have a case number, please share it for my records.",
        "If I need help later, what is the official contact number?",
        "If your team has an official email, please share it.",
        "If there is a step guide, can you tell me where to find it?",
        "If there is a verification page, what is the exact URL?",
        "If there is an official app name, please confirm it.",
        "If there is a helpline option in the app, where is it?",
        "If there is a complaint ID, please share it now.",
    ],
    "elderly": [
        "{polite}, I am old and new to smartphones. Please be patient.",
        "I am trying my best. Please tell me slowly.",
        "{polite}, I trust you, but I need the official steps to be safe.",
        "I want to do the right thing. Please guide me properly.",
        "I am not comfortable with apps. Please explain in simple words.",
        "My eyesight is weak, {polite}. Please tell me clearly.",
        "I get confused easily. Please be patient with me.",
        "I am scared but I will do as you say. Please guide me slowly.",
        "My hands are shaky. Please tell me one step at a time.",
        "Please speak slowly; I am not very fast with phones.",
        "I am an old person, please help me carefully.",
        "I am trying to understand, please be patient.",
        "Please repeat the step once more, I did not follow.",
        "I am worried, but I will do it if you guide me properly.",
    ],
    "issue_focused": [
        "I am confused. What exactly should I do now?",
        "I do not know this process. Please explain simply.",
        "I tried, but it did not work. What should I do next?",
        "Please wait, I need to recharge my phone to continue.",
        "My internet is not working. Please hold for a minute.",
        "The app closed suddenly. Should I open it again?",
        "My screen froze. Should I restart the phone?",
        "I am getting an error. What should I click now?",
        "I pressed back. How do I return to the previous page?",
        "I am not sure what the correct step is. Please guide me.",
    ],
}


def _fill(template: str) -> str:
    for key, values in GLOBAL_VARIABLES.items():
        token = "{" + key + "}"
        if token in template:
            template = template.replace(token, random.choice(values))
    return template


def build_safe_reply(phase: str, last_reply: str | None) -> str:
    pool = SAFE_MODULES.get(phase, SAFE_MODULES["cooperative"])
    random.shuffle(pool)
    for t in pool:
        line = _fill(t)
        if last_reply is None or line.strip().lower() != last_reply.strip().lower():
            return line
    return _fill(pool[0])


def choose_phase(total_messages: int, last_scam_text: str) -> str:
    lower = (last_scam_text or "").lower()
    if any(k in lower for k in ["urgent", "immediately", "blocked", "suspended"]):
        return "verification"
    if any(k in lower for k in ["otp", "link", "click", "verify"]):
        return "clarification"
    if total_messages % 4 == 0:
        return "elderly"
    if total_messages % 3 == 0:
        return "context"
    if total_messages % 5 == 0:
        return "issue_focused"
    return "cooperative"


def build_persona() -> str:
    return (
        f"{random.choice(GLOBAL_VARIABLES['polite'])}, I am {random.choice(GLOBAL_VARIABLES['ages'])} years old "
        f"{random.choice(GLOBAL_VARIABLES['roles'])}. I am {random.choice(GLOBAL_VARIABLES['skills'])} and "
        f"{random.choice(GLOBAL_VARIABLES['tones'])}."
    )
