from __future__ import annotations
import asyncio
import typer
from agents.orchestrator import Orchestrator
from common.tools import Tools
from common.utils import log

app = typer.Typer(help="CLI do pipeline IA – Fluxo de Pessoas (UrbaniX Group)")

@app.command()
def run(
    city: str = typer.Option(..., "--city", help="Nome do município, ex.: Londrina"),
    uf: str = typer.Option(..., "--uf", help="UF, ex.: PR"),
    discover: bool = typer.Option(False, "--discover", help="Executa apenas a descoberta de fontes"),
    ingest: bool = typer.Option(False, "--ingest", help="Executa ingestão das fontes descobertas"),
    all: bool = typer.Option(False, "--all", help="Executa pipeline completo (quando implementado)"),
):
    """Executa o pipeline para a cidade/UF informados."""
    async def _run():
        tools = Tools()
        orch = Orchestrator(tools)
        if discover or ingest or all:
            log(f"Iniciando pipeline para {city}-{uf}")
        if discover:
            seeds = await tools.search_agent(city, uf)
            print({"stage": "DISCOVER", "results": len(seeds)})
        if ingest:
            catalog = await tools.classify_sources([])  # TODO: passar seeds reais
            raw = await tools.ingest(catalog)
            print({"stage": "INGEST", "items": len(raw) if raw else 0})
        if all:
            outputs = await orch.run_city(city, uf)
            print({"stage": "DONE", "outputs": outputs})
    asyncio.run(_run())

if __name__ == "__main__":
    app()