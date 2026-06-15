from __future__ import annotations

import json
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = next(path for path in PROJECT_DIR.iterdir() if path.name.startswith("02_"))


def test_intent_risk_eval_set_is_built_from_actual_voc_pool() -> None:
    cases_path = DATA_DIR / "mock_data" / "intent_risk_test_cases.json"
    coverage_path = DATA_DIR / "eval_sets" / "intent_risk_coverage_report_2026-06-12.json"
    label_log_path = DATA_DIR / "eval_sets" / "intent_risk_labeling_log_2026-06-12.json"

    cases = json.loads(cases_path.read_text(encoding="utf-8"))
    coverage = json.loads(coverage_path.read_text(encoding="utf-8"))
    label_logs = json.loads(label_log_path.read_text(encoding="utf-8"))

    assert coverage["raw_voc_count"] == 500
    assert coverage["selected_case_count"] == len(cases)
    assert coverage["excluded_case_count"] == 500 - len(cases)
    assert coverage["coverage_passed"] is True
    assert len(label_logs) == 500
    assert len(cases) >= 100

    required_fields = {
        "case_id",
        "message_text",
        "raw_message",
        "normalized_message",
        "translated_message",
        "product_type",
        "expected_intent",
        "expected_risk",
        "expected_action",
        "service_flow_type",
        "intent_type",
        "risk_level",
        "procedure_type",
        "primary_procedure",
        "secondary_procedures",
        "expected_ar_allowed",
        "expected_ar_scope",
        "expected_official_evidence_required",
        "expected_youtube_allowed",
        "expected_followup_question",
        "source_voc_case_id",
    }
    for case in cases:
        assert required_fields.issubset(case)
        assert case["case_id"].startswith("IR_VOC_")
        assert case["source_voc_case_id"].startswith("VOC_")
        assert case["message_text"] == case["normalized_message"]
        assert case["procedure_type"] == case["primary_procedure"]
        assert case["expected_intent"] in {"self_care", "self_as", "expert_as"}
        assert case["expected_risk"] in {"low", "medium", "high"}
        assert case["label_rule_id"] == "voc_rule_v1_2026_06_12"


def test_intent_risk_eval_set_has_required_label_coverage() -> None:
    coverage_path = DATA_DIR / "eval_sets" / "intent_risk_coverage_report_2026-06-12.json"
    coverage = json.loads(coverage_path.read_text(encoding="utf-8"))

    assert all(coverage["minimum_checks"].values())
    assert set(coverage["selected_by_product_type"]) == {
        "air_conditioner",
        "washing_machine",
        "air_purifier",
        "water_purifier",
    }
    assert set(coverage["selected_by_service_flow_type"]) == {"self_care", "self_as", "expert_as"}
    assert set(coverage["selected_by_risk_level"]) == {"low", "medium", "high"}
    assert int(coverage["selected_by_procedure_type"]["remote_operation"]) >= 1
    assert "policy_review_remote_operation" not in coverage["excluded_by_reason"]
    assert int(coverage["selected_by_followup_required"]["true"]) >= 5


def test_remote_operation_eval_cases_are_self_care_manual_only() -> None:
    cases_path = DATA_DIR / "mock_data" / "intent_risk_test_cases.json"
    cases = json.loads(cases_path.read_text(encoding="utf-8"))
    remote_cases = [case for case in cases if case["procedure_type"] == "remote_operation"]

    assert remote_cases
    for case in remote_cases:
        assert case["service_flow_type"] == "self_care"
        assert case["intent_type"] == "usage_help"
        assert case["expected_risk"] == "low"
        assert case["expected_action"] == "manual_or_service_guidance_only"
        assert case["expected_ar_allowed"] is False
        assert case["expected_ar_scope"] is None
        assert case["expected_youtube_allowed"] is True
