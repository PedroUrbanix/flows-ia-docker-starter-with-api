from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List

from services.arcgis_discovery import (
    candidate_roots_for_city,
    crawl_all_layers,
    fetch_geojson_paged,
)
from services.sources_ai import ai_discover_arcgis_roots
from ui.interactive import interactive_filter_and_download
from utils.io import ensure_dir, save_geojson

CATALOG_ROOTS: Dict[str, List[str]] = {
    "londrina|pr": [
        "https://geo.londrina.pr.gov.br/server/rest/services",
    ]
}


def _normalize_root(value: str) -> str:
    return value.strip().rstrip("/")


async def run_discover_and_download(
    city: str,
    state: str,
    modes: List[str],
    outputs: List[str],
    outdir: str,
    roots: List[str],
) -> None:
    key = f"{city.lower()}|{state.lower()}"
    output_dir = Path(outdir)
    ensure_dir(output_dir)

    roots_all: List[str] = []
    if roots:
        roots_all.extend(roots)

    mode_set = {mode.lower() for mode in modes}
    if "catalog" in mode_set and key in CATALOG_ROOTS:
        roots_all.extend(CATALOG_ROOTS[key])

    roots_all.extend(candidate_roots_for_city(city, state))

    if "ai" in mode_set:
        ai_roots = await ai_discover_arcgis_roots(city, state)
        roots_all.extend(ai_roots)

    normalized_roots = sorted({_normalize_root(root) for root in roots_all if root})

    if not normalized_roots:
        print("[warn] nenhuma raiz encontrada")
        return

    found = crawl_all_layers(normalized_roots)
    if not found:
        print("[warn] nenhum servico encontrado")
        return

    selection = interactive_filter_and_download(found)
    if not selection:
        print("[warn] nenhuma camada selecionada")
        return

    manifest = []
    for item in selection:
        layer = item.get("layer", {})
        query_url = (layer.get("url") or "").rstrip("/") + "/query"
        name = item.get("display_name") or layer.get("name") or "layer"
        geojson = fetch_geojson_paged(query_url)
        if not geojson:
            print(f"[warn] falha ao baixar {name}")
            continue
        safe_name = (
            name.lower()
            .replace(" ", "_")
            .replace("/", "_")
            .replace("|", "_")
        )
        geojson_path = output_dir / f"{safe_name}.geojson"
        save_geojson(geojson, geojson_path)
        manifest.append({"name": name, "geojson": str(geojson_path)})
        print(f"[ok] salvo: {geojson_path}")

    manifest_path = output_dir / "manifest_crawler.json"
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"[ok] {len(manifest)} camadas baixadas -> {output_dir.resolve()}")

