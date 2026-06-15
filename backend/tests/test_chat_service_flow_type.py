from __future__ import annotations

from fastapi.testclient import TestClient

from app.path_setup import configure_import_paths


configure_import_paths()

from ai_decision_engine import CareShotARDecisionEngine
from app.dependencies import get_service
from app.main import app
from app.services import CareShotBackendService


class FakeCareShotRepository:
    def __init__(self) -> None:
        self.decision_logs: list[dict] = []
        self.service_route_logs: list[dict] = []

    def get_user_profile(self, user_id: str) -> dict:
        return {
            "user_id": user_id,
            "preferred_language": "en",
            "video_style": "step_by_step",
        }

    def get_device_context(self, device_id: str) -> dict:
        return {
            "device_id": device_id,
            "model_name": "AS-Q24ENXE",
            "product_type": "air_conditioner",
            "region": "Gujarat",
            "city": "Ahmedabad",
            "series": "wall_ac",
            "model_aliases": ["AS Q24 ENXE"],
        }

    def get_usage_log(self, device_id: str) -> dict:
        return {
            "device_id": device_id,
            "care_triggers": [{"procedure_type": "filter_cleaning"}],
        }

    def get_smart_diagnosis(self, device_id: str) -> dict:
        return {"device_id": device_id, "severity": "low", "detected_signals": []}

    def get_environment_context(self, region: str, city: str | None = None) -> dict:
        return {"region": region, "city": city, "humidity": 72}

    def get_product_model(self, model_name: str, product_type: str) -> dict:
        return {
            "model_name": model_name,
            "product_type": product_type,
            "structure_type": "wall_ac_type_a",
        }

    def find_official_assets(
        self,
        model_name: str,
        product_type: str,
        aliases: list[str] | None = None,
        series: str | None = None,
    ) -> dict:
        return {
            "match_status": "verified",
            "match_type": "exact_model",
            "official_assets": [{"asset_id": "ASSET_AC_FILTER_001"}],
            "forbidden_actions": [],
        }

    def find_reusable_care_video(self, **_kwargs) -> None:
        return None

    def create_decision_log(self, payload: dict) -> dict:
        self.decision_logs.append(payload)
        return payload

    def create_service_route_log(self, payload: dict) -> dict:
        self.service_route_logs.append(payload)
        return payload


class StubARSelector:
    def select_and_build(self, analysis: dict) -> dict:
        return {
            "request_id": analysis["request_id"],
            "status": "stubbed",
            "blocked_reason": None,
            "ar_guide_usage": "not_rendered_in_unit_test",
            "selected_template_id": None,
            "ar_guide_plan": None,
        }


def make_service(repo: FakeCareShotRepository) -> CareShotBackendService:
    service = CareShotBackendService.__new__(CareShotBackendService)
    service.repo = repo
    service.decision_engine = CareShotARDecisionEngine(repo)
    service.ar_selector = StubARSelector()
    return service


def test_decision_engine_maps_customer_messages_to_service_flow_type() -> None:
    repo = FakeCareShotRepository()
    engine = CareShotARDecisionEngine(repo)

    self_care = engine.analyze("U001", "D001", "Please help me clean the AC filter.")
    assert self_care["intent"]["service_flow_type"] == "self_care"
    assert self_care["decision_result"]["service_flow_type"] == "self_care"
    assert self_care["decision_result"]["ar_guide_allowed"] is True

    self_as = engine.analyze("U001", "D001", "The AC has weak airflow and smells bad.")
    assert self_as["intent"]["service_flow_type"] == "self_as"
    assert self_as["procedure"]["procedure_type"] == "odor_self_check"
    assert self_as["procedure"]["primary_procedure"] == "odor_self_check"
    assert self_as["procedure"]["secondary_procedures"] == ["no_cooling_self_check"]
    assert self_as["decision_result"]["service_flow_type"] == "self_as"
    assert self_as["decision_result"]["ar_guide_allowed"] is True

    no_cooling = engine.analyze("U001", "D001", "The AC is not cooling enough.")
    assert no_cooling["intent"]["service_flow_type"] == "self_as"
    assert no_cooling["procedure"]["procedure_type"] == "no_cooling_self_check"
    assert no_cooling["procedure"]["secondary_procedures"] == []

    water_leak = engine.analyze("U001", "D001", "Water is dripping from the air conditioner.")
    assert water_leak["intent"]["service_flow_type"] == "self_as"
    assert water_leak["procedure"]["procedure_type"] == "water_leak_monsoon"

    remote = engine.analyze("U001", "D001", "How do I use the AC remote timer?")
    assert remote["intent"]["intent_type"] == "usage_help"
    assert remote["intent"]["service_flow_type"] == "self_care"
    assert remote["procedure"]["procedure_type"] == "remote_operation"
    assert remote["decision_result"]["service_flow_type"] == "self_care"
    assert remote["decision_result"]["risk_level"] == "low"
    assert remote["decision_result"]["decision_action"] == "manual_or_service_guidance_only"
    assert remote["decision_result"]["ar_guide_allowed"] is False

    fan_speed = engine.analyze("U001", "D001", "How do I change fan speed mode?")
    assert fan_speed["intent"]["intent_type"] == "usage_help"
    assert fan_speed["intent"]["service_flow_type"] == "self_care"
    assert fan_speed["procedure"]["procedure_type"] == "remote_operation"
    assert fan_speed["decision_result"]["ar_guide_allowed"] is False

    power_issue = engine.analyze("U001", "D001", "The AC power suddenly turns off.")
    assert power_issue["intent"]["service_flow_type"] == "self_as"
    assert power_issue["procedure"]["procedure_type"] == "power_troubleshooting"
    assert power_issue["decision_result"]["service_flow_type"] == "self_as"
    assert power_issue["decision_result"]["decision_action"] == "prepare_limited_ar_safe_check"
    assert power_issue["decision_result"]["ar_guide_allowed"] is True
    assert power_issue["decision_result"]["ar_scope"] == "external_safe_check_only"
    assert power_issue["decision_result"]["reuse_decision"] == "limited_power_troubleshooting_ar"

    korean_power_issue = engine.analyze("U001", "D001", "에어컨 전원이 갑자기 꺼졌어요.")
    assert korean_power_issue["intent"]["service_flow_type"] == "self_as"
    assert korean_power_issue["procedure"]["procedure_type"] == "power_troubleshooting"
    assert korean_power_issue["decision_result"]["ar_guide_allowed"] is True
    assert korean_power_issue["decision_result"]["ar_scope"] == "external_safe_check_only"

    readable_korean_power_issue = engine.analyze("U001", "D001", "에어컨 전원이 갑자기 꺼져요.")
    assert readable_korean_power_issue["intent"]["service_flow_type"] == "self_as"
    assert readable_korean_power_issue["procedure"]["procedure_type"] == "power_troubleshooting"
    assert readable_korean_power_issue["decision_result"]["ar_scope"] == "external_safe_check_only"

    expert_as = engine.analyze("U001", "D001", "There is smoke and a burning smell from the AC.")
    assert expert_as["intent"]["service_flow_type"] == "expert_as"
    assert expert_as["procedure"]["secondary_procedures"] == []
    assert expert_as["decision_result"]["service_flow_type"] == "expert_as"
    assert expert_as["decision_result"]["decision_action"] == "route_to_service"
    assert expert_as["decision_result"]["ar_guide_allowed"] is False


def test_chat_messages_response_and_logs_include_service_flow_type() -> None:
    repo = FakeCareShotRepository()
    service = make_service(repo)
    app.dependency_overrides[get_service] = lambda: service

    try:
        care_response = TestClient(app).post(
            "/api/v1/chat/messages",
            json={
                "user_id": "U001",
                "device_id": "D001",
                "message": "Please help me clean the AC filter.",
                "include_rag_evidence": False,
            },
        )
        assert care_response.status_code == 200
        assert care_response.json()["analysis"]["decision_result"]["service_flow_type"] == "self_care"

        as_response = TestClient(app).post(
            "/api/v1/chat/messages",
            json={
                "user_id": "U001",
                "device_id": "D001",
                "message": "The AC has weak airflow and smells bad.",
                "include_rag_evidence": False,
            },
        )
        assert as_response.status_code == 200
        assert as_response.json()["analysis"]["decision_result"]["service_flow_type"] == "self_as"

        expert_response = TestClient(app).post(
            "/api/v1/chat/messages",
            json={
                "user_id": "U001",
                "device_id": "D001",
                "message": "There is smoke and a burning smell from the AC.",
                "include_rag_evidence": False,
            },
        )
        expert_payload = expert_response.json()
        assert expert_response.status_code == 200
        assert expert_payload["analysis"]["decision_result"]["service_flow_type"] == "expert_as"
        assert expert_payload["analysis"]["decision_result"]["ar_guide_allowed"] is False
        assert expert_payload["analysis"]["chatbot_response"]["service_route"]["enabled"] is True
        assert repo.decision_logs == []
        assert repo.service_route_logs[-1]["route_type"] == "service_center_or_agent"
    finally:
        app.dependency_overrides.clear()
