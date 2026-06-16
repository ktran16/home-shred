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

    # Server-side neural TTS (Piper) for the workout voice coach. A single CPU
    # engine covers both languages; voice models live under <media_dir>/tts/voices
    # (download with `make tts-voices`). If disabled or a model is missing the API
    # returns 503 and the frontend falls back to the browser's speech synthesis.
    tts_enabled: bool = True
    tts_voice_en: str = "en_US-amy-medium"
    tts_voice_vi: str = "vi_VN-vais1000-medium"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
