"""Voice-coach text-to-speech endpoint.

Returns a WAV for a cue phrase. Defined as a sync ``def`` so FastAPI runs the
CPU-bound Piper synthesis in its threadpool instead of blocking the event loop.
The frontend points an <audio> element straight at this URL and falls back to the
browser's speech synthesis if it 503s (TTS disabled / model missing).
"""

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse

from app.services import tts as tts_svc

router = APIRouter(prefix="/tts", tags=["tts"])


@router.get("")
def synthesize(
    text: str = Query(..., min_length=1, max_length=tts_svc.MAX_TEXT_CHARS),
    lang: str = Query("en"),
) -> FileResponse:
    try:
        path = tts_svc.synthesize(text, lang)
    except tts_svc.TtsUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return FileResponse(
        path,
        media_type="audio/wav",
        headers={"Cache-Control": "public, max-age=86400"},
    )
