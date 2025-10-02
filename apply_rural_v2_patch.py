#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Aplica a Prioridade Rural v2 (ICN + ISO + IAX) ao projeto e empacota um ZIP final.
- Corrigido: execução sem PYTHONPATH (gera run_rural.py)
- Corrigido: fechamento de anel em Polygon do KML
- Corrigido: exclusão de pastas pesadas ao montar o ZIP
- Corrigido: ENTREGA_RURAL_v2.md com código-fonte embutido

Uso:
  python apply_rural_v2_patch.py
"""
from pathlib import Path
import zipfile, textwrap, datetime

ROOT = Path(".").resolve()
DIST = ROOT / "dist"
OUTDIR = ROOT / "out" / "rural"

def ensure_dirs():
    for d in [ROOT/"src/cli_rural", ROOT/"src/pipelines", ROOT/"src/utils", ROOT/"docs", OUTDIR, DIST]:
        d.mkdir(parents=True, exist_ok=True)

def write(path: Path, content: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(content), encoding="utf-8")

def append_or_create(path: Path, text: str):
    if path.exists():
        path.write_text(path.read_text(encoding="utf-8") + "\n" + text, encoding="utf-8")
    else:
        path.write_text(text, encoding="utf-8")

def update_requirements(minimal: bool = True):
    need = {"shapely>=2.0.4","pyproj>=3.6.1"}
    if not minimal:
        need |= {"requests>=2.32.0","python-dotenv>=1.0.1"}
    req = ROOT/"requirements.txt"
    if req.exists():
        cur = set(l.strip() for l in req.read_text(encoding="utf-8").splitlines() if l.strip())
        cur |= need
        req.write_text("\n".join(sorted(cur))+"\n", encoding="utf-8")
    else:
        req.write_text("\n".join(sorted(need))+"\n", encoding="utf-8")

def build_zip():
    out_zip = DIST/"flows-ia-rural-v2-ready.zip"
    if out_zip.exists():
        out_zip.unlink()
    EXCLUDE_DIRS = {"dist", "out", ".git", ".venv", "node_modules", "__pycache__"}
    with zipfile.ZipFile(out_zip, "w", zipfile.ZIP_DEFLATED) as z:
        for p in ROOT.rglob("*"):
            if not p.is_file():
                continue
            if any(part in EXCLUDE_DIRS for part in p.relative_to(ROOT).parts):
                continue
            z.write(p, p.relative_to(ROOT))
    return out_zip

def slurp(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8")
    except Exception:
        return ""

# ---------------- utils ----------------
GEOIO = """
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
"""

GEOMATH = """
from shapely.geometry import shape, mapping, Point, LineString
from shapely.ops import unary_union, transform
from pyproj import Transformer

_T_W84_to_3857 = Transformer.from_crs("EPSG:4326", "EPSG:3857", always_xy=True).transform
_T_3857_to_W84 = Transformer.from_crs("EPSG:3857", "EPSG:4326", always_xy=True).transform

def as_shapely_fc(geojson: dict):
    feats = []
    for f in geojson.get("features", []):
        g = f.get("geometry")
        if not g: continue
        feats.append( (shape(g), f.get("properties", {})) )
    return feats

def to_featurecollection(objs):
    out = {"type":"FeatureCollection","features":[]}
    for geom, props in objs:
        out["features"].append({
            "type":"Feature",
            "properties": props or {},
            "geometry": mapping(geom)
        })
    return out

def to_3857(geom):
    return transform(_T_W84_to_3857, geom)

def to_4326(geom):
    return transform(_T_3857_to_W84, geom)

def union_3857(geoms):
    return unary_union([to_3857(g) for g in geoms])

def line_endpoints_wgs84(line: LineString):
    x0,y0 = line.coords[0]
    x1,y1 = line.coords[-1]
    return Point(x0,y0), Point(x1,y1)
"""

NORM = """
def q5_q95(values):
    xs = [v for v in values if v is not None]
    if not xs: return (0.0, 1.0)
    xs = sorted(xs)
    def q(p):
        if not xs: return 0.0
        k = (len(xs)-1) * p
        f = int(k); c = min(f+1, len(xs)-1)
        if f == c: return xs[f]
        return xs[f] + (xs[c]-xs[f])*(k-f)
    return (q(0.05), q(0.95))

def norm_direct(x, p5, p95):
    if x is None: return 0.0
    if p95 <= p5: return 0.0
    v = (x - p5) / (p95 - p5)
    if v < 0: v = 0.0
    if v > 1: v = 1.0
    return float(v)

def norm_inverse(x, p5, p95):
    if x is None: return 0.0
    if p95 <= p5: return 0.0
    v = (p95 - x) / (p95 - p5)
    if v < 0: v = 0.0
    if v > 1: v = 1.0
    return float(v)
"""

POI_WEIGHTS = """
from typing import Dict

CRITICAL_SET = {"hospital", "school", "fire_station", "police"}
COMMERCIAL_SET = {"industrial", "store", "shop", "supermarket", "office"}

def classify_poi(props: dict) -> str:
    keys = ["amenity","shop","office","landuse","category","type","poi_class","kind"]
    vals = []
    for k in keys:
        v = props.get(k)
        if isinstance(v, str):
            vals.append(v.strip().lower())
    for v in vals:
        if v in CRITICAL_SET:
            return "CRITICAL"
        if v in COMMERCIAL_SET:
            return "COMMERCIAL"
    if any(v in ("clinic","university","college","kindergarten") for v in vals):
        return "CRITICAL"
    if any(v in ("mall","marketplace","warehouse","factory","plant") for v in vals):
        return "COMMERCIAL"
    return "OTHER"

def weight_for_category(cat: str, weights: Dict[str, float]) -> float:
    return float(weights.get(cat, {"CRITICAL":5.0,"COMMERCIAL":3.0,"OTHER":1.0}.get(cat, 1.0)))
"""

PIPELINE = """
from pathlib import Path
from typing import Optional, List, Dict
import csv
from shapely.geometry import mapping, LineString
from utils.geoio import read_any_geo, write_geojson
from utils.geomath import as_shapely_fc, to_3857, union_3857, line_endpoints_wgs84
from utils.norm import q5_q95, norm_direct, norm_inverse
from utils.poi_weights import classify_poi, weight_for_category

def _min_endpoint_dist_to_paved_m(line_wgs84: LineString, paved_union_3857) -> float:
    p0, p1 = line_endpoints_wgs84(line_wgs84)
    d0 = to_3857(p0).distance(paved_union_3857)
    d1 = to_3857(p1).distance(paved_union_3857)
    return float(min(d0, d1))

def _bridge_flag(line_wgs84: LineString, paved_union_3857, tol_m: float = 1.0) -> float:
    p0, p1 = line_endpoints_wgs84(line_wgs84)
    c = 0
    if to_3857(p0).distance(paved_union_3857) <= tol_m: c += 1
    if to_3857(p1).distance(paved_union_3857) <= tol_m: c += 1
    return 1.0 if c == 2 else (0.5 if c == 1 else 0.0)

def _touch_paved(line_wgs84: LineString, paved_union_3857, tol_m: float = 0.5) -> int:
    lm = to_3857(line_wgs84)
    return 1 if (lm.distance(paved_union_3857) <= tol_m or lm.intersects(paved_union_3857)) else 0

def _prox_obra_m(line_wgs84: LineString, planned_union_3857) -> Optional[float]:
    if planned_union_3857 is None: return None
    return float(to_3857(line_wgs84).distance(planned_union_3857))

def _adh_overlap(line_wgs84: LineString, planned_union_3857, buffer_m: float = 200.0):
    if planned_union_3857 is None: return (None, None)
    lm = to_3857(line_wgs84)
    buf = planned_union_3857.buffer(buffer_m)
    inter = lm.intersection(buf)
    if inter.is_empty:
        return (0.0, 0.0)
    overlap_m = inter.length
    pct = (overlap_m / lm.length) if lm.length > 0 else 0.0
    return (float(overlap_m), float(pct))

def _poi_weighted(line_wgs84: LineString, pois_fc: List, buffer_m: float, weights: Dict[str, float]):
    lm = to_3857(line_wgs84)
    buf = lm.buffer(buffer_m)
    n_crit = n_comm = n_other = 0
    weighted = 0.0
    for g, props in pois_fc:
        gm = to_3857(g)
        if not gm.is_empty and gm.intersects(buf):
            cat = classify_poi(props or {})
            w = weight_for_category(cat, weights)
            if cat == "CRITICAL": n_crit += 1
            elif cat == "COMMERCIAL": n_comm += 1
            else: n_other += 1
            weighted += w
    len_km = lm.length / 1000.0 if lm.length > 0 else 0.0
    weighted_per_km = (weighted / len_km) if len_km > 0 else weighted
    return n_crit, n_comm, n_other, weighted, weighted_per_km

def _pop_proxy(line_wgs84: LineString,
               pop_grid_fc: Optional[List],
               pop_grid_field: Optional[str],
               res_points_fc: Optional[List],
               persons_per_addr: float,
               buffer_m: float):
    lm = to_3857(line_wgs84)
    buf = lm.buffer(buffer_m)
    pop_total = 0.0

    if pop_grid_fc and pop_grid_field:
        for g, props in pop_grid_fc:
            gm = to_3857(g)
            if gm.is_empty: continue
            inter = gm.intersection(buf)
            if inter.is_empty: continue
            poly_area = gm.area
            if poly_area <= 0: continue
            pop_val = props.get(pop_grid_field)
            if pop_val is None: continue
            try:
                pop_val = float(pop_val)
            except:
                continue
            frac = inter.area / poly_area
            pop_total += pop_val * frac
    elif res_points_fc:
        count = 0
        for g, props in res_points_fc:
            gm = to_3857(g)
            if not gm.is_empty and gm.within(buf):
                count += 1
        pop_total = count * float(persons_per_addr)

    len_km = lm.length / 1000.0 if lm.length > 0 else 0.0
    pop_per_km = (pop_total / len_km) if len_km > 0 else pop_total
    return pop_total, pop_per_km

def _compute_scores(features: List[Dict]) -> None:
    dist_conn = [f["properties"].get("dist_conn_m") for f in features if f["properties"].get("dist_conn_m") is not None]
    prox_obra = [f["properties"].get("prox_obra_m") for f in features if f["properties"].get("prox_obra_m") is not None]
    overlap_m = [f["properties"].get("overlap_m") for f in features if f["properties"].get("overlap_m") is not None]
    adh_pct   = [f["properties"].get("adh_pct")   for f in features if f["properties"].get("adh_pct")   is not None]
    poi_wpkm  = [f["properties"].get("poi_w_per_km") for f in features if f["properties"].get("poi_w_per_km") is not None]
    pop_pkm   = [f["properties"].get("pop_per_km") for f in features if f["properties"].get("pop_per_km") is not None]

    p5_d,p95_d   = q5_q95(dist_conn) if dist_conn else (0.0,1.0)
    p5_po,p95_po = q5_q95(prox_obra) if prox_obra else (0.0,1.0)
    p5_ov,p95_ov = q5_q95(overlap_m) if overlap_m else (0.0,1.0)
    p5_ap,p95_ap = q5_q95(adh_pct)   if adh_pct   else (0.0,1.0)
    p5_pw,p95_pw = q5_q95(poi_wpkm)  if poi_wpkm  else (0.0,1.0)
    p5_pp,p95_pp = q5_q95(pop_pkm)   if pop_pkm   else (0.0,1.0)

    for f in features:
        pr = f["properties"]

        icn = 0.0
        if pr.get("dist_conn_m") is not None:
            icn += 0.45 * norm_inverse(pr["dist_conn_m"], p5_d, p95_d)
        icn += 0.35 * float(pr.get("bridge_flag", 0.0))
        icn += 0.20 * float(pr.get("touch_paved", 0))
        pr["ICN"] = round(icn, 4)

        iso = 0.0
        if pr.get("prox_obra_m") is not None:
            iso += 0.60 * norm_inverse(pr["prox_obra_m"], p5_po, p95_po)
        if pr.get("adh_pct") is not None:
            iso += 0.40 * norm_direct(pr["adh_pct"], p5_ap, p95_ap)
        elif pr.get("overlap_m") is not None:
            iso += 0.40 * norm_direct(pr["overlap_m"], p5_ov, p95_ov)
        pr["ISO"] = round(iso, 4)

        iax = None
        has_poi = pr.get("poi_w_per_km") is not None
        has_pop = pr.get("pop_per_km") is not None
        if has_poi or has_pop:
            part_poi = norm_direct(pr.get("poi_w_per_km"), p5_pw, p95_pw) if has_poi else 0.0
            part_pop = norm_direct(pr.get("pop_per_km"), p5_pp, p95_pp) if has_pop else 0.0
            iax = (0.5 * part_poi + 0.5 * part_pop) if (has_poi and has_pop) else (part_poi if has_poi else part_pop)
            pr["IAX"] = round(iax, 4)

        if iax is None:
            ipd = 0.65 * icn + 0.35 * iso
        else:
            ipd = 0.50 * icn + 0.25 * iso + 0.25 * iax
        pr["IPD"] = round(ipd, 4)
        pr["prioridade"] = "ALTA" if ipd >= 0.66 else ("MÉDIA" if ipd >= 0.33 else "BAIXA")
        pr["color_hex"] = "#4CAF50" if pr["prioridade"] == "ALTA" else ("#FFC107" if pr["prioridade"] == "MÉDIA" else "#F44336")

        just_att = []
        if pr.get("poi_weighted") is not None:
            try:
                just_att.append(f"POIs(peso)={int(round(float(pr['poi_weighted'])))}")
            except:
                pass
        if pr.get("pop_attended") is not None:
            try:
                just_att.append(f"População={int(round(float(pr['pop_attended'])))}")
            except:
                pass
        if just_att:
            pr["Justificativa_Score_Atendimento"] = " | ".join(just_att)
        if pr.get("prox_obra_m") is not None:
            prox_txt = f"{int(round(pr['prox_obra_m']))} m de corredor"
            if pr.get("adh_pct") is not None:
                try:
                    prox_txt += f" | aderência {int(round(pr['adh_pct'] * 100))}%"
                except:
                    pass
            pr["Justificativa_Score_Proximidade"] = prox_txt

def run_rural_priority(
    rural_path: Path,
    urban_paved_path: Path,
    planned_corridors_path: Optional[Path],
    rural_centers_path: Optional[Path],
    outdir: Path,
    adh_buffer_m: float = 200.0,
    centers_radius_m: float = 3000.0,
    meta_sources: Optional[Dict] = None,
    pois_path: Optional[Path] = None,
    poi_buffer_m: float = 500.0,
    poi_weights: Optional[Dict[str, float]] = None,
    pop_grid_path: Optional[Path] = None,
    pop_grid_pop_field: Optional[str] = None,
    res_points_path: Optional[Path] = None,
    persons_per_addr: float = 3.0,
    pop_buffer_m: Optional[float] = None,
):
    rural = read_any_geo(rural_path)
    urban = read_any_geo(urban_paved_path)
    planned = read_any_geo(planned_corridors_path) if planned_corridors_path else None
    centers = read_any_geo(rural_centers_path) if rural_centers_path else None
    pois = read_any_geo(pois_path) if pois_path else None
    pop_grid = read_any_geo(pop_grid_path) if pop_grid_path else None
    res_pts = read_any_geo(res_points_path) if res_points_path else None

    rural_fc = as_shapely_fc(rural)
    urban_fc = as_shapely_fc(urban)
    planned_fc = as_shapely_fc(planned) if planned else None
    centers_fc = as_shapely_fc(centers) if centers else None
    pois_fc = as_shapely_fc(pois) if pois else None
    pop_grid_fc = as_shapely_fc(pop_grid) if pop_grid else None
    res_pts_fc = as_shapely_fc(res_pts) if res_pts else None

    paved_union_3857 = union_3857([g for g,_ in urban_fc]) if urban_fc else None
    planned_union_3857 = union_3857([g for g,_ in planned_fc]) if planned_fc else None

    poi_weights = poi_weights or {"CRITICAL":5.0, "COMMERCIAL":3.0, "OTHER":1.0}
    pop_buf_m = poi_buffer_m if pop_buffer_m is None else float(pop_buffer_m)

    feats_out = []
    for idx, (g, props) in enumerate(rural_fc):
        if g.geom_type != "LineString":
            continue

        dist_conn_m = _min_endpoint_dist_to_paved_m(g, paved_union_3857) if paved_union_3857 is not None else None
        bridge = _bridge_flag(g, paved_union_3857) if paved_union_3857 is not None else 0.0
        touch  = _touch_paved(g, paved_union_3857) if paved_union_3857 is not None else 0
        prox_m = _prox_obra_m(g, planned_union_3857) if planned_union_3857 is not None else None
        overlap_m, adh_pct = _adh_overlap(g, planned_union_3857, buffer_m=adh_buffer_m) if planned_union_3857 is not None else (None, None)

        poi_crit = poi_comm = poi_other = None
        poi_weighted = poi_w_per_km = None
        if pois_fc:
            poi_crit, poi_comm, poi_other, poi_weighted, poi_w_per_km = _poi_weighted(
                g, pois_fc, buffer_m=poi_buffer_m, weights=poi_weights
            )

        pop_attended = pop_per_km = None
        if pop_grid_fc or res_pts_fc:
            pop_attended, pop_per_km = _pop_proxy(
                g,
                pop_grid_fc=pop_grid_fc,
                pop_grid_field=pop_grid_pop_field,
                res_points_fc=res_pts_fc,
                persons_per_addr=persons_per_addr,
                buffer_m=pop_buf_m
            )

        pr = dict(props or {})
        pr.update({
            "id_idx": idx,
            "len_m": to_3857(g).length,
            "dist_conn_m": dist_conn_m,
            "bridge_flag": bridge,
            "touch_paved": touch,
            "prox_obra_m": prox_m,
            "overlap_m": overlap_m,
            "adh_pct": adh_pct,
            "poi_crit_n": poi_crit,
            "poi_comm_n": poi_comm,
            "poi_other_n": poi_other,
            "poi_weighted": poi_weighted,
            "poi_w_per_km": poi_w_per_km,
            "pop_attended": pop_attended,
            "pop_per_km": pop_per_km,
        })
        if meta_sources:
            pr.update(meta_sources)

        feats_out.append({"type":"Feature","properties":pr,"geometry": mapping(g)})

    _compute_scores(feats_out)

    outdir = Path(outdir); outdir.mkdir(parents=True, exist_ok=True)
    gj = {"type":"FeatureCollection","features":feats_out}
    out_geo = outdir/"rural_priority.geojson"
    write_geojson(gj, out_geo)

    keys = [
        "id_idx","len_m","dist_conn_m","bridge_flag","touch_paved",
        "prox_obra_m","overlap_m","adh_pct",
        "poi_crit_n","poi_comm_n","poi_other_n","poi_weighted","poi_w_per_km",
        "pop_attended","pop_per_km",
        "ICN","ISO","IAX","IPD","prioridade","color_hex",
        "Justificativa_Score_Atendimento","Justificativa_Score_Proximidade"
    ]
    out_csv = outdir/"rural_priority.csv"
    with out_csv.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(keys)
        for ftr in feats_out:
            pr = ftr["properties"]
            writer.writerow([pr.get(k,"") for k in keys])

    return {"geojson": str(out_geo), "csv": str(out_csv), "features": len(feats_out)}
"""

CLI = """
import argparse, json
from pathlib import Path
from pipelines.rural_priority import run_rural_priority

def main():
    p = argparse.ArgumentParser("flows-ia rural priority v2")
    p.add_argument("--rural", required=True, help="GeoJSON/KMZ das estradas rurais (LineString)")
    p.add_argument("--paved", required=True, help="GeoJSON/KMZ da malha pavimentada")
    p.add_argument("--planned", help="GeoJSON/KMZ dos corredores/obras planejadas")
    p.add_argument("--centers", help="GeoJSON/KMZ de centros rurais (Point/Polygon)")
    p.add_argument("--outdir", default="out/rural", help="Pasta de saída")
    p.add_argument("--adh-buffer-m", type=float, default=200.0, help="Buffer (m) para aderência ao corredor")
    p.add_argument("--centers-radius-m", type=float, default=3000.0, help="Raio (m) de influência dos centros rurais")
    p.add_argument("--meta", help="JSON com metadados (ex.: fontes/datas)")

    p.add_argument("--pois", help="GeoJSON/KMZ com POIs (Point/Line/Polygon)")
    p.add_argument("--poi-buffer-m", type=float, default=500.0, help="Buffer (m) para contabilizar POIs ao longo do trecho")
    p.add_argument("--poi-weights", help='JSON de pesos {"CRITICAL":5,"COMMERCIAL":3,"OTHER":1}')

    p.add_argument("--pop-grid", help="GeoJSON de polígonos com campo de população (ex.: pop)")
    p.add_argument("--pop-grid-pop-field", help="Campo de população no pop-grid (ex.: pop)")
    p.add_argument("--res-points", help="GeoJSON de pontos residenciais (amostra de endereços)")
    p.add_argument("--persons-per-addr", type=float, default=3.0, help="Pessoas por endereço (proxy)")
    p.add_argument("--pop-buffer-m", type=float, help="Buffer (m) para população (se vazio, usa o mesmo dos POIs)")

    a = p.parse_args()
    meta = json.loads(a.meta) if a.meta else None
    poi_weights = json.loads(a.poi_weights) if a.poi_weights else None

    out = run_rural_priority(
        rural_path=Path(a.rural),
        urban_paved_path=Path(a.paved),
        planned_corridors_path=Path(a.planned) if a.planned else None,
        rural_centers_path=Path(a.centers) if a.centers else None,
        outdir=Path(a.outdir),
        adh_buffer_m=a.adh_buffer_m,
        centers_radius_m=a.centers_radius_m,
        meta_sources=meta,
        pois_path=Path(a.pois) if a.pois else None,
        poi_buffer_m=a.poi_buffer_m,
        poi_weights=poi_weights,
        pop_grid_path=Path(a.pop_grid) if a.pop_grid else None,
        pop_grid_pop_field=a.pop_grid_pop_field,
        res_points_path=Path(a.res_points) if a.res_points else None,
        persons_per_addr=a.persons_per_addr,
        pop_buffer_m=a.pop_buffer_m
    )
    print(json.dumps(out, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
"""

RUNNER = """
# run_rural.py
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).parent / "src"))
from cli_rural.__main__ import main

if __name__ == "__main__":
    main()
"""

README_APPEND = """
## Prioridade Rural v2 (ICN + ISO + IAX)
Calcula ranking de estradas rurais combinando:
- **ICN**: distância de conexão, ponte de ligação, continuidade
- **ISO**: proximidade e aderência a corredor/obra planejada
- **IAX**: exposição/atendimento (POIs ponderados + população proxy)

### Executar sem PYTHONPATH (recomendado)
```bash
python run_rural.py   --rural data/rural_roads.geojson   --paved data/urban_paved.geojson   --planned data/corredores_planejados.geojson   --pois data/pois.geojson   --poi-buffer-m 500   --poi-weights '{"CRITICAL":5,"COMMERCIAL":3,"OTHER":1}'   --pop-grid data/pop_grid.geojson   --pop-grid-pop-field pop   --outdir out/rural
```

### Alternativa (com PYTHONPATH)
```bash
PYTHONPATH=src python -m cli_rural   --rural data/rural_roads.geojson   --paved data/urban_paved.geojson   --planned data/corredores_planejados.geojson   --pois data/pois.geojson   --poi-buffer-m 500   --poi-weights '{"CRITICAL":5,"COMMERCIAL":3,"OTHER":1}'   --pop-grid data/pop_grid.geojson   --pop-grid-pop-field pop   --outdir out/rural
```

Saídas: `out/rural/rural_priority.geojson` e `out/rural/rural_priority.csv`
"""

def write_all():
    ensure_dirs()
    write(ROOT/"src/utils/geoio.py", GEOIO)
    write(ROOT/"src/utils/geomath.py", GEOMATH)
    write(ROOT/"src/utils/norm.py", NORM)
    write(ROOT/"src/utils/poi_weights.py", POI_WEIGHTS)
    write(ROOT/"src/pipelines/rural_priority.py", PIPELINE)
    write(ROOT/"src/cli_rural/__main__.py", CLI)
    write(ROOT/"run_rural.py", RUNNER)
    append_or_create(ROOT/"README.md", README_APPEND)
    update_requirements(minimal=True)

    # Documento técnico com código embutido
    sections = []
    sections.append(f"# ENTREGA – Prioridade Rural v2 (ICN + ISO + IAX)\n_Gerado em {datetime.datetime.utcnow().isoformat()}Z_\n")
    sections.append("## Como executar\nVeja `README.md`.\n")
    def dump(rel):
        p = ROOT/rel
        return f"\n### `{rel}`\n```python\n{slurp(p)}\n```\n"
    for rel in [
        "src/utils/geoio.py",
        "src/utils/geomath.py",
        "src/utils/norm.py",
        "src/utils/poi_weights.py",
        "src/pipelines/rural_priority.py",
        "src/cli_rural/__main__.py",
    ]:
        sections.append(dump(rel))
    (ROOT/"ENTREGA_RURAL_v2.md").write_text("".join(sections), encoding="utf-8")

def main():
    write_all()
    z = build_zip()
    print("=== OK ===")
    print("ZIP final:", z)
    print("Doc:", (ROOT/"ENTREGA_RURAL_v2.md"))

if __name__ == "__main__":
    main()
