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
    use_llm: bool
    db_path: str
    rule_threshold: int
    llm_threshold: float
    guvi_callback_url: str


def load_settings() -> Settings:
    service_api_key = _get_env("SERVICE_API_KEY")
    if not service_api_key:
        raise RuntimeError("SERVICE_API_KEY is required")

    use_llm = _get_env("USE_LLM", "0").lower() in {"1", "true", "yes"}

    groq_api_keys: list[str] = []
    if use_llm:
        groq_keys_raw = _get_env("GROQ_API_KEYS")
        if groq_keys_raw:
            groq_api_keys = [k.strip() for k in groq_keys_raw.split(",") if k.strip()]
        else:
            idx = 1
            while True:
                key = _get_env(f"GROQ_API_KEY_{idx}")
                if not key:
                    break
                groq_api_keys.append(key)
                idx += 1
        if not groq_api_keys:
            groq_key = _get_env("GROQ_API_KEY")
            if groq_key:
                groq_api_keys = [groq_key]
        if not groq_api_keys:
            raise RuntimeError("GROQ_API_KEYS or GROQ_API_KEY_1..N is required when USE_LLM=1")

    groq_model = _get_env("GROQ_MODEL", "mistral-7b-instruct")
    groq_base_url = _get_env("GROQ_BASE_URL", "https://api.groq.com/openai/v1")
    db_path = _get_env("DB_PATH", "./himanshu_agentic_honeypot.db")

    rule_threshold = int(_get_env("RULE_THRESHOLD", "3"))
    llm_threshold = float(_get_env("LLM_THRESHOLD", "0.6"))

    guvi_callback_url = _get_env(
        "GUVI_CALLBACK_URL",
        "https://hackathon.guvi.in/api/updateHoneyPotFinalResult",
    )

    return Settings(
        service_api_key=service_api_key,
        groq_api_keys=groq_api_keys,
        groq_model=groq_model,
        groq_base_url=groq_base_url,
        use_llm=use_llm,
        db_path=db_path,
        rule_threshold=rule_threshold,
        llm_threshold=llm_threshold,
        guvi_callback_url=guvi_callback_url,
    )
