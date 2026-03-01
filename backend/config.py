from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    secret_key: str = "change-me"
    admin_email: str = "admin@example.com"
    admin_password: str = ""
    exp_token: int = 30
    db_url: str = "sqlite+pysqlite:///:memory:?cache=shared"
    password_length: int = 8
    jwt_algorithm: str = "HS256"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
