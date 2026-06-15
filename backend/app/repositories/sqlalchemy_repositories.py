from __future__ import annotations

import json
import re
from typing import Any

from .base import BaseRepository, json_param
from .utils import normalize_payload, utc_now


def _normalize_product_code(value: str | None) -> str:
    return re.sub(r"[^A-Z0-9]", "", (value or "").upper())


def _user_email_from_demo_id(user_id: str | None) -> str | None:
    if not user_id:
        return None
    if "@" in user_id:
        return user_id
    match = re.fullmatch(r"U(\d+)", user_id.upper())
    if match:
        return f"u{int(match.group(1)):03d}@careshot.local"
    return user_id


def _demo_user_id_from_email(user_email: str | None) -> str | None:
    if not user_email:
        return None
    match = re.fullmatch(r"u(\d+)@careshot\.local", user_email.lower())
    if match:
        return f"U{int(match.group(1)):03d}"
    return user_email


def _product_code_from_device_id(device_id: str | None) -> str | None:
    if not device_id:
        return None
    if device_id.upper() == "D001":
        return "AS-Q24ENXE"
    return device_id


def _device_id_from_product_code(product_code: str | None) -> str | None:
    if product_code == "AS-Q24ENXE":
        return "D001"
    return product_code


def _load_json(value: Any, default: Any = None) -> Any:
    if value is None:
        return default
    if isinstance(value, (dict, list)):
        return value
    try:
        return json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return default


def _content_id_from_guide_id(guide_id: Any) -> str:
    return f"GUIDE_{guide_id}"


def _guide_id_from_content_id(content_id: str | None) -> str | None:
    if not content_id:
        return None
    return content_id.removeprefix("GUIDE_")


def _split_guide_steps(guide_text: str | None) -> list[str]:
    if not guide_text:
        return []
    steps: list[str] = []
    for line in guide_text.splitlines():
        cleaned = line.strip()
        cleaned = re.sub(r"^\d+[\.\)]\s*", "", cleaned)
        if cleaned:
            steps.append(cleaned)
    return steps


_EPHEMERAL_AR_SESSIONS: dict[str, dict[str, Any]] = {}
_EPHEMERAL_AR_STEP_LOGS: dict[str, list[dict[str, Any]]] = {}


class SQLAlchemyUserRepository(BaseRepository):
    def get_user_profile(self, user_id: str) -> dict[str, Any] | None:
        user_email = _user_email_from_demo_id(user_id)
        row = self.fetch_one(
            """
            SELECT u.*, r.country, r.state AS region, r.city, r.timezone,
                   r.climate_zone, r.water_hardness_level
            FROM "USER" u
            LEFT JOIN "REGION" r ON r.region_id = u.region_id
            WHERE u.user_email = ?
            LIMIT 1
            """,
            (user_email,),
        )
        if not row:
            return None
        return {
            **row,
            "user_id": user_id if user_id and "@" not in user_id else _demo_user_id_from_email(row["user_email"]),
            "video_style": "step_by_step",
        }

    def register_user_with_demo_seed(self, payload: dict[str, Any]) -> dict[str, Any]:
        user_email = str(payload.get("user_email") or payload.get("email") or "").strip().lower()
        if not user_email or "@" not in user_email:
            raise ValueError("valid user_email is required")

        now = utc_now()
        region_id = self.resolve_signup_region_id(payload)
        existing = self.fetch_one('SELECT * FROM "USER" WHERE user_email = ? LIMIT 1', (user_email,))
        password = payload.get("password") or (existing or {}).get("password") or "demo_password"
        values = (
            password,
            payload.get("name") or payload.get("customer_name") or user_email.split("@")[0],
            payload.get("phone") or payload.get("phone_number"),
            payload.get("address"),
            region_id,
            payload.get("preferred_language") or "en",
            user_email,
        )
        if existing:
            self.execute_write(
                """
                UPDATE "USER"
                SET password = ?, name = ?, phone = ?, address = ?, region_id = ?, preferred_language = ?
                WHERE user_email = ?
                """,
                values,
            )
        else:
            self.execute_write(
                """
                INSERT INTO "USER" (
                  password, name, phone, address, region_id, preferred_language, user_email
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                values,
            )

        self.ensure_demo_product_seed(user_email=user_email, product_code="AS-Q24ENXE", now=now)
        profile = self.get_user_profile(user_email) or {}
        profile["demo_seed"] = {
            "product_code": "AS-Q24ENXE",
            "user_product": True,
            "usage_log": True,
            "smart_diagnosis": True,
            "self_management_history": True,
        }
        return profile

    def verify_user_login(self, user_email: str, password: str) -> dict[str, Any] | None:
        normalized_email = str(user_email or "").strip().lower()
        row = self.fetch_one(
            'SELECT * FROM "USER" WHERE user_email = ? AND password = ? LIMIT 1',
            (normalized_email, password),
        )
        if not row:
            return None
        return self.get_user_profile(normalized_email)

    def resolve_signup_region_id(self, payload: dict[str, Any]) -> str:
        region_id = str(payload.get("region_id") or "").strip()
        if region_id:
            row = self.fetch_one('SELECT region_id FROM "REGION" WHERE region_id = ? LIMIT 1', (region_id,))
            if row:
                return str(row["region_id"])

        region = str(payload.get("region") or payload.get("state") or "").strip()
        city = str(payload.get("city") or "").strip() or None
        if region:
            row = self.fetch_one(
                """
                SELECT region_id
                FROM "REGION"
                WHERE state = ? OR region_id = ?
                ORDER BY CASE WHEN (? IS NOT NULL AND city = ?) THEN 0 ELSE 1 END
                LIMIT 1
                """,
                (region, region, city, city),
            )
            if row:
                return str(row["region_id"])

        address = str(payload.get("address") or "").lower()
        address_matches = [
            (("new delhi", "delhi", "connaught", "뉴델리", "델리", "코넛"), "Delhi", "Delhi"),
            (("ahmedabad", "gujarat", "아메다바드", "구자라트"), "Gujarat", "Ahmedabad"),
        ]
        for keywords, state, matched_city in address_matches:
            if any(keyword in address for keyword in keywords):
                row = self.fetch_one(
                    """
                    SELECT region_id
                    FROM "REGION"
                    WHERE state = ? AND city = ?
                    LIMIT 1
                    """,
                    (state, matched_city),
                )
                if row:
                    return str(row["region_id"])

        row = self.fetch_one(
            'SELECT region_id FROM "REGION" WHERE state = ? AND city = ? LIMIT 1',
            ("Delhi", "Delhi"),
        )
        return str((row or {}).get("region_id") or "INDIA_DELHI_DELHI")

    def ensure_demo_product_seed(self, user_email: str, product_code: str, now: str) -> None:
        product = self.fetch_one('SELECT product_code, product_name FROM "PRODUCT" WHERE product_code = ? LIMIT 1', (product_code,))
        if not product:
            raise ValueError(f"Demo product not found: {product_code}")

        user_product = self.fetch_one(
            'SELECT user_email FROM "USER_PRODUCT" WHERE user_email = ? AND product_code = ? LIMIT 1',
            (user_email, product_code),
        )
        if not user_product:
            self.execute_write(
                """
                INSERT INTO "USER_PRODUCT" (
                  user_email, product_code, registration_attempt_id, display_name, registered_at
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (user_email, product_code, None, f"Air Conditioner {product_code}", now),
            )

        usage_log = self.fetch_one(
            'SELECT usage_log_id FROM "APPLIANCE_USAGE_LOG" WHERE user_email = ? AND product_code = ? LIMIT 1',
            (user_email, product_code),
        )
        if not usage_log:
            next_id = self.fetch_one('SELECT COALESCE(MAX(usage_log_id), 0) + 1 AS next_id FROM "APPLIANCE_USAGE_LOG"')
            self.execute_write(
                """
                INSERT INTO "APPLIANCE_USAGE_LOG" (
                  usage_log_id, product_code, user_email, usage_period_days, recent_used_hours,
                  last_used_at, setting_temperature, operation_mode, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                ((next_id or {}).get("next_id") or 1, product_code, user_email, 7, 42, now, 24, "cool", now),
            )

        diagnosis = self.fetch_one(
            'SELECT diagnosis_id FROM "SMART_DIAGNOSIS_RESULT" WHERE user_email = ? AND product_code = ? LIMIT 1',
            (user_email, product_code),
        )
        if not diagnosis:
            next_id = self.fetch_one('SELECT COALESCE(MAX(diagnosis_id), 0) + 1 AS next_id FROM "SMART_DIAGNOSIS_RESULT"')
            raw_result = {
                "diagnosis_id": f"SD_SIGNUP_{str(user_email).replace('@', '_')}",
                "user_id": user_email,
                "device_id": "D001",
                "product_type": "air_conditioner",
                "model_name": product_code,
                "result_code": "NORMAL",
                "severity": "none",
                "summary": "Normal signup demo smart diagnosis seed.",
                "detected_signals": ["normal"],
                "scenario_basis": "Generated at signup for DB-backed frontend demo.",
                "evidence_level": "demo_synthetic",
                "created_at": now,
            }
            self.execute_write(
                """
                INSERT INTO "SMART_DIAGNOSIS_RESULT" (
                  diagnosis_id, user_email, product_code, diagnosis_code, diagnosis_message,
                  severity_level, raw_result_json, diagnosed_at, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    (next_id or {}).get("next_id") or 1,
                    user_email,
                    product_code,
                    "NORMAL",
                    "Normal signup demo smart diagnosis seed.",
                    None,
                    json_param(raw_result),
                    now,
                    now,
                ),
            )

        history = self.fetch_one(
            'SELECT history_id FROM "SELF_MANAGEMENT_HISTORY" WHERE user_email = ? AND product_code = ? LIMIT 1',
            (user_email, product_code),
        )
        if not history:
            next_id = self.fetch_one('SELECT COALESCE(MAX(history_id), 0) + 1 AS next_id FROM "SELF_MANAGEMENT_HISTORY"')
            self.execute_write(
                """
                INSERT INTO "SELF_MANAGEMENT_HISTORY" (
                  history_id, product_code, user_email, management_category, management_type, created_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                ((next_id or {}).get("next_id") or 1, product_code, user_email, "filter_cleaning", "self_care", now),
            )


class SQLAlchemyDeviceRepository(BaseRepository):
    def get_device_context(self, device_id: str) -> dict[str, Any] | None:
        product_code = _product_code_from_device_id(device_id)
        row = self.fetch_one(
            """
            SELECT
              p.*,
              up.user_email,
              up.display_name,
              up.registered_at,
              u.region_id,
              r.state AS region,
              r.city,
              r.country,
              r.timezone,
              r.climate_zone,
              r.water_hardness_level
            FROM "PRODUCT" p
            LEFT JOIN "USER_PRODUCT" up ON up.product_code = p.product_code
            LEFT JOIN "USER" u ON u.user_email = up.user_email
            LEFT JOIN "REGION" r ON r.region_id = u.region_id
            WHERE p.product_code = ? OR p.model_name = ?
            ORDER BY up.registered_at ASC
            LIMIT 1
            """,
            (product_code, product_code),
        )
        if not row:
            return None
        return {
            **row,
            "device_id": device_id,
            "user_id": _demo_user_id_from_email(row.get("user_email")),
            "model_aliases": [],
            "series": None,
        }

    def get_device_context_for_user(self, user_id: str, device_id: str) -> dict[str, Any] | None:
        user_email = _user_email_from_demo_id(user_id)
        product_code = _product_code_from_device_id(device_id)
        row = self.fetch_one(
            """
            SELECT
              p.*,
              up.user_email,
              up.display_name,
              up.registered_at,
              u.region_id,
              r.state AS region,
              r.city,
              r.country,
              r.timezone,
              r.climate_zone,
              r.water_hardness_level
            FROM "PRODUCT" p
            JOIN "USER_PRODUCT" up ON up.product_code = p.product_code
            JOIN "USER" u ON u.user_email = up.user_email
            LEFT JOIN "REGION" r ON r.region_id = u.region_id
            WHERE up.user_email = ?
              AND (p.product_code = ? OR p.model_name = ?)
            LIMIT 1
            """,
            (user_email, product_code, product_code),
        )
        if not row:
            return self.get_device_context(device_id)
        return {
            **row,
            "device_id": device_id,
            "user_id": _demo_user_id_from_email(row.get("user_email")),
            "model_aliases": [],
            "series": None,
        }


class SQLAlchemyUsageLogRepository(BaseRepository):
    def get_usage_log(self, device_id: str) -> dict[str, Any] | None:
        product_code = _product_code_from_device_id(device_id)
        row = self.fetch_one(
            """
            SELECT * FROM "APPLIANCE_USAGE_LOG"
            WHERE product_code = ?
            ORDER BY created_at DESC
            LIMIT 1
            """,
            (product_code,),
        )
        if not row:
            return None
        return {
            **row,
            "device_id": device_id,
            "user_id": _demo_user_id_from_email(row.get("user_email")),
            "care_triggers": ["filter_cleaning"],
            "updated_at": row.get("created_at"),
        }

    def get_usage_log_for_user(self, user_id: str, device_id: str) -> dict[str, Any] | None:
        user_email = _user_email_from_demo_id(user_id)
        product_code = _product_code_from_device_id(device_id)
        row = self.fetch_one(
            """
            SELECT * FROM "APPLIANCE_USAGE_LOG"
            WHERE user_email = ? AND product_code = ?
            ORDER BY created_at DESC
            LIMIT 1
            """,
            (user_email, product_code),
        )
        if not row:
            return self.get_usage_log(device_id)
        return {
            **row,
            "device_id": device_id,
            "user_id": _demo_user_id_from_email(row.get("user_email")),
            "care_triggers": ["filter_cleaning"],
            "updated_at": row.get("created_at"),
        }

    def get_smart_diagnosis(self, device_id: str, include_high_risk_sample: bool = False) -> dict[str, Any] | None:
        product_code = _product_code_from_device_id(device_id)
        if include_high_risk_sample:
            row = self.fetch_one(
                """
                SELECT * FROM "SMART_DIAGNOSIS_RESULT"
                WHERE product_code = ?
                ORDER BY
                  CASE severity_level WHEN 'high' THEN 0 WHEN 'medium' THEN 1 WHEN 'low' THEN 2 ELSE 3 END,
                  created_at DESC
                LIMIT 1
                """,
                (product_code,),
            )
        else:
            row = self.fetch_one(
                """
                SELECT * FROM "SMART_DIAGNOSIS_RESULT"
                WHERE product_code = ?
                ORDER BY created_at DESC
                LIMIT 1
                """,
                (product_code,),
            )
        if not row:
            return None
        raw = _load_json(row.get("raw_result_json"), {})
        return {
            **row,
            "device_id": device_id,
            "user_id": _demo_user_id_from_email(row.get("user_email")),
            "severity": row.get("severity_level") or raw.get("severity") or "none",
            "detected_signals": raw.get("detected_signals", []),
            "summary": row.get("diagnosis_message"),
        }

    def get_smart_diagnosis_for_user(
        self,
        user_id: str,
        device_id: str,
        include_high_risk_sample: bool = False,
    ) -> dict[str, Any] | None:
        user_email = _user_email_from_demo_id(user_id)
        product_code = _product_code_from_device_id(device_id)
        if include_high_risk_sample:
            row = self.fetch_one(
                """
                SELECT * FROM "SMART_DIAGNOSIS_RESULT"
                WHERE user_email = ? AND product_code = ?
                ORDER BY
                  CASE severity_level WHEN 'high' THEN 0 WHEN 'medium' THEN 1 WHEN 'low' THEN 2 ELSE 3 END,
                  created_at DESC
                LIMIT 1
                """,
                (user_email, product_code),
            )
        else:
            row = self.fetch_one(
                """
                SELECT * FROM "SMART_DIAGNOSIS_RESULT"
                WHERE user_email = ? AND product_code = ?
                ORDER BY created_at DESC
                LIMIT 1
                """,
                (user_email, product_code),
            )
        if not row:
            return self.get_smart_diagnosis(device_id, include_high_risk_sample)
        raw = _load_json(row.get("raw_result_json"), {})
        return {
            **row,
            "device_id": device_id,
            "user_id": _demo_user_id_from_email(row.get("user_email")),
            "severity": row.get("severity_level") or raw.get("severity") or "none",
            "detected_signals": raw.get("detected_signals", []),
            "summary": row.get("diagnosis_message"),
        }


class SQLAlchemyEnvironmentRepository(BaseRepository):
    def list_environment_refresh_targets(self, limit: int = 20) -> list[dict[str, Any]]:
        rows = self.fetch_all(
            """
            SELECT DISTINCT priority, region, city
            FROM (
              SELECT 0 AS priority, r.state AS region, r.city
              FROM "USER" u
              JOIN "REGION" r ON r.region_id = u.region_id
              WHERE r.state IS NOT NULL
                AND r.city IS NOT NULL
              UNION ALL
              SELECT 1 AS priority, r.state AS region, r.city
              FROM "ENVIRONMENT_OBSERVATION" eo
              JOIN "REGION" r ON r.region_id = eo.region_id
              WHERE r.state IS NOT NULL
                AND r.city IS NOT NULL
            )
            ORDER BY priority, region, city
            LIMIT ?
            """,
            (limit,),
        )
        default_targets = [
            {"region": "Delhi", "city": "Delhi"},
            {"region": "Gujarat", "city": "Ahmedabad"},
        ]
        combined = default_targets + rows
        if rows:
            seen: set[tuple[str, str]] = set()
            targets: list[dict[str, Any]] = []
            for row in combined:
                key = (str(row.get("region")), str(row.get("city")))
                if key in seen:
                    continue
                seen.add(key)
                targets.append({"region": row.get("region"), "city": row.get("city")})
                if len(targets) >= limit:
                    break
            return targets
        return default_targets[:limit]

    def get_environment_context(self, region: str, city: str | None = None) -> dict[str, Any] | None:
        return self.get_current_environment_observation(region, city)

    def get_current_environment_observation(self, region: str, city: str | None = None) -> dict[str, Any] | None:
        params: list[Any] = []
        sql = """
            SELECT eo.*, r.country, r.state AS region, r.city, r.timezone,
                   r.climate_zone, r.water_hardness_level
            FROM "ENVIRONMENT_OBSERVATION" eo
            JOIN "REGION" r ON r.region_id = eo.region_id
            WHERE (r.state = ? OR r.region_id = ?)
        """
        params.extend([region, region])
        if city:
            sql += " AND r.city = ?"
            params.append(city)
        sql += " ORDER BY eo.observed_at DESC, eo.observation_id DESC LIMIT 1"
        row = self.fetch_one(sql, tuple(params))
        if not row:
            return None
        return {
            **row,
            "temperature_c": row.get("temperature"),
            "humidity_percent": row.get("humidity"),
        }

    def list_environment_providers(self) -> list[dict[str, Any]]:
        return [{"provider_id": "ENV_PROVIDER_OPENWEATHER", "enabled": 1, "source": "ENVIRONMENT_OBSERVATION"}]

    def create_environment_observation(self, payload: dict[str, Any]) -> dict[str, Any]:
        payload = normalize_payload(payload, {"observed_at": utc_now, "payload": {}})
        next_id_row = self.fetch_one(
            'SELECT COALESCE(MAX(observation_id), 0) + 1 AS next_id FROM "ENVIRONMENT_OBSERVATION"'
        )
        region_id = self.resolve_region_id(
            payload.get("region_id") or payload.get("region") or "INDIA_GUJARAT_AHMEDABAD",
            payload.get("city"),
        )
        self.execute_write(
            """
            INSERT INTO "ENVIRONMENT_OBSERVATION" (
              observation_id, region_id, observed_at, temperature, humidity, aqi, pm25, pm10,
              rain_intensity, monsoon_intensity, provider, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                (next_id_row or {}).get("next_id") or 1,
                region_id,
                payload["observed_at"],
                payload.get("temperature_c"),
                payload.get("humidity_percent"),
                payload.get("aqi"),
                payload.get("pm25"),
                payload.get("pm10"),
                payload.get("rain_intensity"),
                payload.get("monsoon_intensity") or payload.get("rain_monsoon_intensity"),
                payload.get("provider_id") or payload.get("provider") or "ENV_PROVIDER_OPENWEATHER",
                payload.get("created_at") or utc_now(),
            ),
        )
        payload["observation_id"] = (next_id_row or {}).get("next_id") or 1
        payload["region_id"] = region_id
        return payload

    def resolve_region_id(self, region_id_or_state: str, city: str | None = None) -> str:
        row = self.fetch_one(
            """
            SELECT region_id
            FROM "REGION"
            WHERE region_id = ?
               OR (state = ? AND (? IS NULL OR city = ?))
            ORDER BY CASE WHEN region_id = ? THEN 0 ELSE 1 END
            LIMIT 1
            """,
            (region_id_or_state, region_id_or_state, city, city, region_id_or_state),
        )
        return (row or {}).get("region_id") or region_id_or_state

    def create_environment_fetch_log(self, payload: dict[str, Any]) -> dict[str, Any]:
        payload = normalize_payload(payload, {"fetched_at": utc_now, "response_summary": {}})
        return payload


class SQLAlchemyProductModelRepository(BaseRepository):
    def get_product_model(self, model_name: str, product_type: str | None = None) -> dict[str, Any] | None:
        sql = """
            SELECT *, product_code AS product_model_id
            FROM "PRODUCT"
            WHERE (model_name = ? OR product_code = ?)
        """
        params: list[Any] = [model_name, model_name]
        if product_type:
            sql += " AND product_type = ?"
            params.append(product_type)
        sql += " LIMIT 1"
        return self.fetch_one(sql, tuple(params))

    def get_product_model_by_structure(self, structure_type: str) -> dict[str, Any] | None:
        return self.fetch_one(
            """
            SELECT *, product_code AS product_model_id
            FROM "PRODUCT"
            WHERE structure_type = ? AND model_name IS NULL
            LIMIT 1
            """,
            (structure_type,),
        )

    def resolve_model_structure(self, model_name: str, product_type: str | None = None) -> dict[str, Any] | None:
        product = self.get_product_model(model_name, product_type)
        if not product:
            return None
        structure = {
            "structure_type": product.get("structure_type"),
            "product_type": product.get("product_type"),
            "active": 1,
        }
        reference = SQLAlchemyReferenceImageRepository(self.manager).get_reference_image(
            model_name=model_name,
            structure_type=product.get("structure_type"),
        )
        part_map_version = SQLAlchemyPartMapRepository(self.manager).get_part_map_version(
            reference_image_id=(reference or {}).get("reference_image_id"),
            structure_type=product.get("structure_type"),
        )
        return {
            "match_type": "exact_model",
            "model_name": model_name,
            "product_type": product["product_type"],
            "structure_type": product["structure_type"],
            "product_model": product,
            "structure": structure,
            "reference_image": reference,
            "part_map_version": part_map_version,
        }


class SQLAlchemyProductCodeRepository(BaseRepository):
    @staticmethod
    def normalize_product_code(input_code: str) -> str:
        return _normalize_product_code(input_code)

    def find_product_code(self, input_code: str) -> dict[str, Any] | None:
        normalized = self.normalize_product_code(input_code)
        rows = self.fetch_all(
            """
            SELECT *
            FROM "PRODUCT"
            """,
        )
        for row in rows:
            if _normalize_product_code(row.get("product_code")) == normalized or _normalize_product_code(row.get("model_name")) == normalized:
                supported = row.get("registration_supported") == "Y"
                return {
                    **row,
                    "product_code_id": row["product_code"],
                    "normalized_product_code": normalized,
                    "verification_status": "verified" if supported else "unverified",
                    "registration_supported": 1 if supported else 0,
                    "product_model_id": row["product_code"],
                }
        return None

    def create_product_registration_attempt(self, payload: dict[str, Any]) -> dict[str, Any]:
        payload = normalize_payload(payload, {"created_at": utc_now})
        self.execute_write(
            """
            INSERT INTO "PRODUCT_REGISTRATION_ATTEMPT" (
              user_email, input_product_code, normalized_input_code, matched_product_code,
              match_status, failure_reason, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                _user_email_from_demo_id(payload.get("user_id")),
                payload["input_code"],
                payload["normalized_input_code"],
                payload.get("matched_product_code_id"),
                payload["match_status"],
                payload.get("failure_reason"),
                payload["created_at"],
            ),
        )
        return payload


class SQLAlchemyStructureTypeRepository(BaseRepository):
    def list_structure_types(self, product_type: str | None = None) -> list[dict[str, Any]]:
        sql = """
            SELECT DISTINCT structure_type, product_type, 'Y' AS active
            FROM "PRODUCT"
            WHERE structure_type IS NOT NULL
        """
        params: list[Any] = []
        if product_type:
            sql += " AND product_type = ?"
            params.append(product_type)
        sql += " ORDER BY structure_type ASC"
        return self.fetch_all(sql, tuple(params))

    def get_structure_type(self, structure_type: str) -> dict[str, Any] | None:
        return self.fetch_one(
            """
            SELECT DISTINCT structure_type, product_type, 'Y' AS active
            FROM "PRODUCT"
            WHERE structure_type = ?
            LIMIT 1
            """,
            (structure_type,),
        )


class SQLAlchemyReferenceImageRepository(BaseRepository):
    def get_reference_image(
        self,
        reference_image_id: str | None = None,
        model_name: str | None = None,
        structure_type: str | None = None,
        image_role: str | None = None,
    ) -> dict[str, Any] | None:
        sql = """
            SELECT
              t.ar_target_id,
              'AR_TARGET_' || t.ar_target_id AS reference_image_id,
              p.model_name,
              p.product_type,
              p.structure_type,
              'open_cover_filter_visible' AS image_role,
              t.reference_image_path AS image_path,
              t.reference_image_path,
              t.mind_target_path,
              t.target_width,
              t.target_height,
              1 AS version,
              t.active,
              t.created_at
            FROM "AR_TARGET" t
            JOIN "PRODUCT" p ON p.product_code = t.product_code
            WHERE t.active = 'Y'
        """
        params: list[Any] = []
        if reference_image_id:
            sql += " AND ('AR_TARGET_' || t.ar_target_id = ? OR t.ar_target_id = ?)"
            params.extend([reference_image_id, reference_image_id.removeprefix("AR_TARGET_")])
        if model_name:
            sql += " AND p.model_name = ?"
            params.append(model_name)
        if structure_type:
            sql += " AND p.structure_type = ?"
            params.append(structure_type)
        sql += " ORDER BY t.ar_target_id DESC LIMIT 1"
        return self.fetch_one(sql, tuple(params))


class SQLAlchemyPartMapRepository(BaseRepository):
    def get_part_map(self, structure_type: str) -> list[dict[str, Any]]:
        product = self.fetch_one('SELECT product_type FROM "PRODUCT" WHERE structure_type = ? LIMIT 1', (structure_type,))
        product_type = (product or {}).get("product_type")
        if structure_type == "wall_ac_type_a":
            return [
                {"part_id": "power_area", "structure_type": structure_type, "product_type": product_type, "label": "Power area", "user_accessible": 1},
                {"part_id": "front_cover", "structure_type": structure_type, "product_type": product_type, "label": "Front cover", "user_accessible": 1},
                {"part_id": "front_filter", "structure_type": structure_type, "product_type": product_type, "label": "Filter", "user_accessible": 1},
                {"part_id": "air_outlet", "structure_type": structure_type, "product_type": product_type, "label": "Air outlet", "user_accessible": 1},
                {"part_id": "internal_electrical_area", "structure_type": structure_type, "product_type": product_type, "label": "Internal electrical area", "user_accessible": 0},
            ]
        return []

    def get_part_map_by_part(self, structure_type: str, part_id: str) -> dict[str, Any] | None:
        return next((part for part in self.get_part_map(structure_type) if part["part_id"] == part_id), None)

    def get_part_map_version(
        self,
        part_map_version_id: str | None = None,
        reference_image_id: str | None = None,
        structure_type: str | None = None,
    ) -> dict[str, Any] | None:
        if not structure_type and reference_image_id:
            reference = SQLAlchemyReferenceImageRepository(self.manager).get_reference_image(reference_image_id=reference_image_id)
            structure_type = (reference or {}).get("structure_type")
        if not structure_type:
            return None
        return {
            "part_map_version_id": part_map_version_id or f"PMV_{structure_type.upper()}_FROM_AR_GUIDE",
            "reference_image_id": reference_image_id,
            "structure_type": structure_type,
            "calibrated_at": None,
            "source_table": "AR_GUIDE.overlay_config_json",
        }

    def get_ar_overlay_validation_logs(
        self,
        reference_image_id: str | None = None,
        part_map_version_id: str | None = None,
        structure_type: str | None = None,
    ) -> list[dict[str, Any]]:
        return []


class SQLAlchemyOfficialAssetRepository(BaseRepository):
    def get_guide(self, guide_id: str) -> dict[str, Any] | None:
        physical_id = _guide_id_from_content_id(str(guide_id))
        row = self.fetch_one(
            """
            SELECT g.*, p.product_type, p.model_name, a.source_title, a.source_type AS asset_source_type
            FROM "GUIDE" g
            JOIN "PRODUCT" p ON p.product_code = g.product_code
            LEFT JOIN "OFFICIAL_ASSET" a ON a.asset_id = g.source_asset_id
            WHERE g.guide_id = ? AND g.is_active = 'Y'
            LIMIT 1
            """,
            (physical_id,),
        )
        return self._content_from_guide(row) if row else None

    def get_official_content(self, content_id: str) -> dict[str, Any] | None:
        guide_id = _guide_id_from_content_id(content_id)
        row = self.fetch_one(
            """
            SELECT g.*, a.source_title, a.source_type AS asset_source_type
            FROM "GUIDE" g
            LEFT JOIN "OFFICIAL_ASSET" a ON a.asset_id = g.source_asset_id
            WHERE g.guide_id = ? AND g.guide_type = 'manual'
            LIMIT 1
            """,
            (guide_id,),
        )
        return self._content_from_guide(row) if row else None

    def find_official_assets(
        self,
        model_name: str,
        product_type: str,
        aliases: list[str] | None = None,
        series: str | None = None,
    ) -> dict[str, Any]:
        rows = self.fetch_all(
            """
            SELECT *
            FROM "OFFICIAL_ASSET"
            WHERE verified_yn = 'Y'
              AND (product_type = ? OR product_type = 'common')
              AND (model_name = ? OR product_code = ? OR model_name IS NULL)
            ORDER BY
              CASE WHEN model_name = ? OR product_code = ? THEN 0 ELSE 1 END,
              asset_id ASC
            """,
            (product_type, model_name, model_name, model_name, model_name),
        )
        assets = [self._asset_compat(row) for row in rows]
        if assets:
            match_type = "exact_model" if any(asset.get("model_name") == model_name for asset in assets) else "product_type_common"
            return self._official_match_result("verified", match_type, model_name, product_type, assets)

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
        procedures = sorted({p for asset in assets for p in (asset.get("available_procedures") or [])})
        forbidden = sorted({a for asset in assets for a in (asset.get("forbidden_actions") or [])})
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

    @staticmethod
    def _asset_compat(asset: dict[str, Any]) -> dict[str, Any]:
        procedure = asset.get("procedure_type")
        return {
            **asset,
            "verification_status": "verified" if asset.get("verified_yn") == "Y" else "needs_review",
            "applicability_scope": "exact_model" if asset.get("model_name") else "product_type_common",
            "available_procedures": [procedure] if procedure else [],
            "forbidden_actions": [],
        }

    @staticmethod
    def _content_from_guide(row: dict[str, Any]) -> dict[str, Any]:
        source_chunk_ids = _load_json(row.get("source_chunk_ids"), [])
        source_asset_ids = [row["source_asset_id"]] if row.get("source_asset_id") else []
        return {
            **row,
            "content_id": _content_id_from_guide_id(row["guide_id"]),
            "content_type": row.get("guide_type") or "manual",
            "title": row.get("guide_title"),
            "procedure_type": row.get("guide_category"),
            "language": row.get("language_code"),
            "source_asset_ids": source_asset_ids,
            "source_chunk_ids": source_chunk_ids,
        }

    def find_official_contents(
        self,
        product_type: str,
        procedure_type: str,
        language: str | None = None,
        model_name: str | None = None,
    ) -> list[dict[str, Any]]:
        sql = """
            SELECT g.*, p.product_type, p.model_name, a.source_title, a.source_type AS asset_source_type
            FROM "GUIDE" g
            JOIN "PRODUCT" p ON p.product_code = g.product_code
            LEFT JOIN "OFFICIAL_ASSET" a ON a.asset_id = g.source_asset_id
            WHERE p.product_type = ?
              AND g.guide_category = ?
              AND g.guide_type = 'manual'
              AND g.is_active = 'Y'
        """
        params: list[Any] = [product_type, procedure_type]
        if language:
            sql += " AND g.language_code = ?"
            params.append(language)
        if model_name:
            sql += " AND (p.model_name = ? OR p.model_name IS NULL)"
            params.append(model_name)
        sql += " ORDER BY p.model_name DESC, g.guide_id ASC"
        return [self._content_from_guide(row) for row in self.fetch_all(sql, tuple(params))]

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
        videos = self.fetch_all(
            """
            SELECT g.*, p.product_type, p.model_name
            FROM "GUIDE" g
            JOIN "PRODUCT" p ON p.product_code = g.product_code
            WHERE p.product_type = ?
              AND g.guide_category = ?
              AND g.language_code = ?
              AND g.video_url IS NOT NULL
            """,
            (product_type, procedure_type, language),
        )
        if not videos:
            return None
        for video in videos:
            video["procedure_type"] = video.get("guide_category")
            video["reuse_decision"] = "full_reuse"
        if model_name:
            for video in videos:
                if video.get("model_name") == model_name:
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

    def find_official_youtube_recommendations(
        self,
        product_type: str,
        procedure_type: str,
        language: str | None = None,
        limit: int = 3,
    ) -> list[dict[str, Any]]:
        sql = """
            SELECT
              a.asset_id,
              a.source_title AS title,
              a.source_url,
              a.source_type,
              c.chunk_id,
              c.procedure_type,
              c.language_code AS language,
              c.chunk_text,
              c.source_section
            FROM "OFFICIAL_ASSET" a
            JOIN "OFFICIAL_DOCUMENT_CHUNK" c ON c.asset_id = a.asset_id
            WHERE a.source_type = 'official_youtube'
              AND a.product_type = ?
              AND c.procedure_type = ?
        """
        params: list[Any] = [product_type, procedure_type]
        if language:
            sql += " AND c.language_code = ?"
            params.append(language)
        sql += """
            ORDER BY
              CASE
                WHEN c.chunk_text LIKE '%Official channel: LG India%' THEN 0
                WHEN c.chunk_text LIKE '%Official channel: LG DIY Service%' THEN 1
                WHEN c.chunk_text LIKE '%Official channel: LG Global%' THEN 2
                ELSE 3
              END,
              a.asset_id ASC
            LIMIT ?
        """
        params.append(limit)
        return self.fetch_all(sql, tuple(params))


class SQLAlchemyRAGRepository(BaseRepository):
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
        sql = """
            SELECT c.*, a.product_type, a.model_name, c.language_code AS language
            FROM "OFFICIAL_DOCUMENT_CHUNK" c
            JOIN "OFFICIAL_ASSET" a ON a.asset_id = c.asset_id
            WHERE a.product_type = ?
        """
        params: list[Any] = [product_type]
        if model_name:
            sql += """
              AND (
                a.model_name = ?
                OR a.model_name IS NULL
                OR c.product_code = ?
                OR c.chunk_text LIKE ?
              )
            """
            params.extend([model_name, model_name, f"%{model_name}%"])
        if procedure_type:
            sql += " AND c.procedure_type = ?"
            params.append(procedure_type)
        if language:
            sql += " AND c.language_code = ?"
            params.append(language)
        chunks = self.fetch_all(sql, tuple(params))
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
        sql = """
            SELECT
              c.*,
              a.product_type,
              a.model_name,
              a.source_type AS source_type,
              CASE
                WHEN a.model_name IS NOT NULL THEN 'exact_model'
                ELSE 'product_type_common'
              END AS applicability_scope,
              c.language_code AS language,
              e.embedding_model,
              e.embedding_vector AS embedding_vector_json,
              NULL AS embedding_norm,
              e.created_at AS indexed_at
            FROM "OFFICIAL_DOCUMENT_CHUNK" c
            JOIN "OFFICIAL_ASSET" a ON a.asset_id = c.asset_id
            JOIN "OFFICIAL_DOCUMENT_EMBEDDING" e ON c.chunk_id = e.chunk_id
            WHERE a.product_type = ?
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
            sql += """
              AND (
                a.model_name = ?
                OR a.model_name IS NULL
                OR c.product_code = ?
                OR c.chunk_text LIKE ?
              )
            """
            params.extend([model_name, model_name, f"%{model_name}%"])
        if procedure_type and require_procedure:
            sql += " AND c.procedure_type = ?"
            params.append(procedure_type)
        if language:
            sql += " AND c.language_code = ?"
            params.append(language)
        if embedding_model:
            sql += " AND e.embedding_model = ?"
            params.append(embedding_model)
        sql += """
            ORDER BY
              CASE WHEN a.source_type = 'official_youtube' THEN 0 ELSE 1 END,
              c.chunk_id ASC
            LIMIT ?
        """
        params.append(limit)
        rows = self.fetch_all(sql, tuple(params))
        for row in rows:
            vector = _load_json(row.get("embedding_vector"), {}) or _load_json(row.get("embedding_vector_json"), {})
            row["embedding_vector"] = vector
            if isinstance(vector, list):
                row["embedding_dimension"] = len(vector)
            elif row.get("embedding_model") == "careshot_local_hashing_v1":
                row["embedding_dimension"] = 512
            elif isinstance(vector, dict) and vector:
                row["embedding_dimension"] = max(int(index) for index in vector) + 1
            else:
                row["embedding_dimension"] = 0
        return rows

    def get_embedding_stats(self) -> dict[str, Any]:
        if self.manager.engine.url.get_backend_name() == "sqlite":
            table_exists = self.fetch_one(
                """
                SELECT COUNT(*) AS count
                FROM sqlite_master
                WHERE type = 'table'
                  AND name = 'OFFICIAL_DOCUMENT_EMBEDDING'
                """
            )
        else:
            table_exists = self.fetch_one(
                """
                SELECT COUNT(*) AS count
                FROM information_schema.tables
                WHERE table_schema = 'public'
                  AND table_name = 'OFFICIAL_DOCUMENT_EMBEDDING'
                """
            )
        if not table_exists or not table_exists["count"]:
            return {"table_exists": False, "embedding_count": 0, "chunk_status_counts": {}, "model_counts": {}}
        chunk_rows = self.fetch_all(
            """
            SELECT embedding_status, COUNT(*) AS count
            FROM "OFFICIAL_DOCUMENT_CHUNK"
            GROUP BY embedding_status
            """
        )
        model_rows = self.fetch_all(
            """
            SELECT embedding_model, embedding_status, COUNT(*) AS count
            FROM "OFFICIAL_DOCUMENT_EMBEDDING"
            GROUP BY embedding_model, embedding_status
            """
        )
        return {
            "table_exists": True,
            "embedding_count": self.count("official_document_embeddings"),
            "chunk_status_counts": {(row["embedding_status"] or "null"): row["count"] for row in chunk_rows},
            "model_counts": {f"{row['embedding_model']}::{row['embedding_status']}": row["count"] for row in model_rows},
        }

    def create_rag_search_log(self, payload: dict[str, Any]) -> dict[str, Any]:
        payload = normalize_payload(payload, {"created_at": utc_now, "strict_filter": {}, "matched_chunk_ids": [], "score": {}})
        next_id_row = self.fetch_one('SELECT COALESCE(MAX(rag_log_id), 0) + 1 AS next_id FROM "RAG_SEARCH_LOG"')
        selected_asset_ids = (payload.get("strict_filter") or {}).get("official_asset_ids_priority") or []
        search_status = "no_match" if payload.get("no_match_reason") else "success"
        self.execute_write(
            """
            INSERT INTO "RAG_SEARCH_LOG" (
              rag_log_id, inquiry_id, ai_response_id, query_text,
              top_chunk_ids, selected_asset_ids, search_status, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                (next_id_row or {}).get("next_id") or 1,
                payload.get("inquiry_id"),
                payload.get("ai_response_id"),
                payload["query"],
                json_param(payload.get("matched_chunk_ids", [])),
                json_param(selected_asset_ids),
                search_status,
                payload["created_at"],
            ),
        )
        return payload


class SQLAlchemyConversationRepository(BaseRepository):
    def create_chat_session(self, payload: dict[str, Any]) -> dict[str, Any]:
        payload = normalize_payload(
            payload, {"created_at": utc_now, "updated_at": utc_now, "status": "active"}
        )
        next_id_row = self.fetch_one('SELECT COALESCE(MAX(session_id), 0) + 1 AS next_id FROM "CHAT_SESSION"')
        session_id = payload.get("session_id")
        try:
            session_id_value = int(session_id) if session_id is not None else int((next_id_row or {}).get("next_id") or 1)
        except (TypeError, ValueError):
            session_id_value = int((next_id_row or {}).get("next_id") or 1)
        self.execute_write(
            """
            INSERT INTO "CHAT_SESSION" (
              session_id, user_email, product_code, session_status, started_at, ended_at
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                session_id_value,
                _user_email_from_demo_id(payload.get("user_id") or payload.get("user_email")),
                _product_code_from_device_id(payload.get("device_id") or payload.get("product_code")),
                payload.get("session_status") or payload.get("status"),
                payload["created_at"],
                payload.get("ended_at"),
            ),
        )
        payload["session_id"] = session_id_value
        return payload

    def get_chat_session(self, session_id: str) -> dict[str, Any] | None:
        return self.fetch_one('SELECT * FROM "CHAT_SESSION" WHERE session_id = ? LIMIT 1', (session_id,))

    def add_chat_message(self, payload: dict[str, Any]) -> dict[str, Any]:
        payload = normalize_payload(payload, {"created_at": utc_now, "intent_snapshot": {}, "risk_snapshot": {}})
        next_id_row = self.fetch_one('SELECT COALESCE(MAX(message_id), 0) + 1 AS next_id FROM "CHAT_MESSAGE"')
        message_id = payload.get("message_id")
        try:
            message_id_value = int(message_id) if message_id is not None else int((next_id_row or {}).get("next_id") or 1)
        except (TypeError, ValueError):
            message_id_value = int((next_id_row or {}).get("next_id") or 1)
        sender_type = payload.get("sender_type") or payload.get("role") or "user"
        if sender_type == "assistant":
            sender_type = "ai"
        self.execute_write(
            """
            INSERT INTO "CHAT_MESSAGE" (
              message_id, session_id, sender_type, message_type, message_content, created_at
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                message_id_value,
                payload["session_id"],
                sender_type,
                payload.get("message_type") or "text",
                payload.get("message_content") or payload.get("message_text"),
                payload["created_at"],
            ),
        )
        payload["message_id"] = message_id_value
        payload["sender_type"] = sender_type
        return payload

    def get_chat_messages(self, session_id: str) -> list[dict[str, Any]]:
        return self.fetch_all(
            'SELECT * FROM "CHAT_MESSAGE" WHERE session_id = ? ORDER BY created_at ASC',
            (session_id,),
        )

    def create_chatbot_inquiry(self, payload: dict[str, Any]) -> dict[str, Any]:
        payload = normalize_payload(payload, {"created_at": utc_now})
        next_id_row = self.fetch_one('SELECT COALESCE(MAX(inquiry_id), 0) + 1 AS next_id FROM "CHATBOT_INQUIRY"')
        inquiry_id = payload.get("inquiry_id")
        try:
            inquiry_id_value = int(inquiry_id) if inquiry_id is not None else int((next_id_row or {}).get("next_id") or 1)
        except (TypeError, ValueError):
            inquiry_id_value = int((next_id_row or {}).get("next_id") or 1)
        self.execute_write(
            """
            INSERT INTO "CHATBOT_INQUIRY" (
              inquiry_id, session_id, user_email, product_code, inquiry_content, created_at
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                inquiry_id_value,
                payload["session_id"],
                _user_email_from_demo_id(payload.get("user_id") or payload.get("user_email")),
                _product_code_from_device_id(payload.get("device_id") or payload.get("product_code")),
                payload["inquiry_content"],
                payload["created_at"],
            ),
        )
        payload["inquiry_id"] = inquiry_id_value
        return payload

    def create_ai_inquiry_analysis(self, payload: dict[str, Any]) -> dict[str, Any]:
        payload = normalize_payload(payload, {"created_at": utc_now, "status_yn": "N"})
        next_id_row = self.fetch_one('SELECT COALESCE(MAX(ai_response_id), 0) + 1 AS next_id FROM "AI_INQUIRY_ANALYSIS"')
        ai_response_id = payload.get("ai_response_id")
        try:
            ai_response_id_value = (
                int(ai_response_id) if ai_response_id is not None else int((next_id_row or {}).get("next_id") or 1)
            )
        except (TypeError, ValueError):
            ai_response_id_value = int((next_id_row or {}).get("next_id") or 1)
        self.execute_write(
            """
            INSERT INTO "AI_INQUIRY_ANALYSIS" (
              ai_response_id, inquiry_id, symptom, intent_type, risk_level,
              recommended_guide_id, safety_reason, status_yn
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                ai_response_id_value,
                payload["inquiry_id"],
                payload.get("symptom"),
                payload["intent_type"],
                payload.get("risk_level"),
                payload.get("recommended_guide_id"),
                payload.get("safety_reason"),
                payload.get("status_yn") or "N",
            ),
        )
        payload["ai_response_id"] = ai_response_id_value
        return payload

    def get_conversation_state(self, session_id: str) -> dict[str, Any] | None:
        return self.fetch_one('SELECT * FROM "CONVERSATION_STATE" WHERE session_id = ? LIMIT 1', (session_id,))

    def upsert_conversation_state(self, payload: dict[str, Any]) -> dict[str, Any]:
        payload = normalize_payload(
            payload,
            {
                "updated_at": utc_now,
                "missing_slots": [],
                "collected_slots": {},
                "state_status": "collecting",
            },
        )
        current = self.get_conversation_state(payload["session_id"])
        missing_slots = payload.get("missing_slots", [])
        missing_slots_text = json_param(missing_slots) if not isinstance(missing_slots, str) else missing_slots
        collected_slots = payload.get("collected_slots", payload.get("slots", {}))
        if current:
            self.execute_write(
                """
                UPDATE "CONVERSATION_STATE"
                SET current_intent = ?, missing_slots = ?, collected_slots_json = ?,
                    next_question = ?, state_status = ?, updated_at = ?
                WHERE session_id = ?
                """,
                (
                    payload.get("current_intent"),
                    missing_slots_text,
                    json_param(collected_slots),
                    payload.get("next_question"),
                    payload.get("state_status"),
                    payload["updated_at"],
                    payload["session_id"],
                ),
            )
        else:
            next_id_row = self.fetch_one('SELECT COALESCE(MAX(state_id), 0) + 1 AS next_id FROM "CONVERSATION_STATE"')
            self.execute_write(
                """
                INSERT INTO "CONVERSATION_STATE" (
                  state_id, session_id, current_intent, missing_slots,
                  collected_slots_json, next_question, state_status, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    (next_id_row or {}).get("next_id") or 1,
                    payload["session_id"],
                    payload.get("current_intent"),
                    missing_slots_text,
                    json_param(collected_slots),
                    payload.get("next_question"),
                    payload.get("state_status"),
                    payload["updated_at"],
                ),
            )
        return self.get_conversation_state(payload["session_id"]) or payload


class SQLAlchemyARSessionRepository(BaseRepository):
    def get_ar_guide_steps(self, guide_id: str) -> list[dict[str, Any]]:
        row = self._ar_guide_row(guide_id=guide_id)
        if not row:
            return []
        cfg = _load_json(row.get("overlay_config_json"), {}) or {}
        text_steps = _split_guide_steps(row.get("guide_text"))
        action_types = cfg.get("allowed_actions") or []
        part_cycle = ["power_area", "front_cover", "front_filter", "front_filter", "air_outlet", "front_filter", "front_cover"]
        return [
            {
                "guide_step_id": f"{row['guide_id']}_STEP_{idx:02d}",
                "guide_id": cfg.get("guide_id") or str(row["guide_id"]),
                "step_order": idx,
                "product_type": cfg.get("product_type") or row.get("product_type"),
                "structure_type": cfg.get("structure_type") or row.get("structure_type"),
                "procedure_type": row.get("procedure_type"),
                "guide_type": cfg.get("guide_type") or ("preventive_care" if row.get("trigger_type") == "self_care" else "self_check"),
                "target_part": part_cycle[min(idx - 1, len(part_cycle) - 1)],
                "action_type": action_types[min(idx - 1, len(action_types) - 1)] if action_types else "highlight_and_confirm",
                "instruction_text": text,
                "safety_message": "Power off before touching user-accessible parts.",
            }
            for idx, text in enumerate(text_steps, start=1)
        ]

    def find_ar_guides(
        self,
        product_type: str,
        procedure_type: str | None = None,
        guide_type: str | None = None,
        structure_type: str | None = None,
    ) -> list[dict[str, Any]]:
        sql = """
            SELECT
              ag.ar_guide_id,
              ag.guide_id AS numeric_guide_id,
              ag.procedure_type,
              ag.overlay_config_json,
              ag.created_at,
              g.guide_text,
              g.trigger_type,
              p.product_type,
              p.structure_type
            FROM "AR_GUIDE" ag
            JOIN "GUIDE" g ON g.guide_id = ag.guide_id
            JOIN "PRODUCT" p ON p.product_code = ag.product_code
            WHERE ag.active = 'Y'
              AND p.product_type = ?
        """
        params: list[Any] = [product_type]
        if procedure_type:
            sql += " AND ag.procedure_type = ?"
            params.append(procedure_type)
        if structure_type:
            sql += " AND p.structure_type = ?"
            params.append(structure_type)
        sql += " ORDER BY ag.ar_guide_id"
        rows = []
        for row in self.fetch_all(sql, tuple(params)):
            cfg = _load_json(row.get("overlay_config_json"), {}) or {}
            cfg_guide_type = cfg.get("guide_type") or ("preventive_care" if row.get("trigger_type") == "self_care" else "self_check")
            if guide_type and cfg_guide_type != guide_type:
                continue
            rows.append(
                {
                    **row,
                    "guide_id": cfg.get("guide_id") or str(row["numeric_guide_id"]),
                    "guide_type": cfg_guide_type,
                    "step_count": len(_split_guide_steps(row.get("guide_text"))),
                }
            )
        return rows

    def get_ar_guide_template(
        self,
        template_id: str | None = None,
        guide_id: str | None = None,
        product_type: str | None = None,
        procedure_type: str | None = None,
        structure_type: str | None = None,
    ) -> dict[str, Any] | None:
        rows = self._ar_guide_rows(
            guide_id=guide_id,
            product_type=product_type,
            procedure_type=procedure_type,
            structure_type=structure_type,
        )
        for row in rows:
            cfg = _load_json(row.get("overlay_config_json"), {}) or {}
            if template_id and cfg.get("template_id") != template_id:
                continue
            return {
                **cfg,
                "template_id": cfg.get("template_id") or f"AR_GUIDE_{row['ar_guide_id']}",
                "guide_id": cfg.get("guide_id") or str(row["guide_id"]),
                "product_type": cfg.get("product_type") or row.get("product_type"),
                "structure_type": cfg.get("structure_type") or row.get("structure_type"),
                "procedure_type": row.get("procedure_type"),
                "risk_ceiling": cfg.get("risk_ceiling") or "medium",
                "source_table": "AR_GUIDE",
            }
        return None

    def _ar_guide_row(self, guide_id: str) -> dict[str, Any] | None:
        rows = self._ar_guide_rows(guide_id=guide_id)
        return rows[0] if rows else None

    def _ar_guide_rows(
        self,
        guide_id: str | None = None,
        product_type: str | None = None,
        procedure_type: str | None = None,
        structure_type: str | None = None,
    ) -> list[dict[str, Any]]:
        sql = """
            SELECT
              ag.*,
              g.guide_text,
              g.guide_title,
              g.trigger_type,
              p.product_type,
              p.model_name,
              p.structure_type
            FROM "AR_GUIDE" ag
            JOIN "GUIDE" g ON g.guide_id = ag.guide_id
            JOIN "PRODUCT" p ON p.product_code = ag.product_code
            WHERE ag.active = 'Y'
        """
        params: list[Any] = []
        if guide_id:
            sql += " AND (CAST(ag.guide_id AS TEXT) = ? OR ag.overlay_config_json LIKE ?)"
            params.extend([str(guide_id), f'%"{guide_id}"%'])
        if product_type:
            sql += " AND p.product_type = ?"
            params.append(product_type)
        if procedure_type:
            sql += " AND ag.procedure_type = ?"
            params.append(procedure_type)
        if structure_type:
            sql += " AND p.structure_type = ?"
            params.append(structure_type)
        sql += " ORDER BY ag.ar_guide_id"
        return self.fetch_all(sql, tuple(params))

    def create_ar_session_log(self, payload: dict[str, Any]) -> dict[str, Any]:
        payload = normalize_payload(
            payload,
            {
                "created_at": utc_now,
                "updated_at": utc_now,
                "completed_steps": [],
                "completed": False,
                "clicked_as": False,
                "service_flow_type": "self_care",
            },
        )
        payload["completed"] = bool(payload.get("completed"))
        payload["clicked_as"] = bool(payload.get("clicked_as"))
        _EPHEMERAL_AR_SESSIONS[payload["session_id"]] = payload
        if payload["completed"]:
            self._save_self_management_history(payload)
            payload["_history_saved"] = True
        return payload

    def get_ar_session_logs(self, user_id: str | None = None, device_id: str | None = None) -> list[dict[str, Any]]:
        sessions = list(_EPHEMERAL_AR_SESSIONS.values())
        if user_id:
            sessions = [session for session in sessions if session.get("user_id") == user_id]
        if device_id:
            sessions = [session for session in sessions if session.get("device_id") == device_id]
        return sorted(sessions, key=lambda item: item.get("updated_at") or item.get("created_at") or "", reverse=True)

    def get_ar_session_log(self, session_id: str) -> dict[str, Any] | None:
        session = _EPHEMERAL_AR_SESSIONS.get(session_id)
        return dict(session) if session else None

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
        updated_at = utc_now()
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
        current.update(
            {
                "completed_steps": next_completed_steps,
                "completed": next_completed,
                "solved": next_solved,
                "clicked_as": next_clicked_as,
                "updated_at": updated_at,
                "raw_json": raw_json,
            }
        )
        if next_completed and not current.get("_history_saved"):
            self._save_self_management_history(current)
            current["_history_saved"] = True
        _EPHEMERAL_AR_SESSIONS[session_id] = current
        return dict(current)

    def create_ar_step_log(self, payload: dict[str, Any]) -> dict[str, Any]:
        payload = normalize_payload(payload, {"created_at": utc_now})
        _EPHEMERAL_AR_STEP_LOGS.setdefault(payload["session_id"], []).append(payload)
        return payload

    def get_ar_step_logs(self, session_id: str) -> list[dict[str, Any]]:
        return sorted(_EPHEMERAL_AR_STEP_LOGS.get(session_id, []), key=lambda item: item.get("created_at") or "")

    def _save_self_management_history(self, payload: dict[str, Any]) -> None:
        next_id_row = self.fetch_one('SELECT COALESCE(MAX(history_id), 0) + 1 AS next_id FROM "SELF_MANAGEMENT_HISTORY"')
        self.execute_write(
            """
            INSERT INTO "SELF_MANAGEMENT_HISTORY" (
              history_id, product_code, user_email, management_category,
              management_type, created_at
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                (next_id_row or {}).get("next_id") or 1,
                _product_code_from_device_id(payload["device_id"]),
                _user_email_from_demo_id(payload["user_id"]),
                payload.get("procedure_type") or "ar_guide",
                payload.get("service_flow_type") or "self_care",
                payload.get("updated_at") or payload.get("completed_at") or utc_now(),
            ),
        )


class SQLAlchemyCareHistoryRepository(BaseRepository):
    def create_care_activity_log(self, payload: dict[str, Any]) -> dict[str, Any]:
        payload = normalize_payload(
            payload,
            {
                "status": "completed",
                "service_flow_type": "self_care",
                "activity_channel": "official_content",
                "progress_percent": 100,
            },
        )
        next_id_row = self.fetch_one('SELECT COALESCE(MAX(history_id), 0) + 1 AS next_id FROM "SELF_MANAGEMENT_HISTORY"')
        self.execute_write(
            """
            INSERT INTO "SELF_MANAGEMENT_HISTORY" (
              history_id, product_code, user_email, management_category,
              management_type, created_at
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                (next_id_row or {}).get("next_id") or 1,
                _product_code_from_device_id(payload["device_id"]),
                _user_email_from_demo_id(payload["user_id"]),
                payload.get("procedure_type"),
                payload["service_flow_type"],
                payload.get("completed_at") or payload.get("started_at") or utc_now(),
            ),
        )
        return payload

    def get_device_care_summary(self, user_id: str, device_id: str) -> dict[str, Any] | None:
        user_email = _user_email_from_demo_id(user_id)
        product_code = _product_code_from_device_id(device_id)
        rows = self.fetch_all(
            """
            SELECT management_type, COUNT(*) AS count, MAX(created_at) AS last_at
            FROM "SELF_MANAGEMENT_HISTORY"
            WHERE user_email = ? AND product_code = ?
            GROUP BY management_type
            """,
            (user_email, product_code),
        )
        self_care_count = sum(int(row["count"]) for row in rows if row.get("management_type") == "self_care")
        self_as_count = sum(int(row["count"]) for row in rows if row.get("management_type") == "self_as")
        total = self_care_count + self_as_count
        return {
            "summary_id": f"SUMMARY_{user_id}_{device_id}",
            "user_id": user_id,
            "device_id": device_id,
            "self_care_count": self_care_count,
            "self_as_count": self_as_count,
            "total_care_count": total,
            "care_score": min(100.0, total * 10.0),
            "last_self_care_at": next((row.get("last_at") for row in rows if row.get("management_type") == "self_care"), None),
            "last_self_as_at": next((row.get("last_at") for row in rows if row.get("management_type") == "self_as"), None),
            "updated_at": max([row.get("last_at") for row in rows if row.get("last_at")] or [None]),
        }

    def upsert_device_care_summary(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self.get_device_care_summary(payload["user_id"], payload["device_id"]) or payload

    def get_device_care_history(
        self,
        user_id: str,
        device_id: str,
        service_flow_type: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        user_email = _user_email_from_demo_id(user_id)
        product_code = _product_code_from_device_id(device_id)
        sql = """
            SELECT
              CAST(history_id AS TEXT) AS history_id,
              ? AS user_id,
              ? AS device_id,
              management_type AS service_flow_type,
              'official_content' AS activity_channel,
              management_category AS procedure_type,
              management_category AS title,
              'completed' AS status,
              created_at AS started_at,
              created_at AS completed_at,
              NULL AS source_content_view_id,
              NULL AS source_ar_session_id,
              NULL AS source_route_log_id,
              NULL AS source_expert_as_request_id,
              'SELF_MANAGEMENT_HISTORY' AS source_table,
              created_at AS sort_at,
              NULL AS step_log_count
            FROM "SELF_MANAGEMENT_HISTORY"
            WHERE user_email = ? AND product_code = ?
        """
        params: list[Any] = [user_id, device_id, user_email, product_code]
        if service_flow_type:
            sql += " AND management_type = ?"
            params.append(service_flow_type)
        sql += """
            ORDER BY sort_at DESC, history_id DESC
            LIMIT ?
        """
        params.append(limit)
        return self.fetch_all(sql, tuple(params))


class SQLAlchemyEvaluationRepository(BaseRepository):
    def get_intent_risk_test_cases(self, product_type: str | None = None) -> list[dict[str, Any]]:
        return []

    def save_intent_risk_eval_result(self, payload: dict[str, Any]) -> dict[str, Any]:
        payload = normalize_payload(payload, {"evaluated_at": utc_now})
        return payload


class SQLAlchemyDecisionRepository(BaseRepository):
    def create_safety_audit_log(self, payload: dict[str, Any]) -> dict[str, Any]:
        payload = normalize_payload(payload, {"created_at": utc_now, "reasons": [], "forbidden_actions": [], "evidence_refs": []})
        return payload

    def create_decision_log(self, payload: dict[str, Any]) -> dict[str, Any]:
        payload = normalize_payload(payload, {"created_at": utc_now, "evidence_refs": []})
        return payload

    def create_service_route_log(self, payload: dict[str, Any]) -> dict[str, Any]:
        payload = normalize_payload(payload, {"created_at": utc_now, "status": "created"})
        return payload
