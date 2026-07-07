"""Optional Vietnamese neural TTS via F5-TTS (a flow-matching voice-cloning model).

Piper's Vietnamese voice is intelligible but robotic; F5-TTS sounds markedly more
human. It is heavier (needs ``torch`` + ``f5-tts``, the ``f5`` optional-dependency
group kept out of the runtime image) so it is strictly opt-in: the main ``tts``
service only reaches for it when ``tts_vi_engine == "f5"`` *and* everything below
imports/loads cleanly. Any failure raises :class:`F5Unavailable`, which the caller
treats as "fall back to Piper" — so turning the engine on can never break audio.

Everything is imported lazily and the model is cached in-process, mirroring the
Piper path. Cues are synthesized once (at session pre-warm) and cached on disk by
the ``tts`` service, so the slow first synthesis is paid at most once per phrase.
"""

import hashlib
from functools import lru_cache
from pathlib import Path
from typing import Any

from app.config import get_settings


class F5Unavailable(Exception):
    """F5 deps/model/reference are missing or synthesis failed — use Piper instead."""


def _f5_dir() -> Path:
    settings = get_settings()
    # tts_f5_dir may be absolute or relative to media_dir.
    p = Path(settings.tts_f5_dir)
    return p if p.is_absolute() else Path(settings.media_dir).parent / p


@lru_cache(maxsize=8)
def _ref_fingerprint(path: str, mtime_ns: int, size: int) -> str:
    """Short content hash of the reference clip (mtime/size in the key just avoid
    re-hashing an unchanged file). Lets a swapped ref.wav invalidate the cache."""
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()[:12]


def model_tag() -> str:
    """Identifier folded into the audio cache key so switching engine/model/voice
    (including replacing the reference clip) regenerates instead of serving stale
    cross-engine audio."""
    settings = get_settings()
    ref = _f5_dir() / settings.tts_f5_ref_audio
    fp = "noref"
    if ref.exists():
        st = ref.stat()
        fp = _ref_fingerprint(str(ref), st.st_mtime_ns, st.st_size)
    return f"f5:{settings.tts_f5_model}:{fp}"


@lru_cache(maxsize=1)
def _load_model() -> Any:
    try:
        from f5_tts.api import F5TTS
    except ImportError as exc:  # torch / f5-tts not installed (base install)
        raise F5Unavailable("f5-tts is not installed") from exc

    settings = get_settings()
    base = _f5_dir()
    ckpt = base / settings.tts_f5_model
    vocab = base / "vocab.txt"
    if not ckpt.exists() or not vocab.exists():
        raise F5Unavailable(f"F5 model/vocab not found under {base}")
    try:
        return F5TTS(
            model=settings.tts_f5_arch,
            ckpt_file=str(ckpt),
            vocab_file=str(vocab),
            device="cpu",
        )
    except Exception as exc:  # arch mismatch, corrupt ckpt, etc.
        raise F5Unavailable(f"could not load F5 model: {exc}") from exc


def _reference() -> tuple[str, str]:
    settings = get_settings()
    ref = _f5_dir() / settings.tts_f5_ref_audio
    if not ref.exists():
        raise F5Unavailable(f"F5 reference audio not found: {ref}")
    return str(ref), settings.tts_f5_ref_text


def synthesize_to(text: str, out: Path) -> None:
    """Synthesize ``text`` (Vietnamese) with F5 and write a WAV to ``out``.

    Raises :class:`F5Unavailable` on any missing dependency/model or synthesis
    error; the caller falls back to Piper.
    """
    model = _load_model()
    ref_audio, ref_text = _reference()
    settings = get_settings()
    try:
        import soundfile as sf

        wav, sample_rate, _ = model.infer(
            ref_file=ref_audio,
            ref_text=ref_text,
            gen_text=text,
            speed=settings.tts_f5_speed,
            remove_silence=True,
        )
        out.parent.mkdir(parents=True, exist_ok=True)
        # Explicit format: the caller writes to a ".wav.tmp" temp (published
        # atomically), whose ".tmp" extension soundfile can't map to a format.
        sf.write(str(out), wav, sample_rate, format="WAV", subtype="PCM_16")
    except F5Unavailable:
        raise
    except Exception as exc:  # any inference/IO failure → let caller use Piper
        raise F5Unavailable(f"F5 synthesis failed: {exc}") from exc
