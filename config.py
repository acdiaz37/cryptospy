import json
import os
from pathlib import Path
from pydantic_settings import BaseSettings


def _load_json(filename: str) -> dict:
    path = Path(filename)
    if not path.exists():
        raise FileNotFoundError(f"Required config file not found: {filename}")
    return json.loads(path.read_text(encoding="utf-8"))


# ─────────────────────────────────────────────
# 1. Variables sensibles / por entorno → .env
# ─────────────────────────────────────────────
ENV_PATH = Path(".env")


class Settings(BaseSettings):
    BOT_TOKEN: str = ""
    GROK_API_KEY: str = ""
    GOOGLE_SHEETS_ID: str = ""
    GOOGLE_SERVICE_ACCOUNT_JSON: str = ""
    ANALYSIS_WINDOW_HOURS: int = 24
    ENV: str = "development"
    WEBHOOK_URL: str = ""
    WEBHOOK_PORT: int = 8080

    class Config:
        env_file = ".env"

    def get_service_account_credentials(self) -> dict:
        """Devuelve el dict de credenciales de Google, ya sea desde JSON string o archivo."""
        raw = self.GOOGLE_SERVICE_ACCOUNT_JSON.strip()
        if raw.startswith("{"):
            return json.loads(raw)
        # Es un path
        with open(raw, "r", encoding="utf-8") as f:
            return json.load(f)

    def save(self) -> None:
        """Persiste los valores actuales al archivo .env"""
        lines = [
            f"BOT_TOKEN={self.BOT_TOKEN}",
            f"GROK_API_KEY={self.GROK_API_KEY}",
            f"GOOGLE_SHEETS_ID={self.GOOGLE_SHEETS_ID}",
            f"GOOGLE_SERVICE_ACCOUNT_JSON={self.GOOGLE_SERVICE_ACCOUNT_JSON}",
            f"ANALYSIS_WINDOW_HOURS={self.ANALYSIS_WINDOW_HOURS}",
            f"ENV={self.ENV}",
            f"WEBHOOK_URL={self.WEBHOOK_URL}",
            f"WEBHOOK_PORT={self.WEBHOOK_PORT}",
        ]
        ENV_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


settings = Settings()


# ─────────────────────────────────────────────
# 2. Assets / Universo de criptos → JSON
# ─────────────────────────────────────────────
_assets_config = _load_json("config/assets.json")
ASSET_UNIVERSE: list[str] = _assets_config["universe"]
ASSET_SYMBOLS: dict[str, str] = _assets_config["symbols"]


# ─────────────────────────────────────────────
# 3. Prompts → JSON
# ─────────────────────────────────────────────
_prompts_config = _load_json("prompts/analysis.json")
PROMPT_MODEL: str = _prompts_config["model"]
PROMPT_TEMPERATURE: float = _prompts_config["temperature"]
PROMPT_MAX_TOKENS: int = _prompts_config["max_tokens"]
PROMPT_SYSTEM_TEMPLATE: str = _prompts_config["system_prompt"]
PROMPT_USER_TEMPLATE: str = _prompts_config["user_prompt_structure"]
