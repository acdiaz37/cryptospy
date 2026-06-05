import os
import json
from pathlib import Path
from pydantic_settings import BaseSettings


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


ASSET_UNIVERSE = [
    "bitcoin", "ethereum", "solana", "ripple", "chainlink",
    "avalanche-2", "hyperliquid", "injective-protocol", "fetch-ai",
    "cardano", "polkadot", "polygon", "arbitrum", "optimism",
    "near", "aptos", "sui", "celestia", "dydx", "render-token",
    "immutable-x", "mantle", "filecoin", "cosmos", "algorand",
    "stellar", "vechain", "tron", "litecoin", "bitcoin-cash",
    "uniswap", "aave", "maker", "lido-dao", "curve-dao-token",
    "synthetix-network-token", "compound-governance-token",
    "the-graph", "1inch", "pancakeswap-token", "cosmos-hub",
    "ethereum-classic", "okb", "leo-token", "crypto-com-chain",
    "kaspa", "bonk", "pepe", "shiba-inu", "dogecoin"
]

# Mapeo de CoinGecko ID a símbolo de par (para mostrar y para consultas)
ASSET_SYMBOLS = {
    "bitcoin": "BTC",
    "ethereum": "ETH",
    "solana": "SOL",
    "ripple": "XRP",
    "chainlink": "LINK",
    "avalanche-2": "AVAX",
    "hyperliquid": "HYPE",
    "injective-protocol": "INJ",
    "fetch-ai": "FET",
    "cardano": "ADA",
    "polkadot": "DOT",
    "polygon": "MATIC",
    "arbitrum": "ARB",
    "optimism": "OP",
    "near": "NEAR",
    "aptos": "APT",
    "sui": "SUI",
    "celestia": "TIA",
    "dydx": "DYDX",
    "render-token": "RENDER",
    "immutable-x": "IMX",
    "mantle": "MNT",
    "filecoin": "FIL",
    "cosmos": "ATOM",
    "algorand": "ALGO",
    "stellar": "XLM",
    "vechain": "VET",
    "tron": "TRX",
    "litecoin": "LTC",
    "bitcoin-cash": "BCH",
    "uniswap": "UNI",
    "aave": "AAVE",
    "maker": "MKR",
    "lido-dao": "LDO",
    "curve-dao-token": "CRV",
    "synthetix-network-token": "SNX",
    "compound-governance-token": "COMP",
    "the-graph": "GRT",
    "1inch": "1INCH",
    "pancakeswap-token": "CAKE",
    "cosmos-hub": "ATOM",
    "ethereum-classic": "ETC",
    "okb": "OKB",
    "leo-token": "LEO",
    "crypto-com-chain": "CRO",
    "kaspa": "KAS",
    "bonk": "BONK",
    "pepe": "PEPE",
    "shiba-inu": "SHIB",
    "dogecoin": "DOGE",
}
