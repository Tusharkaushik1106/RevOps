from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "local"
    log_level: str = "INFO"
    database_url: str = "postgresql+psycopg://ric:ric@localhost:5432/ric"
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    razorpay_key_id: str | None = None
    razorpay_key_secret: str | None = None
    llm_provider: str = "disabled"
    llm_api_key: str | None = None
    supabase_url: str | None = None
    supabase_anon_key: str | None = None
    cors_origins: list[str] = ["http://localhost:3000"]
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
