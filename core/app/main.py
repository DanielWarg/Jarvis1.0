from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse, JSONResponse, Response
from pydantic import BaseModel
from typing import Optional, Dict, Set
import os
import json
import httpx
from .db import ping_database
from .mqtt_client import ping_mqtt
from fastapi.middleware.cors import CORSMiddleware
import asyncio
from .cameras import list_cameras, upsert_camera, get_camera, Camera, capture_snapshot_jpeg
from .advanced_ai_brain import advanced_ai
from .command_handlers import register_all_handlers


class ChatRequest(BaseModel):
    prompt: str
    model: Optional[str] = None
    stream: bool = True
    options: Optional[Dict] = None


OLLAMA_URL = os.getenv("OLLAMA_URL", "http://127.0.0.1:11434")
DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", "gpt-oss:20b")


app = FastAPI(
    title="🤖 JARVIS Ultimate AI System",
    description="Advanced AI-powered HUD control with gpt-oss:20B, tool calling, and autonomous learning",
    version="3.0.0"
)

@app.on_event("startup")
async def startup_event():
    """Initialize the advanced JARVIS system"""
    logger.info("🚀 JARVIS Ultimate AI System starting up...")
    
    # Register all command handlers
    register_all_handlers()
    logger.info("✅ Command handlers registered")
    
    # Check AI brain connection
    # Note: health check will be added to advanced_ai_brain if needed
    logger.info("🧠 AI Brain initialized with tool calling capabilities")
    
    # Enable autonomous mode
    await advanced_ai.enable_autonomous_mode()
    logger.info("🤖 Autonomous mode ACTIVATED - JARVIS is now self-aware!")

import logging
logging.basicConfig(level=logging.INFO)

origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/api/jarvis/command")
async def jarvis_advanced_command(request: dict):
    """Advanced JARVIS command processing with AI brain"""
    try:
        user_input = request.get("prompt", "")
        context = request.get("context", {})
        
        if not user_input:
            return {"error": "No command provided", "success": False}
        
        # Process with advanced AI brain
        result = await advanced_ai.process_advanced_command(user_input, context)
        return result
        
    except Exception as e:
        logger.error(f"Advanced command error: {e}")
        return {"error": str(e), "success": False}

@app.get("/api/jarvis/capabilities") 
async def get_jarvis_capabilities():
    """Get JARVIS current capabilities and available tools"""
    tools = advanced_ai.tool_registry.get_available_tools()
    commands = advanced_ai.memory_system.get_execution_log(10)
    
    return {
        "status": "online",
        "autonomous_mode": advanced_ai.autonomous_mode,
        "learning_enabled": advanced_ai.learning_enabled,
        "available_tools": tools,
        "recent_commands": commands,
        "memory_stats": {
            "short_term_memories": len(advanced_ai.memory_system.short_term_memory),
            "tool_usage": advanced_ai.tool_registry.tool_usage_stats
        }
    }

@app.get("/api/health")
def health():
    db_ok = ping_database()
    mqtt_ok = ping_mqtt()
    try:
        # enkel kontroll: finns modellen listad hos Ollama
        import httpx as _hx

        r = _hx.get(f"{OLLAMA_URL}/api/tags", timeout=2.0)
        models = r.json().get("models", []) if r.status_code == 200 else []
        ollama_ok = any(m.get("name") == DEFAULT_MODEL for m in models)
    except Exception:
        ollama_ok = False
    status = {
        "status": "ok" if db_ok else "degraded",
        "db": db_ok,
        "mqtt": mqtt_ok,
        "ollama": ollama_ok,
        "default_model": DEFAULT_MODEL,
    }
    return status


async def stream_ollama_generate(payload: dict):
    async with httpx.AsyncClient(timeout=None) as client:
        async with client.stream("POST", f"{OLLAMA_URL}/api/generate", json=payload) as resp:
            if resp.status_code != 200:
                body = (await resp.aread()).decode("utf-8", errors="ignore")
                detail = body or f"HTTP {resp.status_code}"
                yield json.dumps({"error": f"Ollama fel: {detail}"}) + "\n"
                return
            async for line in resp.aiter_lines():
                if not line:
                    continue
                # Vidarebefordra NDJSON-raden oförändrad
                yield line + "\n"


async def stream_ollama_generate_sse(payload: dict):
    async for ndjson_line in stream_ollama_generate(payload):
        try:
            obj = json.loads(ndjson_line)
        except json.JSONDecodeError:
            yield f"data: {ndjson_line.strip()}\n\n"
            continue
        if "error" in obj:
            yield f"event: error\ndata: {json.dumps(obj)}\n\n"
            return
        if "response" in obj:
            # skicka token/text som data
            yield f"data: {json.dumps(obj['response'])}\n\n"
        if obj.get("done"):
            yield "event: done\ndata: [DONE]\n\n"
            return


@app.post("/api/chat")
async def chat(req: ChatRequest):
    model_name = req.model or DEFAULT_MODEL
    payload: dict = {"model": model_name, "prompt": req.prompt, "stream": req.stream}
    if req.options:
        # Platta in options (Ollama accepterar t.ex. temperature, top_p osv.)
        payload.update(req.options)

    try:
        if req.stream:
            # Content negotiation för SSE-fallback via query ?sse=1 eller Accept-header hanteras enklare via query
            # (i UI kommer vi använda WS för primär streaming).
            return StreamingResponse(stream_ollama_generate(payload), media_type="application/x-ndjson")
        else:
            async with httpx.AsyncClient(timeout=None) as client:
                r = await client.post(f"{OLLAMA_URL}/api/generate", json=payload)
                r.raise_for_status()
                return JSONResponse(content=r.json())
    except httpx.HTTPError as e:
        raise HTTPException(status_code=502, detail=str(e)) from e


@app.websocket("/ws/jarvis")
async def ws_jarvis_advanced(websocket: WebSocket):
    """Advanced JARVIS WebSocket with AI brain and tool calling"""
    from .websocket import handle_websocket
    await handle_websocket(websocket)

@app.websocket("/ws/chat")
async def ws_chat(websocket: WebSocket):
    await websocket.accept()
    try:
        raw_message = await websocket.receive_text()
        try:
            parsed = json.loads(raw_message)
            prompt = parsed.get("prompt", "")
            model = parsed.get("model", DEFAULT_MODEL)
        except json.JSONDecodeError:
            prompt = raw_message
            model = DEFAULT_MODEL

        payload = {"model": model, "prompt": prompt, "stream": True}
        async for line in stream_ollama_generate(payload):
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            if "response" in obj:
                await websocket.send_text(obj["response"])  # strömma tokens/fragment
            if obj.get("done"):
                await websocket.send_json({"done": True, "total_duration": obj.get("total_duration")})
                break
    except WebSocketDisconnect:
        pass
    except Exception as e:
        try:
            await websocket.send_json({"error": str(e)})
        except Exception:
            pass
    # Låt klienten stänga, undvik kompatibilitetsproblem i vissa websockets-versioner

# New JARVIS AI WebSocket endpoint
@app.websocket("/ws/jarvis")
async def ws_jarvis_ai(websocket: WebSocket):
    """JARVIS AI Brain WebSocket - HUD Control"""
    from .websocket import handle_websocket
    await handle_websocket(websocket)


# --- Realtime events (WS) ---
event_clients: Set[WebSocket] = set()


async def broadcast_event(event: dict) -> None:
    data = json.dumps(event)
    stale: Set[WebSocket] = set()
    for ws in event_clients:
        try:
            await ws.send_text(data)
        except Exception:
            stale.add(ws)
    for ws in stale:
        try:
            await ws.close()
        except Exception:
            pass
        event_clients.discard(ws)


@app.websocket("/ws/events")
async def ws_events(websocket: WebSocket):
    await websocket.accept()
    event_clients.add(websocket)
    try:
        while True:
            # vi lyssnar inte på klientmeddelanden i denna kanal
            await asyncio.sleep(60)
    except WebSocketDisconnect:
        pass
    finally:
        event_clients.discard(websocket)


class TestEvent(BaseModel):
    type: str = "motion"
    cameraId: str = "cam-1"
    snapshotUrl: Optional[str] = None
    message: Optional[str] = None


@app.post("/api/events/test")
async def post_test_event(ev: TestEvent):
    event_dict = ev.dict()
    if not event_dict.get("snapshotUrl"):
        event_dict["snapshotUrl"] = f"{os.getenv('PUBLIC_BASE', 'http://127.0.0.1:8000')}/api/cameras/{ev.cameraId}/snapshot.svg"
    if not event_dict.get("message"):
        event_dict["message"] = f"Rörelse detekterad på {ev.cameraId}"
    await broadcast_event(event_dict)
    return {"ok": True}


@app.get("/api/cameras/{camera_id}/snapshot.svg")
def camera_snapshot_svg(camera_id: str):
    # Generera enkel SVG-placeholder (lokalt)
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="320" height="180">
<rect width="100%" height="100%" fill="#111827"/>
<text x="50%" y="50%" dominant-baseline="middle" text-anchor="middle" fill="#e5e7eb" font-size="20" font-family="Arial, Helvetica, sans-serif">{camera_id} snapshot</text>
</svg>'''
    return Response(content=svg, media_type="image/svg+xml")


# --- Kamera endpoints ---


class CameraIn(BaseModel):
    id: str
    url: str
    name: Optional[str] = None


@app.get("/api/cameras")
def api_list_cameras():
    return [c.__dict__ for c in list_cameras()]


@app.post("/api/cameras")
def api_upsert_camera(cam: CameraIn):
    upsert_camera(Camera(**cam.dict()))
    return {"ok": True}


@app.get("/api/cameras/{camera_id}/snapshot.jpg")
def api_snapshot_jpg(camera_id: str):
    cam = get_camera(camera_id)
    if not cam:
        raise HTTPException(status_code=404, detail="camera not found")
    content = capture_snapshot_jpeg(cam.url)
    if not content:
        # fallback: svg placeholder
        return camera_snapshot_svg(camera_id)
    return Response(content=content, media_type="image/jpeg")
