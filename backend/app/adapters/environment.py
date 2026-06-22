from __future__ import annotations

import json
import os
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from typing import Any, Protocol
from uuid import uuid4


class EnvironmentProvider(Protocol):
    provider_id: str

    def fetch(self, region: str, city: str | None, requested_metrics: list[str]) -> dict[str, Any]:
        ...


class EnvironmentProviderError(RuntimeError):
    pass


class MissingAPIKeyError(EnvironmentProviderError):
    pass


CITY_ALIASES: dict[tuple[str, str], tuple[str, str]] = {
    ("delhi", "new delhi"): ("Delhi", "Delhi"),
    ("delhi", "뉴델리"): ("Delhi", "Delhi"),
}


def normalize_region_city(region: str, city: str | None) -> tuple[str, str | None]:
    normalized_region = (region or "").strip()
    normalized_city = city.strip() if isinstance(city, str) else city
    alias_key = (normalized_region.lower(), (normalized_city or "").lower())
    if alias_key in CITY_ALIASES:
        return CITY_ALIASES[alias_key]
    return normalized_region, normalized_city


class APIKeyManager:
    ENV_BY_PROVIDER = {
        "ENV_PROVIDER_OPENWEATHER": "OPENWEATHER_API_KEY",
        "ENV_PROVIDER_WAQI": "WAQI_API_KEY",
        "ENV_PROVIDER_OPENMETEO": "OPENMETEO_API_KEY",
    }

    def get(self, provider_id: str) -> str | None:
        env_name = self.ENV_BY_PROVIDER.get(provider_id)
        return os.environ.get(env_name or "") if env_name else None

    def require(self, provider_id: str) -> str:
        key = self.get(provider_id)
        if not key:
            env_name = self.ENV_BY_PROVIDER.get(provider_id, f"{provider_id}_API_KEY")
            raise MissingAPIKeyError(f"Missing API key for {provider_id}. Set {env_name}.")
        return key


class OpenMeteoEnvironmentProvider:
    provider_id = "ENV_PROVIDER_OPENMETEO"

    def __init__(self, timeout_sec: int = 10) -> None:
        self.timeout_sec = timeout_sec
        self.api_key = os.environ.get("OPENMETEO_API_KEY")

    def fetch(self, region: str, city: str | None, requested_metrics: list[str]) -> dict[str, Any]:
        location_name = city or region
        latitude, longitude, resolved_name = self.geocode(location_name)
        weather = self.fetch_weather(latitude, longitude, requested_metrics)
        air = self.fetch_air_quality(latitude, longitude, requested_metrics)
        rain_value = weather.get("rain") or weather.get("precipitation") or 0.0
        monsoon_intensity = self.monsoon_intensity(float(rain_value))
        return {
            "provider_id": self.provider_id,
            "country": "India",
            "region": region,
            "city": city or resolved_name,
            "observed_at": datetime.now(timezone.utc).isoformat(),
            "temperature_c": weather.get("temperature_2m"),
            "humidity_percent": weather.get("relative_humidity_2m"),
            "aqi": air.get("us_aqi"),
            "pm25": air.get("pm2_5"),
            "pm10": air.get("pm10"),
            "rain_monsoon_intensity": monsoon_intensity,
            "water_hardness_level": None,
            "payload": {
                "source": "open_meteo_weather_and_air_quality",
                "requested_metrics": requested_metrics,
                "latitude": latitude,
                "longitude": longitude,
                "resolved_name": resolved_name,
                "weather": weather,
                "air_quality": air,
                "rain_monsoon_intensity": monsoon_intensity,
            },
        }

    def geocode(self, name: str) -> tuple[float, float, str]:
        params = urllib.parse.urlencode({"name": name, "count": 1, "language": "en", "format": "json"})
        url = f"https://geocoding-api.open-meteo.com/v1/search?{params}"
        data = self.get_json(url)
        results = data.get("results") or []
        if not results:
            raise ValueError(f"Open-Meteo geocoding returned no result for {name}")
        first = results[0]
        return float(first["latitude"]), float(first["longitude"]), first.get("name") or name

    def fetch_weather(self, latitude: float, longitude: float, requested_metrics: list[str]) -> dict[str, Any]:
        weather_metrics = self.weather_current_fields(requested_metrics)
        if not weather_metrics:
            return {}
        params = urllib.parse.urlencode(
            {
                "latitude": latitude,
                "longitude": longitude,
                "current": ",".join(weather_metrics),
                "timezone": "auto",
            }
        )
        url = f"https://api.open-meteo.com/v1/forecast?{params}"
        data = self.get_json(url)
        return data.get("current") or {}

    def fetch_air_quality(self, latitude: float, longitude: float, requested_metrics: list[str]) -> dict[str, Any]:
        air_metrics = self.air_current_fields(requested_metrics)
        if not air_metrics:
            return {}
        params = urllib.parse.urlencode(
            {
                "latitude": latitude,
                "longitude": longitude,
                "current": ",".join(air_metrics),
                "timezone": "auto",
            }
        )
        url = f"https://air-quality-api.open-meteo.com/v1/air-quality?{params}"
        data = self.get_json(url)
        return data.get("current") or {}

    def get_json(self, url: str) -> dict[str, Any]:
        request = urllib.request.Request(url, headers={"User-Agent": "CareShotARGuideEngine/0.3"})
        with urllib.request.urlopen(request, timeout=self.timeout_sec) as response:
            return json.loads(response.read().decode("utf-8"))

    @staticmethod
    def weather_current_fields(requested_metrics: list[str]) -> list[str]:
        fields: list[str] = []
        metric_set = set(requested_metrics)
        if "temperature" in metric_set:
            fields.append("temperature_2m")
        if "humidity" in metric_set:
            fields.append("relative_humidity_2m")
        if "rain_monsoon_intensity" in metric_set:
            fields.extend(["rain", "precipitation", "weather_code"])
        return fields

    @staticmethod
    def air_current_fields(requested_metrics: list[str]) -> list[str]:
        fields: list[str] = []
        metric_set = set(requested_metrics)
        if "pm10" in metric_set:
            fields.append("pm10")
        if "pm25" in metric_set:
            fields.append("pm2_5")
        if "aqi" in metric_set:
            fields.append("us_aqi")
        return fields

    @staticmethod
    def monsoon_intensity(rain_mm: float) -> str:
        if rain_mm >= 20:
            return "heavy"
        if rain_mm >= 5:
            return "moderate"
        if rain_mm > 0:
            return "light"
        return "none"


class OpenWeatherEnvironmentProvider:
    provider_id = "ENV_PROVIDER_OPENWEATHER"

    def __init__(self, key_manager: APIKeyManager | None = None, timeout_sec: int = 10) -> None:
        self.key_manager = key_manager or APIKeyManager()
        self.timeout_sec = timeout_sec

    def fetch(self, region: str, city: str | None, requested_metrics: list[str]) -> dict[str, Any]:
        api_key = self.key_manager.require(self.provider_id)
        latitude, longitude, resolved_name = self.geocode(city or region, api_key)
        weather = self.fetch_weather(latitude, longitude, api_key, requested_metrics)
        air = self.fetch_air_quality(latitude, longitude, api_key, requested_metrics)
        rain_value = (weather.get("rain") or {}).get("1h") or (weather.get("rain") or {}).get("3h") or 0.0
        return {
            "provider_id": self.provider_id,
            "country": "India",
            "region": region,
            "city": city or resolved_name,
            "observed_at": datetime.now(timezone.utc).isoformat(),
            "temperature_c": (weather.get("main") or {}).get("temp"),
            "humidity_percent": (weather.get("main") or {}).get("humidity"),
            "aqi": self.openweather_aqi((air.get("list") or [{}])[0].get("main", {}).get("aqi")),
            "pm25": ((air.get("list") or [{}])[0].get("components") or {}).get("pm2_5"),
            "pm10": ((air.get("list") or [{}])[0].get("components") or {}).get("pm10"),
            "rain_monsoon_intensity": OpenMeteoEnvironmentProvider.monsoon_intensity(float(rain_value)),
            "water_hardness_level": None,
            "payload": {
                "source": "openweather_weather_and_air_pollution",
                "requested_metrics": requested_metrics,
                "latitude": latitude,
                "longitude": longitude,
                "resolved_name": resolved_name,
                "weather": weather,
                "air_quality": air,
            },
        }

    def geocode(self, name: str, api_key: str) -> tuple[float, float, str]:
        params = urllib.parse.urlencode({"q": f"{name},IN", "limit": 1, "appid": api_key})
        data = self.get_json(f"https://api.openweathermap.org/geo/1.0/direct?{params}")
        if not data:
            raise EnvironmentProviderError(f"OpenWeather geocoding returned no result for {name}")
        first = data[0]
        return float(first["lat"]), float(first["lon"]), first.get("name") or name

    def fetch_weather(self, latitude: float, longitude: float, api_key: str, requested_metrics: list[str]) -> dict[str, Any]:
        if not any(metric in requested_metrics for metric in ["temperature", "humidity", "rain_monsoon_intensity"]):
            return {}
        params = urllib.parse.urlencode({"lat": latitude, "lon": longitude, "appid": api_key, "units": "metric"})
        return self.get_json(f"https://api.openweathermap.org/data/2.5/weather?{params}")

    def fetch_air_quality(self, latitude: float, longitude: float, api_key: str, requested_metrics: list[str]) -> dict[str, Any]:
        if not any(metric in requested_metrics for metric in ["aqi", "pm25", "pm10"]):
            return {}
        params = urllib.parse.urlencode({"lat": latitude, "lon": longitude, "appid": api_key})
        return self.get_json(f"https://api.openweathermap.org/data/2.5/air_pollution?{params}")

    def get_json(self, url: str) -> Any:
        request = urllib.request.Request(url, headers={"User-Agent": "CareShotARGuideEngine/0.3"})
        with urllib.request.urlopen(request, timeout=self.timeout_sec) as response:
            return json.loads(response.read().decode("utf-8"))

    @staticmethod
    def openweather_aqi(value: int | None) -> int | None:
        if value is None:
            return None
        # OpenWeather uses 1-5 categories. Convert to a rough US-AQI band center.
        return {1: 25, 2: 75, 3: 125, 4: 175, 5: 250}.get(int(value))


class WAQIEnvironmentProvider:
    provider_id = "ENV_PROVIDER_WAQI"

    def __init__(self, key_manager: APIKeyManager | None = None, timeout_sec: int = 10) -> None:
        self.key_manager = key_manager or APIKeyManager()
        self.timeout_sec = timeout_sec

    def fetch(self, region: str, city: str | None, requested_metrics: list[str]) -> dict[str, Any]:
        api_key = self.key_manager.require(self.provider_id)
        location_name = city or region
        params = urllib.parse.urlencode({"token": api_key})
        data = self.get_json(f"https://api.waqi.info/feed/{urllib.parse.quote(location_name)}/?{params}")
        if data.get("status") != "ok":
            raise EnvironmentProviderError(f"WAQI returned status={data.get('status')} for {location_name}")
        payload = data.get("data") or {}
        iaqi = payload.get("iaqi") or {}
        return {
            "provider_id": self.provider_id,
            "country": "India",
            "region": region,
            "city": city or payload.get("city", {}).get("name") or location_name,
            "observed_at": datetime.now(timezone.utc).isoformat(),
            "temperature_c": None,
            "humidity_percent": None,
            "aqi": payload.get("aqi") if "aqi" in requested_metrics else None,
            "pm25": (iaqi.get("pm25") or {}).get("v") if "pm25" in requested_metrics else None,
            "pm10": (iaqi.get("pm10") or {}).get("v") if "pm10" in requested_metrics else None,
            "rain_monsoon_intensity": None,
            "water_hardness_level": None,
            "payload": {
                "source": "waqi_air_quality",
                "requested_metrics": requested_metrics,
                "raw_city": payload.get("city"),
                "iaqi": iaqi,
            },
        }

    def get_json(self, url: str) -> dict[str, Any]:
        request = urllib.request.Request(url, headers={"User-Agent": "CareShotARGuideEngine/0.3"})
        with urllib.request.urlopen(request, timeout=self.timeout_sec) as response:
            return json.loads(response.read().decode("utf-8"))


class ForcedFailureEnvironmentProvider:
    provider_id = "ENV_PROVIDER_FORCE_FAIL"

    def fetch(self, region: str, city: str | None, requested_metrics: list[str]) -> dict[str, Any]:
        raise EnvironmentProviderError("Forced provider failure for fallback integration verification.")


class EnvironmentDataAdapter:
    WATER_HARDNESS_PROVIDER_ID = "ENV_PROVIDER_WATER_HARDNESS_CONTEXT"

    def __init__(
        self,
        repo: Any,
        provider: EnvironmentProvider | None = None,
        providers: dict[str, EnvironmentProvider] | None = None,
    ) -> None:
        self.repo = repo
        self.provider = provider or OpenMeteoEnvironmentProvider()
        self.providers = providers or {
            self.provider.provider_id: self.provider,
            "ENV_PROVIDER_OPENWEATHER": OpenWeatherEnvironmentProvider(),
            "ENV_PROVIDER_WAQI": WAQIEnvironmentProvider(),
            "ENV_PROVIDER_FORCE_FAIL": ForcedFailureEnvironmentProvider(),
        }

    def get_environment(
        self,
        user_id: str | None,
        region: str,
        city: str | None,
        product_type: str | None,
        requested_metrics: list[str] | None = None,
        provider_id: str | None = None,
        force_refresh: bool = False,
        cache_ttl_minutes: int = 60,
    ) -> dict[str, Any]:
        requested_region = region
        requested_city = city
        region, city = normalize_region_city(region, city)
        metrics = requested_metrics or [
            "temperature",
            "humidity",
            "aqi",
            "pm25",
            "pm10",
            "rain_monsoon_intensity",
            "water_hardness",
        ]
        cached = self.repo.get_current_environment_observation(region=region, city=city)
        if cached and not force_refresh and self.is_fresh(cached.get("observed_at"), cache_ttl_minutes):
            return {
                "mode": "cache_hit",
                "provider": cached.get("provider_id"),
                "cache_ttl_minutes": cache_ttl_minutes,
                "observation": self.with_fallback_water_hardness(cached, region, city),
                "fetch_log": None,
                "normalized_location": {
                    "requested_region": requested_region,
                    "requested_city": requested_city,
                    "region": region,
                    "city": city,
                },
            }

        runtime_provider = self.select_provider(provider_id)
        try:
            fetched = runtime_provider.fetch(region=region, city=city, requested_metrics=metrics)
            if provider_id:
                fetched["requested_provider_id"] = provider_id
            observation = self.persist_observation(fetched, region=region, city=city)
            log = self.repo.create_environment_fetch_log(
                {
                    "fetch_log_id": f"ENVFETCH_{uuid4().hex[:12].upper()}",
                    "provider_id": provider_id or fetched["provider_id"],
                    "request_region": region,
                    "request_city": city,
                    "status": "success_external_api",
                    "response_summary": {
                        "mode": "external_api_refresh",
                        "user_id": user_id,
                        "product_type": product_type,
                        "requested_metrics": metrics,
                        "runtime_provider_id": runtime_provider.provider_id,
                        "observation_id": observation["observation_id"],
                        "requested_region": requested_region,
                        "requested_city": requested_city,
                    },
                }
            )
            return {
                "mode": "external_api_refresh",
                "provider": runtime_provider.provider_id,
                "requested_provider": provider_id,
                "cache_ttl_minutes": cache_ttl_minutes,
                "observation": observation,
                "fetch_log": log,
                "normalized_location": {
                    "requested_region": requested_region,
                    "requested_city": requested_city,
                    "region": region,
                    "city": city,
                },
            }
        except Exception as exc:
            fallback = self.fallback_observation(region=region, city=city)
            log = self.repo.create_environment_fetch_log(
                {
                    "fetch_log_id": f"ENVFETCH_{uuid4().hex[:12].upper()}",
                    "provider_id": provider_id or runtime_provider.provider_id,
                    "request_region": region,
                    "request_city": city,
                    "status": "failed_external_api_used_fallback_cache",
                    "error_message": str(exc),
                    "response_summary": {
                        "mode": "fallback_cache",
                        "user_id": user_id,
                        "product_type": product_type,
                        "requested_metrics": metrics,
                        "runtime_provider_id": runtime_provider.provider_id,
                        "requested_region": requested_region,
                        "requested_city": requested_city,
                    },
                }
            )
            return {
                "mode": "fallback_cache",
                "provider": fallback.get("provider_id") or "environment_contexts",
                "cache_ttl_minutes": cache_ttl_minutes,
                "observation": fallback,
                "fetch_log": log,
                "error": str(exc),
                "normalized_location": {
                    "requested_region": requested_region,
                    "requested_city": requested_city,
                    "region": region,
                    "city": city,
                },
            }

    def select_provider(self, provider_id: str | None) -> EnvironmentProvider:
        if provider_id and provider_id in self.providers:
            return self.providers[provider_id]
        return self.provider

    def persist_observation(self, fetched: dict[str, Any], region: str, city: str | None) -> dict[str, Any]:
        fallback = self.repo.get_environment_context(region=region, city=city)
        water_hardness = fetched.get("water_hardness_level") or (fallback or {}).get("water_hardness_level")
        payload = dict(fetched.get("payload") or {})
        if fetched.get("requested_provider_id"):
            payload["requested_provider_id"] = fetched["requested_provider_id"]
        if not fetched.get("water_hardness_level") and water_hardness:
            payload["water_hardness_provider_id"] = self.WATER_HARDNESS_PROVIDER_ID
            payload["fallback_water_hardness_source"] = (fallback or {}).get("environment_id")
        return self.repo.create_environment_observation(
            {
                "observation_id": f"ENVOBS_{uuid4().hex[:12].upper()}",
                "provider_id": fetched["provider_id"],
                "country": fetched.get("country") or "India",
                "region": region,
                "city": city or fetched.get("city"),
                "observed_at": fetched.get("observed_at") or datetime.now(timezone.utc).isoformat(),
                "temperature_c": fetched.get("temperature_c"),
                "humidity_percent": fetched.get("humidity_percent"),
                "aqi": fetched.get("aqi"),
                "pm25": fetched.get("pm25"),
                "pm10": fetched.get("pm10"),
                "water_hardness_level": water_hardness,
                "payload": payload,
            }
        )

    def fallback_observation(self, region: str, city: str | None) -> dict[str, Any]:
        fallback = self.repo.get_environment_context(region=region, city=city) or {}
        return {
            "observation_id": None,
            "provider_id": fallback.get("source") or "environment_contexts",
            "country": fallback.get("country") or "India",
            "region": region,
            "city": city,
            "observed_at": fallback.get("observed_at"),
            "temperature_c": fallback.get("temperature_c"),
            "humidity_percent": fallback.get("humidity_percent"),
            "aqi": fallback.get("aqi"),
            "pm25": fallback.get("pm25"),
            "pm10": fallback.get("pm10"),
            "water_hardness_level": fallback.get("water_hardness_level"),
            "payload": {
                "source": "environment_contexts_fallback",
                "environment_id": fallback.get("environment_id"),
                "care_triggers": fallback.get("care_triggers"),
            },
        }

    def with_fallback_water_hardness(self, observation: dict[str, Any], region: str, city: str | None) -> dict[str, Any]:
        if observation.get("water_hardness_level"):
            return observation
        fallback = self.repo.get_environment_context(region=region, city=city)
        if fallback and fallback.get("water_hardness_level"):
            observation = dict(observation)
            observation["water_hardness_level"] = fallback["water_hardness_level"]
            payload = dict(observation.get("payload") or {})
            payload["water_hardness_provider_id"] = self.WATER_HARDNESS_PROVIDER_ID
            payload["fallback_water_hardness_source"] = fallback.get("environment_id")
            observation["payload"] = payload
        return observation

    @staticmethod
    def is_fresh(observed_at: str | None, ttl_minutes: int) -> bool:
        if not observed_at:
            return False
        try:
            normalized = observed_at.replace("Z", "+00:00")
            dt = datetime.fromisoformat(normalized)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return datetime.now(timezone.utc) - dt <= timedelta(minutes=ttl_minutes)
        except Exception:
            return False
