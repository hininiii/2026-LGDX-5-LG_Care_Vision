from __future__ import annotations

from copy import deepcopy

from fastapi.testclient import TestClient

from app.engines.decision_v2 import (
    DECISION_ENGINE_V2_INPUT_SCHEMA,
    DECISION_ENGINE_V2_OUTPUT_SCHEMA,
    DecisionEngineV2,
)
from app.main import app


def _post_chat(message: str, *, include_rag_evidence: bool = True, session_id: int | str | None = None) -> dict:
    payload = {
        "user_id": "U001",
        "device_id": "D001",
        "message": message,
        "include_rag_evidence": include_rag_evidence,
    }
    if session_id is not None:
        payload["session_id"] = str(session_id)
    response = TestClient(app).post("/api/v1/chat/messages", json=payload)
    assert response.status_code == 200
    return response.json()


def test_decision_engine_v2_schema_constants_include_required_fields() -> None:
    assert DECISION_ENGINE_V2_INPUT_SCHEMA["schema_version"] == "decision_engine_v2_input_v1"
    assert DECISION_ENGINE_V2_OUTPUT_SCHEMA["schema_version"] == "decision_engine_v2_output_v1"

    for field in [
        "customer_message",
        "collected_slots",
        "llm_assist",
        "rag_evidence",
        "smart_diagnosis",
        "usage_log",
        "environment",
        "official_asset_match",
    ]:
        assert field in DECISION_ENGINE_V2_INPUT_SCHEMA["fields"]

    for field in [
        "service_flow_type",
        "intent_type",
        "risk_level",
        "decision_action",
        "ar_guide_allowed",
        "blocked_reason",
        "allowed_actions",
        "forbidden_actions",
        "evidence_refs",
        "procedure_type",
    ]:
        assert field in DECISION_ENGINE_V2_OUTPUT_SCHEMA["fields"]


def test_chat_self_care_uses_decision_engine_v2_and_preserves_guide_flow() -> None:
    payload = _post_chat("Please help me clean the AC filter.")
    decision_v2 = payload["analysis"]["decision_v2"]

    assert decision_v2["source_engine"] == "decision_engine_v2_rule_safety_rag"
    assert decision_v2["fallback_engine"] == "v1_rule_engine"
    assert decision_v2["service_flow_type"] == "self_care"
    assert decision_v2["intent_type"] == "care"
    assert decision_v2["risk_level"] == "low"
    assert decision_v2["ar_guide_allowed"] is True
    assert decision_v2["procedure_type"] == "filter_cleaning"
    assert decision_v2["evidence_refs"]
    assert "start_user_accessible_care_guide" in decision_v2["allowed_actions"]
    assert payload["chatbot_engine"]["guide_options"]["service_flow_type"] == "self_care"


def test_chat_self_as_uses_decision_engine_v2_and_preserves_ar_plan_flow() -> None:
    payload = _post_chat("The AC has weak airflow from the outlet, risk signal none, dusty room.")
    decision_v2 = payload["analysis"]["decision_v2"]

    assert decision_v2["service_flow_type"] == "self_as"
    assert decision_v2["intent_type"] == "self_check"
    assert decision_v2["risk_level"] in {"low", "medium"}
    assert decision_v2["ar_guide_allowed"] is True
    assert decision_v2["procedure_type"] == "no_cooling_self_check"
    assert "start_external_self_check" in decision_v2["allowed_actions"]
    assert payload["chatbot_engine"]["guide_options"]["service_flow_type"] == "self_as"


def test_chat_expert_as_v2_blocks_ar_and_routes_to_service() -> None:
    payload = _post_chat("There is smoke and a burning smell from the AC.", include_rag_evidence=False)
    decision_v2 = payload["analysis"]["decision_v2"]

    assert decision_v2["service_flow_type"] == "expert_as"
    assert decision_v2["intent_type"] == "high_risk"
    assert decision_v2["risk_level"] == "high"
    assert decision_v2["decision_action"] == "route_to_service"
    assert decision_v2["ar_guide_allowed"] is False
    assert "ar_self_guidance" in decision_v2["forbidden_actions"]
    assert payload["ar_guide_plan_result"]["ar_guide_plan"] is None


def test_chat_multiturn_final_answer_runs_decision_engine_v2_after_slots_are_collected() -> None:
    first = _post_chat("냄새가 나요", include_rag_evidence=False)
    session_id = first["chatbot_engine"]["chat_session"]["session_id"]
    assert "decision_v2" not in first["analysis"]

    second = _post_chat(
        "곰팡이 냄새고 송풍구에서 나요. 장마라 습해요. 타는 냄새는 아니에요.",
        include_rag_evidence=True,
        session_id=session_id,
    )
    decision_v2 = second["analysis"]["decision_v2"]

    assert decision_v2["service_flow_type"] == "self_as"
    assert decision_v2["risk_level"] == "low"
    assert decision_v2["procedure_type"] == "odor_self_check"
    assert decision_v2["ar_guide_allowed"] is True
    assert second["chatbot_engine"]["conversation_state"]["state_status"] in {"ready", "completed"}


def test_decision_engine_v2_blocks_when_official_match_is_missing() -> None:
    engine = DecisionEngineV2()
    analysis = {
        "request_id": "REQ_TEST_OFFICIAL_MISSING",
        "input": {"message": "Help me repair the AC."},
        "intent": {"intent_type": "self_check", "service_flow_type": "self_as"},
        "procedure": {"procedure_type": "no_cooling_self_check"},
        "context": {"smart_diagnosis": {}, "usage_log": {}, "environment": {}},
        "official_asset_match": {
            "match_status": "not_verified",
            "match_type": "none",
            "official_assets": [],
            "forbidden_actions": [],
        },
        "decision_result": {
            "service_flow_type": "self_as",
            "risk_level": "low",
            "decision_action": "prepare_ar_guide_session",
            "generation_allowed": True,
            "ar_guide_allowed": True,
            "reasons": [],
        },
    }

    engine.apply_to_analysis(
        analysis,
        customer_message="Help me repair the AC.",
        collected_slots={},
        llm_assist={},
        rag_evidence=None,
    )
    decision_v2 = analysis["decision_v2"]

    assert decision_v2["decision_action"] == "official_match_review_needed"
    assert decision_v2["ar_guide_allowed"] is False
    assert decision_v2["generation_allowed"] is False
    assert decision_v2["blocked_reason"] == "Official asset match is not verified."
    assert analysis["decision_result"]["ar_guide_allowed"] is False


def test_decision_engine_v2_blocks_when_rag_evidence_is_missing() -> None:
    engine = DecisionEngineV2()
    base_analysis = {
        "request_id": "REQ_TEST_RAG_MISSING",
        "input": {"message": "The AC is not cooling enough."},
        "intent": {"intent_type": "self_check", "service_flow_type": "self_as"},
        "procedure": {"procedure_type": "no_cooling_self_check"},
        "context": {"smart_diagnosis": {}, "usage_log": {}, "environment": {}},
        "official_asset_match": {
            "match_status": "verified",
            "match_type": "exact_model",
            "official_assets": [{"asset_id": "ASSET_TEST", "title": "Official Manual"}],
            "forbidden_actions": [],
        },
        "decision_result": {
            "service_flow_type": "self_as",
            "risk_level": "low",
            "decision_action": "prepare_ar_guide_session",
            "generation_allowed": True,
            "ar_guide_allowed": True,
            "reasons": [],
        },
    }
    analysis = deepcopy(base_analysis)

    engine.apply_to_analysis(
        analysis,
        customer_message="The AC is not cooling enough.",
        collected_slots={},
        llm_assist={},
        rag_evidence={"result_count": 0, "results": []},
    )
    decision_v2 = analysis["decision_v2"]

    assert decision_v2["decision_action"] == "official_evidence_required"
    assert decision_v2["ar_guide_allowed"] is False
    assert decision_v2["blocked_reason"] == "Official RAG evidence is required before AR guidance."


def test_chat_power_troubleshooting_v2_keeps_external_safe_check_only() -> None:
    payload = _post_chat("The AC power suddenly turns off.")
    decision_v2 = payload["analysis"]["decision_v2"]
    decision = payload["analysis"]["decision_result"]

    assert decision_v2["service_flow_type"] == "self_as"
    assert decision_v2["risk_level"] == "medium"
    assert decision_v2["decision_action"] == "prepare_limited_ar_safe_check"
    assert decision_v2["ar_guide_allowed"] is True
    assert decision_v2["ar_scope"] == "external_safe_check_only"
    assert "touch_pcb" in decision_v2["forbidden_actions"]
    assert "single_breaker_reset_if_safe" in decision_v2["allowed_actions"]
    assert decision["ar_scope"] == "external_safe_check_only"
    assert payload["ar_guide_plan_result"]["ar_guide_plan"]["ar_scope"] == "external_safe_check_only"


def test_chat_remote_operation_v2_is_self_care_manual_only() -> None:
    payload = _post_chat("How do I use the AC remote timer?")
    decision_v2 = payload["analysis"]["decision_v2"]
    decision = payload["analysis"]["decision_result"]

    assert decision_v2["service_flow_type"] == "self_care"
    assert decision_v2["intent_type"] == "usage_help"
    assert decision_v2["risk_level"] == "low"
    assert decision_v2["procedure_type"] == "remote_operation"
    assert decision_v2["decision_action"] == "manual_or_service_guidance_only"
    assert decision_v2["ar_guide_allowed"] is False
    assert decision_v2["generation_allowed"] is True
    assert "show_official_youtube" in decision_v2["allowed_actions"]
    assert decision["service_flow_type"] == "self_care"
    assert decision["ar_guide_allowed"] is False
    assert payload["ar_guide_plan_result"]["ar_guide_plan"] is None


def test_chat_fan_speed_mode_v2_is_self_care_manual_only() -> None:
    payload = _post_chat("How do I change fan speed mode?")
    decision_v2 = payload["analysis"]["decision_v2"]

    assert decision_v2["service_flow_type"] == "self_care"
    assert decision_v2["intent_type"] == "usage_help"
    assert decision_v2["risk_level"] == "low"
    assert decision_v2["procedure_type"] == "remote_operation"
    assert decision_v2["ar_guide_allowed"] is False
