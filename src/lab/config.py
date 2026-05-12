"""Runtime settings loaded from environment / .env.

Access via ``get_settings()``. The result is lru_cached, so the same
``Settings`` instance is reused across the process. Tests can clear the
cache with ``get_settings.cache_clear()`` to pick up monkeypatched
environment variables.

``.env`` is owned by ``make up`` (rewritten with the dynamic Postgres
host port on every container start) — never edit it by hand.
"""

from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",  # .env may contain unrelated keys; tolerate them
    )

    DATABASE_URL: str = "postgresql+psycopg://postgres:postgres@localhost:5432/lab"
    TEST_DATABASE_URL: str = "postgresql+psycopg://postgres:postgres@localhost:5432/lab_test"

    @field_validator("DATABASE_URL", "TEST_DATABASE_URL")
    @classmethod
    def normalize_database_url(cls, v: str) -> str:
        if v.startswith("postgresql://"):
            # only first occurrence — passwords may contain the literal scheme
            return v.replace("postgresql://", "postgresql+psycopg://", 1)
        return v


@lru_cache
def get_settings() -> Settings:
    return Settings()
