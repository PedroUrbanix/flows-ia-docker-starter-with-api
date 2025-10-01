# Combined CLI (ingest + discover) always registered; async-aware dispatcher
import argparse, sys, inspect, asyncio

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

# soft imports (may fail, we still register subcommands)
INGEST_AVAILABLE = True
DISCOVER_AVAILABLE = True
try:
    from pipelines.ingest_city import run_ingest
except Exception as e:
    INGEST_AVAILABLE = False
    run_ingest = None
try:
    from pipelines.crawl_layers import run_discover_and_download
except Exception as e:
    DISCOVER_AVAILABLE = False
    run_discover_and_download = None

def _call(func, *args, **kwargs):
    if func is None:
        print("Comando indisponível neste build.", file=sys.stderr)
        sys.exit(2)
    if inspect.iscoroutinefunction(func):
        return asyncio.run(func(*args, **kwargs))
    res = func(*args, **kwargs)
    if inspect.iscoroutine(res):
        return asyncio.run(res)
    return res

def main():
    p = argparse.ArgumentParser("flows-ia")
    sub = p.add_subparsers(dest="cmd", required=True)

    # sempre registra 'ingest' (mesmo se indisponível); erro só na execução
    f = sub.add_parser("ingest", help="Ingestão por catálogo (educação/saúde/assistência/base)")
    f.add_argument("--city", required=True)
    f.add_argument("--state", required=True)
    f.add_argument("--outputs", default="geojson,kmz")
    f.add_argument("--mode", default="catalog,ai")
    f.add_argument("--what", default="core")
    f.add_argument("--outdir", default="out")
    f.add_argument("--interactive", action="store_true",
                   help="(opcional) listar fontes e excluir por índices antes de baixar")

    d = sub.add_parser("discover", help="Crawler interativo: lista todas as camadas ArcGIS e permite excluir")
    d.add_argument("--city", required=True)
    d.add_argument("--state", required=True)
    d.add_argument("--mode", default="catalog,ai")
    d.add_argument("--outputs", default="geojson")
    d.add_argument("--outdir", default="out")
    d.add_argument("--roots", default="")

    args = p.parse_args()
    if args.cmd == "ingest":
        if not INGEST_AVAILABLE:
            print("Ingest indisponível: falha ao importar pipelines.ingest_city.run_ingest.", file=sys.stderr)
            sys.exit(2)
        return _call(run_ingest,
            city=args.city, state=args.state,
            outputs=[x.strip() for x in args.outputs.split(",") if x.strip()],
            modes=[x.strip() for x in args.mode.split(",") if x.strip()],
            what=args.what, outdir=args.outdir,
            interactive=getattr(args, "interactive", False),
        )
    else:
        if not DISCOVER_AVAILABLE:
            print("Discover indisponível: falha ao importar pipelines.crawl_layers.run_discover_and_download.", file=sys.stderr)
            sys.exit(2)
        return _call(run_discover_and_download,
            city=args.city, state=args.state,
            modes=[x.strip() for x in args.mode.split(",") if x.strip()],
            outputs=[x.strip() for x in args.outputs.split(",") if x.strip()],
            outdir=args.outdir,
            roots=[x.strip() for x in args.roots.split(",") if x.strip()],
        )

if __name__ == "__main__":
    main()
