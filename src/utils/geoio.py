
from pathlib import Path
import json, zipfile, xml.etree.ElementTree as ET

def read_geojson(path: Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))

def write_geojson(obj: dict, path: Path):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(obj, ensure_ascii=False), encoding="utf-8")

def _kml_coords_to_list(coord_text: str):
    pts = []
    for tok in (coord_text or "").strip().split():
        parts = tok.split(",")
        if len(parts) >= 2:
            lon = float(parts[0]); lat = float(parts[1])
            pts.append([lon, lat])
    return pts

def _kml_linestring(elem):
    coords = elem.find(".//{http://www.opengis.net/kml/2.2}coordinates")
    if coords is None or not coords.text:
        return None
    pts = _kml_coords_to_list(coords.text)
    if len(pts) < 2:
        return None
    return {"type":"LineString","coordinates": pts}

def _kml_point(elem):
    coords = elem.find(".//{http://www.opengis.net/kml/2.2}coordinates")
    if coords is None or not coords.text:
        return None
    pts = _kml_coords_to_list(coords.text)
    if not pts:
        return None
    lon, lat = pts[0]
    return {"type":"Point","coordinates":[lon, lat]}

def _kml_polygon(elem):
    coords = elem.findall(".//{http://www.opengis.net/kml/2.2}outerBoundaryIs//{http://www.opengis.net/kml/2.2}coordinates")
    if not coords:
        return None
    rings = []
    for c in coords:
        pts = _kml_coords_to_list(c.text or "")
        if len(pts) >= 4:
            rings.append(pts)
    # Fechar anéis (GeoJSON exige primeiro==último)
    if rings:
        closed = []
        for ring in rings:
            if ring[0] != ring[-1]:
                ring = ring + [ring[0]]
            closed.append(ring)
        rings = closed
    if not rings:
        return None
    return {"type":"Polygon","coordinates": rings}

def read_kmz_as_geojson(path: Path) -> dict:
    with zipfile.ZipFile(path, "r") as z:
        kml_names = [n for n in z.namelist() if n.lower().endswith(".kml")]
        if not kml_names:
            raise RuntimeError("KMZ sem KML interno")
        kml_xml = z.read(kml_names[0]).decode("utf-8", errors="ignore")
    ns = {"k":"http://www.opengis.net/kml/2.2"}
    root = ET.fromstring(kml_xml)
    feats = []
    for pm in root.findall(".//k:Placemark", ns):
        name_el = pm.find("k:name", ns)
        props = {"name": name_el.text.strip() if name_el is not None and name_el.text else ""}
        geom = None
        if pm.find(".//k:LineString", ns) is not None:
            geom = _kml_linestring(pm)
        elif pm.find(".//k:Polygon", ns) is not None:
            geom = _kml_polygon(pm)
        elif pm.find(".//k:Point", ns) is not None:
            geom = _kml_point(pm)
        if geom:
            feats.append({"type":"Feature","properties":props,"geometry":geom})
    return {"type":"FeatureCollection","features":feats}

def read_any_geo(path: Path) -> dict:
    p = Path(path)
    if p.suffix.lower() in [".geojson",".json"]:
        return read_geojson(p)
    if p.suffix.lower() == ".kmz":
        return read_kmz_as_geojson(p)
    raise RuntimeError(f"Formato não suportado: {p}")
