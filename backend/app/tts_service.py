from __future__ import annotations

import hashlib
import json
import os
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from google.oauth2 import service_account


TRUTHY = {"1", "true", "yes", "on"}
DEFAULT_TTS_VOICE = "en-IN-Standard-A"
DEFAULT_TTS_CACHE_DIR = "runtime_logs/tts_cache"
TTS_CACHE_KEY_RE = re.compile(r"^[a-f0-9]{64}$")


@dataclass(frozen=True)
class TTSAudioAsset:
    cache_key: str
    cache_path: Path
    audio_url: str
    provider: str
    cached: bool
    content_type: str = "audio/mpeg"


def google_tts_enabled() -> bool:
    return os.getenv("GOOGLE_TTS_ENABLED", "0").strip().lower() in TRUTHY


def google_tts_voice_name() -> str:
    return os.getenv("GOOGLE_TTS_VOICE_NAME", DEFAULT_TTS_VOICE).strip() or DEFAULT_TTS_VOICE


def google_tts_pregenerate_enabled() -> bool:
    return os.getenv("GOOGLE_TTS_PREGENERATE", "0").strip().lower() in TRUTHY


def tts_cache_dir() -> Path:
    return Path(os.getenv("GOOGLE_TTS_CACHE_DIR", DEFAULT_TTS_CACHE_DIR))


def tts_cache_key(
    *,
    text: str,
    language_code: str = "en-IN",
    voice_name: str | None = None,
    speaking_rate: float = 0.92,
) -> str:
    selected_voice = voice_name or google_tts_voice_name()
    normalized_text = validate_tts_text(text)
    return hashlib.sha256(
        f"{language_code}|{selected_voice}|{speaking_rate}|{normalized_text}".encode("utf-8")
    ).hexdigest()


def tts_cache_path(cache_key: str) -> Path:
    validate_tts_cache_key(cache_key)
    return tts_cache_dir() / f"{cache_key}.mp3"


def tts_audio_url(cache_key: str, *, base_api_path: str = "/api/v1") -> str:
    validate_tts_cache_key(cache_key)
    return f"{base_api_path.rstrip('/')}/tts/audio/{cache_key}.mp3"


def validate_tts_cache_key(cache_key: str) -> str:
    normalized = cache_key.removesuffix(".mp3").strip().lower()
    if not TTS_CACHE_KEY_RE.match(normalized):
        raise ValueError("Invalid TTS cache key")
    return normalized


def validate_tts_text(text: str) -> str:
    normalized_text = text.strip()
    if not normalized_text:
        raise ValueError("TTS text is empty")
    if len(normalized_text) > 800:
        raise ValueError("TTS text is too long")
    return normalized_text


@lru_cache(maxsize=1)
def _tts_client():
    from google.cloud import texttospeech

    credentials_json = os.getenv("GOOGLE_TTS_CREDENTIALS_JSON", "").strip()
    if credentials_json:
        info = json.loads(credentials_json)
        credentials = service_account.Credentials.from_service_account_info(info)
        return texttospeech.TextToSpeechClient(credentials=credentials)
    return texttospeech.TextToSpeechClient()


def synthesize_google_tts_mp3(
    *,
    text: str,
    language_code: str = "en-IN",
    voice_name: str | None = None,
    speaking_rate: float = 0.92,
) -> bytes:
    asset = generate_google_tts_mp3_asset(
        text=text,
        language_code=language_code,
        voice_name=voice_name,
        speaking_rate=speaking_rate,
    )
    return asset.cache_path.read_bytes()


def generate_google_tts_mp3_asset(
    *,
    text: str,
    language_code: str = "en-IN",
    voice_name: str | None = None,
    speaking_rate: float = 0.92,
    base_api_path: str = "/api/v1",
) -> TTSAudioAsset:
    if not google_tts_enabled():
        raise RuntimeError("Google TTS is disabled")

    normalized_text = validate_tts_text(text)
    selected_voice = voice_name or google_tts_voice_name()
    cache_dir = tts_cache_dir()
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_key = tts_cache_key(
        text=normalized_text,
        language_code=language_code,
        voice_name=selected_voice,
        speaking_rate=speaking_rate,
    )
    cache_path = tts_cache_path(cache_key)
    if cache_path.exists():
        return TTSAudioAsset(
            cache_key=cache_key,
            cache_path=cache_path,
            audio_url=tts_audio_url(cache_key, base_api_path=base_api_path),
            provider="google_cloud_tts",
            cached=True,
        )

    from google.cloud import texttospeech

    response = _tts_client().synthesize_speech(
        request={
            "input": texttospeech.SynthesisInput(text=normalized_text),
            "voice": texttospeech.VoiceSelectionParams(
                language_code=language_code,
                name=selected_voice,
            ),
            "audio_config": texttospeech.AudioConfig(
                audio_encoding=texttospeech.AudioEncoding.MP3,
                speaking_rate=speaking_rate,
            ),
        }
    )
    audio_content = bytes(response.audio_content)
    cache_path.write_bytes(audio_content)
    return TTSAudioAsset(
        cache_key=cache_key,
        cache_path=cache_path,
        audio_url=tts_audio_url(cache_key, base_api_path=base_api_path),
        provider="google_cloud_tts",
        cached=False,
    )


def read_cached_tts_audio(cache_key: str) -> bytes | None:
    path = tts_cache_path(validate_tts_cache_key(cache_key))
    if not path.exists():
        return None
    return path.read_bytes()
