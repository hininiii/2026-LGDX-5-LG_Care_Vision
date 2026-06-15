from __future__ import annotations

from fastapi.testclient import TestClient

from app.llm_service import LLM_OUTPUT_SCHEMA, LLM_PROMPT_SCHEMA, create_llm_service
from app.main import app


def test_llm_service_mock_returns_prompt_output_contract_and_non_authoritative_slots() -> None:
    service = create_llm_service("mock")

    result = service.assist_chat_turn(
        {
            "payload": {"message": "The AC has a bad smell.", "language_code": "en"},
            "turn_context": {
                "original_message": "The AC has a bad smell.",
                "collected_slots": {"product_family": "air_conditioner"},
            },
            "analysis": {
                "decision_result": {"service_flow_type": "self_as", "risk_level": "low"},
                "procedure": {"procedure_type": "odor_self_check"},
            },
            "guide_options": None,
            "conversation_state": {"state_status": "completed"},
        }
    )

    assert result["provider"] == "mock_rule_adapter"
    assert result["prompt_schema_version"] == LLM_PROMPT_SCHEMA["schema_version"]
    assert result["output_schema_version"] == LLM_OUTPUT_SCHEMA["schema_version"]
    assert result["slot_candidates"]["symptom_type"]["value"] == "odor"
    assert result["decision_authority"]["llm_can_override_safety"] is False
    assert result["decision_authority"]["llm_can_verify_official_evidence"] is False


def test_chat_messages_response_includes_llm_assist_without_changing_decision_authority() -> None:
    response = TestClient(app).post(
        "/api/v1/chat/messages",
        json={
            "user_id": "U001",
            "device_id": "D001",
            "message": "There is smoke and a burning smell from the AC.",
            "include_rag_evidence": False,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    llm_assist = payload["chatbot_engine"]["llm_assist"]
    policy = payload["chatbot_engine"]["llm_policy"]

    assert payload["analysis"]["decision_result"]["service_flow_type"] == "expert_as"
    assert payload["analysis"]["decision_result"]["ar_guide_allowed"] is False
    assert llm_assist["provider"] == "mock_rule_adapter"
    assert llm_assist["decision_authority"]["llm_can_override_safety"] is False
    assert policy["final_ar_permission_by_llm"] is False
    assert policy["official_evidence_verification_by_llm"] is False
    assert payload["chatbot_engine"]["ai_message"]["message_type"] == "safety_card"


def test_chat_messages_uses_mock_llm_for_multiturn_clarification_copy() -> None:
    response = TestClient(app).post(
        "/api/v1/chat/messages",
        json={
            "user_id": "U001",
            "device_id": "D001",
            "message": "냄새가 나요",
            "language_code": "ko",
            "include_rag_evidence": False,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    state = payload["chatbot_engine"]["conversation_state"]
    llm_assist = payload["chatbot_engine"]["llm_assist"]
    ai_message = payload["chatbot_engine"]["ai_message"]

    assert state["state_status"] == "collecting"
    assert llm_assist["provider"] == "mock_rule_adapter"
    assert llm_assist["response_text"] == state["next_question"]
    assert ai_message["message_content"] == state["next_question"]
