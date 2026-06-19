from __future__ import annotations

import hashlib
import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request
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
    storage_provider: str = "render_runtime"
    object_path: str | None = None


def google_tts_enabled() -> bool:
    return os.getenv("GOOGLE_TTS_ENABLED", "0").strip().lower() in TRUTHY


def google_tts_voice_name() -> str:
    return os.getenv("GOOGLE_TTS_VOICE_NAME", DEFAULT_TTS_VOICE).strip() or DEFAULT_TTS_VOICE


def google_tts_pregenerate_enabled() -> bool:
    return os.getenv("GOOGLE_TTS_PREGENERATE", "0").strip().lower() in TRUTHY


def supabase_tts_storage_enabled() -> bool:
    return os.getenv("SUPABASE_TTS_STORAGE_ENABLED", "0").strip().lower() in TRUTHY


def supabase_tts_bucket() -> str:
    return os.getenv("SUPABASE_TTS_BUCKET", "tts-audio").strip() or "tts-audio"


def supabase_url() -> str:
    return os.getenv("SUPABASE_URL", "").strip().rstrip("/")


def supabase_service_role_key() -> str:
    return os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()


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


def tts_storage_object_path(
    cache_key: str,
    *,
    language_code: str = "en-IN",
    voice_name: str | None = None,
) -> str:
    normalized_key = validate_tts_cache_key(cache_key)
    selected_voice = voice_name or google_tts_voice_name()
    safe_language = _safe_storage_path_segment(language_code)
    safe_voice = _safe_storage_path_segment(selected_voice)
    return f"tts/{safe_language}/{safe_voice}/{normalized_key}.mp3"


def tts_storage_public_url(object_path: str) -> str:
    base_url = supabase_url()
    bucket = supabase_tts_bucket()
    if not base_url:
        raise RuntimeError("SUPABASE_URL is not configured")
    quoted_path = urllib.parse.quote(object_path.lstrip("/"), safe="/")
    quoted_bucket = urllib.parse.quote(bucket, safe="")
    return f"{base_url}/storage/v1/object/public/{quoted_bucket}/{quoted_path}"


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


def _safe_storage_path_segment(value: str) -> str:
    normalized = re.sub(r"[^A-Za-z0-9._-]+", "-", value.strip())
    return normalized.strip("-") or "default"


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
        use_storage=False,
    )
    return asset.cache_path.read_bytes()


def generate_google_tts_mp3_asset(
    *,
    text: str,
    language_code: str = "en-IN",
    voice_name: str | None = None,
    speaking_rate: float = 0.92,
    base_api_path: str = "/api/v1",
    use_storage: bool = True,
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
    if use_storage and supabase_tts_storage_enabled():
        storage_asset = _try_get_existing_supabase_tts_asset(
            cache_key=cache_key, cache_path=cache_path, language_code=language_code, voice_name=selected_voice
        )
        if storage_asset:
            return storage_asset

    if cache_path.exists():
        if use_storage and supabase_tts_storage_enabled():
            uploaded_asset = _try_upload_cached_tts_to_supabase(
                cache_key=cache_key,
                cache_path=cache_path,
                language_code=language_code,
                voice_name=selected_voice,
                cached=True,
            )
            if uploaded_asset:
                return uploaded_asset
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
    if use_storage and supabase_tts_storage_enabled():
        uploaded_asset = _try_upload_cached_tts_to_supabase(
            cache_key=cache_key,
            cache_path=cache_path,
            language_code=language_code,
            voice_name=selected_voice,
            cached=False,
        )
        if uploaded_asset:
            return uploaded_asset

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


def _try_get_existing_supabase_tts_asset(
    *,
    cache_key: str,
    cache_path: Path,
    language_code: str,
    voice_name: str,
) -> TTSAudioAsset | None:
    try:
        return _get_existing_supabase_tts_asset(
            cache_key=cache_key, cache_path=cache_path, language_code=language_code, voice_name=voice_name
        )
    except RuntimeError:
        return None


def _try_upload_cached_tts_to_supabase(
    *,
    cache_key: str,
    cache_path: Path,
    language_code: str,
    voice_name: str,
    cached: bool,
) -> TTSAudioAsset | None:
    try:
        return _upload_cached_tts_to_supabase(
            cache_key=cache_key,
            cache_path=cache_path,
            language_code=language_code,
            voice_name=voice_name,
            cached=cached,
        )
    except RuntimeError:
        return None


def _get_existing_supabase_tts_asset(
    *,
    cache_key: str,
    cache_path: Path,
    language_code: str,
    voice_name: str,
) -> TTSAudioAsset | None:
    object_path = tts_storage_object_path(cache_key, language_code=language_code, voice_name=voice_name)
    public_url = tts_storage_public_url(object_path)
    request = urllib.request.Request(public_url, method="HEAD")
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            if 200 <= response.status < 300:
                return TTSAudioAsset(
                    cache_key=cache_key,
                    cache_path=cache_path,
                    audio_url=public_url,
                    provider="google_cloud_tts",
                    cached=True,
                    storage_provider="supabase_storage",
                    object_path=object_path,
                )
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return None
        raise RuntimeError(f"Supabase Storage lookup failed: HTTP {exc.code}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Supabase Storage lookup failed: {exc}") from exc
    return None


def _upload_cached_tts_to_supabase(
    *,
    cache_key: str,
    cache_path: Path,
    language_code: str,
    voice_name: str,
    cached: bool,
) -> TTSAudioAsset | None:
    if not cache_path.exists():
        return None
    object_path = tts_storage_object_path(cache_key, language_code=language_code, voice_name=voice_name)
    public_url = tts_storage_public_url(object_path)
    _upload_bytes_to_supabase_storage(object_path=object_path, audio=cache_path.read_bytes())
    return TTSAudioAsset(
        cache_key=cache_key,
        cache_path=cache_path,
        audio_url=public_url,
        provider="google_cloud_tts",
        cached=cached,
        storage_provider="supabase_storage",
        object_path=object_path,
    )


def _upload_bytes_to_supabase_storage(*, object_path: str, audio: bytes) -> None:
    base_url = supabase_url()
    service_key = supabase_service_role_key()
    bucket = supabase_tts_bucket()
    if not base_url:
        raise RuntimeError("SUPABASE_URL is not configured")
    if not service_key:
        raise RuntimeError("SUPABASE_SERVICE_ROLE_KEY is not configured")
    quoted_bucket = urllib.parse.quote(bucket, safe="")
    quoted_path = urllib.parse.quote(object_path.lstrip("/"), safe="/")
    upload_url = f"{base_url}/storage/v1/object/{quoted_bucket}/{quoted_path}"
    request = urllib.request.Request(
        upload_url,
        data=audio,
        method="POST",
        headers={
            "apikey": service_key,
            "Authorization": f"Bearer {service_key}",
            "Content-Type": "audio/mpeg",
            "Cache-Control": "31536000",
            "x-upsert": "false",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            if 200 <= response.status < 300:
                return
            raise RuntimeError(f"Supabase Storage upload failed: HTTP {response.status}")
    except urllib.error.HTTPError as exc:
        if exc.code == 400 and "already exists" in exc.read().decode("utf-8", errors="ignore").lower():
            return
        raise RuntimeError(f"Supabase Storage upload failed: HTTP {exc.code}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Supabase Storage upload failed: {exc}") from exc
