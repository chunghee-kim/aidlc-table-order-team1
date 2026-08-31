"""Application configuration (U1). Loads from environment / .env with local fallbacks."""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Secrets / infra — local fallbacks provided; override via .env (do not commit real secrets).
    jwt_secret: str = "dev-insecure-change-me"
    jwt_expire_hours: int = 16
    database_url: str = "sqlite:///./tableorder.db"
    bcrypt_cost: int = 12
    cors_origins: str = "http://localhost:5173"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()
