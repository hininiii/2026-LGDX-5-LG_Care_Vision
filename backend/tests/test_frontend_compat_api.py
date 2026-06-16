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
        assert payload["card_policy"] == {
            "card_type": "ar_start",
            "title": "AR 가이드 시작 가능",
            "description": "공식 근거가 확인된 Low/Medium 자가점검 또는 관리 안내입니다.",
            "primary_action": "start_ar",
            "show_manual_button": True,
            "show_ar_button": True,
            "show_service_button": False,
            "reason": "official_guide_options_ready",
        }
        assert service.last_chat_payload == {
            "user_id": "U001",
            "device_id": "D001",
            "session_id": None,
            "message": "필터 청소 방법 알려줘",
            "include_rag_evidence": True,
        }
    finally:
        app.dependency_overrides.clear()


def test_frontend_ai_chat_card_policy_routes_high_risk_to_service_only() -> None:
    class HighRiskService(FrontendCompatService):
        def process_chat_message(self, payload: dict) -> dict:
            return {
                "chat_session": {"session_id": "CHAT_TEST_HIGH_RISK"},
                "analysis": {
                    "decision_result": {
                        "intent_type": "high_risk",
                        "service_flow_type": "expert_as",
                        "risk_level": "high",
                        "decision_action": "route_to_service",
                        "ar_guide_allowed": False,
                        "blocked_reason": "High-risk symptom detected.",
                    },
                },
                "chatbot_engine": {
                    "ai_message": {
                        "message_type": "safety_card",
                        "message_content": "AR is blocked.",
                    },
                    "conversation_state": {
                        "session_id": "CHAT_TEST_HIGH_RISK",
                        "missing_slots": [],
                    },
                    "guide_options": None,
                },
            }

    service = HighRiskService()
    app.dependency_overrides[get_service] = lambda: service
    client = TestClient(app)

    try:
        response = client.post("/api/ai/chat", json={"message": "연기와 타는 냄새가 나요", "context": {"deviceId": "D001"}})
        assert response.status_code == 200
        payload = response.json()
        assert payload["service_flow_type"] == "expert_as"
        assert payload["risk_level"] == "high"
        assert payload["guide_options"] is None
        assert payload["card_policy"]["card_type"] == "service_route"
        assert payload["card_policy"]["show_ar_button"] is False
        assert payload["card_policy"]["show_manual_button"] is False
        assert payload["card_policy"]["show_service_button"] is True
        assert payload["card_policy"]["primary_action"] == "service_center"
    finally:
        app.dependency_overrides.clear()


def test_frontend_ai_chat_card_policy_blocks_official_no_match() -> None:
    class NoMatchService(FrontendCompatService):
        def process_chat_message(self, payload: dict) -> dict:
            return {
                "chat_session": {"session_id": "CHAT_TEST_NO_MATCH"},
                "analysis": {
                    "official_asset_match": {"match_status": "needs_review"},
                    "decision_result": {
                        "intent_type": "self_check",
                        "service_flow_type": "self_as",
                        "risk_level": "unknown",
                        "decision_action": "official_match_review_needed",
                        "ar_guide_allowed": False,
                        "blocked_reason": "Official asset match is not verified.",
                    },
                },
                "chatbot_engine": {
                    "ai_message": {
                        "message_type": "text",
                        "message_content": "Official guide options are not ready.",
                    },
                    "conversation_state": {
                        "session_id": "CHAT_TEST_NO_MATCH",
                        "missing_slots": [],
                    },
                    "guide_options": None,
                },
            }

    service = NoMatchService()
    app.dependency_overrides[get_service] = lambda: service
    client = TestClient(app)

    try:
        response = client.post("/api/ai/chat", json={"message": "알 수 없는 증상이에요", "context": {"deviceId": "D001"}})
        assert response.status_code == 200
        payload = response.json()
        assert payload["recommended_action"] == "official_match_review_needed"
        assert payload["guide_options"] is None
        assert payload["card_policy"]["card_type"] == "safety_block"
        assert payload["card_policy"]["title"] == "공식자료 확인 불가"
        assert payload["card_policy"]["show_ar_button"] is False
        assert payload["card_policy"]["show_manual_button"] is False
        assert payload["card_policy"]["show_service_button"] is True
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


def test_frontend_ai_chat_uses_backend_question_for_generic_low_info_symptom_missing() -> None:
    class SymptomMissingService(FrontendCompatService):
        def process_chat_message(self, payload: dict) -> dict:
            return {
                "chat_session": {"session_id": "CHAT_TEST_GENERIC"},
                "analysis": {
                    "procedure": {},
                    "decision_result": {
                        "risk_level": "low",
                        "decision_action": "ask_clarification",
                        "missing_slots": ["symptom_type"],
                        "next_question": "어떤 문제가 있나요? 냉방/바람, 소음/진동, 냄새, 물샘, 전원 문제, 필터 관리 중 가까운 증상을 알려주세요.",
                    },
                },
                "chatbot_engine": {
                    "ai_message": {
                        "message_type": "text",
                        "message_content": "fallback",
                    },
                    "conversation_state": {
                        "session_id": "CHAT_TEST_GENERIC",
                        "missing_slots": ["symptom_type"],
                        "next_question": "어떤 문제가 있나요? 냉방/바람, 소음/진동, 냄새, 물샘, 전원 문제, 필터 관리 중 가까운 증상을 알려주세요.",
                    },
                    "guide_options": None,
                },
            }

    service = SymptomMissingService()
    app.dependency_overrides[get_service] = lambda: service
    client = TestClient(app)

    try:
        response = client.post("/api/ai/chat", json={"message": "이상해요", "context": {"deviceId": "D001"}})
        assert response.status_code == 200
        payload = response.json()
        assert payload["needs_clarification"] is True
        assert payload["procedure_type"] is None
        assert payload["guide_options"] is None
        assert payload["message"].startswith("어떤 문제가 있나요?")
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


def test_frontend_ai_chat_power_issue_asks_risk_only_first() -> None:
    class PowerClarificationService(FrontendCompatService):
        def process_chat_message(self, payload: dict) -> dict:
            self.last_chat_payload = payload
            return {
                "chat_session": {"session_id": "CHAT_TEST_POWER"},
                "analysis": {
                    "procedure": {"procedure_type": "power_troubleshooting"},
                    "decision_result": {
                        "service_flow_type": "self_as",
                        "risk_level": "medium",
                        "decision_action": "ask_clarification",
                        "missing_slots": ["risk_signal", "symptom_location", "recent_diagnosis"],
                    },
                },
                "chatbot_engine": {
                    "ai_message": {
                        "message_type": "text",
                        "message_content": "Do you see any smoke?",
                    },
                    "conversation_state": {
                        "session_id": "CHAT_TEST_POWER",
                        "missing_slots": ["risk_signal", "symptom_location", "recent_diagnosis"],
                        "state_status": "collecting",
                    },
                    "guide_options": None,
                },
            }

    service = PowerClarificationService()
    app.dependency_overrides[get_service] = lambda: service
    client = TestClient(app)

    try:
        response = client.post(
            "/api/ai/chat",
            json={
                "message": "전원이 불안정하고 자주 꺼져요",
                "context": {"deviceId": "D001", "session_id": "CHAT_TEST_POWER"},
            },
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["needs_clarification"] is True
        assert payload["procedure_type"] == "power_troubleshooting"
        assert "위험 신호" in payload["message"]
        assert "아니요" in payload["message"]
        assert "전원부" not in payload["message"]
        assert "플러그" not in payload["message"]
        assert "차단기" not in payload["message"]
        assert "표시장" not in payload["message"]
    finally:
        app.dependency_overrides.clear()


def test_frontend_ai_chat_power_issue_asks_detail_after_negative_risk() -> None:
    class PowerDetailService(FrontendCompatService):
        def process_chat_message(self, payload: dict) -> dict:
            self.last_chat_payload = payload
            return {
                "chat_session": {"session_id": "CHAT_TEST_POWER_DETAIL"},
                "analysis": {
                    "procedure": {"procedure_type": "power_troubleshooting"},
                    "decision_result": {
                        "service_flow_type": "self_as",
                        "risk_level": "medium",
                        "decision_action": "ask_clarification",
                        "missing_slots": ["symptom_location", "recent_diagnosis"],
                    },
                },
                "chatbot_engine": {
                    "ai_message": {
                        "message_type": "text",
                        "message_content": "Where do you notice it?",
                    },
                    "conversation_state": {
                        "session_id": "CHAT_TEST_POWER_DETAIL",
                        "missing_slots": ["symptom_location", "recent_diagnosis"],
                        "state_status": "collecting",
                    },
                    "guide_options": None,
                },
            }

    service = PowerDetailService()
    app.dependency_overrides[get_service] = lambda: service
    client = TestClient(app)

    try:
        response = client.post(
            "/api/ai/chat",
            json={
                "message": "아니요",
                "context": {"deviceId": "D001", "session_id": "CHAT_TEST_POWER_DETAIL"},
            },
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["needs_clarification"] is True
        assert payload["procedure_type"] == "power_troubleshooting"
        assert "전원이 꺼지는 상황" in payload["message"]
        assert "플러그" in payload["message"]
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
