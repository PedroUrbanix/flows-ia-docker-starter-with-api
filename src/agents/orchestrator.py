from __future__ import annotations

from ..common.utils import log


class Orchestrator:
    def __init__(self, tools):
        self.t = tools

    async def run_city(self, municipio: str, uf: str):
        log(f"[discover] {municipio}-{uf}")
        seeds = await self.t.search_agent(municipio, uf)

        log("[classify] cataloguing sources")
        catalog = await self.t.classify_sources(seeds)

        log("[ingest] collecting raw datasets")
        raw = await self.t.ingest(catalog)

        log("[normalize] harmonising schemas")
        norm = await self.t.normalize(raw)

        log("[enrich] overlaying reference layers")
        enr = await self.t.enrich(norm)

        log("[export] writing artefacts")
        outputs = await self.t.export(enr, municipio)

        log("[qa] running validation and metadata export")
        qa = await self.t.qa(outputs)
        await self.t.write_metadata(outputs, qa, municipio, uf)
        return outputs
