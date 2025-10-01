from __future__ import annotations

import copy
import json
import zipfile
from pathlib import Path
from typing import Any, Iterable

try:
    from pyproj import Transformer  # type: ignore
except ImportError:  # pragma: no cover - optional dependency
    Transformer = None  # type: ignore


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def save_geojson(geojson: dict[str, Any], path: Path) -> None:
    ensure_dir(path.parent)
    path.write_text(json.dumps(geojson, ensure_ascii=False), encoding="utf-8")


def _detect_epsg(geojson: dict[str, Any]) -> int | None:
    crs = geojson.get("crs")
    if not isinstance(crs, dict):
        return None
    props = crs.get("properties")
    if not isinstance(props, dict):
        return None
    for key in ("name", "code", "epsg"):
        value = props.get(key)
        if isinstance(value, int):
            return value
        if isinstance(value, str):
            digits = "".join(ch for ch in value if ch.isdigit())
            if digits:
                try:
                    return int(digits)
                except ValueError:
                    continue
    return None


def _transform_position(transform: Any, position: Iterable[Any]) -> list[Any]:
    data = list(position)
    if len(data) < 2:
        return data
    x, y = data[0], data[1]
    try:
        nx, ny = transform(x, y)
    except Exception:  # pragma: no cover - defensive
        return data
    tail = data[2:]
    return [nx, ny, *tail]


def _map_coordinates(transform: Any, coords: Any) -> Any:
    if isinstance(coords, (list, tuple)):
        if coords and isinstance(coords[0], (int, float)):
            return _transform_position(transform, coords)
        return [_map_coordinates(transform, item) for item in coords]
    return coords


def _transform_geometry(transform: Any, geometry: dict[str, Any]) -> dict[str, Any]:
    geom_type = geometry.get("type")
    if geom_type == "GeometryCollection":
        geometries = geometry.get("geometries")
        if isinstance(geometries, list):
            return {
                "type": geom_type,
                "geometries": [
                    _transform_geometry(transform, g)
                    if isinstance(g, dict)
                    else g
                    for g in geometries
                ],
            }
        return geometry
    coords = geometry.get("coordinates")
    if coords is None:
        return geometry
    return {
        "type": geom_type,
        "coordinates": _map_coordinates(transform, coords),
    }


def reproj_to_4326(geojson: dict[str, Any]) -> dict[str, Any]:
    epsg = _detect_epsg(geojson)
    if epsg in (None, 4326):
        return geojson
    if Transformer is None:
        print("[warn] pyproj nao instalado; retornando geometria original")
        return geojson
    try:
        transformer = Transformer.from_crs(f"epsg:{epsg}", "epsg:4326", always_xy=True)
    except Exception:  # pragma: no cover - defensive
        return geojson

    features = geojson.get("features")
    if not isinstance(features, list):
        return geojson

    converted = copy.deepcopy(geojson)
    converted_features: list[dict[str, Any]] = []
    for feature in features:
        if not isinstance(feature, dict):
            continue
        new_feature = copy.deepcopy(feature)
        geometry = feature.get("geometry")
        if isinstance(geometry, dict):
            new_feature["geometry"] = _transform_geometry(transformer.transform, geometry)
        converted_features.append(new_feature)
    converted["features"] = converted_features
    # remove CRS porque agora esta em EPSG:4326
    converted.pop("crs", None)
    return converted


def to_kml_kmz(geojson: dict[str, Any], kmz_path: Path) -> None:
    def coord_str(coords: Iterable[Iterable[float]]) -> str:
        return " ".join(f"{x},{y},0" for x, y, *_ in coords)

    kml = [
        "<?xml version=\"1.0\" encoding=\"UTF-8\"?>",
        "<kml xmlns=\"http://www.opengis.net/kml/2.2\"><Document>",
    ]
    for feature in geojson.get("features", []):
        geometry = (feature or {}).get("geometry") or {}
        props = (feature or {}).get("properties") or {}
        name = props.get("name") or props.get("NOME") or ""
        gtype = geometry.get("type")
        coords = geometry.get("coordinates")
        if gtype == "Point" and isinstance(coords, (list, tuple)):
            x, y, *_ = coords
            kml.extend([
                "<Placemark>",
                f"<name>{name}</name>" if name else "",
                f"<Point><coordinates>{x},{y},0</coordinates></Point>",
                "</Placemark>",
            ])
        elif gtype == "Polygon" and isinstance(coords, list) and coords:
            outer = coords[0]
            kml.extend([
                "<Placemark>",
                f"<name>{name}</name>" if name else "",
                "<Polygon><outerBoundaryIs><LinearRing><coordinates>",
                coord_str(outer),
                "</coordinates></LinearRing></outerBoundaryIs></Polygon>",
                "</Placemark>",
            ])
        elif gtype == "MultiPolygon" and isinstance(coords, list):
            for poly in coords:
                if not poly:
                    continue
                outer = poly[0]
                kml.extend([
                    "<Placemark>",
                    f"<name>{name}</name>" if name else "",
                    "<Polygon><outerBoundaryIs><LinearRing><coordinates>",
                    coord_str(outer),
                    "</coordinates></LinearRing></outerBoundaryIs></Polygon>",
                    "</Placemark>",
                ])
    kml.append("</Document></kml>")
    xml = "\n".join(line for line in kml if line).encode("utf-8")
    ensure_dir(kmz_path.parent)
    with zipfile.ZipFile(kmz_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("doc.kml", xml)
