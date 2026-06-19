from __future__ import annotations

import shutil

from fastapi.testclient import TestClient

from app.dependencies import get_service
from app.main import app
from app.repositories import CareShotRepository
from app.repositories.database import DEFAULT_SQLITE_DB_PATH
from app.services import CareShotBackendService
from app.tts_service import tts_cache_key


def make_test_client(tmp_path):
    test_db = tmp_path / "careshot_ar_mock.db"
    shutil.copy2(DEFAULT_SQLITE_DB_PATH, test_db)
    service = CareShotBackendService()
    service.repo = CareShotRepository(test_db)
    service.rag_service.repo = service.repo
    app.dependency_overrides[get_service] = lambda: service
    return TestClient(app)


def test_ar_guide_steps_include_tts_metadata(tmp_path) -> None:
    client = make_test_client(tmp_path)
    try:
        response = client.post(
            "/api/v1/ar/plans",
            json={
                "user_id": "U001",
                "device_id": "D001",
                "message": "Please help me clean the AC filter.",
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    first_step = response.json()["ar_overlay_data"]["guide_steps"][0]
    assert first_step["tts_enabled"] is True
    assert first_step["tts_text"] == first_step["display_instruction"]
    assert first_step["tts_language_code"] == "en-IN"
    assert first_step["tts_provider"] in {"web_speech", "google_cloud_tts"}
    assert first_step["audio_url"] is None


def test_google_tts_provider_is_selected_when_enabled(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("GOOGLE_TTS_ENABLED", "1")
    client = make_test_client(tmp_path)
    try:
        response = client.post(
            "/api/v1/ar/plans",
            json={
                "user_id": "U001",
                "device_id": "D001",
                "message": "Please help me clean the AC filter.",
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    first_step = response.json()["ar_overlay_data"]["guide_steps"][0]
    assert first_step["tts_provider"] == "google_cloud_tts"
    assert first_step["audio_url"] is None


def test_tts_generate_returns_cached_audio_url_and_audio_file(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("GOOGLE_TTS_ENABLED", "1")
    monkeypatch.setenv("GOOGLE_TTS_CACHE_DIR", str(tmp_path / "tts_cache"))
    text = "Turn off the air conditioner before opening the front cover."
    key = tts_cache_key(text=text, language_code="en-IN", speaking_rate=0.92)
    cache_dir = tmp_path / "tts_cache"
    cache_dir.mkdir(parents=True)
    (cache_dir / f"{key}.mp3").write_bytes(b"fake-mp3")

    client = TestClient(app)
    generate_response = client.post(
        "/api/v1/tts/generate",
        json={"text": text, "language_code": "en-IN", "speaking_rate": 0.92},
    )

    assert generate_response.status_code == 200
    payload = generate_response.json()
    assert payload["audio_url"] == f"/api/v1/tts/audio/{key}.mp3"
    assert payload["cache_key"] == key
    assert payload["provider"] == "google_cloud_tts"
    assert payload["cached"] is True

    audio_response = client.get(payload["audio_url"])
    assert audio_response.status_code == 200
    assert audio_response.headers["content-type"] == "audio/mpeg"
    assert audio_response.content == b"fake-mp3"


def test_tts_generate_uploads_cached_audio_to_supabase_storage(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("GOOGLE_TTS_ENABLED", "1")
    monkeypatch.setenv("GOOGLE_TTS_CACHE_DIR", str(tmp_path / "tts_cache"))
    monkeypatch.setenv("SUPABASE_TTS_STORAGE_ENABLED", "1")
    monkeypatch.setenv("SUPABASE_URL", "https://example-ref.supabase.co")
    monkeypatch.setenv("SUPABASE_TTS_BUCKET", "tts-audio")
    text = "Turn off the air conditioner before opening the front cover."
    key = tts_cache_key(text=text, language_code="en-IN", speaking_rate=0.92)
    cache_dir = tmp_path / "tts_cache"
    cache_dir.mkdir(parents=True)
    (cache_dir / f"{key}.mp3").write_bytes(b"fake-mp3")
    uploads = []

    monkeypatch.setattr("app.tts_service._get_existing_supabase_tts_asset", lambda **_: None)
    monkeypatch.setattr(
        "app.tts_service._upload_bytes_to_supabase_storage",
        lambda **kwargs: uploads.append(kwargs),
    )

    response = TestClient(app).post(
        "/api/v1/tts/generate",
        json={"text": text, "language_code": "en-IN", "speaking_rate": 0.92},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["storage_provider"] == "supabase_storage"
    assert payload["audio_url"].startswith(
        "https://example-ref.supabase.co/storage/v1/object/public/tts-audio/tts/en-IN/en-IN-Standard-A/"
    )
    assert payload["audio_url"].endswith(f"/{key}.mp3")
    assert payload["object_path"] == f"tts/en-IN/en-IN-Standard-A/{key}.mp3"
    assert uploads == [{"object_path": payload["object_path"], "audio": b"fake-mp3"}]


def test_tts_generate_falls_back_to_runtime_cache_when_supabase_upload_fails(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("GOOGLE_TTS_ENABLED", "1")
    monkeypatch.setenv("GOOGLE_TTS_CACHE_DIR", str(tmp_path / "tts_cache"))
    monkeypatch.setenv("SUPABASE_TTS_STORAGE_ENABLED", "1")
    monkeypatch.setenv("SUPABASE_URL", "https://example-ref.supabase.co")
    text = "Turn off the air conditioner before opening the front cover."
    key = tts_cache_key(text=text, language_code="en-IN", speaking_rate=0.92)
    cache_dir = tmp_path / "tts_cache"
    cache_dir.mkdir(parents=True)
    (cache_dir / f"{key}.mp3").write_bytes(b"fake-mp3")

    monkeypatch.setattr("app.tts_service._get_existing_supabase_tts_asset", lambda **_: None)
    monkeypatch.setattr(
        "app.tts_service._upload_bytes_to_supabase_storage",
        lambda **_: (_ for _ in ()).throw(RuntimeError("upload failed")),
    )

    response = TestClient(app).post(
        "/api/v1/tts/generate",
        json={"text": text, "language_code": "en-IN", "speaking_rate": 0.92},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["storage_provider"] == "render_runtime"
    assert payload["audio_url"] == f"/api/v1/tts/audio/{key}.mp3"
    assert payload["object_path"] is None


def test_guide_steps_include_audio_url_when_pregenerate_enabled(tmp_path, monkeypatch) -> None:
    class FakeAsset:
        cache_key = "a" * 64
        audio_url = "/api/v1/tts/audio/" + ("a" * 64) + ".mp3"
        provider = "google_cloud_tts"

    monkeypatch.setenv("GOOGLE_TTS_ENABLED", "1")
    monkeypatch.setenv("GOOGLE_TTS_PREGENERATE", "1")
    monkeypatch.setattr("app.services.generate_google_tts_mp3_asset", lambda **_: FakeAsset())
    client = make_test_client(tmp_path)
    try:
        response = client.post(
            "/api/v1/ar/plans",
            json={
                "user_id": "U001",
                "device_id": "D001",
                "message": "Please help me clean the AC filter.",
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    first_step = response.json()["ar_overlay_data"]["guide_steps"][0]
    assert first_step["tts_provider"] == "google_cloud_tts"
    assert first_step["audio_url"] == FakeAsset.audio_url
    assert first_step["tts_cache_key"] == FakeAsset.cache_key


def test_guide_steps_keep_audio_url_null_when_pregenerate_disabled(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("GOOGLE_TTS_ENABLED", "1")
    monkeypatch.delenv("GOOGLE_TTS_PREGENERATE", raising=False)
    client = make_test_client(tmp_path)
    try:
        response = client.post(
            "/api/v1/ar/plans",
            json={
                "user_id": "U001",
                "device_id": "D001",
                "message": "Please help me clean the AC filter.",
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    first_step = response.json()["ar_overlay_data"]["guide_steps"][0]
    assert first_step["tts_provider"] == "google_cloud_tts"
    assert first_step["audio_url"] is None
    assert first_step["tts_cache_key"] is None


def test_google_tts_endpoint_is_disabled_by_default(monkeypatch) -> None:
    monkeypatch.delenv("GOOGLE_TTS_ENABLED", raising=False)
    client = TestClient(app)
    response = client.post(
        "/api/v1/tts/synthesize",
        json={
            "text": "Turn off the air conditioner before opening the front cover.",
            "language_code": "en-IN",
        },
    )

    assert response.status_code == 503
    assert response.json()["detail"] == "Google TTS is disabled"
