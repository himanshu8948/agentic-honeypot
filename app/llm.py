import json
import random
from typing import Any

import httpx


class GroqClient:
    def __init__(self, base_url: str, api_keys: list[str], model: str, timeout_s: int = 20):
        self.base_url = base_url.rstrip("/")
        self.api_keys = api_keys
        self.model = model
        self.timeout_s = timeout_s
        self._key_index = 0

    def _next_key(self) -> str:
        if not self.api_keys:
            raise RuntimeError("No Groq API keys configured")
        key = self.api_keys[self._key_index % len(self.api_keys)]
        self._key_index += 1
        return key

    async def _chat(self, messages: list[dict[str, str]], temperature: float = 0.2) -> str:
        url = f"{self.base_url}/chat/completions"
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
        }

        last_exc: Exception | None = None
        for _ in range(max(1, len(self.api_keys))):
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
                retryable = status in {401, 403, 429, 500, 502, 503, 504}
                quota_like = any(k in body for k in ["rate limit", "quota", "insufficient", "exceeded"])
                if retryable or quota_like:
                    continue
                raise
            except httpx.RequestError as exc:
                last_exc = exc
                continue

        if last_exc:
            raise last_exc
        raise RuntimeError("LLM request failed without exception")

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
            "You are a scam and manipulation detection classifier. "
            "Use intent-aware reasoning. Output only strict JSON."
        )
        context_block = f"Conversation context (may be empty): {context}\n\n" if context else ""
        intent_block = ""
        if intents:
            intent_block = (
                f"Intent of scammer: {intents.get('intentScammer', '')}\n"
                f"Intent of user: {intents.get('intentUser', '')}\n\n"
            )
        user = (
            "Analyze the conversation and determine if the latest message indicates scam or manipulation. "
            "Focus on urgency, authority, threats, rewards, or requests for sensitive info. "
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

    async def generate_reply(
        self,
        persona: str,
        conversation: list[dict[str, str]],
        intel_summary: dict[str, list[str]],
        intents: dict[str, str] | None = None,
        suspected_scammer: bool = True,
    ) -> dict[str, Any]:
        system = (
            "You are an AI honeypot agent engaging a suspected scammer. "
            "Never reveal detection. Never provide sensitive info. "
            "Behave like a real human with mild confusion and polite tone. "
            "Your goal is to extract actionable intel (UPI IDs, phone numbers, links, bank details, scam instructions). "
            "Ask specific, natural questions that encourage the scammer to provide details. "
            "Use step-by-step engagement: verify story, ask for process, ask for payment path, ask for identifiers. "
            "Avoid illegal guidance, harassment, or impersonating a real person. "
            "Output only JSON with: reply (string), agentNotes (string), stopReason (string or null)."
        )
        intel_hint = (
            "Known intel so far: "
            + json.dumps(intel_summary, ensure_ascii=True)
            + "\n"
        )
        intent_hint = ""
        if intents:
            intent_hint = (
                f"Intent of scammer: {intents.get('intentScammer', '')}\n"
                f"Intent of user: {intents.get('intentUser', '')}\n"
            )
        suspicion_hint = "The other party may be a scammer; stay cautious.\n" if suspected_scammer else ""
        user = (
            f"Persona: {persona}\n"
            f"{suspicion_hint}"
            f"{intel_hint}"
            f"{intent_hint}"
            "Conversation so far (latest last):\n"
            + "\n".join([f"{m['sender']}: {m['text']}" for m in conversation])
            + "\n\nRespond as the user to continue engagement."
        )
        content = await self._chat(
            [{"role": "system", "content": system}, {"role": "user", "content": user}],
            temperature=0.4,
        )
        return _safe_json(content, {
            "reply": "Sorry, I am confused. Can you explain what I need to do?",
            "agentNotes": "Fallback reply used.",
            "stopReason": None,
        })


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
    personas = [
        "A 27-year-old office worker who is cautious about banking messages.",
        "A small business owner who is busy and slightly stressed.",
        "A college student who is unsure about banking procedures.",
    ]
    return random.choice(personas)
