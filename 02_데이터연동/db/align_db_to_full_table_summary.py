# -*- coding: utf-8 -*-
"""Align SQLite DB to 01_정의서/최종_DB_테이블_전체정리.md.

The target schema intentionally contains only the 21 persisted tables in the
final table document. Deprecated tables are not recreated.
"""
from __future__ import annotations

import json
import re
import shutil
import sqlite3
from datetime import datetime
from pathlib import Path


BASE = Path(__file__).resolve().parent
DB_PATH = BASE / "careshot_ar_mock.db"
SCHEMA_PATH = BASE / "schema.sql"


def load_json(value, default=None):
    if not value:
        return default
    try:
        return json.loads(value)
    except Exception:
        return default


def norm_id(*parts: object) -> str:
    raw = "_".join(str(p or "").strip() for p in parts if str(p or "").strip())
    raw = raw or "unknown"
    return (re.sub(r"[^A-Za-z0-9]+", "_", raw).strip("_").upper() or "UNKNOWN")[:50]


def email_for_user(user_id: str | None) -> str | None:
    if not user_id:
        return None
    return user_id.lower() if "@" in user_id else f"{user_id.lower()}@careshot.local"


def product_code_for_model(model_name: str | None) -> str | None:
    return str(model_name).strip() if model_name else None


def first_json_list_value(raw: str | None) -> str | None:
    value = load_json(raw, [])
    return str(value[0])[:100] if isinstance(value, list) and value else None


def bool_yn(value, default="Y") -> str:
    if value is None:
        return default
    if isinstance(value, str):
        return "Y" if value.lower() in {"1", "true", "y", "yes", "verified", "active"} else "N"
    return "Y" if bool(value) else "N"


def latlon_from_raw(raw: str | None):
    data = load_json(raw, {}) or {}
    blob = json.dumps(data.get("source_api", {}))
    lat = re.search(r"latitude=([-0-9.]+)", blob)
    lon = re.search(r"longitude=([-0-9.]+)", blob)
    return (float(lat.group(1)) if lat else None, float(lon.group(1)) if lon else None)


def table_exists(con: sqlite3.Connection, name: str) -> bool:
    return con.execute(
        "select 1 from sqlite_master where type='table' and name=?", (name,)
    ).fetchone() is not None


def main() -> None:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = DB_PATH.with_name(f"{DB_PATH.stem}_before_21table_align_{timestamp}{DB_PATH.suffix}")
    shutil.copy2(DB_PATH, backup)

    src = sqlite3.connect(backup)
    src.row_factory = sqlite3.Row
    DB_PATH.unlink()
    dst = sqlite3.connect(DB_PATH)
    dst.execute("PRAGMA foreign_keys=ON")
    dst.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))

    regions: dict[str, dict] = {}

    def add_region(country, state, city, lat=None, lon=None, climate=None, water=None, monsoon=None):
        country = country or "India"
        state = state or "Unknown"
        city = city or "Unknown"
        region_id = norm_id(country, state, city)
        region = regions.setdefault(
            region_id,
            {
                "region_id": region_id,
                "country": country,
                "state": state,
                "city": city,
                "latitude": lat,
                "longitude": lon,
                "timezone": "Asia/Kolkata",
                "climate_zone": climate,
                "water_hardness_level": water,
                "monsoon_zone": monsoon,
                "active": "Y",
            },
        )
        for key, value in {
            "latitude": lat,
            "longitude": lon,
            "climate_zone": climate,
            "water_hardness_level": water,
            "monsoon_zone": monsoon,
        }.items():
            if region.get(key) in (None, "") and value not in (None, ""):
                region[key] = value
        return region_id

    if table_exists(src, "environment_contexts"):
        for row in src.execute("select * from environment_contexts"):
            lat, lon = latlon_from_raw(row["raw_json"])
            add_region(row["country"], row["region"], row["city"], lat, lon, row["climate_zone"], row["water_hardness_level"])
    for source_table in ["environment_observations", "users", "devices"]:
        if table_exists(src, source_table):
            for row in src.execute(f"select distinct country, region, city from {source_table}"):
                add_region(row["country"], row["region"], row["city"])

    for region in regions.values():
        region["latitude"] = region["latitude"] if region["latitude"] is not None else 0.0
        region["longitude"] = region["longitude"] if region["longitude"] is not None else 0.0
        dst.execute(
            'insert into "REGION" values (?,?,?,?,?,?,?,?,?,?,?)',
            tuple(region[k] for k in [
                "region_id",
                "country",
                "state",
                "city",
                "latitude",
                "longitude",
                "timezone",
                "climate_zone",
                "water_hardness_level",
                "monsoon_zone",
                "active",
            ]),
        )

    user_map: dict[str, str] = {}
    if table_exists(src, "users"):
        for row in src.execute("select * from users"):
            email = email_for_user(row["user_id"])
            if not email:
                continue
            user_map[row["user_id"]] = email
            region_id = add_region(row["country"], row["region"], row["city"])
            dst.execute(
                'insert or ignore into "USER" values (?,?,?,?,?,?,?)',
                (
                    email,
                    "demo_password",
                    row["customer_name"] or row["user_id"],
                    None,
                    f"{row['city']}, {row['region']}, {row['country'] or 'India'}",
                    region_id,
                    row["preferred_language"] or "en",
                ),
            )

    products: dict[str, dict] = {}

    def add_product(code, name=None, model=None, ptype=None, structure=None, image=None, manual=None, supported="Y", source_type="demo_seed", source_url=None):
        code = product_code_for_model(code)
        if not code:
            return None
        product = products.setdefault(
            code,
            {
                "product_code": code,
                "product_name": name or model or code,
                "model_name": model or code,
                "product_type": ptype or "unknown",
                "structure_type": structure,
                "image_path": image,
                "manual_file_path": manual,
                "registration_supported": supported or "Y",
                "source_type": source_type or "demo_seed",
                "source_url": source_url,
            },
        )
        for key, value in {
            "product_name": name,
            "model_name": model,
            "product_type": ptype,
            "structure_type": structure,
            "image_path": image,
            "manual_file_path": manual,
            "source_url": source_url,
        }.items():
            if product.get(key) in (None, "", "unknown") and value not in (None, ""):
                product[key] = value
        if supported == "N":
            product["registration_supported"] = "N"
        return code

    if table_exists(src, "product_code_registry"):
        for row in src.execute("select * from product_code_registry"):
            add_product(
                row["product_code"] or row["model_name"],
                row["model_name"] or row["product_code"],
                row["model_name"] or row["product_code"],
                row["product_type"],
                row["structure_type"],
                supported=bool_yn(row["registration_supported"]),
                source_type=row["source_type"] or "official_or_demo",
                source_url=row["source_url"] or row["support_url"],
            )
    if table_exists(src, "product_models"):
        for row in src.execute("select * from product_models"):
            add_product(row["model_name"], row["model_name"], row["model_name"], row["product_type"], row["structure_type"], row["reference_image"], source_type="model_seed")
    if table_exists(src, "devices"):
        for row in src.execute("select distinct model_name, product_type, display_name from devices where model_name is not null"):
            add_product(row["model_name"], row["display_name"] or row["model_name"], row["model_name"], row["product_type"], source_type="thinq_mock")
    for table in ["official_assets", "official_document_chunks"]:
        if table_exists(src, table):
            for row in src.execute(f"select distinct model_name, product_type from {table} where model_name is not null and model_name != ''"):
                add_product(row["model_name"], row["model_name"], row["model_name"], row["product_type"], source_type="official_asset")

    for product in products.values():
        dst.execute(
            'insert or ignore into "PRODUCT" values (?,?,?,?,?,?,?,?,?,?)',
            tuple(product[k] for k in [
                "product_code",
                "product_name",
                "model_name",
                "product_type",
                "structure_type",
                "image_path",
                "manual_file_path",
                "registration_supported",
                "source_type",
                "source_url",
            ]),
        )

    device_map: dict[str, tuple[str, str]] = {}
    if table_exists(src, "devices"):
        for row in src.execute("select * from devices"):
            email = user_map.get(row["user_id"], email_for_user(row["user_id"]))
            code = row["registered_product_code"] if row["registered_product_code"] in products else product_code_for_model(row["model_name"])
            if not email or not code or code not in products:
                continue
            device_map[row["device_id"]] = (email, code)
            dst.execute(
                'insert or ignore into "USER_PRODUCT" (user_email,product_code,display_name,registered_at) values (?,?,?,?)',
                (email, code, row["display_name"] or code, row["registered_at"]),
            )

    asset_map: dict[str, int] = {}
    if table_exists(src, "official_assets"):
        for idx, row in enumerate(src.execute("select * from official_assets order by asset_id"), start=1):
            asset_map[row["asset_id"]] = idx
            model = row["model_name"] or None
            code = product_code_for_model(model) if model in products else None
            source_type = row["asset_type"] or row["source_origin"] or "official_manual"
            if source_type == "youtube":
                source_type = "official_youtube"
            verified = "N" if str(row["verification_status"] or "").lower() in {"unverified", "blocked"} else "Y"
            dst.execute(
                'insert into "OFFICIAL_ASSET" values (?,?,?,?,?,?,?,?,?,?,?)',
                (
                    idx,
                    code,
                    row["product_type"] or "unknown",
                    model,
                    first_json_list_value(row["available_procedures_json"]),
                    source_type[:50],
                    (row["title"] or row["asset_id"])[:255],
                    row["source_url"] or row["download_url"] or row["online_url"] or "unknown",
                    "en",
                    verified,
                    row["last_checked_at"] or row["source_date"],
                ),
            )

    chunk_map: dict[str, int] = {}
    chunk_asset: dict[int, int] = {}
    if table_exists(src, "official_document_chunks"):
        for idx, row in enumerate(src.execute("select * from official_document_chunks order by chunk_id"), start=1):
            asset_id = asset_map.get(row["asset_id"])
            if not asset_id:
                continue
            chunk_map[row["chunk_id"]] = idx
            chunk_asset[idx] = asset_id
            model = row["model_name"] or None
            code = product_code_for_model(model) if model in products else None
            dst.execute(
                'insert into "OFFICIAL_DOCUMENT_CHUNK" values (?,?,?,?,?,?,?,?,?,?)',
                (
                    idx,
                    asset_id,
                    code,
                    row["procedure_type"],
                    row["chunk_text"] or "",
                    row["source_url"],
                    row["source_section"] or row["chunk_title"],
                    row["language"] or "en",
                    row["embedding_status"] or "pending",
                    row["created_at"] or row["last_checked_at"],
                ),
            )

    ar_target_map: dict[tuple[str, str], int] = {}
    if table_exists(src, "reference_images"):
        for idx, row in enumerate(src.execute("select * from reference_images order by reference_image_id"), start=1):
            code = product_code_for_model(row["model_name"])
            if code not in products:
                continue
            mind_path = re.sub(r"\.[A-Za-z0-9]+$", ".mind", row["image_path"] or f"/static/assets/ar/{code}.mind")
            ar_target_map[(code, row["structure_type"])] = idx
            dst.execute(
                'insert into "AR_TARGET" values (?,?,?,?,?,?,?,?,?)',
                (idx, code, row["image_role"] or row["reference_image_id"], row["image_path"], mind_path, None, None, "Y", row["created_at"]),
            )

    guide_next = 1
    if table_exists(src, "official_contents"):
        for row in src.execute("select * from official_contents order by content_id"):
            code = product_code_for_model(row["model_name"])
            if code not in products:
                continue
            source_ids = load_json(row["source_asset_ids_json"], []) or []
            source_asset = asset_map.get(source_ids[0]) if source_ids else None
            dst.execute(
                'insert into "GUIDE" values (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
                (
                    guide_next,
                    code,
                    row["procedure_type"] or "general",
                    "manual",
                    "self_care",
                    (row["title"] or "Manual Guide")[:150],
                    None,
                    row["title"] or "Official guide content",
                    row["source_url"] if row["content_type"] == "video" else None,
                    None,
                    "official_manual",
                    source_asset,
                    None,
                    row["source_url"],
                    None,
                    row["language"] or "en",
                    "Y",
                    row["created_at"],
                    row["updated_at"],
                ),
            )
            guide_next += 1

    if table_exists(src, "ar_guide_templates"):
        for row in src.execute("select * from ar_guide_templates order by template_id"):
            code = "AS-Q24ENXE" if "AS-Q24ENXE" in products else next(iter(products), None)
            if not code:
                continue
            step_rows = src.execute(
                "select instruction_text from ar_guide_steps where guide_id=? order by step_order",
                (row["guide_id"],),
            ).fetchall() if table_exists(src, "ar_guide_steps") else []
            guide_text = "\n".join(f"{i + 1}. {step['instruction_text']}" for i, step in enumerate(step_rows)) or row["procedure_type"] or "AR Guide"
            trigger = "self_care" if row["guide_type"] in {"preventive_care", "self_care"} else "self_as"
            dst.execute(
                'insert into "GUIDE" values (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
                (
                    guide_next,
                    code,
                    row["procedure_type"] or "general",
                    "ar",
                    trigger,
                    f"{row['procedure_type'] or 'AR'} AR Guide"[:150],
                    None,
                    guide_text,
                    None,
                    None,
                    "custom",
                    None,
                    None,
                    None,
                    row["template_id"],
                    "ko",
                    "Y",
                    row["created_at"],
                    row["updated_at"],
                ),
            )
            target_id = ar_target_map.get((code, row["structure_type"])) or (next(iter(ar_target_map.values())) if ar_target_map else None)
            if target_id:
                dst.execute(
                    'insert into "AR_GUIDE" values (?,?,?,?,?,?,?,?,?)',
                    (guide_next, code, guide_next, target_id, row["procedure_type"] or "general", None, row["raw_json"] or "{}", "Y", row["created_at"]),
                )
            guide_next += 1

    session_map: dict[str, int] = {}
    if table_exists(src, "chat_sessions"):
        for idx, row in enumerate(src.execute("select * from chat_sessions order by session_id"), start=1):
            user_product = device_map.get(row["device_id"])
            if not user_product:
                continue
            status = row["status"] if row["status"] in {"active", "closed", "abandoned"} else "active"
            session_map[row["session_id"]] = idx
            dst.execute(
                'insert into "CHAT_SESSION" values (?,?,?,?,?,?)',
                (idx, user_product[0], user_product[1], status, row["created_at"], row["updated_at"] if status != "active" else None),
            )

    if table_exists(src, "chat_messages"):
        for idx, row in enumerate(src.execute("select * from chat_messages order by message_id"), start=1):
            session_id = session_map.get(row["session_id"])
            if not session_id:
                continue
            sender = {"assistant": "ai", "bot": "ai", "ai": "ai", "user": "user", "system": "system"}.get((row["role"] or "").lower(), "ai")
            dst.execute(
                'insert into "CHAT_MESSAGE" values (?,?,?,?,?,?)',
                (idx, session_id, sender, "text", row["message_text"] or "", row["created_at"]),
            )

    if table_exists(src, "conversation_state"):
        next_state = 1
        for row in src.execute("select * from conversation_state"):
            session_id = session_map.get(row["session_id"])
            if not session_id:
                continue
            candidates = load_json(row["intent_candidates_json"], []) or []
            intent = candidates[0] if isinstance(candidates, list) and candidates else None
            if isinstance(intent, dict):
                intent = intent.get("intent_type") or intent.get("intent") or intent.get("label")
            if intent not in {"self_care", "self_as", "expert_as"}:
                intent = None
            dst.execute(
                'insert into "CONVERSATION_STATE" values (?,?,?,?,?,?,?,?)',
                (next_state, session_id, intent, row["missing_slots_json"], row["slots_json"], row["last_question_id"], "ready" if row["ready_for_decision"] else "collecting", row["updated_at"]),
            )
            next_state += 1

    if table_exists(src, "smart_diagnosis_results"):
        for idx, row in enumerate(src.execute("select * from smart_diagnosis_results order by diagnosis_id"), start=1):
            user_product = device_map.get(row["device_id"]) or (user_map.get(row["user_id"]), product_code_for_model(row["model_name"]))
            if not user_product or not user_product[0] or not user_product[1]:
                continue
            if not dst.execute('select 1 from "USER_PRODUCT" where user_email=? and product_code=?', user_product).fetchone():
                continue
            severity = row["severity"] if row["severity"] in {"low", "medium", "high"} else None
            dst.execute(
                'insert into "SMART_DIAGNOSIS_RESULT" values (?,?,?,?,?,?,?,?,?)',
                (idx, user_product[0], user_product[1], row["result_code"], row["summary"], severity, row["raw_json"], row["created_at"], row["created_at"]),
            )

    if table_exists(src, "usage_logs"):
        for idx, row in enumerate(src.execute("select * from usage_logs order by usage_log_id"), start=1):
            user_product = device_map.get(row["device_id"]) or (user_map.get(row["user_id"]), product_code_for_model(row["model_name"]))
            if not user_product or not user_product[0] or not user_product[1]:
                continue
            if not dst.execute('select 1 from "USER_PRODUCT" where user_email=? and product_code=?', user_product).fetchone():
                continue
            summary = load_json(row["usage_summary_json"], {}) or {}
            hours = summary.get("recent_used_hours") or summary.get("runtime_hours") or summary.get("daily_runtime_hours") or 0
            days = summary.get("usage_period_days") or 7
            dst.execute(
                'insert into "APPLIANCE_USAGE_LOG" values (?,?,?,?,?,?,?,?,?)',
                (idx, user_product[1], user_product[0], days, hours, row["updated_at"], None, summary.get("operation_mode"), row["updated_at"]),
            )

    if table_exists(src, "official_document_embeddings"):
        for idx, row in enumerate(src.execute("select * from official_document_embeddings order by embedding_id"), start=1):
            chunk_id = chunk_map.get(row["chunk_id"])
            if not chunk_id:
                continue
            dst.execute(
                'insert or ignore into "OFFICIAL_DOCUMENT_EMBEDDING" values (?,?,?,?,?,?)',
                (idx, chunk_id, row["embedding_model"] or "local_hash_embedding", row["embedding_vector_json"] or "[]", row["embedding_status"] or "embedded", row["indexed_at"]),
            )

    if table_exists(src, "rag_search_logs"):
        for idx, row in enumerate(src.execute("select * from rag_search_logs order by search_id"), start=1):
            old_chunks = load_json(row["matched_chunk_ids_json"], []) or []
            new_chunks = [chunk_map[c] for c in old_chunks if c in chunk_map]
            asset_ids = sorted({chunk_asset[c] for c in new_chunks if c in chunk_asset})
            status = "success" if new_chunks else ("no_match" if row["no_match_reason"] else "success")
            dst.execute(
                'insert into "RAG_SEARCH_LOG" values (?,?,?,?,?,?,?,?)',
                (idx, None, None, row["query"] or "", json.dumps(new_chunks, ensure_ascii=False), json.dumps(asset_ids, ensure_ascii=False), status, row["created_at"]),
            )

    obs_next = 1
    if table_exists(src, "environment_observations"):
        for row in src.execute("select * from environment_observations"):
            region_id = add_region(row["country"], row["region"], row["city"])
            dst.execute(
                'insert into "ENVIRONMENT_OBSERVATION" values (?,?,?,?,?,?,?,?,?,?,?,?)',
                (obs_next, region_id, row["observed_at"] or datetime.now().isoformat(), row["temperature_c"], row["humidity_percent"], row["aqi"], row["pm25"], row["pm10"], None, None, row["provider_id"], datetime.now().isoformat()),
            )
            obs_next += 1
    if table_exists(src, "environment_contexts"):
        for row in src.execute("select * from environment_contexts"):
            region_id = add_region(row["country"], row["region"], row["city"])
            dst.execute(
                'insert into "ENVIRONMENT_OBSERVATION" values (?,?,?,?,?,?,?,?,?,?,?,?)',
                (obs_next, region_id, row["observed_at"] or datetime.now().isoformat(), row["temperature_c"], row["humidity_percent"], row["aqi"], None, None, None, None, row["source"], datetime.now().isoformat()),
            )
            obs_next += 1

    if table_exists(src, "care_activity_logs"):
        for idx, row in enumerate(src.execute("select * from care_activity_logs"), start=1):
            user_product = device_map.get(row["device_id"])
            if not user_product:
                continue
            management_type = "self_care" if row["service_flow_type"] in {"self_care", "preventive_care"} else "self_as"
            dst.execute(
                'insert into "SELF_MANAGEMENT_HISTORY" values (?,?,?,?,?,?)',
                (idx, user_product[1], user_product[0], row["procedure_type"] or "general", management_type, row["completed_at"] or row["started_at"]),
            )

    first_session = dst.execute('select session_id,user_email,product_code from "CHAT_SESSION" order by session_id limit 1').fetchone()
    if first_session:
        dst.execute(
            'insert into "CHATBOT_INQUIRY" values (?,?,?,?,?,?)',
            (1, first_session[0], first_session[1], first_session[2], "에어컨 냄새가 나고 바람이 약해요.", datetime.now().isoformat()),
        )
        guide = dst.execute('select guide_id from "GUIDE" where product_code=? order by guide_id limit 1', (first_session[2],)).fetchone()
        dst.execute(
            'insert into "AI_INQUIRY_ANALYSIS" values (?,?,?,?,?,?,?,?)',
            (1, 1, "냄새/냉방 약함", "self_as", "low", guide[0] if guide else None, None, "N"),
        )

    dst.commit()
    fk_errors = dst.execute("PRAGMA foreign_key_check").fetchall()
    if fk_errors:
        raise RuntimeError(f"foreign key errors: {fk_errors[:20]}")

    tables = [r[0] for r in dst.execute("select name from sqlite_master where type='table' and name not like 'sqlite_%' order by name")]
    print(f"backup={backup}")
    print(f"table_count={len(tables)}")
    for table in tables:
        count = dst.execute(f'select count(*) from "{table}"').fetchone()[0]
        print(f"{table}={count}")

    dst.close()
    src.close()


if __name__ == "__main__":
    main()
