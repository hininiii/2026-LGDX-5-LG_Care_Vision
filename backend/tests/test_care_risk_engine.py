from __future__ import annotations

from fastapi.testclient import TestClient

from app.engines import CareRiskScoreEngine, PreventiveCareRecommendationEngine
from app.main import app


def test_care_risk_score_engine_combines_usage_environment_and_diagnosis() -> None:
    engine = CareRiskScoreEngine()

    result = engine.evaluate(
        device={"device_id": "D001", "product_type": "air_conditioner"},
        usage_log={"usage_summary": {"days_since_last_care": 45, "daily_runtime_hours": 3}},
        smart_diagnosis={"severity": "low"},
        environment={
            "humidity_percent": 78,
            "aqi": 180,
            "pm25": 65,
            "pm10": 130,
            "water_hardness_level": "medium",
            "payload": {"rain_monsoon_intensity": "moderate"},
        },
        rules=[
            {
                "threshold": {
                    "low": 40,
                    "medium": 65,
                    "high": 85,
                }
            }
        ],
        procedure_type="filter_cleaning",
    )

    assert result["procedure_type"] == "filter_cleaning"
    assert result["care_risk_score"] >= 85
    assert result["risk_band"] == "high"
    assert result["urgency"] == "immediate"
    assert any("습도" in reason for reason in result["trigger_reason"])
    assert {option["option_type"] for option in result["recommended_options"]} == {"manual", "ar_guide"}


def test_care_risk_score_engine_reads_flat_usage_log_fields() -> None:
    engine = CareRiskScoreEngine()

    result = engine.evaluate(
        device={"product_type": "air_conditioner"},
        usage_log={"usage_period_days": 7, "recent_used_hours": 14},
        smart_diagnosis={"severity": "none"},
        environment={"humidity_percent": 38, "aqi": 72},
        rules=[],
        procedure_type="filter_cleaning",
    )

    assert result["care_risk_score"] == 30.0
    assert any(factor["factor"] == "daily_runtime_hours" for factor in result["factor_scores"])
    assert any("최근 일평균 사용 시간" in reason for reason in result["trigger_reason"])


def test_care_risk_score_engine_reads_cached_environment_monsoon_field() -> None:
    result = CareRiskScoreEngine().evaluate(
        device={"product_type": "air_conditioner"},
        usage_log={"usage_period_days": 7, "recent_used_hours": 42},
        smart_diagnosis={"severity": "none"},
        environment={
            "humidity_percent": 71,
            "aqi": 154,
            "monsoon_intensity": "moderate",
        },
        rules=[],
        procedure_type="filter_cleaning",
    )

    assert result["care_risk_score"] == 75.0
    assert result["trigger_reason"][0] == "최근 일평균 사용 시간은 6.0시간입니다."
    assert result["trigger_reason"][1] == "현재 습도는 71%로 높습니다."
    assert result["trigger_reason"][2] == "현재 대기질 지수(AQI)는 154로 높습니다."
    assert result["trigger_reason"][3] == "몬순 강도가 보통 수준이라 에어컨 습기 관리 필요성이 높아졌습니다."


def test_preventive_recommendation_engine_builds_manual_and_ar_options() -> None:
    score_result = {
        "procedure_type": "filter_cleaning",
        "urgency": "soon",
        "recommended_options": [
            {"option_type": "manual", "label": "View official manual", "enabled": True},
            {"option_type": "ar_guide", "label": "Start AR Guide", "enabled": True},
        ],
    }

    result = PreventiveCareRecommendationEngine().build(
        device={"product_type": "air_conditioner"},
        score_result=score_result,
    )

    assert result["title"] == "AC filter care recommended"
    assert result["urgency"] == "soon"
    assert {option["option_type"] for option in result["recommended_options"]} == {"manual", "ar_guide"}


def test_care_risk_evaluate_api_uses_final_21_table_structure_without_rule_table() -> None:
    response = TestClient(app).post(
        "/api/v1/care/risk/evaluate",
        json={"user_id": "U001", "device_id": "D001"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["care_risk_score"]["stored"] is False
    assert payload["environment_observation"]["humidity_percent"] >= 60
    assert payload["environment_observation"]["aqi"] >= 150
    assert payload["environment_observation"]["monsoon_intensity"] == "moderate"
    trigger_reason = payload["care_risk_score"]["trigger_reason"]
    assert trigger_reason[0] == "최근 일평균 사용 시간은 6.0시간입니다."
    assert any("습도" in reason for reason in trigger_reason[1:])
    assert any("AQI" in reason for reason in trigger_reason[1:])
    assert any("몬순" in reason for reason in trigger_reason[1:])
    assert payload["care_risk_decision"]["thresholds"] == {"low": 40, "medium": 65, "high": 85}
    if payload["guide_options"] is not None:
        assert payload["guide_options"]["storage_policy"]["completion_saved_table"] == "SELF_MANAGEMENT_HISTORY"
