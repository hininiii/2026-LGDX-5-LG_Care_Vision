from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from threading import Lock
from typing import Any
from urllib import error, parse, request

from fastapi import HTTPException


BACKEND_DIR = Path(__file__).resolve().parents[1]
TTS_CACHE_DIR = BACKEND_DIR / "runtime_logs" / "tts_cache"
TTS_CACHE_INDEX_PATH = TTS_CACHE_DIR / "tts_audio_cache.json"
DEFAULT_TTS_BUCKET = "guide-audio"
_CACHE_INDEX_LOCK = Lock()
_urlopen = request.urlopen


def google_tts_enabled() -> bool:
    return os.getenv("GOOGLE_TTS_ENABLED", "0").strip().lower() in {"1", "true", "yes", "on"}


def google_tts_voice_name(language_code: str, requested_voice_name: str | None = None) -> str | None:
    if requested_voice_name:
        return requested_voice_name
    configured = os.getenv("GOOGLE_TTS_VOICE_NAME", "").strip()
    if configured:
        return configured
    if language_code == "en-IN":
        return "en-IN-Standard-A"
    return None


def supabase_tts_storage_enabled() -> bool:
    configured = os.getenv("CARESHOT_TTS_STORAGE_ENABLED", "").strip().lower()
    if configured in {"0", "false", "no", "off"}:
        return False
    if configured in {"1", "true", "yes", "on"}:
        return bool(supabase_storage_url() and supabase_storage_key())
    return bool(supabase_storage_url() and supabase_storage_key())


def supabase_storage_url() -> str:
    return (
        os.getenv("SUPABASE_URL", "")
        or os.getenv("CARESHOT_SUPABASE_URL", "")
        or os.getenv("SUPABASE_PROJECT_URL", "")
    ).strip().rstrip("/")


def supabase_storage_key() -> str:
    return (
        os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
        or os.getenv("CARESHOT_SUPABASE_SERVICE_ROLE_KEY", "")
        or os.getenv("SUPABASE_KEY", "")
    ).strip()


def supabase_tts_bucket() -> str:
    return os.getenv("CARESHOT_TTS_STORAGE_BUCKET", DEFAULT_TTS_BUCKET).strip() or DEFAULT_TTS_BUCKET


def supabase_tts_public_bucket() -> bool:
    return os.getenv("CARESHOT_TTS_STORAGE_PUBLIC", "1").strip().lower() in {"1", "true", "yes", "on"}


def supabase_tts_signed_url_expires_in() -> int:
    raw_value = os.getenv("CARESHOT_TTS_SIGNED_URL_EXPIRES_IN", "604800").strip()
    try:
        return max(60, min(int(raw_value), 60 * 60 * 24 * 30))
    except ValueError:
        return 604800


def _credentials_from_env() -> Any:
    credentials_json = os.getenv("GOOGLE_TTS_CREDENTIALS_JSON", "").strip()
    if not credentials_json:
        return None
    try:
        from google.oauth2 import service_account

        info = json.loads(credentials_json)
        return service_account.Credentials.from_service_account_info(
            info,
            scopes=["https://www.googleapis.com/auth/cloud-platform"],
        )
    except Exception as exc:  # pragma: no cover - exact auth exceptions vary by google-auth version
        raise HTTPException(status_code=500, detail="Invalid Google TTS credentials JSON") from exc


def _client():
    try:
        from google.cloud import texttospeech
    except Exception as exc:  # pragma: no cover - import failure is environment-dependent
        raise HTTPException(status_code=503, detail="Google TTS client library is not installed") from exc

    credentials = _credentials_from_env()
    if credentials is not None:
        return texttospeech.TextToSpeechClient(credentials=credentials), texttospeech
    return texttospeech.TextToSpeechClient(), texttospeech


def _clean_text(text: str) -> str:
    return " ".join((text or "").split())


def _cache_material(*, text: str, language_code: str, voice_name: str | None, speaking_rate: float) -> str:
    return json.dumps(
        {
            "text": text,
            "language_code": language_code,
            "voice_name": voice_name,
            "speaking_rate": round(speaking_rate, 3),
            "encoding": "MP3",
        },
        ensure_ascii=False,
        sort_keys=True,
    )


def tts_cache_key(*, text: str, language_code: str, voice_name: str | None, speaking_rate: float) -> str:
    clean_text = _clean_text(text)
    material = _cache_material(
        text=clean_text,
        language_code=language_code,
        voice_name=voice_name,
        speaking_rate=speaking_rate,
    )
    return hashlib.sha256(material.encode("utf-8")).hexdigest()[:32]


def _cache_path(*, text: str, language_code: str, voice_name: str | None, speaking_rate: float) -> Path:
    return TTS_CACHE_DIR / f"{tts_cache_key(text=text, language_code=language_code, voice_name=voice_name, speaking_rate=speaking_rate)}.mp3"


def _storage_object_path(*, cache_key: str, language_code: str) -> str:
    safe_language = re_sub_path_part(language_code or "en-IN")
    return f"tts/{safe_language}/{cache_key}.mp3"


def re_sub_path_part(value: str) -> str:
    safe = "".join(ch if ch.isalnum() or ch in {"-", "_"} else "-" for ch in value.strip())
    return safe or "default"


def _load_cache_index() -> dict[str, Any]:
    if not TTS_CACHE_INDEX_PATH.exists():
        return {}
    try:
        return json.loads(TTS_CACHE_INDEX_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def _save_cache_index(index: dict[str, Any]) -> None:
    TTS_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    TTS_CACHE_INDEX_PATH.write_text(
        json.dumps(index, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )


def _supabase_headers(content_type: str | None = None) -> dict[str, str]:
    key = supabase_storage_key()
    headers = {
        "apikey": key,
        "Authorization": f"Bearer {key}",
    }
    if content_type:
        headers["Content-Type"] = content_type
    return headers


def _supabase_upload_object(*, bucket: str, object_path: str, audio: bytes) -> None:
    base_url = supabase_storage_url()
    encoded_path = "/".join(parse.quote(part, safe="") for part in object_path.split("/"))
    endpoint = f"{base_url}/storage/v1/object/{parse.quote(bucket, safe='')}/{encoded_path}"
    req = request.Request(
        endpoint,
        data=audio,
        method="POST",
        headers={
            **_supabase_headers("audio/mpeg"),
            "Cache-Control": "31536000",
            "x-upsert": "true",
        },
    )
    with _urlopen(req, timeout=20) as response:
        if response.status not in {200, 201}:
            raise HTTPException(status_code=502, detail="Supabase Storage upload failed")


def _supabase_public_url(*, bucket: str, object_path: str) -> str:
    base_url = supabase_storage_url()
    encoded_path = "/".join(parse.quote(part, safe="") for part in object_path.split("/"))
    return f"{base_url}/storage/v1/object/public/{parse.quote(bucket, safe='')}/{encoded_path}"


def _supabase_signed_url(*, bucket: str, object_path: str) -> str:
    base_url = supabase_storage_url()
    encoded_path = "/".join(parse.quote(part, safe="") for part in object_path.split("/"))
    endpoint = f"{base_url}/storage/v1/object/sign/{parse.quote(bucket, safe='')}/{encoded_path}"
    body = json.dumps({"expiresIn": supabase_tts_signed_url_expires_in()}).encode("utf-8")
    req = request.Request(
        endpoint,
        data=body,
        method="POST",
        headers=_supabase_headers("application/json"),
    )
    with _urlopen(req, timeout=20) as response:
        payload = json.loads(response.read().decode("utf-8"))
    signed_url = payload.get("signedURL") or payload.get("signedUrl") or payload.get("signed_url")
    if not signed_url:
        raise HTTPException(status_code=502, detail="Supabase Storage signed URL was empty")
    if signed_url.startswith("http"):
        return signed_url
    return f"{base_url}{signed_url}"


def _audio_url_for_object(*, bucket: str, object_path: str) -> str:
    if supabase_tts_public_bucket():
        return _supabase_public_url(bucket=bucket, object_path=object_path)
    return _supabase_signed_url(bucket=bucket, object_path=object_path)


def get_or_create_tts_audio_url(
    *,
    text: str,
    language_code: str = "en-IN",
    voice_name: str | None = None,
    speaking_rate: float = 0.92,
) -> str | None:
    clean_text = _clean_text(text)
    if not clean_text or not google_tts_enabled() or not supabase_tts_storage_enabled():
        return None

    resolved_voice_name = google_tts_voice_name(language_code, voice_name)
    cache_key = tts_cache_key(
        text=clean_text,
        language_code=language_code,
        voice_name=resolved_voice_name,
        speaking_rate=speaking_rate,
    )
    bucket = supabase_tts_bucket()
    object_path = _storage_object_path(cache_key=cache_key, language_code=language_code)

    with _CACHE_INDEX_LOCK:
        index = _load_cache_index()
        cached = index.get(cache_key)
        if cached and cached.get("bucket") == bucket and cached.get("object_path"):
            return _audio_url_for_object(bucket=bucket, object_path=str(cached["object_path"]))

    try:
        audio = synthesize_google_tts_mp3(
            text=clean_text,
            language_code=language_code,
            voice_name=resolved_voice_name,
            speaking_rate=speaking_rate,
        )
        _supabase_upload_object(bucket=bucket, object_path=object_path, audio=audio)
        audio_url = _audio_url_for_object(bucket=bucket, object_path=object_path)
    except (HTTPException, OSError, error.URLError, TimeoutError):
        if os.getenv("CARESHOT_TTS_STORAGE_STRICT", "0").strip().lower() in {"1", "true", "yes", "on"}:
            raise
        return None

    with _CACHE_INDEX_LOCK:
        index = _load_cache_index()
        index[cache_key] = {
            "bucket": bucket,
            "object_path": object_path,
            "audio_url": audio_url if supabase_tts_public_bucket() else None,
            "language_code": language_code,
            "voice_name": resolved_voice_name,
            "speaking_rate": round(speaking_rate, 3),
        }
        _save_cache_index(index)
    return audio_url


def build_tts_step_fields(*, text: str | None, ar_allowed: bool, language_code: str) -> dict[str, Any]:
    tts_text = (text or "").strip()
    enabled = bool(ar_allowed and tts_text)
    provider = "google_cloud_tts" if enabled and google_tts_enabled() else "web_speech"
    fields: dict[str, Any] = {
        "tts_enabled": enabled,
        "tts_text": tts_text if enabled else "",
        "tts_language_code": language_code,
        "tts_provider": provider,
    }
    if enabled and provider == "google_cloud_tts":
        audio_url = get_or_create_tts_audio_url(text=tts_text, language_code=language_code)
        if audio_url:
            fields["audio_url"] = audio_url
            fields["tts_cache_key"] = tts_cache_key(
                text=tts_text,
                language_code=language_code,
                voice_name=google_tts_voice_name(language_code),
                speaking_rate=0.92,
            )
    return fields


def synthesize_google_tts_mp3(
    *,
    text: str,
    language_code: str = "en-IN",
    voice_name: str | None = None,
    speaking_rate: float = 0.92,
) -> bytes:
    clean_text = " ".join((text or "").split())
    if not clean_text:
        raise HTTPException(status_code=422, detail="TTS text is empty")
    if len(clean_text) > 800:
        raise HTTPException(status_code=422, detail="TTS text is too long")
    if not google_tts_enabled():
        raise HTTPException(status_code=503, detail="Google TTS is disabled")

    resolved_voice_name = google_tts_voice_name(language_code, voice_name)
    TTS_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_path = _cache_path(
        text=clean_text,
        language_code=language_code,
        voice_name=resolved_voice_name,
        speaking_rate=speaking_rate,
    )
    if cache_path.exists() and cache_path.stat().st_size > 0:
        return cache_path.read_bytes()

    client, texttospeech = _client()
    voice_kwargs: dict[str, Any] = {"language_code": language_code}
    if resolved_voice_name:
        voice_kwargs["name"] = resolved_voice_name

    response = client.synthesize_speech(
        input=texttospeech.SynthesisInput(text=clean_text),
        voice=texttospeech.VoiceSelectionParams(**voice_kwargs),
        audio_config=texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.MP3,
            speaking_rate=speaking_rate,
        ),
    )
    audio_content = bytes(response.audio_content)
    if not audio_content:
        raise HTTPException(status_code=502, detail="Google TTS returned empty audio")
    cache_path.write_bytes(audio_content)
    return audio_content
