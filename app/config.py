import os
from dataclasses import dataclass


def _get_env(name: str, default: str | None = None) -> str | None:
    value = os.getenv(name)
    if value is None or value == "":
        return default
    return value


@dataclass(frozen=True)
class Settings:
    service_api_key: str
    groq_api_keys: list[str]
    groq_model: str
    groq_base_url: str
    db_path: str
    rule_threshold: int
    llm_threshold: float
    guvi_callback_url: str
    trusted_sms_headers: set[str]


def load_settings() -> Settings:
    service_api_key = _get_env("SERVICE_API_KEY")
    if not service_api_key:
        raise RuntimeError("SERVICE_API_KEY is required")

    groq_api_keys = _load_groq_api_keys()

    groq_model = _get_env("GROQ_MODEL", "llama3-70b-8192")
    groq_base_url = _get_env("GROQ_BASE_URL", "https://api.groq.com/openai/v1")
    db_path = _get_env("DB_PATH", "./honeypot.db")

    rule_threshold = int(_get_env("RULE_THRESHOLD", "3"))
    llm_threshold = float(_get_env("LLM_THRESHOLD", "0.6"))

    guvi_callback_url = _get_env(
        "GUVI_CALLBACK_URL",
        "https://hackathon.guvi.in/api/updateHoneyPotFinalResult",
    )
    trusted_sms_headers = _load_trusted_headers()

    return Settings(
        service_api_key=service_api_key,
        groq_api_keys=groq_api_keys,
        groq_model=groq_model,
        groq_base_url=groq_base_url,
        db_path=db_path,
        rule_threshold=rule_threshold,
        llm_threshold=llm_threshold,
        guvi_callback_url=guvi_callback_url,
        trusted_sms_headers=trusted_sms_headers,
    )


def _load_groq_api_keys() -> list[str]:
    # Preferred single-key configuration.
    one_key = _get_env("GROQ_API_KEY")
    if one_key and one_key.strip():
        return [one_key.strip()]

    # Backward compatibility: if old CSV env is provided, use only first key.
    keys_raw = _get_env("GROQ_API_KEYS")
    if keys_raw:
        keys = [k.strip() for k in keys_raw.split(",") if k.strip()]
        if keys:
            return [keys[0]]

    raise RuntimeError("GROQ_API_KEY is required")


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
