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
    # rationale: cues are pre-generated into the disk cache at session start, so
    # synthesis latency doesn't matter — prefer the larger "high" English model.
    tts_voice_en: str = "en_US-lessac-high"
    tts_voice_vi: str = "vi_VN-vais1000-medium"
    # rationale: >1 slows phoneme pacing slightly; ~1.05 sounds calmer and less
    # robotic for short coaching cues. Folded into the audio cache key.
    tts_length_scale: float = 1.05

    # Optional higher-quality Vietnamese engine (F5-TTS, a flow-matching neural
    # model that clones a reference voice). Piper's VI voice is intelligible but
    # robotic; F5 sounds markedly more human. It needs `torch`/`f5-tts` (the
    # `f5` optional-dependency group — deliberately kept out of the runtime image)
    # and a downloaded model (`make tts-f5`). When engine="f5" but the deps or
    # model are missing, synthesis silently falls back to Piper, so enabling this
    # is safe. Set engine="f5" only where the extras are installed.
    tts_vi_engine: str = "piper"  # "piper" | "f5"
    tts_f5_dir: str = "media/tts/f5"  # holds model_last.pt, vocab.txt, ref.wav
    tts_f5_model: str = "model_last.pt"
    tts_f5_arch: str = "F5TTS_Base"
    # Reference clip + its exact transcript that F5 clones the voice from. The
    # default ref.wav is the bundled VIVOS Southern-Vietnamese female clip (copied
    # in by `make tts-f5`; see assets/ATTRIBUTION.md). Drop in your own clean
    # 5-10s clip + its transcript here to change the coach's voice.
    tts_f5_ref_audio: str = "ref.wav"
    tts_f5_ref_text: str = "nếu thỉnh thoảng có vài ngày nghỉ người thụy điển thường ra đảo chơi."
    tts_f5_speed: float = 0.9  # <1 slows F5 slightly, calmer coaching pace

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
