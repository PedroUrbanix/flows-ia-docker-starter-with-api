
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
