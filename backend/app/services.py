from __future__ import annotations

import os
import re
from datetime import datetime, timezone
from functools import lru_cache
from typing import Any
from uuid import uuid4

from .path_setup import configure_import_paths


configure_import_paths()

from ai_decision_engine import CareShotARDecisionEngine  # noqa: E402
from ar_guide_template_selector import ARGuideTemplateSelector  # noqa: E402
from rag_service import RAGService  # noqa: E402
from seed_ar_mock_db import DB_PATH, main as seed_db  # noqa: E402

from .adapters import EnvironmentDataAdapter
from .chatbot_engine import ChatbotEngine
from .engines import CareRiskScoreEngine, DecisionEngineV2, PreventiveCareRecommendationEngine
from .evaluation_service import EvaluationService
from .llm_service import create_llm_service
from .repositories import CareShotRepository, PostgreSQLRepositoryRegistry
from .tts_service import generate_google_tts_mp3_asset, google_tts_enabled, google_tts_pregenerate_enabled


PART_LABELS = {
    "power_area": "전원 영역",
    "front_cover": "전면 커버",
    "front_filter": "필터",
    "air_outlet": "송풍구",
    "internal_electrical_area": "내부 전기부",
}

ACTION_COPY = {
    "highlight_and_confirm": {
        "title": "전원을 먼저 꺼주세요",
        "instruction": "작업 전 에어컨 전원이 꺼져 있는지 확인합니다.",
        "safety": "전원이 켜진 상태에서는 커버를 열지 마세요.",
    },
    "open_direction": {
        "title": "전면 커버를 위로 여세요",
        "instruction": "표시된 전면 커버 아래쪽을 잡고 천천히 위로 들어 올립니다.",
        "safety": "무리하게 힘을 주지 말고 양손으로 천천히 여세요.",
    },
    "pull_direction": {
        "title": "필터를 앞으로 빼세요",
        "instruction": "화살표 방향으로 필터 손잡이를 잡고 부드럽게 분리합니다.",
        "safety": "필터 안쪽의 내부 부품은 만지지 마세요.",
    },
    "bottom_sheet_instruction": {
        "title": "필터를 세척하고 말리세요",
        "instruction": "먼지를 제거한 뒤 물로 가볍게 헹구고 그늘에서 완전히 말립니다.",
        "safety": "젖은 필터를 바로 장착하지 마세요.",
    },
    "surface_check": {
        "title": "송풍구 표면을 닦으세요",
        "instruction": "송풍구 표면의 먼지만 부드러운 천으로 닦습니다.",
        "safety": "송풍구 안쪽으로 물을 뿌리거나 도구를 넣지 마세요.",
    },
    "insert_direction": {
        "title": "필터를 다시 넣으세요",
        "instruction": "완전히 마른 필터를 원래 방향으로 다시 끼웁니다.",
        "safety": "필터 방향이 맞는지 확인하세요.",
    },
    "close_and_complete": {
        "title": "커버를 닫고 완료하세요",
        "instruction": "전면 커버가 완전히 닫혔는지 확인하면 관리가 완료됩니다.",
        "safety": "커버가 들떠 있으면 다시 눌러 고정하세요.",
    },
    "inspect_filter": {
        "title": "필터 상태를 확인하세요",
        "instruction": "필터에 먼지가 많으면 분리 후 청소합니다.",
        "safety": "필터 뒤쪽의 내부 부품은 만지지 마세요.",
    },
    "inspect_surface": {
        "title": "송풍구 막힘을 확인하세요",
        "instruction": "송풍구 표면에 먼지나 막힘이 있는지 확인합니다.",
        "safety": "깊은 내부 점검은 A/S로 연결하세요.",
    },
    "close_and_check_result": {
        "title": "다시 조립하고 증상을 확인하세요",
        "instruction": "필터와 커버를 원위치한 뒤 증상이 해결됐는지 확인합니다.",
        "safety": "증상이 계속되면 A/S 접수로 이동하세요.",
    },
}


AIRCON_DYNAMIC_MANUAL_GUIDES = {
    "power_troubleshooting": {
        "service_flows": {"self_as"},
        "title": "Air Conditioner No Power Safe-Check Guide",
        "summary": "External-only checklist for no power or sudden power-off symptoms before requesting service.",
        "safety_scope": "external_safe_check_only",
        "steps": [
            "Stop using the air conditioner immediately if there is smoke, a burning smell, sparks, heat, water near power, or repeated breaker trips.",
            "Turn the unit off from the remote controller or power button.",
            "Check whether the remote/controller display works and replace batteries if the remote is unresponsive.",
            "Check whether the indoor unit power indicator or display is on.",
            "If the plug or wall outlet is safely accessible, confirm the plug is firmly connected. Do not touch damaged cords, loose sockets, or wet outlets.",
            "Check whether the home circuit breaker is tripped. Reset only once if it is safe; if it trips again, stop and request expert A/S.",
            "Do not open the indoor unit cover, wiring area, PCB, compressor area, refrigerant line, or any internal electrical part.",
            "If power does not return or the unit turns off again, request expert A/S.",
        ],
        "stop_conditions": [
            "smoke",
            "burning_smell",
            "spark",
            "wet_outlet",
            "damaged_cord",
            "repeated_breaker_trip",
            "power_not_restored",
        ],
    },
    "no_cooling_self_check": {
        "service_flows": {"self_as"},
        "title": "Air Conditioner Weak Cooling Self-Check Guide",
        "summary": "Safe external checks for weak cooling before requesting service.",
        "safety_scope": "external_self_check_only",
        "steps": [
            "Confirm the selected mode is Cool and the set temperature is lower than the room temperature.",
            "Check whether doors, windows, or direct sunlight are increasing the room heat load.",
            "Check whether the air inlet or outlet is blocked by curtains, furniture, or dust.",
            "Inspect the visible filter area if it is user-accessible; clean the filter only if the model guide allows it.",
            "Run the unit for several minutes and check whether airflow improves.",
            "Do not open internal covers, refrigerant lines, fan motors, PCB, or compressor parts.",
            "If cooling does not improve, request expert A/S.",
        ],
        "stop_conditions": ["ice_on_unit", "water_leak", "burning_smell", "cooling_not_restored"],
    },
    "odor_self_check": {
        "service_flows": {"self_as"},
        "title": "Air Conditioner Odor Self-Check Guide",
        "summary": "Safe user-level checks for odor from the air conditioner.",
        "safety_scope": "external_self_check_only",
        "steps": [
            "Stop using the air conditioner and request expert A/S if the odor smells like burning, gas, or chemicals.",
            "Check whether the room source, drain smell, or nearby objects may be causing the odor.",
            "Check the visible filter area if it is user-accessible; clean the filter only if the model guide allows it.",
            "Use fan or auto-clean mode if the model officially supports it.",
            "Ventilate the room and check whether the odor decreases after the unit dries.",
            "Do not spray water or chemicals inside the unit and do not open internal covers.",
            "If odor continues, request expert A/S.",
        ],
        "stop_conditions": ["burning_smell", "gas_smell", "chemical_smell", "odor_persists"],
    },
    "water_leak_monsoon": {
        "service_flows": {"self_as"},
        "title": "Air Conditioner Water Leak Self-Check Guide",
        "summary": "Safe external checks for dripping or condensation symptoms.",
        "safety_scope": "external_self_check_only",
        "steps": [
            "Turn the unit off if water is near the power outlet, plug, or electrical area.",
            "Check whether doors or windows are open and humid outdoor air is entering the room.",
            "Check whether the indoor unit air outlet has condensation during high humidity.",
            "Check whether the visible drain hose route is bent, blocked, or tilted upward if it is safely accessible.",
            "Wipe visible water around the unit and monitor whether dripping continues.",
            "Do not open internal covers, touch wiring, or dismantle the drain pan.",
            "If dripping continues or water is near electricity, request expert A/S.",
        ],
        "stop_conditions": ["water_near_power", "continuous_dripping", "internal_leak_suspected"],
    },
    "noise_self_check": {
        "service_flows": {"self_as"},
        "title": "Air Conditioner Noise Self-Check Guide",
        "summary": "Safe external checks for vibration or unusual noise.",
        "safety_scope": "external_self_check_only",
        "steps": [
            "Stop the unit and request expert A/S if the noise is loud, metallic, burning-related, or accompanied by vibration of the wall.",
            "Check whether the front cover or visible panel is fully closed.",
            "Check whether nearby furniture, curtains, or loose objects are vibrating from airflow.",
            "Check whether the unit is mounted level from a safe viewing distance.",
            "Restart the unit at a lower fan speed and check whether the noise changes.",
            "Do not open internal covers, remove fan parts, or touch the motor area.",
            "If the noise continues, request expert A/S.",
        ],
        "stop_conditions": ["metallic_noise", "burning_smell", "strong_vibration", "noise_persists"],
    },
    "remote_operation": {
        "service_flows": {"self_care", "self_as"},
        "title": "Air Conditioner Remote Operation Guide",
        "summary": "Step-by-step guide for safe remote controller operation.",
        "safety_scope": "user_operation_only",
        "steps": [
            "Check whether the remote display is on and replace batteries if it is blank.",
            "Point the remote controller at the indoor unit receiver.",
            "Select the required mode such as Cool, Fan, Dry, or Auto according to the model guide.",
            "Adjust temperature, fan speed, and timer one setting at a time.",
            "Wait for the indoor unit to respond before pressing another button.",
            "Do not open the remote or indoor unit if the controls do not respond.",
            "If the remote or receiver does not respond after battery replacement, request support.",
        ],
        "stop_conditions": ["remote_not_responding", "receiver_not_responding"],
    },
    "auto_clean": {
        "service_flows": {"self_care"},
        "title": "Air Conditioner Auto Clean Guide",
        "summary": "Official-feature-oriented guide for running auto clean or fan dry mode.",
        "safety_scope": "user_operation_only",
        "steps": [
            "Check whether the model supports Auto Clean, Freeze Cleaning, or fan dry mode.",
            "Use the remote controller or app menu to select the supported cleaning function.",
            "Keep the unit powered and allow the cycle to finish without opening covers.",
            "Ventilate the room if humidity or odor remains after the cycle.",
            "Clean the user-accessible filter separately only if the model guide allows it.",
            "Do not spray water or chemicals inside the unit.",
            "If odor or moisture continues, request support.",
        ],
        "stop_conditions": ["unsupported_feature", "odor_persists", "moisture_persists"],
    },
}

RAG_PROCEDURE_ALIASES = {
    "odor_self_check": "odor_mold_care",
}


class CareShotBackendService:
    """FastAPI dependency root for RAG, decision, and AR guide services."""

    def __init__(self) -> None:
        database_url = os.environ.get("CARESHOT_DATABASE_URL")
        if not database_url and not DB_PATH.exists():
            seed_db()
        self.repo = PostgreSQLRepositoryRegistry(database_url) if database_url else CareShotRepository()
        self.decision_engine = CareShotARDecisionEngine(self.repo)
        self.decision_engine_v2 = DecisionEngineV2()
        self.ar_selector = ARGuideTemplateSelector()
        self.rag_service = RAGService(self.repo)
        self.llm_service = create_llm_service()
        self.environment_adapter = EnvironmentDataAdapter(self.repo)
        self.care_risk_engine = CareRiskScoreEngine()
        self.preventive_recommendation_engine = PreventiveCareRecommendationEngine()
        self.chatbot_engine = ChatbotEngine(self)
        self.evaluation_service = EvaluationService(self)

    def health(self) -> dict[str, Any]:
        return {"ok": True, "service": "CareShot AR Guide Engine", "version": "0.2-fastapi"}

    def register_frontend_user(self, payload: dict[str, Any]) -> dict[str, Any]:
        if not hasattr(self.repo, "register_user_with_demo_seed"):
            raise RuntimeError("User registration repository is not available")
        return self.repo.register_user_with_demo_seed(payload)

    def login_frontend_user(self, payload: dict[str, Any]) -> dict[str, Any]:
        user_email = str(payload.get("user_email") or payload.get("email") or "").strip().lower()
        password = str(payload.get("password") or "")
        if not user_email or not password:
            raise ValueError("user_email and password are required")
        if not hasattr(self.repo, "verify_user_login"):
            raise RuntimeError("User login repository is not available")
        profile = self.repo.verify_user_login(user_email, password)
        if not profile:
            raise PermissionError("invalid email or password")
        return profile

    def update_frontend_user(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self.register_frontend_user(payload)

    def demo_context(self, user_id: str = "U001", device_id: str = "D001") -> dict[str, Any]:
        device = (
            self.repo.get_device_context_for_user(user_id, device_id)
            if hasattr(self.repo, "get_device_context_for_user")
            else self.repo.get_device_context(device_id)
        )
        environment = None
        if device:
            environment = self.repo.get_current_environment_observation(
                region=device.get("region") or "Gujarat",
                city=device.get("city"),
            )
        return {
            "user": self.repo.get_user_profile(user_id),
            "device": device,
            "usage_log": (
                self.repo.get_usage_log_for_user(user_id, device_id)
                if hasattr(self.repo, "get_usage_log_for_user")
                else self.repo.get_usage_log(device_id)
            ),
            "smart_diagnosis": (
                self.repo.get_smart_diagnosis_for_user(user_id, device_id)
                if hasattr(self.repo, "get_smart_diagnosis_for_user")
                else self.repo.get_smart_diagnosis(device_id)
            ),
            "environment_observation": environment,
        }

    def analyze(self, payload: dict[str, Any]) -> dict[str, Any]:
        analysis = self.decision_engine.analyze(
            user_id=payload.get("user_id", "U001"),
            device_id=payload.get("device_id", "D001"),
            message=payload.get("message", "Please help me clean the AC filter."),
            request_id=payload.get("request_id"),
        )
        if payload.get("include_rag_evidence", True):
            analysis["rag_evidence"] = self.search_rag_for_analysis(payload, analysis)
        self.persist_decision_side_effects(payload, analysis)
        return analysis

    def process_chat_message(self, payload: dict[str, Any]) -> dict[str, Any]:
        if not hasattr(self, "chatbot_engine"):
            self.chatbot_engine = ChatbotEngine(self)
        return self.chatbot_engine.handle_message(payload)

    def run_intent_risk_evaluation(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        payload = payload or {}
        if not hasattr(self, "evaluation_service"):
            self.evaluation_service = EvaluationService(self)
        return self.evaluation_service.run_intent_risk_evaluation(
            cases_path=payload.get("cases_path") or payload.get("casesPath") or payload.get("input_path") or payload.get("inputPath"),
            results_path=payload.get("results_path") or payload.get("resultsPath"),
            report_json_path=payload.get("report_json_path") or payload.get("reportJsonPath"),
            report_md_path=payload.get("report_md_path") or payload.get("reportMdPath"),
            report_date=payload.get("report_date") or payload.get("reportDate"),
            product_type=payload.get("product_type"),
            limit=payload.get("limit"),
            run_id=payload.get("run_id"),
        )

    def persist_decision_side_effects(self, payload: dict[str, Any], analysis: dict[str, Any]) -> None:
        decision = analysis.get("decision_result") or {}
        user_id = payload.get("user_id", "U001")
        device_id = payload.get("device_id", "D001")

        if decision.get("decision_action") == "route_to_service":
            self.repo.create_service_route_log(
                {
                    "route_log_id": f"ROUTE_{uuid4().hex[:12].upper()}",
                    "session_id": payload.get("session_id"),
                    "user_id": user_id,
                    "device_id": device_id,
                    "route_type": "service_center_or_agent",
                    "reason": decision.get("blocked_reason") or "High risk request blocks AR guide.",
                    "status": "created",
                }
            )

    def search_rag(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self.rag_service.search(payload)

    def search_rag_for_analysis(self, payload: dict[str, Any], analysis: dict[str, Any]) -> dict[str, Any] | None:
        decision = analysis.get("decision_result") or {}
        if decision.get("decision_action") == "route_to_service":
            return {
                "skipped": True,
                "reason": "High-risk request is routed to service center before AR guide evidence search.",
            }

        device = (analysis.get("context") or {}).get("device") or {}
        procedure = analysis.get("procedure") or {}
        requested_procedure_type = procedure.get("procedure_type")
        rag_procedure_type = RAG_PROCEDURE_ALIASES.get(requested_procedure_type, requested_procedure_type)
        official_match = analysis.get("official_asset_match") or {}
        official_assets = official_match.get("official_assets") or []
        official_asset_ids = [asset.get("asset_id") for asset in official_assets if asset.get("asset_id")]

        if official_match.get("match_status") != "verified":
            return {
                "skipped": True,
                "reason": "Official asset strict matching failed; RAG evidence search is blocked.",
            }

        result = self.rag_service.search(
            {
                "session_id": payload.get("session_id"),
                "inquiry_id": payload.get("inquiry_id"),
                "ai_response_id": payload.get("ai_response_id"),
                "query": payload.get("message") or (analysis.get("input") or {}).get("message"),
                "product_type": device.get("product_type"),
                "model_name": device.get("model_name"),
                "procedure_type": rag_procedure_type,
                "requested_procedure_type": requested_procedure_type,
                "procedure_alias_used": rag_procedure_type if rag_procedure_type != requested_procedure_type else None,
                "language": "en",
                "official_asset_ids": official_asset_ids,
                "limit": int(payload.get("rag_limit") or 3),
            }
        )
        result["requested_procedure_type"] = requested_procedure_type
        if rag_procedure_type != requested_procedure_type:
            result["procedure_alias_used"] = rag_procedure_type
        return result

    def plan_from_analysis(self, analysis: dict[str, Any]) -> dict[str, Any]:
        plan_result = self.ar_selector.select_and_build(analysis)
        overlay_data = None
        overlay_build_warning = None
        if plan_result.get("ar_guide_plan"):
            try:
                overlay_data = self.build_overlay_data(analysis, plan_result["ar_guide_plan"])
            except ValueError as exc:
                overlay_build_warning = str(exc)
        return {
            "analysis": analysis,
            "ar_guide_plan_result": plan_result,
            "ar_overlay_data": overlay_data,
            "ar_overlay_build_warning": overlay_build_warning,
        }

    def build_overlay_data(self, analysis: dict[str, Any], ar_guide_plan: dict[str, Any]) -> dict[str, Any]:
        if ar_guide_plan.get("ar_scope") == "external_safe_check_only":
            return self.build_dynamic_safe_check_overlay_data(analysis, ar_guide_plan)

        product_model = analysis["context"].get("product_model")
        if not product_model:
            raise ValueError("Product model not found for AR guide.")

        structure_type = product_model["structure_type"]
        guide = self.pick_ar_guide(analysis, structure_type)
        guide_steps = self.repo.get_ar_guide_steps(guide["guide_id"])
        part_maps = self.repo.get_part_map(structure_type)
        reference_image = self.repo.get_reference_image(
            model_name=product_model.get("model_name"),
            structure_type=structure_type,
            image_role="open_cover_filter_visible",
        ) or self.repo.get_reference_image(structure_type=structure_type)
        part_map_version = None
        validations: list[dict[str, Any]] = []
        if reference_image:
            part_map_version = self.repo.get_part_map_version(
                reference_image_id=reference_image.get("reference_image_id"),
                structure_type=structure_type,
            )
            validations = self.repo.get_ar_overlay_validation_logs(
                reference_image_id=reference_image.get("reference_image_id"),
                part_map_version_id=(part_map_version or {}).get("part_map_version_id"),
                structure_type=structure_type,
            )
        template = self.repo.get_ar_guide_template(
            guide_id=guide["guide_id"],
            product_type=analysis["context"]["device"]["product_type"],
            procedure_type=analysis["procedure"]["procedure_type"],
            structure_type=structure_type,
        )
        part_lookup = {part["part_id"]: self.normalize_part(part) for part in part_maps}

        display_steps = []
        for step in guide_steps:
            target_part = step["target_part"]
            copy = ACTION_COPY.get(step["action_type"], {})
            display_instruction = copy.get("instruction") or step.get("instruction_text")
            display_steps.append(
                {
                    **step,
                    "display_title": copy.get("title") or f"{PART_LABELS.get(target_part, target_part)} 안내",
                    "display_instruction": display_instruction,
                    "display_safety": copy.get("safety") or step.get("safety_message"),
                    "target_part_map": part_lookup.get(target_part),
                    "next_button_label": "완료" if step["step_order"] == len(guide_steps) else "다음 단계",
                    **self.tts_fields_for_step(display_instruction),
                }
            )

        return {
            "product_model": product_model,
            "structure_type": self.repo.get_structure_type(structure_type),
            "reference_image": reference_image,
            "part_map_version": part_map_version,
            "ar_guide_template": template,
            "overlay_validation_logs": validations,
            "part_maps": list(part_lookup.values()),
            "guide": guide,
            "guide_steps": display_steps,
            "ar_guide_plan": ar_guide_plan,
        }

    def build_dynamic_safe_check_overlay_data(
        self,
        analysis: dict[str, Any],
        ar_guide_plan: dict[str, Any],
    ) -> dict[str, Any]:
        product_model = analysis["context"].get("product_model")
        if not product_model:
            raise ValueError("Product model not found for AR guide.")

        structure_type = product_model["structure_type"]
        reference_image = self.repo.get_reference_image(
            model_name=product_model.get("model_name"),
            structure_type=structure_type,
            image_role="closed_front",
        ) or self.repo.get_reference_image(structure_type=structure_type)
        guide_steps = []
        for index, step in enumerate(ar_guide_plan.get("overlay_steps") or [], start=1):
            action = step.get("action") or "safe_check"
            title = action.replace("_", " ").title()
            guide_steps.append(
                {
                    "guide_step_id": step.get("step_id"),
                    "step_order": index,
                    "action_type": action,
                    "target_part": ", ".join(step.get("target_parts") or []),
                    "instruction_text": title,
                    "safety_message": "External safe-check only. Do not open covers, wiring, PCB, refrigerant, compressor, or damaged power parts.",
                    "display_title": title,
                    "display_instruction": title,
                    "display_safety": "External safe-check only. Stop and request expert A/S if power is not restored or a high-risk signal appears.",
                    "target_part_map": None,
                    "next_button_label": "Complete" if index == len(ar_guide_plan.get("overlay_steps") or []) else "Next",
                }
            )
        return {
            "product_model": product_model,
            "structure_type": self.repo.get_structure_type(structure_type),
            "reference_image": reference_image,
            "part_map_version": None,
            "ar_guide_template": {
                "template_id": ar_guide_plan.get("template_id"),
                "procedure_type": ar_guide_plan.get("procedure_type"),
                "ar_scope": ar_guide_plan.get("ar_scope"),
                "risk_ceiling": ar_guide_plan.get("risk_level"),
            },
            "overlay_validation_logs": [],
            "part_maps": [],
            "guide": {
                "guide_id": ar_guide_plan.get("template_id") or "dynamic_safe_check",
                "guide_type": "self_check",
                "structure_type": structure_type,
                "dynamic": True,
            },
            "guide_steps": guide_steps,
            "ar_guide_plan": ar_guide_plan,
        }

    def pick_ar_guide(self, analysis: dict[str, Any], structure_type: str) -> dict[str, Any]:
        intent_type = analysis["intent"]["intent_type"]
        guide_type = "preventive_care" if intent_type == "care" else "self_check"
        matches = self.repo.find_ar_guides(
            product_type=analysis["context"]["device"]["product_type"],
            procedure_type=analysis["procedure"]["procedure_type"],
            guide_type=guide_type,
            structure_type=structure_type,
        )
        if not matches:
            matches = self.repo.find_ar_guides(
                product_type=analysis["context"]["device"]["product_type"],
                guide_type=guide_type,
                structure_type=structure_type,
            )
        if not matches:
            raise ValueError("No AR guide steps matched the decision result.")
        return matches[0]

    @staticmethod
    def normalize_part(part: dict[str, Any]) -> dict[str, Any]:
        part_id = part["part_id"]
        label = PART_LABELS.get(part_id, part.get("label") or part_id)
        return {
            **part,
            "display_label": label,
            "display_name": label,
        }

    def create_session(self, payload: dict[str, Any]) -> dict[str, Any]:
        session_id = payload.get("session_id") or f"ARS_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')}"
        return self.repo.create_ar_session_log(
            {
                "session_id": session_id,
                "user_id": payload.get("user_id", "U001"),
                "device_id": payload.get("device_id", "D001"),
                "guide_id": payload["guide_id"],
                "guide_type": payload.get("guide_type", "preventive_care"),
                "service_flow_type": payload.get("service_flow_type", "self_care"),
                "procedure_type": payload.get("procedure_type"),
                "source_alert_id": payload.get("source_alert_id"),
                "source_chat_session_id": payload.get("source_chat_session_id"),
                "structure_type": payload.get("structure_type", "wall_ac_type_a"),
                "completed_steps": payload.get("completed_steps", []),
                "completed": payload.get("completed", False),
                "solved": payload.get("solved"),
                "clicked_as": payload.get("clicked_as", False),
            }
        )

    def get_session(self, session_id: str) -> dict[str, Any] | None:
        session = self.repo.get_ar_session_log(session_id)
        if session:
            session["step_logs"] = self.repo.get_ar_step_logs(session_id)
        return session

    def update_session(self, session_id: str, payload: dict[str, Any]) -> dict[str, Any] | None:
        session = self.repo.update_ar_session_log(
            session_id=session_id,
            completed_steps=payload.get("completed_steps"),
            completed=payload.get("completed"),
            solved=payload.get("solved"),
            clicked_as=payload.get("clicked_as"),
        )
        if session and payload.get("completed_steps"):
            for index, step_id in enumerate(payload.get("completed_steps") or [], start=1):
                guide_step_id = str(step_id)
                self.repo.create_ar_step_log(
                    {
                        "step_log_id": f"ARSTEPLOG_{uuid4().hex[:12].upper()}",
                        "session_id": session_id,
                        "guide_step_id": guide_step_id,
                        "step_order": index,
                        "action": "complete_step",
                        "status": "completed",
                    }
                )
        return session

    def get_current_environment(
        self,
        region: str,
        city: str | None = None,
        user_id: str | None = "U001",
        product_type: str | None = None,
        requested_metrics: list[str] | None = None,
        provider_id: str | None = None,
        cache_ttl_minutes: int = 60,
        force_refresh: bool = False,
    ) -> dict[str, Any]:
        environment = self.environment_adapter.get_environment(
            user_id=user_id,
            region=region,
            city=city,
            product_type=product_type,
            requested_metrics=requested_metrics,
            provider_id=provider_id,
            force_refresh=force_refresh,
            cache_ttl_minutes=cache_ttl_minutes,
        )
        return {
            "region": region,
            "city": city,
            "environment": environment,
            "observation": environment.get("observation"),
            "providers": self.repo.list_environment_providers(),
        }

    def refresh_environment(self, payload: dict[str, Any]) -> dict[str, Any]:
        provider_id = payload.get("provider_id", "ENV_PROVIDER_OPENWEATHER")
        region = payload.get("region", "Gujarat")
        city = payload.get("city")
        environment = self.environment_adapter.get_environment(
            user_id=payload.get("user_id"),
            region=region,
            city=city,
            product_type=payload.get("product_type"),
            requested_metrics=payload.get("requested_metrics"),
            provider_id=provider_id,
            force_refresh=payload.get("force_refresh", True),
            cache_ttl_minutes=int(payload.get("cache_ttl_minutes") or 60),
        )
        return {
            "fetch_log": environment.get("fetch_log"),
            "current": {
                "region": region,
                "city": city,
                "environment": environment,
                "observation": environment.get("observation"),
                "providers": self.repo.list_environment_providers(),
            },
        }

    def list_environment_refresh_targets(self, limit: int = 20) -> list[dict[str, Any]]:
        if hasattr(self.repo, "list_environment_refresh_targets"):
            return self.repo.list_environment_refresh_targets(limit=limit)
        return [
            {"region": "Delhi", "city": "Delhi"},
            {"region": "Gujarat", "city": "Ahmedabad"},
        ]

    def refresh_scheduled_environment_targets(
        self,
        *,
        provider_id: str = "ENV_PROVIDER_OPENMETEO",
        limit: int = 20,
    ) -> dict[str, Any]:
        targets = self.list_environment_refresh_targets(limit=limit)
        refreshed: list[dict[str, Any]] = []
        failed: list[dict[str, Any]] = []
        for target in targets:
            region = target.get("region")
            city = target.get("city")
            if not region:
                continue
            try:
                current = self.refresh_environment(
                    {
                        "region": region,
                        "city": city,
                        "provider_id": provider_id,
                        "force_refresh": True,
                        "cache_ttl_minutes": 60,
                    }
                )["current"]
                observation = current.get("observation") or {}
                refreshed.append(
                    {
                        "region": observation.get("region") or region,
                        "city": observation.get("city") or city,
                        "observed_at": observation.get("observed_at"),
                        "aqi": observation.get("aqi"),
                        "temperature_c": observation.get("temperature_c"),
                        "humidity_percent": observation.get("humidity_percent"),
                    }
                )
            except Exception as exc:
                failed.append({"region": region, "city": city, "error": str(exc)})
        return {
            "refreshed_count": len(refreshed),
            "failed_count": len(failed),
            "targets_count": len(targets),
            "provider_id": provider_id,
            "refreshed": refreshed,
            "failed": failed,
            "refreshed_at": datetime.now(timezone.utc).isoformat(),
        }

    def evaluate_care_risk(self, payload: dict[str, Any]) -> dict[str, Any]:
        user_id = payload.get("user_id", "U001")
        device_id = payload.get("device_id", "D001")
        user_profile = self.repo.get_user_profile(user_id)
        device = (
            self.repo.get_device_context_for_user(user_id, device_id)
            if hasattr(self.repo, "get_device_context_for_user")
            else self.repo.get_device_context(device_id)
        )
        if not device:
            raise ValueError(f"Device not found: {device_id}")
        usage_log = (
            self.repo.get_usage_log_for_user(user_id, device_id)
            if hasattr(self.repo, "get_usage_log_for_user")
            else self.repo.get_usage_log(device_id)
        )
        smart_diagnosis = (
            self.repo.get_smart_diagnosis_for_user(user_id, device_id)
            if hasattr(self.repo, "get_smart_diagnosis_for_user")
            else self.repo.get_smart_diagnosis(device_id)
        )
        environment_region = payload.get("region") or (user_profile or {}).get("region") or device.get("region") or "Gujarat"
        environment_city = payload.get("city") or (user_profile or {}).get("city") or device.get("city")
        environment_result = self.environment_adapter.get_environment(
            user_id=user_id,
            region=environment_region,
            city=environment_city,
            product_type=device.get("product_type"),
            requested_metrics=payload.get("requested_metrics"),
            force_refresh=payload.get("force_environment_refresh", False),
            cache_ttl_minutes=int(payload.get("cache_ttl_minutes") or 60),
        )
        environment = environment_result.get("observation")
        procedure_type = payload.get("procedure_type") or self.default_procedure_for_product(device["product_type"])
        rules = (
            self.repo.get_care_risk_rules(device["product_type"], procedure_type)
            if hasattr(self.repo, "get_care_risk_rules")
            else []
        )
        score_result = self.care_risk_engine.evaluate(
            device=device,
            usage_log=usage_log,
            smart_diagnosis=smart_diagnosis,
            environment=environment,
            rules=rules,
            procedure_type=procedure_type,
        )
        score = score_result["care_risk_score"]
        risk_level = score_result["risk_band"]
        recommendation = self.preventive_recommendation_engine.build(device, score_result)
        guide_options = None
        if score >= score_result["alert_threshold"]:
            guide_options = self.get_guide_options(
                user_id=user_id,
                device_id=device_id,
                procedure_type=procedure_type,
                service_flow_type="self_care",
                language_code="en",
            )

        return {
            "device": device,
            "usage_log": usage_log,
            "smart_diagnosis": smart_diagnosis,
            "environment_result": environment_result,
            "environment_observation": environment,
            "rules": rules,
            "care_risk_decision": score_result,
            "recommended_options": recommendation["recommended_options"],
            "care_risk_score": {
                "user_id": user_id,
                "device_id": device_id,
                "product_type": device["product_type"],
                "procedure_type": procedure_type,
                "score": score,
                "risk_level": risk_level,
                "trigger_reason": score_result["trigger_reason"],
                "stored": False,
            },
            "guide_options": guide_options,
        }

    def get_device_care_history(
        self,
        user_id: str,
        device_id: str,
        service_flow_type: str | None = None,
        limit: int = 50,
    ) -> dict[str, Any] | None:
        if not self.repo.get_device_context(device_id):
            return None
        limit = min(max(int(limit or 50), 1), 200)
        summary = self.repo.get_device_care_summary(user_id, device_id) or {
            "summary_id": None,
            "user_id": user_id,
            "device_id": device_id,
            "self_care_count": 0,
            "self_as_count": 0,
            "total_care_count": 0,
            "care_score": 0,
            "last_self_care_at": None,
            "last_self_as_at": None,
            "updated_at": None,
        }
        rows = self.repo.get_device_care_history(
            user_id=user_id,
            device_id=device_id,
            service_flow_type=service_flow_type,
            limit=limit,
        )
        return {
            "user_id": user_id,
            "device_id": device_id,
            "summary": summary,
            "items": [self.normalize_care_history_item(row) for row in rows],
        }

    def normalize_care_history_item(self, row: dict[str, Any]) -> dict[str, Any]:
        item = {
            "history_id": row["history_id"],
            "service_flow_type": row.get("service_flow_type") or "self_care",
            "activity_channel": row.get("activity_channel") or "official_content",
            "procedure_type": row.get("procedure_type"),
            "title": row.get("title"),
            "status": row.get("status") or "created",
            "started_at": row.get("started_at"),
            "completed_at": row.get("completed_at"),
            "source_content_view_id": row.get("source_content_view_id"),
            "source_ar_session_id": row.get("source_ar_session_id"),
            "source_route_log_id": row.get("source_route_log_id"),
            "source_expert_as_request_id": row.get("source_expert_as_request_id"),
            "step_log_count": row.get("step_log_count"),
        }
        if not item["title"]:
            item["title"] = self.default_care_history_title(
                item["activity_channel"],
                item["procedure_type"],
                item["service_flow_type"],
            )
        return item

    @staticmethod
    def default_care_history_title(
        activity_channel: str,
        procedure_type: str | None,
        service_flow_type: str,
    ) -> str:
        label = (procedure_type or service_flow_type or "care").replace("_", " ").title()
        if activity_channel == "ar_guide":
            return f"{label} AR Guide"
        if activity_channel == "expert_as":
            return "Expert A/S routing"
        if activity_channel == "chatbot":
            return f"{label} chatbot self-check"
        return f"{label} official content"

    def get_guide_options(
        self,
        user_id: str,
        device_id: str,
        procedure_type: str | None = None,
        service_flow_type: str = "self_care",
        language_code: str = "en",
        rag_evidence: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        device = self.repo.get_device_context(device_id)
        if not device:
            return None
        procedure = procedure_type or self.default_procedure_for_product(device["product_type"])
        product_model = self.repo.get_product_model(device.get("model_name"), device["product_type"])
        manual_guides = self.repo.find_official_contents(
            product_type=device["product_type"],
            procedure_type=procedure,
            language=language_code,
            model_name=device.get("model_name"),
        )
        ar_template = self.repo.get_ar_guide_template(
            product_type=device["product_type"],
            procedure_type=procedure,
            structure_type=(product_model or {}).get("structure_type"),
        )
        youtube_recommendations = self.select_youtube_recommendations(
            product_type=device["product_type"],
            procedure_type=procedure,
            service_flow_type=service_flow_type,
            language_code=language_code,
            rag_evidence=rag_evidence,
        )
        manual_options = [self.content_option(guide) for guide in manual_guides]
        dynamic_manual = None
        if not manual_options:
            dynamic_manual = self.dynamic_manual_guide_option(
                device=device,
                procedure_type=procedure,
                service_flow_type=service_flow_type,
                language_code=language_code,
                youtube_recommendations=youtube_recommendations,
                rag_evidence=rag_evidence,
            )
            if dynamic_manual:
                manual_options.append(dynamic_manual)

        ar_options = [self.ar_guide_option(ar_template)] if ar_template else []
        if not ar_options and dynamic_manual:
            dynamic_ar = self.dynamic_ar_guide_option(
                device=device,
                product_model=product_model or {},
                procedure_type=procedure,
            )
            if dynamic_ar:
                ar_options.append(dynamic_ar)

        return {
            "option_set_id": f"GUIDE_OPTIONS_{user_id}_{device_id}_{procedure}",
            "user_id": user_id,
            "device_id": device_id,
            "product_code": device.get("product_code"),
            "service_flow_type": service_flow_type,
            "procedure_type": procedure,
            "language_code": language_code,
            "manual_guides": manual_options,
            "youtube_recommendations": youtube_recommendations,
            "ar_guides": ar_options,
            "matching_policy": {
                "manual_match": "product_type + exact procedure_type + language + exact_model_or_common_model; if no DB manual exists, whitelisted dynamic manual guide can be generated from official RAG/YouTube evidence.",
                "youtube_match": "RAG official_youtube evidence first, then DB official_youtube fallback by exact procedure_type",
                "blocked_fallbacks": [
                    "No filter_cleaning fallback for self-AS power/no-power symptoms.",
                    "No expert_as_only video in self_care or self_as recommendation cards.",
                    "No cross-procedure YouTube recommendation.",
                ],
            },
            "storage_policy": {
                "recommendation_saved": False,
                "completion_saved_table": "SELF_MANAGEMENT_HISTORY",
                "manual_or_ar_method_saved": False,
            },
        }

    def select_youtube_recommendations(
        self,
        product_type: str,
        procedure_type: str,
        service_flow_type: str,
        language_code: str = "en",
        rag_evidence: dict[str, Any] | None = None,
        limit: int = 3,
    ) -> list[dict[str, Any]]:
        candidates: list[dict[str, Any]] = []
        for item in (rag_evidence or {}).get("results") or []:
            if item.get("source_type") != "official_youtube":
                continue
            candidates.append(item)

        if len(candidates) < limit and hasattr(self.repo, "find_official_youtube_recommendations"):
            candidates.extend(
                self.repo.find_official_youtube_recommendations(
                    product_type=product_type,
                    procedure_type=procedure_type,
                    language=language_code,
                    limit=limit * 3,
                )
            )

        selected: list[dict[str, Any]] = []
        seen_urls: set[str] = set()
        for candidate in candidates:
            recommendation = self.youtube_recommendation_option(candidate, procedure_type, service_flow_type)
            if not recommendation:
                continue
            if recommendation["source_url"] in seen_urls:
                continue
            seen_urls.add(recommendation["source_url"])
            selected.append(recommendation)
            if len(selected) >= limit:
                break
        return selected

    def dynamic_manual_guide_option(
        self,
        device: dict[str, Any],
        procedure_type: str,
        service_flow_type: str,
        language_code: str,
        youtube_recommendations: list[dict[str, Any]],
        rag_evidence: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        if device.get("product_type") != "air_conditioner":
            return None
        guide_template = AIRCON_DYNAMIC_MANUAL_GUIDES.get(procedure_type)
        if not guide_template or service_flow_type not in guide_template["service_flows"]:
            return None

        evidence_by_key: dict[str, dict[str, Any]] = {}
        accepted_evidence_procedures = {procedure_type}
        if procedure_type in RAG_PROCEDURE_ALIASES:
            accepted_evidence_procedures.add(RAG_PROCEDURE_ALIASES[procedure_type])
        for item in (rag_evidence or {}).get("results") or []:
            if item.get("procedure_type") not in accepted_evidence_procedures:
                continue
            source_url = item.get("source_url")
            key = str(item.get("chunk_id") or source_url or item.get("asset_id"))
            if not key:
                continue
            evidence_by_key[key] = {
                "asset_id": item.get("asset_id"),
                "chunk_id": item.get("chunk_id"),
                "title": item.get("title") or item.get("chunk_title") or f"{procedure_type.replace('_', ' ').title()} evidence",
                "source_url": source_url,
                "source_type": item.get("source_type") or "official_pdf",
                "section_title": item.get("source_section"),
                "excerpt": (item.get("chunk_text") or "")[:240] or None,
            }
        for item in youtube_recommendations:
            if not item.get("source_url"):
                continue
            key = str(item.get("chunk_id") or item.get("source_url") or item.get("asset_id"))
            evidence_by_key[key] = {
                "asset_id": item.get("asset_id"),
                "chunk_id": item.get("chunk_id"),
                "title": item.get("title"),
                "source_url": item.get("source_url"),
                "source_type": "official_youtube",
            }
        evidence = list(evidence_by_key.values())
        first_video_url = next((item.get("source_url") for item in youtube_recommendations if item.get("source_url")), None)
        first_source_url = first_video_url or next((item.get("source_url") for item in evidence if item.get("source_url")), None)
        return {
            "content_id": f"DYNAMIC_GUIDE_AIRCON_{procedure_type.upper()}",
            "guide_id": f"DYNAMIC_{procedure_type.upper()}",
            "content_type": "manual",
            "title": guide_template["title"],
            "summary": guide_template["summary"],
            "guide_text": "\n".join(
                f"{index}. {step}"
                for index, step in enumerate(guide_template["steps"], start=1)
            ),
            "language_code": "en-IN" if language_code == "en" else language_code,
            "source_url": first_source_url,
            "video_url": first_video_url,
            "evidence": evidence,
            "display_steps": self.display_steps_from_text_steps(guide_template["steps"]),
            "dynamic": True,
            "generation_source": "rag_chunk_dynamic_manual",
            "safety_scope": guide_template["safety_scope"],
            "stop_conditions": guide_template["stop_conditions"],
        }

    @staticmethod
    def official_youtube_evidence_from_recommendations(youtube_recommendations: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return [
            {
                "asset_id": item.get("asset_id"),
                "chunk_id": item.get("chunk_id"),
                "title": item.get("title"),
                "source_url": item.get("source_url"),
                "source_type": "official_youtube",
            }
            for item in youtube_recommendations
            if item.get("source_url")
        ]

    def youtube_recommendation_option(
        self,
        candidate: dict[str, Any],
        procedure_type: str,
        service_flow_type: str,
    ) -> dict[str, Any] | None:
        if candidate.get("procedure_type") != procedure_type:
            return None
        source_url = candidate.get("source_url") or ""
        if not source_url.startswith(("https://www.youtube.com/watch", "https://youtu.be/")):
            return None

        chunk_text = candidate.get("chunk_text") or ""
        risk_policy = self.extract_chunk_field(chunk_text, "Risk policy") or "self_care_allowed"
        if not self.youtube_allowed_for_service_flow(risk_policy, service_flow_type):
            return None

        return {
            "asset_id": candidate.get("asset_id"),
            "chunk_id": candidate.get("chunk_id"),
            "title": candidate.get("title") or candidate.get("chunk_title") or self.extract_chunk_field(chunk_text, "Official YouTube video title"),
            "source_url": source_url,
            "video_id": self.extract_youtube_video_id(source_url),
            "source_type": "official_youtube",
            "channel_name": self.extract_channel_name(chunk_text),
            "procedure_type": procedure_type,
            "risk_policy": risk_policy,
            "self_guidance_allowed": risk_policy != "expert_as_only",
            "recommendation_reason": (
                "Exact procedure_type match from official YouTube RAG evidence."
                if candidate.get("retrieval_mode")
                else "Exact procedure_type match from official YouTube catalog fallback."
            ),
        }

    @staticmethod
    def youtube_allowed_for_service_flow(risk_policy: str, service_flow_type: str) -> bool:
        if risk_policy == "expert_as_only":
            return service_flow_type == "expert_as"
        if service_flow_type == "self_care":
            return risk_policy == "self_care_allowed"
        if service_flow_type == "self_as":
            return risk_policy in {"self_care_allowed", "self_as_allowed", "title_classified"}
        return False

    @staticmethod
    def extract_chunk_field(chunk_text: str, label: str) -> str | None:
        for line in (chunk_text or "").splitlines():
            prefix = f"{label}:"
            if line.startswith(prefix):
                return line[len(prefix) :].strip()
        return None

    @staticmethod
    def extract_channel_name(chunk_text: str) -> str | None:
        channel = CareShotBackendService.extract_chunk_field(chunk_text, "Official channel")
        if not channel:
            return None
        return channel.split("(", 1)[0].strip()

    @staticmethod
    def extract_youtube_video_id(source_url: str) -> str | None:
        match = re.search(r"(?:v=|youtu\.be/)([A-Za-z0-9_-]{11})", source_url or "")
        return match.group(1) if match else None

    def complete_guide(self, guide_id: str, payload: dict[str, Any]) -> dict[str, Any] | None:
        guide = self.repo.get_guide(guide_id)
        if not guide:
            return None
        user_id = payload.get("user_id", "U001")
        device_id = payload.get("device_id", "D001")
        procedure_type = payload.get("procedure_type") or guide.get("procedure_type") or guide.get("guide_category")
        service_flow_type = payload.get("service_flow_type") or guide.get("trigger_type") or "self_care"
        activity = self.repo.create_care_activity_log(
            {
                "activity_id": f"CAREACT_{uuid4().hex[:12].upper()}",
                "user_id": user_id,
                "device_id": device_id,
                "service_flow_type": service_flow_type,
                "procedure_type": procedure_type,
                "source_chat_session_id": payload.get("source_chat_session_id"),
                "guide_id": guide.get("guide_id"),
                "status": "completed",
                "completed_at": datetime.now(timezone.utc).isoformat(),
            }
        )
        return {
            "guide": {
                "guide_id": guide.get("guide_id"),
                "content_id": guide.get("content_id"),
                "guide_type": guide.get("guide_type"),
                "title": guide.get("title"),
                "procedure_type": procedure_type,
            },
            "self_management_history": activity,
            "device_care_summary": self.repo.get_device_care_summary(user_id, device_id),
        }

    @staticmethod
    def content_option(content: dict[str, Any], match: dict[str, Any] | None = None) -> dict[str, Any]:
        source_asset_ids = content.get("source_asset_ids") or []
        evidence_refs = (match or {}).get("evidence_refs") or source_asset_ids
        evidence = [
            {
                "asset_id": asset_id,
                "title": content["title"],
                "source_url": content.get("source_url"),
                "source_type": content.get("content_type"),
            }
            for asset_id in evidence_refs
            if asset_id
        ]
        return {
            "content_id": content["content_id"],
            "guide_id": content.get("guide_id"),
            "content_type": content["content_type"],
            "title": content["title"],
            "summary": content.get("guide_summary"),
            "guide_text": content.get("guide_text"),
            "language_code": "en-IN" if content.get("language") == "en" else content.get("language"),
            "source_url": content.get("source_url"),
            "video_url": content.get("video_url"),
            "evidence": evidence,
            "display_steps": CareShotBackendService.display_steps_from_text_steps(
                content.get("guide_text") or content.get("guide_summary") or ""
            ),
        }

    @staticmethod
    def display_steps_from_text_steps(steps: list[str] | str | None) -> list[dict[str, Any]]:
        if isinstance(steps, str):
            raw_steps = [
                line.strip()
                for line in steps.splitlines()
                if line.strip()
            ]
        else:
            raw_steps = [str(step).strip() for step in (steps or []) if str(step).strip()]
        provider = "google_cloud_tts" if google_tts_enabled() else "web_speech"
        return [
            {
                "title": f"STEP {index}",
                "text": step,
                **CareShotBackendService.tts_fields_for_step(step, provider=provider),
            }
            for index, step in enumerate(raw_steps, start=1)
        ]

    @staticmethod
    def tts_fields_for_step(
        text: str | None,
        *,
        language_code: str = "en-IN",
        provider: str | None = None,
    ) -> dict[str, Any]:
        tts_text = (text or "").strip()
        selected_provider = provider or ("google_cloud_tts" if google_tts_enabled() else "web_speech")
        audio_url = None
        cache_key = None
        if tts_text and google_tts_enabled() and google_tts_pregenerate_enabled():
            try:
                asset = generate_google_tts_mp3_asset(text=tts_text, language_code=language_code)
                audio_url = asset.audio_url
                cache_key = asset.cache_key
                selected_provider = asset.provider
            except Exception:
                audio_url = None
                cache_key = None
        return {
            "tts_enabled": bool(tts_text),
            "tts_text": tts_text,
            "tts_language_code": language_code,
            "tts_provider": selected_provider,
            "audio_url": audio_url,
            "tts_cache_key": cache_key,
        }

    @staticmethod
    def ar_guide_option(template: dict[str, Any]) -> dict[str, Any]:
        return {
            "template_id": template["template_id"],
            "guide_id": template["guide_id"],
            "title": f"{template['procedure_type'].replace('_', ' ').title()} AR Guide",
            "product_type": template["product_type"],
            "structure_type": template.get("structure_type"),
            "procedure_type": template["procedure_type"],
            "risk_ceiling": template["risk_ceiling"],
            "guide_type": template.get("guide_type"),
            "ar_scope": template.get("ar_scope"),
            "forbidden_actions": template.get("forbidden_actions"),
        }

    @staticmethod
    def dynamic_ar_guide_option(
        device: dict[str, Any],
        product_model: dict[str, Any],
        procedure_type: str,
    ) -> dict[str, Any] | None:
        if device.get("product_type") != "air_conditioner" or procedure_type != "power_troubleshooting":
            return None
        return {
            "template_id": "aircon_power_troubleshooting_safe_check_v1",
            "guide_id": "DYNAMIC_POWER_TROUBLESHOOTING_SAFE_CHECK",
            "title": "Power Troubleshooting Safe-Check AR Guide",
            "product_type": "air_conditioner",
            "structure_type": product_model.get("structure_type") or "wall_ac_type_a",
            "procedure_type": "power_troubleshooting",
            "risk_ceiling": "medium",
            "guide_type": "self_check",
            "dynamic": True,
            "ar_scope": "external_safe_check_only",
            "forbidden_actions": [
                "open_internal_cover",
                "touch_pcb",
                "repair_wiring",
                "inspect_compressor",
                "check_refrigerant",
                "touch_damaged_cord",
                "touch_wet_outlet",
            ],
        }

    @staticmethod
    def default_procedure_for_product(product_type: str) -> str:
        return {
            "air_conditioner": "filter_cleaning",
            "washing_machine": "tub_clean",
            "air_purifier": "filter_cleaning",
            "water_purifier": "limescale_care",
        }.get(product_type, "general_care")

    @staticmethod
    def compute_care_risk_score(
        device: dict[str, Any],
        usage_log: dict[str, Any] | None,
        environment: dict[str, Any] | None,
    ) -> tuple[float, list[str]]:
        score = 20.0
        reasons: list[str] = []
        usage_summary = (usage_log or {}).get("usage_summary") or {}
        days_since_last_care = float(usage_summary.get("days_since_last_care") or 0)
        daily_runtime = float(usage_summary.get("daily_runtime_hours") or 0)
        if days_since_last_care:
            score += min(days_since_last_care * 0.8, 40)
            reasons.append(f"Days since last care: {int(days_since_last_care)}.")
        if daily_runtime:
            score += min(daily_runtime * 5, 15)
            reasons.append(f"Recent daily runtime: {daily_runtime:.1f}h.")
        humidity = float((environment or {}).get("humidity_percent") or 0)
        if humidity >= 60:
            score += 15
            reasons.append(f"Humidity is high at {humidity:.0f}%.")
        aqi = float((environment or {}).get("aqi") or 0)
        if aqi >= 150:
            score += 15
            reasons.append(f"AQI is poor at {aqi:.0f}.")
        if (environment or {}).get("water_hardness_level") == "high":
            score += 5
            reasons.append("Water hardness is high in the current environment context.")
        score = min(round(score, 1), 100.0)
        if not reasons:
            reasons.append("No strong risk factor was found; score remains low.")
        return score, reasons

@lru_cache(maxsize=1)
def get_backend_service() -> CareShotBackendService:
    return CareShotBackendService()
