"""Lightweight weather lookup for the home screen greeting.

Uses Open-Meteo (free, no API key, no signup):
  · geocoding:  https://geocoding-api.open-meteo.com/v1/search?name={city}
  · forecast:   https://api.open-meteo.com/v1/forecast?latitude=..&longitude=..

Everything is optional and non-blocking: if there is no network, no city
configured, or the API errors, we return None and the home screen falls
back to a time-only greeting.  Results are cached for a short time so we
do not hammer the API on every page switch.
"""

import json
import logging
import time
import urllib.parse
import urllib.request

GEO_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"

TIMEOUT = 4.0          # seconds - fail fast when offline
CACHE_TTL = 20 * 60    # seconds - re-check weather at most every 20 min

_cache: dict = {"at": 0.0, "payload": None}

#: WMO weather interpretation codes -> short friendly label
WMO = {
    0: "clear sky",
    1: "mainly clear",
    2: "partly cloudy",
    3: "overcast",
    45: "fog",
    48: "freezing fog",
    51: "light drizzle",
    53: "drizzle",
    55: "heavy drizzle",
    56: "freezing drizzle",
    57: "freezing drizzle",
    61: "light rain",
    63: "rain",
    65: "heavy rain",
    66: "freezing rain",
    67: "freezing rain",
    71: "light snow",
    73: "snow",
    75: "heavy snow",
    77: "snow grains",
    80: "light showers",
    81: "showers",
    82: "heavy showers",
    85: "snow showers",
    86: "heavy snow showers",
    95: "thunderstorm",
    96: "storm with hail",
    99: "storm with hail",
}


def _get_json(url: str, params: dict):
    qs = urllib.parse.urlencode(params)
    req = urllib.request.Request(f"{url}?{qs}", headers={"User-Agent": "RCD2000/1.0"})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _geocode(city: str) -> tuple | None:
    """City name -> (lat, lon) via Open-Meteo geocoding."""
    data = _get_json(GEO_URL, {"name": city, "count": 1, "language": "en", "format": "json"})
    results = data.get("results") or []
    if not results:
        return None
    r = results[0]
    return (r["latitude"], r["longitude"])


def _describe(weather_code: int) -> str:
    return WMO.get(weather_code, "mixed conditions")


def fetch_weather(city: str) -> dict | None:
    """Return {temp_c, condition} for *city*, or None on any failure.

    Cached for CACHE_TTL seconds so repeated home-page visits are free.
    """
    city = (city or "").strip()
    if not city:
        return None

    now = time.time()
    if _cache["payload"] is not None and now - _cache["at"] < CACHE_TTL:
        return _cache["payload"]

    try:
        latlon = _geocode(city)
        if latlon is None:
            logging.info("Weather: could not geocode city %r", city)
            return None
        lat, lon = latlon
        data = _get_json(FORECAST_URL, {
            "latitude": lat,
            "longitude": lon,
            "current": "temperature_2m,weather_code",
            "timezone": "auto",
        })
        current = data.get("current") or {}
        temp = current.get("temperature_2m")
        code = current.get("weather_code")
        if temp is None:
            return None
        payload = {
            "temp_c": round(temp),
            "condition": _describe(int(code)) if code is not None else "",
            "city": city,
        }
        _cache.update(at=now, payload=payload)
        return payload
    except Exception:
        logging.info("Weather: lookup failed (offline?) for %r", city, exc_info=True)
        return None
