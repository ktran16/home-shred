#!/usr/bin/env sh
# Download the Vietnamese F5-TTS model + vocab used by the optional high-quality
# voice coach, and bootstrap a reference clip (cloned voice source) from Piper.
#
# Usage: sh scripts/fetch-f5-voice.sh [TARGET_DIR]   (default: media/tts/f5)
#
# The target dir must match TTS_F5_DIR. After this, set TTS_VI_ENGINE=f5 and make
# sure the `f5` optional deps are installed (uv pip install -e '.[f5]').
# For the best result, replace ref.wav with a clean 5-10s human Vietnamese clip
# and set TTS_F5_REF_TEXT to its exact transcript.
set -eu

TARGET="${1:-media/tts/f5}"
BASE="https://huggingface.co/danhtran2mind/Vi-F5-TTS/resolve/main"
mkdir -p "$TARGET"

echo "→ model_last.pt (~large)"
curl -fsSL -o "$TARGET/model_last.pt" "$BASE/Vi_F5_TTS_ckpts/model_last.pt"
echo "→ vocab.txt"
curl -fsSL -o "$TARGET/vocab.txt" "$BASE/vocab.txt"

# Install the reference clip (voice F5 clones). Prefer the bundled human clip — a
# Southern-Vietnamese female voice from the VIVOS corpus (CC-BY-NC-SA-4.0; see
# assets/ATTRIBUTION.md and keep TTS_F5_REF_TEXT matching its transcript). Fall
# back to a Piper-synthesized clip only if the asset is absent.
ASSET_WAV="assets/vivos_ref_vi.wav"
if [ ! -f "$TARGET/ref.wav" ]; then
  if [ -f "$ASSET_WAV" ]; then
    echo "→ ref.wav (bundled VIVOS Southern female clip)"
    cp "$ASSET_WAV" "$TARGET/ref.wav"
  else
    echo "→ ref.wav (fallback: bootstrapped from Piper)"
    python - "$TARGET" <<'PY'
import sys, wave
from pathlib import Path
from piper import PiperVoice, SynthesisConfig

target = Path(sys.argv[1])
voices = Path("media/tts/voices")
ref_text = "Xin chào, đây là trợ lý giọng nói cho buổi tập của bạn."
v = PiperVoice.load(
    str(voices / "vi_VN-vais1000-medium.onnx"),
    config_path=str(voices / "vi_VN-vais1000-medium.onnx.json"),
)
with wave.open(str(target / "ref.wav"), "wb") as w:
    v.synthesize_wav(ref_text, w, syn_config=SynthesisConfig(length_scale=1.0))
print("   wrote", target / "ref.wav")
PY
  fi
fi

echo "Done. F5 voice assets in: $TARGET"
