from __future__ import annotations

from copy import deepcopy
from typing import Any


DECISION_ENGINE_V2_INPUT_SCHEMA: dict[str, Any] = {
    "schema_version": "decision_engine_v2_input_v1",
    "fields": {
        "customer_message": "Original customer inquiry text.",
        "collected_slots": "ConversationState slots collected across turns.",
        "llm_assist": "Non-authoritative LLMService assistance.",
        "rag_evidence": "Official RAG evidence bundle, if searched.",
        "smart_diagnosis": "ThinQ or smart diagnosis context.",
        "usage_log": "Device usage and care trigger context.",
        "environment": "Environment observation/context.",
        "official_asset_match": "Strict official source match result.",
    },
}


DECISION_ENGINE_V2_OUTPUT_SCHEMA: dict[str, Any] = {
    "schema_version": "decision_engine_v2_output_v1",
    "fields": {
        "service_flow_type": "self_care, self_as, or expert_as.",
        "intent_type": "care, self_check, high_risk, or related intent label.",
        "risk_level": "low, medium, high, or unknown.",
        "decision_action": "Next backend action.",
        "ar_guide_allowed": "Whether AR guide creation may proceed.",
        "blocked_reason": "Reason AR/self-guidance is blocked, if any.",
        "allowed_actions": "Actions allowed for the user/UI.",
        "forbidden_actions": "Actions blocked by safety policy.",
        "evidence_refs": "Official asset/chunk/video references used by the decision.",
        "procedure_type": "Resolved care/self-check procedure type.",
    },
}


HIGH_RISK_SIGNALS = {"burning_smell", "smoke", "spark", "electric_shock", "gas_leak"}

BASE_FORBIDDEN_ACTIONS = {
    "open_internal_cover",
    "touch_pcb",
    "repair_wiring",
    "inspect_compressor",
    "check_refrigerant",
    "internal_disassembly",
    "spray_water_inside_unit",
}

POWER_FORBIDDEN_ACTIONS = BASE_FORBIDDEN_ACTIONS | {
    "touch_damaged_cord",
    "touch_wet_outlet",
    "repeat_breaker_reset",
}


class DecisionEngineV2:
    """Rule/RAG/safety combiner that wraps the v1 rule engine result.

    V2 does not use the LLM as the final authority. It consumes LLM assistance as
    context only, then applies deterministic safety and official-evidence gates.
    """

    input_schema = DECISION_ENGINE_V2_INPUT_SCHEMA
    output_schema = DECISION_ENGINE_V2_OUTPUT_SCHEMA

    def build_input(
        self,
        analysis: dict[str, Any],
        *,
        customer_message: str,
        collected_slots: dict[str, Any] | None = None,
        llm_assist: dict[str, Any] | None = None,
        rag_evidence: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        context = analysis.get("context") or {}
        return {
            "schema_version": self.input_schema["schema_version"],
            "customer_message": customer_message,
            "collected_slots": collected_slots or {},
            "llm_assist": llm_assist or {},
            "rag_evidence": rag_evidence if rag_evidence is not None else analysis.get("rag_evidence"),
            "smart_diagnosis": context.get("smart_diagnosis"),
            "usage_log": context.get("usage_log"),
            "environment": context.get("environment"),
            "official_asset_match": analysis.get("official_asset_match") or {},
            "v1_decision_result": analysis.get("decision_result") or {},
            "v1_intent": analysis.get("intent") or {},
            "v1_procedure": analysis.get("procedure") or {},
        }

    def evaluate(self, decision_input: dict[str, Any]) -> dict[str, Any]:
        v1_decision = deepcopy(decision_input.get("v1_decision_result") or {})
        v1_intent = decision_input.get("v1_intent") or {}
        v1_procedure = decision_input.get("v1_procedure") or {}
        official_match = decision_input.get("official_asset_match") or {}
        rag_evidence = decision_input.get("rag_evidence")
        slots = decision_input.get("collected_slots") or {}
        diagnosis = decision_input.get("smart_diagnosis") or {}

        procedure_type = v1_procedure.get("procedure_type") or slots.get("procedure_type")
        intent_type = v1_intent.get("intent_type") or "self_check"
        service_flow_type = v1_decision.get("service_flow_type") or v1_intent.get("service_flow_type") or "self_as"
        risk_level = v1_decision.get("risk_level") or "unknown"

        output = {
            "schema_version": self.output_schema["schema_version"],
            "source_engine": "decision_engine_v2_rule_safety_rag",
            "fallback_engine": "v1_rule_engine",
            "service_flow_type": service_flow_type,
            "intent_type": intent_type,
            "risk_level": risk_level,
            "decision_action": v1_decision.get("decision_action") or "prepare_ar_guide_session",
            "ar_guide_allowed": bool(v1_decision.get("ar_guide_allowed")),
            "generation_allowed": bool(v1_decision.get("generation_allowed")),
            "blocked_reason": v1_decision.get("blocked_reason"),
            "allowed_actions": self.allowed_actions(service_flow_type, procedure_type),
            "forbidden_actions": self.forbidden_actions(service_flow_type, procedure_type, official_match),
            "evidence_refs": self.evidence_refs(official_match, rag_evidence),
            "procedure_type": procedure_type,
            "ar_scope": v1_decision.get("ar_scope"),
            "reasons": list(v1_decision.get("reasons") or []),
            "v1_decision_action": v1_decision.get("decision_action"),
            "input_schema_version": decision_input.get("schema_version"),
            "llm_used_as_final_authority": False,
        }

        high_risk_reason = self.high_risk_reason(slots, diagnosis, v1_decision)
        if high_risk_reason:
            output.update(
                {
                    "service_flow_type": "expert_as",
                    "intent_type": "high_risk",
                    "risk_level": "high",
                    "decision_action": "route_to_service",
                    "ar_guide_allowed": False,
                    "generation_allowed": False,
                    "blocked_reason": high_risk_reason,
                    "allowed_actions": ["stop_use", "connect_official_as", "show_safety_card"],
                    "forbidden_actions": sorted(BASE_FORBIDDEN_ACTIONS | {"ar_self_guidance"}),
                    "ar_scope": None,
                }
            )
            output["reasons"] = self.append_reason(output["reasons"], high_risk_reason)
            return output

        official_block = self.official_block_reason(official_match)
        if official_block:
            output.update(
                {
                    "risk_level": "unknown",
                    "decision_action": "official_match_review_needed",
                    "ar_guide_allowed": False,
                    "generation_allowed": False,
                    "blocked_reason": official_block,
                    "allowed_actions": ["show_manual_or_service_message", "request_official_review"],
                    "ar_scope": None,
                }
            )
            output["reasons"] = self.append_reason(output["reasons"], official_block)
            return output

        rag_block = self.rag_block_reason(rag_evidence)
        if rag_block:
            output.update(
                {
                    "decision_action": "official_evidence_required",
                    "ar_guide_allowed": False,
                    "generation_allowed": False,
                    "blocked_reason": rag_block,
                    "allowed_actions": ["show_manual_or_service_message", "retry_rag_search"],
                    "ar_scope": None,
                }
            )
            output["reasons"] = self.append_reason(output["reasons"], rag_block)
            return output

        if procedure_type == "power_troubleshooting" or output.get("ar_scope") == "external_safe_check_only":
            output.update(
                {
                    "service_flow_type": "self_as",
                    "intent_type": "self_check",
                    "risk_level": "medium",
                    "decision_action": "prepare_limited_ar_safe_check",
                    "ar_guide_allowed": True,
                    "generation_allowed": True,
                    "ar_scope": "external_safe_check_only",
                    "allowed_actions": [
                        "external_power_indicator_check",
                        "remote_battery_check",
                        "safe_plug_connection_check",
                        "single_breaker_reset_if_safe",
                        "connect_official_as_if_not_restored",
                    ],
                    "forbidden_actions": sorted(POWER_FORBIDDEN_ACTIONS),
                }
            )
            output["reasons"] = self.append_reason(
                output["reasons"],
                "Power troubleshooting is limited to external safe-check actions.",
            )
            return output

        if service_flow_type in {"self_care", "self_as"}:
            output.update(
                {
                    "decision_action": v1_decision.get("decision_action") or "prepare_ar_guide_session",
                    "ar_guide_allowed": bool(v1_decision.get("ar_guide_allowed", True)),
                    "generation_allowed": bool(v1_decision.get("generation_allowed", True)),
                    "blocked_reason": None,
                }
            )
        return output

    def apply_to_analysis(
        self,
        analysis: dict[str, Any],
        *,
        customer_message: str,
        collected_slots: dict[str, Any] | None = None,
        llm_assist: dict[str, Any] | None = None,
        rag_evidence: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        decision_input = self.build_input(
            analysis,
            customer_message=customer_message,
            collected_slots=collected_slots,
            llm_assist=llm_assist,
            rag_evidence=rag_evidence,
        )
        output = self.evaluate(decision_input)
        merged_decision = deepcopy(analysis.get("decision_result") or {})
        for key in [
            "service_flow_type",
            "risk_level",
            "decision_action",
            "ar_guide_allowed",
            "generation_allowed",
            "blocked_reason",
            "allowed_actions",
            "forbidden_actions",
            "evidence_refs",
            "ar_scope",
            "reasons",
        ]:
            if key in output and output[key] is not None:
                merged_decision[key] = output[key]
        if output.get("procedure_type"):
            analysis.setdefault("procedure", {})["procedure_type"] = output["procedure_type"]
        analysis["decision_result"] = merged_decision
        analysis["decision_engine_v2_input"] = decision_input
        analysis["decision_v2"] = output
        return analysis

    @staticmethod
    def high_risk_reason(
        slots: dict[str, Any],
        diagnosis: dict[str, Any],
        v1_decision: dict[str, Any],
    ) -> str | None:
        if v1_decision.get("service_flow_type") == "expert_as" or v1_decision.get("risk_level") == "high":
            return "High-risk symptom or smart diagnosis signal detected."
        if slots.get("risk_signal") in HIGH_RISK_SIGNALS:
            return f"High-risk slot detected: {slots['risk_signal']}."
        if diagnosis.get("severity") == "high":
            return "High-risk smart diagnosis severity detected."
        return None

    @staticmethod
    def official_block_reason(official_match: dict[str, Any]) -> str | None:
        if official_match and official_match.get("match_status") != "verified":
            return "Official asset match is not verified."
        return None

    @staticmethod
    def rag_block_reason(rag_evidence: dict[str, Any] | None) -> str | None:
        if rag_evidence is None:
            return None
        if rag_evidence.get("skipped"):
            return f"RAG evidence search skipped: {rag_evidence.get('reason') or 'unknown reason'}."
        if int(rag_evidence.get("result_count") or 0) <= 0:
            return "Official RAG evidence is required before AR guidance."
        if rag_evidence.get("ar_guide_blocked"):
            return rag_evidence.get("blocked_reason") or "RAG evidence blocked AR guidance."
        return None

    @staticmethod
    def evidence_refs(
        official_match: dict[str, Any],
        rag_evidence: dict[str, Any] | None,
    ) -> list[dict[str, Any]]:
        refs: list[dict[str, Any]] = []
        for asset in official_match.get("official_assets") or []:
            refs.append(
                {
                    "source": "official_asset",
                    "asset_id": asset.get("asset_id"),
                    "title": asset.get("title"),
                    "source_url": asset.get("source_url"),
                }
            )
        for item in (rag_evidence or {}).get("results") or []:
            refs.append(
                {
                    "source": "rag_evidence",
                    "asset_id": item.get("asset_id"),
                    "chunk_id": item.get("chunk_id"),
                    "title": item.get("title") or item.get("chunk_title"),
                    "source_url": item.get("source_url"),
                    "procedure_type": item.get("procedure_type"),
                }
            )
        seen = set()
        unique_refs = []
        for ref in refs:
            key = (ref.get("source"), ref.get("asset_id"), ref.get("chunk_id"), ref.get("source_url"))
            if key in seen:
                continue
            seen.add(key)
            unique_refs.append(ref)
        return unique_refs

    @staticmethod
    def allowed_actions(service_flow_type: str, procedure_type: str | None) -> list[str]:
        if service_flow_type == "expert_as":
            return ["stop_use", "connect_official_as", "show_safety_card"]
        if procedure_type == "power_troubleshooting":
            return [
                "external_power_indicator_check",
                "remote_battery_check",
                "safe_plug_connection_check",
                "single_breaker_reset_if_safe",
            ]
        if procedure_type == "remote_operation":
            return ["show_official_content", "show_official_youtube", "manual_or_service_guidance_only"]
        if service_flow_type == "self_care":
            return ["show_official_content", "start_user_accessible_care_guide", "save_self_management_history"]
        return ["show_official_content", "start_external_self_check", "connect_official_as_if_unresolved"]

    @staticmethod
    def forbidden_actions(
        service_flow_type: str,
        procedure_type: str | None,
        official_match: dict[str, Any],
    ) -> list[str]:
        forbidden = set(official_match.get("forbidden_actions") or []) | set(BASE_FORBIDDEN_ACTIONS)
        if service_flow_type == "expert_as":
            forbidden.add("ar_self_guidance")
        if procedure_type == "power_troubleshooting":
            forbidden |= POWER_FORBIDDEN_ACTIONS
        return sorted(forbidden)

    @staticmethod
    def append_reason(reasons: list[str], reason: str) -> list[str]:
        if reason and reason not in reasons:
            reasons.append(reason)
        return reasons
