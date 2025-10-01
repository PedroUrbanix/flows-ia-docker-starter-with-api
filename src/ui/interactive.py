# src/ui/interactive.py
from rich.table import Table
from rich.console import Console

console = Console()

def print_layers(layers):
    table = Table(title=f"Camadas encontradas ({len(layers)})")
    table.add_column("#", justify="right", style="cyan", no_wrap=True)
    table.add_column("Layer")
    table.add_column("Geometry")
    table.add_column("Service")
    for i, item in enumerate(layers, start=1):
        svc = item["service"]
        ly = item["layer"]
        disp = f"{ly['name']}"
        service_name = f"{svc.get('name')} [{svc.get('type')}]"
        table.add_row(str(i), disp, ly.get("geometryType") or "-", service_name)
    console.print(table)

def parse_exclusions(s:str, n:int):
    # ex.: "1,5-9,12"
    s = s.strip()
    if not s: return set()
    out = set()
    for part in s.split(","):
        part = part.strip()
        if "-" in part:
            a,b = part.split("-",1)
            try:
                a=int(a); b=int(b)
                for k in range(a,b+1):
                    if 1<=k<=n: out.add(k)
            except: pass
        else:
            try:
                k=int(part)
                if 1<=k<=n: out.add(k)
            except: pass
    return out

def interactive_filter_and_download(found):
    current = list(found)
    while True:
        print_layers(current)
        console.print("[bold]Digite números/intervalos para EXCLUIR (ex.: 1,5-9) e ENTER para aplicar.")
        console.print("[bold]Ou tecle ENTER vazio para não excluir agora; 'd' para baixar; 'q' para sair.")
        s = input("> ").strip().lower()
        if s == "q":
            return []
        if s == "d" or s == "download":
            return current
        if not s:
            # sem exclusão, continua mostrando novamente
            continue
        # aplica exclusões
        exc = parse_exclusions(s, len(current))
        if not exc:
            console.print("[yellow]Nenhum índice válido informado.[/yellow]")
            continue
        current = [it for idx, it in enumerate(current, start=1) if idx not in exc]
        console.print(f"[green]Excluídos {len(exc)}. Restantes: {len(current)}[/green]")
