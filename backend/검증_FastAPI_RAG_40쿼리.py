from __future__ import annotations

import json
import sys
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

from app.main import app


PROJECT_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_DIR / "02_데이터연동"
OUTPUT_DIR = PROJECT_DIR / "06_산출물"
QUERY_SET_PATH = DATA_DIR / "eval_sets" / "rag_service_v2_quality_query_set_2026-06-04.json"
REPORT_MD_PATH = OUTPUT_DIR / "FastAPI_RAG_40쿼리_검증리포트_2026-06-04.md"
REPORT_JSON_PATH = OUTPUT_DIR / "FastAPI_RAG_40쿼리_검증결과_2026-06-04.json"


def load_query_set() -> list[dict[str, Any]]:
    return json.loads(QUERY_SET_PATH.read_text(encoding="utf-8"))


def official_only(results: list[dict[str, Any]]) -> bool:
    allowed = ("https://www.lg.com/in/", "https://gscs-manual.lge.com/")
    for item in results:
        source_url = item.get("source_url") or ""
        if source_url and not source_url.startswith(allowed):
            return False
    return True


def validate_case(case: dict[str, Any], response: dict[str, Any], status_code: int) -> dict[str, Any]:
    results = response.get("results") or []
    top1 = results[0] if results else {}
    expected_no_match = bool(case.get("expected_no_match"))
    expected_min_results = int(case.get("expected_min_results") or 0)
    expected_top1_procedures = set(case.get("expected_top1_procedures") or [])

    checks = {
        "status_200": status_code == 200,
        "official_url_only": official_only(results),
    }

    if expected_no_match:
        checks["expected_no_match"] = response.get("result_count") == 0 and response.get("ar_guide_blocked") is True
    else:
        checks["min_result_count"] = int(response.get("result_count") or 0) >= expected_min_results
        checks["ar_allowed"] = response.get("ar_guide_allowed") is True
        if expected_top1_procedures:
            checks["top1_procedure"] = top1.get("procedure_type") in expected_top1_procedures

    passed = all(checks.values())
    return {
        "case_id": case.get("case_id"),
        "passed": passed,
        "checks": checks,
        "request": {
            "query": case.get("query"),
            "product_type": case.get("product_type"),
            "model_name": case.get("model_name"),
            "procedure_type": case.get("procedure_type"),
            "language": case.get("language") or "en",
        },
        "response_summary": {
            "status_code": status_code,
            "result_count": response.get("result_count"),
            "retrieval_mode": response.get("retrieval_mode"),
            "ar_guide_allowed": response.get("ar_guide_allowed"),
            "ar_guide_blocked": response.get("ar_guide_blocked"),
            "top1_chunk_id": top1.get("chunk_id"),
            "top1_procedure_type": top1.get("procedure_type"),
            "top1_source_url": top1.get("source_url"),
            "no_match_reason": response.get("no_match_reason"),
        },
    }


def post_testclient(client: TestClient, payload: dict[str, Any]) -> tuple[int, dict[str, Any]]:
    response = client.post("/api/v1/rag/search", json=payload)
    return response.status_code, response.json()


def post_live_http(base_url: str, payload: dict[str, Any]) -> tuple[int, dict[str, Any]]:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        f"{base_url.rstrip('/')}/api/v1/rag/search",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=30) as response:  # noqa: S310 - local verification URL.
        return response.status, json.loads(response.read().decode("utf-8"))


def run_validation(base_url: str | None = None) -> dict[str, Any]:
    client = None if base_url else TestClient(app)
    cases = load_query_set()
    results = []

    for case in cases:
        payload = {
            "query": case["query"],
            "product_type": case["product_type"],
            "model_name": case.get("model_name"),
            "procedure_type": case.get("procedure_type"),
            "language": case.get("language") or "en",
            "limit": 5,
        }
        if base_url:
            status_code, body = post_live_http(base_url, payload)
        else:
            assert client is not None
            status_code, body = post_testclient(client, payload)
        results.append(validate_case(case, body, status_code))

    passed = [item for item in results if item["passed"]]
    failed = [item for item in results if not item["passed"]]
    return {
        "validated_at": datetime.now().isoformat(timespec="seconds"),
        "api_path": "/api/v1/rag/search",
        "execution_mode": "live_http" if base_url else "fastapi_testclient",
        "base_url": base_url,
        "query_set_path": str(QUERY_SET_PATH),
        "total": len(results),
        "passed": len(passed),
        "failed": len(failed),
        "all_passed": len(failed) == 0,
        "results": results,
    }


def write_reports(summary: dict[str, Any]) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_JSON_PATH.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = [
        "# FastAPI RAG 40쿼리 검증 리포트",
        "",
        f"- 검증 일시: {summary['validated_at']}",
        f"- API 경로: `{summary['api_path']}`",
        f"- 실행 방식: `{summary['execution_mode']}`",
        f"- Base URL: `{summary.get('base_url') or 'TestClient'}`",
        f"- Query set: `{summary['query_set_path']}`",
        f"- 전체: {summary['total']}",
        f"- 통과: {summary['passed']}",
        f"- 실패: {summary['failed']}",
        f"- 결론: {'통과' if summary['all_passed'] else '실패 보정 필요'}",
        "",
        "## 실패 케이스",
        "",
    ]

    failures = [item for item in summary["results"] if not item["passed"]]
    if not failures:
        lines.append("- 없음")
    else:
        for item in failures:
            lines.append(f"- {item['case_id']}: {item['checks']}")

    lines.extend(["", "## 케이스별 요약", ""])
    for item in summary["results"]:
        status = "PASS" if item["passed"] else "FAIL"
        summary_row = item["response_summary"]
        lines.append(
            f"- {status} `{item['case_id']}`: "
            f"result_count={summary_row['result_count']}, "
            f"mode={summary_row['retrieval_mode']}, "
            f"top1_procedure={summary_row['top1_procedure_type']}"
        )

    REPORT_MD_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    base_url_arg = None
    if len(sys.argv) >= 3 and sys.argv[1] == "--base-url":
        base_url_arg = sys.argv[2]
    validation_summary = run_validation(base_url=base_url_arg)
    write_reports(validation_summary)
    print(
        json.dumps(
            {
                "total": validation_summary["total"],
                "passed": validation_summary["passed"],
                "failed": validation_summary["failed"],
                "all_passed": validation_summary["all_passed"],
                "report_md": str(REPORT_MD_PATH),
                "report_json": str(REPORT_JSON_PATH),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
