from __future__ import annotations

import argparse
import asyncio

from .agents.orchestrator import Orchestrator
from .common.tools import Tools


async def run_pipeline(city: str, state: str) -> None:
    tools = Tools()
    orchestrator = Orchestrator(tools)
    results = await orchestrator.run_city(city, state)
    print("Pipeline completed.")
    if results:
        print("Outputs:")
        for key, value in results.items():
            print(f"- {key}: {value}")


def main() -> None:
    parser = argparse.ArgumentParser("flows-ia main entrypoint")
    parser.add_argument("--city", required=True, help="Municipality name")
    parser.add_argument("--state", required=True, help="State/UF code")
    args = parser.parse_args()

    asyncio.run(run_pipeline(city=args.city, state=args.state))


if __name__ == "__main__":
    main()
