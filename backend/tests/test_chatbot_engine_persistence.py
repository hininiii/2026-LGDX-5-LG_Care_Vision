from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app
from app.services import get_backend_service


def test_chatbot_engine_persists_chat_session_inquiry_analysis_messages_and_state() -> None:
    service = get_backend_service()

    response = TestClient(app).post(
        "/api/v1/chat/messages",
        json={
            "user_id": "U001",
            "device_id": "D001",
            "message": "Please help me clean the AC filter.",
            "include_rag_evidence": True,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    engine = payload["chatbot_engine"]
    session_id = engine["chat_session"]["session_id"]
    inquiry_id = engine["inquiry"]["inquiry_id"]
    ai_response_id = engine["ai_inquiry_analysis"]["ai_response_id"]

    assert payload["analysis"]["decision_result"]["service_flow_type"] == "self_care"
    assert engine["guide_options"]["service_flow_type"] == "self_care"
    assert engine["ai_message"]["message_type"] == "guide_card"

    repo = service.repo
    assert repo.get_chat_session(session_id)["session_status"] == "active"
    messages = repo.get_chat_messages(session_id)
    assert messages[-2]["sender_type"] == "user"
    assert messages[-1]["sender_type"] == "ai"
    assert messages[-1]["message_type"] == "guide_card"

    inquiry = repo.conversation.fetch_one(
        'SELECT * FROM "CHATBOT_INQUIRY" WHERE inquiry_id = ?',
        (inquiry_id,),
    )
    assert inquiry["inquiry_content"] == "Please help me clean the AC filter."

    ai_analysis = repo.conversation.fetch_one(
        'SELECT * FROM "AI_INQUIRY_ANALYSIS" WHERE ai_response_id = ?',
        (ai_response_id,),
    )
    assert ai_analysis["inquiry_id"] == inquiry_id
    assert ai_analysis["intent_type"] == "self_care"
    assert ai_analysis["risk_level"] == "low"
    assert ai_analysis["recommended_guide_id"] is not None

    state = repo.get_conversation_state(session_id)
    assert state["current_intent"] == "self_care"
    assert state["state_status"] == "ready"

    rag_log = repo.rag.fetch_one(
        'SELECT * FROM "RAG_SEARCH_LOG" WHERE inquiry_id = ? AND ai_response_id = ? ORDER BY rag_log_id DESC LIMIT 1',
        (inquiry_id, ai_response_id),
    )
    assert rag_log is not None
    assert rag_log["search_status"] == "success"


def test_chatbot_engine_blocks_expert_as_guide_options() -> None:
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
    engine = payload["chatbot_engine"]

    assert payload["analysis"]["decision_result"]["service_flow_type"] == "expert_as"
    assert payload["analysis"]["decision_result"]["ar_guide_allowed"] is False
    assert engine["guide_options"] is None
    assert engine["ai_message"]["message_type"] == "safety_card"
    assert engine["ai_inquiry_analysis"]["intent_type"] == "expert_as"
    assert engine["ai_inquiry_analysis"]["safety_reason"]


def test_chatbot_engine_returns_dynamic_manual_and_limited_ar_options_for_power_troubleshooting() -> None:
    response = TestClient(app).post(
        "/api/v1/chat/messages",
        json={
            "user_id": "U001",
            "device_id": "D001",
            "message": "The AC power suddenly turns off.",
            "include_rag_evidence": True,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    decision = payload["analysis"]["decision_result"]
    options = payload["chatbot_engine"]["guide_options"]

    assert decision["service_flow_type"] == "self_as"
    assert decision["ar_guide_allowed"] is True
    assert decision["ar_scope"] == "external_safe_check_only"
    assert payload["analysis"]["procedure"]["procedure_type"] == "power_troubleshooting"
    assert options["procedure_type"] == "power_troubleshooting"
    assert options["manual_guides"]
    assert options["manual_guides"][0]["dynamic"] is True
    assert "Do not open the indoor unit cover" in options["manual_guides"][0]["guide_text"]
    assert options["ar_guides"]
    assert options["ar_guides"][0]["ar_scope"] == "external_safe_check_only"
    assert options["youtube_recommendations"]
    assert all(item["procedure_type"] == "power_troubleshooting" for item in options["youtube_recommendations"])
    assert payload["ar_guide_plan_result"]["selected_template_id"] == "aircon_power_troubleshooting_safe_check_v1"
    assert payload["ar_guide_plan_result"]["ar_guide_plan"]["ar_scope"] == "external_safe_check_only"
