from __future__ import annotations

import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = SCRIPT_DIR.parent
PROJECT_DIR = BACKEND_DIR.parent
DATA_DIR = next(path for path in PROJECT_DIR.iterdir() if path.name.startswith("02_"))
OUTPUT_DIR = next(path for path in PROJECT_DIR.iterdir() if path.name.startswith("06_"))
MOCK_DIR = DATA_DIR / "mock_data"
SOURCE_VOC_PATH = DATA_DIR / "source_data" / "voc" / "raw_voc_cases.jsonl"
EVAL_DIR = DATA_DIR / "eval_sets"

GENERATED_AT = datetime.now(timezone.utc).isoformat()
RUN_DATE = "2026-06-12"


SERVICE_FLOW_TO_INTENT = {
    "self_care": "care",
    "self_as": "self_check",
    "expert_as": "high_risk",
}

PRODUCT_MODEL_DEFAULTS = {
    "air_conditioner": "AS-Q24ENXE",
    "washing_machine": "FHD1207STB",
    "air_purifier": "AS60GDWT0",
    "water_purifier": "WW140NP",
}

PRODUCT_OWN_PATTERNS = {
    "air_conditioner": [
        r"air conditioner",
        r"\bac\b",
        r"cooling",
        r"split",
        r"inverter",
    ],
    "washing_machine": [
        r"washing machine",
        r"washer",
        r"laundry",
        r"clothes",
        r"drum",
        r"tub",
    ],
    "air_purifier": [
        r"air purifier",
        r"purifier",
        r"air quality",
        r"hepa",
        r"\baqi\b",
    ],
    "water_purifier": [
        r"water purifier",
        r"\bro\b",
        r"\btds\b",
        r"filter",
        r"water",
    ],
}

PRODUCT_OTHER_PATTERNS = {
    "air_conditioner": [r"washing machine", r"washer", r"laundry", r"water purifier", r"air purifier"],
    "washing_machine": [r"air conditioner", r"\bac\b", r"air purifier", r"water purifier"],
    "air_purifier": [r"air conditioner", r"\bac\b", r"washing machine", r"washer", r"water purifier"],
    "water_purifier": [r"air conditioner", r"\bac\b", r"washing machine", r"washer", r"air purifier"],
}

OUT_OF_SCOPE_PATTERNS = [
    r"\bprice\b",
    r"\bbuy\b",
    r"\bbought\b",
    r"\bpurchas",
    r"\bwarranty\b",
    r"\brecommend",
    r"\bcomparison\b",
    r"\bcompare\b",
    r"\bstar\b",
    r"\baffiliate\b",
    r"wrong information",
    r"please make a video",
    r"brand",
    r"market",
    r"\bbill\b",
    r"electricity saving",
    r"budget",
]

HIGH_RISK_PATTERNS = [
    r"burning smell",
    r"\bsmoke\b",
    r"\bspark",
    r"electric shock",
    r"gas leak",
    r"gas leakage",
    r"refrigerant.*(leak|charging|refill|repair)",
    r"\bwiring\b",
    r"wire.*(spark|burn|repair|heat)",
    r"power board.*(spark|burn|repair)",
    r"\bfire\b",
    r"internal disassembly",
    r"open.*(pcb|compressor|internal)",
    r"(repair|replace|change).*(pcb|compressor|wiring|wire)",
    r"(pcb|compressor).*(repair|replace|change|damaged|khrab|fault)",
]

HIGH_RISK_OUT_OF_SCOPE_OVERRIDE_PATTERNS = [
    r"gas leak",
    r"gas leakage",
    r"\bwiring\b",
    r"burning smell",
    r"\bsmoke\b",
    r"\bspark",
    r"electric shock",
    r"(pcb|compressor).*(damaged|khrab|fault)",
]

PROCEDURE_RULES = [
    (
        "power_troubleshooting",
        [
            r"no power",
            r"power.*(off|cut|trip)",
            r"(turns|turn|switch).*off",
            r"not start",
            r"doesn.?t start",
            r"not working",
        ],
    ),
    (
        "water_leak_monsoon",
        [
            r"water.*(leak|drip|drain)",
            r"pani.*(leak|nikal)",
            r"(leakage|leaking|dripping|drainage)",
        ],
    ),
    (
        "noise_self_check",
        [
            r"noise problem",
            r"\bnoise\b",
            r"vibration",
            r"rattl",
            r"hissing",
            r"\bsound (aa|coming|problem)",
            r"awaz",
        ],
    ),
    (
        "odor_self_check",
        [
            r"bad smell",
            r"\bsmell\b",
            r"\bodor\b",
            r"mold",
            r"musty",
            r"smeel",
        ],
    ),
    (
        "no_cooling_self_check",
        [
            r"not cooling",
            r"low cooling",
            r"cooling.*(problem|issue|not|less)",
            r"weak airflow",
            r"not cold",
            r"warm air",
        ],
    ),
    (
        "remote_operation",
        [
            r"\bremote\b",
            r"\btimer\b",
            r"\bmode\b",
        ],
    ),
    (
        "filter_cleaning",
        [
            r"filter.*(clean|wash|dust)",
            r"(clean|wash).*filter",
            r"clean filters",
        ],
    ),
    (
        "filter_replacement",
        [
            r"filter.*(replace|change|replacement)",
            r"(replace|change).*filter",
        ],
    ),
    (
        "tub_clean",
        [
            r"tub clean",
            r"drum.*clean",
            r"washing machine.*smell",
            r"washer.*smell",
        ],
    ),
    (
        "limescale_care",
        [
            r"limescale",
            r"hard water",
            r"scale deposit",
            r"\btds\b",
        ],
    ),
]

CARE_PROCEDURES = {"filter_cleaning", "filter_replacement", "tub_clean", "limescale_care"}
USAGE_HELP_PROCEDURES = {"remote_operation"}

def has_any(text: str, patterns: list[str]) -> bool:
    return any(re.search(pattern, text) for pattern in patterns)


def matched_patterns(text: str, patterns: list[str]) -> list[str]:
    return [pattern for pattern in patterns if re.search(pattern, text)]


def normalize_text(row: dict[str, Any]) -> str:
    return str(row.get("english_text") or row.get("raw_text") or "").strip()


def is_product_mismatch(product_type: str, text: str) -> bool:
    own = PRODUCT_OWN_PATTERNS.get(product_type, [])
    other = PRODUCT_OTHER_PATTERNS.get(product_type, [])
    return has_any(text, other) and not has_any(text, own)


def all_matched_procedures(text: str) -> list[str]:
    procedures: list[str] = []
    for procedure, patterns in PROCEDURE_RULES:
        if has_any(text, patterns):
            procedures.append(procedure)
    return procedures


def is_ambiguous_followup_needed(text: str, procedure_type: str, service_flow_type: str) -> bool:
    if service_flow_type != "self_as":
        return False
    if procedure_type == "power_troubleshooting" and re.search(r"suddenly turns off|gas leakage|smoke|spark", text):
        return False
    token_count = len(re.findall(r"[a-z0-9]+", text))
    lacks_location = not has_any(
        text,
        [
            r"indoor",
            r"outdoor",
            r"outlet",
            r"filter",
            r"front",
            r"drain",
            r"pipe",
            r"plug",
            r"wire",
            r"unit",
            r"room",
        ],
    )
    lacks_risk_signal = not has_any(text, HIGH_RISK_PATTERNS + [r"no smoke", r"no spark", r"no burning"])
    if procedure_type in {"odor_self_check", "water_leak_monsoon", "noise_self_check", "no_cooling_self_check"}:
        return token_count <= 8 or (lacks_location and lacks_risk_signal)
    if procedure_type == "power_troubleshooting":
        return token_count <= 8
    return False


def classify_row(row: dict[str, Any]) -> dict[str, Any]:
    normalized = normalize_text(row)
    text = normalized.lower()
    product_type = row.get("product_type") or "unknown"
    procedures = all_matched_procedures(text)
    high_risk_match = has_any(text, HIGH_RISK_PATTERNS)
    out_of_scope_match = has_any(text, OUT_OF_SCOPE_PATTERNS)

    if is_product_mismatch(product_type, text):
        return excluded(row, normalized, "product_text_mismatch", procedures)

    if high_risk_match and (not out_of_scope_match or has_any(text, HIGH_RISK_OUT_OF_SCOPE_OVERRIDE_PATTERNS)):
        return selected(row, normalized, "expert_as", "high", "high_risk_troubleshooting", [], False)

    if out_of_scope_match and not procedures:
        return excluded(row, normalized, "out_of_scope_purchase_price_warranty_or_general_comment", procedures)

    if not procedures:
        return excluded(row, normalized, "no_project_symptom_or_care_signal", procedures)

    primary = procedures[0]
    if primary in USAGE_HELP_PROCEDURES and not has_any(text, PRODUCT_OWN_PATTERNS.get(product_type, [])):
        return excluded(row, normalized, "product_text_mismatch", procedures)

    if out_of_scope_match and primary in CARE_PROCEDURES:
        strong_care = has_any(
            text,
            [
                r"clean filters",
                r"filter.*(clean|replace|change)",
                r"(clean|wash).*filter",
                r"hard water",
                r"limescale",
                r"scale deposit",
            ],
        )
        if not strong_care:
            return excluded(row, normalized, "out_of_scope_mixed_purchase_context", procedures)

    if out_of_scope_match and primary in USAGE_HELP_PROCEDURES:
        return excluded(row, normalized, "out_of_scope_mixed_purchase_context", procedures)

    secondary = [procedure for procedure in procedures[1:] if procedure != primary]
    if primary in CARE_PROCEDURES:
        return selected(row, normalized, "self_care", "low", primary, secondary, False)
    if primary in USAGE_HELP_PROCEDURES:
        return selected(row, normalized, "self_care", "low", primary, secondary, False)

    followup_needed = is_ambiguous_followup_needed(text, primary, "self_as")
    return selected(row, normalized, "self_as", "medium", primary, secondary, followup_needed)


def selected(
    row: dict[str, Any],
    normalized: str,
    service_flow_type: str,
    risk_level: str,
    procedure_type: str,
    secondary_procedures: list[str],
    followup_needed: bool,
) -> dict[str, Any]:
    if service_flow_type == "expert_as":
        expected_action = "route_to_service"
        expected_ar_allowed = False
        expected_ar_scope = None
        expected_youtube_allowed = False
        blocked_reason = "high_risk"
    elif followup_needed:
        expected_action = "ask_clarification"
        expected_ar_allowed = False
        expected_ar_scope = None
        expected_youtube_allowed = False
        blocked_reason = "ambiguous_slots"
    elif procedure_type == "power_troubleshooting":
        expected_action = "prepare_limited_ar_safe_check"
        expected_ar_allowed = True
        expected_ar_scope = "external_safe_check_only"
        expected_youtube_allowed = True
        blocked_reason = None
    elif procedure_type == "remote_operation":
        expected_action = "manual_or_service_guidance_only"
        expected_ar_allowed = False
        expected_ar_scope = None
        expected_youtube_allowed = True
        blocked_reason = None
    elif service_flow_type == "self_care":
        expected_action = "prepare_ar_guide_session"
        expected_ar_allowed = True
        expected_ar_scope = "user_accessible_care"
        expected_youtube_allowed = True
        blocked_reason = None
    else:
        expected_action = "prepare_ar_guide_session"
        expected_ar_allowed = True
        expected_ar_scope = "limited_self_check"
        expected_youtube_allowed = True
        blocked_reason = None

    intent_type = "usage_help" if procedure_type == "remote_operation" else SERVICE_FLOW_TO_INTENT[service_flow_type]
    case_id = f"IR_{row['voc_case_id']}"
    required_slots = []
    if followup_needed:
        required_slots = ["risk_signal", "symptom_location"]
        if procedure_type in {"odor_self_check", "water_leak_monsoon", "no_cooling_self_check"}:
            required_slots.append("environment_context")

    raw_json = {
        "source_voc_case_id": row.get("voc_case_id"),
        "raw_message": row.get("raw_text") or "",
        "normalized_message": normalized,
        "translated_message": row.get("english_text") or normalized,
        "korean_translation": row.get("korean_translation") or "",
        "language_hint": row.get("language_hint"),
        "source_type": row.get("source_type"),
        "source_path": row.get("source_path"),
        "source_url": row.get("source_url"),
        "source_row_index": row.get("source_row_index"),
        "evidence_level": row.get("evidence_level"),
        "pain_tags": row.get("pain_tags") or [],
        "service_flow_type": service_flow_type,
        "intent_type": intent_type,
        "risk_level": risk_level,
        "procedure_type": procedure_type,
        "primary_procedure": procedure_type,
        "secondary_procedures": secondary_procedures,
        "expected_action": expected_action,
        "expected_ar_allowed": expected_ar_allowed,
        "expected_ar_scope": expected_ar_scope,
        "expected_official_evidence_required": service_flow_type != "expert_as",
        "expected_youtube_allowed": expected_youtube_allowed,
        "expected_followup_question": followup_needed,
        "blocked_reason": blocked_reason,
        "label_confidence": "high" if not followup_needed else "medium",
        "label_rule_id": "voc_rule_v1_2026_06_12",
        "label_notes": "Derived from actual VOC source row using 2026-06-12 intent/risk label guide.",
    }

    return {
        "selected": True,
        "case": {
            "case_id": case_id,
            "message_text": normalized,
            "language": row.get("language_hint") or "mixed_or_unknown",
            "product_type": row.get("product_type"),
            "model_name": PRODUCT_MODEL_DEFAULTS.get(row.get("product_type"), ""),
            "expected_intent": service_flow_type,
            "expected_risk": risk_level,
            "expected_action": expected_action,
            "expected_required_slots_json": json.dumps(required_slots, ensure_ascii=False),
            "tags_json": json.dumps(
                [
                    row.get("source_type"),
                    service_flow_type,
                    risk_level,
                    procedure_type,
                    "actual_voc",
                ],
                ensure_ascii=False,
            ),
            "created_at": GENERATED_AT,
            "raw_json": json.dumps(raw_json, ensure_ascii=False, sort_keys=True),
            **raw_json,
        },
        "log": {
            "voc_case_id": row.get("voc_case_id"),
            "selected": True,
            "case_id": case_id,
            "product_type": row.get("product_type"),
            "service_flow_type": service_flow_type,
            "risk_level": risk_level,
            "procedure_type": procedure_type,
            "expected_action": expected_action,
            "expected_ar_allowed": expected_ar_allowed,
            "expected_followup_question": followup_needed,
            "source_type": row.get("source_type"),
            "source_row_index": row.get("source_row_index"),
        },
    }


def excluded(
    row: dict[str, Any],
    normalized: str,
    reason: str,
    procedures: list[str],
) -> dict[str, Any]:
    return {
        "selected": False,
        "case": None,
        "log": {
            "voc_case_id": row.get("voc_case_id"),
            "selected": False,
            "exclude_reason": reason,
            "matched_procedures": procedures,
            "product_type": row.get("product_type"),
            "source_type": row.get("source_type"),
            "source_row_index": row.get("source_row_index"),
            "message_preview": normalized[:180],
        },
    }


def load_raw_voc() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with SOURCE_VOC_PATH.open("r", encoding="utf-8") as file:
        for line in file:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def counter_dict(counter: Counter) -> dict[str, int]:
    return {str(key): value for key, value in sorted(counter.items(), key=lambda item: str(item[0]))}


def build_coverage(cases: list[dict[str, Any]], logs: list[dict[str, Any]], raw_count: int) -> dict[str, Any]:
    selected_logs = [log for log in logs if log["selected"]]
    excluded_logs = [log for log in logs if not log["selected"]]
    product_counter = Counter(case["product_type"] for case in cases)
    intent_counter = Counter(case["service_flow_type"] for case in cases)
    risk_counter = Counter(case["risk_level"] for case in cases)
    procedure_counter = Counter(case["procedure_type"] for case in cases)
    action_counter = Counter(case["expected_action"] for case in cases)
    followup_counter = Counter(str(case["expected_followup_question"]).lower() for case in cases)
    source_counter = Counter(log["source_type"] for log in selected_logs)
    excluded_counter = Counter(log["exclude_reason"] for log in excluded_logs)

    minimums = {
        "raw_pool_size_is_500": raw_count == 500,
        "selected_cases_at_least_100": len(cases) >= 100,
        "each_product_at_least_20": all(product_counter.get(product, 0) >= 20 for product in PRODUCT_MODEL_DEFAULTS),
        "self_care_at_least_20": intent_counter.get("self_care", 0) >= 20,
        "self_as_at_least_20": intent_counter.get("self_as", 0) >= 20,
        "expert_as_at_least_10": intent_counter.get("expert_as", 0) >= 10,
        "low_medium_high_each_at_least_10": all(risk_counter.get(risk, 0) >= 10 for risk in ["low", "medium", "high"]),
        "followup_cases_at_least_5": followup_counter.get("true", 0) >= 5,
    }

    return {
        "generated_at": GENERATED_AT,
        "source_path": str(SOURCE_VOC_PATH.relative_to(PROJECT_DIR)),
        "raw_voc_count": raw_count,
        "selected_case_count": len(cases),
        "excluded_case_count": len(excluded_logs),
        "coverage_passed": all(minimums.values()),
        "minimum_checks": minimums,
        "selected_by_product_type": counter_dict(product_counter),
        "selected_by_service_flow_type": counter_dict(intent_counter),
        "selected_by_risk_level": counter_dict(risk_counter),
        "selected_by_procedure_type": counter_dict(procedure_counter),
        "selected_by_expected_action": counter_dict(action_counter),
        "selected_by_followup_required": counter_dict(followup_counter),
        "selected_by_source_type": counter_dict(source_counter),
        "excluded_by_reason": counter_dict(excluded_counter),
    }


def write_markdown_reports(coverage: dict[str, Any], logs: list[dict[str, Any]]) -> None:
    coverage_md = OUTPUT_DIR / f"{RUN_DATE}_intent_risk_coverage_report.md"
    label_log_md = OUTPUT_DIR / f"{RUN_DATE}_intent_risk_labeling_log.md"

    coverage_lines = [
        "# intent/risk VOC 평가셋 coverage report",
        "",
        f"생성일: {GENERATED_AT}",
        "",
        "## 요약",
        "",
        f"- 원천 VOC: {coverage['raw_voc_count']}건",
        f"- 평가셋 선별: {coverage['selected_case_count']}건",
        f"- 제외: {coverage['excluded_case_count']}건",
        f"- coverage passed: {coverage['coverage_passed']}",
        "",
        "## 최소 기준 체크",
        "",
    ]
    for key, value in coverage["minimum_checks"].items():
        coverage_lines.append(f"- {key}: {value}")

    for title, key in [
        ("제품군", "selected_by_product_type"),
        ("service_flow_type", "selected_by_service_flow_type"),
        ("risk_level", "selected_by_risk_level"),
        ("procedure_type", "selected_by_procedure_type"),
        ("expected_action", "selected_by_expected_action"),
        ("followup", "selected_by_followup_required"),
        ("source_type", "selected_by_source_type"),
        ("제외 사유", "excluded_by_reason"),
    ]:
        coverage_lines.extend(["", f"## {title}", ""])
        for item_key, count in coverage[key].items():
            coverage_lines.append(f"- {item_key}: {count}")

    coverage_lines.extend(
        [
            "",
            "## 해석",
            "",
            "- 실제 VOC 500건 원천 풀에서 프로젝트 관련 문의만 선별했다.",
            "- 구매/가격/보증/추천/일반 리뷰성 문장은 정답 평가셋에서 제외했다.",
            "- 제품군 추정과 본문 제품이 충돌하는 행은 `product_text_mismatch`로 제외했다.",
            "- `remote_operation`은 2026-06-12 정책 확정에 따라 `self_care`/`low`/`manual_or_service_guidance_only`/AR false/YouTube true 평가 케이스로 포함했다.",
        ]
    )
    coverage_md.write_text("\n".join(coverage_lines) + "\n", encoding="utf-8")

    selected = [log for log in logs if log["selected"]]
    excluded = [log for log in logs if not log["selected"]]
    label_lines = [
        "# intent/risk VOC 라벨링 로그",
        "",
        f"생성일: {GENERATED_AT}",
        "",
        "## 생성 방식",
        "",
        "- 입력: `02_데이터연동/source_data/voc/raw_voc_cases.jsonl`",
        "- 임의 생성 문장 사용 없음",
        "- 25번 intent/risk label guide 기준의 deterministic rule로 1차 라벨링",
        "- 제외 행은 사유를 남기고 정답 평가셋에는 포함하지 않음",
        "",
        "## 선택 샘플 20건",
        "",
    ]
    for log in selected[:20]:
        label_lines.append(
            f"- {log['case_id']} | {log['product_type']} | {log['service_flow_type']} | "
            f"{log['risk_level']} | {log['procedure_type']} | action={log['expected_action']} | "
            f"followup={log['expected_followup_question']}"
        )

    label_lines.extend(["", "## 제외 샘플 20건", ""])
    for log in excluded[:20]:
        label_lines.append(
            f"- {log['voc_case_id']} | {log['product_type']} | reason={log['exclude_reason']} | "
            f"matched={log.get('matched_procedures')}"
        )

    label_lines.extend(
        [
            "",
            "## 실패/수정 기록",
            "",
            "- 초기 키워드 점검에서 `electricity bill`, `PCB warranty` 같은 비증상 문장이 high risk로 과분류될 수 있음을 확인했다.",
            "- 최종 스크립트에서는 구매/가격/보증/추천 문맥을 out-of-scope로 먼저 제외하고, high risk는 위험 신호 또는 위험 행동 조합에서만 선택하도록 보정했다.",
            "- 원천 제품군과 본문 제품군이 충돌하는 행은 `product_text_mismatch`로 제외했다.",
        ]
    )
    label_log_md.write_text("\n".join(label_lines) + "\n", encoding="utf-8")


def main() -> None:
    raw_rows = load_raw_voc()
    labeled = [classify_row(row) for row in raw_rows]
    cases = [item["case"] for item in labeled if item["selected"] and item["case"]]
    logs = [item["log"] for item in labeled]
    coverage = build_coverage(cases, logs, len(raw_rows))

    write_json(MOCK_DIR / "intent_risk_test_cases.json", cases)
    write_json(EVAL_DIR / f"intent_risk_labeling_log_{RUN_DATE}.json", logs)
    write_json(EVAL_DIR / f"intent_risk_coverage_report_{RUN_DATE}.json", coverage)
    write_markdown_reports(coverage, logs)

    print(json.dumps(coverage, ensure_ascii=False, indent=2))
    if not coverage["coverage_passed"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
