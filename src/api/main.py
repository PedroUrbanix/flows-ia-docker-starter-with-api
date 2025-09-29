from __future__ import annotations
import asyncio
from fastapi import FastAPI
from pydantic import BaseModel
from agents.orchestrator import Orchestrator
from common.tools import Tools

app = FastAPI(title="flows-ia API", version="0.1.0")

class RunRequest(BaseModel):
    city: str
    uf: str
    discover: bool = False
    ingest: bool = False
    all: bool = True

@app.get("/health")
def health():
    return {"status": "ok", "version": "0.1.0"}

@app.post("/run")
def run(req: RunRequest):
    async def _run():
        tools = Tools()
        orch = Orchestrator(tools)
        if req.all:
            return await orch.run_city(req.city, req.uf)
        seeds = await tools.search_agent(req.city, req.uf) if req.discover else []
        catalog = await tools.classify_sources(seeds) if req.ingest else {}
        return {"seeds": len(seeds), "catalog": bool(catalog)}
    return asyncio.run(_run())