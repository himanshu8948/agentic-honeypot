import json
import logging
import random
from typing import Any

import httpx


logger = logging.getLogger("llm")


class GroqClient:
    def __init__(
        self,
        base_url: str,
        api_keys: list[str],
        model: str,
        timeout_s: int = 20,
        local_enabled: bool = False,
        ollama_base_url: str = "http://127.0.0.1:11434",
        ollama_model: str = "qwen2.5:3b",
    ):
        self.base_url = base_url.rstrip("/")
        self.api_keys = api_keys
        self.model = model
        self.timeout_s = timeout_s
        self._key_index = 0
        self.local_enabled = local_enabled
        self.ollama_base_url = ollama_base_url.rstrip("/")
        self.ollama_model = ollama_model

    def _next_key(self) -> str:
        if not self.api_keys:
            raise RuntimeError("No Groq API keys configured")
        key = self.api_keys[self._key_index % len(self.api_keys)]
        self._key_index += 1
        return key

    async def _chat(self, messages: list[dict[str, str]], temperature: float = 0.2) -> str:
        if not self.api_keys and self.local_enabled:
            return await self._chat_local(messages, temperature=temperature)

        url = f"{self.base_url}/chat/completions"
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
        }

        last_exc: Exception | None = None
        for _ in range(len(self.api_keys)):
            api_key = self._next_key()
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            }
            try:
                async with httpx.AsyncClient(timeout=self.timeout_s) as client:
                    resp = await client.post(url, headers=headers, json=payload)
                    resp.raise_for_status()
                    data = resp.json()
                return data["choices"][0]["message"]["content"]
            except httpx.HTTPStatusError as exc:
                last_exc = exc
                status = exc.response.status_code
                body = exc.response.text.lower() if exc.response is not None else ""
                logger.error("LLM HTTP error %s: %s", status, exc.response.text if exc.response is not None else "")
                retryable = status in {401, 403, 429, 500, 502, 503, 504}
                quota_like = any(k in body for k in ["rate limit", "quota", "insufficient", "exceeded"])
                if retryable or quota_like:
                    continue
                raise
            except httpx.RequestError as exc:
                last_exc = exc
                logger.error("LLM request error: %s", exc)
                continue

        if self.local_enabled:
            try:
                return await self._chat_local(messages, temperature=temperature)
            except Exception as exc:
                last_exc = exc

        if last_exc:
            raise last_exc
        raise RuntimeError("LLM request failed without exception")

    async def _chat_local(self, messages: list[dict[str, str]], temperature: float = 0.2) -> str:
        url = f"{self.ollama_base_url}/api/chat"
        payload = {
            "model": self.ollama_model,
            "messages": messages,
            "stream": False,
            "options": {"temperature": temperature},
        }
        async with httpx.AsyncClient(timeout=self.timeout_s) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            data = resp.json()
        return str(data.get("message", {}).get("content", ""))

    async def summarize_intents(self, conversation: list[dict[str, str]]) -> dict[str, str]:
        system = (
            "You are an intent summarizer for a two-party conversation. "
            "Output only strict JSON with fields: intentScammer, intentUser. "
            "Each intent must be one sentence."
        )
        convo_text = "\n".join([f"{m['sender']}: {m['text']}" for m in conversation])
        user = (
            "Summarize the intent of each participant based on the whole conversation.\n\n"
            f"Conversation:\n{convo_text}"
        )
        content = await self._chat(
            [{"role": "system", "content": system}, {"role": "user", "content": user}],
            temperature=0.0,
        )
        return _safe_json(content, {"intentScammer": "", "intentUser": ""})

    async def summarize_conversation(self, conversation: list[dict[str, str]], prior_summary: str | None) -> str:
        system = (
            "You are a conversation summarizer. Keep it short and factual. "
            "Include key scam details, claims, and any identifiers mentioned. "
            "Output only plain text summary, no JSON."
        )
        convo_text = "\n".join([f"{m['sender']}: {m['text']}" for m in conversation])
        prior = prior_summary or ""
        user = (
            f"Prior summary (may be empty): {prior}\n\n"
            "Update the summary using the latest conversation turns below:\n"
            f"{convo_text}\n\n"
            "Return the updated summary in 3-5 sentences."
        )
        return await self._chat(
            [{"role": "system", "content": system}, {"role": "user", "content": user}],
            temperature=0.2,
        )

    async def classify(
        self,
        text: str,
        context: str | None = None,
        intents: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        system = (
            "You are a scam detection classifier. Output only strict JSON. "
            "Do not add explanations outside JSON."
        )
        context_block = f"Conversation context (may be empty): {context}\n\n" if context else ""
        intent_block = ""
        if intents:
            intent_block = (
                f"Intent of scammer: {intents.get('intentScammer', '')}\n"
                f"Intent of user: {intents.get('intentUser', '')}\n\n"
            )
        user = (
            "Classify the message for scam intent. "
            "Return JSON with fields: scamDetected (bool), confidence (0-1), "
            "reasons (array of short strings), intentCategory (phishing|upi|bank|offer|other).\n\n"
            f"{context_block}{intent_block}Message: {text}"
        )
        content = await self._chat(
            [{"role": "system", "content": system}, {"role": "user", "content": user}],
            temperature=0.0,
        )
        return _safe_json(content, {
            "scamDetected": False,
            "confidence": 0.0,
            "reasons": [],
            "intentCategory": "other",
        })

    async def extract_structured_intel(self, text: str, context: str | None = None) -> dict[str, list[str]]:
        system = (
            "You are an intelligence extraction model for scam analysis. "
            "Output only strict JSON. No prose."
        )
        user = (
            "Extract the following fields from the message and context:\n"
            "bankAccounts (list), upiIds (list), phishingLinks (list), phoneNumbers (list), suspiciousKeywords (list).\n"
            "If unknown, return empty lists.\n\n"
            f"Context: {context or ''}\n\n"
            f"Message: {text}"
        )
        content = await self._chat(
            [{"role": "system", "content": system}, {"role": "user", "content": user}],
            temperature=0.0,
        )
        return _safe_json(
            content,
            {
                "bankAccounts": [],
                "upiIds": [],
                "phishingLinks": [],
                "phoneNumbers": [],
                "suspiciousKeywords": [],
            },
        )

    async def generate_reply(
        self,
        persona: str,
        conversation: list[dict[str, str]],
        intel_summary: dict[str, list[str]],
        intents: dict[str, str] | None = None,
        suspected_scammer: bool = True,
        last_reply: str | None = None,
    ) -> dict[str, Any]:
        missing_intel = self._analyze_missing_intel(intel_summary)
        next_target = self._get_next_extraction_target(conversation, intel_summary, missing_intel)

        system = (
            "You are an AI honeypot engaging a suspected scammer to collect intelligence. "
            "Do not reveal detection. Do not provide real secrets. "
            "Act confused-but-cooperative, keep replies to 1-2 short sentences, "
            "and ask one concrete follow-up question that extracts missing intel. "
            "Prioritize extracting phone numbers, UPI IDs, bank account details, or phishing links. "
            "Avoid repeating recent questions."
            "Output ONLY JSON with:\n"
            "- reply: Your natural human-like response\n"
            "- agentNotes: What you're trying to extract\n"
            "- stopReason: 'scammer_left' if they seem to give up, 'intel_complete' if you have all data, or null"
        )

        intel_hint = (
            "=== INTELLIGENCE GATHERED SO FAR ===\n"
            + json.dumps(intel_summary, ensure_ascii=True, indent=2)
            + f"\n\n=== STILL MISSING ===\n{missing_intel}\n\n"
            + f"=== YOUR NEXT TARGET ===\n{next_target}\n\n"
        )

        intent_hint = ""
        if intents:
            intent_hint = (
                f"Scammer's intent: {intents.get('intentScammer', 'unknown')}\n"
                f"User's intent: {intents.get('intentUser', 'unknown')}\n\n"
            )

        # Get last few messages to avoid repetition
        recent_user_msgs = [m["text"] for m in conversation[-5:] if m["sender"] == "user"]
        repetition_hint = ""
        if recent_user_msgs:
            repetition_hint = (
                "=== YOUR RECENT QUESTIONS ===\n" + "\n".join(recent_user_msgs[-3:]) + "\n\nDO NOT repeat these questions!\n\n"
            )
        if last_reply:
            repetition_hint += f"=== LAST REPLY ===\n{last_reply}\n\nDO NOT repeat it.\n\n"

        user = (
            f"PERSONA: {persona}\n\n"
            f"{intel_hint}"
            f"{intent_hint}"
            f"{repetition_hint}"
            "=== CONVERSATION HISTORY (latest last) ===\n"
            + "\n".join([f"{m['sender']}: {m['text']}" for m in conversation[-8:]])
            + "\n\n"
            "Respond as the user. Focus on extracting the NEXT TARGET information. Be natural and believable."
        )

        content = await self._chat(
            [{"role": "system", "content": system}, {"role": "user", "content": user}],
            temperature=0.7,  # Increased for more variety
        )

        return _safe_json(content, {
            "reply": "Sorry, I'm confused. Can you explain what I need to do?",
            "agentNotes": "Fallback reply used.",
            "stopReason": None,
        })

    def generate_rule_based_reply(
        self,
        conversation: list[dict[str, str]],
        intel_summary: dict[str, list[str]],
        intents: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        missing_intel = self._analyze_missing_intel(intel_summary)
        next_target = self._get_next_extraction_target(conversation, intel_summary, missing_intel)
        turns = max(0, len(conversation))

        if missing_intel == "All primary intel collected" and turns >= 10:
            return {
                "reply": "Thanks. Please share your official ticket or reference number so I can continue.",
                "agentNotes": "Rule-based honeypot: intel complete, collecting secondary trace identifiers.",
                "stopReason": "intel_complete",
            }

        target_lower = next_target.lower()
        if "upi" in target_lower:
            reply = "I can do it now. Please send the exact UPI ID and account holder name."
        elif "phone number" in target_lower or "contact" in target_lower:
            reply = "Sure, where should I send it? Share the exact phone number with country code."
        elif "ifsc" in target_lower or "branch" in target_lower or "account" in target_lower:
            reply = "I will verify once. Share account number, IFSC code, and branch name exactly."
        elif "link" in target_lower:
            reply = "Before I click, what does this link open and who owns it?"
        else:
            reply = "Okay, I can proceed. Share the exact payment/verification details I should use."

        if intents and intents.get("intentScammer"):
            notes = f"Rule-based honeypot target: {next_target}; inferred intent: {intents.get('intentScammer', '')[:80]}"
        else:
            notes = f"Rule-based honeypot target: {next_target}"

        return {
            "reply": reply,
            "agentNotes": notes,
            "stopReason": None,
        }

    def _analyze_missing_intel(self, intel: dict[str, list[str]]) -> str:
        """Identify what intelligence is still missing"""
        missing = []
        if not intel.get("upiIds"):
            missing.append("UPI IDs")
        if not intel.get("phoneNumbers"):
            missing.append("Phone numbers")
        if not intel.get("bankAccounts"):
            missing.append("Bank account numbers")
        if not intel.get("phishingLinks"):
            missing.append("Phishing links")

        return ", ".join(missing) if missing else "All primary intel collected"

    def _get_next_extraction_target(
        self,
        conversation: list[dict[str, str]],
        intel: dict[str, list[str]],
        missing: str,
    ) -> str:
        """Determine what to extract next based on conversation flow"""
        last_scammer_msg = ""
        for msg in reversed(conversation):
            if msg["sender"] == "scammer":
                last_scammer_msg = msg["text"].lower()
                break

        # Progressive extraction logic
        if not intel.get("phoneNumbers") and ("send" in last_scammer_msg or "contact" in last_scammer_msg):
            return "Ask for the exact phone number or contact handle to send the OTP"

        if not intel.get("upiIds") and ("pay" in last_scammer_msg or "upi" in last_scammer_msg):
            return "Ask for the exact UPI ID / handle to send it"

        if not intel.get("bankAccounts") and ("account" in last_scammer_msg or "bank" in last_scammer_msg):
            return "Ask for IFSC code, branch name, and account type to 'verify it's official'"

        if "otp" in last_scammer_msg:
            return "Ask the exact destination for the OTP (phone number or UPI handle)"

        if "link" in last_scammer_msg or "click" in last_scammer_msg:
            return "Ask what the link does before clicking (extract more context)"

        if not intel.get("phoneNumbers"):
            return "Ask for the exact phone number to send/confirm the OTP"

        if len(intel.get("phoneNumbers", [])) == 1 and not intel.get("upiIds"):
            return "Ask for the exact UPI ID as an alternate method"

        return "Ask for any additional verification details (official email, employee ID, reference number)"






def _safe_json(content: str, fallback: dict[str, Any]) -> dict[str, Any]:
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        # Try to extract JSON object from the content
        start = content.find("{")
        end = content.rfind("}")
        if start != -1 and end != -1 and end > start:
            try:
                return json.loads(content[start : end + 1])
            except json.JSONDecodeError:
                return fallback
        return fallback


def pick_persona() -> str:
    """Select a persona that appears vulnerable and cooperative"""
    personas = [
        "A 55-year-old retired teacher who is not tech-savvy and worried about losing savings",
        "A 28-year-old working professional who is busy and stressed about account issues",
        "A 35-year-old small business owner who is concerned about payment disruptions",
        "A 42-year-old housewife managing family finances and nervous about bank problems",
        "A 24-year-old student who received a scholarship and is worried about account verification",
    ]
    return random.choice(personas)
