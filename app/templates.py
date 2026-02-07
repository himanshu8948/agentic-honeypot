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
}

PHASE_TEMPLATES: Dict[str, List[str]] = {
    "hook": [
        "Hello? Who is this? Is this {relatives}?",
        "Can you speak louder? My {ailments} today.",
        "I was just waiting for a call from {banks}. Are you them?",
        "Beta, don't shout. I am an old man living in {cities}.",
        "Is this regarding the money I sent to {relatives}?",
        "Wait, let me turn off the TV. [Sound of static] Hello?",
        "Who? {banks}? Which branch? The one near the market?",
        "I don't have an account there. Or maybe I do... I forget things due to my {ailments}.",
        "Are you the same person who called yesterday about my {technologies}?",
        "Hold on, let me put on my glasses. Who did you say you are?",
    ],
    "stall": [
        "I am looking for my card. It is in the cupboard... or maybe {relatives} took it.",
        "The number is rubbed off. I can only see the last 4 digits: 4... 5... wait, is that a 6?",
        "Oh no! I dropped the card behind the sofa. My {ailments} make it hard to bend down.",
        "Can I just give you my passbook number? It is a {banks} passbook.",
        "Wait, {distractions}. Please hold for one minute... [Silence for 20 seconds]... Hello?",
        "I found the card! Oh wait, this is my library card. Let me check the other drawer.",
        "Why do you need the number? {relatives} told me never to share it.",
        "I am reading the number: 5... 2... no, 8... sorry, my eyes are bad.",
        "The card is blue color. Is that the right one?",
        "Can you call me back in 10 minutes? {distractions}.",
    ],
    "trap": [
        "I opened the Play Store. It is asking for a password. Is it my birthday?",
        "I see an app called 'Candy Crush'. Do I download that?",
        "You want me to download AnyDesk? Is that for fixing the fan?",
        "It says 'Download Pending' for the last 10 minutes. The internet in {cities} is very bad.",
        "I clicked 'Allow' but now the screen is black. Did I break the phone?",
        "Where is the 'Support' button? I only see a picture of a cat.",
        "My {relatives} installed something yesterday. Should I delete it?",
        "It is asking for my fingerprint. But my hands are oily from eating.",
        "QuickSupport? Is that the red icon or the blue one?",
        "I cannot find the TeamViewer. Can I just send you a photo on WhatsApp?",
    ],
    "bait": [
        "Okay, write down the OTP. It is 4... 5... wait, the message disappeared.",
        "The message says 'Do not share this code'. Should I still give it?",
        "My OTP is 1... 2... 3... 4. Is that correct? It seems too simple.",
        "I didn't get an SMS. I got an email from {banks}. Should I read that?",
        "The code is 894... oh wait, that is the time on the clock.",
        "I sent the money to the UPI ID you gave, but it failed. It says 'Wrong Receiver'.",
        "My name on the card is {fake_names}. Spell it? S-U-R-E...",
        "The expiry date is 02/1980. Is that expired?",
        "The CVV is the number on the front or the back?",
        "I typed the amount 10,000 but I think I added an extra zero. Did you get 1 lakh?",
    ],
    "intel": [
        "I cannot type your UPI ID. Can you send me a QR code instead?",
        "What is your employee ID? I need to write it in my diary for {relatives}.",
        "Which branch of {banks} are you calling from? I can come there personally.",
        "Give me your manager's number. My phone is not working, I will call from the landline.",
        "If I send the money, will I get a receipt? Send me your WhatsApp number first.",
        "I have a lot of money in my {banks} account. 50 lakhs. Is it safe?",
        "Can you verify my address? Do you have my address in {cities}?",
        "What is the IFSC code of your bank? I need to authorize the transfer.",
        "I am pressing the button but nothing is happening. Can you do it from your side?",
        "Send me a test message on WhatsApp so I know it's you.",
    ],
}


def _fill(template: str) -> str:
    for key, values in GLOBAL_VARIABLES.items():
        if "{" + key + "}" in template:
            template = template.replace("{" + key + "}", random.choice(values))
    return template


def build_combinatorial_reply(phase: str, last_reply: str | None) -> str:
    pool = PHASE_TEMPLATES.get(phase, PHASE_TEMPLATES["hook"])
    random.shuffle(pool)
    for t in pool:
        line = _fill(t)
        if last_reply is None or line.strip().lower() != last_reply.strip().lower():
            return line
    return _fill(pool[0])


def choose_phase(total_messages: int) -> str:
    if total_messages <= 2:
        return "hook"
    if total_messages <= 5:
        return "stall"
    if total_messages <= 8:
        return "trap"
    if total_messages <= 12:
        return "bait"
    return "intel"