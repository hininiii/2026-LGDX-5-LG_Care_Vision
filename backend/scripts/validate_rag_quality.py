from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = SCRIPT_DIR.parent
PROJECT_DIR = BACKEND_DIR.parent
DATA_DIR = next(path for path in PROJECT_DIR.iterdir() if path.name.startswith("02_"))
OUTPUT_DIR = next(path for path in PROJECT_DIR.iterdir() if path.name.startswith("06_"))
EVAL_DIR = DATA_DIR / "eval_sets"

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.path_setup import configure_import_paths  # noqa: E402
from app.repositories import CareShotRepository  # noqa: E402


configure_import_paths()
from rag_service import BOILERPLATE_PATTERNS, OFFICIAL_SOURCE_PREFIXES, RAGService  # noqa: E402


def load_query_set() -> list[dict[str, Any]]:
    candidates = sorted(EVAL_DIR.glob("rag_service_v2_quality_query_set_*.json"), reverse=True)
    if not candidates:
        raise FileNotFoundError(f"RAG quality query set not found: {EVAL_DIR}")
    return json.loads(candidates[0].read_text(encoding="utf-8"))


def is_official_url(url: str) -> bool:
    return str(url or "").startswith(OFFICIAL_SOURCE_PREFIXES)


def has_boilerplate(text: str) -> bool:
    lower = str(text or "").lower()
    return any(pattern in lower for pattern in BOILERPLATE_PATTERNS)


def validate_case(service: RAGService, case: dict[str, Any]) -> dict[str, Any]:
    response = service.search(
        {
            "query": case["query"],
            "product_type": case["product_type"],
            "model_name": case.get("model_name"),
            "procedure_type": case.get("procedure_type"),
            "language": case.get("language", "en"),
            "limit": 5,
        }
    )
    results = response["results"]
    first = results[0] if results else None
    expected_top1 = case.get("expected_top1_procedures") or []
    expected_no_match = bool(case.get("expected_no_match"))
    expected_ar_allowed = bool(case.get("expected_ar_allowed"))
    expected_risk = case.get("expected_risk")

    official_url_only = all(is_official_url(item.get("source_url")) for item in results)
    no_boilerplate = all(
        not has_boilerplate(f"{item.get('chunk_title') or ''} {item.get('chunk_text') or ''}")
        for item in results
    )
    top1_ok = True if expected_no_match else bool(first and first.get("procedure_type") in expected_top1)
    min_results_ok = response["result_count"] >= int(case.get("expected_min_results", 1))
    no_match_ok = (
        response["result_count"] == 0 and response["ar_guide_blocked"] is True
        if expected_no_match
        else response["result_count"] > 0
    )
    high_risk_policy_blocked = (
        True
        if expected_risk != "high"
        else bool(first and str(first.get("procedure_type") or "").startswith("high_risk"))
        and expected_ar_allowed is False
    )
    no_high_risk_mixed_into_safe_flow = (
        all(not str(item.get("procedure_type") or "").startswith("high_risk") for item in results)
        if expected_ar_allowed
        else True
    )
    no_filter_cleaning_mixed_into_power = (
        all(item.get("procedure_type") != "filter_cleaning" for item in results)
        if case.get("procedure_type") == "power_troubleshooting"
        else True
    )
    embedding_model_ok = response.get("embedding_model") == "BAAI/bge-m3"
    embedding_dimension_ok = response.get("embedding_dimension") == 1024

    checks = {
        "embedding_model_ok": embedding_model_ok,
        "embedding_dimension_ok": embedding_dimension_ok,
        "official_url_only": official_url_only,
        "no_boilerplate": no_boilerplate,
        "top1_procedure_ok": top1_ok,
        "min_results_ok": min_results_ok,
        "no_match_ok": no_match_ok,
        "high_risk_policy_blocked": high_risk_policy_blocked,
        "no_high_risk_mixed_into_safe_flow": no_high_risk_mixed_into_safe_flow,
        "no_filter_cleaning_mixed_into_power": no_filter_cleaning_mixed_into_power,
    }
    return {
        "case_id": case["case_id"],
        "query": case["query"],
        "procedure_type": case.get("procedure_type"),
        "expected_top1_procedures": expected_top1,
        "passed": all(checks.values()),
        "checks": checks,
        "response_summary": {
            "embedding_model": response.get("embedding_model"),
            "embedding_dimension": response.get("embedding_dimension"),
            "retrieval_mode": response.get("retrieval_mode"),
            "result_count": response.get("result_count"),
            "first_chunk_id": first.get("chunk_id") if first else None,
            "first_procedure_type": first.get("procedure_type") if first else None,
            "first_source_type": first.get("source_type") if first else None,
            "first_source_url": first.get("source_url") if first else None,
            "first_vector_score": first.get("vector_score") if first else None,
        },
    }


def run() -> dict[str, Any]:
    service = RAGService(CareShotRepository())
    query_set = load_query_set()
    extra_cases = [
        {
            "case_id": "RAGQ_AC_POWER_MIX_001",
            "query": "My LG AC has no power and suddenly turns off.",
            "product_type": "air_conditioner",
            "model_name": "AS-Q24ENXE",
            "procedure_type": "power_troubleshooting",
            "language": "en",
            "expected_ar_allowed": True,
            "expected_min_results": 1,
            "expected_top1_procedures": ["power_troubleshooting"],
        }
    ]
    case_results = [validate_case(service, case) for case in query_set]
    extra_results = [validate_case(service, case) for case in extra_cases]
    now = datetime.now(timezone.utc).isoformat()
    summary = {
        "created_at": now,
        "embedding_model": service.embedding_provider.model_name,
        "embedding_dimension": service.embedding_provider.dimension,
        "query_count": len(query_set),
        "passed_count": sum(1 for row in case_results if row["passed"]),
        "failed_count": sum(1 for row in case_results if not row["passed"]),
        "extra_case_count": len(extra_results),
        "extra_passed_count": sum(1 for row in extra_results if row["passed"]),
        "case_results": case_results,
        "extra_results": extra_results,
        "official_url_only_passed": all(row["checks"]["official_url_only"] for row in case_results),
        "top1_accuracy": round(
            sum(1 for row in case_results if row["checks"]["top1_procedure_ok"]) / len(case_results),
            4,
        ),
        "no_high_risk_mixed_into_safe_flow": all(
            row["checks"]["no_high_risk_mixed_into_safe_flow"] for row in case_results
        ),
        "power_troubleshooting_filter_cleaning_mixed": not all(
            row["checks"]["no_filter_cleaning_mixed_into_power"] for row in extra_results
        ),
    }
    date = datetime.now(timezone.utc).date().isoformat()
    result_path = OUTPUT_DIR / f"RAG_BGE_M3_40쿼리_검증결과_{date}.json"
    report_path = OUTPUT_DIR / f"RAG_BGE_M3_40쿼리_검증리포트_{date}.md"
    result_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    failed = [row for row in case_results + extra_results if not row["passed"]]
    failed_text = "\n".join(
        f"- {row['case_id']}: "
        + ", ".join(key for key, value in row["checks"].items() if not value)
        for row in failed
    ) or "- none"
    report = f"""# RAG BGE-M3 40 Query Validation

- created_at: {now}
- embedding_model: {summary['embedding_model']}
- embedding_dimension: {summary['embedding_dimension']}
- query_count: {summary['query_count']}
- passed_count: {summary['passed_count']}
- failed_count: {summary['failed_count']}
- top1_accuracy: {summary['top1_accuracy']}
- official_url_only_passed: {summary['official_url_only_passed']}
- no_high_risk_mixed_into_safe_flow: {summary['no_high_risk_mixed_into_safe_flow']}
- power_troubleshooting_filter_cleaning_mixed: {summary['power_troubleshooting_filter_cleaning_mixed']}

## Failed Checks

{failed_text}
"""
    report_path.write_text(report, encoding="utf-8")
    summary["result_path"] = str(result_path)
    summary["report_path"] = str(report_path)
    return summary


if __name__ == "__main__":
    print(json.dumps(run(), ensure_ascii=True, indent=2))
