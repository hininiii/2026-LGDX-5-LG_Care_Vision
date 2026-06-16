from __future__ import annotations

import json

from app.evaluation_service import EvaluationService
from app.services import CareShotBackendService


def test_evaluation_service_runs_subset_and_writes_artifacts(tmp_path) -> None:
    service = CareShotBackendService()
    evaluator = EvaluationService(service)

    results_path = tmp_path / "intent_risk_eval_results.json"
    report_json_path = tmp_path / "intent_risk_accuracy_report.json"
    report_md_path = tmp_path / "intent_risk_accuracy_report.md"

    summary = evaluator.run_intent_risk_evaluation(
        results_path=results_path,
        report_json_path=report_json_path,
        report_md_path=report_md_path,
        limit=2,
        run_id="TEST_INTENT_RISK_EVAL",
    )

    assert summary["run_id"] == "TEST_INTENT_RISK_EVAL"
    assert summary["case_count"] == 2
    assert results_path.exists()
    assert report_json_path.exists()
    assert report_md_path.exists()

    results = json.loads(results_path.read_text(encoding="utf-8"))
    report = json.loads(report_json_path.read_text(encoding="utf-8"))

    assert len(results) == 2
    assert report["metrics"]["total_cases"] == 2
    assert "intent_accuracy" in report["metrics"]
    assert "risk_accuracy" in report["metrics"]
    assert "action_accuracy" in report["metrics"]
    assert "high_risk_recall" in report["metrics"]
    assert "no_match_precision" in report["metrics"]
    assert "failed_case_count" in report["metrics"]
    assert summary["report_date"]
    assert summary["legacy_results_path"]
    assert {"expected_intent", "predicted_intent", "error_type"}.issubset(results[0])


def test_evaluation_service_error_type_prioritizes_high_risk_miss() -> None:
    flags = {
        "is_intent_correct": False,
        "is_risk_correct": False,
        "is_action_correct": False,
        "is_procedure_correct": False,
        "is_ar_allowed_correct": False,
        "is_followup_question_correct": True,
    }

    error_type = EvaluationService.classify_error(
        {
            "expected_intent": "expert_as",
            "expected_risk": "high",
            "expected_action": "route_to_service",
            "expected_no_match": False,
        },
        {
            "predicted_intent": "self_as",
            "predicted_risk": "medium",
            "predicted_action": "prepare_ar_guide_session",
            "predicted_no_match": False,
        },
        flags,
        None,
    )

    assert error_type == "high_risk_missed"
