import os, json, asyncio, requests

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

PROMPT_SOURCES = """
Você é um assistente que sugere endpoints públicos de camadas geoespaciais (ArcGIS REST /query)
para um município brasileiro. Responda APENAS em JSON válido no formato:

{{"sources":[
  {{"name":"slug_simples","type":"arcgis_query","url":"https://.../MapServer/0/query",
    "params":{{"where":"1=1","outFields":"*","returnGeometry":"true","outSR":"4326","f":"geojson"}}}}
]}}

Regra: só traga endpoints plausíveis/públicos (sem credenciais), priorizando o eixo {what}.
Município: {city} - {state}.
"""

PROMPT_ROOTS = """
Você é um assistente que sugere **URLs raiz** de ArcGIS REST para um município brasileiro.
Responda APENAS em JSON válido:

{{"roots":[
  "https://<dominio>/server/rest/services",
  "https://<dominio>/arcgis/rest/services"
]}}

Município: {city} - {state}. Traga 1–5 candidatos plausíveis.
"""

def _post_openai(payload: dict) -> dict:
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json",
    }
    r = requests.post("https://api.openai.com/v1/chat/completions",
                      headers=headers, json=payload, timeout=60)
    r.raise_for_status()
    return r.json()

def _safe_parse_json_block(content: str):
    content = (content or "").strip()
    try:
        return json.loads(content)
    except Exception:
        pass
    try:
        start = content.index("{")
        end = content.rindex("}") + 1
        return json.loads(content[start:end])
    except Exception:
        return None

async def ai_discover_sources(city: str, state: str, what: str = "core") -> list[dict]:
    if not OPENAI_API_KEY:
        return []
    prompt = PROMPT_SOURCES.format(city=city, state=state, what=what)
    payload = {
        "model": "gpt-4o-mini",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.2,
    }
    try:
        data = await asyncio.to_thread(_post_openai, payload)
    except Exception as e:
        print(f"[warn] ai_discover_sources: {e}")
        return []
    content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
    js = _safe_parse_json_block(content) or {}
    raw = js.get("sources") or []
    out = []
    for s in raw:
        if isinstance(s, dict) and s.get("type") == "arcgis_query" and s.get("url"):
            params = s.get("params") or {
                "where": "1=1",
                "outFields": "*",
                "returnGeometry": "true",
                "outSR": "4326",
                "f": "geojson",
            }
            out.append({
                "name": s.get("name") or "descoberto_ai",
                "type": "arcgis_query",
                "url": s["url"],
                "params": params,
            })
    return out

async def ai_discover_arcgis_roots(city: str, state: str) -> list[str]:
    if not OPENAI_API_KEY:
        return []
    prompt = PROMPT_ROOTS.format(city=city, state=state)
    payload = {
        "model": "gpt-4o-mini",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.2,
    }
    try:
        data = await asyncio.to_thread(_post_openai, payload)
    except Exception as e:
        print(f"[warn] ai_discover_arcgis_roots: {e}")
        return []
    content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
    js = _safe_parse_json_block(content) or {}
    roots = js.get("roots") or []
    return [r for r in roots if isinstance(r, str) and r.strip()]

# ---- Compat: versões síncronas para código que não usa await ----

def ai_discover_sources_sync(city: str, state: str, what: str = "core") -> list[dict]:
    try:
        return asyncio.run(ai_discover_sources(city, state, what))
    except RuntimeError:
        # já existe loop; roda em thread
        return asyncio.get_event_loop().run_until_complete(ai_discover_sources(city, state, what))

def ai_discover_arcgis_roots_sync(city: str, state: str) -> list[str]:
    try:
        return asyncio.run(ai_discover_arcgis_roots(city, state))
    except RuntimeError:
        return asyncio.get_event_loop().run_until_complete(ai_discover_arcgis_roots(city, state))
