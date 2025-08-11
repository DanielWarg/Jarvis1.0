from __future__ import annotations

import asyncio
import time
import json
import os
from datetime import datetime
from typing import Any, AsyncGenerator, Dict, Optional, Set, List

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import ORJSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import logging
from dotenv import load_dotenv
import httpx
import httpx

from .memory import MemoryStore
from .decision import EpsilonGreedyBandit, simulate_first
from .training import stream_dataset


load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("jarvis")

app = FastAPI(title="Jarvis 2.0 Backend", version="0.1.0", default_response_class=ORJSONResponse)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
os.makedirs(DATA_DIR, exist_ok=True)
MEMORY_PATH = os.path.join(DATA_DIR, "jarvis.db")
memory = MemoryStore(MEMORY_PATH)
bandit = EpsilonGreedyBandit(memory)


class JarvisCommand(BaseModel):
    type: str = Field(..., description="Command type, e.g., SHOW_MODULE, HIDE_OVERLAY, OPEN_VIDEO")
    payload: Optional[Dict[str, Any]] = None


class JarvisResponse(BaseModel):
    ok: bool
    message: str
    ts: str = Field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    command: Optional[JarvisCommand] = None


@app.get("/api/health")
async def health() -> Dict[str, Any]:
    return {"status": "ok", "db": memory.ping(), "ts": datetime.utcnow().isoformat() + "Z"}


@app.post("/api/jarvis/command", response_model=JarvisResponse)
async def jarvis_command(cmd: JarvisCommand) -> JarvisResponse:
    # Persist basic interaction for future learning
    memory.append_event("command", json.dumps(cmd.dict(), ensure_ascii=False))
    # Extra: spara USER_QUERY som textminne
    try:
        if (cmd.type or "").upper() == "USER_QUERY":
            q = (cmd.payload or {}).get("query", "")
            if q:
                memory.upsert_text_memory(q, score=0.0, tags_json=json.dumps({"source": "user_query"}, ensure_ascii=False))
    except Exception:
        pass
    # simulate-first risk gating
    scores = simulate_first(cmd.dict())
    logger.info("/api/jarvis/command type=%s risk=%.3f", cmd.type, scores.get("risk", 1.0))
    if scores.get("risk", 1.0) > 0.8:
        return JarvisResponse(ok=False, message="Command blocked by safety", command=cmd)
    # Optional WS broadcast for HUD when receiving explicit dispatch commands
    try:
        ctype = (cmd.type or "").lower()
        if ctype in {"dispatch", "hud"} and isinstance(cmd.payload, dict):
            logger.info("broadcasting hud_command via WS")
            await hub.broadcast({"type": "hud_command", "command": cmd.payload})
    except Exception:
        logger.exception("ws broadcast failed")
    return JarvisResponse(ok=True, message="Command received", command=cmd)


class ToolPickBody(BaseModel):
    candidates: List[str]


@app.post("/api/decision/pick_tool")
async def pick_tool(body: ToolPickBody) -> Dict[str, Any]:
    choice = bandit.pick(body.candidates)
    return {"ok": True, "tool": choice}


class ChatBody(BaseModel):
    prompt: str
    model: Optional[str] = "gpt-oss:20b"
    stream: Optional[bool] = False
    provider: Optional[str] = "auto"  # 'local' | 'openai' | 'auto'


@app.post("/api/chat")
async def chat(body: ChatBody) -> Dict[str, Any]:
    logger.info("/api/chat model=%s prompt_len=%d", body.model, len(body.prompt or ""))
    # Minimal RAG: hämta relevanta textminnen via LIKE och inkludera i prompten
    try:
        contexts = memory.retrieve_text_memories(body.prompt, limit=5)
    except Exception:
        contexts = []
    ctx_text = "\n".join([f"- {it.get('text','')}" for it in (contexts or []) if it.get('text')])
    full_prompt = (
        ("Relevanta minnen:\n" + ctx_text + "\n\n") if ctx_text else ""
    ) + f"Använd relevant kontext ovan vid behov. Besvara på svenska.\n\nFråga: {body.prompt}\nSvar:"
    try:
        memory.append_event("chat.in", json.dumps({"prompt": body.prompt}, ensure_ascii=False))
    except Exception:
        pass
    # Välj provider
    provider = (body.provider or "auto").lower()
    last_error = None
    async def respond(text: str) -> Dict[str, Any]:
        mem_id: Optional[int] = None
        try:
            tags = {"source": "chat", "model": body.model or "gpt-oss:20b", "provider": provider}
            mem_id = memory.upsert_text_memory(text, score=0.0, tags_json=json.dumps(tags, ensure_ascii=False))
            memory.append_event("chat.out", json.dumps({"text": text, "memory_id": mem_id}, ensure_ascii=False))
        except Exception:
            pass
        return {"ok": True, "text": text, "memory_id": mem_id}

    # 1) Lokal (Ollama)
    async def try_local():
        try:
            t0 = time.time()
            async with httpx.AsyncClient(timeout=20.0) as client:
                r = await client.post(
                    "http://127.0.0.1:11434/api/generate",
                    json={
                        "model": body.model or os.getenv("LOCAL_MODEL", "gpt-oss:20b"),
                        "prompt": full_prompt,
                        "stream": False,
                        "options": {"num_predict": 256, "temperature": 0.3},
                    },
                )
                if r.status_code == 200:
                    data = r.json()
                    dt = (time.time() - t0) * 1000
                    logger.info("chat local ms=%.0f", dt)
                    return await respond(data.get("response", ""))
        except Exception as e:
            return e
        return RuntimeError("local_failed")

    # 2) OpenAI
    async def try_openai():
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            return RuntimeError("openai_key_missing")
        try:
            t0 = time.time()
            async with httpx.AsyncClient(timeout=25.0) as client:
                r = await client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={"Authorization": f"Bearer {api_key}"},
                    json={
                        "model": os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
                        "messages": [
                            {"role": "system", "content": "Du är Jarvis. Svara på svenska och använd 'Relevanta minnen' om de hjälper."},
                            {"role": "user", "content": full_prompt},
                        ],
                        "temperature": 0.5,
                        "max_tokens": 256,
                    },
                )
                if r.status_code == 200:
                    data = r.json()
                    text = ((data.get("choices") or [{}])[0].get("message") or {}).get("content", "")
                    dt = (time.time() - t0) * 1000
                    logger.info("chat openai ms=%.0f", dt)
                    return await respond(text)
        except Exception as e:
            return e
        return RuntimeError("openai_failed")

    try:
        if provider == "local":
            res = await try_local()
            if isinstance(res, dict):
                return res
            last_error = res
        elif provider == "openai":
            res = await try_openai()
            if isinstance(res, dict):
                return res
            last_error = res
        else:  # auto: race local vs openai
            t_local = asyncio.create_task(try_local())
            t_openai = asyncio.create_task(try_openai())
            done, pending = await asyncio.wait({t_local, t_openai}, return_when=asyncio.FIRST_COMPLETED)
            for d in done:
                res = d.result()
                if isinstance(res, dict):
                    # cancel the slower one
                    for p in pending:
                        p.cancel()
                    return res
                last_error = res
            # if first completed wasn't dict, wait the other
            for p in pending:
                try:
                    res = await p
                    if isinstance(res, dict):
                        return res
                    last_error = res
                except asyncio.CancelledError:
                    pass
    except Exception:
        logger.exception("/api/chat error")
    # Stub: visa vilken kontext som skulle ha använts, för verifiering i UI
    stub_ctx = ("\n\n[Kontext]\n" + ctx_text) if ctx_text else ""
    return {"ok": True, "text": f"[stub] {body.prompt}{stub_ctx}", "memory_id": None}


class ActBody(BaseModel):
    prompt: Optional[str] = ""
    model: Optional[str] = "gpt-oss:20b"
    allow: Optional[List[str]] = None  # e.g. ["SHOW_MODULE","HIDE_OVERLAY","OPEN_VIDEO"]
    provider: Optional[str] = "auto"  # 'local' | 'openai' | 'auto'


def _validate_hud_command(cmd: Dict[str, Any], allow: Optional[List[str]] = None) -> Optional[Dict[str, Any]]:
    if not isinstance(cmd, dict):
        return None
    ctype = (cmd.get("type") or "").upper()
    if allow and ctype not in allow:
        return None
    if ctype == "SHOW_MODULE":
        # Normalisera svenska/alias -> interna moduler
        raw = (cmd.get("module") or "").strip().lower()
        alias = {
            "kalender": "calendar",
            "calendar": "calendar",
            "mail": "mail",
            "mejl": "mail",
            "email": "mail",
            "finans": "finance",
            "ekonomi": "finance",
            "finance": "finance",
            "påminnelser": "reminders",
            "paminnelser": "reminders",
            "reminders": "reminders",
            "plånbok": "wallet",
            "planbok": "wallet",
            "wallet": "wallet",
            "video": "video",
        }
        mod = alias.get(raw, raw)
        if mod in {"calendar","mail","finance","reminders","wallet","video"}:
            return {"type": "SHOW_MODULE", "module": mod}
        return None
    if ctype == "HIDE_OVERLAY":
        return {"type": "HIDE_OVERLAY"}
    if ctype == "OPEN_VIDEO":
        src = cmd.get("source") or {"kind": "webcam"}
        if isinstance(src, str):
            src = {"kind": src}
        if isinstance(src, dict):
            return {"type": "OPEN_VIDEO", "source": {"kind": (src.get("kind") or "webcam")}}
    return None


@app.post("/api/ai/act")
async def ai_act(body: ActBody) -> Dict[str, Any]:
    """Be modellen föreslå ett HUD-kommando och sänd via WS (med säkerhetsgrind)."""
    allow = ["SHOW_MODULE","HIDE_OVERLAY","OPEN_VIDEO"] if body.allow is None else body.allow
    instruction = (
        "Du styr ett HUD-UI. Välj ETT av följande kommandon som JSON utan extra text: "
        "SHOW_MODULE{\"module\": one of [calendar,mail,finance,reminders,wallet,video]}, "
        "HIDE_OVERLAY{}, OPEN_VIDEO{\"source\":{\"kind\":\"webcam\"}}. "
        "Svara endast med ett JSON-objekt. På svenska i val av modulnamn går bra.\n"
    )
    user = body.prompt or ""
    full_prompt = f"{instruction}\nAnvändarens önskemål: {user}\nJSON:"
    proposed: Optional[Dict[str, Any]] = None
    # Försök med modell(er)
    provider = (body.provider or "auto").lower()
    import re, json as pyjson
    async def try_local():
        try:
            t0 = time.time()
            async with httpx.AsyncClient(timeout=15.0) as client:
                r = await client.post(
                    "http://127.0.0.1:11434/api/generate",
                    json={
                        "model": body.model or os.getenv("LOCAL_MODEL", "gpt-oss:20b"),
                        "prompt": full_prompt,
                        "stream": False,
                        "options": {"num_predict": 128, "temperature": 0.2},
                    },
                )
                if r.status_code == 200:
                    text = (r.json() or {}).get("response", "")
                    m = re.search(r"\{[\s\S]*\}", text)
                    if m:
                        logger.info("ai_act local ms=%.0f", (time.time()-t0)*1000)
                        return pyjson.loads(m.group(0))
        except Exception:
            return None
        return None
    async def try_openai():
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            return None
        try:
            t0 = time.time()
            async with httpx.AsyncClient(timeout=20.0) as client:
                r = await client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={"Authorization": f"Bearer {api_key}"},
                    json={
                        "model": os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
                        "messages": [
                            {"role": "system", "content": "Svara med ENBART ett JSON-objekt med HUD-kommandot enligt specifikationen."},
                            {"role": "user", "content": full_prompt},
                        ],
                        "temperature": 0.2,
                        "max_tokens": 100,
                    },
                )
                if r.status_code == 200:
                    data = r.json()
                    text = ((data.get("choices") or [{}])[0].get("message") or {}).get("content", "")
                    m = re.search(r"\{[\s\S]*\}", text)
                    if m:
                        logger.info("ai_act openai ms=%.0f", (time.time()-t0)*1000)
                        return pyjson.loads(m.group(0))
        except Exception:
            return None
        return None

    if provider == "local":
        proposed = await try_local()
    elif provider == "openai":
        proposed = await try_openai()
    else:
        # auto: race
        t_local = asyncio.create_task(try_local())
        t_openai = asyncio.create_task(try_openai())
        done, pending = await asyncio.wait({t_local, t_openai}, return_when=asyncio.FIRST_COMPLETED)
        proposed = None
        for d in done:
            val = d.result()
            if val:
                proposed = val
                break
        if proposed is None:
            for p in pending:
                try:
                    val = await p
                    if val:
                        proposed = val
                        break
                except asyncio.CancelledError:
                    pass
    # Fallback: enkel regelbaserad tolkning
    if proposed is None:
        low = (user or "").lower()
        if any(k in low for k in ["stäng", "hide", "close"]):
            proposed = {"type": "HIDE_OVERLAY"}
        elif any(k in low for k in ["video", "kamera"]):
            proposed = {"type": "OPEN_VIDEO", "source": {"kind": "webcam"}}
        elif any(k in low for k in ["kalender", "calendar"]):
            proposed = {"type": "SHOW_MODULE", "module": "calendar"}
        elif any(k in low for k in ["mail", "mejl"]):
            proposed = {"type": "SHOW_MODULE", "module": "mail"}
        else:
            # sista utväg: visa finance som demo
            proposed = {"type": "SHOW_MODULE", "module": "finance"}

    cmd = _validate_hud_command(proposed, allow=allow)
    if not cmd:
        # Sista fallback: härleda från användartext om modellen gav ogiltigt JSON
        low = (user or "").lower()
        heuristic = None
        if any(k in low for k in ["stäng", "hide", "close"]):
            heuristic = {"type": "HIDE_OVERLAY"}
        elif any(k in low for k in ["video", "kamera"]):
            heuristic = {"type": "OPEN_VIDEO", "source": {"kind": "webcam"}}
        elif any(k in low for k in ["kalender", "calendar"]):
            heuristic = {"type": "SHOW_MODULE", "module": "calendar"}
        elif any(k in low for k in ["mail", "mejl", "email"]):
            heuristic = {"type": "SHOW_MODULE", "module": "mail"}
        elif any(k in low for k in ["finans", "ekonomi", "finance"]):
            heuristic = {"type": "SHOW_MODULE", "module": "finance"}
        elif any(k in low for k in ["påminnelser", "paminnelser", "reminders"]):
            heuristic = {"type": "SHOW_MODULE", "module": "reminders"}
        elif any(k in low for k in ["plånbok", "planbok", "wallet"]):
            heuristic = {"type": "SHOW_MODULE", "module": "wallet"}
        if heuristic:
            cmd = _validate_hud_command(heuristic, allow=allow)
    if not cmd:
        return {"ok": False, "error": "invalid_command"}
    # Safety gate
    scores = simulate_first(cmd)
    if scores.get("risk", 1.0) > 0.8:
        return {"ok": False, "error": "blocked_by_safety"}
    try:
        await hub.broadcast({"type": "hud_command", "command": cmd})
        memory.append_event("ai.act", json.dumps({"prompt": user, "command": cmd}, ensure_ascii=False))
    except Exception:
        logger.exception("ai_act broadcast failed")
        return {"ok": False, "error": "broadcast_failed"}
    return {"ok": True, "command": cmd}


class CVIngestBody(BaseModel):
    source: str
    meta: Optional[Dict[str, Any]] = None


@app.post("/api/cv/ingest")
async def cv_ingest(body: CVIngestBody) -> Dict[str, Any]:
    meta_json = json.dumps(body.meta) if body.meta is not None else None
    frame_id = memory.add_cv_frame(body.source, meta_json=meta_json)
    memory.append_event("cv.ingest", json.dumps({"id": frame_id, "source": body.source}))
    return {"ok": True, "id": frame_id}


class SensorBody(BaseModel):
    sensor: str
    value: float
    meta: Optional[Dict[str, Any]] = None


@app.post("/api/sensor/telemetry")
async def sensor_telemetry(body: SensorBody) -> Dict[str, Any]:
    meta_json = json.dumps(body.meta) if body.meta is not None else None
    sid = memory.add_sensor_telemetry(body.sensor, body.value, meta_json=meta_json)
    memory.append_event("sensor.telemetry", json.dumps({"id": sid, "sensor": body.sensor}))
    return {"ok": True, "id": sid}


@app.get("/api/training/dump")
async def training_dump():
    # Stream newline-delimited JSON for offline training pipeline
    async def gen():
        for chunk in stream_dataset(MEMORY_PATH):
            yield chunk
    return ORJSONResponse(gen(), media_type="application/x-ndjson")


class WeatherQuery(BaseModel):
    lat: float
    lon: float


@app.post("/api/weather/current")
async def weather_current(body: WeatherQuery) -> Dict[str, Any]:
    """Proxar Open‑Meteo för enkel väderhämtning utan API‑nyckel."""
    url = (
        "https://api.open-meteo.com/v1/forecast?"\
        f"latitude={body.lat}&longitude={body.lon}&current=temperature_2m,weather_code"
    )
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.get(url)
            r.raise_for_status()
            data = r.json()
            cur = (data or {}).get("current") or {}
            temp = cur.get("temperature_2m")
            code = cur.get("weather_code")
            return {"ok": True, "temperature": temp, "code": code}
    except Exception as e:
        logger.exception("weather fetch failed")
        return {"ok": False, "error": str(e)}


@app.post("/api/weather/openweather")
async def weather_openweather(body: WeatherQuery) -> Dict[str, Any]:
    api_key = os.getenv("OPENWEATHER_API_KEY")
    if not api_key:
        return {"ok": False, "error": "OPENWEATHER_API_KEY missing"}
    url = (
        "https://api.openweathermap.org/data/2.5/weather?"\
        f"lat={body.lat}&lon={body.lon}&units=metric&appid={api_key}"
    )
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.get(url)
            r.raise_for_status()
            data = r.json()
            main = (data or {}).get("main") or {}
            weather = ((data or {}).get("weather") or [{}])[0]
            temp = main.get("temp")
            desc = weather.get("description")
            code = weather.get("id")
            return {"ok": True, "temperature": temp, "code": code, "description": desc}
    except Exception as e:
        logger.exception("openweather fetch failed")
        return {"ok": False, "error": str(e)}


class CityQuery(BaseModel):
    city: str
    provider: Optional[str] = "openmeteo"  # or 'openweather'


@app.post("/api/weather/by_city")
async def weather_by_city(body: CityQuery) -> Dict[str, Any]:
    # Geokoda stadsnamn via Open-Meteo (gratis, ingen nyckel)
    try:
        geo_url = (
            "https://geocoding-api.open-meteo.com/v1/search?"\
            f"name={httpx.QueryParams({'name': body.city})['name']}&count=1&language=sv&format=json"
        )
        async with httpx.AsyncClient(timeout=10.0) as client:
            gr = await client.get(geo_url)
            gr.raise_for_status()
            g = gr.json() or {}
            results = g.get("results") or []
            if not results:
                return {"ok": False, "error": "city_not_found"}
            lat = float(results[0]["latitude"])
            lon = float(results[0]["longitude"])

        # Använd vald provider
        if (body.provider or "").lower() == "openweather":
            return await weather_openweather(WeatherQuery(lat=lat, lon=lon))
        else:
            return await weather_current(WeatherQuery(lat=lat, lon=lon))
    except Exception as e:
        logger.exception("weather by_city failed")
        return {"ok": False, "error": str(e)}


class ReverseQuery(BaseModel):
    lat: float
    lon: float


@app.post("/api/geo/reverse")
async def geo_reverse(body: ReverseQuery) -> Dict[str, Any]:
    """Reverse‑geokoda lat/lon till närmaste platsnamn via Open‑Meteo (gratis)."""
    try:
        url = (
            "https://geocoding-api.open-meteo.com/v1/reverse?"
            f"latitude={body.lat}&longitude={body.lon}&language=sv&format=json"
        )
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.get(url)
            if r.status_code == 200:
                data = r.json() or {}
                results = data.get("results") or []
                if results:
                    top = results[0]
                    return {
                        "ok": True,
                        "city": top.get("name"),
                        "admin1": top.get("admin1"),
                        "admin2": top.get("admin2"),
                        "country": top.get("country"),
                    }
            # Fallback: Nominatim (kräver User-Agent), jsonv2, svenska
            nurl = (
                "https://nominatim.openstreetmap.org/reverse?"
                f"format=jsonv2&lat={body.lat}&lon={body.lon}&accept-language=sv"
            )
            r2 = await client.get(nurl, headers={"User-Agent": "Jarvis/0.1 (+https://example.local)"})
            r2.raise_for_status()
            d2 = r2.json() or {}
            addr = d2.get("address") or {}
            city = addr.get("city") or addr.get("town") or addr.get("village") or addr.get("municipality")
            if not city:
                city = addr.get("county") or addr.get("state") or addr.get("country")
            return {
                "ok": True,
                "city": city,
                "admin1": addr.get("state"),
                "admin2": addr.get("county"),
                "country": addr.get("country"),
            }
    except Exception as e:
        logger.exception("reverse geocoding failed")
        return {"ok": False, "error": str(e)}


class MemoryUpsert(BaseModel):
    text: str
    score: Optional[float] = 0.0
    tags: Optional[Dict[str, Any]] = None


@app.post("/api/memory/upsert")
async def memory_upsert(body: MemoryUpsert) -> Dict[str, Any]:
    tags_json = json.dumps(body.tags) if body.tags is not None else None
    mem_id = memory.upsert_text_memory(body.text, score=body.score or 0.0, tags_json=tags_json)
    return {"ok": True, "id": mem_id}


class MemoryQuery(BaseModel):
    query: str
    limit: Optional[int] = 5


@app.post("/api/memory/retrieve")
async def memory_retrieve(body: MemoryQuery) -> Dict[str, Any]:
    items = memory.retrieve_text_memories(body.query, limit=body.limit or 5)
    return {"ok": True, "items": items}


class MemoryRecentBody(BaseModel):
    limit: Optional[int] = 10


@app.post("/api/memory/recent")
async def memory_recent(body: MemoryRecentBody) -> Dict[str, Any]:
    items = memory.get_recent_text_memories(limit=body.limit or 10)
    return {"ok": True, "items": items}


@app.get("/api/tools/stats")
async def tools_stats() -> Dict[str, Any]:
    items = memory.get_all_tool_stats()
    return {"ok": True, "items": items}


class FeedbackBody(BaseModel):
    kind: str  # 'memory' | 'tool'
    id: Optional[int] = None
    tool: Optional[str] = None
    up: bool = True


@app.post("/api/feedback")
async def feedback(body: FeedbackBody) -> Dict[str, Any]:
    if body.kind == "memory" and body.id is not None:
        memory.update_memory_score(body.id, 1.0 if body.up else -1.0)
        return {"ok": True}
    if body.kind == "tool" and body.tool:
        memory.update_tool_stats(body.tool, success=body.up)
        return {"ok": True}
    return {"ok": False, "error": "invalid feedback payload"}


class Hub:
    def __init__(self) -> None:
        self._clients: Set[WebSocket] = set()
        self._lock = asyncio.Lock()

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        async with self._lock:
            self._clients.add(ws)

    async def disconnect(self, ws: WebSocket) -> None:
        async with self._lock:
            self._clients.discard(ws)

    async def broadcast(self, event: Dict[str, Any]) -> None:
        data = json.dumps(event)
        async with self._lock:
            clients = list(self._clients)
        # Skicka i parallell utanför låset för att undvika att blockera andra operationer
        results = await asyncio.gather(
            *[ws.send_text(data) for ws in clients], return_exceptions=True
        )
        # Rensa döda anslutningar
        async with self._lock:
            for ws, res in zip(clients, results):
                if isinstance(res, Exception):
                    self._clients.discard(ws)


hub = Hub()


@app.websocket("/ws/jarvis")
async def ws_jarvis(ws: WebSocket) -> None:
    await hub.connect(ws)
    try:
        await ws.send_text(json.dumps({"type": "hello", "ts": datetime.utcnow().isoformat() + "Z"}))
        while True:
            raw = await ws.receive_text()
            memory.append_event("ws_in", raw)
            try:
                msg = json.loads(raw)
            except Exception:
                await ws.send_text(json.dumps({"type": "error", "message": "invalid json"}))
                continue

            # Minimal intent handling: echo back and optionally forward to HUD
            if msg.get("type") == "ping":
                await ws.send_text(json.dumps({"type": "pong", "ts": datetime.utcnow().isoformat() + "Z"}))
            elif msg.get("type") == "dispatch":
                # Forward as a HUD command event
                event = {"type": "hud_command", "command": msg.get("command")}
                await hub.broadcast(event)
                await ws.send_text(json.dumps({"type": "ack", "event": "hud_command"}))
            else:
                await ws.send_text(json.dumps({"type": "echo", "data": msg}))
    except WebSocketDisconnect:
        pass
    finally:
        await hub.disconnect(ws)


async def ai_autonomous_loop() -> AsyncGenerator[None, None]:
    # Placeholder for a proactive loop that could broadcast HUD actions
    while True:
        await asyncio.sleep(60)
        # Example heartbeat event
        await hub.broadcast({"type": "heartbeat", "ts": datetime.utcnow().isoformat() + "Z"})


@app.on_event("startup")
async def on_startup() -> None:
    # Start autonomous loop (non-blocking)
    asyncio.create_task(ai_autonomous_loop())


