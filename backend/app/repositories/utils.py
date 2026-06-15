from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Iterable, Mapping


JSON_FIELDS = {
    "raw_json",
    "model_aliases_json",
    "current_status_json",
    "usage_summary_json",
    "care_triggers_json",
    "detected_signals_json",
    "matched_model_names_json",
    "matched_aliases_json",
    "available_procedures_json",
    "forbidden_actions_json",
    "official_asset_ids_json",
    "reuse_key_json",
    "supported_guide_ids_json",
    "allowed_actions_json",
    "completed_steps_json",
    "intent_snapshot_json",
    "risk_snapshot_json",
    "slots_json",
    "intent_candidates_json",
    "risk_candidates_json",
    "missing_slots_json",
    "safety_tags_json",
    "strict_filter_json",
    "matched_chunk_ids_json",
    "score_json",
    "reasons_json",
    "evidence_refs_json",
    "expected_required_slots_json",
    "tags_json",
    "source_asset_ids_json",
    "part_map_ids_json",
    "embedding_vector_json",
    "required_official_sources_json",
    "camera_alignment_rules_json",
    "highlight_rules_json",
    "payload_json",
    "response_summary_json",
    "threshold_json",
    "issues_json",
    "manual_content_ids_json",
    "ar_template_ids_json",
    "recommended_options_json",
    "address_snapshot_json",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def to_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def row_to_dict(row: Mapping[str, Any] | None) -> dict[str, Any] | None:
    if row is None:
        return None
    result: dict[str, Any] = {}
    for key, value in dict(row).items():
        if key in JSON_FIELDS and value is not None:
            result[key.removesuffix("_json")] = value if isinstance(value, (dict, list)) else json.loads(value)
        else:
            result[key] = value
    return result


def rows_to_dicts(rows: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    return [row_to_dict(row) for row in rows if row is not None]


def normalize_payload(payload: dict[str, Any], defaults: dict[str, Any] | None = None) -> dict[str, Any]:
    normalized = dict(payload)
    for key, value in (defaults or {}).items():
        normalized.setdefault(key, value() if callable(value) else value)
    normalized.setdefault("raw_json", normalized.copy())
    return normalized
