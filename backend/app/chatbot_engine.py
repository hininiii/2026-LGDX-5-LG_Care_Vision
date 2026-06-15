from __future__ import annotations

import json
import re
from typing import Any


class ChatbotEngine:
    """Coordinates chat session persistence, inquiry analysis, and guide options."""

    SLOT_SCHEMA: dict[str, dict[str, Any]] = {
        "product_family": {
            "description": "Appliance family inferred from the registered device or customer wording.",
            "examples": ["air_conditioner", "washing_machine", "air_purifier", "water_purifier"],
        },
        "symptom_type": {
            "description": "Main symptom or care intent.",
            "examples": ["odor", "water_leak", "weak_airflow", "noise", "filter_care", "power_issue"],
        },
        "symptom_location": {
            "description": "Visible location of the symptom.",
            "examples": ["indoor_unit", "outlet", "filter_area", "front_panel", "drain_area", "power_area"],
        },
        "risk_signal": {
            "description": "Danger signal that can force expert_as.",
            "examples": ["burning_smell", "smoke", "spark", "electric_shock", "gas_leak", "none"],
        },
        "recent_diagnosis": {
            "description": "Latest ThinQ or smart diagnosis severity/signals.",
            "examples": ["none", "low", "medium", "high"],
        },
        "environment_context": {
            "description": "Relevant environment clue such as monsoon, humidity, AQI, or hard water.",
            "examples": ["humid", "monsoon", "dusty", "hard_water", "unknown"],
        },
    }

    AMBIGUOUS_PATTERNS = {
        "odor": [
            "smell",
            "odor",
            "odour",
            "bad smell",
            "냄새",
            "악취",
        ],
        "water_leak": [
            "water",
            "leak",
            "drip",
            "dripping",
            "물이",
            "물",
            "누수",
            "새요",
            "떨어",
        ],
        "noise": [
            "noise",
            "sound",
            "vibration",
            "noisy",
            "소리",
            "소음",
            "진동",
        ],
        "weak_airflow": [
            "weak",
            "airflow",
            "not cooling",
            "cooling",
            "바람",
            "약",
            "시원",
            "냉방",
        ],
        "filter_care": [
            "filter",
            "clean",
            "dust",
            "필터",
            "청소",
            "먼지",
        ],
        "power_issue": [
            "power",
            "turns off",
            "no power",
            "unstable",
            "꺼",
            "꺼져",
            "자주 꺼",
            "전원",
            "불안정",
        ],
    }

    RISK_KEYWORDS = {
        "burning_smell": ["burning", "burnt", "타는", "탄내"],
        "smoke": ["smoke", "연기"],
        "spark": ["spark", "sparking", "스파크", "불꽃"],
        "electric_shock": ["shock", "electric", "감전"],
        "gas_leak": ["gas", "refrigerant", "냉매", "가스"],
    }

    LOCATION_KEYWORDS = {
        "indoor_unit": ["indoor", "unit", "실내기", "본체"],
        "outlet": ["outlet", "vent", "air outlet", "송풍구", "바람구멍"],
        "filter_area": ["filter", "필터"],
        "front_panel": ["front", "cover", "panel", "앞", "커버"],
        "drain_area": ["drain", "pipe", "배수", "호스"],
        "power_area": ["plug", "wire", "cord", "socket", "breaker", "플러그", "콘센트", "차단기"],
    }

    ENVIRONMENT_KEYWORDS = {
        "humid": ["humid", "humidity", "습", "습도"],
        "monsoon": ["monsoon", "rain", "rainy", "장마", "비"],
        "dusty": ["dust", "dusty", "먼지"],
        "hard_water": ["hard water", "scale", "limescale", "경수", "석회"],
    }

    def __init__(self, service: Any) -> None:
        self.service = service
        self.repo = service.repo

    def handle_message(self, payload: dict[str, Any]) -> dict[str, Any]:
        payload = dict(payload)
        session = self.ensure_session(payload)
        session_id = session.get("session_id") if session else payload.get("session_id")
        previous_state = self.get_state(session_id)
        turn_context = self.prepare_turn_context(payload, previous_state)
        payload["original_message"] = turn_context["original_message"]
        payload["message"] = turn_context["analysis_message"]
        if session_id is not None:
            payload["session_id"] = session_id
            self.add_chat_message(
                {
                    "session_id": session_id,
                    "sender_type": "user",
                    "message_type": "text",
                    "message_content": turn_context["original_message"],
                }
            )

        analysis = self.service.analyze({**payload, "include_rag_evidence": False})
        if turn_context["state_status"] == "collecting":
            self.apply_clarification_gate(analysis, turn_context)
        inquiry = self.create_inquiry(payload, session_id)
        ai_analysis = self.create_ai_analysis(inquiry, analysis)

        if payload.get("include_rag_evidence", True) and turn_context["state_status"] != "collecting":
            analysis["rag_evidence"] = self.service.search_rag_for_analysis(
                {
                    **payload,
                    "inquiry_id": (inquiry or {}).get("inquiry_id"),
                    "ai_response_id": (ai_analysis or {}).get("ai_response_id"),
                },
                analysis,
            )

        preliminary_llm_assist = self.assist_with_llm(payload, turn_context, analysis, None, None)
        if turn_context["state_status"] != "collecting":
            self.apply_decision_v2(payload, turn_context, analysis, preliminary_llm_assist)

        guide_options = None if turn_context["state_status"] == "collecting" else self.guide_options_for_analysis(payload, analysis)
        state = self.upsert_state(session_id, analysis, bool(guide_options), turn_context)
        llm_assist = self.assist_with_llm(payload, turn_context, analysis, guide_options, state)
        analysis["llm_assist"] = llm_assist
        plan_payload = self.service.plan_from_analysis(analysis)
        ai_message = self.build_ai_message(analysis, guide_options, state, llm_assist)

        if session_id is not None:
            self.add_chat_message(
                {
                    "session_id": session_id,
                    "sender_type": "ai",
                    "message_type": ai_message["message_type"],
                    "message_content": ai_message["message_content"],
                }
            )

        return {
            **plan_payload,
            "chat_session": session,
            "chatbot_engine": {
                "chat_session": session,
                "inquiry": inquiry,
                "ai_inquiry_analysis": ai_analysis,
                "conversation_state": state,
                "slot_schema": self.SLOT_SCHEMA,
                "turn_context": turn_context,
                "llm_assist": llm_assist,
                "guide_options": guide_options,
                "ai_message": ai_message,
                "llm_policy": {
                    "provider": llm_assist.get("provider"),
                    "final_ar_permission_by_llm": False,
                    "official_evidence_verification_by_llm": False,
                },
                "storage_policy": {
                    "chat_tables": [
                        "CHAT_SESSION",
                        "CHATBOT_INQUIRY",
                        "AI_INQUIRY_ANALYSIS",
                        "CHAT_MESSAGE",
                        "CONVERSATION_STATE",
                    ],
                    "legacy_log_tables_reopened": False,
                },
            },
        }

    def ensure_session(self, payload: dict[str, Any]) -> dict[str, Any] | None:
        if not hasattr(self.repo, "create_chat_session"):
            return None
        session_id = payload.get("session_id")
        if session_id and hasattr(self.repo, "get_chat_session"):
            current = self.repo.get_chat_session(session_id)
            if current:
                return current
        return self.repo.create_chat_session(
            {
                "session_id": session_id,
                "user_id": payload.get("user_id", "U001"),
                "device_id": payload.get("device_id", "D001"),
                "status": "active",
            }
        )

    def add_chat_message(self, payload: dict[str, Any]) -> dict[str, Any] | None:
        if hasattr(self.repo, "add_chat_message") and payload.get("message_content"):
            return self.repo.add_chat_message(payload)
        return None

    def assist_with_llm(
        self,
        payload: dict[str, Any],
        turn_context: dict[str, Any],
        analysis: dict[str, Any],
        guide_options: dict[str, Any] | None,
        state: dict[str, Any] | None,
    ) -> dict[str, Any]:
        llm_service = getattr(self.service, "llm_service", None)
        if not llm_service:
            return {
                "provider": "none",
                "mode": "disabled",
                "response_text": None,
                "decision_authority": {
                    "final_ar_permission": "Rule/Safety Guard + RAG official evidence + DecisionEngine",
                    "llm_can_override_safety": False,
                    "llm_can_verify_official_evidence": False,
                },
            }
        try:
            return llm_service.assist_chat_turn(
                {
                    "payload": payload,
                    "turn_context": turn_context,
                    "analysis": analysis,
                    "guide_options": guide_options,
                    "conversation_state": state,
                }
            )
        except Exception as exc:
            return {
                "provider": getattr(llm_service, "provider", "unknown"),
                "mode": "error_fallback",
                "error": str(exc),
                "response_text": None,
                "decision_authority": {
                    "final_ar_permission": "Rule/Safety Guard + RAG official evidence + DecisionEngine",
                    "llm_can_override_safety": False,
                    "llm_can_verify_official_evidence": False,
                },
            }

    def apply_decision_v2(
        self,
        payload: dict[str, Any],
        turn_context: dict[str, Any],
        analysis: dict[str, Any],
        llm_assist: dict[str, Any],
    ) -> None:
        decision_engine_v2 = getattr(self.service, "decision_engine_v2", None)
        if not decision_engine_v2:
            analysis["decision_v2"] = {
                "source_engine": "v1_rule_engine",
                "fallback_reason": "DecisionEngineV2 is not configured.",
            }
            return
        decision_engine_v2.apply_to_analysis(
            analysis,
            customer_message=turn_context.get("original_message") or payload.get("message") or "",
            collected_slots=turn_context.get("collected_slots") or {},
            llm_assist=llm_assist,
            rag_evidence=analysis.get("rag_evidence"),
        )

    def get_state(self, session_id: Any) -> dict[str, Any] | None:
        if not session_id or not hasattr(self.repo, "get_conversation_state"):
            return None
        return self.repo.get_conversation_state(session_id)

    def prepare_turn_context(
        self,
        payload: dict[str, Any],
        previous_state: dict[str, Any] | None,
    ) -> dict[str, Any]:
        original_message = str(payload.get("message") or "")
        previous_slots = self.parse_json_field((previous_state or {}).get("collected_slots_json"), {})
        previous_missing = self.parse_json_field((previous_state or {}).get("missing_slots"), [])
        continuing_collection = bool(
            previous_state
            and previous_state.get("state_status") == "collecting"
            and previous_missing
        )
        current_slots = self.extract_slots(original_message, payload, previous_slots)
        if continuing_collection and previous_slots.get("symptom_type"):
            current_slots["symptom_type"] = previous_slots["symptom_type"]
        collected_slots = self.merge_slots(previous_slots, current_slots)
        ambiguous_kind = self.detect_ambiguous_kind(original_message)

        missing_slots = self.required_missing_slots(
            message=original_message,
            collected_slots=collected_slots,
            ambiguous_kind=ambiguous_kind,
            continuing_collection=continuing_collection,
        )
        state_status = "collecting" if missing_slots else "ready_for_analysis"
        analysis_message = self.build_analysis_message(original_message, collected_slots, continuing_collection)
        next_question = self.next_question_for_slots(missing_slots, collected_slots)

        return {
            "original_message": original_message,
            "analysis_message": analysis_message,
            "previous_state_status": (previous_state or {}).get("state_status"),
            "previous_missing_slots": previous_missing,
            "collected_slots": collected_slots,
            "current_slots": current_slots,
            "missing_slots": missing_slots,
            "next_question": next_question,
            "state_status": state_status,
            "ambiguous_kind": ambiguous_kind,
            "continuing_collection": continuing_collection,
        }

    def extract_slots(
        self,
        message: str,
        payload: dict[str, Any],
        previous_slots: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        normalized = self.normalize(message)
        slots: dict[str, Any] = {}
        slots["product_family"] = self.product_family_from_payload(payload)

        symptom_type = self.detect_symptom_type(normalized)
        if symptom_type:
            slots["symptom_type"] = symptom_type

        negative_risk_reply = self.is_negative_risk_reply(normalized)
        risk_signal = None if negative_risk_reply else self.detect_risk_signal(normalized)
        if risk_signal:
            slots["risk_signal"] = risk_signal
        elif previous_slots and previous_slots.get("risk_signal") and negative_risk_reply:
            slots["risk_signal"] = "none"
        elif negative_risk_reply:
            slots["risk_signal"] = "none"

        symptom_location = self.detect_symptom_location(normalized)
        if symptom_location:
            slots["symptom_location"] = symptom_location

        environment_context = self.detect_environment_context(normalized)
        if environment_context:
            slots["environment_context"] = environment_context

        diagnosis = self.detect_diagnosis_slot(normalized) or self.latest_diagnosis_slot(payload)
        if diagnosis:
            slots["recent_diagnosis"] = diagnosis

        if self.is_affirmative_response(normalized) and previous_slots:
            if previous_slots.get("symptom_type") == "odor" and "risk_signal" not in slots:
                slots["risk_signal"] = "burning_smell"
            if previous_slots.get("symptom_type") == "water_leak" and "symptom_location" not in slots:
                slots["symptom_location"] = "indoor_unit"
        if previous_slots and previous_slots.get("symptom_type") == "weak_airflow":
            if "symptom_location" not in slots and self.has_weak_airflow_detail(normalized):
                slots["symptom_location"] = "outlet"
            if "environment_context" not in slots and self.has_weak_airflow_detail(normalized):
                slots["environment_context"] = "unknown"
        return slots

    @staticmethod
    def merge_slots(previous: dict[str, Any] | None, current: dict[str, Any]) -> dict[str, Any]:
        merged = dict(previous or {})
        for key, value in current.items():
            if value not in (None, "", [], {}):
                merged[key] = value
        return merged

    def required_missing_slots(
        self,
        message: str,
        collected_slots: dict[str, Any],
        ambiguous_kind: str | None,
        continuing_collection: bool,
    ) -> list[str]:
        normalized = self.normalize(message)
        if self.detect_risk_signal(normalized) and not self.is_negative_risk_reply(normalized):
            return []
        symptom_type = collected_slots.get("symptom_type")
        if symptom_type == "filter_care" and not continuing_collection:
            return []
        if symptom_type == "power_issue" and not continuing_collection and "suddenly turns off" in normalized:
            return []
        if not symptom_type and not ambiguous_kind and not continuing_collection:
            return []

        required = ["symptom_type", "risk_signal", "symptom_location"]
        if symptom_type in {"odor", "water_leak", "weak_airflow"}:
            required.append("environment_context")
        if symptom_type == "power_issue":
            required.append("recent_diagnosis")
        return [slot for slot in required if not collected_slots.get(slot)]

    def build_analysis_message(
        self,
        original_message: str,
        collected_slots: dict[str, Any],
        continuing_collection: bool,
    ) -> str:
        if not continuing_collection:
            return original_message
        symptom = collected_slots.get("symptom_type")
        risk = collected_slots.get("risk_signal")
        location = collected_slots.get("symptom_location")
        env = collected_slots.get("environment_context")
        parts: list[str] = []
        if symptom == "odor":
            if risk in {"burning_smell", "smoke", "spark", "electric_shock", "gas_leak"}:
                parts.append("There is burning smell from the AC.")
            else:
                parts.append("There is bad smell odor from my split AC.")
        elif symptom == "water_leak":
            parts.append("Water is dripping from my air conditioner indoor unit.")
        elif symptom == "weak_airflow":
            parts.append("Weak airflow and not cooling from the AC outlet.")
        elif symptom == "noise":
            parts.append("There is vibration noise from the AC indoor unit.")
        elif symptom == "power_issue":
            parts.append("The AC power suddenly turns off.")
        elif symptom == "filter_care":
            parts.append("Please help me clean the AC filter.")
        if location:
            parts.append(f"Symptom location: {location}.")
        if env and symptom != "odor":
            parts.append(f"Environment clue: {env}.")
        if risk == "none":
            parts.append("Risk signal: none.")
        return " ".join(parts)

    def next_question_for_slots(self, missing_slots: list[str], collected_slots: dict[str, Any]) -> str | None:
        if not missing_slots:
            return None
        symptom_type = collected_slots.get("symptom_type")
        first_missing = missing_slots[0]
        if first_missing == "symptom_type":
            return "What exact symptom do you see: smell, water leak, weak airflow, noise, power issue, or filter care?"
        if first_missing == "risk_signal":
            if symptom_type == "odor":
                return "Does it smell like burning or gas, or is it more like mold/dust?"
            return "Do you see any smoke, sparks, burning smell, electric shock, gas leak, or damaged power parts?"
        if first_missing == "symptom_location":
            if symptom_type == "water_leak":
                return "Where is the water coming from: indoor unit, drain pipe, front panel, or around the power area?"
            return "Where do you notice it: outlet, filter area, front panel, indoor unit, drain area, or power area?"
        if first_missing == "environment_context":
            return "Is the room humid, dusty, rainy/monsoon, or affected by hard water?"
        if first_missing == "recent_diagnosis":
            return "Does ThinQ or the display show an error, breaker trip, or repeated power-off signal?"
        return "Please share one more detail about the symptom."

    def detect_ambiguous_kind(self, message: str) -> str | None:
        normalized = self.normalize(message)
        for kind, patterns in self.AMBIGUOUS_PATTERNS.items():
            if any(pattern in normalized for pattern in patterns):
                if len(normalized.split()) <= 6 or kind in {"odor", "water_leak"}:
                    return kind
        return None

    def detect_symptom_type(self, normalized: str) -> str | None:
        for kind, patterns in self.AMBIGUOUS_PATTERNS.items():
            if any(pattern in normalized for pattern in patterns):
                return kind
        return None

    def detect_risk_signal(self, normalized: str) -> str | None:
        for signal, patterns in self.RISK_KEYWORDS.items():
            if any(pattern in normalized for pattern in patterns):
                return signal
        return None

    def detect_symptom_location(self, normalized: str) -> str | None:
        for location, patterns in self.LOCATION_KEYWORDS.items():
            if any(pattern in normalized for pattern in patterns):
                return location
        return None

    def detect_environment_context(self, normalized: str) -> str | None:
        for context, patterns in self.ENVIRONMENT_KEYWORDS.items():
            if any(pattern in normalized for pattern in patterns):
                return context
        return None

    @staticmethod
    def has_weak_airflow_detail(normalized: str) -> bool:
        return any(
            phrase in normalized
            for phrase in [
                "weak airflow",
                "not cooling",
                "airflow",
                "cooling",
                "바람",
                "약",
                "시원",
                "냉방",
            ]
        )

    def latest_diagnosis_slot(self, payload: dict[str, Any]) -> str | None:
        device_id = payload.get("device_id", "D001")
        if not hasattr(self.repo, "get_smart_diagnosis"):
            return None
        try:
            diagnosis = self.repo.get_smart_diagnosis(device_id) or {}
        except Exception:
            return None
        return diagnosis.get("severity") or diagnosis.get("severity_level")

    @staticmethod
    def detect_diagnosis_slot(normalized: str) -> str | None:
        if "thinq" not in normalized and "진단" not in normalized and "diagnosis" not in normalized:
            return None
        for severity in ["high", "medium", "low", "none"]:
            if severity in normalized:
                return severity
        for severity in ["높음", "중간", "낮음", "정상"]:
            if severity in normalized:
                return {
                    "높음": "high",
                    "중간": "medium",
                    "낮음": "low",
                    "정상": "none",
                }[severity]
        return None

    def product_family_from_payload(self, payload: dict[str, Any]) -> str | None:
        device_id = payload.get("device_id", "D001")
        if not hasattr(self.repo, "get_device_context"):
            return None
        try:
            device = self.repo.get_device_context(device_id) or {}
        except Exception:
            return None
        return device.get("product_type")

    @staticmethod
    def parse_json_field(value: Any, default: Any) -> Any:
        if value in (None, ""):
            return default
        if isinstance(value, (dict, list)):
            return value
        try:
            return json.loads(value)
        except (TypeError, json.JSONDecodeError):
            return default

    @staticmethod
    def normalize(message: str) -> str:
        return re.sub(r"\s+", " ", (message or "").lower()).strip()

    @staticmethod
    def is_negative_risk_reply(normalized: str) -> bool:
        return any(
            phrase in normalized
            for phrase in [
                "no",
                "not",
                "none",
                "mold",
                "dust",
                "dusty",
                "아니",
                "아뇨",
                "아냐",
                "없",
                "곰팡",
                "먼지",
            ]
        )

    @staticmethod
    def is_affirmative_response(normalized: str) -> bool:
        return normalized in {"yes", "y", "맞아", "네", "응"} or normalized.startswith("yes ")

    def create_inquiry(self, payload: dict[str, Any], session_id: Any) -> dict[str, Any] | None:
        if not session_id or not hasattr(self.repo, "create_chatbot_inquiry"):
            return None
        return self.repo.create_chatbot_inquiry(
            {
                "session_id": session_id,
                "user_id": payload.get("user_id", "U001"),
                "device_id": payload.get("device_id", "D001"),
                "inquiry_content": payload.get("original_message") or payload.get("message"),
            }
        )

    def create_ai_analysis(
        self,
        inquiry: dict[str, Any] | None,
        analysis: dict[str, Any],
    ) -> dict[str, Any] | None:
        if not inquiry or not hasattr(self.repo, "create_ai_inquiry_analysis"):
            return None
        decision = analysis.get("decision_result") or {}
        intent = analysis.get("intent") or {}
        procedure = analysis.get("procedure") or {}
        return self.repo.create_ai_inquiry_analysis(
            {
                "inquiry_id": inquiry["inquiry_id"],
                "symptom": procedure.get("procedure_type"),
                "intent_type": decision.get("service_flow_type") or intent.get("service_flow_type"),
                "risk_level": decision.get("risk_level"),
                "recommended_guide_id": self.recommended_guide_id(analysis),
                "safety_reason": self.safety_reason(analysis),
                "status_yn": "N",
            }
        )

    @staticmethod
    def apply_clarification_gate(analysis: dict[str, Any], turn_context: dict[str, Any]) -> None:
        decision = analysis.setdefault("decision_result", {})
        intent = analysis.setdefault("intent", {})
        procedure = analysis.setdefault("procedure", {})
        symptom_type = (turn_context.get("collected_slots") or {}).get("symptom_type")
        procedure_by_symptom = {
            "filter_care": ("filter_cleaning", "self_care"),
            "weak_airflow": ("no_cooling_self_check", "self_as"),
            "noise": ("noise_self_check", "self_as"),
            "odor": ("odor_self_check", "self_as"),
            "water_leak": ("water_leak_monsoon", "self_as"),
            "power_issue": ("power_troubleshooting", "self_as"),
        }
        if symptom_type in procedure_by_symptom:
            procedure_type, service_flow_type = procedure_by_symptom[symptom_type]
            procedure["procedure_type"] = procedure_type
            procedure["primary_procedure"] = procedure_type
            decision["service_flow_type"] = service_flow_type
            intent["service_flow_type"] = service_flow_type
        decision["decision_action"] = "ask_clarification"
        decision["ar_guide_allowed"] = False
        decision["generation_allowed"] = False
        decision["content_type"] = "clarification_question"
        decision["blocked_reason"] = "Additional customer detail is required before safe self-guidance."
        decision["missing_slots"] = turn_context["missing_slots"]
        decision["next_question"] = turn_context["next_question"]
        intent["clarification_required"] = True
        analysis["clarification"] = {
            "required": True,
            "missing_slots": turn_context["missing_slots"],
            "next_question": turn_context["next_question"],
            "slot_schema_version": "conversation_state_slots_v1",
        }

    def guide_options_for_analysis(
        self,
        payload: dict[str, Any],
        analysis: dict[str, Any],
    ) -> dict[str, Any] | None:
        decision = analysis.get("decision_result") or {}
        official_match = analysis.get("official_asset_match") or {}
        rag_evidence = analysis.get("rag_evidence") or {}
        service_flow_type = decision.get("service_flow_type")
        if service_flow_type not in {"self_care", "self_as"}:
            return None
        if not decision.get("ar_guide_allowed") and decision.get("decision_action") != "manual_or_service_guidance_only":
            return None
        if official_match.get("match_status") != "verified":
            return None
        if rag_evidence.get("ar_guide_blocked"):
            return None
        try:
            return self.service.get_guide_options(
                user_id=payload.get("user_id", "U001"),
                device_id=payload.get("device_id", "D001"),
                procedure_type=(analysis.get("procedure") or {}).get("procedure_type"),
                service_flow_type=service_flow_type,
                language_code=payload.get("language_code", "en"),
                rag_evidence=rag_evidence,
            )
        except AttributeError:
            return None

    def upsert_state(
        self,
        session_id: Any,
        analysis: dict[str, Any],
        has_guide_options: bool,
        turn_context: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        if not session_id or not hasattr(self.repo, "upsert_conversation_state"):
            return None
        intent = analysis.get("intent") or {}
        decision = analysis.get("decision_result") or {}
        service_flow_type = decision.get("service_flow_type") or intent.get("service_flow_type")
        confidence = float(intent.get("confidence") or 0)
        turn_context = turn_context or {}
        missing_slots: list[str] = list(turn_context.get("missing_slots") or [])
        next_question = turn_context.get("next_question")
        state_status = "completed"
        if missing_slots:
            state_status = "collecting"
        elif has_guide_options:
            state_status = "ready"
        elif service_flow_type != "expert_as" and confidence < 0.8:
            missing_slots = ["symptom_type"]
            next_question = self.next_question_for_slots(missing_slots, turn_context.get("collected_slots") or {})
            state_status = "collecting"

        collected_slots = dict(turn_context.get("collected_slots") or {})
        collected_slots.update(
            {
                "procedure_type": (analysis.get("procedure") or {}).get("procedure_type"),
                "risk_level": decision.get("risk_level"),
                "service_flow_type": service_flow_type,
                "official_match_status": (analysis.get("official_asset_match") or {}).get("match_status"),
            }
        )
        return self.repo.upsert_conversation_state(
            {
                "session_id": session_id,
                "current_intent": service_flow_type,
                "missing_slots": missing_slots,
                "collected_slots": collected_slots,
                "next_question": next_question,
                "state_status": state_status,
            }
        )

    @staticmethod
    def recommended_guide_id(analysis: dict[str, Any]) -> Any:
        official_content = ((analysis.get("chatbot_response") or {}).get("official_content") or {})
        return official_content.get("guide_id")

    @staticmethod
    def safety_reason(analysis: dict[str, Any]) -> str | None:
        decision = analysis.get("decision_result") or {}
        if decision.get("service_flow_type") != "expert_as":
            return None
        if decision.get("blocked_reason"):
            return decision["blocked_reason"]
        reasons = decision.get("reasons") or []
        return "; ".join(str(reason) for reason in reasons) if reasons else "Expert A/S routing required."

    @staticmethod
    def build_ai_message(
        analysis: dict[str, Any],
        guide_options: dict[str, Any] | None,
        state: dict[str, Any] | None,
        llm_assist: dict[str, Any] | None = None,
    ) -> dict[str, str]:
        decision = analysis.get("decision_result") or {}
        service_flow_type = decision.get("service_flow_type")
        response_text = (llm_assist or {}).get("response_text")
        if state and state.get("state_status") == "collecting":
            return {
                "message_type": "text",
                "message_content": response_text or state.get("next_question") or "Please share one more detail about the symptom.",
            }
        if service_flow_type == "expert_as":
            return {
                "message_type": "safety_card",
                "message_content": response_text
                or "This looks high risk, so AR self-guidance is blocked. Please connect to official A/S or a service center.",
            }
        if guide_options:
            return {
                "message_type": "guide_card",
                "message_content": response_text or "Official Manual Guide and AR Guide options are ready for this request.",
            }
        return {
            "message_type": "text",
            "message_content": response_text or "I checked the request, but official guide options are not ready for safe self-guidance.",
        }
