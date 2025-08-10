from __future__ import annotations

import asyncio
import json
import os
from datetime import datetime
from typing import Any, AsyncGenerator, Dict, Optional, Set, List

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from .memory import MemoryStore


app = FastAPI(title="Jarvis 2.0 Backend", version="0.1.0")

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
    return JarvisResponse(ok=True, message="Command received", command=cmd)


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
        dead: List[WebSocket] = []
        data = json.dumps(event)
        async with self._lock:
            for ws in list(self._clients):
                try:
                    await ws.send_text(data)
                except Exception:
                    dead.append(ws)
            for ws in dead:
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


