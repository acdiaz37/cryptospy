import httpx
import logging
from typing import Dict

from config import ASSET_UNIVERSE, ASSET_SYMBOLS

logger = logging.getLogger(__name__)
BASE_URL = "https://api.coingecko.com/api/v3"


class CoinGeckoClient:
    def __init__(self):
        self.client = httpx.AsyncClient(base_url=BASE_URL, timeout=30.0)

    async def get_prices(self, ids: list[str] | None = None) -> Dict[str, float]:
        """
        Obtiene precios actuales en USD para una lista de CoinGecko IDs.
        Si no se pasan IDs, usa el universo completo.
        """
        target_ids = ids or ASSET_UNIVERSE
        ids_param = ",".join(target_ids)
        try:
            resp = await self.client.get(
                "/simple/price",
                params={
                    "ids": ids_param,
                    "vs_currencies": "usd",
                    "precision": "8",
                },
            )
            resp.raise_for_status()
            data = resp.json()
            # Extraer solo los precios USD
            result = {}
            for cid in target_ids:
                if cid in data and "usd" in data[cid]:
                    result[cid] = float(data[cid]["usd"])
            return result
        except httpx.HTTPStatusError as e:
            logger.error("CoinGecko HTTP error: %s - %s", e.response.status_code, e.response.text)
            raise
        except Exception as e:
            logger.error("CoinGecko error: %s", e)
            raise

    def pair_from_id(self, gecko_id: str) -> str:
        """Devuelve el par tipo BTC/USDT dado un CoinGecko ID."""
        symbol = ASSET_SYMBOLS.get(gecko_id, gecko_id.upper())
        return f"{symbol}/USDT"

    def id_from_symbol(self, symbol: str) -> str | None:
        """Busca el CoinGecko ID dado un símbolo como BTC, ETH, etc."""
        sym = symbol.upper()
        for gid, s in ASSET_SYMBOLS.items():
            if s == sym:
                return gid
        return None
