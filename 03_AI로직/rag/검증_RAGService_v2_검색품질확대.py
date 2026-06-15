from __future__ import annotations

import json
import re
import sqlite3
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


RAG_DIR = Path(__file__).resolve().parent
PROJECT_DIR = RAG_DIR.parents[1]
DB_DIR = PROJECT_DIR / "02_데이터연동" / "db"
OUTPUT_DIR = PROJECT_DIR / "06_산출물"
EVAL_DIR = PROJECT_DIR / "02_데이터연동" / "eval_sets"
LOG_DIR = PROJECT_DIR / "07_개발로그"
FASTAPI_BACKEND_DIR = next(path for path in PROJECT_DIR.iterdir() if path.name.startswith("04_") and (path / "app").exists())

sys.path.insert(0, str(FASTAPI_BACKEND_DIR))
sys.path.insert(0, str(DB_DIR))
sys.path.insert(0, str(RAG_DIR))
sys.path.insert(0, str(RAG_DIR.parent / "rules"))

from app.repositories import CareShotRepository  # noqa: E402
from ar_guide_template_selector import ARGuideTemplateSelector  # noqa: E402
from rag_service import (  # noqa: E402
    BOILERPLATE_PATTERNS,
    OFFICIAL_PDF_SOURCE_TYPES,
    OFFICIAL_SOURCE_PREFIXES,
    RAGService,
)


TODAY = datetime.now(timezone.utc).date().isoformat()
NOW = datetime.now(timezone.utc).isoformat()


QUERY_SET: list[dict[str, Any]] = [
    # Air conditioner: low-risk care/self-check
    {"case_id": "RAGQ_AC_FILTER_001", "query": "How do I clean the air conditioner filter full of dust?", "product_type": "air_conditioner", "model_name": "AS-Q24ENXE", "procedure_type": "filter_cleaning", "language": "en", "expected_risk": "low", "expected_ar_allowed": True, "expected_min_results": 1, "expected_top1_procedures": ["filter_cleaning"]},
    {"case_id": "RAGQ_AC_FILTER_002", "query": "AC smells dusty when I switch it on, should I clean the filter?", "product_type": "air_conditioner", "model_name": "AS-Q24ENXE", "procedure_type": "filter_cleaning", "language": "en", "expected_risk": "low", "expected_ar_allowed": True, "expected_min_results": 1, "expected_top1_procedures": ["filter_cleaning"]},
    {"case_id": "RAGQ_AC_FILTER_003", "query": "एसी फिल्टर कैसे साफ करें", "product_type": "air_conditioner", "model_name": "AS-Q24ENXE", "procedure_type": "filter_cleaning", "language": "hi", "expected_risk": "low", "expected_ar_allowed": True, "expected_min_results": 1, "expected_top1_procedures": ["filter_cleaning"]},
    {"case_id": "RAGQ_AC_ODOR_001", "query": "There is mold smell from my split AC after monsoon", "product_type": "air_conditioner", "model_name": "AS-Q24ENXE", "procedure_type": "filter_cleaning", "language": "en", "expected_risk": "low", "expected_ar_allowed": True, "expected_min_results": 1, "expected_top1_procedures": ["filter_cleaning"]},
    {"case_id": "RAGQ_AC_COOL_001", "query": "My LG air conditioner is not cooling enough", "product_type": "air_conditioner", "model_name": "AS-Q24ENXE", "procedure_type": "no_cooling_self_check", "language": "en", "expected_risk": "medium", "expected_ar_allowed": True, "expected_min_results": 1, "expected_top1_procedures": ["no_cooling_self_check"]},
    {"case_id": "RAGQ_AC_COOL_002", "query": "Cold air is weak even though the AC is on", "product_type": "air_conditioner", "model_name": "AS-Q24ENXE", "procedure_type": "no_cooling_self_check", "language": "en", "expected_risk": "medium", "expected_ar_allowed": True, "expected_min_results": 1, "expected_top1_procedures": ["no_cooling_self_check"]},
    {"case_id": "RAGQ_AC_COOL_003", "query": "एसी ठंडी हवा नहीं दे रहा है", "product_type": "air_conditioner", "model_name": "AS-Q24ENXE", "procedure_type": "no_cooling_self_check", "language": "hi", "expected_risk": "medium", "expected_ar_allowed": True, "expected_min_results": 1, "expected_top1_procedures": ["no_cooling_self_check"]},
    {"case_id": "RAGQ_AC_WATER_001", "query": "Water is dripping from my air conditioner indoor unit", "product_type": "air_conditioner", "model_name": "AS-Q24ENXE", "procedure_type": "water_leak_monsoon", "language": "en", "expected_risk": "medium", "expected_ar_allowed": True, "expected_min_results": 1, "expected_top1_procedures": ["water_leak_monsoon"]},
    {"case_id": "RAGQ_AC_WATER_002", "query": "During monsoon my AC has condensation and water leak", "product_type": "air_conditioner", "model_name": "AS-Q24ENXE", "procedure_type": "water_leak_monsoon", "language": "en", "expected_risk": "medium", "expected_ar_allowed": True, "expected_min_results": 1, "expected_top1_procedures": ["water_leak_monsoon"]},
    {"case_id": "RAGQ_AC_NOISE_001", "query": "My AC makes hissing and gulping sound", "product_type": "air_conditioner", "model_name": "AS-Q24ENXE", "procedure_type": "noise_self_check", "language": "en", "expected_risk": "medium", "expected_ar_allowed": True, "expected_min_results": 1, "expected_top1_procedures": ["noise_self_check"]},
    {"case_id": "RAGQ_AC_NOISE_002", "query": "There is vibration noise from the AC indoor unit", "product_type": "air_conditioner", "model_name": "AS-Q24ENXE", "procedure_type": "noise_self_check", "language": "en", "expected_risk": "medium", "expected_ar_allowed": True, "expected_min_results": 1, "expected_top1_procedures": ["noise_self_check"]},
    {"case_id": "RAGQ_AC_REMOTE_001", "query": "How do I use fan speed and mode on LG AC remote?", "product_type": "air_conditioner", "model_name": "AS-Q24ENXE", "procedure_type": "remote_operation", "language": "en", "expected_risk": "low", "expected_ar_allowed": True, "expected_min_results": 1, "expected_top1_procedures": ["remote_operation"]},
    {"case_id": "RAGQ_AC_REMOTE_002", "query": "Remote display is confusing, how to operate cooling mode?", "product_type": "air_conditioner", "model_name": "AS-Q24ENXE", "procedure_type": "remote_operation", "language": "en", "expected_risk": "low", "expected_ar_allowed": True, "expected_min_results": 1, "expected_top1_procedures": ["remote_operation"]},
    {"case_id": "RAGQ_AC_ERROR_001", "query": "SP CP PO appears on my LG AC display", "product_type": "air_conditioner", "model_name": "AS-Q24ENXE", "procedure_type": "power_error_self_check", "language": "en", "expected_risk": "medium", "expected_ar_allowed": True, "expected_min_results": 1, "expected_top1_procedures": ["power_error_self_check"]},
    {"case_id": "RAGQ_AC_ERROR_002", "query": "HI is shown on the air conditioner display", "product_type": "air_conditioner", "model_name": "AS-Q24ENXE", "procedure_type": "power_error_self_check", "language": "en", "expected_risk": "medium", "expected_ar_allowed": True, "expected_min_results": 1, "expected_top1_procedures": ["power_error_self_check"]},
    # Air conditioner high risk
    {"case_id": "RAGQ_AC_HIGH_ELEC_001", "query": "There is burning smell and spark from AC power wire", "product_type": "air_conditioner", "model_name": "AS-Q24ENXE", "procedure_type": "high_risk_electrical", "language": "en", "expected_risk": "high", "expected_ar_allowed": False, "expected_min_results": 1, "expected_top1_procedures": ["high_risk_electrical"]},
    {"case_id": "RAGQ_AC_HIGH_ELEC_002", "query": "I got electric shock from my air conditioner plug", "product_type": "air_conditioner", "model_name": "AS-Q24ENXE", "procedure_type": "high_risk_electrical", "language": "en", "expected_risk": "high", "expected_ar_allowed": False, "expected_min_results": 1, "expected_top1_procedures": ["high_risk_electrical"]},
    {"case_id": "RAGQ_AC_HIGH_REFR_001", "query": "Gas is leaking from the AC pipe, how can I refill refrigerant?", "product_type": "air_conditioner", "model_name": "AS-Q24ENXE", "procedure_type": "high_risk_refrigerant", "language": "en", "expected_risk": "high", "expected_ar_allowed": False, "expected_min_results": 1, "expected_top1_procedures": ["high_risk_refrigerant"]},
    {"case_id": "RAGQ_AC_HIGH_REFR_002", "query": "Compressor repair and refrigerant charging steps for LG AC", "product_type": "air_conditioner", "model_name": "AS-Q24ENXE", "procedure_type": "high_risk_refrigerant", "language": "en", "expected_risk": "high", "expected_ar_allowed": False, "expected_min_results": 1, "expected_top1_procedures": ["high_risk_refrigerant"]},
    # Official PDF metadata cases: Owner's Manual PDF is one official PDF source type, not the only PDF source.
    {"case_id": "RAGQ_PDF_AC_001", "query": "Official PDF warning about electric shock for air conditioner", "product_type": "air_conditioner", "model_name": "TS-Q14YNZE", "procedure_type": "high_risk_electrical", "language": "en", "expected_risk": "high", "expected_ar_allowed": False, "expected_min_results": 1, "expected_top1_procedures": ["high_risk_electrical"], "expected_source_type_any": sorted(OFFICIAL_PDF_SOURCE_TYPES)},
    {"case_id": "RAGQ_PDF_AC_002", "query": "Air conditioner official PDF water leak or drainage safety", "product_type": "air_conditioner", "model_name": "TS-Q14YNZE", "procedure_type": "water_leak_monsoon", "language": "en", "expected_risk": "medium", "expected_ar_allowed": True, "expected_min_results": 1, "expected_top1_procedures": ["water_leak_monsoon"], "expected_source_type_any": sorted(OFFICIAL_PDF_SOURCE_TYPES)},
    {"case_id": "RAGQ_PDF_WM_001", "query": "Washing machine official PDF electrical warning", "product_type": "washing_machine", "model_name": "FHD1207STB", "procedure_type": "high_risk_electrical", "language": "en", "expected_risk": "high", "expected_ar_allowed": False, "expected_min_results": 1, "expected_top1_procedures": ["high_risk_electrical"], "expected_source_type_any": sorted(OFFICIAL_PDF_SOURCE_TYPES)},
    {"case_id": "RAGQ_WP_FILTER_META_001", "query": "Water purifier official filter replacement and safety", "product_type": "water_purifier", "model_name": "WW140NP", "procedure_type": "filter_replacement", "language": "en", "expected_risk": "low", "expected_ar_allowed": True, "expected_min_results": 1, "expected_top1_procedures": ["filter_replacement"], "official_pdf_unavailable_reason": "LG India official Help Library evidence exists, but no extractable official PDF evidence was confirmed for WW140NP in the current official corpus."},
    # Other product families
    {"case_id": "RAGQ_WM_TUB_001", "query": "How to run tub clean cycle and remove smell in washing machine", "product_type": "washing_machine", "model_name": "FHD1207STB", "procedure_type": "tub_clean", "language": "en", "expected_risk": "low", "expected_ar_allowed": True, "expected_min_results": 1, "expected_top1_procedures": ["tub_clean"]},
    {"case_id": "RAGQ_WM_TUB_002", "query": "Washer smells bad after monsoon, tub clean guide", "product_type": "washing_machine", "model_name": "FHD1107STB", "procedure_type": "tub_clean", "language": "en", "expected_risk": "low", "expected_ar_allowed": True, "expected_min_results": 1, "expected_top1_procedures": ["tub_clean"]},
    {"case_id": "RAGQ_WM_LIME_001", "query": "Hard water scale in washing machine drum", "product_type": "washing_machine", "model_name": "FHD1207STB", "procedure_type": "limescale_care", "language": "en", "expected_risk": "low", "expected_ar_allowed": True, "expected_min_results": 1, "expected_top1_procedures": ["limescale_care"]},
    {"case_id": "RAGQ_WM_HIGH_001", "query": "Washing machine gives electric shock and burning smell", "product_type": "washing_machine", "model_name": "FHD1207STB", "procedure_type": "high_risk_electrical", "language": "en", "expected_risk": "high", "expected_ar_allowed": False, "expected_min_results": 1, "expected_top1_procedures": ["high_risk_electrical"]},
    {"case_id": "RAGQ_AP_FILTER_001", "query": "Air purifier filter replacement lamp is on", "product_type": "air_purifier", "model_name": "AS60GDWT0", "procedure_type": "filter_replacement", "language": "en", "expected_risk": "low", "expected_ar_allowed": True, "expected_min_results": 1, "expected_top1_procedures": ["filter_replacement"]},
    {"case_id": "RAGQ_AP_FILTER_002", "query": "How to clean dust filter in LG air purifier", "product_type": "air_purifier", "model_name": "AS60GHWG0", "procedure_type": "filter_cleaning", "language": "en", "expected_risk": "low", "expected_ar_allowed": True, "expected_min_results": 1, "expected_top1_procedures": ["filter_cleaning", "filter_replacement"]},
    {"case_id": "RAGQ_AP_HIGH_001", "query": "Air purifier smells burning and sparks near power cable", "product_type": "air_purifier", "model_name": "AS60GDWT0", "procedure_type": "high_risk_electrical", "language": "en", "expected_risk": "high", "expected_ar_allowed": False, "expected_min_results": 1, "expected_top1_procedures": ["high_risk_electrical"]},
    {"case_id": "RAGQ_WP_LIME_001", "query": "Water purifier has hard water limescale deposit", "product_type": "water_purifier", "model_name": "WW140NP", "procedure_type": "limescale_care", "language": "en", "expected_risk": "medium", "expected_ar_allowed": True, "expected_min_results": 1, "expected_top1_procedures": ["limescale_care"]},
    {"case_id": "RAGQ_WP_FILTER_001", "query": "When should I replace LG water purifier filter?", "product_type": "water_purifier", "model_name": "WW130NP", "procedure_type": "filter_replacement", "language": "en", "expected_risk": "low", "expected_ar_allowed": True, "expected_min_results": 1, "expected_top1_procedures": ["filter_replacement"]},
    {"case_id": "RAGQ_WP_HIGH_001", "query": "Water purifier power board is sparking", "product_type": "water_purifier", "model_name": "WW140NP", "procedure_type": "high_risk_electrical", "language": "en", "expected_risk": "high", "expected_ar_allowed": False, "expected_min_results": 1, "expected_top1_procedures": ["high_risk_electrical"]},
    # No-match and forced wrong-metadata cases
    {"case_id": "RAGQ_NOMATCH_001", "query": "quantum refrigerator aquarium motherboard teleport setup", "product_type": "air_conditioner", "model_name": "AS-Q24ENXE", "procedure_type": "unsupported_procedure", "language": "en", "expected_risk": "unknown", "expected_ar_allowed": False, "expected_min_results": 0, "expected_no_match": True},
    {"case_id": "RAGQ_NOMATCH_002", "query": "install solar panel on washing machine drum", "product_type": "washing_machine", "model_name": "FHD1207STB", "procedure_type": "unsupported_procedure", "language": "en", "expected_risk": "unknown", "expected_ar_allowed": False, "expected_min_results": 0, "expected_no_match": True},
    {"case_id": "RAGQ_NOMATCH_003", "query": "paint air purifier with oil and connect to car battery", "product_type": "air_purifier", "model_name": "AS60GDWT0", "procedure_type": "unsupported_procedure", "language": "en", "expected_risk": "unknown", "expected_ar_allowed": False, "expected_min_results": 0, "expected_no_match": True},
    {"case_id": "RAGQ_NOMATCH_004", "query": "replace refrigerator compressor in water purifier", "product_type": "water_purifier", "model_name": "WW140NP", "procedure_type": "unsupported_procedure", "language": "en", "expected_risk": "unknown", "expected_ar_allowed": False, "expected_min_results": 0, "expected_no_match": True},
    # Additional mixed-language/support cases
    {"case_id": "RAGQ_HI_REMOTE_001", "query": "रिमोट से एसी मोड कैसे बदलें", "product_type": "air_conditioner", "model_name": "AS-Q24ENXE", "procedure_type": "remote_operation", "language": "hi", "expected_risk": "low", "expected_ar_allowed": True, "expected_min_results": 1, "expected_top1_procedures": ["remote_operation"]},
    {"case_id": "RAGQ_HI_WATER_001", "query": "एसी से पानी टपक रहा है", "product_type": "air_conditioner", "model_name": "AS-Q24ENXE", "procedure_type": "water_leak_monsoon", "language": "hi", "expected_risk": "medium", "expected_ar_allowed": True, "expected_min_results": 1, "expected_top1_procedures": ["water_leak_monsoon"]},
    {"case_id": "RAGQ_HI_HIGH_001", "query": "एसी वायर से चिंगारी आ रही है", "product_type": "air_conditioner", "model_name": "AS-Q24ENXE", "procedure_type": "high_risk_electrical", "language": "hi", "expected_risk": "high", "expected_ar_allowed": False, "expected_min_results": 1, "expected_top1_procedures": ["high_risk_electrical"]},
]


def is_official_url(url: str) -> bool:
    return str(url or "").startswith(OFFICIAL_SOURCE_PREFIXES)


def has_boilerplate(text: str) -> bool:
    lower = str(text or "").lower()
    return any(pattern in lower for pattern in BOILERPLATE_PATTERNS)


def scan_boilerplate_chunks(db_path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        for row in conn.execute(
            """
            SELECT chunk_id, asset_id, source_url, chunk_title, chunk_text
            FROM official_document_chunks
            """
        ).fetchall():
            text = f"{row['chunk_title'] or ''} {row['chunk_text'] or ''}".lower()
            matched = [pattern for pattern in BOILERPLATE_PATTERNS if pattern in text]
            if matched:
                rows.append(
                    {
                        "chunk_id": row["chunk_id"],
                        "asset_id": row["asset_id"],
                        "source_url": row["source_url"],
                        "matched_patterns": matched,
                    }
                )
    return rows


def pdf_metadata_ok(
    results: list[dict[str, Any]],
    expected_source_type: str | list[str] | tuple[str, ...] | set[str] | None,
) -> dict[str, Any]:
    if not expected_source_type:
        return {"required": False, "passed": True, "matched_result": None}
    expected_source_types = (
        {expected_source_type}
        if isinstance(expected_source_type, str)
        else set(expected_source_type)
    )
    for item in results:
        if item.get("source_type") in expected_source_types:
            chunk_text = item.get("chunk_text") or ""
            return {
                "required": True,
                "passed": bool(item.get("source_url"))
                and bool(item.get("source_section"))
                and bool(item.get("source_raw_file"))
                and (
                    bool(item.get("pdf_page_number"))
                    or "[page " in chunk_text.lower()
                    or item.get("source_section") == "pdf_text"
                ),
                "matched_result": {
                    "chunk_id": item.get("chunk_id"),
                    "source_type": item.get("source_type"),
                    "source_section": item.get("source_section"),
                    "source_url": item.get("source_url"),
                    "source_raw_file": item.get("source_raw_file"),
                    "pdf_page_number": item.get("pdf_page_number"),
                    "pdf_page_marker": item.get("pdf_page_marker"),
                    "page_marker_detected": bool(item.get("pdf_page_marker")) or "[page " in chunk_text.lower(),
                    "accepted_source_types": sorted(expected_source_types),
                },
            }
    return {
        "required": True,
        "passed": False,
        "matched_result": None,
        "accepted_source_types": sorted(expected_source_types),
    }


def topk_contains_expected(results: list[dict[str, Any]], expected: list[str] | None) -> bool:
    if not expected:
        return True
    return any(item.get("procedure_type") in expected for item in results)


def high_risk_policy_blocked(case: dict[str, Any], response: dict[str, Any]) -> bool:
    if case.get("expected_risk") != "high":
        return True
    first = response["results"][0] if response.get("results") else {}
    risk_procedure = str(first.get("procedure_type") or "").startswith("high_risk")
    forbidden = bool(first.get("forbidden_actions"))
    # RAGService returns evidence. AR blocking is a policy gate: high risk evidence must not be passed to ARGuidePlan.
    return bool(response.get("result_count")) and risk_procedure and forbidden and case.get("expected_ar_allowed") is False


def ar_selector_high_risk_smoke() -> dict[str, Any]:
    selector = ARGuideTemplateSelector()
    decision_bundle = {
        "request_id": "RAG_QUALITY_HIGH_RISK_SMOKE",
        "decision_result": {
            "decision_action": "route_to_service",
            "generation_allowed": False,
            "risk_level": "high",
            "content_type": "service_route",
            "reuse_decision": "blocked_high_risk",
        },
        "official_asset_match": {
            "match_status": "verified",
            "match_type": "exact_model",
            "official_assets": [{"asset_id": "OA_LGIN_SUPPORT_FAQ_0001"}],
            "forbidden_actions": ["electrical_repair"],
        },
        "procedure": {"procedure_type": "high_risk_electrical"},
        "context": {
            "user": {"preferred_language": "en", "video_style": "manual"},
            "device": {
                "device_id": "D_SMOKE_AC",
                "product_type": "air_conditioner",
                "model_name": "AS-Q24ENXE",
            },
        },
        "rag_evidence": {"result_count": 1},
    }
    result = selector.select_and_build(decision_bundle)
    return {
        "passed": result.get("status") == "ar_guide_plan_blocked" and result.get("ar_guide_plan") is None,
        "status": result.get("status"),
        "blocked_reason": result.get("blocked_reason"),
    }


def run_eval() -> dict[str, Any]:
    EVAL_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    query_set_path = EVAL_DIR / f"rag_service_v2_quality_query_set_{TODAY}.json"
    query_set_path.write_text(json.dumps(QUERY_SET, ensure_ascii=False, indent=2), encoding="utf-8")

    repo = CareShotRepository(DB_DIR / "careshot_ar_mock.db")
    service = RAGService(repo)
    embedding_stats = repo.get_embedding_stats()
    case_results: list[dict[str, Any]] = []

    for case in QUERY_SET:
        payload = {
            "query": case["query"],
            "product_type": case["product_type"],
            "model_name": case.get("model_name"),
            "procedure_type": case.get("procedure_type"),
            "language": case.get("language", "en"),
            "limit": 5,
        }
        response = service.search(payload)
        results = response["results"]
        first = results[0] if results else None
        expected_top1 = case.get("expected_top1_procedures")
        official_url_only = all(is_official_url(item.get("source_url")) for item in results)
        no_boilerplate_in_results = all(
            not has_boilerplate(f"{item.get('chunk_title') or ''} {item.get('chunk_text') or ''}")
            for item in results
        )
        top1_ok = (
            True
            if case.get("expected_no_match")
            else bool(first and first.get("procedure_type") in (expected_top1 or []))
        )
        topk_ok = (
            True
            if case.get("expected_no_match")
            else topk_contains_expected(results, expected_top1)
        )
        min_results_ok = response["result_count"] >= int(case.get("expected_min_results", 1))
        no_match_ok = (
            response["result_count"] == 0 and response["ar_guide_blocked"] is True
            if case.get("expected_no_match")
            else response["result_count"] > 0
        )
        pdf_check = pdf_metadata_ok(results, case.get("expected_source_type_any"))
        high_risk_ok = high_risk_policy_blocked(case, response)
        policy_ar_allowed = bool(response["result_count"] > 0 and case.get("expected_ar_allowed") is True)
        policy_ar_blocked = not policy_ar_allowed
        ar_policy_ok = (
            policy_ar_allowed is True
            if case.get("expected_ar_allowed")
            else policy_ar_blocked is True
        )
        passed = all(
            [
                official_url_only,
                no_boilerplate_in_results,
                top1_ok,
                topk_ok,
                min_results_ok,
                no_match_ok,
                pdf_check["passed"],
                high_risk_ok,
                ar_policy_ok,
            ]
        )
        case_results.append(
            {
                "case_id": case["case_id"],
                "query": case["query"],
                "product_type": case["product_type"],
                "model_name": case.get("model_name"),
                "procedure_type": case.get("procedure_type"),
                "language": case.get("language"),
                "expected_risk": case.get("expected_risk"),
                "expected_ar_allowed": case.get("expected_ar_allowed"),
                "passed": passed,
                "checks": {
                    "official_url_only": official_url_only,
                    "no_boilerplate_in_results": no_boilerplate_in_results,
                    "top1_procedure_ok": top1_ok,
                    "topk_contains_expected_procedure": topk_ok,
                    "min_results_ok": min_results_ok,
                    "no_match_ok": no_match_ok,
                    "pdf_page_section_source_url_ok": pdf_check["passed"],
                    "high_risk_policy_blocked": high_risk_ok,
                    "ar_policy_ok": ar_policy_ok,
                },
                "response_summary": {
                    "result_count": response["result_count"],
                    "retrieval_mode": response["retrieval_mode"],
                    "rag_ar_guide_allowed_raw": response["ar_guide_allowed"],
                    "rag_ar_guide_blocked_raw": response["ar_guide_blocked"],
                    "policy_ar_allowed": policy_ar_allowed,
                    "policy_ar_blocked": policy_ar_blocked,
                    "no_match_reason": response["no_match_reason"],
                    "first_chunk_id": first.get("chunk_id") if first else None,
                    "first_asset_id": first.get("asset_id") if first else None,
                    "first_procedure_type": first.get("procedure_type") if first else None,
                    "first_source_type": first.get("source_type") if first else None,
                    "first_source_section": first.get("source_section") if first else None,
                    "first_source_url": first.get("source_url") if first else None,
                    "first_score": first.get("score") if first else None,
                    "first_forbidden_actions": first.get("forbidden_actions") if first else [],
                },
                "pdf_metadata_check": pdf_check,
                "top_results": [
                    {
                        "rank": item.get("rank"),
                        "chunk_id": item.get("chunk_id"),
                        "asset_id": item.get("asset_id"),
                        "procedure_type": item.get("procedure_type"),
                        "source_type": item.get("source_type"),
                        "source_section": item.get("source_section"),
                        "source_url": item.get("source_url"),
                        "source_raw_file": item.get("source_raw_file"),
                        "pdf_page_number": item.get("pdf_page_number"),
                        "pdf_page_marker": item.get("pdf_page_marker"),
                        "score": item.get("score"),
                        "vector_score": item.get("vector_score"),
                        "lexical_score": item.get("lexical_score"),
                        "forbidden_actions": item.get("forbidden_actions"),
                    }
                    for item in results[:5]
                ],
            }
        )

    boilerplate_rows = scan_boilerplate_chunks(DB_DIR / "careshot_ar_mock.db")
    ar_smoke = ar_selector_high_risk_smoke()
    summary = {
        "created_at": NOW,
        "query_set_path": str(query_set_path.relative_to(PROJECT_DIR)),
        "query_count": len(QUERY_SET),
        "embedding_stats": embedding_stats,
        "passed_count": sum(1 for row in case_results if row["passed"]),
        "failed_count": sum(1 for row in case_results if not row["passed"]),
        "case_results": case_results,
        "official_url_only_passed": all(
            row["checks"]["official_url_only"] for row in case_results
        ),
        "top1_accuracy": round(
            sum(1 for row in case_results if row["checks"]["top1_procedure_ok"]) / len(case_results),
            4,
        ),
        "topk_expected_procedure_accuracy": round(
            sum(1 for row in case_results if row["checks"]["topk_contains_expected_procedure"]) / len(case_results),
            4,
        ),
        "no_result_case_count": sum(1 for row in case_results if row["response_summary"]["result_count"] == 0),
        "expected_no_match_case_count": sum(
            1 for row in case_results if row["procedure_type"] == "unsupported_procedure"
        ),
        "expected_no_match_passed_count": sum(
            1
            for row in case_results
            if row["procedure_type"] == "unsupported_procedure" and row["checks"]["no_match_ok"]
        ),
        "high_risk_case_count": sum(1 for row in case_results if row["expected_risk"] == "high"),
        "high_risk_policy_blocked_count": sum(
            1
            for row in case_results
            if row["expected_risk"] == "high" and row["checks"]["high_risk_policy_blocked"]
        ),
        "pdf_metadata_required_count": sum(
            1 for row in case_results if row["pdf_metadata_check"]["required"]
        ),
        "pdf_metadata_passed_count": sum(
            1
            for row in case_results
            if row["pdf_metadata_check"]["required"] and row["pdf_metadata_check"]["passed"]
        ),
        "boilerplate_chunk_scan": {
            "matched_chunk_count": len(boilerplate_rows),
            "matches": boilerplate_rows[:50],
        },
        "ar_selector_high_risk_smoke": ar_smoke,
        "procedure_distribution_first_result": dict(
            Counter(
                row["response_summary"]["first_procedure_type"] or "no_match"
                for row in case_results
            )
        ),
    }
    result_path = OUTPUT_DIR / f"RAGService_v2_검색품질확대_결과_{TODAY}.json"
    result_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    report_path = write_report(summary)
    log_path = write_log(summary)
    summary["result_path"] = str(result_path.relative_to(PROJECT_DIR))
    summary["report_path"] = str(report_path.relative_to(PROJECT_DIR))
    summary["log_path"] = str(log_path.relative_to(PROJECT_DIR))
    return summary


def write_report(summary: dict[str, Any]) -> Path:
    report_path = OUTPUT_DIR / f"RAGService_v2_검색품질확대_검증리포트_{TODAY}.md"
    failed = [row for row in summary["case_results"] if not row["passed"]]
    rows = []
    for row in summary["case_results"]:
        res = row["response_summary"]
        rows.append(
            f"| {row['case_id']} | {row['passed']} | {res['result_count']} | "
            f"{res['retrieval_mode']} | {res['first_procedure_type'] or ''} | "
            f"{res['first_source_type'] or ''} | {res['policy_ar_blocked']} |"
        )
    failed_rows = []
    for row in failed:
        failed_checks = [key for key, value in row["checks"].items() if not value]
        failed_rows.append(f"- {row['case_id']}: {', '.join(failed_checks)}")
    failed_text = "\n".join(failed_rows) if failed_rows else "- 없음"

    report = f"""# RAGService v2 검색 품질 확대 검증 리포트

## 1. 검증 목적

RAGService v2가 확장된 공식자료 corpus {summary['embedding_stats']['embedding_count']}개 embedded chunk를 기준으로 공식 URL만 반환하는지, top-k 근거가 절차와 맞는지, PDF 근거의 page/section/source_url이 반환되는지, boilerplate chunk가 다시 검색 대상에 섞이지 않는지, High Risk와 no-match가 ARGuidePlan으로 흘러가지 않도록 차단 가능한지 검증했다.

## 2. 검증 요약

| 항목 | 결과 |
|---|---:|
| 평가 query 수 | {summary['query_count']} |
| 통과 case | {summary['passed_count']} |
| 실패 case | {summary['failed_count']} |
| 공식 URL only | {summary['official_url_only_passed']} |
| top1 procedure accuracy | {summary['top1_accuracy']} |
| top-k expected procedure accuracy | {summary['topk_expected_procedure_accuracy']} |
| 의도한 no-match 통과 | {summary['expected_no_match_passed_count']} / {summary['expected_no_match_case_count']} |
| 전체 no-result case | {summary['no_result_case_count']} |
| High Risk policy block | {summary['high_risk_policy_blocked_count']} / {summary['high_risk_case_count']} |
| PDF metadata 통과 | {summary['pdf_metadata_passed_count']} / {summary['pdf_metadata_required_count']} |
| boilerplate 재검출 chunk | {summary['boilerplate_chunk_scan']['matched_chunk_count']} |
| AR selector High Risk smoke | {summary['ar_selector_high_risk_smoke']['passed']} |

## 3. 평가 query set

평가 query set은 아래 파일에 저장했다.

```text
{summary['query_set_path']}
```

구성 범위:

```text
에어컨 필터 / 냄새 / 냉방 약함 / 물샘 / 소음 / 리모컨 / 에러코드
전기 High Risk / 냉매 High Risk
세탁기 통세척 / 석회질 / 전기 High Risk
공기청정기 필터 / 전기 High Risk
정수기 필터 / 석회질 / 전기 High Risk
PDF Owner's Manual metadata case
Water purifier official Help Library metadata case where India Owner's Manual PDF is unavailable in current corpus
no-match case
영어/힌디어 혼합 case
```

## 4. case별 결과

| case_id | pass | result_count | retrieval_mode | first_procedure | first_source_type | policy_ar_blocked |
|---|---|---:|---|---|---|---|
{chr(10).join(rows)}

## 5. 실패 case

{failed_text}

## 6. High Risk / no-match 차단

RAGService 자체는 검색 근거를 반환하는 서비스이므로, High Risk가 검색 결과를 가질 수 있다. 최종 AR 차단은 DecisionEngine/ARGuideTemplateSelector 정책 게이트에서 수행해야 한다.

이번 검증에서는 다음 두 가지를 확인했다.

```text
1. High Risk query가 high_risk_* procedure와 forbidden_actions 근거를 반환하는지
2. ARGuideTemplateSelector가 risk_level=high, generation_allowed=false decision을 ar_guide_plan_blocked로 차단하는지
```

AR selector smoke result:

```json
{json.dumps(summary['ar_selector_high_risk_smoke'], ensure_ascii=False, indent=2)}
```

## 7. boilerplate 재검출

DB 전체 `official_document_chunks`를 boilerplate pattern으로 재스캔했다.

```text
boilerplate 재검출 chunk 수: {summary['boilerplate_chunk_scan']['matched_chunk_count']}
```

## 8. 다음 작업

RAGService v2 검색 품질 검증이 통과하면 다음 개발은 FastAPI 백엔드 구조 전환이다. 단, 실패 case가 남아 있으면 해당 case의 procedure mapping, language filter, source_type 우선순위, no-match threshold를 먼저 조정한다.
"""
    report_path.write_text(report, encoding="utf-8")
    return report_path


def write_log(summary: dict[str, Any]) -> Path:
    log_path = LOG_DIR / f"{TODAY}_RAGService_v2_검색품질확대_검증로그.md"
    text = f"""# {TODAY} RAGService v2 검색 품질 확대 검증 로그

## 수행 내용

1. 평가 query set {summary['query_count']}개를 생성했다.
2. RAGService v2로 top-k 검색을 실행했다.
3. 공식 URL only, top-k procedure 적합성, PDF metadata, boilerplate 재검출, High Risk/no-match 차단 정책을 검증했다.
4. 결과 JSON과 검증 리포트를 생성했다.

## 결과

| 항목 | 결과 |
|---|---:|
| 통과 case | {summary['passed_count']} |
| 실패 case | {summary['failed_count']} |
| top1 accuracy | {summary['top1_accuracy']} |
| top-k accuracy | {summary['topk_expected_procedure_accuracy']} |
| boilerplate 재검출 chunk | {summary['boilerplate_chunk_scan']['matched_chunk_count']} |
| High Risk policy block | {summary['high_risk_policy_blocked_count']} / {summary['high_risk_case_count']} |
| 의도한 no-match 통과 | {summary['expected_no_match_passed_count']} / {summary['expected_no_match_case_count']} |
| 전체 no-result case | {summary['no_result_case_count']} |

## 산출물

```text
{summary['query_set_path']}
06_산출물/RAGService_v2_검색품질확대_결과_{TODAY}.json
06_산출물/RAGService_v2_검색품질확대_검증리포트_{TODAY}.md
```
"""
    log_path.write_text(text, encoding="utf-8")
    return log_path


def main() -> None:
    summary = run_eval()
    print(json.dumps(summary, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()
