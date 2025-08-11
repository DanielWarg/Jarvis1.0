from __future__ import annotations

import asyncio
import json
import os
from datetime import datetime
from typing import Any, AsyncGenerator, Dict, Optional, Set, List

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import ORJSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import logging
import httpx
import httpx

from .memory import MemoryStore
from .decision import EpsilonGreedyBandit, simulate_first
from .training import stream_dataset


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


@app.post("/api/chat")
async def chat(body: ChatBody) -> Dict[str, Any]:
    logger.info("/api/chat model=%s prompt_len=%d", body.model, len(body.prompt or ""))
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            r = await client.post(
                "http://127.0.0.1:11434/api/generate",
                json={"model": body.model or "gpt-oss:20b", "prompt": body.prompt, "stream": False},
            )
            logger.info("ollama status=%s", r.status_code)
            if r.status_code == 200:
                data = r.json()
                return {"ok": True, "text": data.get("response", "")}
    except Exception:
        logger.exception("/api/chat error")
    return {"ok": True, "text": f"[stub] You said: {body.prompt}"}


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


