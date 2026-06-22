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
    assert any("humidity" in reason for reason in result["trigger_reason"])
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
    assert any("average daily runtime" in reason for reason in result["trigger_reason"])


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

    assert result["care_risk_score"] == 80.0
    assert result["trigger_reason"][0] == "Recent average daily runtime is 6.0 hours."
    assert result["trigger_reason"][1] == "Current humidity is 71%, which is high."
    assert result["trigger_reason"][2] == "Current AQI is 154, which is high."
    assert result["trigger_reason"][3] == "Monsoon intensity is moderate, increasing the need for AC moisture care."


def test_care_risk_score_engine_weights_poor_aqi_stronger_for_air_conditioner() -> None:
    result = CareRiskScoreEngine().evaluate(
        device={"product_type": "air_conditioner"},
        usage_log={"usage_period_days": 7, "recent_used_hours": 42},
        smart_diagnosis={"severity": "none"},
        environment={"humidity_percent": 40, "aqi": 223},
        rules=[],
        procedure_type="filter_cleaning",
    )

    assert result["care_risk_score"] == 65.0
    assert result["risk_band"] == "medium"
    assert result["factor_scores"][0]["score_delta"] == 15
    assert result["factor_scores"][1]["factor"] == "aqi"
    assert result["factor_scores"][1]["score_delta"] == 30
    assert result["trigger_reason"][1] == "Current AQI is 223, which is high."


def test_care_risk_score_engine_weights_extreme_aqi_for_air_conditioner() -> None:
    result = CareRiskScoreEngine().evaluate(
        device={"product_type": "air_conditioner"},
        usage_log={"usage_period_days": 7, "recent_used_hours": 42},
        smart_diagnosis={"severity": "none"},
        environment={"humidity_percent": 38, "aqi": 576},
        rules=[],
        procedure_type="filter_cleaning",
    )

    assert result["care_risk_score"] == 80.0
    assert result["factor_scores"][1]["factor"] == "aqi"
    assert result["factor_scores"][1]["score_delta"] == 45
    assert result["trigger_reason"][1] == "Current AQI is 576, which is high."


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
    assert payload["environment_observation"]["humidity_percent"] is not None
    assert payload["environment_observation"]["aqi"] is not None
    trigger_reason = payload["care_risk_score"]["trigger_reason"]
    assert trigger_reason[0] == "Recent average daily runtime is 6.0 hours."
    observation = payload["environment_observation"]
    if observation["humidity_percent"] >= 60:
        assert any("humidity" in reason for reason in trigger_reason[1:])
    if observation["aqi"] >= 100:
        assert any("AQI" in reason for reason in trigger_reason[1:])
    if observation.get("monsoon_intensity") in {"moderate", "heavy"}:
        assert any("Monsoon" in reason for reason in trigger_reason[1:])
    assert payload["care_risk_decision"]["thresholds"] == {"low": 40, "medium": 65, "high": 85}
    if payload["guide_options"] is not None:
        assert payload["guide_options"]["storage_policy"]["completion_saved_table"] == "SELF_MANAGEMENT_HISTORY"
