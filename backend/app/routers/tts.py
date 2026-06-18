from __future__ import annotations

from fastapi import APIRouter, HTTPException, Response

from ..schemas import TTSGenerateResponse, TTSSynthesizeRequest
from ..tts_service import (
    generate_google_tts_mp3_asset,
    read_cached_tts_audio,
    synthesize_google_tts_mp3,
    validate_tts_cache_key,
)


router = APIRouter(prefix="/tts", tags=["tts"])


@router.post("/synthesize")
def synthesize_tts(request: TTSSynthesizeRequest) -> Response:
    try:
        audio = synthesize_google_tts_mp3(
            text=request.text,
            language_code=request.language_code,
            voice_name=request.voice_name,
            speaking_rate=request.speaking_rate,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Google TTS request failed: {exc}") from exc

    return Response(content=audio, media_type="audio/mpeg")


@router.post("/generate", response_model=TTSGenerateResponse)
def generate_tts(request: TTSSynthesizeRequest) -> dict:
    try:
        asset = generate_google_tts_mp3_asset(
            text=request.text,
            language_code=request.language_code,
            voice_name=request.voice_name,
            speaking_rate=request.speaking_rate,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Google TTS request failed: {exc}") from exc

    return {
        "audio_url": asset.audio_url,
        "cache_key": asset.cache_key,
        "provider": asset.provider,
        "cached": asset.cached,
        "content_type": asset.content_type,
    }


@router.get("/audio/{cache_key}.mp3")
def get_tts_audio(cache_key: str) -> Response:
    try:
        normalized_key = validate_tts_cache_key(cache_key)
        audio = read_cached_tts_audio(normalized_key)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if audio is None:
        raise HTTPException(status_code=404, detail="TTS audio not found")
    return Response(content=audio, media_type="audio/mpeg")
