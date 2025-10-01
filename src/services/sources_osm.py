from __future__ import annotations

from typing import Dict, Iterable, List, Tuple

import httpx

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
OVERPASS_URL = "https://overpass-api.de/api/interpreter"
USER_AGENT = "flows-ia/1.0"


async def get_city_boundary(city: str, state: str) -> Dict | None:
    params = {
        "q": f"{city}, {state}, Brazil",
        "format": "jsonv2",
        "polygon_geojson": 1,
        "addressdetails": 1,
    }
    async with httpx.AsyncClient(timeout=httpx.Timeout(60.0), headers={"User-Agent": USER_AGENT}) as client:
        response = await client.get(NOMINATIM_URL, params=params)
        response.raise_for_status()
        data = response.json()

    for entry in data:
        geometry = entry.get("geojson")
        if geometry:
            return {
                "type": "FeatureCollection",
                "features": [
                    {
                        "type": "Feature",
                        "properties": {"display_name": entry.get("display_name")},
                        "geometry": geometry,
                    }
                ],
            }
    return None


def _overpass_fragments(bbox: Tuple[float, float, float, float], kinds: Iterable[str]) -> List[str]:
    xmin, ymin, xmax, ymax = bbox
    fragments: List[str] = []
    for kind in kinds:
        if kind in {"hospital", "clinic", "school", "kindergarten"}:
            fragments.append(f"node[\"amenity\"=\"{kind}\"]({ymin},{xmin},{ymax},{xmax});")
        elif kind == "bus_stop":
            fragments.append(f"node[\"highway\"=\"bus_stop\"]({ymin},{xmin},{ymax},{xmax});")
    return fragments


async def overpass_pois(bbox: Tuple[float, float, float, float], kinds: List[str]) -> Dict | None:
    fragments = _overpass_fragments(bbox, kinds)
    if not fragments:
        return None
    query = f"[out:json][timeout:60];({''.join(fragments)});out center;"
    async with httpx.AsyncClient(timeout=httpx.Timeout(90.0)) as client:
        response = await client.get(OVERPASS_URL, params={"data": query})
        response.raise_for_status()
        data = response.json()

    features = []
    for element in data.get("elements", []):
        if element.get("type") == "node" and "lon" in element and "lat" in element:
            properties = dict(element.get("tags") or {})
            properties["id"] = element.get("id")
            features.append(
                {
                    "type": "Feature",
                    "properties": properties,
                    "geometry": {
                        "type": "Point",
                        "coordinates": [element["lon"], element["lat"]],
                    },
                }
            )
    return {"type": "FeatureCollection", "features": features} if features else None
