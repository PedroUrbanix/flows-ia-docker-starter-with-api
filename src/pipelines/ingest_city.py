from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Dict, List

from services.sources_ai import ai_discover_sources
from services.sources_arcgis import try_arcgis_geojson
from services.sources_osm import get_city_boundary, overpass_pois
from utils.io import ensure_dir, reproj_to_4326, save_geojson, to_kml_kmz

CATALOG: Dict[str, Dict] = {
    "londrina|pr": {
        "educacao": [
            {
                "name": "escolas_municipais_pontos",
                "type": "arcgis_query",
                "url": "https://geo.londrina.pr.gov.br/server/rest/services/Publico/SmeEducacaoPublico/MapServer/2/query",
                "params": {
                    "where": "1=1",
                    "outFields": "*",
                    "returnGeometry": "true",
                    "outSR": "4326",
                    "f": "geojson",
                },
            },
            {
                "name": "educacao_p4",
                "type": "arcgis_query",
                "url": "https://geo.londrina.pr.gov.br/server/rest/services/Publico/SMEAbrangenciaP4P5EscolasMunicipaisConsultaPublica/MapServer/0/query",
                "params": {
                    "where": "1=1",
                    "outFields": "*",
                    "returnGeometry": "true",
                    "outSR": "4326",
                    "f": "geojson",
                },
            },
            {
                "name": "educacao_p5",
                "type": "arcgis_query",
                "url": "https://geo.londrina.pr.gov.br/server/rest/services/Publico/SMEAbrangenciaP4P5EscolasMunicipaisConsultaPublica/MapServer/1/query",
                "params": {
                    "where": "1=1",
                    "outFields": "*",
                    "returnGeometry": "true",
                    "outSR": "4326",
                    "f": "geojson",
                },
            },
            {
                "name": "educacao_abrangencia_escolas",
                "type": "arcgis_query",
                "url": "https://geo.londrina.pr.gov.br/server/rest/services/Publico/SMEAbrangenciaP4P5EscolasMunicipaisConsultaPublica/MapServer/2/query",
                "params": {
                    "where": "1=1",
                    "outFields": "*",
                    "returnGeometry": "true",
                    "outSR": "4326",
                    "f": "geojson",
                },
            },
        ],
        "saude": [
            {
                "name": "ubs_pontos",
                "type": "arcgis_query",
                "url": "https://geo.londrina.pr.gov.br/server/rest/services/Publico/SaudeUnidadesBasicasAbrangenciaPublico/MapServer/0/query",
                "params": {
                    "where": "1=1",
                    "outFields": "*",
                    "returnGeometry": "true",
                    "outSR": "4326",
                    "f": "geojson",
                },
            },
            {
                "name": "ubs_territorios",
                "type": "arcgis_query",
                "url": "https://geo.londrina.pr.gov.br/server/rest/services/Publico/SaudeUnidadesBasicasAbrangenciaPublico/MapServer/1/query",
                "params": {
                    "where": "1=1",
                    "outFields": "*",
                    "returnGeometry": "true",
                    "outSR": "4326",
                    "f": "geojson",
                },
            },
        ],
        "assistencia": [
            {
                "name": "cras_pontos",
                "type": "arcgis_query",
                "url": "https://geo.londrina.pr.gov.br/server/rest/services/Publico/SmasInformacoesGerais/MapServer/1/query",
                "params": {
                    "where": "1=1",
                    "outFields": "*",
                    "returnGeometry": "true",
                    "outSR": "4326",
                    "f": "geojson",
                },
            },
            {
                "name": "cras_territorios",
                "type": "arcgis_query",
                "url": "https://geo.londrina.pr.gov.br/server/rest/services/Publico/SmasInformacoesGerais/MapServer/2/query",
                "params": {
                    "where": "1=1",
                    "outFields": "*",
                    "returnGeometry": "true",
                    "outSR": "4326",
                    "f": "geojson",
                },
            },
        ],
        "core": [
            {
                "name": "bairros_sig",
                "type": "arcgis_try",
                "url": "https://geo.londrina.pr.gov.br/server/rest/services/Publico/MapasBase/MapServer/0/query",
                "params": {
                    "where": "1=1",
                    "outFields": "*",
                    "returnGeometry": "true",
                    "outSR": "4326",
                    "f": "geojson",
                },
            }
        ],
    }
}


async def _collect_source(source: Dict) -> Dict | None:
    try:
        if source.get("type") == "arcgis_query":
            geojson = await try_arcgis_geojson(source["url"], source.get("params", {}))
        elif source.get("type") == "arcgis_try":
            geojson = await try_arcgis_geojson(source["url"], source.get("params", {}), soft=True)
        else:
            return None
    except Exception as exc:  # pragma: no cover - defensive logging
        print("[warn]", source.get("name"), "failed:", exc)
        return None
    if not geojson:
        return None
    return {"name": source["name"], "geojson": geojson}


async def run_ingest(city: str, state: str, outputs: List[str], modes: List[str], what: str, outdir: str, interactive: bool = False):
    key = f"{city.lower()}|{state.lower()}"
    out = Path(outdir)
    ensure_dir(out)

    boundary = await get_city_boundary(city, state)
    if boundary:
        save_geojson(boundary, out / f"{city}_{state}_boundary.geojson")
        if "kmz" in outputs:
            to_kml_kmz(boundary, out / f"{city}_{state}_boundary.kmz")

    sources: List[Dict] = []
    if "catalog" in modes and key in CATALOG:
        if what == "all":
            for items in CATALOG[key].values():
                sources.extend(items)
        else:
            sources.extend(CATALOG[key].get(what, []))

    if "ai" in modes:
        ai_sources = await ai_discover_sources(city, state, what=what)
        if ai_sources:
            sources.extend(ai_sources)

    collected: List[Dict] = []
    if sources:
        results = await asyncio.gather(
            *(_collect_source(source) for source in sources),
            return_exceptions=True,
        )
        for result in results:
            if isinstance(result, Exception):
                print("[warn] arcgis task failed:", result)
                continue
            if result:
                collected.append(result)

    if boundary:
        bbox = boundary_bbox(boundary)
        pois = await overpass_pois(
            bbox,
            kinds=["hospital", "clinic", "school", "kindergarten", "bus_stop"],
        )
        if pois:
            collected.append({"name": "osm_pois_saude_educacao_onibus", "geojson": pois})

    manifest = []
    for item in collected:
        name = item["name"]
        geojson = reproj_to_4326(item["geojson"])
        safe_key = key.replace("|", "_")
        geo_path = out / f"{safe_key}_{name}.geojson"
        save_geojson(geojson, geo_path)
        if "kmz" in outputs:
            to_kml_kmz(geojson, out / f"{safe_key}_{name}.kmz")
        manifest.append({"name": name, "geojson": str(geo_path)})

    (out / f"{key}_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print("[ok]", len(manifest), "layers saved in", out.resolve())


def boundary_bbox(geojson: dict):
    import math

    xmin, ymin, xmax, ymax = math.inf, math.inf, -math.inf, -math.inf

    def iterator(geom):
        gtype = geom.get("type")
        coords = geom.get("coordinates")
        if gtype == "Polygon":
            for ring in coords:
                for x, y, *_ in ring:
                    yield x, y
        elif gtype == "MultiPolygon":
            for poly in coords:
                for ring in poly:
                    for x, y, *_ in ring:
                        yield x, y

    for feature in geojson.get("features", []):
        geometry = feature.get("geometry") or {}
        for x, y in iterator(geometry):
            xmin = min(xmin, x)
            ymin = min(ymin, y)
            xmax = max(xmax, x)
            ymax = max(ymax, y)
    return (xmin, ymin, xmax, ymax)

