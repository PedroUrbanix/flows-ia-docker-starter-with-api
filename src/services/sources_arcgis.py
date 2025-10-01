from __future__ import annotations

from typing import Any, Dict

import httpx


async def try_arcgis_geojson(
    url: str,
    params: Dict[str, Any] | None,
    soft: bool = False,
    client: httpx.AsyncClient | None = None,
) -> Dict | None:
    query = {
        "f": "geojson",
        "returnGeometry": "true",
        "outSR": "4326",
    }
    if params:
        query.update(params)

    owns_client = client is None
    if owns_client:
        client = httpx.AsyncClient(timeout=httpx.Timeout(90.0))

    try:
        response = await client.get(url, params=query)
        if soft and response.status_code != 200:
            return None
        response.raise_for_status()
        payload = response.json()
    except httpx.HTTPError:
        if soft:
            return None
        raise
    finally:
        if owns_client and client is not None:
            await client.aclose()

    if isinstance(payload, dict) and payload.get("type") == "FeatureCollection" and "features" in payload:
        return payload
    return None
