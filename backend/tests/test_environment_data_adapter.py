from __future__ import annotations

import shutil
from datetime import datetime, timedelta, timezone
from typing import Any

from app.adapters.environment import EnvironmentDataAdapter
from app.repositories import CareShotRepository
from app.repositories.database import DEFAULT_SQLITE_DB_PATH


class FakeProvider:
    provider_id = "ENV_PROVIDER_TEST"

    def __init__(self, should_fail: bool = False) -> None:
        self.should_fail = should_fail
        self.calls = 0

    def fetch(self, region: str, city: str | None, requested_metrics: list[str]) -> dict[str, Any]:
        self.calls += 1
        if self.should_fail:
            raise RuntimeError("external api failed")
        return {
            "provider_id": self.provider_id,
            "country": "India",
            "region": region,
            "city": city,
            "observed_at": datetime.now(timezone.utc).isoformat(),
            "temperature_c": 32.5,
            "humidity_percent": 76.0,
            "aqi": 155,
            "pm25": 61.0,
            "pm10": 122.0,
            "water_hardness_level": None,
            "payload": {"source": "fake_provider", "requested_metrics": requested_metrics},
        }


class FakeEnvironmentRepository:
    def __init__(self, cached: dict[str, Any] | None = None) -> None:
        self.cached = cached
        self.observations: list[dict[str, Any]] = []
        self.fetch_logs: list[dict[str, Any]] = []
        self.current_observation_calls: list[tuple[str, str | None]] = []
        self.context = {
            "environment_id": "ENVCTX_TEST_001",
            "country": "India",
            "region": "Gujarat",
            "city": "Ahmedabad",
            "observed_at": "2026-06-04T00:00:00+00:00",
            "temperature_c": 34.0,
            "humidity_percent": 70.0,
            "aqi": 180,
            "water_hardness_level": "high",
            "care_triggers": ["filter_cleaning"],
            "source": "fallback_cache",
        }

    def get_current_environment_observation(self, region: str, city: str | None = None) -> dict[str, Any] | None:
        self.current_observation_calls.append((region, city))
        return self.cached

    def get_environment_context(self, region: str, city: str | None = None) -> dict[str, Any] | None:
        return self.context

    def create_environment_observation(self, payload: dict[str, Any]) -> dict[str, Any]:
        self.observations.append(payload)
        return payload

    def create_environment_fetch_log(self, payload: dict[str, Any]) -> dict[str, Any]:
        self.fetch_logs.append(payload)
        return payload


def test_environment_adapter_uses_fresh_cache_without_external_call() -> None:
    cached = {
        "observation_id": "ENVOBS_CACHE",
        "provider_id": "ENV_PROVIDER_CACHE",
        "region": "Gujarat",
        "city": "Ahmedabad",
        "observed_at": datetime.now(timezone.utc).isoformat(),
        "humidity_percent": 72.0,
        "water_hardness_level": "medium",
    }
    repo = FakeEnvironmentRepository(cached=cached)
    provider = FakeProvider()
    adapter = EnvironmentDataAdapter(repo, provider, providers={"ENV_PROVIDER_OPENWEATHER": provider})

    result = adapter.get_environment(
        user_id="U001",
        region="Gujarat",
        city="Ahmedabad",
        product_type="air_conditioner",
        cache_ttl_minutes=180,
    )

    assert result["mode"] == "cache_hit"
    assert result["observation"]["observation_id"] == "ENVOBS_CACHE"
    assert provider.calls == 0
    assert repo.fetch_logs == []
    assert repo.observations == []


def test_environment_adapter_refreshes_external_api_and_persists_observation() -> None:
    repo = FakeEnvironmentRepository()
    provider = FakeProvider()
    adapter = EnvironmentDataAdapter(repo, provider, providers={"ENV_PROVIDER_OPENWEATHER": provider})

    result = adapter.get_environment(
        user_id="U001",
        region="Gujarat",
        city="Ahmedabad",
        product_type="air_conditioner",
        provider_id="ENV_PROVIDER_OPENWEATHER",
        force_refresh=True,
    )

    assert result["mode"] == "external_api_refresh"
    assert provider.calls == 1
    assert len(repo.observations) == 1
    assert repo.observations[0]["water_hardness_level"] == "high"
    assert repo.observations[0]["payload"]["fallback_water_hardness_source"] == "ENVCTX_TEST_001"
    assert len(repo.fetch_logs) == 1
    assert repo.fetch_logs[0]["status"] == "success_external_api"
    assert repo.fetch_logs[0]["provider_id"] == "ENV_PROVIDER_OPENWEATHER"
    assert repo.observations[0]["payload"]["water_hardness_provider_id"] == "ENV_PROVIDER_WATER_HARDNESS_CONTEXT"


def test_environment_adapter_normalizes_new_delhi_alias_before_cache_and_persist() -> None:
    repo = FakeEnvironmentRepository()
    provider = FakeProvider()
    adapter = EnvironmentDataAdapter(repo, provider, providers={"ENV_PROVIDER_OPENMETEO": provider})

    result = adapter.get_environment(
        user_id="U001",
        region="Delhi",
        city="New Delhi",
        product_type="air_conditioner",
        provider_id="ENV_PROVIDER_OPENMETEO",
        force_refresh=True,
    )

    assert repo.current_observation_calls == [("Delhi", "Delhi")]
    assert result["normalized_location"] == {
        "requested_region": "Delhi",
        "requested_city": "New Delhi",
        "region": "Delhi",
        "city": "Delhi",
    }
    assert provider.calls == 1
    assert repo.observations[0]["region"] == "Delhi"
    assert repo.observations[0]["city"] == "Delhi"


def test_openweather_provider_without_api_key_uses_fallback_cache(monkeypatch) -> None:
    monkeypatch.delenv("OPENWEATHER_API_KEY", raising=False)
    repo = FakeEnvironmentRepository()
    adapter = EnvironmentDataAdapter(repo)

    result = adapter.get_environment(
        user_id="U001",
        region="Gujarat",
        city="Ahmedabad",
        product_type="air_conditioner",
        provider_id="ENV_PROVIDER_OPENWEATHER",
        force_refresh=True,
    )

    assert result["mode"] == "fallback_cache"
    assert "Missing API key" in result["error"]
    assert repo.fetch_logs[0]["provider_id"] == "ENV_PROVIDER_OPENWEATHER"
    assert repo.fetch_logs[0]["status"] == "failed_external_api_used_fallback_cache"


def test_environment_adapter_uses_fallback_cache_when_external_api_fails() -> None:
    stale = {
        "observation_id": "ENVOBS_STALE",
        "provider_id": "ENV_PROVIDER_CACHE",
        "region": "Gujarat",
        "city": "Ahmedabad",
        "observed_at": (datetime.now(timezone.utc) - timedelta(days=1)).isoformat(),
    }
    repo = FakeEnvironmentRepository(cached=stale)
    provider = FakeProvider(should_fail=True)
    adapter = EnvironmentDataAdapter(repo, provider)

    result = adapter.get_environment(
        user_id="U001",
        region="Gujarat",
        city="Ahmedabad",
        product_type="air_conditioner",
        force_refresh=False,
        cache_ttl_minutes=10,
    )

    assert result["mode"] == "fallback_cache"
    assert result["observation"]["provider_id"] == "fallback_cache"
    assert result["observation"]["water_hardness_level"] == "high"
    assert provider.calls == 1
    assert repo.observations == []
    assert len(repo.fetch_logs) == 1
    assert repo.fetch_logs[0]["status"] == "failed_external_api_used_fallback_cache"


def test_environment_adapter_selects_registered_provider_by_id() -> None:
    repo = FakeEnvironmentRepository()
    selected_provider = FakeProvider()
    default_provider = FakeProvider()
    adapter = EnvironmentDataAdapter(
        repo,
        default_provider,
        providers={"ENV_PROVIDER_OPENWEATHER": selected_provider},
    )

    result = adapter.get_environment(
        user_id="U001",
        region="Gujarat",
        city="Ahmedabad",
        product_type="air_conditioner",
        provider_id="ENV_PROVIDER_OPENWEATHER",
        force_refresh=True,
    )

    assert result["mode"] == "external_api_refresh"
    assert selected_provider.calls == 1
    assert default_provider.calls == 0


def test_environment_adapter_forced_failure_exercises_live_fallback_path() -> None:
    repo = FakeEnvironmentRepository()
    default_provider = FakeProvider()
    failing_provider = FakeProvider(should_fail=True)
    adapter = EnvironmentDataAdapter(
        repo,
        default_provider,
        providers={"ENV_PROVIDER_FORCE_FAIL": failing_provider},
    )

    result = adapter.get_environment(
        user_id="U001",
        region="Gujarat",
        city="Ahmedabad",
        product_type="air_conditioner",
        provider_id="ENV_PROVIDER_FORCE_FAIL",
        force_refresh=True,
    )

    assert result["mode"] == "fallback_cache"
    assert failing_provider.calls == 1
    assert default_provider.calls == 0
    assert repo.fetch_logs[0]["provider_id"] == "ENV_PROVIDER_FORCE_FAIL"


def test_sqlite_environment_observation_insert_matches_final_21_table_shape(tmp_path) -> None:
    test_db = tmp_path / "careshot_ar_mock.db"
    shutil.copy2(DEFAULT_SQLITE_DB_PATH, test_db)
    repo = CareShotRepository(test_db)
    observed_at = (datetime.now(timezone.utc) + timedelta(minutes=5)).isoformat()

    observation = repo.create_environment_observation(
        {
            "region": "Gujarat",
            "city": "Ahmedabad",
            "observed_at": observed_at,
            "temperature_c": 31.2,
            "humidity_percent": 68,
            "aqi": 88,
            "pm25": 22.5,
            "pm10": 41.0,
            "rain_monsoon_intensity": "moderate",
            "provider_id": "ENV_PROVIDER_OPENMETEO",
        }
    )

    assert isinstance(observation["observation_id"], int)
    assert observation["region_id"] == "INDIA_GUJARAT_AHMEDABAD"

    row = repo.get_current_environment_observation("Gujarat", "Ahmedabad")
    assert row["observation_id"] == observation["observation_id"]
    assert row["temperature_c"] == 31.2
    assert row["humidity_percent"] == 68
    assert row["provider"] == "ENV_PROVIDER_OPENMETEO"
