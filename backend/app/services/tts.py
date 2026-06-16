"""Server-side neural text-to-speech (Piper) for the workout voice coach.

This replaces the browser Web Speech API, whose voice quality depends on whatever
the client device happens to have installed (often a robotic espeak fallback on
Linux). Piper is a small, CPU-friendly ONNX TTS that ships good English *and*
Vietnamese voices, so one engine serves every cue language.

Generated WAVs are cached on disk keyed by (voice, text). The workout cues are
nearly deterministic, so after the first play of each phrase every later play is
an instant cache hit that never spins the model.

Voice model files (`<voice>.onnx` + `<voice>.onnx.json`) are NOT committed — they
are downloaded once with `make tts-voices` into `<media_dir>/tts/voices`. If TTS
is disabled or the model is missing the service raises ``TtsUnavailableError`` and
the API returns 503; the frontend then falls back to browser speech.
"""

import hashlib
import wave
from functools import lru_cache
from pathlib import Path
from typing import Any

from app.config import get_settings

_SUBDIR = "tts"
# Keep the query/text bounded so a stray request can't drive a huge synthesis.
MAX_TEXT_CHARS = 600


class TtsUnavailableError(Exception):
    """TTS is disabled, the text is empty, or the requested voice model/engine is missing."""


def voice_for_lang(lang: str) -> str:
    """Map a cue language to a configured Piper voice. Unknown langs use English."""
    settings = get_settings()
    return settings.tts_voice_vi if lang == "vi" else settings.tts_voice_en


def _voices_dir() -> Path:
    return Path(get_settings().media_dir) / _SUBDIR / "voices"


def _cache_dir() -> Path:
    return Path(get_settings().media_dir) / _SUBDIR / "cache"


def cache_key(voice: str, text: str) -> str:
    """Stable cache filename stem for a (voice, text) pair."""
    return hashlib.sha256(f"{voice}\n{text}".encode()).hexdigest()


def _model_paths(voice: str) -> tuple[Path, Path]:
    base = _voices_dir() / voice
    return base.with_name(f"{voice}.onnx"), base.with_name(f"{voice}.onnx.json")


@lru_cache(maxsize=4)
def _load_voice(voice: str) -> Any:
    """Load (and cache in-process) a Piper voice. Piper is imported lazily so the
    app — and the test suite — import fine without the heavy dependency present."""
    try:
        from piper import PiperVoice
    except ImportError as exc:  # piper-tts not installed
        raise TtsUnavailableError("piper-tts is not installed") from exc

    model, config = _model_paths(voice)
    if not model.exists() or not config.exists():
        raise TtsUnavailableError(f"voice model not found: {voice}")
    return PiperVoice.load(str(model), config_path=str(config))


def synthesize(text: str, lang: str = "en") -> Path:
    """Return the path to a WAV of ``text`` in ``lang``, generating + caching on miss.

    Raises ``TtsUnavailableError`` when TTS is off, text is empty, or the model is
    unavailable — the router translates that to a 503 so the client can fall back.
    """
    if not get_settings().tts_enabled:
        raise TtsUnavailableError("TTS is disabled")
    text = (text or "").strip()[:MAX_TEXT_CHARS]
    if not text:
        raise TtsUnavailableError("empty text")

    voice = voice_for_lang(lang)
    out = _cache_dir() / f"{cache_key(voice, text)}.wav"
    if out.exists():
        return out

    piper_voice = _load_voice(voice)
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_suffix(".wav.tmp")
    with wave.open(str(tmp), "wb") as wav_file:
        # synthesize_wav writes a complete WAV (headers + samples) for the whole text.
        piper_voice.synthesize_wav(text, wav_file)
    tmp.replace(out)  # publish atomically so a concurrent reader never sees a partial file
    return out
