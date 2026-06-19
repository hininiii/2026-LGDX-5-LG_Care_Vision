from __future__ import annotations

import shutil
from fastapi.testclient import TestClient

from app.dependencies import get_service
from app.main import app
from app.repositories import CareShotRepository
from app.repositories.database import DEFAULT_SQLITE_DB_PATH
from app.services import CareShotBackendService
from app import tts_service


def make_test_client(tmp_path):
    test_db = tmp_path / "careshot_ar_mock.db"
    shutil.copy2(DEFAULT_SQLITE_DB_PATH, test_db)
    service = CareShotBackendService()
    service.repo = CareShotRepository(test_db)
    app.dependency_overrides[get_service] = lambda: service
    return TestClient(app)


def test_ar_guide_steps_include_web_speech_tts_fields(tmp_path) -> None:
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
    payload = response.json()
    steps = payload["ar_overlay_data"]["guide_steps"]
    assert steps
    first_step = steps[0]
    assert first_step["tts_enabled"] is True
    assert first_step["tts_text"] == first_step["display_instruction"]
    assert first_step["tts_language_code"] == "en-IN"
    assert first_step["tts_provider"] == "web_speech"


def test_blocked_ar_plan_disables_tts(tmp_path) -> None:
    client = make_test_client(tmp_path)
    try:
        response = client.post(
            "/api/v1/ar/plans",
            json={
                "user_id": "U001",
                "device_id": "D001",
                "message": "There is smoke and burning smell from the AC.",
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["ar_overlay_data"] is None
    plan_result = payload["ar_guide_plan_result"]
    assert plan_result["status"] == "ar_guide_plan_blocked"
    assert plan_result["ar_guide_plan"] is None
    assert plan_result["tts_enabled"] is False
    assert plan_result["tts_provider"] == "web_speech"


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
    assert first_step["tts_enabled"] is True
    assert first_step["tts_provider"] == "google_cloud_tts"
    assert "audio_url" not in first_step


def test_google_tts_audio_url_is_uploaded_and_cached_when_supabase_storage_is_enabled(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("GOOGLE_TTS_ENABLED", "1")
    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "service-role-secret")
    monkeypatch.setenv("CARESHOT_TTS_STORAGE_BUCKET", "guide-audio")
    monkeypatch.setenv("CARESHOT_TTS_STORAGE_PUBLIC", "1")
    monkeypatch.setattr(tts_service, "TTS_CACHE_DIR", tmp_path)
    monkeypatch.setattr(tts_service, "TTS_CACHE_INDEX_PATH", tmp_path / "tts_audio_cache.json")
    monkeypatch.setattr(tts_service, "synthesize_google_tts_mp3", lambda **_: b"mp3-bytes")

    upload_calls: list[str] = []

    class FakeResponse:
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self) -> bytes:
            return b"{}"

    def fake_urlopen(req, timeout=20):
        upload_calls.append(req.full_url)
        return FakeResponse()

    monkeypatch.setattr(tts_service, "_urlopen", fake_urlopen)

    first_url = tts_service.get_or_create_tts_audio_url(
        text="Turn off the air conditioner before opening the front cover.",
        language_code="en-IN",
    )
    second_url = tts_service.get_or_create_tts_audio_url(
        text="Turn off the air conditioner before opening the front cover.",
        language_code="en-IN",
    )

    assert first_url == second_url
    assert first_url is not None
    assert first_url.startswith("https://example.supabase.co/storage/v1/object/public/guide-audio/tts/en-IN/")
    assert first_url.endswith(".mp3")
    assert len(upload_calls) == 1
    assert (tmp_path / "tts_audio_cache.json").exists()


def test_guide_options_include_audio_url_when_tts_storage_is_enabled(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("GOOGLE_TTS_ENABLED", "1")
    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "service-role-secret")
    monkeypatch.setenv("CARESHOT_TTS_STORAGE_BUCKET", "guide-audio")
    monkeypatch.setenv("CARESHOT_TTS_STORAGE_PUBLIC", "1")
    monkeypatch.setattr(tts_service, "TTS_CACHE_DIR", tmp_path / "tts-cache")
    monkeypatch.setattr(tts_service, "TTS_CACHE_INDEX_PATH", tmp_path / "tts-cache" / "tts_audio_cache.json")
    monkeypatch.setattr(tts_service, "synthesize_google_tts_mp3", lambda **_: b"mp3-bytes")

    class FakeResponse:
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self) -> bytes:
            return b"{}"

    monkeypatch.setattr(tts_service, "_urlopen", lambda req, timeout=20: FakeResponse())
    client = make_test_client(tmp_path)
    try:
        response = client.get(
            "/api/v1/guides/options",
            params={
                "user_id": "U001",
                "device_id": "D001",
                "product_code": "AS-Q24ENXE",
                "procedure_type": "filter_cleaning",
                "service_flow_type": "self_care",
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    first_step = response.json()["display_steps"][0]
    assert first_step["tts_provider"] == "google_cloud_tts"
    assert first_step["audio_url"].startswith(
        "https://example.supabase.co/storage/v1/object/public/guide-audio/tts/en-IN/"
    )
    assert first_step["tts_cache_key"]


def test_google_tts_endpoint_is_disabled_by_default() -> None:
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
