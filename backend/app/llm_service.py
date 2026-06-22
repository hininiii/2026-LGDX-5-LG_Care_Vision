from __future__ import annotations

import os
import re
from typing import Any, Protocol


LLM_PROMPT_SCHEMA: dict[str, Any] = {
    "schema_version": "llm_assist_prompt_v1",
    "input": {
        "customer_message": "Original customer message, never rewritten as official evidence.",
        "conversation_slots": "Collected ConversationState slots.",
        "decision_result": "Rule/RAG/safety decision result, read-only for the LLM.",
        "guide_options": "Official guide options already approved by backend gates.",
        "language_code": "Requested response language.",
    },
    "allowed_tasks": [
        "summarize_customer_inquiry",
        "suggest_slot_candidates",
        "draft_customer_response",
        "transform_safety_template_copy",
    ],
    "forbidden_tasks": [
        "final_ar_permission_decision",
        "official_evidence_verification",
        "high_risk_override",
        "invent_unverified_repair_steps",
    ],
}


LLM_OUTPUT_SCHEMA: dict[str, Any] = {
    "schema_version": "llm_assist_output_v1",
    "fields": {
        "provider": "mock, openai, or another configured adapter.",
        "model": "Adapter model name.",
        "summary": "Short customer inquiry summary.",
        "slot_candidates": "Non-authoritative slot suggestions.",
        "response_text": "Customer-facing response draft.",
        "safety_copy": "Safety template copy transformed for the user.",
        "decision_authority": "Explicit statement that final gating is not done by the LLM.",
    },
}


class LLMService(Protocol):
    provider: str
    model_name: str

    def assist_chat_turn(self, prompt: dict[str, Any]) -> dict[str, Any]:
        """Return non-authoritative LLM assistance for one chat turn."""


class LLMServiceMock:
    provider = "mock_rule_adapter"
    model_name = "careshot-llm-mock-v1"

    def assist_chat_turn(self, prompt: dict[str, Any]) -> dict[str, Any]:
        payload = prompt.get("payload") or {}
        turn_context = prompt.get("turn_context") or {}
        analysis = prompt.get("analysis") or {}
        guide_options = prompt.get("guide_options")
        conversation_state = prompt.get("conversation_state") or {}
        language_code = payload.get("language_code") or "en"

        message = turn_context.get("original_message") or payload.get("message") or ""
        slots = turn_context.get("collected_slots") or {}
        decision = analysis.get("decision_result") or {}
        procedure = analysis.get("procedure") or {}

        slot_candidates = self.extract_slot_candidates(message, slots)
        safety_copy = self.render_safety_copy(decision, procedure, language_code)
        response_text = self.generate_response_text(
            decision=decision,
            procedure=procedure,
            guide_options=guide_options,
            conversation_state=conversation_state,
            safety_copy=safety_copy,
            language_code=language_code,
        )

        return {
            "provider": self.provider,
            "model": self.model_name,
            "mode": "deterministic_mock",
            "prompt_schema_version": LLM_PROMPT_SCHEMA["schema_version"],
            "output_schema_version": LLM_OUTPUT_SCHEMA["schema_version"],
            "prompt_contract": LLM_PROMPT_SCHEMA,
            "output_contract": LLM_OUTPUT_SCHEMA,
            "summary": self.summarize(message, slots, procedure),
            "slot_candidates": slot_candidates,
            "response_text": response_text,
            "safety_copy": safety_copy,
            "language_code": language_code,
            "decision_authority": {
                "final_ar_permission": "Rule/Safety Guard + RAG official evidence + DecisionEngine",
                "llm_can_override_safety": False,
                "llm_can_verify_official_evidence": False,
            },
        }

    def summarize(self, message: str, slots: dict[str, Any], procedure: dict[str, Any]) -> str:
        symptom = slots.get("symptom_type") or procedure.get("procedure_type") or "general inquiry"
        product = slots.get("product_family") or "registered appliance"
        risk = slots.get("risk_signal") or "unknown risk signal"
        cleaned = self.compact(message)
        return f"{product}: {symptom}; risk={risk}; customer='{cleaned}'."

    def extract_slot_candidates(self, message: str, slots: dict[str, Any]) -> dict[str, dict[str, Any]]:
        normalized = self.normalize(message)
        candidates: dict[str, dict[str, Any]] = {}
        for slot_name, value in slots.items():
            if value not in (None, "", [], {}):
                candidates[slot_name] = {
                    "value": value,
                    "confidence": 0.95,
                    "source": "conversation_state",
                }

        keyword_candidates = {
            "odor": ["smell", "odor", "bad smell", "냄새", "악취"],
            "water_leak": ["water", "leak", "drip", "dripping", "물이", "누수"],
            "weak_airflow": ["weak airflow", "not cooling", "바람", "안 시원"],
            "noise": ["noise", "vibration", "sound", "소리", "진동"],
            "power_issue": ["power", "turns off", "전원", "꺼져"],
            "filter_care": ["filter", "clean", "필터", "청소"],
        }
        if "symptom_type" not in candidates:
            for value, patterns in keyword_candidates.items():
                if any(pattern in normalized for pattern in patterns):
                    candidates["symptom_type"] = {
                        "value": value,
                        "confidence": 0.7,
                        "source": "mock_keyword_hint",
                    }
                    break

        if "risk_signal" not in candidates:
            if any(pattern in normalized for pattern in ["smoke", "연기"]):
                candidates["risk_signal"] = {"value": "smoke", "confidence": 0.75, "source": "mock_keyword_hint"}
            elif any(pattern in normalized for pattern in ["burning", "타는", "탄내"]):
                candidates["risk_signal"] = {
                    "value": "burning_smell",
                    "confidence": 0.75,
                    "source": "mock_keyword_hint",
                }
            elif any(pattern in normalized for pattern in ["no ", "not ", "없", "아니"]):
                candidates["risk_signal"] = {"value": "none", "confidence": 0.65, "source": "mock_keyword_hint"}

        return candidates

    def generate_response_text(
        self,
        decision: dict[str, Any],
        procedure: dict[str, Any],
        guide_options: dict[str, Any] | None,
        conversation_state: dict[str, Any],
        safety_copy: str,
        language_code: str,
    ) -> str:
        if conversation_state.get("state_status") == "collecting":
            return conversation_state.get("next_question") or self.translate(
                "Please share one more detail before I guide you.",
                language_code,
            )
        if decision.get("service_flow_type") == "expert_as":
            return safety_copy
        if guide_options:
            procedure_type = procedure.get("procedure_type") or guide_options.get("procedure_type") or "this request"
            return self.translate(
                f"Official guide options are ready for {procedure_type}. I will only show steps allowed by safety rules and official evidence.",
                language_code,
            )
        return self.translate(
            "I checked the request, but safe official guide options are not ready yet.",
            language_code,
        )

    def render_safety_copy(
        self,
        decision: dict[str, Any],
        procedure: dict[str, Any],
        language_code: str,
    ) -> str:
        service_flow = decision.get("service_flow_type")
        procedure_type = procedure.get("procedure_type")
        if service_flow == "expert_as":
            return self.translate(
                "This may be high risk. Stop using the appliance and connect to official A/S. AR self-guidance is blocked.",
                language_code,
            )
        if procedure_type == "power_troubleshooting":
            return self.translate(
                "Only external safe-check steps are allowed. Do not open covers, wiring, PCB, compressor, or refrigerant parts.",
                language_code,
            )
        return self.translate(
            "Only user-accessible steps backed by official evidence are allowed.",
            language_code,
        )

    @staticmethod
    def translate(text: str, language_code: str) -> str:
        return text

    @staticmethod
    def compact(message: str) -> str:
        return re.sub(r"\s+", " ", str(message or "")).strip()[:160]

    @staticmethod
    def normalize(message: str) -> str:
        return re.sub(r"\s+", " ", str(message or "").lower()).strip()


class ExternalLLMAdapter:
    """Interface-compatible placeholder for OpenAI or another external LLM provider."""

    provider = "external_adapter"

    def __init__(self, model_name: str | None = None) -> None:
        self.model_name = model_name or os.environ.get("CARESHOT_LLM_MODEL") or "external-llm"

    def assist_chat_turn(self, prompt: dict[str, Any]) -> dict[str, Any]:
        raise RuntimeError(
            "External LLM adapter is intentionally not enabled in this MVP. "
            "Use CARESHOT_LLM_PROVIDER=mock until API credentials and safety review are configured."
        )


def create_llm_service(provider: str | None = None) -> LLMService:
    selected = (provider or os.environ.get("CARESHOT_LLM_PROVIDER") or "mock").strip().lower()
    if selected in {"mock", "local_rule", "rule", "disabled"}:
        return LLMServiceMock()
    if selected in {"openai", "external"}:
        return ExternalLLMAdapter()
    return LLMServiceMock()
