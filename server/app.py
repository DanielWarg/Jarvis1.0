from __future__ import annotations

import asyncio
import time
import json
import os
from datetime import datetime
from typing import Any, AsyncGenerator, Dict, Optional, Set, List

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import ORJSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import logging
from dotenv import load_dotenv
import httpx
import httpx
import math
import base64
from urllib.parse import urlencode

from .memory import MemoryStore
from .decision import EpsilonGreedyBandit, simulate_first
from .prompts.system_prompts import system_prompt as SP, developer_prompt as DP
from .training import stream_dataset
from .memory import MemoryStore
from .tools.registry import list_tool_specs, validate_and_execute_tool


load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("jarvis")

app = FastAPI(title="Jarvis 2.0 Backend", version="0.1.0", default_response_class=ORJSONResponse)
MINIMAL_MODE = os.getenv("JARVIS_MINIMAL", "0") == "1"
# Harmony feature flags (Fas 1 – adapter bakom flaggor)
USE_HARMONY = (os.getenv("USE_HARMONY", "false").lower() == "true")
USE_TOOLS = (os.getenv("USE_TOOLS", "false").lower() == "true")
try:
    HARMONY_TEMPERATURE_COMMANDS = float(os.getenv("HARMONY_TEMPERATURE_COMMANDS", "0.2"))
except Exception:
    HARMONY_TEMPERATURE_COMMANDS = 0.2


def _harmony_system_prompt() -> str:
    return SP() + " För denna fas: skriv ENDAST slutligt svar mellan taggarna [FINAL] och [/FINAL]."


def _harmony_developer_prompt() -> str:
    return DP()


def _extract_final(text: str) -> str:
    try:
        start = text.find("[FINAL]")
        end = text.find("[/FINAL]")
        if start != -1 and end != -1 and end > start:
            return text[start + len("[FINAL]"):end].strip()
    except Exception:
        pass
    return (text or "").strip()

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
    return {"status": "ok", "db": memory.ping(), "ts": datetime.utcnow().isoformat() + "Z", "harmony": USE_HARMONY, "tools": USE_TOOLS}


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


class ExecToolBody(BaseModel):
    name: str
    args: Optional[Dict[str, Any]] = None


@app.post("/api/tools/exec")
async def tools_exec(body: ExecToolBody) -> Dict[str, Any]:
    if not USE_TOOLS:
        return {"ok": False, "error": "tools_disabled"}
    res = validate_and_execute_tool(body.name, body.args or {}, memory)
    # Enkel telemetri
    try:
        if res.get("ok"):
            memory.update_tool_stats(body.name, success=True)
        else:
            memory.update_tool_stats(body.name, success=False)
    except Exception:
        pass
    return res


@app.get("/api/tools/specs")
async def tools_specs() -> Dict[str, Any]:
    return {"ok": True, "items": list_tool_specs()}


class ChatBody(BaseModel):
    prompt: str
    model: Optional[str] = "gpt-oss:20b"
    stream: Optional[bool] = False
    provider: Optional[str] = "auto"  # 'local' | 'openai' | 'auto'
    raw: Optional[bool] = False         # when True → no RAG/context, clean reply


@app.post("/api/chat")
async def chat(body: ChatBody) -> Dict[str, Any]:
    logger.info("/api/chat model=%s prompt_len=%d", body.model, len(body.prompt or ""))
    # Minimal RAG: hämta relevanta textminnen via LIKE och inkludera i prompten
    if MINIMAL_MODE or bool(body.raw):
        contexts = []
        ctx_payload = []
        full_prompt = f"Besvara på svenska.\n\nFråga: {body.prompt}\nSvar:"
    else:
        try:
            # Hybrid: använd lokalt BM25+recency om tillgängligt, annars LIKE
            contexts = memory.retrieve_text_bm25_recency(body.prompt, limit=5)
        except Exception:
            try:
                contexts = memory.retrieve_text_memories(body.prompt, limit=5)
            except Exception:
                contexts = []
        ctx_text = "\n".join([f"- {it.get('text','')}" for it in (contexts or []) if it.get('text')])
        ctx_payload = [it.get('text','') for it in contexts[:3] if it.get('text')]
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
    async def respond(text: str, used_provider: str, engine: Optional[str] = None) -> Dict[str, Any]:
        mem_id: Optional[int] = None
        try:
            tags = {"source": "chat", "model": body.model or "gpt-oss:20b", "provider": used_provider, "engine": engine}
            mem_id = memory.upsert_text_memory(text, score=0.0, tags_json=json.dumps(tags, ensure_ascii=False))
            memory.append_event("chat.out", json.dumps({"text": text, "memory_id": mem_id}, ensure_ascii=False))
        except Exception:
            pass
        return {"ok": True, "text": text, "memory_id": mem_id, "provider": used_provider, "engine": engine}

    # 1) Lokal (Ollama)
    async def try_local():
        try:
            t0 = time.time()
            async with httpx.AsyncClient(timeout=60.0) as client:
                r = await client.post(
                    "http://127.0.0.1:11434/api/generate",
                    json={
                        "model": body.model or os.getenv("LOCAL_MODEL", "gpt-oss:20b"),
                        "prompt": (f"System: {_harmony_system_prompt()}\nDeveloper: {_harmony_developer_prompt()}\nUser: {full_prompt}\nSvar: ") if USE_HARMONY else full_prompt,
                        "stream": False,
                        "options": {"num_predict": 512, "temperature": HARMONY_TEMPERATURE_COMMANDS if USE_HARMONY else 0.3},
                    },
                )
                if r.status_code == 200:
                    data = r.json()
                    dt = (time.time() - t0) * 1000
                    logger.info("chat local ms=%.0f", dt)
                    raw_text = (data.get("response", "") or "").strip()
                    local_text = _extract_final(raw_text) if USE_HARMONY else raw_text
                    if not local_text:
                        return RuntimeError("local_empty")
                    return await respond(local_text, used_provider="local", engine=(body.model or os.getenv("LOCAL_MODEL", "gpt-oss:20b")))
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
                        "messages": (
                            [
                                {"role": "system", "content": _harmony_system_prompt()},
                                {"role": "developer", "content": _harmony_developer_prompt()},
                                {"role": "user", "content": full_prompt},
                            ] if USE_HARMONY else [
                                {"role": "system", "content": "Du är Jarvis. Svara på svenska och använd 'Relevanta minnen' om de hjälper."},
                                {"role": "user", "content": full_prompt},
                            ]
                        ),
                        "temperature": HARMONY_TEMPERATURE_COMMANDS if USE_HARMONY else 0.5,
                        "max_tokens": 256,
                    },
                )
                if r.status_code == 200:
                    data = r.json()
                    raw_text = ((data.get("choices") or [{}])[0].get("message") or {}).get("content", "")
                    text = _extract_final(raw_text) if USE_HARMONY else raw_text
                    dt = (time.time() - t0) * 1000
                    logger.info("chat openai ms=%.0f", dt)
                    return await respond(text, used_provider="openai", engine=os.getenv("OPENAI_MODEL", "gpt-4o-mini"))
        except Exception as e:
            return e
        return RuntimeError("openai_failed")

    try:
        if provider == "local":
            res = await try_local()
            if isinstance(res, dict):
                return res
            # if local failed/empty under 'local', fall back to stub at end
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
                if isinstance(res, dict) and (res.get("text") or "").strip():
                    # cancel the slower one
                    for p in pending:
                        p.cancel()
                    return res
                last_error = res
            # if first completed wasn't dict, wait the other
            for p in pending:
                try:
                    res = await p
                    if isinstance(res, dict) and (res.get("text") or "").strip():
                        return res
                    last_error = res
                except asyncio.CancelledError:
                    pass
    except Exception:
        logger.exception("/api/chat error")
    # Stub: visa vilken kontext som skulle ha använts, för verifiering i UI
    stub_ctx = ("\n\n[Kontext]\n" + ctx_text) if ctx_text else ""
    return {"ok": True, "text": f"[stub] {body.prompt}{stub_ctx}", "memory_id": None, "provider": provider, "engine": None, "contexts": ctx_payload}


@app.post("/api/chat/stream")
async def chat_stream(body: ChatBody):
    # Förbered RAG-kontekst likt /api/chat
    if MINIMAL_MODE or bool(body.raw):
        contexts = []
        ctx_payload = []
        full_prompt = f"Besvara på svenska.\n\nFråga: {body.prompt}\nSvar:"
    else:
        try:
            contexts = memory.retrieve_text_bm25_recency(body.prompt, limit=5)
        except Exception:
            try:
                contexts = memory.retrieve_text_memories(body.prompt, limit=5)
            except Exception:
                contexts = []
        ctx_text = "\n".join([f"- {it.get('text','')}" for it in (contexts or []) if it.get('text')])
        ctx_payload = [it.get('text','') for it in (contexts or []) if it.get('text')][:3]
        full_prompt = (("Relevanta minnen:\n" + ctx_text + "\n\n") if ctx_text else "") + f"Använd relevant kontext ovan vid behov. Besvara på svenska.\n\nFråga: {body.prompt}\nSvar:"

    provider = (body.provider or "auto").lower()

    async def gen():
        final_text = ""
        used_provider = None
        emitted = False

        async def sse_send(obj):
            yield f"data: {json.dumps(obj, ensure_ascii=False)}\n\n"

        async def openai_stream():
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                return
            try:
                async with httpx.AsyncClient(timeout=None) as client:
                    r = await client.post(
                        "https://api.openai.com/v1/chat/completions",
                        headers={"Authorization": f"Bearer {api_key}"},
                        json={
                            "model": os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
                            "messages": (
                                [
                                    {"role": "system", "content": _harmony_system_prompt()},
                                    {"role": "developer", "content": _harmony_developer_prompt()},
                                    {"role": "user", "content": full_prompt},
                                ] if USE_HARMONY else [
                                    {"role": "system", "content": "Du är Jarvis. Svara på svenska och använd 'Relevanta minnen' om de hjälper."},
                                    {"role": "user", "content": full_prompt},
                                ]
                            ),
                            "temperature": HARMONY_TEMPERATURE_COMMANDS if USE_HARMONY else 0.5,
                            "stream": True,
                            "max_tokens": 256,
                        },
                    )
                    if r.status_code != 200:
                        return
                    nonlocal final_text, used_provider, emitted
                    used_provider = "openai"
                    async for line in r.aiter_lines():
                        if not line:
                            continue
                        if line.startswith("data: "):
                            data = line[len("data: "):].strip()
                            if data == "[DONE]":
                                break
                            try:
                                obj = json.loads(data)
                                raw_delta = (((obj.get("choices") or [{}])[0]).get("delta") or {}).get("content")
                                delta = _extract_final(raw_delta) if USE_HARMONY else raw_delta
                                if delta:
                                    emitted = True
                                    final_text += delta
                                    async for out in sse_send({"type": "chunk", "text": delta}):
                                        yield out
                            except Exception:
                                continue
            except Exception:
                return

        async def local_stream():
            try:
                async with httpx.AsyncClient(timeout=None) as client:
                    r = await client.post(
                        "http://127.0.0.1:11434/api/generate",
                        json={
                            "model": body.model or os.getenv("LOCAL_MODEL", "gpt-oss:20b"),
                            "prompt": full_prompt,
                            "stream": True,
                            "options": {"num_predict": 256, "temperature": 0.3},
                        },
                    )
                    if r.status_code != 200:
                        return
                    nonlocal final_text, used_provider, emitted
                    used_provider = "local"
                    async for line in r.aiter_lines():
                        if not line:
                            continue
                        try:
                            obj = json.loads(line)
                            if obj.get("done"):
                                break
                            delta = obj.get("response")
                            if delta:
                                emitted = True
                                final_text += delta
                                async for out in sse_send({"type": "chunk", "text": delta}):
                                    yield out
                        except Exception:
                            continue
            except Exception:
                return

        # skicka meta först
        async for out in sse_send({"type": "meta", "contexts": ctx_payload}):
            yield out

        if provider == "openai":
            async for out in openai_stream():
                yield out
        elif provider == "local":
            async for out in local_stream():
                yield out
        else:
            # auto: försök online först, sedan lokal om inget kom
            async for out in openai_stream():
                yield out
            if not emitted:
                async for out in local_stream():
                    yield out

        # done-event och minnesupsert
        mem_id = None
        try:
            if final_text:
                tags = {"source": "chat", "provider": used_provider}
                mem_id = memory.upsert_text_memory(final_text, score=0.0, tags_json=json.dumps(tags, ensure_ascii=False))
        except Exception:
            pass
        async for out in sse_send({"type": "done", "provider": used_provider, "memory_id": mem_id}):
            yield out

    return StreamingResponse(gen(), media_type="text/event-stream")


class ActBody(BaseModel):
    prompt: Optional[str] = ""
    model: Optional[str] = "gpt-oss:20b"
    allow: Optional[List[str]] = None  # e.g. ["SHOW_MODULE","HIDE_OVERLAY","OPEN_VIDEO"]
    provider: Optional[str] = "auto"  # 'local' | 'openai' | 'auto'
    dry_run: Optional[bool] = False


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
    if body.dry_run:
        return {"ok": True, "command": cmd, "scores": scores}
    if scores.get("risk", 1.0) > 0.8:
        return {"ok": False, "error": "blocked_by_safety", "scores": scores}
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
    # Skapa embeddings (OpenAI) om nyckel finns
    try:
        api_key = os.getenv("OPENAI_API_KEY")
        if api_key and (body.text or "").strip():
            async with httpx.AsyncClient(timeout=20.0) as client:
                r = await client.post(
                    "https://api.openai.com/v1/embeddings",
                    headers={"Authorization": f"Bearer {api_key}"},
                    json={"input": body.text, "model": os.getenv("OPENAI_EMBED_MODEL", "text-embedding-3-small")},
                )
                if r.status_code == 200:
                    d = r.json() or {}
                    vec = ((d.get("data") or [{}])[0].get("embedding") or [])
                    memory.upsert_embedding(mem_id, model=os.getenv("OPENAI_EMBED_MODEL", "text-embedding-3-small"), dim=len(vec), vector_json=json.dumps(vec))
    except Exception:
        logger.exception("embedding upsert failed")
    return {"ok": True, "id": mem_id}


class MemoryQuery(BaseModel):
    query: str
    limit: Optional[int] = 5


@app.post("/api/memory/retrieve")
async def memory_retrieve(body: MemoryQuery) -> Dict[str, Any]:
    # Hybrid: BM25/LIKE + semantisk (cosine)
    like_items = memory.retrieve_text_memories(body.query, limit=(body.limit or 5))
    results = list(like_items)
    try:
        api_key = os.getenv("OPENAI_API_KEY")
        if api_key and (body.query or "").strip():
            async with httpx.AsyncClient(timeout=20.0) as client:
                rq = await client.post(
                    "https://api.openai.com/v1/embeddings",
                    headers={"Authorization": f"Bearer {api_key}"},
                    json={"input": body.query, "model": os.getenv("OPENAI_EMBED_MODEL", "text-embedding-3-small")},
                )
                if rq.status_code == 200:
                    qv = ((rq.json().get("data") or [{}])[0].get("embedding") or [])
                    rows = memory.get_all_embeddings(model=os.getenv("OPENAI_EMBED_MODEL", "text-embedding-3-small"))
                    # Cosine similarity
                    def cos(a,b):
                        if not a or not b:
                            return 0.0
                        num = sum(x*y for x,y in zip(a,b))
                        da = math.sqrt(sum(x*x for x in a))
                        db = math.sqrt(sum(y*y for y in b))
                        return (num/(da*db)) if da>0 and db>0 else 0.0
                    sims = []
                    for mem_id, dim, vec_json in rows:
                        try:
                            v = json.loads(vec_json)
                            sims.append((mem_id, cos(qv, v)))
                        except Exception:
                            continue
                    sims.sort(key=lambda x: x[1], reverse=True)
                    top_ids = [mid for mid,_ in sims[: (body.limit or 5)]]
                    id_to_text = memory.get_texts_for_mem_ids(top_ids)
                    for mid in top_ids:
                        txt = id_to_text.get(mid)
                        if txt and all(x.get('text') != txt for x in results):
                            results.append({"id": mid, "text": txt, "kind": "text", "score": 0.0, "ts": ""})
    except Exception:
        logger.exception("hybrid retrieve failed")
    # Trim till limit*2 för att undvika för stor retur
    return {"ok": True, "items": results[: max(1,(body.limit or 5))]}


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


# ────────────────────────────────────────────────────────────────────────────────
# Spotify OAuth (Authorization Code)

SPOTIFY_AUTH_URL = "https://accounts.spotify.com/authorize"
SPOTIFY_TOKEN_URL = "https://accounts.spotify.com/api/token"


class SpotifyAuthBody(BaseModel):
    scopes: Optional[List[str]] = None


@app.get("/api/spotify/auth_url")
async def spotify_auth_url(scopes: Optional[str] = None) -> Dict[str, Any]:
    client_id = os.getenv("SPOTIFY_CLIENT_ID")
    redirect_uri = os.getenv("SPOTIFY_REDIRECT_URI", "http://127.0.0.1:3100/spotify/callback")
    if not client_id:
        return {"ok": False, "error": "missing_client_id"}
    scope_str = scopes or " ".join([
        "streaming",
        "user-read-email",
        "user-read-private",
        "user-read-playback-state",
        "user-modify-playback-state",
        "user-read-currently-playing",
        "playlist-read-private",
        "playlist-modify-private",
        "playlist-modify-public",
    ])
    params = {
        "response_type": "code",
        "client_id": client_id,
        "scope": scope_str,
        "redirect_uri": redirect_uri,
        "show_dialog": "true",
    }
    return {"ok": True, "url": f"{SPOTIFY_AUTH_URL}?{urlencode(params)}"}


@app.get("/api/spotify/callback")
async def spotify_callback(code: Optional[str] = None, state: Optional[str] = None) -> Dict[str, Any]:
    if not code:
        return {"ok": False, "error": "missing_code"}
    client_id = os.getenv("SPOTIFY_CLIENT_ID")
    client_secret = os.getenv("SPOTIFY_CLIENT_SECRET")
    redirect_uri = os.getenv("SPOTIFY_REDIRECT_URI", "http://127.0.0.1:3100/spotify/callback")
    if not client_id or not client_secret:
        return {"ok": False, "error": "missing_client_config"}
    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": redirect_uri,
        "client_id": client_id,
        "client_secret": client_secret,
    }
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            r = await client.post(SPOTIFY_TOKEN_URL, data=data)
            r.raise_for_status()
            token = r.json()
    except Exception:
        logger.exception("spotify token exchange failed")
        return {"ok": False, "error": "token_exchange_failed"}
    try:
        memory.append_event("spotify.tokens", json.dumps({"received": True}))
    except Exception:
        pass
    return {"ok": True, "token": token}


@app.get("/api/spotify/me")
async def spotify_me(access_token: str) -> Dict[str, Any]:
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.get("https://api.spotify.com/v1/me", headers={"Authorization": f"Bearer {access_token}"})
            r.raise_for_status()
            return {"ok": True, "me": r.json()}
    except Exception:
        logger.exception("spotify me failed")
        return {"ok": False, "error": "spotify_me_failed"}


# Token refresh för Spotify
class SpotifyRefreshBody(BaseModel):
    refresh_token: str


@app.post("/api/spotify/refresh")
async def spotify_refresh(body: SpotifyRefreshBody) -> Dict[str, Any]:
    client_id = os.getenv("SPOTIFY_CLIENT_ID")
    client_secret = os.getenv("SPOTIFY_CLIENT_SECRET")
    if not client_id or not client_secret:
        return {"ok": False, "error": "missing_client_config"}
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            r = await client.post(
                SPOTIFY_TOKEN_URL,
                data={
                    "grant_type": "refresh_token",
                    "refresh_token": body.refresh_token,
                    "client_id": client_id,
                    "client_secret": client_secret,
                },
            )
            r.raise_for_status()
            token = r.json()
            try:
                memory.append_event("spotify.refresh", json.dumps({"ok": True}))
            except Exception:
                pass
            return {"ok": True, "token": token}
    except Exception:
        logger.exception("spotify refresh failed")
        return {"ok": False, "error": "refresh_failed"}


@app.get("/api/spotify/devices")
async def spotify_devices(access_token: str) -> Dict[str, Any]:
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.get(
                "https://api.spotify.com/v1/me/player/devices",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            r.raise_for_status()
            return {"ok": True, "devices": r.json()}
    except Exception:
        logger.exception("spotify devices failed")
        return {"ok": False, "error": "spotify_devices_failed"}


@app.get("/api/spotify/state")
async def spotify_state(access_token: str) -> Dict[str, Any]:
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.get(
                "https://api.spotify.com/v1/me/player",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            if r.status_code == 204:
                return {"ok": True, "state": None}
            r.raise_for_status()
            return {"ok": True, "state": r.json()}
    except Exception:
        logger.exception("spotify state failed")
        return {"ok": False, "error": "spotify_state_failed"}


@app.get("/api/spotify/current")
async def spotify_current(access_token: str) -> Dict[str, Any]:
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.get(
                "https://api.spotify.com/v1/me/player/currently-playing",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            if r.status_code == 204:
                return {"ok": True, "item": None}
            r.raise_for_status()
            return {"ok": True, "item": r.json()}
    except Exception:
        logger.exception("spotify current failed")
        return {"ok": False, "error": "spotify_current_failed"}


@app.get("/api/spotify/recommendations")
async def spotify_recommendations(access_token: str, seed_tracks: Optional[str] = None, seed_artists: Optional[str] = None, seed_genres: Optional[str] = None, limit: Optional[int] = 5) -> Dict[str, Any]:
    try:
        params: Dict[str, Any] = {"limit": int(limit or 5)}
        if seed_tracks:
            params["seed_tracks"] = seed_tracks
        if seed_artists:
            params["seed_artists"] = seed_artists
        if seed_genres:
            params["seed_genres"] = seed_genres
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.get(
                "https://api.spotify.com/v1/recommendations",
                headers={"Authorization": f"Bearer {access_token}"},
                params=params,
            )
            r.raise_for_status()
            return {"ok": True, "recs": r.json()}
    except Exception:
        logger.exception("spotify recommendations failed")
        return {"ok": False, "error": "spotify_recommendations_failed"}


# Lista användarens spellistor
@app.get("/api/spotify/playlists")
async def spotify_playlists(access_token: str, limit: Optional[int] = 20, offset: Optional[int] = 0) -> Dict[str, Any]:
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.get(
                f"https://api.spotify.com/v1/me/playlists?limit={int(limit or 20)}&offset={int(offset or 0)}",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            r.raise_for_status()
            return {"ok": True, "playlists": r.json()}
    except Exception:
        logger.exception("spotify playlists failed")
        return {"ok": False, "error": "spotify_playlists_failed"}


# Sök låtar/playlist
@app.get("/api/spotify/search")
async def spotify_search(access_token: str, q: str, type: Optional[str] = "track,playlist", limit: Optional[int] = 10) -> Dict[str, Any]:
    try:
        qp = httpx.QueryParams({"q": q, "type": type or "track,playlist", "limit": int(limit or 10)})
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.get(
                f"https://api.spotify.com/v1/search?{qp}",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            r.raise_for_status()
            return {"ok": True, "result": r.json()}
    except Exception:
        logger.exception("spotify search failed")
        return {"ok": False, "error": "spotify_search_failed"}


class SpotifyPlayBody(BaseModel):
    access_token: str
    device_id: Optional[str] = None
    uris: Optional[List[str]] = None
    context_uri: Optional[str] = None
    position_ms: Optional[int] = None
    offset_position: Optional[int] = None  # for context playback
    offset_uri: Optional[str] = None       # alternative to position


@app.post("/api/spotify/play")
async def spotify_play(body: SpotifyPlayBody) -> Dict[str, Any]:
    if not body.uris and not body.context_uri:
        return {"ok": False, "error": "missing_uris_or_context"}
    try:
        qp = ""
        if body.device_id:
            qp = "?" + str(httpx.QueryParams({"device_id": body.device_id}))
        payload: Dict[str, Any] = {}
        if body.uris:
            payload["uris"] = body.uris
        if body.context_uri:
            payload["context_uri"] = body.context_uri
        if body.position_ms is not None:
            payload["position_ms"] = int(body.position_ms)
        if body.offset_uri or (body.offset_position is not None):
            off: Dict[str, Any] = {}
            if body.offset_uri:
                off["uri"] = body.offset_uri
            if body.offset_position is not None:
                off["position"] = int(body.offset_position)
            if off:
                payload["offset"] = off
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.put(
                f"https://api.spotify.com/v1/me/player/play{qp}",
                headers={"Authorization": f"Bearer {body.access_token}", "Content-Type": "application/json"},
                json=payload,
            )
            # 204 No Content på success
            if r.status_code in (200, 204):
                return {"ok": True}
            return {"ok": False, "error": f"status_{r.status_code}", "details": r.text}
    except Exception as e:
        logger.exception("spotify play failed")
        return {"ok": False, "error": "spotify_play_failed", "message": str(e)}


class SpotifyQueueBody(BaseModel):
    access_token: str
    device_id: Optional[str] = None
    uri: str


@app.post("/api/spotify/queue")
async def spotify_queue(body: SpotifyQueueBody) -> Dict[str, Any]:
    try:
        params: Dict[str, Any] = {"uri": body.uri}
        if body.device_id:
            params["device_id"] = body.device_id
        qp = str(httpx.QueryParams(params))
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.post(
                f"https://api.spotify.com/v1/me/player/queue?{qp}",
                headers={"Authorization": f"Bearer {body.access_token}"},
            )
            if r.status_code in (200, 204):
                return {"ok": True}
            return {"ok": False, "error": f"status_{r.status_code}", "details": r.text}
    except Exception as e:
        logger.exception("spotify queue failed")
        return {"ok": False, "error": "spotify_queue_failed", "message": str(e)}


# ────────────────────────────────────────────────────────────────────────────────
# AI‑driven media‑akt (NL → spela låt/playlist på Spotify)
class MediaActBody(BaseModel):
    prompt: str
    access_token: str
    device_id: Optional[str] = None
    provider: Optional[str] = "auto"  # 'local' | 'openai' | 'auto'


@app.post("/api/ai/media_act")
async def ai_media_act(body: MediaActBody) -> Dict[str, Any]:
    """Tolka prompten och spela upp via Spotify.
    Förväntat JSON från modellen:
    {"action":"play_track","track":"Back In Black","artist":"AC/DC"}
    eller {"action":"play_playlist","playlist":"Hard Rock Classics"}
    """
    if not body.access_token:
        return {"ok": False, "error": "missing_access_token"}

    instruction = (
        "Du får en svensk text om musikuppspelning. Svara ENBART med ett JSON-objekt utan förklaring. "
        "Fält: action = 'play_track' | 'play_playlist'. För play_track: 'track' (namn), valfritt 'artist'. "
        "För play_playlist: 'playlist' (namn). Exempel: {\"action\":\"play_track\",\"track\":\"Back In Black\",\"artist\":\"AC/DC\"}."
    )
    provider = (body.provider or "auto").lower()

    import re as _re

    async def try_local():
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                r = await client.post(
                    "http://127.0.0.1:11434/api/generate",
                    json={
                        "model": os.getenv("LOCAL_MODEL", "gpt-oss:20b"),
                        "prompt": f"{instruction}\n\nAnvändarens önskemål: {body.prompt}\nJSON:",
                        "stream": False,
                        "options": {"num_predict": 128, "temperature": 0.2},
                    },
                )
                if r.status_code == 200:
                    text = (r.json() or {}).get("response", "")
                    m = _re.search(r"\{[\s\S]*\}", text)
                    if m:
                        return json.loads(m.group(0))
        except Exception:
            return None
        return None

    async def try_openai():
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            return None
        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                r = await client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={"Authorization": f"Bearer {api_key}"},
                    json={
                        "model": os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
                        "messages": [
                            {"role": "system", "content": instruction},
                            {"role": "user", "content": body.prompt},
                        ],
                        "temperature": 0.2,
                        "max_tokens": 100,
                    },
                )
                if r.status_code == 200:
                    data = r.json()
                    text = ((data.get("choices") or [{}])[0].get("message") or {}).get("content", "")
                    m = _re.search(r"\{[\s\S]*\}", text)
                    if m:
                        return json.loads(m.group(0))
        except Exception:
            return None
        return None

    parsed = None
    if provider == "local":
        parsed = await try_local()
    elif provider == "openai":
        parsed = await try_openai()
    else:
        t1 = asyncio.create_task(try_openai())
        t2 = asyncio.create_task(try_local())
        done, pending = await asyncio.wait({t1, t2}, return_when=asyncio.FIRST_COMPLETED)
        for d in done:
            val = d.result()
            if val:
                parsed = val
        for p in pending:
            try:
                val = await p
                if not parsed and val:
                    parsed = val
            except asyncio.CancelledError:
                pass

    if not isinstance(parsed, dict):
        # Heuristisk fallback: tolka "spela X med Y" → play_track
        low = (body.prompt or "").strip().lower()
        try:
            import re as _re
            m = _re.search(r"spela\s+(.+?)(?:\s+med\s+(.+))?$", low)
            if m:
                track_guess = (m.group(1) or "").strip()
                artist_guess = (m.group(2) or "").strip()
                parsed = {"action": "play_track", "track": track_guess}
                if artist_guess:
                    parsed["artist"] = artist_guess
            else:
                parsed = {"action": "play_track", "track": low.replace("spela", "").strip()}
        except Exception:
            return {"ok": False, "error": "parse_failed"}

    action = (parsed.get("action") or "").lower()
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            if action == "play_track":
                q = (parsed.get("track") or "").strip()
                artist = (parsed.get("artist") or "").strip()
                if not q:
                    return {"ok": False, "error": "missing_track"}
                query = f"{q} artist:{artist}" if artist else q
                sr = await client.get(
                    f"https://api.spotify.com/v1/search",
                    params={"q": query, "type": "track", "limit": 5},
                    headers={"Authorization": f"Bearer {body.access_token}"},
                )
                sr.raise_for_status()
                data = sr.json() or {}
                items = (data.get("tracks") or {}).get("items") or []
                # Om artist inte angavs men prompten innehåller en favorit: använd recommendations med seed på artist
                if not items and artist:
                    # hämta artist-id
                    ar = await client.get(
                        "https://api.spotify.com/v1/search",
                        params={"q": artist, "type": "artist", "limit": 1},
                        headers={"Authorization": f"Bearer {body.access_token}"},
                    )
                    if ar.status_code == 200:
                        aid = (((ar.json() or {}).get("artists") or {}).get("items") or [{}])[0].get("id")
                        if aid:
                            rr = await client.get(
                                "https://api.spotify.com/v1/recommendations",
                                params={"seed_artists": aid, "limit": 5},
                                headers={"Authorization": f"Bearer {body.access_token}"},
                            )
                            if rr.status_code == 200:
                                items = ((rr.json() or {}).get("tracks") or [])
                if not items:
                    return {"ok": False, "error": "no_track_results"}
                uri = (items[0] or {}).get("uri")
                pr = await client.put(
                    f"https://api.spotify.com/v1/me/player/play",
                    params={"device_id": body.device_id} if body.device_id else None,
                    headers={"Authorization": f"Bearer {body.access_token}", "Content-Type": "application/json"},
                    json={"uris": [uri], "position_ms": 0},
                )
                if pr.status_code not in (200, 204):
                    return {"ok": False, "error": f"status_{pr.status_code}", "details": pr.text}
                return {"ok": True, "played": {"kind": "track", "uri": uri}}

            if action == "play_playlist":
                name = (parsed.get("playlist") or "").strip()
                if not name:
                    return {"ok": False, "error": "missing_playlist"}
                sr = await client.get(
                    f"https://api.spotify.com/v1/search",
                    params={"q": name, "type": "playlist", "limit": 5},
                    headers={"Authorization": f"Bearer {body.access_token}"},
                )
                sr.raise_for_status()
                items = ((sr.json() or {}).get("playlists") or {}).get("items") or []
                if not items:
                    return {"ok": False, "error": "no_playlist_results"}
                ctx = (items[0] or {}).get("uri")
                pr = await client.put(
                    f"https://api.spotify.com/v1/me/player/play",
                    params={"device_id": body.device_id} if body.device_id else None,
                    headers={"Authorization": f"Bearer {body.access_token}", "Content-Type": "application/json"},
                    json={"context_uri": ctx, "position_ms": 0, "offset": {"position": 0}},
                )
                if pr.status_code not in (200, 204):
                    return {"ok": False, "error": f"status_{pr.status_code}", "details": pr.text}
                return {"ok": True, "played": {"kind": "playlist", "uri": ctx}}
    except Exception as e:
        logger.exception("ai_media_act failed")
        return {"ok": False, "error": "media_act_failed", "message": str(e)}

    return {"ok": False, "error": "unsupported_action"}


# ────────────────────────────────────────────────────────────────────────────────
# En enda AI-router som väljer chat / HUD‑akt / media‑akt
class RouteBody(BaseModel):
    prompt: str
    provider: Optional[str] = "auto"
    hud_allow: Optional[List[str]] = ["SHOW_MODULE","OPEN_VIDEO","HIDE_OVERLAY"]
    spotify_access_token: Optional[str] = None
    spotify_device_id: Optional[str] = None


@app.post("/api/ai/route")
async def ai_route(body: RouteBody) -> Dict[str, Any]:
    instr = (
        "Klassificera användarens avsikt och svara ENDAST med JSON.\n"
        "Fält: intent in ['chat','hud','media_track','media_playlist'].\n"
        "Om media_track: ge 'track' och ev 'artist'. Om media_playlist: ge 'playlist'.\n"
        "Om hud: ge 'text' som beskriver vad HUD ska göra (svenska).\n"
    )
    provider = (body.provider or "auto").lower()

    import re as _re

    async def classify_local():
        try:
            async with httpx.AsyncClient(timeout=12.0) as client:
                r = await client.post(
                    "http://127.0.0.1:11434/api/generate",
                    json={
                        "model": os.getenv("LOCAL_MODEL", "gpt-oss:20b"),
                        "prompt": f"{instr}\n\nAnvändarens text: {body.prompt}\nJSON:",
                        "stream": False,
                        "options": {"num_predict": 100, "temperature": 0.2},
                    },
                )
                if r.status_code == 200:
                    text = (r.json() or {}).get("response", "")
                    m = _re.search(r"\{[\s\S]*\}", text)
                    if m:
                        return json.loads(m.group(0))
        except Exception:
            return None
        return None

    async def classify_openai():
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            return None
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                r = await client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={"Authorization": f"Bearer {api_key}"},
                    json={
                        "model": os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
                        "messages": [
                            {"role": "system", "content": instr},
                            {"role": "user", "content": body.prompt},
                        ],
                        "temperature": 0.2,
                        "max_tokens": 80,
                    },
                )
                if r.status_code == 200:
                    d = r.json()
                    text = ((d.get("choices") or [{}])[0].get("message") or {}).get("content", "")
                    m = _re.search(r"\{[\s\S]*\}", text)
                    if m:
                        return json.loads(m.group(0))
        except Exception:
            return None
        return None

    parsed = None
    if provider == "local":
        parsed = await classify_local()
    elif provider == "openai":
        parsed = await classify_openai()
    else:
        t1 = asyncio.create_task(classify_openai())
        t2 = asyncio.create_task(classify_local())
        done, pending = await asyncio.wait({t1, t2}, return_when=asyncio.FIRST_COMPLETED)
        for d in done:
            v = d.result()
            if v:
                parsed = v
        for p in pending:
            try:
                v = await p
                if not parsed and v:
                    parsed = v
            except asyncio.CancelledError:
                pass

    # Heuristik om LLM fallerar
    if not isinstance(parsed, dict):
        low = (body.prompt or "").lower()
        if low.startswith("spela") or " spela " in low:
            parsed = {"intent": "media_track"}
        elif any(k in low for k in ["visa","öppna","stäng","open","close"]):
            parsed = {"intent": "hud"}
        else:
            parsed = {"intent": "chat"}

    intent = (parsed.get("intent") or "chat").lower()
    # Route
    if intent in {"media_track","media_playlist"}:
        if not body.spotify_access_token:
            return {"ok": False, "error": "missing_spotify_token"}
        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                rr = await client.post(
                    "http://127.0.0.1:8000/api/ai/media_act",
                    json={
                        "prompt": body.prompt,
                        "access_token": body.spotify_access_token,
                        "device_id": body.spotify_device_id,
                        "provider": provider,
                    },
                )
                return {"ok": True, "kind": "media", "result": rr.json()}
        except Exception:
            logger.exception("route->media failed")
            return {"ok": False, "error": "route_media_failed"}

    if intent == "hud":
        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                rr = await client.post(
                    "http://127.0.0.1:8000/api/ai/act",
                    json={"prompt": body.prompt, "allow": body.hud_allow, "provider": provider},
                )
                return {"ok": True, "kind": "hud", "result": rr.json()}
        except Exception:
            logger.exception("route->hud failed")
            return {"ok": False, "error": "route_hud_failed"}

    # default chat
    try:
        async with httpx.AsyncClient(timeout=25.0) as client:
            rr = await client.post(
                "http://127.0.0.1:8000/api/chat",
                json={"prompt": body.prompt, "provider": provider},
            )
            return {"ok": True, "kind": "chat", "result": rr.json()}
    except Exception:
        logger.exception("route->chat failed")
        return {"ok": False, "error": "route_chat_failed"}

