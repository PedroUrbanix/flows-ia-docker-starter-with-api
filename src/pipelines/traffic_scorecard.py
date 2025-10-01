from __future__ import annotations

import csv
from pathlib import Path
from typing import Dict, List, Tuple

from .traffic_metrics import run_segment


def fmt_pct(value: float | None) -> str:
    try:
        return f"{round(100 * float(value))}%"
    except (TypeError, ValueError):
        return "0%"


def score_priority(tti: float, pct_slow_jam: float, delay_min: float) -> Tuple[str, float]:
    tti_n = max(0.0, min((float(tti) - 1.0) / 1.5, 1.0))
    slow_n = max(0.0, min(float(pct_slow_jam), 1.0))
    delay_n = max(0.0, min(float(delay_min) / 10.0, 1.0))
    score = 0.45 * tti_n + 0.35 * slow_n + 0.20 * delay_n
    label = "ALTA" if score >= 0.66 else ("MEDIA" if score >= 0.33 else "BAIXA")
    return label, score


def row_from_segment(name: str, relevance_txt: str, seg: Dict) -> Dict:
    duration_s = float(seg.get("duration_s") or 0.0)
    static_s = float(seg.get("static_s") or duration_s)
    distance_m = float(seg.get("distance_m") or 0.0)
    tti = float(seg.get("TTI") or 0.0)
    delay_s = max(0.0, duration_s - static_s)
    delay_per_km = delay_s / max(1e-6, distance_m / 1000.0)
    pct_slow = float(seg.get("pct_slow") or 0.0)
    pct_jam = float(seg.get("pct_jam") or 0.0)
    pct_slow_jam = pct_slow + pct_jam
    label, _ = score_priority(tti, pct_slow_jam, delay_s / 60.0)
    return {
        "Via": name,
        "Relevancia": relevance_txt or "n/d",
        "TTI Medio (agora)": (
            f"{round(tti, 2)} (trip takes {round((tti - 1) * 100)}% more time)"
            if tti
            else "n/d"
        ),
        "Atraso por km": f"{round(delay_per_km):.0f} s/km" if delay_s > 0 else "0 s/km",
        "% do Trecho Congestionado": f"{fmt_pct(pct_slow_jam)} classificado como SLOW/JAM",
        "Potencial de Reducao de Tempo": f"{round(delay_s / 60)} minutos",
        "Score de Prioridade": label,
    }


def to_markdown_table(rows: List[Dict]) -> str:
    vias = [r["Via"] for r in rows]
    fields = [
        "Relevancia",
        "TTI Medio (agora)",
        "Atraso por km",
        "% do Trecho Congestionado",
        "Potencial de Reducao de Tempo",
        "Score de Prioridade",
    ]
    md = ["| Metrica | " + " | ".join(vias) + " |", "|:--| " + " | ".join([":--" for _ in vias]) + " |"]
    for field in fields:
        row = [field] + [r.get(field, "n/d") for r in rows]
        md.append("| " + " | ".join(row) + " |")
    return "\n".join(md)


def save_csv(rows: List[Dict], out_csv: Path):
    keys = list(rows[0].keys())
    with out_csv.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=keys)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, "") for k in keys})


def run_scorecard(api_key: str, candidates: List[Dict], outdir: Path) -> Dict:
    outdir.mkdir(parents=True, exist_ok=True)
    result_rows = []
    for candidate in candidates:
        segment = run_segment(
            api_key=api_key,
            origin=candidate["origin"],
            destination=candidate["destination"],
            outdir=outdir,
        )
        result_rows.append(
            row_from_segment(
                name=candidate["name"],
                relevance_txt=candidate.get("relevance", "n/d"),
                seg=segment,
            )
        )
    markdown = to_markdown_table(result_rows)
    out_md = outdir / "scorecard.md"
    out_md.write_text(markdown, encoding="utf-8")
    out_csv = outdir / "scorecard.csv"
    save_csv(result_rows, out_csv)
    return {"markdown": str(out_md), "csv": str(out_csv), "rows": result_rows}
