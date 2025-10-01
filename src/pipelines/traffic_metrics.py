from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Dict, Mapping

import httpx

GOOGLE_DIRECTIONS_URL = "https://maps.googleapis.com/maps/api/directions/json"


class TrafficMetricsError(RuntimeError):
    """Raised when the Google Maps response cannot be turned into metrics."""


def _format_latlon(point: Mapping[str, float]) -> str:
    try:
        lat = float(point["latitude"])
        lon = float(point["longitude"])
    except (KeyError, TypeError, ValueError) as exc:  # pragma: no cover - defensive
        raise TrafficMetricsError("origin/destination must provide latitude and longitude") from exc
    return f"{lat},{lon}"


def _extract_leg(data: Dict) -> Dict:
    routes = data.get("routes") or []
    if not routes:
        raise TrafficMetricsError("Google Maps returned no routes")
    legs = routes[0].get("legs") or []
    if not legs:
        raise TrafficMetricsError("Google Maps returned route without legs")
    return legs[0]


def run_segment(
    api_key: str,
    origin: Mapping[str, float],
    destination: Mapping[str, float],
    outdir: Path | None = None,
) -> Dict:
    if not api_key:
        raise TrafficMetricsError("Google Maps API key is missing")

    params = {
        "origin": _format_latlon(origin),
        "destination": _format_latlon(destination),
        "departure_time": "now",
        "traffic_model": "best_guess",
        "mode": "driving",
        "key": api_key,
    }

    try:
        with httpx.Client(timeout=httpx.Timeout(30.0)) as client:
            response = client.get(GOOGLE_DIRECTIONS_URL, params=params)
            response.raise_for_status()
    except httpx.HTTPError as exc:  # pragma: no cover - network dependent
        raise TrafficMetricsError(f"Google Maps request failed: {exc}") from exc

    payload = response.json()

    status = payload.get("status", "UNKNOWN")
    if status != "OK":
        raise TrafficMetricsError(f"Google Maps returned status {status}")

    leg = _extract_leg(payload)

    duration_in_traffic = leg.get("duration_in_traffic", {}).get("value")
    duration = leg.get("duration", {}).get("value")
    distance = leg.get("distance", {}).get("value")

    if duration_in_traffic is None:
        duration_in_traffic = duration
    if duration is None or distance is None:
        raise TrafficMetricsError("Google Maps response did not include duration/distance")

    tti = max(0.0, float(duration_in_traffic) / max(1.0, float(duration)))
    result = {
        "duration_s": float(duration_in_traffic),
        "static_s": float(duration),
        "distance_m": float(distance),
        "TTI": tti,
        "pct_slow": 0.0,
        "pct_jam": 0.0,
        "fetched_at": int(time.time()),
    }

    if outdir:
        outdir.mkdir(parents=True, exist_ok=True)
        raw_path = outdir / "last_segment_raw.json"
        raw_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    return result
