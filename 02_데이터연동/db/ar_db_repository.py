from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DB_DIR = Path(__file__).resolve().parent
DB_PATH = DB_DIR / "careshot_ar_mock.db"


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
    "reasons_json",
    "evidence_refs_json",
    "issues_json",
}


class CareShotRepository:
    def __init__(self, db_path: str | Path = DB_PATH) -> None:
        self.db_path = Path(db_path)

    def connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def _row_to_dict(self, row: sqlite3.Row | None) -> dict[str, Any] | None:
        if row is None:
            return None
        result: dict[str, Any] = {}
        for key in row.keys():
            value = row[key]
            if key in JSON_FIELDS and value is not None:
                result[key.removesuffix("_json")] = json.loads(value)
            else:
                result[key] = value
        return result

    def _rows_to_dicts(self, rows: list[sqlite3.Row]) -> list[dict[str, Any]]:
        return [self._row_to_dict(row) for row in rows if row is not None]

    def get_user_profile(self, user_id: str) -> dict[str, Any] | None:
        with self.connect() as conn:
            row = conn.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)).fetchone()
            return self._row_to_dict(row)

    def get_device_context(self, device_id: str) -> dict[str, Any] | None:
        with self.connect() as conn:
            row = conn.execute("SELECT * FROM devices WHERE device_id = ?", (device_id,)).fetchone()
            return self._row_to_dict(row)

    def get_usage_log(self, device_id: str) -> dict[str, Any] | None:
        with self.connect() as conn:
            row = conn.execute(
                """
                SELECT * FROM usage_logs
                WHERE device_id = ?
                ORDER BY updated_at DESC
                LIMIT 1
                """,
                (device_id,),
            ).fetchone()
            return self._row_to_dict(row)

    def get_smart_diagnosis(self, device_id: str, include_high_risk_sample: bool = False) -> dict[str, Any] | None:
        with self.connect() as conn:
            if include_high_risk_sample:
                row = conn.execute(
                    """
                    SELECT * FROM smart_diagnosis_results
                    WHERE device_id = ?
                    ORDER BY
                      CASE severity WHEN 'high' THEN 0 WHEN 'medium' THEN 1 WHEN 'low' THEN 2 ELSE 3 END,
                      created_at DESC
                    LIMIT 1
                    """,
                    (device_id,),
                ).fetchone()
            else:
                row = conn.execute(
                    """
                    SELECT * FROM smart_diagnosis_results
                    WHERE device_id = ?
                      AND diagnosis_id NOT LIKE '%HIGH_RISK_SAMPLE%'
                    ORDER BY created_at DESC
                    LIMIT 1
                    """,
                    (device_id,),
                ).fetchone()
            return self._row_to_dict(row)

    def get_environment_context(self, region: str, city: str | None = None) -> dict[str, Any] | None:
        with self.connect() as conn:
            if city:
                row = conn.execute(
                    """
                    SELECT * FROM environment_contexts
                    WHERE region = ? AND city = ?
                    ORDER BY observed_at DESC
                    LIMIT 1
                    """,
                    (region, city),
                ).fetchone()
                if row:
                    return self._row_to_dict(row)

            row = conn.execute(
                """
                SELECT * FROM environment_contexts
                WHERE region = ?
                ORDER BY observed_at DESC
                LIMIT 1
                """,
                (region,),
            ).fetchone()
            return self._row_to_dict(row)

    def find_official_assets(
        self,
        model_name: str,
        product_type: str,
        aliases: list[str] | None = None,
        series: str | None = None,
    ) -> dict[str, Any]:
        aliases = aliases or []
        with self.connect() as conn:
            rows = conn.execute(
                """
                SELECT * FROM official_assets
                WHERE verification_status IN ('verified', 'collected_official_lg_india')
                  AND (product_type = ? OR product_type = 'common')
                """,
                (product_type,),
            ).fetchall()

        assets = self._rows_to_dicts(rows)

        def includes(values: list[str] | None, target: str) -> bool:
            return target in (values or [])

        exact = [
            asset for asset in assets
            if asset.get("product_type") == product_type
            and (
                asset.get("model_name") == model_name
                or includes(asset.get("matched_model_names"), model_name)
            )
            and asset.get("applicability_scope") == "exact_model"
        ]
        if exact:
            return self._official_match_result("verified", "exact_model", model_name, product_type, exact)

        alias = [
            asset for asset in assets
            if asset.get("product_type") == product_type
            and asset.get("applicability_scope") in {"exact_model", "official_alias"}
            and any(includes(asset.get("matched_aliases"), alias_value) for alias_value in aliases + [model_name])
        ]
        if alias:
            return self._official_match_result("verified", "official_alias", model_name, product_type, alias)

        series_matches = [
            asset for asset in assets
            if asset.get("product_type") == product_type
            and asset.get("applicability_scope") == "official_series"
            and series is not None
            and asset.get("matched_series") == series
        ]
        if series_matches:
            return self._official_match_result("verified", "official_series", model_name, product_type, series_matches)

        common = [
            asset for asset in assets
            if asset.get("product_type") == product_type
            and asset.get("applicability_scope") == "product_type_common"
        ]
        if common:
            return self._official_match_result("verified", "product_type_common", model_name, product_type, common)

        return {
            "match_status": "needs_review",
            "match_type": "none",
            "strict_match": True,
            "model_name": model_name,
            "product_type": product_type,
            "official_assets": [],
            "applicable_procedures": [],
            "forbidden_actions": [],
            "review_reason": "No verified official asset matched exact model, alias, series, or product type common scope.",
        }

    def _official_match_result(
        self,
        status: str,
        match_type: str,
        model_name: str,
        product_type: str,
        assets: list[dict[str, Any]],
    ) -> dict[str, Any]:
        procedures = sorted({
            procedure
            for asset in assets
            for procedure in (asset.get("available_procedures") or [])
        })
        forbidden = sorted({
            action
            for asset in assets
            for action in (asset.get("forbidden_actions") or [])
        })
        return {
            "match_status": status,
            "match_type": match_type,
            "strict_match": True,
            "model_name": model_name,
            "product_type": product_type,
            "official_assets": assets,
            "applicable_procedures": procedures,
            "forbidden_actions": forbidden,
            "review_reason": None,
        }

    def find_reusable_care_video(
        self,
        product_type: str,
        procedure_type: str,
        language: str,
        video_style: str,
        model_name: str | None = None,
        series: str | None = None,
        match_type: str | None = None,
    ) -> dict[str, Any] | None:
        with self.connect() as conn:
            rows = conn.execute(
                """
                SELECT * FROM care_videos
                WHERE product_type = ?
                  AND procedure_type = ?
                  AND language = ?
                  AND video_style = ?
                  AND quality_status = 'pass'
                  AND safety_status = 'pass'
                """,
                (product_type, procedure_type, language, video_style),
            ).fetchall()

        videos = self._rows_to_dicts(rows)
        if not videos:
            return None

        if model_name:
            for video in videos:
                if video.get("model_name") == model_name:
                    video["reuse_decision"] = "full_reuse"
                    return video

        if series:
            for video in videos:
                if video.get("series") == series:
                    video["reuse_decision"] = "full_reuse" if match_type == "official_series" else "partial_rerender"
                    return video

        for video in videos:
            if video.get("match_type") == "product_type_common":
                video["reuse_decision"] = "full_reuse" if match_type == "product_type_common" else "partial_rerender"
                return video

        return None

    def get_product_model(self, model_name: str, product_type: str | None = None) -> dict[str, Any] | None:
        with self.connect() as conn:
            if product_type:
                row = conn.execute(
                    """
                    SELECT * FROM product_models
                    WHERE model_name = ? AND product_type = ?
                    LIMIT 1
                    """,
                    (model_name, product_type),
                ).fetchone()
            else:
                row = conn.execute(
                    "SELECT * FROM product_models WHERE model_name = ? LIMIT 1",
                    (model_name,),
                ).fetchone()
            return self._row_to_dict(row)

    def get_product_model_by_structure(self, structure_type: str) -> dict[str, Any] | None:
        with self.connect() as conn:
            row = conn.execute(
                """
                SELECT * FROM product_models
                WHERE structure_type = ? AND model_name IS NULL
                LIMIT 1
                """,
                (structure_type,),
            ).fetchone()
            return self._row_to_dict(row)

    def get_part_map(self, structure_type: str) -> list[dict[str, Any]]:
        with self.connect() as conn:
            rows = conn.execute(
                """
                SELECT * FROM part_maps
                WHERE structure_type = ?
                ORDER BY user_accessible DESC, part_id ASC
                """,
                (structure_type,),
            ).fetchall()
            return self._rows_to_dicts(rows)

    def get_part_map_by_part(self, structure_type: str, part_id: str) -> dict[str, Any] | None:
        with self.connect() as conn:
            row = conn.execute(
                """
                SELECT * FROM part_maps
                WHERE structure_type = ? AND part_id = ?
                LIMIT 1
                """,
                (structure_type, part_id),
            ).fetchone()
            return self._row_to_dict(row)

    def get_ar_guide_steps(self, guide_id: str) -> list[dict[str, Any]]:
        with self.connect() as conn:
            rows = conn.execute(
                """
                SELECT * FROM ar_guide_steps
                WHERE guide_id = ?
                ORDER BY step_order ASC
                """,
                (guide_id,),
            ).fetchall()
            return self._rows_to_dicts(rows)

    def find_ar_guides(
        self,
        product_type: str,
        procedure_type: str | None = None,
        guide_type: str | None = None,
        structure_type: str | None = None,
    ) -> list[dict[str, Any]]:
        query = """
            SELECT guide_id, guide_type, product_type, structure_type, procedure_type,
                   COUNT(*) AS step_count, MIN(created_at) AS created_at
            FROM ar_guide_steps
            WHERE product_type = ?
        """
        params: list[Any] = [product_type]
        if procedure_type:
            query += " AND procedure_type = ?"
            params.append(procedure_type)
        if guide_type:
            query += " AND guide_type = ?"
            params.append(guide_type)
        if structure_type:
            query += " AND structure_type = ?"
            params.append(structure_type)
        query += " GROUP BY guide_id, guide_type, product_type, structure_type, procedure_type ORDER BY guide_id"

        with self.connect() as conn:
            rows = conn.execute(query, tuple(params)).fetchall()
            return self._rows_to_dicts(rows)

    def create_ar_session_log(self, payload: dict[str, Any]) -> dict[str, Any]:
        now = datetime.now(timezone.utc).isoformat()
        payload = dict(payload)
        payload.setdefault("created_at", now)
        payload.setdefault("updated_at", now)
        payload.setdefault("completed_steps", [])
        payload.setdefault("completed", False)
        payload.setdefault("clicked_as", False)
        payload.setdefault("raw_json", payload.copy())

        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO ar_session_logs (
                  session_id, user_id, device_id, guide_id, guide_type, structure_type,
                  completed_steps_json, completed, solved, clicked_as,
                  created_at, updated_at, raw_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    payload["session_id"],
                    payload["user_id"],
                    payload["device_id"],
                    payload["guide_id"],
                    payload["guide_type"],
                    payload["structure_type"],
                    json.dumps(payload.get("completed_steps", []), ensure_ascii=False),
                    int(bool(payload.get("completed"))),
                    None if payload.get("solved") is None else int(bool(payload.get("solved"))),
                    int(bool(payload.get("clicked_as"))),
                    payload["created_at"],
                    payload["updated_at"],
                    json.dumps(payload["raw_json"], ensure_ascii=False),
                ),
            )
            conn.commit()

        return payload

    def get_ar_session_logs(self, user_id: str | None = None, device_id: str | None = None) -> list[dict[str, Any]]:
        query = "SELECT * FROM ar_session_logs WHERE 1=1"
        params: list[Any] = []
        if user_id:
            query += " AND user_id = ?"
            params.append(user_id)
        if device_id:
            query += " AND device_id = ?"
            params.append(device_id)
        query += " ORDER BY created_at DESC"

        with self.connect() as conn:
            rows = conn.execute(query, tuple(params)).fetchall()
            return self._rows_to_dicts(rows)

    def get_ar_session_log(self, session_id: str) -> dict[str, Any] | None:
        with self.connect() as conn:
            row = conn.execute(
                "SELECT * FROM ar_session_logs WHERE session_id = ? LIMIT 1",
                (session_id,),
            ).fetchone()
            return self._row_to_dict(row)

    def update_ar_session_log(
        self,
        session_id: str,
        completed_steps: list[str] | None = None,
        completed: bool | None = None,
        solved: bool | None = None,
        clicked_as: bool | None = None,
    ) -> dict[str, Any] | None:
        current = self.get_ar_session_log(session_id)
        if current is None:
            return None

        next_completed_steps = completed_steps if completed_steps is not None else current.get("completed_steps", [])
        next_completed = bool(completed) if completed is not None else bool(current.get("completed"))
        next_solved = solved if solved is not None else current.get("solved")
        next_clicked_as = bool(clicked_as) if clicked_as is not None else bool(current.get("clicked_as"))
        updated_at = datetime.now(timezone.utc).isoformat()
        raw_json = dict(current.get("raw") or {})
        raw_json.update(
            {
                "completed_steps": next_completed_steps,
                "completed": next_completed,
                "solved": next_solved,
                "clicked_as": next_clicked_as,
                "updated_at": updated_at,
            }
        )

        with self.connect() as conn:
            conn.execute(
                """
                UPDATE ar_session_logs
                SET completed_steps_json = ?,
                    completed = ?,
                    solved = ?,
                    clicked_as = ?,
                    updated_at = ?,
                    raw_json = ?
                WHERE session_id = ?
                """,
                (
                    json.dumps(next_completed_steps, ensure_ascii=False),
                    int(next_completed),
                    None if next_solved is None else int(bool(next_solved)),
                    int(next_clicked_as),
                    updated_at,
                    json.dumps(raw_json, ensure_ascii=False),
                    session_id,
                ),
            )
            conn.commit()

        return self.get_ar_session_log(session_id)

    def create_chat_session(self, payload: dict[str, Any]) -> dict[str, Any]:
        now = datetime.now(timezone.utc).isoformat()
        payload = dict(payload)
        payload.setdefault("created_at", now)
        payload.setdefault("updated_at", now)
        payload.setdefault("status", "active")
        payload.setdefault("entry_channel", "thinq_chatbot_mock")
        payload.setdefault("raw_json", payload.copy())

        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO chat_sessions (
                  session_id, user_id, device_id, status, language, entry_channel,
                  current_intent, current_risk_level, created_at, updated_at, raw_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    payload["session_id"],
                    payload["user_id"],
                    payload["device_id"],
                    payload["status"],
                    payload["language"],
                    payload.get("entry_channel"),
                    payload.get("current_intent"),
                    payload.get("current_risk_level"),
                    payload["created_at"],
                    payload["updated_at"],
                    json.dumps(payload["raw_json"], ensure_ascii=False),
                ),
            )
            conn.commit()

        return payload

    def get_chat_session(self, session_id: str) -> dict[str, Any] | None:
        with self.connect() as conn:
            row = conn.execute(
                "SELECT * FROM chat_sessions WHERE session_id = ? LIMIT 1",
                (session_id,),
            ).fetchone()
            return self._row_to_dict(row)

    def add_chat_message(self, payload: dict[str, Any]) -> dict[str, Any]:
        now = datetime.now(timezone.utc).isoformat()
        payload = dict(payload)
        payload.setdefault("created_at", now)
        payload.setdefault("intent_snapshot", {})
        payload.setdefault("risk_snapshot", {})
        payload.setdefault("raw_json", payload.copy())

        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO chat_messages (
                  message_id, session_id, role, message_text, message_state,
                  detected_language, intent_snapshot_json, risk_snapshot_json,
                  created_at, raw_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    payload["message_id"],
                    payload["session_id"],
                    payload["role"],
                    payload["message_text"],
                    payload["message_state"],
                    payload.get("detected_language"),
                    json.dumps(payload.get("intent_snapshot", {}), ensure_ascii=False),
                    json.dumps(payload.get("risk_snapshot", {}), ensure_ascii=False),
                    payload["created_at"],
                    json.dumps(payload["raw_json"], ensure_ascii=False),
                ),
            )
            conn.commit()

        return payload

    def get_chat_messages(self, session_id: str) -> list[dict[str, Any]]:
        with self.connect() as conn:
            rows = conn.execute(
                """
                SELECT * FROM chat_messages
                WHERE session_id = ?
                ORDER BY created_at ASC
                """,
                (session_id,),
            ).fetchall()
            return self._rows_to_dicts(rows)

    def get_conversation_state(self, session_id: str) -> dict[str, Any] | None:
        with self.connect() as conn:
            row = conn.execute(
                "SELECT * FROM conversation_state WHERE session_id = ? LIMIT 1",
                (session_id,),
            ).fetchone()
            return self._row_to_dict(row)

    def upsert_conversation_state(self, payload: dict[str, Any]) -> dict[str, Any]:
        now = datetime.now(timezone.utc).isoformat()
        payload = dict(payload)
        payload.setdefault("updated_at", now)
        payload.setdefault("slots", {})
        payload.setdefault("intent_candidates", [])
        payload.setdefault("risk_candidates", [])
        payload.setdefault("missing_slots", [])
        payload.setdefault("ready_for_decision", False)
        payload.setdefault("raw_json", payload.copy())

        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO conversation_state (
                  session_id, slots_json, intent_candidates_json, risk_candidates_json,
                  missing_slots_json, last_question_id, ready_for_decision,
                  updated_at, raw_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(session_id) DO UPDATE SET
                  slots_json = excluded.slots_json,
                  intent_candidates_json = excluded.intent_candidates_json,
                  risk_candidates_json = excluded.risk_candidates_json,
                  missing_slots_json = excluded.missing_slots_json,
                  last_question_id = excluded.last_question_id,
                  ready_for_decision = excluded.ready_for_decision,
                  updated_at = excluded.updated_at,
                  raw_json = excluded.raw_json
                """,
                (
                    payload["session_id"],
                    json.dumps(payload.get("slots", {}), ensure_ascii=False),
                    json.dumps(payload.get("intent_candidates", []), ensure_ascii=False),
                    json.dumps(payload.get("risk_candidates", []), ensure_ascii=False),
                    json.dumps(payload.get("missing_slots", []), ensure_ascii=False),
                    payload.get("last_question_id"),
                    int(bool(payload.get("ready_for_decision"))),
                    payload["updated_at"],
                    json.dumps(payload["raw_json"], ensure_ascii=False),
                ),
            )
            conn.commit()

        return self.get_conversation_state(payload["session_id"]) or payload

    def search_official_document_chunks(
        self,
        query: str,
        product_type: str,
        model_name: str | None = None,
        procedure_type: str | None = None,
        language: str | None = None,
        limit: int = 5,
    ) -> list[dict[str, Any]]:
        terms = [term.lower() for term in query.split() if len(term) >= 3]
        with self.connect() as conn:
            sql = """
                SELECT * FROM official_document_chunks
                WHERE product_type = ?
            """
            params: list[Any] = [product_type]
            if model_name:
                sql += " AND (model_name = ? OR model_name IS NULL)"
                params.append(model_name)
            if procedure_type:
                sql += " AND procedure_type = ?"
                params.append(procedure_type)
            if language:
                sql += " AND language = ?"
                params.append(language)
            rows = conn.execute(sql, tuple(params)).fetchall()

        chunks = self._rows_to_dicts(rows)
        for chunk in chunks:
            text = f"{chunk.get('chunk_title') or ''} {chunk.get('chunk_text') or ''}".lower()
            chunk["mock_score"] = sum(1 for term in terms if term in text)

        chunks.sort(key=lambda item: item.get("mock_score", 0), reverse=True)
        return chunks[:limit]

    def search_vector_official_document_chunks(
        self,
        product_type: str,
        model_name: str | None = None,
        procedure_type: str | None = None,
        language: str | None = None,
        embedding_model: str | None = None,
        require_procedure: bool = True,
        limit: int = 500,
    ) -> list[dict[str, Any]]:
        query = """
            SELECT
              c.*,
              e.embedding_model,
              e.embedding_dimension,
              e.embedding_vector_json,
              e.embedding_norm,
              e.indexed_at
            FROM official_document_chunks c
            JOIN official_document_embeddings e ON c.chunk_id = e.chunk_id
            WHERE c.product_type = ?
              AND (
                c.source_url LIKE 'https://www.lg.com/in/%'
                OR c.source_url LIKE 'https://gscs-manual.lge.com/%'
                OR c.source_url LIKE 'https://www.youtube.com/watch%'
                OR c.source_url LIKE 'https://youtu.be/%'
              )
              AND c.embedding_status = 'embedded'
              AND e.embedding_status = 'embedded'
        """
        params: list[Any] = [product_type]
        if model_name:
            query += """
              AND (
                c.model_name = ?
                OR c.model_name IS NULL
                OR c.applicability_scope IN ('product_type_common', 'official_series')
              )
            """
            params.append(model_name)
        if procedure_type and require_procedure:
            query += " AND c.procedure_type = ?"
            params.append(procedure_type)
        if language:
            query += " AND c.language = ?"
            params.append(language)
        if embedding_model:
            query += " AND e.embedding_model = ?"
            params.append(embedding_model)
        query += """
            ORDER BY
              CASE
                WHEN c.source_url LIKE 'https://www.youtube.com/watch%' THEN 0
                WHEN c.source_url LIKE 'https://youtu.be/%' THEN 0
                ELSE 1
              END,
              c.chunk_id ASC
            LIMIT ?
        """
        params.append(limit)

        with self.connect() as conn:
            rows = conn.execute(query, tuple(params)).fetchall()
            return self._rows_to_dicts(rows)

    def get_embedding_stats(self) -> dict[str, Any]:
        with self.connect() as conn:
            table_exists = conn.execute(
                """
                SELECT COUNT(*)
                FROM sqlite_master
                WHERE type = 'table'
                  AND name = 'official_document_embeddings'
                """
            ).fetchone()[0]
            if not table_exists:
                return {
                    "table_exists": False,
                    "embedding_count": 0,
                    "chunk_status_counts": {},
                    "model_counts": {},
                }
            chunk_status_rows = conn.execute(
                """
                SELECT embedding_status, COUNT(*) AS count
                FROM official_document_chunks
                GROUP BY embedding_status
                """
            ).fetchall()
            model_rows = conn.execute(
                """
                SELECT embedding_model, embedding_status, COUNT(*) AS count
                FROM official_document_embeddings
                GROUP BY embedding_model, embedding_status
                """
            ).fetchall()
            embedding_count = conn.execute(
                "SELECT COUNT(*) FROM official_document_embeddings"
            ).fetchone()[0]

        return {
            "table_exists": True,
            "embedding_count": embedding_count,
            "chunk_status_counts": {
                (row["embedding_status"] or "null"): row["count"]
                for row in chunk_status_rows
            },
            "model_counts": {
                f"{row['embedding_model']}::{row['embedding_status']}": row["count"]
                for row in model_rows
            },
        }

    def create_rag_search_log(self, payload: dict[str, Any]) -> dict[str, Any]:
        now = datetime.now(timezone.utc).isoformat()
        payload = dict(payload)
        payload.setdefault("created_at", now)
        payload.setdefault("strict_filter", {})
        payload.setdefault("matched_chunk_ids", [])
        payload.setdefault("score", {})
        payload.setdefault("raw_json", payload.copy())

        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO rag_search_logs (
                  search_id, session_id, query, product_type, model_name,
                  procedure_type, strict_filter_json, matched_chunk_ids_json,
                  score_json, no_match_reason, created_at, raw_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    payload["search_id"],
                    payload.get("session_id"),
                    payload["query"],
                    payload.get("product_type"),
                    payload.get("model_name"),
                    payload.get("procedure_type"),
                    json.dumps(payload.get("strict_filter", {}), ensure_ascii=False),
                    json.dumps(payload.get("matched_chunk_ids", []), ensure_ascii=False),
                    json.dumps(payload.get("score", {}), ensure_ascii=False),
                    payload.get("no_match_reason"),
                    payload["created_at"],
                    json.dumps(payload["raw_json"], ensure_ascii=False),
                ),
            )
            conn.commit()

        return payload

    def create_safety_audit_log(self, payload: dict[str, Any]) -> dict[str, Any]:
        now = datetime.now(timezone.utc).isoformat()
        payload = dict(payload)
        payload.setdefault("created_at", now)
        payload.setdefault("reasons", [])
        payload.setdefault("forbidden_actions", [])
        payload.setdefault("evidence_refs", [])
        payload.setdefault("raw_json", payload.copy())

        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO safety_audit_logs (
                  audit_id, session_id, user_id, device_id, risk_level, blocked,
                  decision_action, reasons_json, forbidden_actions_json,
                  evidence_refs_json, customer_message_template_id, created_at, raw_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    payload["audit_id"],
                    payload.get("session_id"),
                    payload.get("user_id"),
                    payload.get("device_id"),
                    payload["risk_level"],
                    int(bool(payload.get("blocked"))),
                    payload["decision_action"],
                    json.dumps(payload.get("reasons", []), ensure_ascii=False),
                    json.dumps(payload.get("forbidden_actions", []), ensure_ascii=False),
                    json.dumps(payload.get("evidence_refs", []), ensure_ascii=False),
                    payload.get("customer_message_template_id"),
                    payload["created_at"],
                    json.dumps(payload["raw_json"], ensure_ascii=False),
                ),
            )
            conn.commit()

        return payload

    def get_intent_risk_test_cases(self, product_type: str | None = None) -> list[dict[str, Any]]:
        query = "SELECT * FROM intent_risk_test_cases WHERE 1=1"
        params: list[Any] = []
        if product_type:
            query += " AND product_type = ?"
            params.append(product_type)
        query += " ORDER BY case_id ASC"
        with self.connect() as conn:
            rows = conn.execute(query, tuple(params)).fetchall()
            return self._rows_to_dicts(rows)

    def save_intent_risk_eval_result(self, payload: dict[str, Any]) -> dict[str, Any]:
        now = datetime.now(timezone.utc).isoformat()
        payload = dict(payload)
        payload.setdefault("evaluated_at", now)
        payload.setdefault("raw_json", payload.copy())

        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO intent_risk_eval_results (
                  eval_result_id, run_id, case_id, predicted_intent, predicted_risk,
                  predicted_action, is_intent_correct, is_risk_correct,
                  is_action_correct, error_type, evaluated_at, raw_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    payload["eval_result_id"],
                    payload["run_id"],
                    payload["case_id"],
                    payload["predicted_intent"],
                    payload["predicted_risk"],
                    payload["predicted_action"],
                    int(bool(payload.get("is_intent_correct"))),
                    int(bool(payload.get("is_risk_correct"))),
                    int(bool(payload.get("is_action_correct"))),
                    payload.get("error_type"),
                    payload["evaluated_at"],
                    json.dumps(payload["raw_json"], ensure_ascii=False),
                ),
            )
            conn.commit()

        return payload

    def find_official_contents(
        self,
        product_type: str,
        procedure_type: str,
        language: str | None = None,
        model_name: str | None = None,
    ) -> list[dict[str, Any]]:
        query = """
            SELECT * FROM official_contents
            WHERE product_type = ?
              AND procedure_type = ?
        """
        params: list[Any] = [product_type, procedure_type]
        if language:
            query += " AND language = ?"
            params.append(language)
        if model_name:
            query += " AND (model_name = ? OR model_name IS NULL)"
            params.append(model_name)
        query += " ORDER BY model_name DESC, content_id ASC"
        with self.connect() as conn:
            rows = conn.execute(query, tuple(params)).fetchall()
            return self._rows_to_dicts(rows)

    def get_reference_image(
        self,
        reference_image_id: str | None = None,
        model_name: str | None = None,
        structure_type: str | None = None,
        image_role: str | None = None,
    ) -> dict[str, Any] | None:
        query = "SELECT * FROM reference_images WHERE 1=1"
        params: list[Any] = []
        if reference_image_id:
            query += " AND reference_image_id = ?"
            params.append(reference_image_id)
        if model_name:
            query += " AND model_name = ?"
            params.append(model_name)
        if structure_type:
            query += " AND structure_type = ?"
            params.append(structure_type)
        if image_role:
            query += " AND image_role = ?"
            params.append(image_role)
        query += " ORDER BY version DESC LIMIT 1"

        with self.connect() as conn:
            row = conn.execute(query, tuple(params)).fetchone()
            return self._row_to_dict(row)

    def get_part_map_version(
        self,
        part_map_version_id: str | None = None,
        reference_image_id: str | None = None,
        structure_type: str | None = None,
    ) -> dict[str, Any] | None:
        query = "SELECT * FROM part_map_versions WHERE 1=1"
        params: list[Any] = []
        if part_map_version_id:
            query += " AND part_map_version_id = ?"
            params.append(part_map_version_id)
        if reference_image_id:
            query += " AND reference_image_id = ?"
            params.append(reference_image_id)
        if structure_type:
            query += " AND structure_type = ?"
            params.append(structure_type)
        query += " ORDER BY calibrated_at DESC LIMIT 1"

        with self.connect() as conn:
            row = conn.execute(query, tuple(params)).fetchone()
            return self._row_to_dict(row)

    def list_structure_types(self, product_type: str | None = None) -> list[dict[str, Any]]:
        query = "SELECT * FROM structure_types WHERE active = 1"
        params: list[Any] = []
        if product_type:
            query += " AND product_type = ?"
            params.append(product_type)
        query += " ORDER BY demo_priority ASC, structure_type ASC"
        with self.connect() as conn:
            rows = conn.execute(query, tuple(params)).fetchall()
            return self._rows_to_dicts(rows)

    def get_structure_type(self, structure_type: str) -> dict[str, Any] | None:
        with self.connect() as conn:
            row = conn.execute(
                "SELECT * FROM structure_types WHERE structure_type = ? LIMIT 1",
                (structure_type,),
            ).fetchone()
            return self._row_to_dict(row)

    def get_ar_guide_template(
        self,
        template_id: str | None = None,
        guide_id: str | None = None,
        product_type: str | None = None,
        procedure_type: str | None = None,
        structure_type: str | None = None,
    ) -> dict[str, Any] | None:
        query = "SELECT * FROM ar_guide_templates WHERE approved_status IN ('development_ready', 'approved')"
        params: list[Any] = []
        if template_id:
            query += " AND template_id = ?"
            params.append(template_id)
        if guide_id:
            query += " AND guide_id = ?"
            params.append(guide_id)
        if product_type:
            query += " AND product_type = ?"
            params.append(product_type)
        if procedure_type:
            query += " AND procedure_type = ?"
            params.append(procedure_type)
        if structure_type:
            query += " AND (structure_type = ? OR structure_type IS NULL)"
            params.append(structure_type)
        query += " ORDER BY structure_type DESC, version DESC LIMIT 1"
        with self.connect() as conn:
            row = conn.execute(query, tuple(params)).fetchone()
            return self._row_to_dict(row)

    def get_current_environment_observation(self, region: str, city: str | None = None) -> dict[str, Any] | None:
        with self.connect() as conn:
            if city:
                row = conn.execute(
                    """
                    SELECT * FROM environment_observations
                    WHERE region = ? AND city = ?
                    ORDER BY observed_at DESC
                    LIMIT 1
                    """,
                    (region, city),
                ).fetchone()
                if row:
                    return self._row_to_dict(row)
            row = conn.execute(
                """
                SELECT * FROM environment_observations
                WHERE region = ?
                ORDER BY observed_at DESC
                LIMIT 1
                """,
                (region,),
            ).fetchone()
            return self._row_to_dict(row)

    def list_environment_providers(self) -> list[dict[str, Any]]:
        with self.connect() as conn:
            rows = conn.execute(
                "SELECT * FROM environment_providers WHERE enabled = 1 ORDER BY provider_id"
            ).fetchall()
            return self._rows_to_dicts(rows)

    def create_environment_fetch_log(self, payload: dict[str, Any]) -> dict[str, Any]:
        now = datetime.now(timezone.utc).isoformat()
        payload = dict(payload)
        payload.setdefault("fetched_at", now)
        payload.setdefault("response_summary", {})
        payload.setdefault("raw_json", payload.copy())
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO environment_api_fetch_logs (
                  fetch_log_id, provider_id, request_region, request_city, status,
                  fetched_at, error_message, response_summary_json, raw_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    payload["fetch_log_id"],
                    payload["provider_id"],
                    payload.get("request_region"),
                    payload.get("request_city"),
                    payload["status"],
                    payload["fetched_at"],
                    payload.get("error_message"),
                    json.dumps(payload.get("response_summary", {}), ensure_ascii=False),
                    json.dumps(payload["raw_json"], ensure_ascii=False),
                ),
            )
            conn.commit()
        return payload

    def get_care_risk_rules(self, product_type: str, procedure_type: str | None = None) -> list[dict[str, Any]]:
        query = "SELECT * FROM care_risk_rules WHERE product_type = ? AND enabled = 1"
        params: list[Any] = [product_type]
        if procedure_type:
            query += " AND procedure_type = ?"
            params.append(procedure_type)
        query += " ORDER BY rule_id"
        with self.connect() as conn:
            rows = conn.execute(query, tuple(params)).fetchall()
            return self._rows_to_dicts(rows)

    def create_care_risk_score(self, payload: dict[str, Any]) -> dict[str, Any]:
        now = datetime.now(timezone.utc).isoformat()
        payload = dict(payload)
        payload.setdefault("computed_at", now)
        payload.setdefault("reasons", [])
        payload.setdefault("raw_json", payload.copy())
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO care_risk_scores (
                  score_id, user_id, device_id, product_type, procedure_type,
                  score, risk_level, reasons_json, usage_log_id,
                  environment_observation_id, computed_at, raw_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    payload["score_id"],
                    payload["user_id"],
                    payload["device_id"],
                    payload["product_type"],
                    payload["procedure_type"],
                    payload["score"],
                    payload["risk_level"],
                    json.dumps(payload.get("reasons", []), ensure_ascii=False),
                    payload.get("usage_log_id"),
                    payload.get("environment_observation_id"),
                    payload["computed_at"],
                    json.dumps(payload["raw_json"], ensure_ascii=False),
                ),
            )
            conn.commit()
        return payload

    def get_latest_care_risk_score(self, device_id: str) -> dict[str, Any] | None:
        with self.connect() as conn:
            row = conn.execute(
                """
                SELECT * FROM care_risk_scores
                WHERE device_id = ?
                ORDER BY computed_at DESC
                LIMIT 1
                """,
                (device_id,),
            ).fetchone()
            return self._row_to_dict(row)

    def create_preventive_alert(self, payload: dict[str, Any]) -> dict[str, Any]:
        now = datetime.now(timezone.utc).isoformat()
        payload = dict(payload)
        payload.setdefault("created_at", now)
        payload.setdefault("status", "created")
        payload.setdefault("raw_json", payload.copy())
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO preventive_alerts (
                  alert_id, score_id, user_id, device_id, procedure_type, title,
                  message, status, created_at, shown_at, raw_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    payload["alert_id"],
                    payload["score_id"],
                    payload["user_id"],
                    payload["device_id"],
                    payload["procedure_type"],
                    payload["title"],
                    payload["message"],
                    payload["status"],
                    payload["created_at"],
                    payload.get("shown_at"),
                    json.dumps(payload["raw_json"], ensure_ascii=False),
                ),
            )
            conn.commit()
        return payload

    def list_preventive_alerts(
        self,
        user_id: str | None = None,
        device_id: str | None = None,
        status: str | None = None,
    ) -> list[dict[str, Any]]:
        query = "SELECT * FROM preventive_alerts WHERE 1=1"
        params: list[Any] = []
        if user_id:
            query += " AND user_id = ?"
            params.append(user_id)
        if device_id:
            query += " AND device_id = ?"
            params.append(device_id)
        if status:
            query += " AND status = ?"
            params.append(status)
        query += " ORDER BY created_at DESC"
        with self.connect() as conn:
            rows = conn.execute(query, tuple(params)).fetchall()
            return self._rows_to_dicts(rows)

    def get_preventive_alert(self, alert_id: str) -> dict[str, Any] | None:
        with self.connect() as conn:
            row = conn.execute(
                "SELECT * FROM preventive_alerts WHERE alert_id = ? LIMIT 1",
                (alert_id,),
            ).fetchone()
            return self._row_to_dict(row)

    def create_preventive_alert_action(self, payload: dict[str, Any]) -> dict[str, Any]:
        now = datetime.now(timezone.utc).isoformat()
        payload = dict(payload)
        payload.setdefault("created_at", now)
        payload.setdefault("raw_json", payload.copy())
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO preventive_alert_actions (
                  action_id, alert_id, user_id, action_type, selected_content_id,
                  selected_session_id, created_at, raw_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    payload["action_id"],
                    payload["alert_id"],
                    payload["user_id"],
                    payload["action_type"],
                    payload.get("selected_content_id"),
                    payload.get("selected_session_id"),
                    payload["created_at"],
                    json.dumps(payload["raw_json"], ensure_ascii=False),
                ),
            )
            conn.commit()
        return payload

    def create_notification_log(self, payload: dict[str, Any]) -> dict[str, Any]:
        now = datetime.now(timezone.utc).isoformat()
        payload = dict(payload)
        payload.setdefault("sent_at", now)
        payload.setdefault("raw_json", payload.copy())
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO notification_logs (
                  notification_id, alert_id, user_id, device_id, channel, status,
                  message, sent_at, clicked_at, raw_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    payload["notification_id"],
                    payload.get("alert_id"),
                    payload["user_id"],
                    payload.get("device_id"),
                    payload["channel"],
                    payload["status"],
                    payload.get("message"),
                    payload.get("sent_at"),
                    payload.get("clicked_at"),
                    json.dumps(payload["raw_json"], ensure_ascii=False),
                ),
            )
            conn.commit()
        return payload

    def create_care_content_match(self, payload: dict[str, Any]) -> dict[str, Any]:
        now = datetime.now(timezone.utc).isoformat()
        payload = dict(payload)
        payload.setdefault("created_at", now)
        payload.setdefault("evidence_refs", [])
        payload.setdefault("raw_json", payload.copy())
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO care_content_matches (
                  match_id, alert_id, content_id, template_id, match_type,
                  match_score, evidence_refs_json, created_at, raw_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    payload["match_id"],
                    payload["alert_id"],
                    payload.get("content_id"),
                    payload.get("template_id"),
                    payload["match_type"],
                    payload.get("match_score"),
                    json.dumps(payload.get("evidence_refs", []), ensure_ascii=False),
                    payload["created_at"],
                    json.dumps(payload["raw_json"], ensure_ascii=False),
                ),
            )
            conn.commit()
        return payload

    def get_care_content_matches(self, alert_id: str) -> list[dict[str, Any]]:
        with self.connect() as conn:
            rows = conn.execute(
                "SELECT * FROM care_content_matches WHERE alert_id = ? ORDER BY match_score DESC",
                (alert_id,),
            ).fetchall()
            return self._rows_to_dicts(rows)

    def create_decision_log(self, payload: dict[str, Any]) -> dict[str, Any]:
        now = datetime.now(timezone.utc).isoformat()
        payload = dict(payload)
        payload.setdefault("created_at", now)
        payload.setdefault("evidence_refs", [])
        payload.setdefault("raw_json", payload.copy())
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO decision_logs (
                  decision_log_id, session_id, user_id, device_id, request_id,
                  intent_type, risk_level, decision_action, procedure_type,
                  official_match_status, evidence_refs_json, created_at, raw_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    payload["decision_log_id"],
                    payload.get("session_id"),
                    payload["user_id"],
                    payload["device_id"],
                    payload.get("request_id"),
                    payload.get("intent_type"),
                    payload.get("risk_level"),
                    payload["decision_action"],
                    payload.get("procedure_type"),
                    payload.get("official_match_status"),
                    json.dumps(payload.get("evidence_refs", []), ensure_ascii=False),
                    payload["created_at"],
                    json.dumps(payload["raw_json"], ensure_ascii=False),
                ),
            )
            conn.commit()
        return payload

    def create_service_route_log(self, payload: dict[str, Any]) -> dict[str, Any]:
        now = datetime.now(timezone.utc).isoformat()
        payload = dict(payload)
        payload.setdefault("created_at", now)
        payload.setdefault("status", "created")
        payload.setdefault("raw_json", payload.copy())
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO service_route_logs (
                  route_log_id, session_id, user_id, device_id, route_type,
                  reason, status, created_at, raw_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    payload["route_log_id"],
                    payload.get("session_id"),
                    payload["user_id"],
                    payload["device_id"],
                    payload["route_type"],
                    payload["reason"],
                    payload["status"],
                    payload["created_at"],
                    json.dumps(payload["raw_json"], ensure_ascii=False),
                ),
            )
            conn.commit()
        return payload

    def create_ar_step_log(self, payload: dict[str, Any]) -> dict[str, Any]:
        now = datetime.now(timezone.utc).isoformat()
        payload = dict(payload)
        payload.setdefault("created_at", now)
        payload.setdefault("raw_json", payload.copy())
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO ar_step_logs (
                  step_log_id, session_id, guide_step_id, step_order, action,
                  status, created_at, raw_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    payload["step_log_id"],
                    payload["session_id"],
                    payload.get("guide_step_id"),
                    payload.get("step_order"),
                    payload["action"],
                    payload["status"],
                    payload["created_at"],
                    json.dumps(payload["raw_json"], ensure_ascii=False),
                ),
            )
            conn.commit()
        return payload

    def get_ar_step_logs(self, session_id: str) -> list[dict[str, Any]]:
        with self.connect() as conn:
            rows = conn.execute(
                "SELECT * FROM ar_step_logs WHERE session_id = ? ORDER BY created_at ASC",
                (session_id,),
            ).fetchall()
            return self._rows_to_dicts(rows)

    def get_ar_overlay_validation_logs(
        self,
        reference_image_id: str | None = None,
        part_map_version_id: str | None = None,
        structure_type: str | None = None,
    ) -> list[dict[str, Any]]:
        query = "SELECT * FROM ar_overlay_validation_logs WHERE 1=1"
        params: list[Any] = []
        if reference_image_id:
            query += " AND reference_image_id = ?"
            params.append(reference_image_id)
        if part_map_version_id:
            query += " AND part_map_version_id = ?"
            params.append(part_map_version_id)
        if structure_type:
            query += " AND structure_type = ?"
            params.append(structure_type)
        query += " ORDER BY validated_at DESC"
        with self.connect() as conn:
            rows = conn.execute(query, tuple(params)).fetchall()
            return self._rows_to_dicts(rows)


if __name__ == "__main__":
    repo = CareShotRepository()
    print(json.dumps(repo.get_user_profile("U001"), ensure_ascii=False, indent=2))
