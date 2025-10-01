# flows-api-crawler

CLI para **descobrir camadas geográficas** (ArcGIS REST) por **município + UF**, listar **todas** as camadas,
permitir que você **exclua** interativamente e então **baixar** tudo em **GeoJSON** (e opcionalmente **KMZ**).

- Descoberta determinística (padrões de domínio) + opcional **IA** para sugerir outros endpoints.
- Crawler entra em **cada serviço** e **cada layer** (`MapServer`/`FeatureServer`), de **todas as pastas**.
- Deduplica layers repetidos (por nome + geometryType + assinatura de campos).

## Como rodar (Docker)
```bash
cp .env.example .env   # opcional: preencha OPENAI_API_KEY para modo 'ai'
docker compose build

# Modo interativo (crawler completo)
docker compose run --rm app python -m cli discover   --city "Londrina" --state "PR"   --mode catalog,ai   --outputs geojson   --outdir out
```

No modo interativo, o terminal mostra **todas as camadas** encontradas e pede:
- Digite **números/intervalos** para excluir (ex.: `1,5-9`), ou pressione **ENTER** para continuar sem excluir.
- Digite **d** para baixar, **q** para sair.
- Você pode iterar: excluir mais → listar novamente → baixar.

## Como rodar (local)
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export PYTHONPATH=src
# opcional: export OPENAI_API_KEY="sua_key"
python -m cli discover --city "Londrina" --state "PR" --mode catalog,ai --outputs geojson --outdir out
```

### Parâmetros
- `--city`, `--state` (UF) **obrigatórios**
- `--mode`: `catalog`, `ai` (pode ambos)
- `--outputs`: `geojson` (e futuramente `kmz`)
- `--outdir`: pasta de saída
- `--roots`: lista de URLs raiz de ArcGIS REST (se quiser passar explicitamente)

### Observações
- **Catálogo** inclui raiz conhecida de Londrina (`https://geo.londrina.pr.gov.br/server/rest/services`).
- **IA** tenta propor outras raízes; só entra o que **responder 200 e pjson válido**.
- O download usa paginação `resultOffset` quando o layer indica `maxRecordCount`/`exceededTransferLimit`.
