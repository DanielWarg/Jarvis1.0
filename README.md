

```
      ██╗ █████╗ ██████╗ ██╗   ██╗██╗███████╗
      ██║██╔══██╗██╔══██╗██║   ██║██║██╔════╝
      ██║███████║██████╔╝██║   ██║██║███████╗
 ██   ██║██╔══██║██╔══██╗██║   ██║██║╚════██║
 ╚█████╔╝██║  ██║██║  ██║╚██████╔╝██║███████║
  ╚════╝ ╚═╝  ╚═╝╚═╝  ╚═╝ ╚═════╝ ╚═╝╚══════╝
             The Ultimate AI Assistant
```


──────────────────────────────

# 🚀 JARVIS HUD — Local AI with Voice, Vision & Memory

*"Your personal AI. Local. Private. Limitless."*

---

🌌 Vision
Jarvis HUD is a self-hosted AI powerhouse.
It listens, speaks, understands Swedish commands with precision, remembers context, and controls your world — from media to email, calendars, IoT, and beyond — all inside a sleek, futuristic heads-up display.

Built for speed, privacy, and total control — no cloud lock-in, no compromises.

<div style="background-color:#0d1117;padding:20px;border-radius:10px;text-align:center;"> <img src="docs/image.png" alt="Jarvis HUD — Local AI with Voice, Vision & Memory in a Futuristic Interface" style="max-width:100%;border-radius:8px;"> <p style="color:#8b949e;font-style:italic;">Preview of the Jarvis HUD interface</p> </div>

---

## ✨ Features

* **Futuristic HUD Panels** — System stats, weather, to-do, diagnostics, journal, and media.
* **Overlay Modules** — Calendar, email, finance, reminders, wallet, video feeds.
* **Spotify Control** — OAuth login, playback, queue, search, playlists, auto device sync.
* **Smart Intent Routing** — Natural language → NLU → Agent → Tool.
* **Safe Boot Mode** — Kill camera/mic instantly.
* **Extensible Tools** — Ready for API, IoT, and custom agent integration.

---

## 🛠 Tech Stack

**Frontend:** Next.js 15, React 19, Tailwind CSS v4, next-pwa
**Backend:** FastAPI, httpx, orjson, python-dotenv, SQLite memory store
**AI Core:** `gpt-oss:20B` (Ollama), RAG retrieval, Whisper STT, Piper TTS

*Chosen for modern rendering, real-time capabilities, local-first AI execution, and minimal latency.*

---

## ⚡ Quick Start

### Backend

python3 -m venv .venv
source .venv/bin/activate
pip install fastapi "uvicorn\[standard]" httpx orjson python-dotenv
uvicorn server.app\:app --host 127.0.0.1 --port 8000

### Frontend

cd web
npm install
npm run dev -- -p 3100

Then open: [http://localhost:3100](http://localhost:3100)

---

## 🎵 Spotify Setup

1. Create an app in [Spotify Developer Dashboard](https://developer.spotify.com/dashboard/).
2. Add redirect URI:
   [http://127.0.0.1:3100/spotify/callback](http://127.0.0.1:3100/spotify/callback)
3. Create `.env` in project root:

SPOTIFY\_CLIENT\_ID=xxxx
SPOTIFY\_CLIENT\_SECRET=xxxx
SPOTIFY\_REDIRECT\_URI=[http://127.0.0.1:3100/spotify/callback](http://127.0.0.1:3100/spotify/callback)

4. Start backend, open HUD → Connect Spotify.

---

## 📂 Structure

Jarvis/
├─ README.md
├─ server/         # FastAPI backend
├─ web/            # Next.js frontend
├─ project\_plan.md
├─ requirements.md

---

## 🧠 Master Build Checklist

### Phase 1 — NLU Finalization (in progress)

* Slot extractors for room/device/time/volume
* Router mapping + alias & prefs in agent
* Unit tests (≥10 time, ≥6 volume, ≥6 room/device)
* RAG retrieval for LLM fallback
* Eval: Slot-F1 ≥ 0.9, latency p50 < 120ms, 95% refuse when unsure

### Phase 2 — LiveKit & Voice (planned)

* Local LiveKit server (<100ms RTT)
* Whisper STT, Piper TTS
* Wake-word + barge-in
* Multi-turn with memory

### Phase 3 — Core Tools (upcoming)

* Calendar, email, finance, reminders, video

### Phase 4 — Long-term Memory (upcoming)

* Profiles, contextual retrieval, doc integration

### Phase 5 — Optimization & UX (upcoming)

* Latency/stress tests, SQLite tuning, accessibility, HUD polish

---

## 🛡 Fallback

**Latest stable Spotify auto-start:**
git reset --hard fallback-spotify-autostart-2025-08-12 && git clean -fd

**Previous stable Spotify version:**
git reset --hard fallback-spotify-stable-2025-08-12 && git clean -fd

---

## 🤝 Contributing

We welcome pull requests, bug reports, and feature suggestions.

1. Fork the repo
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## 📜 License

TBD

---
