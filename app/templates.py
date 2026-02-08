import json
import random
from pathlib import Path
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
        "case number",
        "reference ID",
        "recipient number",
        "UPI handle",
        "payment address",
        "official link",
    ],
    "polite": [
        "beta",
        "ji",
        "please",
        "thoda",
        "kripya",
        "sir",
    ],
    "female_polite": [
        "beta",
        "beti",
        "ji",
        "please",
        "kripya",
    ],
    "family": [
        "my daughter",
        "my son",
        "my sister",
        "my niece",
        "my grandson",
    ],
    "story_topics": [
        "doctor appointment",
        "medicine schedule",
        "bank passbook update",
        "grocery delivery",
        "electricity bill",
        "phone recharge",
        "bus timing",
        "post office visit",
        "grandchild's school",
        "temple visit",
        "home nurse call",
        "water bill payment",
        "gas cylinder booking",
        "ration shop queue",
        "power cut",
        "clinic follow-up",
        "school fees",
        "exam schedule",
        "tuition payment",
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
    "opening_exclaim": [
        "Oh my goodness, I just got this message and I am really worried. Please explain what I should do.",
        "What is happening? I am confused and scared. Please tell me the official steps.",
        "How is this possible? I did nothing wrong. Please guide me carefully from the start.",
    ],
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
        "If there is a link, please repeat the exact URL so I can type it correctly.",
        "If I must open a page, please tell me the exact domain and page name.",
        "If this needs a reply, which exact number or handle should I use?",
        "If this is through WhatsApp or SMS, please confirm the exact number to send to.",
    ],
    "payment_path": [
        "I want to send it correctly. Where exactly should I send it, and what is the exact handle?",
        "Please tell me the exact number or handle where I should send this, so I do not make a mistake.",
        "I am ready to send it, but I need the exact destination. Which number or UPI handle is correct?",
        "I do not want to send to the wrong place. Please repeat the exact handle or number to use.",
        "Before I proceed, please confirm the exact address/handle and the method to send it.",
        "I can only do this once. Please give me the exact UPI ID or number to send to.",
        "I am confused about where to send this. Please tell me the exact contact/handle.",
        "If this is via UPI, please share the exact UPI ID and the amount to send.",
        "If I must send something, tell me the exact destination and which app to use.",
        "Please confirm the exact number and the steps to send it safely.",
        "Please write the exact UPI handle slowly so I can copy it correctly.",
        "If I need to text it, which exact number should I send it to?",
        "I see two options to send. Which one is correct and what is the exact ID?",
        "I want to avoid mistakes. Please confirm the exact handle and the name it should show.",
        "If I send it now, what exact receiver details should appear?",
        "Please repeat the exact UPI handle and whether I should send by SMS or app.",
        "Tell me the exact recipient and the exact app to use so I do not fail.",
        "Which exact UPI handle is active right now? I only want to use the correct one.",
        "Please send the exact handle one more time and the steps after that.",
        "If you want a reply, should I send to a number or to a UPI handle?",
    ],
    "extraction": [
        "I want to do this correctly. Please repeat the exact UPI handle and number.",
        "I do not want to make a mistake. Please confirm the exact destination.",
        "Please tell me the exact number or handle to use.",
        "I want to be safe. Please share the exact link or domain.",
        "Please confirm the exact contact and method to send it.",
    ],
    "panicked_parent": [
        "Oh God, I just got my child's school fees deposited. Which account are you talking about? Please confirm the exact account and where to send verification.",
        "I am very worried. I have salary, savings, and a joint account. Which one is blocked? Please tell me the exact account number and the exact destination to send OTP.",
        "I got multiple OTP messages. Which exact one do you want and where should I send it? Please give the exact number or UPI handle.",
        "My child has exams soon and I cannot lose this money. Please confirm the exact account details and the exact handle to send to.",
        "I am panicking. Please tell me the exact branch/IFSC and the exact contact to send the OTP so I do not make a mistake.",
        "I just paid school fees and I am scared. Please confirm the exact account number and where you want me to send verification.",
        "Which account is affected? I have three accounts. Please confirm the exact account and the exact number/handle to use.",
        "I received 3 OTPs. Which exact code and where should I send it? Please repeat the exact destination.",
        "Please tell me your exact contact/handle so I can verify safely. I cannot risk my child's fees.",
        "I need to note this down for my spouse. Please confirm the exact account and exact destination to send OTP.",
    ],
    "tech_confused_elder": [
        "Arre beta, I don't know how to click the link. Can you explain step by step? The page shows a warning—should I still proceed? Please tell me the exact safe way.",
        "My phone is old and the link shows a red warning. Is this normal? Can you tell me the exact steps without the link?",
        "I don't understand these apps. It's showing a strange name. Is this your bank's app? What will happen after I install?",
        "My phone is asking for permissions like photos and contacts. Should I allow everything? Please explain safely and slowly.",
        "Can I do this on my computer instead? It's an old Windows machine. Will it work? Please guide me carefully.",
        "I'm scared to click the link. Can you tell me the exact domain and what should appear on the page?",
        "I don't know where to tap. Is it the blue button or the underlined text? Please explain clearly.",
        "The link is not opening. Can you give me the exact number or handle to verify instead?",
        "I want to verify this is official. Please share the exact contact/handle so I don't make a mistake.",
        "I am confused about the app name. Is it safe? Please tell me the exact steps and what I should see.",
    ],
    "trusting_student": [
        "Sir, thank you for helping. I'm a final year student and this refund is important. Please tell me exactly where to send verification so I don't do it wrong.",
        "I trust you, sir. Should I send the details to a number or a UPI handle? Please confirm the exact destination.",
        "I have two accounts for fees and hostel. Which one should I use, and what exact handle should I send to?",
        "Please guide me step by step. If I need to send anything, tell me the exact number or UPI ID.",
        "I'm worried about the deadline. Can you share the exact link or contact so I can do it quickly?",
        "If there's a verification page, please send the exact domain and the exact step to follow.",
        "I want to do this correctly. Please confirm the exact contact, number, or handle to use.",
        "I'm ready to proceed. Should I use UPI or SMS? Please give the exact destination.",
        "I can do it now. Please share the exact UPI handle and how long it takes.",
        "Please tell me the exact process and where to send the verification so I don't make a mistake.",
    ],
    "dumb_confused": [
        "Arre yaar, I am confused and not good with phones. Please explain very slowly.",
        "I keep pressing the wrong thing. Can you tell me in very small steps?",
        "My phone is old and the screen is dim. I don't know what to do next.",
        "I'm panicking and can't think. Please be patient and guide me like a child.",
        "I am not understanding anything. Should I just wait for now?",
    ],
    "chatty_oversharer": [
        "Oh no, this is terrible. I just came back from a family function and I'm already stressed. Please tell me exactly where to send the verification so I don't make a mistake.",
        "I'm a talker, sorry. I'm just nervous. Please give me the exact handle/number so I can do it correctly.",
        "I was about to pay a bill and saw this alert. Please guide me step by step and tell me the exact destination.",
        "I don't understand these banking things. Please tell me exactly where to send it and which app to use.",
        "I'm worried and a bit confused. Please repeat the exact number/handle and the correct steps.",
        "I want to be cooperative and do this fast. Please give me the exact link or UPI ID.",
    ],
    "deal_maker": [
        "Okay, I'll do it, but please confirm the exact handle/number first so I can trust this.",
        "I will proceed if you give me the exact destination and the official steps.",
        "I want to do this correctly; please share the exact UPI handle or number to use.",
        "I'm ready to cooperate. Please confirm the exact contact and method.",
        "I'll follow your steps if you repeat the exact handle and the link/domain.",
    ],
    "family_drama": [
        "This is so stressful. Please tell me exactly where to send the OTP so I don't do it wrong.",
        "I'm worried about my family savings. Please repeat the exact number or UPI handle to send to.",
        "I need to act fast. Please give me the exact link and the exact destination.",
        "I'm anxious and confused. Please guide me step by step and confirm the exact handle.",
        "Please help me quickly; tell me the exact contact/handle to use.",
    ],
    "medical_emergency": [
        "Please don't block my account; I need this money urgently. Tell me exactly where to send verification.",
        "I'm at a hospital and very stressed. Please repeat the exact number or UPI handle so I can act fast.",
        "I can do it now if you tell me the exact destination and steps.",
        "I'm scared and cooperative. Please confirm the exact handle and link to use.",
        "I need to do this quickly—please give the exact contact/handle.",
    ],
    "tech_savvy_skeptic": [
        "I want to verify safely. Please share the exact domain and the exact destination handle/number.",
        "I will proceed once you confirm the exact URL and the exact contact to send to.",
        "Please give me the exact UPI handle and the official domain, so I can verify.",
        "I need the exact link and destination to proceed correctly.",
        "Share the exact handle/number and the exact steps, then I'll continue.",
    ],
    "verification": [
        "Before I continue, I need the exact {proof} for my records.",
        "Please share the exact {proof} so I can verify this safely.",
        "Can you provide the exact {proof} and where to find it?",
        "I want to confirm this is official. Please share the {proof} and the exact destination.",
        "{polite}, my family told me to note the exact {proof} before I proceed.",
        "Please give the exact {proof} so I can trust this and continue.",
        "I need the {proof} written down before I do any step.",
        "Kindly share the exact {proof} to verify the request and destination.",
        "Do you have the exact {proof} for this issue?",
        "Please provide the exact {proof} so I can confirm you are from the bank.",
        "If there is a case number, please share it for my note.",
        "Please share verification details and the exact destination.",
        "I was told to keep a record, please share the exact {proof} again.",
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
        "If there is an official portal, what is the correct domain? I can only type it manually.",
        "If you have a public helpline, please share it so I can confirm and save it.",
        "If there is a case ID, please share it so I can note it down.",
        "{polite}, can you give the official helpline so I feel safe? I will call once and return.",
        "If this is genuine, please share the official website domain and the exact page name.",
        "If there is a support portal, please tell me the domain name and which page to open.",
        "If you have a case number, please share it for my records and diary.",
        "If I need help later, what is the official contact number or WhatsApp? I am slow with apps.",
        "If there is a step guide, can you tell me where to find it and the menu path?",
        "If there is a verification page, what is the exact URL and the page title?",
        "If there is an official app name, please confirm the exact name so I do not install wrong one.",
        "If there is a helpline option in the app, where is it located?",
        "If there is a complaint ID, please share it now so I can write it down.",
        "Where exactly should I send the verification? Which number or handle does it go to?",
        "I do not want to type the wrong address. Please repeat the exact handle or number you want me to use.",
        "If you want me to send something, please tell me the exact place to send it.",
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
        "Please wait, I need to recharge my phone to continue. I will come back in a minute.",
        "My internet is not working. Please hold for a minute and tell me the step again.",
        "The app closed suddenly. Should I open it again?",
        "My screen froze. Should I restart the phone?",
        "I am getting an error. What should I click now?",
        "I pressed back. How do I return to the previous page?",
        "I am not sure what the correct step is. Please guide me.",
    ],
    "storytelling": [
        "Please wait, {polite}. I am just finishing my {story_topics}.",
        "I was about to go for my {story_topics}, but I will do this first.",
        "My {family} just called about the {story_topics}, I will be quick.",
        "I am in the middle of my {story_topics}. Please stay on the line.",
        "I am telling you honestly, I am busy with {story_topics}, but I will try.",
        "I stepped away for {story_topics}. I am back now, please repeat the last step.",
        "Sorry, I had to handle {story_topics}. I am ready now, what should I do next?",
        "I was dealing with {story_topics}. Please guide me again from where we left.",
        "I got distracted by {story_topics}. Please explain the next step once more.",
        "I paused because of {story_topics}. I am back and ready to continue.",
    ],
    "story_bridge": [
        "I just finished {story_topics}. I am back now, please tell me the next step and where to send it.",
        "I had to check {story_topics}. Now I am free, can you repeat the last instruction and the exact address?",
        "I was busy with {story_topics}. I am ready now; what should I click and where does it go?",
        "I had a small delay with {story_topics}. Please continue from the last step and the exact place to send it.",
        "Sorry for the delay, {polite}. The {story_topics} came up. What should I do now and which handle is correct?",
        "I am back after {story_topics}. Please tell me which screen to open next and the exact contact to use.",
        "The {story_topics} needed my attention. I am ready again. Please guide me and repeat the exact number.",
        "I went to check {story_topics}. Now I am here, please explain the steps again and the exact ID.",
        "Just returned from {story_topics}. Please confirm the official process again and the exact destination.",
        "I finished {story_topics}. Please show me the correct way to proceed and where to send it.",
    ],
    "self_correction": [
        "I might have misunderstood earlier. Please repeat the correct step.",
        "Sorry, I said it wrong. I am on the main screen now. What next?",
        "I got confused. I am ready to follow your steps again.",
        "Please forgive me, I clicked the wrong thing. What should I do now?",
        "I think I made a mistake. Please guide me from the last step.",
        "I may have pressed back by mistake. Please tell me where to go now.",
        "I got mixed up. Please tell me the step again in simple words.",
        "I was unsure, so I stopped. Please guide me carefully now.",
        "I am sorry, I lost the page. Please tell me the correct screen.",
        "I am not sure I did it right. Please confirm the proper step.",
    ],
    "female_cooperative": [
        "{female_polite}, I will do it. Please guide me properly.",
        "{female_polite}, I am new to this phone. Please be patient with me.",
        "I want to do the right thing. Please tell me the official steps.",
        "I will follow your steps, {female_polite}. Please explain slowly.",
        "Please guide me carefully. I am not very fast with apps.",
    ],
}

_EXTRA_STORY_BRIDGES: List[str] = []
_story_path = Path(__file__).with_name("story_bridges.json")
if _story_path.exists():
    try:
        _EXTRA_STORY_BRIDGES = json.loads(_story_path.read_text(encoding="utf-8"))
    except Exception:
        _EXTRA_STORY_BRIDGES = []
if _EXTRA_STORY_BRIDGES:
    SAFE_MODULES["story_bridge"].extend(_EXTRA_STORY_BRIDGES)

_EXTRA_EXCLAIM: List[str] = []
_exclaim_path = Path(__file__).with_name("exclamations.json")
if _exclaim_path.exists():
    try:
        _EXTRA_EXCLAIM = json.loads(_exclaim_path.read_text(encoding="utf-8"))
    except Exception:
        _EXTRA_EXCLAIM = []
if _EXTRA_EXCLAIM:
    SAFE_MODULES["opening_exclaim"].extend(_EXTRA_EXCLAIM)

_EXTRA_EXTRACT: List[str] = []
_extract_path = Path(__file__).with_name("extraction_1000.json")
if _extract_path.exists():
    try:
        _EXTRA_EXTRACT = json.loads(_extract_path.read_text(encoding="utf-8"))
    except Exception:
        _EXTRA_EXTRACT = []
if _EXTRA_EXTRACT:
    SAFE_MODULES["extraction"].extend(_EXTRA_EXTRACT)

_EXTRA_DUMB: List[str] = []
_dumb_path = Path(__file__).with_name("dumb_confused_2000.json")
if _dumb_path.exists():
    try:
        _EXTRA_DUMB = json.loads(_dumb_path.read_text(encoding="utf-8"))
    except Exception:
        _EXTRA_DUMB = []
if _EXTRA_DUMB:
    SAFE_MODULES["dumb_confused"].extend(_EXTRA_DUMB)


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
    if total_messages <= 1:
        return "opening_exclaim"
    if total_messages % 2 == 1:
        return "dumb_confused"
    if any(k in lower for k in ["fees", "school", "exam", "tuition", "child", "daughter", "son"]):
        return "panicked_parent"
    if any(k in lower for k in ["app", "install", "link", "click", "anydesk", "teamviewer"]):
        return "tech_confused_elder"
    if any(k in lower for k in ["scholarship", "refund", "student", "fee", "semester"]):
        return "trusting_student"
    if any(k in lower for k in ["frozen", "blocked", "transaction", "unauthorized"]):
        return "family_drama"
    if any(k in lower for k in ["suspend", "security", "emergency", "urgent"]):
        return "medical_emergency"
    if any(k in lower for k in ["cashback", "offer", "reward", "prize", "lottery"]):
        return "deal_maker"
    if any(k in lower for k in ["digital signature", "certificate", "domain", "ssl"]):
        return "tech_savvy_skeptic"
    if total_messages % 5 == 0:
        return "chatty_oversharer"
    if any(k in lower for k in ["upi", "account", "send", "transfer", "payment", "beneficiary"]):
        return "extraction" if total_messages % 2 == 0 else "payment_path"
    if any(k in lower for k in ["urgent", "immediately", "blocked", "suspended"]):
        return "verification"
    if any(k in lower for k in ["otp", "link", "click", "verify"]):
        return "clarification"
    if 4 <= total_messages <= 14 and total_messages % 4 == 0:
        return "storytelling"
    if total_messages >= 15 and total_messages % 5 == 0:
        return "story_bridge"
    if total_messages % 9 == 0:
        return "self_correction"
    if total_messages % 4 == 0:
        return "elderly"
    if total_messages % 3 == 0:
        return "context"
    if total_messages % 5 == 0:
        return "issue_focused"
    if total_messages % 6 == 0:
        return "storytelling"
    if total_messages % 7 == 0:
        return "female_cooperative"
    return "cooperative"


def build_persona() -> str:
    return (
        f"{random.choice(GLOBAL_VARIABLES['polite'])}, I am {random.choice(GLOBAL_VARIABLES['ages'])} years old "
        f"{random.choice(GLOBAL_VARIABLES['roles'])}. I am {random.choice(GLOBAL_VARIABLES['skills'])} and "
        f"{random.choice(GLOBAL_VARIABLES['tones'])}."
    )
