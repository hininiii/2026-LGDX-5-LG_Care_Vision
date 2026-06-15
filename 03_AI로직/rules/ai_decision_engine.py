from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


RULES_DIR = Path(__file__).resolve().parent
PROJECT_DIR = RULES_DIR.parents[1]
DB_DIR = PROJECT_DIR / "02_데이터연동" / "db"
OUTPUT_DIR = PROJECT_DIR / "06_산출물" / "decision_demo"
OUTPUT_PATH = OUTPUT_DIR / "ar_decision_demo_results.json"


def _find_fastapi_backend_dir() -> Path:
    github_backend = PROJECT_DIR / "backend"
    if (github_backend / "app").exists():
        return github_backend
    for path in PROJECT_DIR.iterdir():
        if path.name.startswith("04_") and (path / "app").exists():
            return path
    raise FileNotFoundError("FastAPI backend app directory was not found.")


FASTAPI_BACKEND_DIR = _find_fastapi_backend_dir()
sys.path.insert(0, str(FASTAPI_BACKEND_DIR))
sys.path.insert(0, str(DB_DIR))

from app.repositories import CareShotRepository  # noqa: E402


HIGH_RISK_KEYWORDS = [
    "spark",
    "smoke",
    "fire",
    "flame",
    "burnt",
    "burn out",
    "burning smell",
    "electric shock",
    "breaker",
    "short circuit",
    "refrigerant",
    "gas leak",
    "pcb",
    "wiring",
    "compressor",
    "internal disassembly",
    "스파크",
    "연기",
    "타는 냄새",
    "감전",
    "누전",
    "차단기",
    "냉매",
    "가스 누출",
    "내부 분해",
]

MEDIUM_RISK_KEYWORDS = [
    "leak",
    "water leak",
    "inside",
    "internal",
    "noise",
    "not cooling",
    "error",
    "누수",
    "내부",
    "소음",
    "안 시원",
    "에러",
]

POWER_ISSUE_KEYWORDS = [
    "no power",
    "power off",
    "power turns off",
    "power turned off",
    "turns off",
    "turned off",
    "turning off",
    "shuts off",
    "shut off",
    "shutdown",
    "stops suddenly",
    "suddenly stopped",
    "switches off",
    "switched off",
    "won't turn on",
    "will not turn on",
    "does not turn on",
    "doesn't turn on",
    "not turning on",
    "전원이 갑자기",
    "전원 꺼",
    "전원꺼",
    "전원이 꺼",
    "갑자기 꺼",
    "꺼져요",
    "꺼짐",
    "안 켜져",
    "켜지지",
    "전원",
    "꺼졌",
    "꺼짐",
    "꺼져",
    "갑자기 꺼",
    "작동이 멈",
    "켜지지",
]

SELF_AS_KEYWORDS = [
    "weak airflow",
    "airflow",
    "smell",
    "bad smell",
    "odor",
    "odour",
    "not cooling",
    "not cold",
    "doesn't cool",
    "does not cool",
    "warm air",
    "fault",
    "broken",
    "malfunction",
    "diagnosis",
    "self check",
    "troubleshoot",
    "troubleshooting",
    "repair",
    "바람 약",
    "바람이 약",
    "냄새",
    "악취",
    "안 시원",
    "시원하지",
    "고장",
    "오류",
    "자가점검",
    "자가 진단",
    "점검",
    "수리",
]

CARE_KEYWORDS = [
    "clean",
    "cleaning",
    "filter",
    "maintenance",
    "maintain",
    "schedule",
    "cycle",
    "interval",
    "prevent",
    "preventive",
    "mold",
    "limescale",
    "tub clean",
    "교체",
    "청소",
    "관리",
    "주기",
    "예방",
    "필터",
    "곰팡이",
    "석회질",
    "통세척",
]


PROCEDURE_BY_PRODUCT_TYPE = {
    "air_conditioner": "filter_cleaning",
    "washing_machine": "tub_clean",
    "air_purifier": "filter_replacement",
    "water_purifier": "limescale_care",
}

PROCEDURE_KEYWORD_RULES = [
    (
        "high_risk_troubleshooting",
        [
            "spark",
            "smoke",
            "burning smell",
            "electric shock",
            "refrigerant",
            "gas leak",
            "pcb",
            "compressor",
            "internal disassembly",
        ],
    ),
    ("power_troubleshooting", POWER_ISSUE_KEYWORDS),
    (
        "water_leak_monsoon",
        ["water leak", "water dripping", "dripping", "condensation", "leak", "monsoon", "물이", "누수", "물 떨어"],
    ),
    (
        "noise_self_check",
        ["noise", "vibration", "hissing", "rattling", "buzzing", "sound", "소음", "진동"],
    ),
    (
        "odor_self_check",
        ["smell", "bad smell", "odor", "odour", "mold smell", "musty", "냄새", "곰팡이"],
    ),
    (
        "no_cooling_self_check",
        [
            "not cooling",
            "not cold",
            "doesn't cool",
            "does not cool",
            "weak airflow",
            "warm air",
            "cooling issue",
            "insufficient cooling",
            "시원하지",
            "찬바람",
            "바람 약",
        ],
    ),
    (
        "remote_operation",
        ["remote", "timer", "sleep timer", "fan speed", "mode", "temperature", "swing", "리모컨", "타이머", "온도", "모드"],
    ),
    (
        "auto_clean",
        ["auto clean", "auto cleaning", "freeze cleaning", "self cleaning", "자동 청소"],
    ),
    (
        "filter_cleaning",
        ["clean filter", "filter cleaning", "air filter", "filter", "필터"],
    ),
]

REMOTE_OPERATION_KEYWORDS = [
    "remote",
    "timer",
    "sleep timer",
    "fan speed",
    "mode",
    "temperature",
    "swing",
    "리모컨",
    "타이머",
    "온도",
    "모드",
]

SELF_AS_KEYWORDS.extend(
    [
        "water leak",
        "water dripping",
        "dripping",
        "condensation",
        "leak",
        "noise",
        "vibration",
        "hissing",
        "rattling",
        "buzzing",
        "no power",
        "power off",
        "turning off",
        "전원",
        "꺼졌",
        "누수",
        "물 떨어",
        "소음",
        "진동",
    ]
)


class CareShotARDecisionEngine:
    def __init__(self, repo: CareShotRepository | None = None) -> None:
        self.repo = repo or CareShotRepository()

    def analyze(self, user_id: str, device_id: str, message: str, request_id: str | None = None) -> dict[str, Any]:
        request_id = request_id or f"REQ_AR_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
        user = self.require(self.repo.get_user_profile(user_id), f"User not found: {user_id}")
        device = self.require(self.repo.get_device_context(device_id), f"Device not found: {device_id}")
        usage_log = self.repo.get_usage_log(device_id)
        diagnosis = self.repo.get_smart_diagnosis(device_id)
        environment = self.repo.get_environment_context(device["region"], device.get("city"))
        product_model = self.repo.get_product_model(device["model_name"], device["product_type"])

        official_match = self.repo.find_official_assets(
            model_name=device["model_name"],
            product_type=device["product_type"],
            aliases=device.get("model_aliases") or [],
            series=device.get("series"),
        )
        intent = self.classify_intent(message, usage_log, diagnosis)
        risk = self.evaluate_risk(message, diagnosis, official_match)
        if intent.get("service_flow_type") == "expert_as" or risk.get("risk_level") == "high":
            procedure = "high_risk_troubleshooting"
        else:
            procedure = self.resolve_procedure(device["product_type"], message, usage_log, intent)
        secondary_procedures = self.resolve_secondary_procedures(message, procedure)
        reusable_content = self.find_reusable_official_content(user, device, procedure, official_match, intent, risk)
        decision = self.build_decision(intent, risk, official_match, reusable_content)

        return {
            "request_id": request_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "input": {
                "user_id": user_id,
                "device_id": device_id,
                "message": message,
            },
            "context": {
                "user": user,
                "device": device,
                "usage_log": usage_log,
                "smart_diagnosis": diagnosis,
                "environment": environment,
                "product_model": product_model,
            },
            "intent": intent,
            "procedure": {
                "procedure_type": procedure,
                "primary_procedure": procedure,
                "secondary_procedures": secondary_procedures,
                "source": "rule_mapping",
            },
            "official_asset_match": official_match,
            "reusable_official_content": reusable_content,
            "decision_result": decision,
            "chatbot_response": self.build_chatbot_response(decision, reusable_content),
        }

    @staticmethod
    def require(value: Any, message: str) -> Any:
        if value is None:
            raise ValueError(message)
        return value

    def classify_intent(
        self,
        message: str,
        usage_log: dict[str, Any] | None,
        diagnosis: dict[str, Any] | None,
    ) -> dict[str, Any]:
        text = message.lower()
        if self.contains_any(text, HIGH_RISK_KEYWORDS):
            return {
                "intent_type": "high_risk",
                "content_type": "service_route",
                "service_flow_type": "expert_as",
                "confidence": 0.98,
            }
        if self.contains_any(text, POWER_ISSUE_KEYWORDS):
            return {
                "intent_type": "self_check",
                "content_type": "self_check",
                "service_flow_type": "self_as",
                "confidence": 0.9,
            }
        if self.contains_any(text, REMOTE_OPERATION_KEYWORDS):
            return {
                "intent_type": "usage_help",
                "content_type": "manual",
                "service_flow_type": "self_care",
                "confidence": 0.9,
            }
        if self.contains_any(text, SELF_AS_KEYWORDS):
            return {
                "intent_type": "self_check",
                "content_type": "self_check",
                "service_flow_type": "self_as",
                "confidence": 0.88,
            }
        if self.contains_any(text, CARE_KEYWORDS):
            return {
                "intent_type": "care",
                "content_type": "care",
                "service_flow_type": "self_care",
                "confidence": 0.86,
            }
        if diagnosis and diagnosis.get("severity") in {"medium", "high"}:
            service_flow_type = "expert_as" if diagnosis.get("severity") == "high" else "self_as"
            return {
                "intent_type": "self_check",
                "content_type": "self_check",
                "service_flow_type": service_flow_type,
                "confidence": 0.82,
            }
        if usage_log and usage_log.get("care_triggers"):
            return {
                "intent_type": "care",
                "content_type": "care",
                "service_flow_type": "self_care",
                "confidence": 0.74,
            }
        return {
            "intent_type": "self_check",
            "content_type": "self_check",
            "service_flow_type": "self_as",
            "confidence": 0.68,
        }

    def evaluate_risk(
        self,
        message: str,
        diagnosis: dict[str, Any] | None,
        official_match: dict[str, Any],
    ) -> dict[str, Any]:
        text = message.lower()
        detected = [signal.lower() for signal in (diagnosis or {}).get("detected_signals", [])]
        combined_text = " ".join([text, *detected])

        if self.contains_any(combined_text, HIGH_RISK_KEYWORDS) or (diagnosis or {}).get("severity") == "high":
            return {
                "risk_level": "high",
                "reasons": ["High-risk symptom or smart diagnosis signal detected."],
            }
        if self.contains_any(combined_text, POWER_ISSUE_KEYWORDS):
            return {
                "risk_level": "medium",
                "ar_guide_allowed": True,
                "ar_scope": "external_safe_check_only",
                "reasons": [
                    "Power interruption or no-power symptom detected; only external safe-check manual and AR guidance are allowed.",
                ],
            }
        if self.contains_any(combined_text, REMOTE_OPERATION_KEYWORDS):
            return {
                "risk_level": "low",
                "ar_guide_allowed": False,
                "reuse_decision": "manual_or_youtube_usage_help",
                "customer_message_template_id": "remote_operation_manual_only",
                "reasons": [
                    "Remote, timer, fan speed, mode, or temperature operation is usage help; manual and official YouTube guidance are allowed, but AR overlay is not required.",
                ],
            }
        if self.contains_any(combined_text, MEDIUM_RISK_KEYWORDS) or (diagnosis or {}).get("severity") == "medium":
            return {
                "risk_level": "medium",
                "reasons": ["Medium-risk symptom requires limited AR guide scope."],
            }
        if official_match["match_status"] != "verified":
            return {
                "risk_level": "unknown",
                "reasons": ["Official source strict matching failed."],
            }
        return {
            "risk_level": "low",
            "reasons": ["Only user-accessible care or self-check actions are detected."],
        }

    def resolve_procedure(
        self,
        product_type: str,
        message: str,
        usage_log: dict[str, Any] | None,
        intent: dict[str, Any],
    ) -> str:
        text = message.lower()
        for procedure, keywords in PROCEDURE_KEYWORD_RULES:
            if self.contains_any(text, keywords):
                return procedure
        if "tub" in text or "통세척" in text:
            return "tub_clean"
        if "limescale" in text or "석회질" in text:
            return "limescale_care"
        if "replace" in text or "교체" in text:
            return "filter_replacement"
        if intent["intent_type"] == "care" and usage_log:
            triggers = usage_log.get("care_triggers") or []
            for trigger in triggers:
                if isinstance(trigger, dict):
                    procedure = trigger.get("procedure_type")
                else:
                    procedure = self.procedure_from_trigger(str(trigger), product_type)
                if procedure and procedure != "general_care":
                    return procedure
        return PROCEDURE_BY_PRODUCT_TYPE.get(product_type, "general_care")

    def resolve_secondary_procedures(self, message: str, primary_procedure: str) -> list[str]:
        if primary_procedure == "high_risk_troubleshooting":
            return []

        text = message.lower()
        secondary: list[str] = []
        for procedure, keywords in PROCEDURE_KEYWORD_RULES:
            if procedure in {primary_procedure, "high_risk_troubleshooting"}:
                continue
            if self.contains_any(text, keywords) and procedure not in secondary:
                secondary.append(procedure)
        return secondary

    def procedure_from_trigger(self, trigger: str, product_type: str) -> str:
        text = trigger.lower()
        if "tub" in text:
            return "tub_clean"
        if "filter" in text and product_type == "air_purifier":
            return "filter_replacement"
        if "filter" in text:
            return "filter_cleaning"
        if "limescale" in text or "hardness" in text:
            return "limescale_care"
        return PROCEDURE_BY_PRODUCT_TYPE.get(product_type, "general_care")

    def find_reusable_official_content(
        self,
        user: dict[str, Any],
        device: dict[str, Any],
        procedure: str,
        official_match: dict[str, Any],
        intent: dict[str, Any],
        risk: dict[str, Any],
    ) -> dict[str, Any] | None:
        if intent.get("service_flow_type") not in {"self_care", "self_as"} or risk["risk_level"] not in {"low", "medium"}:
            return None
        return self.repo.find_reusable_care_video(
            product_type=device["product_type"],
            procedure_type=procedure,
            language=user["preferred_language"],
            video_style=user["video_style"],
            model_name=device["model_name"],
            series=device.get("series"),
            match_type=official_match["match_type"],
        )

    def build_decision(
        self,
        intent: dict[str, Any],
        risk: dict[str, Any],
        official_match: dict[str, Any],
        reusable_content: dict[str, Any] | None,
    ) -> dict[str, Any]:
        service_flow_type = intent.get("service_flow_type", "self_as")
        if risk["risk_level"] == "high":
            return {
                "content_type": intent["content_type"],
                "service_flow_type": "expert_as",
                "risk_level": "high",
                "decision_action": "route_to_service",
                "generation_allowed": False,
                "ar_guide_allowed": False,
                "reuse_decision": "blocked_high_risk",
                "admin_review_required": False,
                "reasons": risk["reasons"],
                "customer_message_template_id": "connect_service_center",
            }
        if risk.get("ar_guide_allowed") is False:
            return {
                "content_type": intent["content_type"],
                "service_flow_type": service_flow_type,
                "risk_level": risk["risk_level"],
                "decision_action": "manual_or_service_guidance_only",
                "generation_allowed": True,
                "ar_guide_allowed": False,
                "reuse_decision": risk.get("reuse_decision") or "manual_guidance_only",
                "admin_review_required": False,
                "reasons": risk["reasons"],
                "customer_message_template_id": risk.get("customer_message_template_id") or "manual_guidance_only",
            }
        if risk.get("ar_scope") == "external_safe_check_only":
            return {
                "content_type": intent["content_type"],
                "service_flow_type": service_flow_type,
                "risk_level": risk["risk_level"],
                "decision_action": "prepare_limited_ar_safe_check",
                "generation_allowed": True,
                "ar_guide_allowed": True,
                "ar_scope": "external_safe_check_only",
                "reuse_decision": "limited_power_troubleshooting_ar",
                "admin_review_required": False,
                "reasons": risk["reasons"],
                "customer_message_template_id": "power_troubleshooting_safe_check",
            }
        if official_match["match_status"] != "verified":
            return {
                "content_type": intent["content_type"],
                "service_flow_type": service_flow_type,
                "risk_level": "unknown",
                "decision_action": "official_match_review_needed",
                "generation_allowed": False,
                "ar_guide_allowed": False,
                "reuse_decision": "blocked_official_match_failed",
                "admin_review_required": False,
                "reasons": ["Strict official asset matching failed."],
                "customer_message_template_id": "official_match_review_needed",
            }

        reuse_decision = (reusable_content or {}).get("reuse_decision") or "new_ar_guide_plan"
        return {
            "content_type": intent["content_type"],
            "service_flow_type": service_flow_type,
            "risk_level": risk["risk_level"],
            "decision_action": "prepare_ar_guide_session",
            "generation_allowed": True,
            "ar_guide_allowed": True,
            "reuse_decision": reuse_decision,
            "admin_review_required": False,
            "reasons": risk["reasons"],
            "customer_message_template_id": "ar_guide_ready",
        }

    def build_chatbot_response(
        self,
        decision: dict[str, Any],
        reusable_content: dict[str, Any] | None,
    ) -> dict[str, Any]:
        if decision["decision_action"] == "route_to_service":
            return {
                "message_state": "high_risk_service_route",
                "visible_text_template_id": "connect_service_center",
                "ar_guide_session": {"enabled": False},
                "service_route": {"enabled": True},
            }

        return {
            "message_state": "ar_guide_ready" if decision["ar_guide_allowed"] else "blocked",
            "visible_text_template_id": decision["customer_message_template_id"],
            "official_content": reusable_content,
            "ar_guide_session": {
                "enabled": decision["ar_guide_allowed"],
                "status": "ready",
            },
            "service_route": {"enabled": False},
        }

    @staticmethod
    def contains_any(text: str, keywords: list[str]) -> bool:
        return any(keyword.lower() in text for keyword in keywords)


def run_demo() -> list[dict[str, Any]]:
    engine = CareShotARDecisionEngine()
    samples = [
        {
            "user_id": "U001",
            "device_id": "D001",
            "message": "Please help me clean the AC filter.",
            "request_id": "REQ_AR_DEMO_001",
        },
        {
            "user_id": "U001",
            "device_id": "D001",
            "message": "There is smoke and a burning smell from the AC.",
            "request_id": "REQ_AR_DEMO_002",
        },
    ]
    results = [engine.analyze(**sample) for sample in samples]
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    return results


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--demo", action="store_true")
    parser.add_argument("--user-id")
    parser.add_argument("--device-id")
    parser.add_argument("--message")
    args = parser.parse_args()

    if args.demo:
        print(json.dumps(run_demo(), ensure_ascii=False, indent=2))
        return

    if not (args.user_id and args.device_id and args.message):
        parser.error("--demo or --user-id/--device-id/--message is required.")

    engine = CareShotARDecisionEngine()
    print(json.dumps(engine.analyze(args.user_id, args.device_id, args.message), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
