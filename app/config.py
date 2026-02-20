import os
from dataclasses import dataclass

from dotenv import load_dotenv


load_dotenv()


def _get_env(name: str, default: str | None = None) -> str | None:
    value = os.getenv(name)
    if value is None or value == "":
        return default
    return value


def _get_env_any(names: tuple[str, ...], default: str | None = None) -> str | None:
    for name in names:
        value = _get_env(name)
        if value is not None and value != "":
            return value
    return default


@dataclass(frozen=True)
class Settings:
    service_api_key: str
    db_path: str
    rule_threshold: int
    guvi_callback_url: str
    trusted_sms_headers: set[str]
    llm_enabled: bool
    groq_api_key: str
    groq_model: str
    llm_timeout_ms: int
    llm_max_tokens: int
    llm_temperature: float
    llm_max_session_tokens: int
    llm_max_daily_tokens: int
    # Engagement/callback pacing knobs (defaults are conservative for most demos)
    target_messages_exchanged: int
    min_messages_before_complete: int
    min_messages_before_complete_with_intel: int
    callback_mode: str


def load_settings() -> Settings:
    service_api_key = _get_env_any(("SERVICE_API_KEY", "API_KEY"))
    if not service_api_key:
        raise RuntimeError("SERVICE_API_KEY (or API_KEY) is required")

    db_path = _get_env("DB_PATH", "./honeypot.db")

    rule_threshold = int(_get_env("RULE_THRESHOLD", "8"))

    guvi_callback_url = _get_env_any(("GUVI_CALLBACK_URL", "CALLBACK_URL"), "")
    trusted_sms_headers = _load_trusted_headers()

    llm_enabled = (_get_env("LLM_ENABLED", "false") or "false").strip().lower() in {"1", "true", "yes", "on"}
    groq_api_key = _get_env("GROQ_API_KEY", "") or ""
    groq_model = (_get_env("GROQ_MODEL", "llama-3.1-8b-instant") or "llama-3.1-8b-instant").strip()
    llm_timeout_ms = int(_get_env("LLM_TIMEOUT_MS", "4000") or "4000")
    llm_max_tokens = int(_get_env("LLM_MAX_TOKENS", "180") or "180")
    llm_temperature = float(_get_env("LLM_TEMPERATURE", "0.2") or "0.2")
    llm_max_session_tokens = int(_get_env("LLM_MAX_SESSION_TOKENS", "2500") or "2500")
    llm_max_daily_tokens = int(_get_env("LLM_MAX_DAILY_TOKENS", "200000") or "200000")

    # Default to hackathon-style long engagements; override in env for shorter demos.
    target_messages_exchanged = int(_get_env("TARGET_MESSAGES_EXCHANGED", "150"))
    min_messages_before_complete = int(_get_env("MIN_MESSAGES_BEFORE_COMPLETE", "10"))
    min_messages_before_complete_with_intel = int(_get_env("MIN_MESSAGES_BEFORE_COMPLETE_WITH_INTEL", "6"))
    callback_mode = (_get_env("CALLBACK_MODE", "always") or "always").strip().lower()
    if callback_mode not in {"always", "on_complete"}:
        callback_mode = "always"

    return Settings(
        service_api_key=service_api_key,
        db_path=db_path,
        rule_threshold=rule_threshold,
        guvi_callback_url=guvi_callback_url,
        trusted_sms_headers=trusted_sms_headers,
        llm_enabled=llm_enabled,
        groq_api_key=groq_api_key,
        groq_model=groq_model,
        llm_timeout_ms=max(500, min(llm_timeout_ms, 10000)),
        llm_max_tokens=max(60, min(llm_max_tokens, 400)),
        llm_temperature=max(0.0, min(llm_temperature, 0.7)),
        llm_max_session_tokens=max(200, min(llm_max_session_tokens, 200000)),
        llm_max_daily_tokens=max(1000, min(llm_max_daily_tokens, 5000000)),
        target_messages_exchanged=max(0, target_messages_exchanged),
        min_messages_before_complete=max(1, min_messages_before_complete),
        min_messages_before_complete_with_intel=max(1, min_messages_before_complete_with_intel),
        callback_mode=callback_mode,
    )

def _load_trusted_headers() -> set[str]:
    headers: set[str] = set()
    csv_headers = _get_env("TRUSTED_SMS_HEADERS", "")
    if csv_headers:
        for h in csv_headers.split(","):
            v = h.strip().upper()
            if v:
                headers.add(v)

    file_path = _get_env("TRUSTED_SMS_HEADERS_PATH")
    if file_path:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                for line in f:
                    v = line.strip().upper()
                    if v and not v.startswith("#"):
                        headers.add(v)
        except OSError:
            pass

    return headers
