from __future__ import annotations

from fastapi.testclient import TestClient

from app.dependencies import get_service
from app.main import app


class FrontendCompatRepo:
    def get_user_profile(self, user_id: str) -> dict:
        return {
            "user_id": user_id,
            "customer_name": "तनीषा",
            "phone_number": "+91-9876543210",
            "country": "India",
            "region": "Delhi",
            "city": "New Delhi",
        }

    def get_device_context(self, device_id: str) -> dict:
        return {
            "device_id": device_id,
            "display_name": "거실 에어컨",
            "model_name": "AS-Q24ENXE",
        }


class FrontendCompatService:
    def __init__(self) -> None:
        self.repo = FrontendCompatRepo()
        self.last_chat_payload: dict | None = None

    def process_chat_message(self, payload: dict) -> dict:
        self.last_chat_payload = payload
        return {
            "chat_session": {"session_id": "CHAT_TEST_001"},
            "analysis": {
                "decision_result": {
                    "intent_type": "self_care",
                    "service_flow_type": "self_care",
                    "risk_level": "low",
                    "decision_action": "show_content_options",
                }
            },
            "chatbot_engine": {
                "ai_message": {
                    "message_type": "guide_card",
                    "message_content": "Official Manual Guide and AR Guide options are ready for this request.",
                },
                "conversation_state": {
                    "session_id": "CHAT_TEST_001",
                    "missing_slots": [],
                },
                "guide_options": {"manual_guides": [], "ar_guides": []},
            },
        }


def test_frontend_user_and_devices_contracts() -> None:
    service = FrontendCompatService()
    app.dependency_overrides[get_service] = lambda: service
    client = TestClient(app)

    try:
        user_response = client.get("/api/users/me")
        assert user_response.status_code == 200
        assert user_response.json() == {
            "user_email": "U001",
            "email": "U001",
            "name": "तनीषा",
            "phone": "+91-9876543210",
            "address": "India Delhi New Delhi",
            "region_id": "",
            "region": "Delhi",
            "city": "New Delhi",
        }

        devices_response = client.get("/api/devices")
        assert devices_response.status_code == 200
        assert devices_response.json() == [
            {"id": "D001", "name": "거실 에어컨", "model": "AS-Q24ENXE"}
        ]
    finally:
        app.dependency_overrides.clear()


def test_frontend_ai_chat_adapts_chatbot_engine_response() -> None:
    service = FrontendCompatService()
    app.dependency_overrides[get_service] = lambda: service
    client = TestClient(app)

    try:
        response = client.post(
            "/api/ai/chat",
            json={
                "message": "필터 청소 방법 알려줘",
                "context": {"deviceId": "D001"},
            },
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["message"].startswith("공식 근거에 맞는")
        assert payload["message_type"] == "guide_card"
        assert payload["session_id"] == "CHAT_TEST_001"
        assert payload["service_flow_type"] == "self_care"
        assert payload["needs_clarification"] is False
        assert service.last_chat_payload == {
            "user_id": "U001",
            "device_id": "D001",
            "session_id": None,
            "message": "필터 청소 방법 알려줘",
            "include_rag_evidence": True,
        }
    finally:
        app.dependency_overrides.clear()


def test_frontend_ai_chat_parses_string_missing_slots_and_localizes_clarification() -> None:
    class ClarificationService(FrontendCompatService):
        def process_chat_message(self, payload: dict) -> dict:
            self.last_chat_payload = payload
            return {
                "chat_session": {"session_id": "CHAT_TEST_002"},
                "analysis": {
                    "procedure": {"procedure_type": "noise_self_check"},
                    "decision_result": {
                        "service_flow_type": "self_as",
                        "risk_level": "medium",
                        "decision_action": "ask_clarification",
                        "missing_slots": ["risk_signal", "symptom_location"],
                    },
                },
                "chatbot_engine": {
                    "ai_message": {
                        "message_type": "text",
                        "message_content": "Do you see any smoke?",
                    },
                    "conversation_state": {
                        "session_id": "CHAT_TEST_002",
                        "missing_slots": "[\"risk_signal\",\"symptom_location\"]",
                        "state_status": "collecting",
                    },
                    "guide_options": None,
                },
            }

    service = ClarificationService()
    app.dependency_overrides[get_service] = lambda: service
    client = TestClient(app)

    try:
        response = client.post(
            "/api/ai/chat",
            json={
                "message": "소음이나 진동이 심해요",
                "context": {"deviceId": "D001", "session_id": "CHAT_TEST_002"},
            },
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["needs_clarification"] is True
        assert payload["missing_slots"] == ["risk_signal", "symptom_location"]
        assert payload["procedure_type"] == "noise_self_check"
        assert "위험 신호" in payload["message"]
        assert payload["guide_options"] is None
    finally:
        app.dependency_overrides.clear()


def test_frontend_ai_chat_asks_risk_signal_before_symptom_detail() -> None:
    class CoolingClarificationService(FrontendCompatService):
        def process_chat_message(self, payload: dict) -> dict:
            self.last_chat_payload = payload
            return {
                "chat_session": {"session_id": "CHAT_TEST_COOLING"},
                "analysis": {
                    "procedure": {"procedure_type": "no_cooling_self_check"},
                    "decision_result": {
                        "service_flow_type": "self_as",
                        "risk_level": "medium",
                        "decision_action": "ask_clarification",
                        "missing_slots": ["risk_signal", "symptom_location"],
                    },
                },
                "chatbot_engine": {
                    "ai_message": {
                        "message_type": "text",
                        "message_content": "Do you see any smoke?",
                    },
                    "conversation_state": {
                        "session_id": "CHAT_TEST_COOLING",
                        "missing_slots": ["risk_signal", "symptom_location"],
                        "state_status": "collecting",
                    },
                    "guide_options": None,
                },
            }

    service = CoolingClarificationService()
    app.dependency_overrides[get_service] = lambda: service
    client = TestClient(app)

    try:
        response = client.post(
            "/api/ai/chat",
            json={
                "message": "냉방/기능이 잘 작동하지 않아요",
                "context": {"deviceId": "D001", "session_id": "CHAT_TEST_COOLING"},
            },
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["needs_clarification"] is True
        assert payload["procedure_type"] == "no_cooling_self_check"
        assert "위험 신호" in payload["message"]
        assert "아니요" in payload["message"]
        assert "바람이 나오는지" not in payload["message"]
        assert "냉방이 안 되는 상황" not in payload["message"]
        assert "소음/진동" not in payload["message"]
    finally:
        app.dependency_overrides.clear()


def test_frontend_ai_chat_uses_procedure_specific_symptom_detail_copy_after_risk() -> None:
    class CoolingDetailService(FrontendCompatService):
        def process_chat_message(self, payload: dict) -> dict:
            self.last_chat_payload = payload
            return {
                "chat_session": {"session_id": "CHAT_TEST_COOLING_DETAIL"},
                "analysis": {
                    "procedure": {"procedure_type": "no_cooling_self_check"},
                    "decision_result": {
                        "service_flow_type": "self_as",
                        "risk_level": "medium",
                        "decision_action": "ask_clarification",
                        "missing_slots": ["symptom_location"],
                    },
                },
                "chatbot_engine": {
                    "ai_message": {
                        "message_type": "text",
                        "message_content": "Where do you notice it?",
                    },
                    "conversation_state": {
                        "session_id": "CHAT_TEST_COOLING_DETAIL",
                        "missing_slots": ["symptom_location"],
                        "state_status": "collecting",
                    },
                    "guide_options": None,
                },
            }

    service = CoolingDetailService()
    app.dependency_overrides[get_service] = lambda: service
    client = TestClient(app)

    try:
        response = client.post(
            "/api/ai/chat",
            json={
                "message": "아니요",
                "context": {"deviceId": "D001", "session_id": "CHAT_TEST_COOLING_DETAIL"},
            },
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["needs_clarification"] is True
        assert payload["procedure_type"] == "no_cooling_self_check"
        assert "냉방이 잘 안 되는 상황" in payload["message"]
        assert "바람은 나오는지" in payload["message"]
        assert "위험 신호" not in payload["message"]
    finally:
        app.dependency_overrides.clear()


def test_frontend_ai_chat_requires_message() -> None:
    app.dependency_overrides[get_service] = lambda: FrontendCompatService()
    client = TestClient(app)

    try:
        response = client.post("/api/ai/chat", json={"context": {"deviceId": "D001"}})
        assert response.status_code == 400
        assert response.json()["detail"] == "message is required"
    finally:
        app.dependency_overrides.clear()
