from __future__ import annotations

import shutil
import sqlite3

from fastapi.testclient import TestClient

from app.dependencies import get_service
from app.main import app
from app.repositories import CareShotRepository
from app.repositories.database import DEFAULT_SQLITE_DB_PATH
from app.services import CareShotBackendService


def make_test_client(tmp_path):
    test_db = tmp_path / "careshot_ar_mock.db"
    shutil.copy2(DEFAULT_SQLITE_DB_PATH, test_db)
    with sqlite3.connect(test_db) as conn:
        conn.execute('DELETE FROM "SELF_MANAGEMENT_HISTORY"')
    service = CareShotBackendService()
    service.repo = CareShotRepository(test_db)
    app.dependency_overrides[get_service] = lambda: service
    return TestClient(app), service


def test_guide_completion_is_saved_as_self_management_history(tmp_path) -> None:
    client, _service = make_test_client(tmp_path)
    try:
        complete_response = client.post(
            "/api/v1/guides/GUIDE_1/complete",
            json={"user_id": "U001", "device_id": "D001", "service_flow_type": "self_care"},
        )
        assert complete_response.status_code == 200
        assert complete_response.json()["self_management_history"]["procedure_type"] == "filter_cleaning"

        history_response = client.get("/api/v1/devices/D001/care-history?user_id=U001")
        assert history_response.status_code == 200
        payload = history_response.json()
        assert payload["summary"]["self_care_count"] == 1
        assert payload["items"][0]["procedure_type"] == "filter_cleaning"
        assert payload["items"][0]["activity_channel"] == "official_content"
    finally:
        app.dependency_overrides.clear()


def test_completed_ar_session_is_saved_as_self_management_history(tmp_path) -> None:
    client, _service = make_test_client(tmp_path)
    try:
        create_response = client.post(
            "/api/v1/ar/sessions",
            json={
                "guide_id": "GUIDE_AC_FILTER_CARE_AR_V1",
                "user_id": "U001",
                "device_id": "D001",
                "guide_type": "preventive_care",
                "service_flow_type": "self_care",
                "procedure_type": "filter_cleaning",
                "structure_type": "wall_ac_type_a",
            },
        )
        assert create_response.status_code == 201
        session_id = create_response.json()["session_id"]
        plan_response = client.post(
            "/api/v1/ar/plans",
            json={
                "user_id": "U001",
                "device_id": "D001",
                "message": "Please help me clean the AC filter.",
            },
        )
        assert plan_response.status_code == 200
        assert plan_response.json()["ar_overlay_data"]
        completed_steps = [
            step["guide_step_id"]
            for step in plan_response.json()["ar_overlay_data"]["guide_steps"][:3]
        ]
        assert completed_steps
        assert isinstance(completed_steps[0], str)

        update_response = client.patch(
            f"/api/v1/ar/sessions/{session_id}",
            json={"completed_steps": completed_steps, "completed": True, "solved": True},
        )
        assert update_response.status_code == 200
        assert update_response.json()["completed_steps"] == completed_steps

        session_response = client.get(f"/api/v1/ar/sessions/{session_id}")
        assert session_response.status_code == 200
        step_logs = session_response.json()["step_logs"]
        assert [log["guide_step_id"] for log in step_logs] == completed_steps

        history_response = client.get("/api/v1/devices/D001/care-history?user_id=U001")
        assert history_response.status_code == 200
        payload = history_response.json()
        assert payload["summary"]["self_care_count"] == 1
        assert payload["items"][0]["procedure_type"] == "filter_cleaning"
    finally:
        app.dependency_overrides.clear()
