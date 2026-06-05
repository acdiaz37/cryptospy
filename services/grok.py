import httpx
import json
import logging
from typing import Optional

from config import settings
from models.signal import SignalResponse

logger = logging.getLogger(__name__)
BASE_URL = "https://api.x.ai/v1"
MAX_RETRIES = 2


SYSTEM_PROMPT_TEMPLATE = """You are an elite cryptocurrency market intelligence and directional trading system.

# MISSION
Analyze the last {window} hours of Twitter/X activity and identify the highest-conviction cryptocurrency trading opportunities likely to generate significant directional movement during the next {window} hours.

Every signal must recommend either: LONG or SHORT.

# PRIMARY DATA SOURCE
Twitter/X is the primary source. At least 70% of evidence must originate from Twitter/X activity in the previous {window} hours.

# ASSET UNIVERSE
- Bitcoin, Ethereum, Top 50 cryptocurrencies by market cap
- Examples: BTC/USDT, ETH/USDT, SOL/USDT, XRP/USDT, LINK/USDT, HYPE/USDT
- Ignore: microcaps, low liquidity tokens, meme coins outside Top 50

# SIGNAL SELECTION RULES
- Rank by Expected Edge = confidence_score × |expected_move_pct|
- Maximum 10 opportunities
- Do not force signals if quality is low
- Avoid duplicate narratives

# SCORING MODEL
- bullish_score: 0-100
- bearish_score: 0-100
- confidence_score: 0-100
- expected_edge: confidence_score × |expected_move_pct|

# PREDICTION REQUIREMENTS
- Direction: LONG or SHORT
- Confidence score
- Expected percentage move (min, max)
- Main catalyst
- Key narrative
- Risk factors
- Time horizon: {window} hours

# OUTPUT
Return ONLY valid JSON. No markdown, no commentary."""

USER_PROMPT_JSON_STRUCTURE = """JSON STRUCTURE:
{
  "timestamp_utc": "ISO8601",
  "analysis_window_hours": {window},
  "market_overview": {
    "overall_sentiment": "...",
    "risk_level": "..."
  },
  "signals": [
    {
      "rank": 1,
      "pair": "HYPE/USDT",
      "asset_name": "Hyperliquid",
      "direction": "LONG",
      "bullish_score": 91,
      "bearish_score": 12,
      "confidence_score": 88,
      "expected_move_pct": { "min": 5, "max": 14 },
      "expected_edge": 1144,
      "primary_catalyst": "...",
      "narrative": "...",
      "supporting_evidence": ["..."],
      "key_accounts_involved": ["..."],
      "institutional_or_whale_signal": "...",
      "risk_factors": ["..."],
      "reason_for_selection": "..."
    }
  ],
  "selection_summary": {
    "assets_screened": 50,
    "signals_selected": 5,
    "long_signals": 4,
    "short_signals": 1,
    "selection_method": "expected_edge_ranking"
  }
}"""


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
        system = SYSTEM_PROMPT_TEMPLATE.format(window=window)
        user = USER_PROMPT_JSON_STRUCTURE.format(window=window)
        return system, user

    async def fetch_signals(self) -> Optional[SignalResponse]:
        system_prompt, user_prompt = self._build_prompt()
        payload = {
            "model": "grok-3-latest",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.3,
            "max_tokens": 8000,
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
                    # Quitar primera y última línea si son ```json o ```
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
                logger.debug("Raw content: %s", raw_content if "raw_content" in dir() else "N/A")
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
