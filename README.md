# flows-ia (Docker starter)

Infra básica para rodar o pipeline de **Fluxo de Pessoas** (UrbaniX Group) em Docker.
Inclui: CLI, API (FastAPI), CI (GitHub Actions) e opção de imagem GPU.

## Uso rápido
```bash
# 1) Ajuste o .env
cp .env.example .env

# 2) (opcional) Cidade/UF padrão
export CITY="Londrina"; export UF="PR"

# 3) Build
docker compose build

# 4) Ajuda do CLI
docker compose run --rm app python -m cli --help

# 5) Rodar DISCOVER+INGEST
docker compose run --rm app python -m cli run --city "${CITY:-Londrina}" --uf "${UF:-PR}" --discover --ingest

# 6) Subir API
docker compose up -d api
curl http://localhost:8000/health
curl -X POST http://localhost:8000/run -H 'Content-Type: application/json' -d '{"city":"Londrina","uf":"PR","all":true}'
```

Saídas: `./outputs/<cidade>/YYYY-MM-DD/` • Dados brutos: `./data/` • Config: `./config/`.

> **Avisos**: Onde não houver dado oficial (ex.: GTFS), o sistema **marcará ESPECULAÇÃO**. Sempre registrar fonte/URL/data/licença no `METADATA.json`.