#!/usr/bin/env sh
# Download the default Piper voice models used by the workout voice coach.
# Usage: sh scripts/fetch-piper-voices.sh [TARGET_DIR]   (default: media/tts/voices)
#
# The voices must match TTS_VOICE_EN / TTS_VOICE_VI in the backend settings.
set -eu

TARGET="${1:-media/tts/voices}"
BASE="https://huggingface.co/rhasspy/piper-voices/resolve/main"
mkdir -p "$TARGET"

fetch() {
  name="$(basename "$1")"
  echo "→ $name"
  curl -fsSL -o "$TARGET/$name" "$1"
}

# English: en_US-lessac-high · Vietnamese: vi_VN-vais1000-medium
fetch "$BASE/en/en_US/lessac/high/en_US-lessac-high.onnx"
fetch "$BASE/en/en_US/lessac/high/en_US-lessac-high.onnx.json"
fetch "$BASE/vi/vi_VN/vais1000/medium/vi_VN-vais1000-medium.onnx"
fetch "$BASE/vi/vi_VN/vais1000/medium/vi_VN-vais1000-medium.onnx.json"

echo "Done. Voice models in: $TARGET"
