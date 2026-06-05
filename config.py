from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    BOT_TOKEN: str
    WEBHOOK_URL: str | None = None
    WEBHOOK_PORT: int = 8080
    ENV: str = "development"

    class Config:
        env_file = ".env"


settings = Settings()
