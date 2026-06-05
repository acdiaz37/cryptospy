import httpx
import json
import logging
from typing import Optional

from config import settings, PROMPT_MODEL, PROMPT_TEMPERATURE, PROMPT_MAX_TOKENS, PROMPT_SYSTEM_TEMPLATE, PROMPT_USER_TEMPLATE
from models.signal import SignalResponse

logger = logging.getLogger(__name__)
BASE_URL = "https://api.x.ai/v1"
MAX_RETRIES = 2


class GrokClient:
    def __init__(self):
        self.api_key = settings.GROK_API_KEY
        self.client = httpx.AsyncClient(
            base_url=BASE_URL,
            timeout=120.0,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
        )

    def _build_prompt(self) -> tuple[str, str]:
        window = settings.ANALYSIS_WINDOW_HOURS
        system = PROMPT_SYSTEM_TEMPLATE.replace("{{ANALYSIS_WINDOW_HOURS}}", str(window))
        user = PROMPT_USER_TEMPLATE.replace("{{ANALYSIS_WINDOW_HOURS}}", str(window))
        return system, user

    async def fetch_signals(self) -> Optional[SignalResponse]:
        system_prompt, user_prompt = self._build_prompt()
        payload = {
            "model": PROMPT_MODEL,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": PROMPT_TEMPERATURE,
            "max_tokens": PROMPT_MAX_TOKENS,
        }

        for attempt in range(MAX_RETRIES + 1):
            try:
                resp = await self.client.post("/chat/completions", json=payload)
                resp.raise_for_status()
                data = resp.json()
                raw_content = data["choices"][0]["message"]["content"]

                # Limpiar posible markdown ```json ... ```
                content = raw_content.strip()
                if content.startswith("```"):
                    lines = content.splitlines()
                    if lines[0].startswith("```"):
                        lines = lines[1:]
                    if lines and lines[-1].startswith("```"):
                        lines = lines[:-1]
                    content = "\n".join(lines).strip()

                parsed = json.loads(content)
                logger.debug("Grok raw response parsed successfully")
                return SignalResponse(**parsed)

            except (json.JSONDecodeError, KeyError, ValueError) as e:
                logger.warning("Grok parse error (attempt %d): %s", attempt + 1, e)
                if "raw_content" in dir():
                    logger.debug("Raw content: %s", raw_content)
                if attempt == MAX_RETRIES:
                    logger.error("Grok failed after %d retries", MAX_RETRIES + 1)
                    return None
            except httpx.HTTPStatusError as e:
                logger.error("Grok HTTP error: %s - %s", e.response.status_code, e.response.text)
                return None
            except Exception as e:
                logger.error("Grok unexpected error: %s", e)
                return None

        return None
