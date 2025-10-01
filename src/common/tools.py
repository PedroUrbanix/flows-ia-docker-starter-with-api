from __future__ import annotations

from typing import Any, Dict, List

from .utils import log


class Tools:
    """Facade with the async operations used by the orchestrator."""

    def __init__(self):
        # In production inject http, geocoder or arcgis clients through the constructor.
        pass

    # === Search ===
    async def search_agent(self, municipio: str, uf: str) -> List[Dict[str, Any]]:
        # TODO: generate queries and fetch sources (prioritise .gov.br domains)
        log(f"[search] {municipio}-{uf}")
        return []

    async def classify_sources(self, seeds) -> Dict[str, Any]:
        # TODO: group sources by theme and detect ArcGIS/GeoServer/REST/PDF/etc
        log(f"[classify] seeds={len(seeds) if seeds else 0}")
        return {}

    # === Ingest ===
    async def ingest(self, catalog: Dict[str, Any]) -> Dict[str, Any]:
        # TODO: downloads + checksum + type detection
        log("[ingest] starting...")
        return {}

    # === Normalisation ===
    async def normalize(self, raw: Dict[str, Any]) -> Dict[str, Any]:
        # TODO: parse into GeoDataFrames (CRS=4326)
        log("[normalize] ...")
        return {}

    # === Enrichment ===
    async def enrich(self, norm: Dict[str, Any]) -> Dict[str, Any]:
        # TODO: overlay with neighbourhood, zoning and IBGE references
        log("[enrich] ...")
        return {}

    # === Export and QA ===
    async def export(self, enr: Dict[str, Any], municipio: str) -> Dict[str, Any]:
        # TODO: save geojson files per theme in outputs/{municipio}/YYYY-MM-DD
        log("[export] ...")
        return {}

    async def qa(self, outputs: Dict[str, Any]) -> Dict[str, Any]:
        # TODO: structural and content validations
        log("[qa] ...")
        return {}

    async def write_metadata(self, outputs, qa, municipio, uf):
        # TODO: METADATA.json
        log("[metadata] ...")
        pass
