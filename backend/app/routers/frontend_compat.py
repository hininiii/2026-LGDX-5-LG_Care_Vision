from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status

from ..dependencies import get_service
from ..services import CareShotBackendService


router = APIRouter(tags=["frontend-compat"])


def _frontend_user_profile(raw: dict[str, Any] | None) -> dict[str, str]:
    raw = raw or {}
    user_email = raw.get("user_email") or raw.get("email") or raw.get("user_id") or "u001@careshot.local"
    name = (
        raw.get("customer_name")
        or raw.get("user_name")
        or raw.get("display_name")
        or raw.get("name")
        or "तनीषा"
    )
    phone = raw.get("phone_number") or raw.get("phone") or "+91-9876543210"
    city = raw.get("city") or "New Delhi"
    region = raw.get("region") or raw.get("state") or "Delhi"
    country = raw.get("country") or "India"
    address = raw.get("address") or raw.get("address_line1") or f"{country} {region} {city}"
    return {
        "user_email": str(user_email),
        "email": str(user_email),
        "name": str(name),
        "phone": str(phone),
        "address": str(address),
        "region_id": str(raw.get("region_id") or ""),
        "region": str(region),
        "city": str(city),
    }


def _frontend_device_option(raw: dict[str, Any] | None, fallback_id: str) -> dict[str, str]:
    raw = raw or {}
    device_id = raw.get("device_id") or fallback_id
    name = raw.get("display_name") or raw.get("nickname") or raw.get("product_name") or "거실 에어컨"
    model = raw.get("model_name") or raw.get("model") or "AS-Q24ENXE"
    return {"id": str(device_id), "name": str(name), "model": str(model)}


def _message_from_payload(payload: dict[str, Any]) -> str:
    message = payload.get("message")
    if isinstance(message, str):
        return message
    if isinstance(message, dict):
        return str(message.get("content") or message.get("text") or "")
    return str(payload.get("content") or payload.get("text") or "")


def _json_list(value: Any) -> list[Any]:
    if value in (None, ""):
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return [value]
        return parsed if isinstance(parsed, list) else []
    return []


def _symptom_location_question(procedure: str | None) -> str:
    return {
        "noise_self_check": "소음이나 진동이 어디에서 느껴지나요? 실내기 본체, 송풍구, 앞 커버, 배수부, 전원부 중 가까운 위치를 알려주세요.",
        "no_cooling_self_check": "냉방이 잘 안 되는 상황을 조금 더 알려주세요. 바람은 나오는지, 바람이 약한지, 송풍구 쪽 문제인지 알려주세요.",
        "power_troubleshooting": "전원 문제가 어디에서 보이나요? 플러그, 콘센트, 차단기, 표시창, 리모컨 중 가까운 위치를 알려주세요.",
        "odor_self_check": "냄새가 어디에서 주로 나나요? 송풍구, 필터, 실내기 본체, 배수부 중 가까운 위치를 알려주세요.",
        "water_leak_monsoon": "물이 어디에서 새나요? 실내기 본체, 송풍구, 배수 호스, 실외기 주변 중 가까운 위치를 알려주세요.",
    }.get(str(procedure), "증상이 나타나는 위치나 상황을 조금 더 알려주세요.")


def _localized_chat_message(raw: dict[str, Any], fallback: str) -> str:
    chatbot = raw.get("chatbot_engine") or {}
    state = chatbot.get("conversation_state") or {}
    analysis = raw.get("analysis") or {}
    decision = analysis.get("decision_result") or {}
    procedure = (analysis.get("procedure") or {}).get("procedure_type")
    missing_slots = _json_list(state.get("missing_slots") or decision.get("missing_slots"))

    if missing_slots:
        first_missing = missing_slots[0]
        if first_missing == "risk_signal":
            return "연기, 스파크, 타는 냄새, 감전, 냉매/가스 냄새 같은 위험 신호가 있나요? 없다면 '아니요'라고 답해주세요."
        if first_missing == "symptom_location":
            return _symptom_location_question(procedure)
        if first_missing == "environment_context":
            return "현재 실내가 습하거나 먼지가 많거나 비/장마 영향을 받고 있나요?"
        if first_missing == "recent_diagnosis":
            return "ThinQ 진단이나 표시창에 에러, 전원 꺼짐, 차단기 관련 신호가 보이나요?"
        return "안전한 안내를 위해 증상을 한 가지만 더 알려주세요."

    if decision.get("service_flow_type") == "expert_as" or decision.get("risk_level") == "high":
        return "위험 신호가 있어 AR 자가 안내는 차단했어요. 공식 A/S 또는 서비스센터 연결을 권장합니다."

    procedure_label = {
        "filter_cleaning": "필터 청소",
        "noise_self_check": "소음/진동 자가점검",
        "no_cooling_self_check": "냉방/바람 약함 자가점검",
        "odor_self_check": "냄새 자가점검",
        "water_leak_monsoon": "누수 자가점검",
        "power_troubleshooting": "전원 자가점검",
    }.get(str(procedure), "가이드")
    if chatbot.get("guide_options"):
        return f"공식 근거에 맞는 {procedure_label} 안내를 준비했어요. 안전 규칙상 허용되는 단계만 보여드릴게요."
    return fallback


def _frontend_ai_chat_response(raw: dict[str, Any]) -> dict[str, Any]:
    chatbot = raw.get("chatbot_engine") or {}
    ai_message = chatbot.get("ai_message") or {}
    analysis = raw.get("analysis") or {}
    decision = analysis.get("decision_result") or {}
    state = chatbot.get("conversation_state") or {}
    guide_options = chatbot.get("guide_options")
    missing_slots = _json_list(state.get("missing_slots") or decision.get("missing_slots"))
    fallback_message = (
        ai_message.get("message_content")
        or state.get("next_question")
        or "I checked your request."
    )

    return {
        "message": _localized_chat_message(raw, fallback_message),
        "message_type": ai_message.get("message_type") or "text",
        "session_id": (raw.get("chat_session") or {}).get("session_id") or state.get("session_id"),
        "intent": decision.get("intent_type") or decision.get("service_flow_type"),
        "service_flow_type": decision.get("service_flow_type"),
        "risk_level": decision.get("risk_level"),
        "procedure_type": (analysis.get("procedure") or {}).get("procedure_type"),
        "recommended_action": decision.get("decision_action"),
        "needs_clarification": bool(missing_slots),
        "missing_slots": missing_slots,
        "guide_options": guide_options,
        "analysis": analysis,
        "raw": raw,
    }


@router.post("/users/register", status_code=status.HTTP_201_CREATED)
def register_frontend_user(
    payload: dict[str, Any],
    service: CareShotBackendService = Depends(get_service),
) -> dict[str, Any]:
    try:
        profile = service.register_frontend_user(payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return {
        "user": _frontend_user_profile(profile),
        "demo_seed": profile.get("demo_seed") or {},
    }


@router.post("/users/login")
def login_frontend_user(
    payload: dict[str, Any],
    service: CareShotBackendService = Depends(get_service),
) -> dict[str, Any]:
    try:
        profile = service.login_frontend_user(payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
    return {"user": _frontend_user_profile(profile)}


@router.get("/users/me")
def get_current_frontend_user(
    user_email: str | None = None,
    service: CareShotBackendService = Depends(get_service),
) -> dict[str, str]:
    return _frontend_user_profile(service.repo.get_user_profile(user_email or "U001"))


@router.put("/users/me")
def update_frontend_user(
    payload: dict[str, Any],
    service: CareShotBackendService = Depends(get_service),
) -> dict[str, Any]:
    try:
        profile = service.update_frontend_user(payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return {"user": _frontend_user_profile(profile)}


@router.get("/devices")
def get_frontend_devices(
    service: CareShotBackendService = Depends(get_service),
) -> list[dict[str, str]]:
    primary = service.repo.get_device_context("D001")
    if primary:
        return [_frontend_device_option(primary, "D001")]
    return [
        {"id": "D001", "name": "거실 에어컨", "model": "AS-Q24ENXE"},
    ]


@router.post("/chat-messages", status_code=status.HTTP_201_CREATED)
def save_frontend_chat_message(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "saved": True,
        "message": payload.get("message") or payload,
        "storage": "frontend_compat_ack",
    }


@router.post("/ai/chat")
def request_frontend_ai_chat(
    payload: dict[str, Any],
    service: CareShotBackendService = Depends(get_service),
) -> dict[str, Any]:
    message = _message_from_payload(payload).strip()
    if not message:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="message is required")

    context = payload.get("context") if isinstance(payload.get("context"), dict) else {}
    request = {
        "user_id": payload.get("user_id") or context.get("user_id") or "U001",
        "device_id": payload.get("device_id") or context.get("deviceId") or context.get("device_id") or "D001",
        "session_id": payload.get("session_id") or context.get("session_id"),
        "message": message,
        "include_rag_evidence": bool(payload.get("include_rag_evidence", True)),
    }
    return _frontend_ai_chat_response(service.process_chat_message(request))
