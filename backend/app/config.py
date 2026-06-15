from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings, read from environment / `.env`."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+asyncpg://homeshred:homeshred@localhost:5434/homeshred"
    test_database_url: str = (
        "postgresql+asyncpg://homeshred:homeshred@localhost:5434/homeshred_test"
    )
    cors_origins: str = "http://localhost:3000"
    # Where uploaded progress photos are stored (SPEC §19.8 W3). Mounted as a volume in prod.
    media_dir: str = "media"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
