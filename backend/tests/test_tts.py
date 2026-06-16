"""Pure-logic tests for the TTS service (no model / no DB needed).

End-to-end synthesis is exercised at deploy time once voice models are present;
here we lock down the language→voice routing, cache-key stability, and the
graceful-unavailable behaviour the frontend fallback relies on.
"""

import pytest

from app.config import get_settings
from app.services import tts


def test_voice_for_lang_routes_vi_and_defaults_to_en():
    settings = get_settings()
    assert tts.voice_for_lang("vi") == settings.tts_voice_vi
    assert tts.voice_for_lang("en") == settings.tts_voice_en
    # unknown languages fall back to English rather than erroring
    assert tts.voice_for_lang("fr") == settings.tts_voice_en


def test_cache_key_is_stable_and_distinguishes_voice_and_text():
    a = tts.cache_key("en_US-amy-medium", "Rest 75 seconds.")
    assert a == tts.cache_key("en_US-amy-medium", "Rest 75 seconds.")
    assert a != tts.cache_key("vi_VN-vais1000-medium", "Rest 75 seconds.")
    assert a != tts.cache_key("en_US-amy-medium", "Rest 60 seconds.")


def test_empty_text_is_unavailable():
    with pytest.raises(tts.TtsUnavailableError):
        tts.synthesize("   ", "en")


def test_disabled_engine_is_unavailable(monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "tts_enabled", False)
    with pytest.raises(tts.TtsUnavailableError):
        tts.synthesize("Push up.", "en")
