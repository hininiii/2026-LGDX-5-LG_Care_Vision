from __future__ import annotations

import json

from fastapi.testclient import TestClient
import pytest

from app.main import app
from app.services import get_backend_service


def _state_slots(state: dict) -> tuple[list[str], dict]:
    return (
        json.loads(state.get("missing_slots") or "[]"),
        json.loads(state.get("collected_slots_json") or "{}"),
    )


def _post_chat(message: str, session_id: int | None = None) -> dict:
    payload = {
        "user_id": "U001",
        "device_id": "D001",
        "message": message,
        "include_rag_evidence": False,
    }
    if session_id is not None:
        payload["session_id"] = str(session_id)
    response = TestClient(app).post("/api/v1/chat/messages", json=payload)
    assert response.status_code == 200
    return response.json()


def test_ambiguous_odor_question_collects_slots_then_finalizes_intent() -> None:
    service = get_backend_service()

    first = _post_chat("냄새가 나요")
    session_id = first["chatbot_engine"]["chat_session"]["session_id"]
    first_state = first["chatbot_engine"]["conversation_state"]
    missing, slots = _state_slots(first_state)

    assert first_state["state_status"] == "collecting"
    assert "risk_signal" in missing
    assert "symptom_location" in missing
    assert "environment_context" in missing
    assert slots["symptom_type"] == "odor"
    assert first["chatbot_engine"]["ai_message"]["message_type"] == "text"
    assert first["analysis"]["decision_result"]["decision_action"] == "ask_clarification"
    assert first["ar_guide_plan_result"]["ar_guide_plan"] is None

    second = _post_chat(
        "곰팡이 냄새고 송풍구에서 나요. 장마라 습해요. 타는 냄새는 아니에요.",
        session_id=session_id,
    )
    final_state = service.repo.get_conversation_state(session_id)
    missing, slots = _state_slots(final_state)

    assert missing == []
    assert final_state["state_status"] in {"completed", "ready"}
    assert slots["symptom_type"] == "odor"
    assert slots["risk_signal"] == "none"
    assert slots["symptom_location"] == "outlet"
    assert slots["environment_context"] in {"humid", "monsoon"}
    assert second["analysis"]["decision_result"]["service_flow_type"] == "self_as"
    assert second["analysis"]["procedure"]["procedure_type"] == "odor_self_check"


def test_ambiguous_water_leak_question_collects_slots_then_finalizes_intent() -> None:
    service = get_backend_service()

    first = _post_chat("물이 새요")
    session_id = first["chatbot_engine"]["chat_session"]["session_id"]
    first_state = first["chatbot_engine"]["conversation_state"]
    missing, slots = _state_slots(first_state)

    assert first_state["state_status"] == "collecting"
    assert slots["symptom_type"] == "water_leak"
    assert "risk_signal" in missing
    assert "symptom_location" in missing

    second = _post_chat(
        "실내기에서 물이 떨어져요. 연기나 감전은 없고 장마 중이에요.",
        session_id=session_id,
    )
    final_state = service.repo.get_conversation_state(session_id)
    missing, slots = _state_slots(final_state)

    assert missing == []
    assert slots["symptom_type"] == "water_leak"
    assert slots["risk_signal"] == "none"
    assert slots["symptom_location"] == "indoor_unit"
    assert second["analysis"]["decision_result"]["service_flow_type"] == "self_as"
    assert second["analysis"]["procedure"]["procedure_type"] == "water_leak_monsoon"


def test_ambiguous_weak_airflow_question_collects_slots_then_finalizes_intent() -> None:
    service = get_backend_service()

    first = _post_chat("바람이 약해요")
    session_id = first["chatbot_engine"]["chat_session"]["session_id"]
    first_state = first["chatbot_engine"]["conversation_state"]
    missing, slots = _state_slots(first_state)

    assert first_state["state_status"] == "collecting"
    assert slots["symptom_type"] == "weak_airflow"
    assert "risk_signal" in missing
    assert "symptom_location" in missing
    assert "environment_context" in missing
    assert first["analysis"]["procedure"]["procedure_type"] == "no_cooling_self_check"
    assert first["analysis"]["decision_result"]["service_flow_type"] == "self_as"

    second = _post_chat(
        "송풍구에서 약하고 먼지가 많아요. 타는 냄새나 연기는 없어요.",
        session_id=session_id,
    )
    final_state = service.repo.get_conversation_state(session_id)
    missing, slots = _state_slots(final_state)

    assert missing == []
    assert slots["symptom_type"] == "weak_airflow"
    assert slots["risk_signal"] == "none"
    assert slots["symptom_location"] == "outlet"
    assert slots["environment_context"] == "dusty"
    assert second["analysis"]["decision_result"]["service_flow_type"] == "self_as"
    assert second["analysis"]["procedure"]["procedure_type"] == "no_cooling_self_check"


def test_weak_airflow_detail_does_not_repeat_combined_clarification_question() -> None:
    service = get_backend_service()

    first = _post_chat("냉방/기능이 잘 작동하지 않아요")
    session_id = first["chatbot_engine"]["chat_session"]["session_id"]
    first_state = first["chatbot_engine"]["conversation_state"]
    first_missing, first_slots = _state_slots(first_state)

    assert first_slots["symptom_type"] == "weak_airflow"
    assert first["analysis"]["procedure"]["procedure_type"] == "no_cooling_self_check"
    assert "risk_signal" in first_missing
    assert "symptom_location" in first_missing

    second = _post_chat("바람이 약하고 안시원해요", session_id=session_id)
    current_state = service.repo.get_conversation_state(session_id)
    missing, slots = _state_slots(current_state)

    assert slots["symptom_type"] == "weak_airflow"
    assert slots["symptom_location"] == "outlet"
    assert slots["environment_context"] == "unknown"
    assert missing == ["risk_signal"]
    assert second["analysis"]["decision_result"]["missing_slots"] == ["risk_signal"]


def test_ambiguous_noise_question_collects_slots_then_finalizes_intent() -> None:
    service = get_backend_service()

    first = _post_chat("소리가 나요")
    session_id = first["chatbot_engine"]["chat_session"]["session_id"]
    first_state = first["chatbot_engine"]["conversation_state"]
    missing, slots = _state_slots(first_state)

    assert first_state["state_status"] == "collecting"
    assert slots["symptom_type"] == "noise"
    assert "risk_signal" in missing
    assert "symptom_location" in missing

    second = _post_chat(
        "실내기에서 진동 소리이고 연기나 전기 문제는 없어요.",
        session_id=session_id,
    )
    final_state = service.repo.get_conversation_state(session_id)
    missing, slots = _state_slots(final_state)

    assert missing == []
    assert slots["symptom_type"] == "noise"
    assert slots["risk_signal"] == "none"
    assert slots["symptom_location"] == "indoor_unit"
    assert second["analysis"]["decision_result"]["service_flow_type"] == "self_as"
    assert second["analysis"]["procedure"]["procedure_type"] == "noise_self_check"


@pytest.mark.parametrize("negative_reply", ["아뇨", "아냐", "아니오", "아니요", "아니야", "없어요"])
def test_short_korean_no_reply_fills_risk_signal_and_asks_next_noise_slot(negative_reply: str) -> None:
    service = get_backend_service()

    first = _post_chat("소음이나 진동이 심해요")
    session_id = first["chatbot_engine"]["chat_session"]["session_id"]

    second = _post_chat(negative_reply, session_id=session_id)
    current_state = service.repo.get_conversation_state(session_id)
    missing, slots = _state_slots(current_state)

    assert slots["symptom_type"] == "noise"
    assert slots["risk_signal"] == "none"
    assert "risk_signal" not in missing
    assert missing == ["symptom_location"]
    assert second["analysis"]["decision_result"]["decision_action"] == "ask_clarification"
    assert "symptom_location" in second["analysis"]["decision_result"]["missing_slots"]


def test_ambiguous_power_question_collects_slots_then_finalizes_intent() -> None:
    service = get_backend_service()

    first = _post_chat("전원이 꺼져요")
    session_id = first["chatbot_engine"]["chat_session"]["session_id"]
    first_state = first["chatbot_engine"]["conversation_state"]
    missing, slots = _state_slots(first_state)

    assert first_state["state_status"] == "collecting"
    assert slots["symptom_type"] == "power_issue"
    assert slots["recent_diagnosis"] == "none"
    assert "risk_signal" in missing
    assert "symptom_location" in missing

    second = _post_chat(
        "차단기나 플러그 쪽이고 타는 냄새나 연기는 없어요. ThinQ 진단은 low예요.",
        session_id=session_id,
    )
    final_state = service.repo.get_conversation_state(session_id)
    missing, slots = _state_slots(final_state)

    assert missing == []
    assert slots["symptom_type"] == "power_issue"
    assert slots["recent_diagnosis"] == "low"
    assert slots["risk_signal"] == "none"
    assert slots["symptom_location"] == "power_area"
    assert second["analysis"]["decision_result"]["service_flow_type"] == "self_as"
    assert second["analysis"]["procedure"]["procedure_type"] == "power_troubleshooting"
    assert second["analysis"]["decision_result"]["ar_scope"] == "external_safe_check_only"


@pytest.mark.parametrize("message", ["이상해요", "문제가 있어요", "고장난 것 같아요", "작동이 이상해요", "상태가 이상해요"])
def test_generic_low_info_initial_question_asks_symptom_before_default_filter_guide(message: str) -> None:
    first = _post_chat(message)
    state = first["chatbot_engine"]["conversation_state"]
    missing, slots = _state_slots(state)

    assert state["state_status"] == "collecting"
    assert missing == ["symptom_type"]
    assert "symptom_type" not in slots
    assert first["analysis"]["decision_result"]["decision_action"] == "ask_clarification"
    assert first["analysis"]["decision_result"]["missing_slots"] == ["symptom_type"]
    assert first["analysis"]["procedure"].get("procedure_type") != "filter_cleaning"
    assert first["chatbot_engine"]["guide_options"] is None
    assert "What issue are you experiencing" in first["chatbot_engine"]["ai_message"]["message_content"]


def test_generic_low_info_followup_can_resolve_to_cooling_self_as() -> None:
    first = _post_chat("이상해요")
    session_id = first["chatbot_engine"]["chat_session"]["session_id"]

    second = _post_chat("냉방이 안 돼요", session_id=session_id)
    state = second["chatbot_engine"]["conversation_state"]
    missing, slots = _state_slots(state)

    assert slots["symptom_type"] == "weak_airflow"
    assert "risk_signal" in missing
    assert second["analysis"]["decision_result"]["decision_action"] == "ask_clarification"
    assert second["analysis"]["decision_result"]["service_flow_type"] == "self_as"
    assert second["analysis"]["procedure"]["procedure_type"] == "no_cooling_self_check"
