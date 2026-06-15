from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from sqlalchemy import text

from .database import DEFAULT_SQLITE_DB_PATH, SQLAlchemySessionManager
from .utils import row_to_dict, rows_to_dicts


TABLE_NAME_ALIASES = {
    "users": "USER",
    "devices": "USER_PRODUCT",
    "usage_logs": "APPLIANCE_USAGE_LOG",
    "smart_diagnosis_results": "SMART_DIAGNOSIS_RESULT",
    "environment_observations": "ENVIRONMENT_OBSERVATION",
    "official_assets": "OFFICIAL_ASSET",
    "official_document_chunks": "OFFICIAL_DOCUMENT_CHUNK",
    "official_document_embeddings": "OFFICIAL_DOCUMENT_EMBEDDING",
    "official_contents": "GUIDE",
    "product_code_registry": "PRODUCT",
    "reference_images": "AR_TARGET",
    "ar_guide_templates": "AR_GUIDE",
    "ar_guide_steps": "AR_GUIDE",
}


def quote_table_name(table_name: str) -> str:
    physical_name = TABLE_NAME_ALIASES.get(table_name, table_name)
    escaped = physical_name.replace('"', '""')
    return f'"{escaped}"'


class BaseRepository:
    def __init__(self, manager: SQLAlchemySessionManager | None = None) -> None:
        self.manager = manager or SQLAlchemySessionManager()

    def _statement(self, sql: str, params: tuple[Any, ...] = ()) -> tuple[Any, dict[str, Any]]:
        named_params: dict[str, Any] = {}
        parts: list[str] = []
        param_index = 0
        for char in sql:
            if char == "?":
                key = f"p{param_index}"
                parts.append(f":{key}")
                named_params[key] = params[param_index]
                param_index += 1
            else:
                parts.append(char)
        if param_index != len(params):
            raise ValueError(f"SQL parameter mismatch: placeholders={param_index}, params={len(params)}")
        return text("".join(parts)), named_params

    def fetch_one(self, sql: str, params: tuple[Any, ...] = ()) -> dict[str, Any] | None:
        statement, named_params = self._statement(sql, params)
        with self.manager.read() as conn:
            row = conn.execute(statement, named_params).mappings().fetchone()
            return row_to_dict(row)

    def fetch_all(self, sql: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
        statement, named_params = self._statement(sql, params)
        with self.manager.read() as conn:
            rows = conn.execute(statement, named_params).mappings().fetchall()
            return rows_to_dicts(rows)

    def execute_write(self, sql: str, params: tuple[Any, ...] = ()) -> None:
        statement, named_params = self._statement(sql, params)
        with self.manager.write() as conn:
            conn.execute(statement, named_params)

    def count(self, table_name: str) -> int:
        with self.manager.read() as conn:
            return int(conn.execute(text(f"SELECT COUNT(*) FROM {quote_table_name(table_name)}")).scalar_one())


class RepositoryConfig:
    def __init__(self, database_url: str | None = None, db_path: str | Path = DEFAULT_SQLITE_DB_PATH) -> None:
        self.database_url = database_url
        self.db_path = Path(db_path)


def json_param(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))
