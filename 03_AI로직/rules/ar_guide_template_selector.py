from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


RULES_DIR = Path(__file__).resolve().parent
PROJECT_DIR = RULES_DIR.parents[1]
TEMPLATE_DIR = RULES_DIR.parent / "ar_guide_templates"
OUTPUT_DIR = PROJECT_DIR / "06_산출물" / "ar_guide_plan_demo"
OUTPUT_PATH = OUTPUT_DIR / "ar_guide_plan_demo_results.json"


RISK_ORDER = {
    "none": 0,
    "low": 1,
    "medium": 2,
    "high": 3,
    "unknown": 99,
}


class ARGuideTemplateSelector:
    def __init__(self, template_dir: str | Path = TEMPLATE_DIR) -> None:
        self.template_dir = Path(template_dir)
        self.templates = self.load_templates()

    def load_templates(self) -> dict[str, dict[str, Any]]:
        templates: dict[str, dict[str, Any]] = {}
        for path in sorted(self.template_dir.glob("*.json")):
            template = json.loads(path.read_text(encoding="utf-8"))
            templates[template["template_id"]] = template
        return templates

    def select_and_build(self, decision_bundle: dict[str, Any]) -> dict[str, Any]:
        decision = decision_bundle["decision_result"]
        official_match = decision_bundle["official_asset_match"]
        procedure = decision_bundle["procedure"]
        context = decision_bundle["context"]
        user = context["user"]
        device = context["device"]

        guard = self.evaluate_ar_guard(decision, official_match)
        if not guard["allowed"]:
            return self.blocked_result(decision_bundle, guard["reason"])

        rag_guard = self.evaluate_rag_guard(decision_bundle.get("rag_evidence"))
        if not rag_guard["allowed"]:
            return self.blocked_result(decision_bundle, rag_guard["reason"])

        template = self.find_template(
            product_type=device["product_type"],
            procedure_type=procedure["procedure_type"],
        )
        if not template:
            return self.blocked_result(
                decision_bundle,
                f"No AR guide template found for product_type={device['product_type']} procedure_type={procedure['procedure_type']}.",
            )

        compatibility = self.check_template_compatibility(
            template=template,
            risk_level=decision["risk_level"],
            match_type=official_match["match_type"],
        )
        if not compatibility["allowed"]:
            return self.blocked_result(decision_bundle, compatibility["reason"], template)

        ar_guide_plan = self.build_ar_guide_plan(
            request_id=decision_bundle["request_id"],
            template=template,
            decision=decision,
            official_match=official_match,
            user=user,
            device=device,
        )
        return {
            "request_id": decision_bundle["request_id"],
            "status": "ar_guide_plan_created",
            "blocked_reason": None,
            "ar_guide_usage": self.ar_guide_usage(decision),
            "selected_template_id": template["template_id"],
            "ar_guide_plan": ar_guide_plan,
        }

    def evaluate_ar_guard(
        self,
        decision: dict[str, Any],
        official_match: dict[str, Any],
    ) -> dict[str, Any]:
        if decision["decision_action"] == "route_to_service":
            return {
                "allowed": False,
                "reason": "High Risk or service route decision blocks AR guide creation.",
            }
        if not decision["generation_allowed"]:
            return {
                "allowed": False,
                "reason": "DecisionResult.generation_allowed is false.",
            }
        if official_match["match_status"] != "verified":
            return {
                "allowed": False,
                "reason": "Official asset match is not verified.",
            }
        if decision["risk_level"] in {"high", "unknown"}:
            return {
                "allowed": False,
                "reason": f"Risk level {decision['risk_level']} is not eligible for AR guide creation.",
            }
        return {"allowed": True, "reason": None}

    def evaluate_rag_guard(self, rag_evidence: dict[str, Any] | None) -> dict[str, Any]:
        if rag_evidence is None:
            return {"allowed": True, "reason": None}
        if rag_evidence.get("skipped"):
            return {
                "allowed": False,
                "reason": f"RAG evidence search skipped: {rag_evidence.get('reason')}",
            }
        if int(rag_evidence.get("result_count") or 0) <= 0:
            return {
                "allowed": False,
                "reason": "RAG evidence is required before AR guide creation.",
            }
        return {"allowed": True, "reason": None}

    def find_template(self, product_type: str, procedure_type: str) -> dict[str, Any] | None:
        for template in self.templates.values():
            if template["product_type"] == product_type and template["procedure_type"] == procedure_type:
                return template
        return None

    def check_template_compatibility(
        self,
        template: dict[str, Any],
        risk_level: str,
        match_type: str,
    ) -> dict[str, Any]:
        if RISK_ORDER.get(risk_level, 99) > RISK_ORDER.get(template["risk_ceiling"], 99):
            return {
                "allowed": False,
                "reason": f"Risk level {risk_level} exceeds template risk ceiling {template['risk_ceiling']}.",
            }
        if match_type not in template["allowed_match_scope"]:
            return {
                "allowed": False,
                "reason": f"Official match type {match_type} is not allowed for template {template['template_id']}.",
            }
        return {"allowed": True, "reason": None}

    def build_ar_guide_plan(
        self,
        request_id: str,
        template: dict[str, Any],
        decision: dict[str, Any],
        official_match: dict[str, Any],
        user: dict[str, Any],
        device: dict[str, Any],
    ) -> dict[str, Any]:
        preferred_guide_style = user["video_style"]
        overlay_steps = []
        for index, step in enumerate(template["scene_steps"], start=1):
            overlay_steps.append(
                {
                    "step_no": index,
                    "step_id": f"{request_id}_AR_STEP_{index:02d}",
                    "source_template_step_id": step["step_id"],
                    "camera": step["camera"],
                    "target_parts": step["parts"],
                    "action": step["action"],
                    "highlight": step.get("highlight"),
                    "subtitle_template_id": step.get("subtitle_template_id"),
                    "tts_template_id": step.get("tts_template_id"),
                    "ar_overlay_rendering": {
                        "mode": "reference_image_overlay",
                        "requires_part_anchor": True,
                        "allow_clean_reference": True,
                        "allow_annotated_overlay": True,
                    },
                }
            )

        official_asset_ids = [
            asset["asset_id"]
            for asset in official_match.get("official_assets", [])
        ]
        return {
            "ar_guide_plan_id": f"AR_GP_{request_id}",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "template_id": template["template_id"],
            "template_version": template["version"],
            "product_type": template["product_type"],
            "procedure_type": template["procedure_type"],
            "model_name": device["model_name"],
            "device_id": device["device_id"],
            "match_type": official_match["match_type"],
            "official_asset_ids": official_asset_ids,
            "risk_level": decision["risk_level"],
            "content_type": decision["content_type"],
            "service_flow_type": decision.get("service_flow_type"),
            "ar_scope": template.get("ar_scope") or decision.get("ar_scope"),
            "language": user["preferred_language"],
            "preferred_guide_style": preferred_guide_style,
            "reuse_decision": decision["reuse_decision"],
            "allowed_actions": template["allowed_actions"],
            "conditional_actions": template.get("conditional_actions", []),
            "forbidden_actions": sorted(
                set(template["forbidden_actions"]) | set(official_match.get("forbidden_actions", []))
            ),
            "forbidden_ar_notes": template["forbidden_generation_notes"],
            "step_count": len(overlay_steps),
            "overlay_steps": overlay_steps,
            "ar_accuracy_constraints": {
                "preserve_product_shape": True,
                "preserve_part_count": True,
                "preserve_cover_and_filter_direction": True,
                "forbid_text_label_hallucination": True,
                "separate_clean_reference_and_annotated_overlay": True,
            },
        }

    def ar_guide_usage(self, decision: dict[str, Any]) -> str:
        if decision["reuse_decision"] == "full_reuse":
            return "official_content_reference_plus_ar_session"
        if decision["reuse_decision"] == "partial_rerender":
            return "official_content_reference_plus_localized_ar_session"
        return "new_ar_guide_plan"

    def blocked_result(
        self,
        decision_bundle: dict[str, Any],
        reason: str,
        template: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return {
            "request_id": decision_bundle["request_id"],
            "status": "ar_guide_plan_blocked",
            "blocked_reason": reason,
            "selected_template_id": template["template_id"] if template else None,
            "ar_guide_plan": None,
        }


def run_demo(decision_result_path: str | Path) -> list[dict[str, Any]]:
    path = Path(decision_result_path)
    if not path.exists():
        raise FileNotFoundError(f"Decision result not found: {path}")

    decision_results = json.loads(path.read_text(encoding="utf-8"))
    selector = ARGuideTemplateSelector()
    ar_results = [selector.select_and_build(result) for result in decision_results]
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(ar_results, ensure_ascii=False, indent=2), encoding="utf-8")
    return ar_results


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--decision-result", help="Path to decision result JSON produced by the AI decision engine.")
    args = parser.parse_args()

    if args.decision_result:
        print(json.dumps(run_demo(args.decision_result), ensure_ascii=False, indent=2))
        return

    selector = ARGuideTemplateSelector()
    print(json.dumps({"loaded_template_count": len(selector.templates)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
