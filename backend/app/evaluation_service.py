from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4
from zoneinfo import ZoneInfo

from .path_setup import DATA_DIR, PROJECT_DIR


DEFAULT_CASES_PATH = DATA_DIR / "mock_data" / "intent_risk_test_cases.json"
DEFAULT_RESULTS_PATH = DATA_DIR / "mock_data" / "intent_risk_eval_results.json"
KST = ZoneInfo("Asia/Seoul")


DEVICE_BY_PRODUCT_TYPE = {
    "air_conditioner": "AS-Q24ENXE",
    "washing_machine": "T70SKSF1Z",
    "air_purifier": "FS10GPBK0",
    "water_purifier": "WW140NP",
}


NO_MATCH_ACTIONS = {"official_match_review_needed", "official_evidence_required"}


class EvaluationService:
    """Runs the intent/risk golden set through ChatbotEngine + DecisionEngineV2.

    The final 21-table SQLite schema intentionally does not include historical
    intent_risk_* tables. Evaluation outputs are therefore written to JSON/MD
    artifacts instead of altering the DB schema.
    """

    def __init__(self, backend_service: Any) -> None:
        self.backend_service = backend_service

    def run_intent_risk_evaluation(
        self,
        *,
        cases_path: str | Path | None = DEFAULT_CASES_PATH,
        results_path: str | Path | None = None,
        report_json_path: str | Path | None = None,
        report_md_path: str | Path | None = None,
        report_date: str | None = None,
        product_type: str | None = None,
        limit: int | None = None,
        run_id: str | None = None,
    ) -> dict[str, Any]:
        run_at = datetime.now(timezone.utc)
        report_date = report_date or run_at.astimezone(KST).date().isoformat()
        cases_path = Path(cases_path) if cases_path else DEFAULT_CASES_PATH
        output_paths = self.default_output_paths(report_date)
        results_path = Path(results_path) if results_path else output_paths["results_path"]
        report_json_path = Path(report_json_path) if report_json_path else output_paths["report_json_path"]
        report_md_path = Path(report_md_path) if report_md_path else output_paths["report_md_path"]

        cases = self.load_cases(cases_path)
        if product_type:
            cases = [case for case in cases if case.get("product_type") == product_type]
        if limit is not None:
            cases = cases[:limit]

        run_id = run_id or f"INTENT_RISK_EVAL_{run_at.strftime('%Y%m%dT%H%M%SZ')}_{uuid4().hex[:6].upper()}"
        evaluated_at = run_at.isoformat()
        results = [self.evaluate_case(case, run_id=run_id, evaluated_at=evaluated_at) for case in cases]
        report = self.build_report(
            run_id=run_id,
            evaluated_at=evaluated_at,
            cases_path=Path(cases_path),
            results_path=Path(results_path),
            cases=cases,
            results=results,
        )

        self.write_json(results_path, results)
        self.write_json(report_json_path, report)
        self.write_json(DEFAULT_RESULTS_PATH, results)
        self.write_markdown_report(report_md_path, report)

        return {
            "run_id": run_id,
            "evaluated_at": evaluated_at,
            "case_count": len(cases),
            "report_date": report_date,
            "results_path": str(Path(results_path)),
            "report_json_path": str(Path(report_json_path)),
            "report_md_path": str(Path(report_md_path)),
            "legacy_results_path": str(DEFAULT_RESULTS_PATH),
            "metrics": report["metrics"],
            "error_type_counts": report["error_type_counts"],
        }

    @staticmethod
    def default_output_paths(report_date: str) -> dict[str, Path]:
        compact_date = report_date.replace("-", "")
        return {
            "results_path": DATA_DIR / "eval_sets" / f"intent_risk_eval_results_{compact_date}.json",
            "report_json_path": DATA_DIR / "eval_sets" / f"intent_risk_accuracy_report_{compact_date}.json",
            "report_md_path": PROJECT_DIR / "06_산출물" / f"{report_date}_intent_risk_accuracy_report.md",
        }

    @staticmethod
    def load_cases(cases_path: str | Path) -> list[dict[str, Any]]:
        path = Path(cases_path)
        return json.loads(path.read_text(encoding="utf-8"))

    @staticmethod
    def write_json(path: str | Path, payload: Any) -> None:
        output_path = Path(path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    def evaluate_case(self, case: dict[str, Any], *, run_id: str, evaluated_at: str) -> dict[str, Any]:
        expected = self.expected_labels(case)
        prediction: dict[str, Any]
        error_message = None
        try:
            prediction = self.predict_case(case)
        except Exception as exc:  # pragma: no cover - captured in output for operational runs
            error_message = str(exc)
            prediction = {
                "predicted_intent": None,
                "predicted_risk": None,
                "predicted_action": None,
                "predicted_procedure_type": None,
                "predicted_ar_allowed": None,
                "predicted_followup_question": None,
                "predicted_no_match": False,
                "analysis_excerpt": {},
            }

        flags = {
            "is_intent_correct": prediction["predicted_intent"] == expected["expected_intent"],
            "is_risk_correct": prediction["predicted_risk"] == expected["expected_risk"],
            "is_action_correct": prediction["predicted_action"] == expected["expected_action"],
            "is_procedure_correct": prediction["predicted_procedure_type"] == expected["expected_procedure_type"],
            "is_ar_allowed_correct": prediction["predicted_ar_allowed"] == expected["expected_ar_allowed"],
            "is_followup_question_correct": prediction["predicted_followup_question"] == expected["expected_followup_question"],
        }
        error_type = self.classify_error(expected, prediction, flags, error_message)

        return {
            "eval_result_id": f"EVAL_{case.get('case_id')}",
            "run_id": run_id,
            "case_id": case.get("case_id"),
            "source_voc_case_id": case.get("source_voc_case_id"),
            "product_type": case.get("product_type"),
            "model_name": case.get("model_name"),
            "message_text": case.get("message_text"),
            **expected,
            **prediction,
            **flags,
            "error_type": error_type,
            "error_message": error_message,
            "evaluated_at": evaluated_at,
        }

    def predict_case(self, case: dict[str, Any]) -> dict[str, Any]:
        message = case.get("message_text") or case.get("normalized_message") or case.get("raw_message") or ""
        device_id = self.resolve_device_id(case)
        user_id = self.resolve_user_id(device_id)
        payload = {
            "user_id": user_id,
            "device_id": device_id,
            "message": message,
            "request_id": f"EVAL_{case.get('case_id')}",
            "include_rag_evidence": True,
            "rag_limit": 3,
        }

        chatbot_engine = self.backend_service.chatbot_engine
        turn_context = chatbot_engine.prepare_turn_context(payload, None)
        analysis_payload = {
            **payload,
            "original_message": turn_context["original_message"],
            "message": turn_context["analysis_message"],
        }
        analysis = self.backend_service.decision_engine.analyze(
            user_id=user_id,
            device_id=device_id,
            message=analysis_payload["message"],
            request_id=analysis_payload["request_id"],
        )

        if turn_context["state_status"] == "collecting":
            chatbot_engine.apply_clarification_gate(analysis, turn_context)
        else:
            analysis["rag_evidence"] = self.backend_service.search_rag_for_analysis(analysis_payload, analysis)
            llm_assist = chatbot_engine.assist_with_llm(analysis_payload, turn_context, analysis, None, None)
            chatbot_engine.apply_decision_v2(analysis_payload, turn_context, analysis, llm_assist)

        decision = analysis.get("decision_result") or {}
        decision_v2 = analysis.get("decision_v2") or {}
        procedure = analysis.get("procedure") or {}
        clarification = analysis.get("clarification") or {}
        predicted_action = decision_v2.get("decision_action") or decision.get("decision_action")
        predicted_intent = (
            decision_v2.get("service_flow_type")
            or decision.get("service_flow_type")
            or (analysis.get("intent") or {}).get("service_flow_type")
        )
        predicted_risk = decision_v2.get("risk_level") or decision.get("risk_level")

        rag_evidence = analysis.get("rag_evidence") or {}
        official_match = analysis.get("official_asset_match") or {}
        return {
            "predicted_intent": predicted_intent,
            "predicted_risk": predicted_risk,
            "predicted_action": predicted_action,
            "predicted_procedure_type": procedure.get("procedure_type"),
            "predicted_ar_allowed": bool(decision.get("ar_guide_allowed")),
            "predicted_followup_question": bool(clarification.get("required") or predicted_action == "ask_clarification"),
            "predicted_no_match": predicted_action in NO_MATCH_ACTIONS,
            "analysis_excerpt": {
                "device_id": device_id,
                "user_id": user_id,
                "turn_state_status": turn_context.get("state_status"),
                "missing_slots": turn_context.get("missing_slots"),
                "official_match_status": official_match.get("match_status"),
                "rag_result_count": rag_evidence.get("result_count"),
                "rag_skipped": rag_evidence.get("skipped"),
                "decision_v2_source": decision_v2.get("source_engine"),
                "blocked_reason": decision_v2.get("blocked_reason") or decision.get("blocked_reason"),
                "ar_scope": decision_v2.get("ar_scope") or decision.get("ar_scope"),
                "secondary_procedures": procedure.get("secondary_procedures"),
            },
        }

    def resolve_device_id(self, case: dict[str, Any]) -> str:
        product_type = case.get("product_type")
        model_name = case.get("model_name")
        if model_name:
            try:
                device = self.backend_service.repo.get_device_context(model_name)
                if device and (not product_type or device.get("product_type") == product_type):
                    return str(model_name)
            except Exception:
                pass
        return DEVICE_BY_PRODUCT_TYPE.get(product_type, "AS-Q24ENXE")

    def resolve_user_id(self, device_id: str) -> str:
        try:
            device = self.backend_service.repo.get_device_context(device_id) or {}
        except Exception:
            return "U001"
        return device.get("user_id") or "U001"

    @staticmethod
    def expected_labels(case: dict[str, Any]) -> dict[str, Any]:
        return {
            "expected_intent": case.get("expected_intent") or case.get("service_flow_type"),
            "expected_risk": case.get("expected_risk") or case.get("risk_level"),
            "expected_action": case.get("expected_action"),
            "expected_procedure_type": case.get("procedure_type") or case.get("primary_procedure"),
            "expected_ar_allowed": bool(case.get("expected_ar_allowed")),
            "expected_followup_question": bool(case.get("expected_followup_question")),
            "expected_no_match": case.get("expected_action") in NO_MATCH_ACTIONS,
        }

    @staticmethod
    def classify_error(
        expected: dict[str, Any],
        prediction: dict[str, Any],
        flags: dict[str, bool],
        error_message: str | None,
    ) -> str | None:
        if error_message:
            return "runtime_error"
        expected_high = expected["expected_risk"] == "high" or expected["expected_intent"] == "expert_as"
        predicted_high = (
            prediction["predicted_risk"] == "high"
            or prediction["predicted_intent"] == "expert_as"
            or prediction["predicted_action"] == "route_to_service"
        )
        if expected_high and not predicted_high:
            return "high_risk_missed"
        if prediction["predicted_no_match"] and not expected["expected_no_match"]:
            return "no_match_false_positive"
        if not flags["is_followup_question_correct"]:
            return "clarification_error"
        if not flags["is_intent_correct"]:
            return "intent_mismatch"
        if not flags["is_risk_correct"]:
            return "risk_mismatch"
        if not flags["is_action_correct"]:
            return "action_mismatch"
        if not flags["is_procedure_correct"]:
            return "procedure_mismatch"
        if not flags["is_ar_allowed_correct"]:
            return "ar_permission_mismatch"
        return None

    def build_report(
        self,
        *,
        run_id: str,
        evaluated_at: str,
        cases_path: Path,
        results_path: Path,
        cases: list[dict[str, Any]],
        results: list[dict[str, Any]],
    ) -> dict[str, Any]:
        total = len(results)
        expected_high = [row for row in results if row["expected_risk"] == "high" or row["expected_intent"] == "expert_as"]
        high_risk_hits = [
            row
            for row in expected_high
            if row["predicted_risk"] == "high"
            or row["predicted_intent"] == "expert_as"
            or row["predicted_action"] == "route_to_service"
        ]
        expected_no_match = [row for row in results if row["expected_no_match"]]
        predicted_no_match = [row for row in results if row["predicted_no_match"]]
        no_match_true_positive = [row for row in predicted_no_match if row["expected_no_match"]]
        metrics = {
            "total_cases": total,
            "intent_accuracy": self.ratio(sum(row["is_intent_correct"] for row in results), total),
            "risk_accuracy": self.ratio(sum(row["is_risk_correct"] for row in results), total),
            "action_accuracy": self.ratio(sum(row["is_action_correct"] for row in results), total),
            "procedure_accuracy": self.ratio(sum(row["is_procedure_correct"] for row in results), total),
            "ar_allowed_accuracy": self.ratio(sum(row["is_ar_allowed_correct"] for row in results), total),
            "clarification_accuracy": self.ratio(sum(row["is_followup_question_correct"] for row in results), total),
            "high_risk_recall": self.ratio(len(high_risk_hits), len(expected_high)),
            "no_match_precision": self.ratio(len(no_match_true_positive), len(predicted_no_match)),
            "expected_high_risk_count": len(expected_high),
            "expected_no_match_count": len(expected_no_match),
            "predicted_no_match_count": len(predicted_no_match),
            "no_match_true_positive_count": len(no_match_true_positive),
            "failed_case_count": sum(1 for row in results if row.get("error_type")),
        }
        return {
            "run_id": run_id,
            "evaluated_at": evaluated_at,
            "cases_path": str(cases_path),
            "results_path": str(results_path),
            "case_count": total,
            "metrics": metrics,
            "label_distribution": {
                "expected_intent": dict(Counter(row.get("expected_intent") for row in results)),
                "predicted_intent": dict(Counter(row.get("predicted_intent") for row in results)),
                "expected_risk": dict(Counter(row.get("expected_risk") for row in results)),
                "predicted_risk": dict(Counter(row.get("predicted_risk") for row in results)),
                "expected_action": dict(Counter(row.get("expected_action") for row in results)),
                "predicted_action": dict(Counter(row.get("predicted_action") for row in results)),
            },
            "error_type_counts": dict(Counter(row.get("error_type") or "correct" for row in results)),
            "failed_cases": [
                self.failure_summary(row)
                for row in results
                if row.get("error_type")
            ],
            "decision_after_evaluation": {
                "rule_fix_applied_in_this_step": (
                    "High-risk keywords were extended with fire/flame/burnt/burn out, "
                    "and high-risk decisions now force procedure_type=high_risk_troubleshooting."
                ),
                "next_rule_corrections": [
                    "Clarification gate is too aggressive for long VOC paragraphs that already contain enough symptom context.",
                    "Remote/mode keyword matching still creates false remote_operation matches in washing machine and air purifier VOC text.",
                    "Air purifier filter replacement and filter cleaning need clearer procedure priority.",
                    "Official RAG coverage gaps for non-AC procedures cause official_evidence_required false positives.",
                ],
                "llm_adapter_decision": (
                    "LLM adapter should be used as non-authoritative extraction assistance for mixed Hindi/English long VOC text, "
                    "especially symptom summary, product family, and clarification necessity."
                ),
                "training_classifier_decision": (
                    "Do not introduce a separate training-based classifier yet. The 147-case set is currently a golden evaluation set; "
                    "rule/RAG/LLM-adapter corrections should be tried before fine-tuning or local classifier training."
                ),
            },
            "notes": [
                "Evaluation output is file-based because the final SQLite schema is frozen at 21 persisted tables.",
                "expected_intent means expected service_flow_type: self_care, self_as, or expert_as.",
                "no_match_precision treats official_match_review_needed/official_evidence_required as predicted no-match actions.",
                "LLM is not the final authority; rules, RAG evidence, and DecisionEngineV2 remain authoritative.",
            ],
        }

    @staticmethod
    def ratio(numerator: int, denominator: int) -> float | None:
        if denominator <= 0:
            return None
        return round(numerator / denominator, 4)

    @staticmethod
    def failure_summary(row: dict[str, Any]) -> dict[str, Any]:
        return {
            "case_id": row.get("case_id"),
            "product_type": row.get("product_type"),
            "procedure_type": row.get("expected_procedure_type"),
            "error_type": row.get("error_type"),
            "expected": {
                "intent": row.get("expected_intent"),
                "risk": row.get("expected_risk"),
                "action": row.get("expected_action"),
                "procedure_type": row.get("expected_procedure_type"),
                "ar_allowed": row.get("expected_ar_allowed"),
                "followup_question": row.get("expected_followup_question"),
            },
            "predicted": {
                "intent": row.get("predicted_intent"),
                "risk": row.get("predicted_risk"),
                "action": row.get("predicted_action"),
                "procedure_type": row.get("predicted_procedure_type"),
                "ar_allowed": row.get("predicted_ar_allowed"),
                "followup_question": row.get("predicted_followup_question"),
            },
            "message_text": row.get("message_text"),
            "analysis_excerpt": row.get("analysis_excerpt"),
        }

    @staticmethod
    def write_markdown_report(path: str | Path, report: dict[str, Any]) -> None:
        output_path = Path(path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        metrics = report["metrics"]
        lines = [
            "# intent/risk EvaluationService 정확도 리포트",
            "",
            f"- run_id: `{report['run_id']}`",
            f"- evaluated_at: `{report['evaluated_at']}`",
            f"- 평가 케이스 수: {report['case_count']}",
            f"- 결과 JSON: `{report['results_path']}`",
            "",
            "## 핵심 정확도",
            "",
            "| Metric | Value |",
            "|---|---:|",
        ]
        for key in [
            "intent_accuracy",
            "risk_accuracy",
            "action_accuracy",
            "procedure_accuracy",
            "ar_allowed_accuracy",
            "clarification_accuracy",
            "high_risk_recall",
            "no_match_precision",
        ]:
            lines.append(f"| {key} | {metrics.get(key)} |")
        lines.extend(
            [
                "",
                "## 분포",
                "",
                "```json",
                json.dumps(report["label_distribution"], ensure_ascii=False, indent=2),
                "```",
                "",
                "## Error Type Counts",
                "",
                "```json",
                json.dumps(report["error_type_counts"], ensure_ascii=False, indent=2),
                "```",
                "",
                "## 실패 케이스 목록",
                "",
            ]
        )
        for failure in report["failed_cases"][:80]:
            lines.extend(
                [
                    f"### {failure['case_id']} - {failure['error_type']}",
                    "",
                    f"- product_type: `{failure['product_type']}`",
                    f"- expected: `{failure['expected']}`",
                    f"- predicted: `{failure['predicted']}`",
                    f"- message: {failure['message_text']}",
                    "",
                ]
            )
        if len(report["failed_cases"]) > 80:
            lines.append(f"- 실패 케이스가 {len(report['failed_cases'])}건이라 상위 80건만 표시했다. 전체는 결과 JSON을 확인한다.")
            lines.append("")
        lines.extend(["## 비고", ""])
        lines.extend(f"- {note}" for note in report["notes"])
        lines.extend(
            [
                "",
                "## 평가 후 결정",
                "",
                "```json",
                json.dumps(report["decision_after_evaluation"], ensure_ascii=False, indent=2),
                "```",
            ]
        )
        output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
