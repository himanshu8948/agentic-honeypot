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


def load_settings() -> Settings:
    service_api_key = _get_env("SERVICE_API_KEY")
    if not service_api_key:
        raise RuntimeError("SERVICE_API_KEY is required")

    deepseek_api_key = _get_env("agentic_key")
    if not deepseek_api_key:
        raise RuntimeError("agentic_key is required")
    groq_api_keys = [deepseek_api_key]

    groq_model = _get_env("DEEPSEEK_MODEL", "deepseek-chat")
    groq_base_url = _get_env("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
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
        db_path=db_path,
        rule_threshold=rule_threshold,
        llm_threshold=llm_threshold,
        guvi_callback_url=guvi_callback_url,
    )
