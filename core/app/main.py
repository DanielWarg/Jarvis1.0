from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel
import os
import json
import httpx


class ChatRequest(BaseModel):
    prompt: str
    model: str = "gpt-oss-20b"
    stream: bool = True
    options: dict | None = None


OLLAMA_URL = os.getenv("OLLAMA_URL", "http://127.0.0.1:11434")


app = FastAPI()


@app.get("/api/health")
def health():
    return {"status": "ok"}


async def stream_ollama_generate(payload: dict):
    async with httpx.AsyncClient(timeout=None) as client:
        async with client.stream("POST", f"{OLLAMA_URL}/api/generate", json=payload) as resp:
            try:
                resp.raise_for_status()
            except httpx.HTTPStatusError as exc:
                # Avsluta tidigt om Ollama svarar med fel
                yield json.dumps({"error": f"Ollama HTTP {exc.response.status_code}"}) + "\n"
                return
            async for line in resp.aiter_lines():
                if not line:
                    continue
                # Vidarebefordra NDJSON-raden oförändrad
                yield line + "\n"


@app.post("/api/chat")
async def chat(req: ChatRequest):
    payload: dict = {"model": req.model, "prompt": req.prompt, "stream": req.stream}
    if req.options:
        # Platta in options (Ollama accepterar t.ex. temperature, top_p osv.)
        payload.update(req.options)

    try:
        if req.stream:
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
            model = parsed.get("model", "gpt-oss-20b")
        except json.JSONDecodeError:
            prompt = raw_message
            model = "gpt-oss-20b"

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
