from __future__ import annotations
from common.utils import log

class Orchestrator:
    def __init__(self, tools):
        self.t = tools

    async def run_city(self, municipio: str, uf: str):
        log(f"▶ DISCOVER {municipio}-{uf}")
        seeds = await self.t.search_agent(municipio, uf)
        catalog = await self.t.classify_sources(seeds)

        log("▶ INGEST")
        raw = await self.t.ingest(catalog)

        log("▶ NORMALIZE")
        norm = await self.t.normalize(raw)

        log("▶ ENRICH (overlay)")
        enr = await self.t.enrich(norm)

        log("▶ EXPORT")
        outputs = await self.t.export(enr, municipio)

        log("▶ QA & REPORT")
        qa = await self.t.qa(outputs)
        await self.t.write_metadata(outputs, qa, municipio, uf)
        return outputs