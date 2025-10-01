from __future__ import annotations

import hashlib
import time
import unicodedata
from typing import Dict, List

import requests

DEFAULT_TIMEOUT_SECONDS = 40
PAGED_TIMEOUT_SECONDS = 120
PAGE_SIZE = 2000
MAX_PAGES = 1000


def _slugify(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value.lower())
    return "".join(char for char in normalized if char.isalnum())


def candidate_roots_for_city(city: str, state: str) -> List[str]:
    city_slug = _slugify(city)
    state_slug = state.lower()
    return [
        f"https://geo.{city_slug}.{state_slug}.gov.br/server/rest/services",
        f"https://geo.{city_slug}.pr.gov.br/server/rest/services",
        f"https://{city_slug}.{state_slug}.gov.br/arcgis/rest/services",
        f"https://arcgis.{city_slug}.{state_slug}.gov.br/arcgis/rest/services",
    ]


def _ensure_pjson(url: str) -> str:
    return url if "f=pjson" in url else f"{url.rstrip('/')}?f=pjson"


def _get_json(url: str) -> Dict | None:
    try:
        response = requests.get(_ensure_pjson(url), timeout=DEFAULT_TIMEOUT_SECONDS)
        response.raise_for_status()
        return response.json()
    except (requests.RequestException, ValueError):
        return None


def _build_service_url(base: str, folder: str, name: str, service_type: str) -> str:
    if folder:
        return f"{base}/{folder}/{name}/{service_type}"
    return f"{base}/{name}/{service_type}"


def _list_services(root: str) -> List[Dict[str, str]]:
    data = _get_json(root)
    if not data:
        return []
    base = root.rstrip("/")
    items: List[Dict[str, str]] = []
    for service in data.get("services", []):
        name = service.get("name")
        service_type = service.get("type")
        if not name or not service_type:
            continue
        items.append(
            {
                "folder": "",
                "name": name,
                "type": service_type,
                "url": _build_service_url(base, "", name, service_type),
            }
        )
    for folder in data.get("folders", []):
        folder_data = _get_json(f"{base}/{folder}")
        if not folder_data:
            continue
        for service in folder_data.get("services", []):
            name = service.get("name")
            service_type = service.get("type")
            if not name or not service_type:
                continue
            items.append(
                {
                    "folder": folder,
                    "name": name,
                    "type": service_type,
                    "url": _build_service_url(base, folder, name, service_type),
                }
            )
    return items


def _list_layers(service_url: str) -> List[Dict[str, object]]:
    data = _get_json(service_url)
    if not data:
        return []
    service_base = service_url.rstrip("/")
    layers: List[Dict[str, object]] = []
    entries = (data.get("layers") or []) + (data.get("tables") or [])
    for entry in entries:
        layer_id = entry.get("id")
        if layer_id is None:
            continue
        name = (entry.get("name") or "").strip() or f"layer_{layer_id}"
        geometry_type = entry.get("geometryType") or "table"
        fields = [field.get("name") for field in entry.get("fields") or [] if field.get("name")]
        layers.append(
            {
                "id": layer_id,
                "name": name,
                "geometryType": geometry_type,
                "fields": fields,
                "url": f"{service_base}/{layer_id}",
            }
        )
    return layers


def crawl_all_layers(roots: List[str]) -> List[Dict[str, object]]:
    found: List[Dict[str, object]] = []
    seen: set[str] = set()
    for root in roots:
        for service in _list_services(root):
            for layer in _list_layers(service["url"]):
                fields = layer.get("fields", [])
                field_signature = ",".join(sorted(fields)) if isinstance(fields, list) else ""
                signature = f"{layer['name']}|{layer['geometryType']}|{field_signature}"
                digest = hashlib.sha1(signature.encode("utf-8")).hexdigest()[:12]
                key = f"{layer['name'].lower()}|{layer['geometryType']}|{digest}"
                if key in seen:
                    continue
                seen.add(key)
                found.append(
                    {
                        "root": root,
                        "service": service,
                        "layer": layer,
                        "dedupe_key": key,
                    }
                )
    return found


def fetch_geojson_paged(query_url: str) -> Dict | None:
    features: List[Dict] = []
    offset = 0
    tries = 0

    base_params = {
        "where": "1=1",
        "outFields": "*",
        "returnGeometry": "true",
        "outSR": "4326",
        "f": "geojson",
    }

    while True:
        params = base_params | {"resultOffset": offset, "resultRecordCount": PAGE_SIZE}
        try:
            response = requests.get(query_url, params=params, timeout=PAGED_TIMEOUT_SECONDS)
            response.raise_for_status()
            geojson = response.json()
        except (requests.RequestException, ValueError):
            break
        batch = geojson.get("features", [])
        if not isinstance(batch, list):
            break
        features.extend(batch)
        if len(batch) < PAGE_SIZE:
            break
        offset += PAGE_SIZE
        tries += 1
        if tries >= MAX_PAGES:
            break
        time.sleep(0.2)

    if not features:
        return None
    return {"type": "FeatureCollection", "features": features}
