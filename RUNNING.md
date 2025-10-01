# Running flows-ia

This guide focuses on executing the project end-to-end, either from the new `main.py` entrypoint, the CLI module, or the API container.

## 1. Requirements
- Python 3.11+
- `pip install -r requirements.txt`
- Populate `.env` from `.env.example` with valid API keys (OpenAI and Google Maps).

## 2. Main Entrypoint
Run the orchestrator straight from the repository root:
```bash
python -m src.main --city "Londrina" --state "PR"
```
This will execute all pipeline stages defined in `Orchestrator`.

## 3. CLI Module
The CLI offers additional knobs (outputs, modes, etc.):
```bash
python -m src.cli --city "Londrina" --state "PR" --mode catalog,ai --outputs geojson,kmz
```

## 4. Traffic Scorecard
Generate traffic reports (requires Google Maps API key):
```bash
python -m src.cli_scorecard --quick --outdir out/traffic
```

## 5. Docker (Optional)
```bash
cp .env.example .env
CITY=Londrina UF=PR docker compose run --rm app python -m src.cli --city "$CITY" --state "$UF"
docker compose up -d api
```
Access the API at `http://localhost:8000` (health at `/health`, ingestion via POST `/run`).
