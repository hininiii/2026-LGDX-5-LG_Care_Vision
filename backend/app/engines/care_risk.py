from __future__ import annotations

from typing import Any


class CareRiskScoreEngine:
    """Scores preventive care need from ThinQ usage, diagnosis, and environment context."""

    DEFAULT_THRESHOLDS = {"low": 40, "medium": 65, "high": 85}

    def evaluate(
        self,
        device: dict[str, Any],
        usage_log: dict[str, Any] | None,
        smart_diagnosis: dict[str, Any] | None,
        environment: dict[str, Any] | None,
        rules: list[dict[str, Any]] | None,
        procedure_type: str,
    ) -> dict[str, Any]:
        thresholds = self.thresholds_from_rules(rules)
        product_type = device.get("product_type")
        score = 20.0
        factors: list[dict[str, Any]] = []

        score += self.usage_score(usage_log, factors)
        score += self.environment_score(product_type, environment, factors)
        score += self.smart_diagnosis_score(smart_diagnosis, factors)

        score = min(round(score, 1), 100.0)
        risk_band = self.risk_band(score, thresholds)
        trigger_reason = [factor["reason"] for factor in factors] or [
            "강한 예방 관리 위험 요인은 확인되지 않았습니다. 현재 관리 위험도는 낮습니다."
        ]

        return {
            "care_risk_score": score,
            "risk_band": risk_band,
            "trigger_reason": trigger_reason,
            "procedure_type": procedure_type,
            "urgency": self.urgency(risk_band),
            "alert_threshold": thresholds["low"],
            "recommended_options": [
                {"option_type": "manual", "label": "View official manual", "enabled": True},
                {"option_type": "ar_guide", "label": "Start AR Guide", "enabled": True},
            ],
            "factor_scores": factors,
            "thresholds": thresholds,
        }

    def usage_score(self, usage_log: dict[str, Any] | None, factors: list[dict[str, Any]]) -> float:
        usage_summary = (usage_log or {}).get("usage_summary") or {}
        score = 0.0
        days_since_last_care = float(usage_summary.get("days_since_last_care") or 0)
        daily_runtime = float(usage_summary.get("daily_runtime_hours") or 0)
        if not daily_runtime:
            recent_used_hours = float((usage_log or {}).get("recent_used_hours") or 0)
            usage_period_days = float((usage_log or {}).get("usage_period_days") or 0)
            if recent_used_hours and usage_period_days:
                daily_runtime = recent_used_hours / usage_period_days
        if days_since_last_care:
            delta = min(days_since_last_care * 0.8, 40)
            score += delta
            factors.append(
                {
                    "factor": "days_since_last_care",
                    "value": days_since_last_care,
                    "score_delta": round(delta, 1),
                    "reason": f"마지막 관리 후 {int(days_since_last_care)}일이 지났습니다.",
                }
            )
        if daily_runtime:
            delta = min(daily_runtime * 5, 15)
            score += delta
            factors.append(
                {
                    "factor": "daily_runtime_hours",
                    "value": daily_runtime,
                    "score_delta": round(delta, 1),
                    "reason": f"최근 일평균 사용 시간은 {daily_runtime:.1f}시간입니다.",
                }
            )
        return score

    def environment_score(
        self,
        product_type: str | None,
        environment: dict[str, Any] | None,
        factors: list[dict[str, Any]],
    ) -> float:
        score = 0.0
        humidity = float((environment or {}).get("humidity_percent") or 0)
        aqi = float((environment or {}).get("aqi") or 0)
        pm25 = float((environment or {}).get("pm25") or 0)
        pm10 = float((environment or {}).get("pm10") or 0)
        water_hardness = (environment or {}).get("water_hardness_level")
        payload = (environment or {}).get("payload") or {}
        monsoon = (
            (environment or {}).get("rain_monsoon_intensity")
            or (environment or {}).get("monsoon_intensity")
            or payload.get("rain_monsoon_intensity")
            or payload.get("monsoon_intensity")
        )

        if product_type in {"air_conditioner", "washing_machine"} and humidity >= 60:
            delta = 15 if humidity < 75 else 20
            score += delta
            factors.append(
                {
                    "factor": "humidity_percent",
                    "value": humidity,
                    "score_delta": delta,
                    "reason": f"현재 습도는 {humidity:.0f}%로 높습니다.",
                }
            )
        if product_type in {"air_conditioner", "air_purifier"} and aqi >= 150:
            delta = 15 if aqi < 250 else 20
            score += delta
            factors.append(
                {
                    "factor": "aqi",
                    "value": aqi,
                    "score_delta": delta,
                    "reason": f"현재 대기질 지수(AQI)는 {aqi:.0f}로 높습니다.",
                }
            )
        if product_type == "air_purifier" and (pm25 >= 60 or pm10 >= 120):
            delta = 10
            score += delta
            factors.append(
                {
                    "factor": "particulate_matter",
                    "value": {"pm25": pm25, "pm10": pm10},
                    "score_delta": delta,
                    "reason": "PM2.5 또는 PM10이 높아 공기청정기 필터 관리가 필요합니다.",
                }
            )
        if product_type in {"washing_machine", "water_purifier"} and water_hardness == "high":
            delta = 10
            score += delta
            factors.append(
                {
                    "factor": "water_hardness_level",
                    "value": water_hardness,
                    "score_delta": delta,
                    "reason": "현재 환경의 물 경도가 높습니다.",
                }
            )
        if product_type == "air_conditioner" and monsoon in {"moderate", "heavy"}:
            delta = 10 if monsoon == "moderate" else 15
            monsoon_label = {"moderate": "보통", "heavy": "강함"}.get(str(monsoon), str(monsoon))
            score += delta
            factors.append(
                {
                    "factor": "rain_monsoon_intensity",
                    "value": monsoon,
                    "score_delta": delta,
                    "reason": f"몬순 강도가 {monsoon_label} 수준이라 에어컨 습기 관리 필요성이 높아졌습니다.",
                }
            )
        return score

    def smart_diagnosis_score(
        self,
        smart_diagnosis: dict[str, Any] | None,
        factors: list[dict[str, Any]],
    ) -> float:
        severity = (smart_diagnosis or {}).get("severity")
        delta_by_severity = {"low": 5, "medium": 15, "high": 25}
        delta = delta_by_severity.get(str(severity), 0)
        if delta:
            factors.append(
                {
                    "factor": "smart_diagnosis_severity",
                    "value": severity,
                    "score_delta": delta,
                    "reason": f"ThinQ 스마트 진단 심각도는 {severity}입니다.",
                }
            )
        return float(delta)

    def thresholds_from_rules(self, rules: list[dict[str, Any]] | None) -> dict[str, float]:
        thresholds = dict(self.DEFAULT_THRESHOLDS)
        for rule in rules or []:
            threshold = rule.get("threshold") or {}
            for key in ("low", "medium", "high"):
                if key in threshold:
                    thresholds[key] = float(threshold[key])
        return thresholds

    @staticmethod
    def risk_band(score: float, thresholds: dict[str, float]) -> str:
        if score >= thresholds["high"]:
            return "high"
        if score >= thresholds["medium"]:
            return "medium"
        return "low"

    @staticmethod
    def urgency(risk_band: str) -> str:
        return {"high": "immediate", "medium": "soon", "low": "recommended"}.get(risk_band, "recommended")


class PreventiveCareRecommendationEngine:
    """Builds alert copy and user choices from a care risk decision."""

    TITLE_MAP = {
        ("air_conditioner", "filter_cleaning"): "AC filter care recommended",
        ("washing_machine", "tub_clean"): "Washer tub clean recommended",
        ("air_purifier", "filter_cleaning"): "Air purifier filter care recommended",
        ("water_purifier", "limescale_care"): "Water purifier limescale care recommended",
    }

    def build(
        self,
        device: dict[str, Any],
        score_result: dict[str, Any],
    ) -> dict[str, Any]:
        product_type = device.get("product_type")
        procedure_type = score_result["procedure_type"]
        title = self.TITLE_MAP.get((product_type, procedure_type), "Preventive care recommended")
        return {
            "title": title,
            "message": (
                "CareShot detected preventive care need from environment data and ThinQ usage log. "
                "Choose either the official manual or AR Guide."
            ),
            "recommended_options": score_result["recommended_options"],
            "urgency": score_result["urgency"],
        }
