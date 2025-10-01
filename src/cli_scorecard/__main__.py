import argparse
import json
import os
from pathlib import Path

from ..pipelines.traffic_scorecard import run_scorecard


def parse_ll(value: str):
    lat, lon = [float(coord.strip()) for coord in value.split(",", 1)]
    return {"latitude": lat, "longitude": lon}


def build_quick_examples():
    return [
        {
            "name": "Via Candidata A",
            "origin": parse_ll("-25.441,-49.276"),
            "destination": parse_ll("-25.428,-49.270"),
            "relevance": "Atende uma escola e 300 residencias",
        },
        {
            "name": "Via Candidata B",
            "origin": parse_ll("-25.452,-49.300"),
            "destination": parse_ll("-25.446,-49.287"),
            "relevance": "Acesso a duas areas rurais",
        },
    ]


def main():
    parser = argparse.ArgumentParser("flows-ia scorecard")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--candidates-json", help="JSON com candidatos (lista de objetos)")
    group.add_argument("--quick", action="store_true", help="Modo rapido com 2 exemplos")
    parser.add_argument(
        "--outdir",
        default="out/traffic",
        help="Pasta de saida",
    )
    parser.add_argument(
        "--api-key",
        default=os.getenv("GOOGLE_MAPS_API_KEY"),
        help="Google Maps API key (ou defina GOOGLE_MAPS_API_KEY no .env)",
    )
    args = parser.parse_args()

    if not args.api_key:
        raise SystemExit("Faltou GOOGLE_MAPS_API_KEY (ou passe --api-key).")

    if args.quick:
        candidates = build_quick_examples()
    else:
        candidates = json.loads(args.candidates_json)

    out = run_scorecard(api_key=args.api_key, candidates=candidates, outdir=Path(args.outdir))
    print(f"\nScorecard gerado:\n- {out['markdown']}\n- {out['csv']}\n")


if __name__ == "__main__":
    main()
