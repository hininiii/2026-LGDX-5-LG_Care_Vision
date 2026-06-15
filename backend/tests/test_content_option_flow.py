from __future__ import annotations

import shutil

from fastapi.testclient import TestClient

from app.dependencies import get_service
from app.main import app
from app.repositories import CareShotRepository
from app.repositories.database import DEFAULT_SQLITE_DB_PATH
from app.services import CareShotBackendService


def make_test_client(tmp_path):
    test_db = tmp_path / "careshot_ar_mock.db"
    shutil.copy2(DEFAULT_SQLITE_DB_PATH, test_db)
    service = CareShotBackendService()
    service.repo = CareShotRepository(test_db)
    app.dependency_overrides[get_service] = lambda: service
    return TestClient(app), service


def test_legacy_alert_and_content_view_endpoints_are_removed_from_api_surface(tmp_path) -> None:
    client, service = make_test_client(tmp_path)
    try:
        openapi_paths = client.get("/openapi.json").json()["paths"]
        assert not any(path.startswith("/api/v1/care/alerts") for path in openapi_paths)
        assert not any(path.startswith("/api/v1/contents") for path in openapi_paths)

        alerts_response = client.get("/api/v1/care/alerts", params={"user_id": "U001", "device_id": "D001"})
        assert alerts_response.status_code == 404

        options_response = client.get("/api/v1/care/alerts/ALERT_AC_FILTER_001/options")
        assert options_response.status_code == 404

        content_response = client.post("/api/v1/contents/GUIDE_1/view/start", json={"user_id": "U001"})
        assert content_response.status_code == 404

        assert service.get_guide_options(user_id="U001", device_id="D001", procedure_type="filter_cleaning")
    finally:
        app.dependency_overrides.clear()


def test_guide_options_are_available_from_final_guide_table(tmp_path) -> None:
    client, _service = make_test_client(tmp_path)
    try:
        response = client.get(
            "/api/v1/guides/options",
            params={"user_id": "U001", "device_id": "D001", "procedure_type": "filter_cleaning"},
        )
        assert response.status_code == 200
        option_set = response.json()
        assert option_set["manual_guides"][0]["content_id"] == "GUIDE_1"
        assert option_set["manual_guides"][0]["video_url"].startswith("https://www.youtube.com/watch")
        assert option_set["youtube_recommendations"]
        assert all(item["procedure_type"] == "filter_cleaning" for item in option_set["youtube_recommendations"])
        assert all(item["risk_policy"] != "expert_as_only" for item in option_set["youtube_recommendations"])
        assert option_set["matching_policy"]["youtube_match"].startswith("RAG official_youtube evidence")
        assert option_set["ar_guides"]
        assert option_set["storage_policy"]["completion_saved_table"] == "SELF_MANAGEMENT_HISTORY"
    finally:
        app.dependency_overrides.clear()


def test_power_troubleshooting_options_do_not_recommend_filter_cleaning_videos(tmp_path) -> None:
    client, _service = make_test_client(tmp_path)
    try:
        response = client.get(
            "/api/v1/guides/options",
            params={
                "user_id": "U001",
                "device_id": "D001",
                "procedure_type": "power_troubleshooting",
                "service_flow_type": "self_as",
            },
        )
        assert response.status_code == 200
        option_set = response.json()
        assert option_set["procedure_type"] == "power_troubleshooting"
        assert option_set["manual_guides"]
        assert option_set["manual_guides"][0]["dynamic"] is True
        assert option_set["manual_guides"][0]["safety_scope"] == "external_safe_check_only"
        assert "Do not open the indoor unit cover" in option_set["manual_guides"][0]["guide_text"]
        assert option_set["ar_guides"]
        assert option_set["ar_guides"][0]["dynamic"] is True
        assert option_set["ar_guides"][0]["ar_scope"] == "external_safe_check_only"
        assert option_set["youtube_recommendations"]
        assert all(item["procedure_type"] == "power_troubleshooting" for item in option_set["youtube_recommendations"])
        assert all(item["procedure_type"] != "filter_cleaning" for item in option_set["youtube_recommendations"])
        assert all(item["risk_policy"] != "expert_as_only" for item in option_set["youtube_recommendations"])
    finally:
        app.dependency_overrides.clear()


def test_dynamic_manual_guides_are_created_for_supported_aircon_procedures(tmp_path) -> None:
    client, _service = make_test_client(tmp_path)
    cases = [
        ("no_cooling_self_check", "self_as"),
        ("odor_self_check", "self_as"),
        ("water_leak_monsoon", "self_as"),
        ("noise_self_check", "self_as"),
        ("remote_operation", "self_care"),
        ("auto_clean", "self_care"),
    ]
    try:
        for procedure_type, service_flow_type in cases:
            response = client.get(
                "/api/v1/guides/options",
                params={
                    "user_id": "U001",
                    "device_id": "D001",
                    "procedure_type": procedure_type,
                    "service_flow_type": service_flow_type,
                },
            )
            assert response.status_code == 200
            option_set = response.json()
            assert option_set["procedure_type"] == procedure_type
            assert option_set["manual_guides"]
            assert option_set["manual_guides"][0]["dynamic"] is True
            assert option_set["manual_guides"][0]["generation_source"] == "rag_chunk_dynamic_manual"
            assert option_set["manual_guides"][0]["content_id"] == f"DYNAMIC_GUIDE_AIRCON_{procedure_type.upper()}"
            assert all(
                item["procedure_type"] == procedure_type
                for item in option_set.get("youtube_recommendations") or []
            )
    finally:
        app.dependency_overrides.clear()
