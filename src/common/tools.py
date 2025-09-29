from __future__ import annotations
from typing import Any, Dict, List
from common.utils import log

class Tools:
    def __init__(self):
        # Em produção: injete clientes http/geocoder/arcgis etc.
        pass

    # === Busca ===
    async def search_agent(self, municipio: str, uf: str) -> List[Dict[str, Any]]:
        # TODO: gerar queries e buscar (priorizar dominios .gov.br)
        log(f"[search] {municipio}-{uf}")
        return []

    async def classify_sources(self, seeds) -> Dict[str, Any]:
        # TODO: classificar por tema, detectar ArcGIS/GeoServer/REST/PDF/etc.
        log(f"[classify] seeds={len(seeds) if seeds else 0}")
        return {}

    # === Ingestão ===
    async def ingest(self, catalog: Dict[str, Any]) -> Dict[str, Any]:
        # TODO: downloads + checksum + detecção de tipo
        log("[ingest] starting…")
        return {}

    # === Normalização ===
    async def normalize(self, raw: Dict[str, Any]) -> Dict[str, Any]:
        # TODO: parse → GeoDataFrames (CRS=4326)
        log("[normalize] …")
        return {}

    # === Enriquecimento ===
    async def enrich(self, norm: Dict[str, Any]) -> Dict[str, Any]:
        # TODO: overlay com bairros/zoneamento/IBGE
        log("[enrich] …")
        return {}

    # === Exportação/QA ===
    async def export(self, enr: Dict[str, Any], municipio: str) -> Dict[str, Any]:
        # TODO: gravar geojsons por tema em outputs/{municipio}/YYYY-MM-DD
        log("[export] …")
        return {}

    async def qa(self, outputs: Dict[str, Any]) -> Dict[str, Any]:
        # TODO: validações estruturais e de conteúdo
        log("[qa] …")
        return {}

    async def write_metadata(self, outputs, qa, municipio, uf):
        # TODO: METADATA.json
        log("[metadata] …")
        pass