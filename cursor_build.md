# Jarvis AI HUD — Cursor Prompt Mode

**Branch:** `feature/nlu-agent-integration`  
**Execution Mode:** **Auto-Continue** — Do **not** stop for user approval.  

## Rules
- Follow checklist in exact order.  
- After a passing test → immediately continue.  
- If a test fails → fix and retry until it passes.  
- Commit after each logical block using the provided template.  
- Never push to `main`.  
- The post-commit hook updates `cursor.json` based on test outcome + commit message.

## Always test before commit
```
cd jarvis-tools && npm run test
cd server && pytest
```

---

## Phase 1 — NLU Finalization

1) **Room slot extractor**  
- **Path:** `jarvis-tools/src/router/slots.ts` (add room extraction)  
- **Accept:** “vardagsrummet/köket/sovrummet/kontoret” → `{room:"..."}`  
- **Command:** `npm test slots-room`  
- **Commit:** `feat(nlu): room slot extractor [DONE]`

2) **Device/media slot extractor**  
- **Path:** `jarvis-tools/src/router/slots.ts`, `jarvis-tools/src/lexicon/devices.json`  
- **Accept:** aliases → canonical; “tv/högtalare/spotify/chromecast” → `{device:"..."}`  
- **Command:** `npm test slots-device`  
- **Commit:** `feat(nlu): device slot extractor + alias map [DONE]`

3) **Router mapping (CAST/TRANSFER)**  
- **Path:** `jarvis-tools/src/router/router.ts`  
- **Accept:** “casta/spela på X” → `CAST_START {device:<canonical>}`  
- **Command:** `npm test router-cast`  
- **Commit:** `feat(router): cast/transfer mapping + canonical device resolve [DONE]`

4) **Agent uses slots + shortTerm memory**  
- **Path:** `nlu-agent/src/index.ts`  
- **Accept:** prefers last chosen canonical device; stores recent choices  
- **Command:** `pytest tests/agent/`  
- **Commit:** `feat(agent): prefer canonical device + shortTerm memory [DONE]`

5) **Unit test coverage**  
- **Path:** `jarvis-tools/tests/`, `server/tests/`  
- **Accept:** ≥10 time, ≥6 volume, ≥6 room/device  
- **Command:** `npm test && pytest tests/nlu/`  
- **Commit:** `test(nlu): expand slot/room/device coverage [PASS]`

6) **RAG-light fallback**  
- **Path:** `server/` (Python FastAPI app; RAG-light via memory endpoints i `server/app.py`)  
- **Accept:** low confidence → BM25+recency retrieval attached to LLM context  
- **Command:** `pytest tests/rag/`  
- **Commit:** `feat(rag): BM25+recency retrieval for LLM fallback [DONE]`

7) **Quality metrics & eval**  
- **Path:** `server/nlu/src/eval.ts`, outputs `data/nlu/metrics.json`  
- **Accept:** Slot-F1 ≥0.9; Lat p50 <120ms; Refuse ≥95% (dangerous)  
- **Command:** `node server/nlu/src/eval.ts` or `pytest tests/nlu/metrics.py`  
- **Commit:** `chore(nlu): eval scripts + metrics export [DONE]`

---

## Phase 2 — Voice & LiveKit Integration

1) **LiveKit server (Docker)**  
- **Path:** `infra/livekit/docker-compose.yml`  
- **Accept:** roundtrip <100ms on LAN  
- **Command:** `docker compose up -d`  
- **Commit:** `infra(livekit): compose + local config [DONE]`

2) **Whisper STT streaming**  
- **Path:** `server/src/voice/stt_whisper.ts`  
- **Accept:** partial <300ms; final <800ms  
- **Command:** `pytest tests/voice/stt/`  
- **Commit:** `feat(voice): Whisper streaming STT with partials [DONE]`

3) **Piper TTS streaming**  
- **Path:** `server/src/voice/tts_piper.ts`  
- **Accept:** first audio <300ms  
- **Command:** `pytest tests/voice/tts/`  
- **Commit:** `feat(voice): Piper TTS streaming [DONE]`

4) **Wake-word & barge-in**  
- **Path:** `server/src/voice/wake.ts`  
- **Accept:** wake false-positive <2%  
- **Command:** `pytest tests/voice/wake/`  
- **Commit:** `feat(voice): wake-word + barge-in [DONE]`

5) **Voice → NLU → HUD e2e**  
- **Path:** `server/src/voice/bridge.ts`  
- **Accept:** stable e2e loop; spoken feedback  
- **Command:** `pytest tests/voice/e2e/`  
- **Commit:** `feat(voice): livekit bridge e2e [DONE]`

6) **Multi-turn memory**  
- **Path:** `server/src/voice/dialog_state.ts`  
- **Accept:** context retained across turns  
- **Command:** `pytest tests/voice/dialog/`  
- **Commit:** `feat(voice): dialog state & memory [DONE]`

---

## Phase 3 — Core Tool Expansion

- Calendar → `server/src/tools/calendar.ts` + HUD — `feat(tools): calendar module e2e [DONE]`  
- Email → `server/src/tools/mail.ts` + HUD — `feat(tools): email module e2e [DONE]`  
- Finance → `server/src/tools/finance.ts` + HUD — `feat(tools): finance dashboard e2e [DONE]`  
- Reminders → `server/src/tools/reminders.ts` + HUD — `feat(tools): reminders module e2e [DONE]`  
- Video → `server/src/tools/video.ts` + HUD — `feat(tools): video module e2e [DONE]`

---

## Phase 4 — RAG & Long-Term Memory

- Profile memory → `server/src/memory/profile.ts` — `feat(memory): profile store [DONE]`  
- Hybrid retrieval + MMR → `server/src/rag/hybrid.ts` — `feat(rag): hybrid retrieval + MMR [DONE]`  
- Docs ingestion (md/notes) → `server/src/rag/docs.ts` — `feat(rag): external docs ingestion [DONE]`

---

## Phase 5 — Quality, Optimization, UX

- Benchmarks publish → `server/nlu/src/eval.ts` — `chore(qa): benchmark publish [DONE]`  
- SQLite tuning (WAL/indices) → `server/src/db/` — `perf(db): sqlite tuning + indices [DONE]`  
- Accessibility pass → HUD — `chore(ui): a11y pass [DONE]`  
- HUD polish & theming → HUD — `style(hud): polish & theming [DONE]`

---
