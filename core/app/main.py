from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel
from typing import Optional, Dict
import os
import json
import httpx
from .db import ping_database
from .mqtt_client import ping_mqtt


class ChatRequest(BaseModel):
    prompt: str
    model: Optional[str] = None
    stream: bool = True
    options: Optional[Dict] = None


OLLAMA_URL = os.getenv("OLLAMA_URL", "http://127.0.0.1:11434")
DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", "gpt-oss:20b")


app = FastAPI()


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
        return
    except Exception as e:
        await websocket.send_json({"error": str(e)})
    finally:
        await websocket.close()
