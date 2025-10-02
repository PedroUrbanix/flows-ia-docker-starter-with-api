
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
