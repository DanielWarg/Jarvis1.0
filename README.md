# Jarvis HUD — Web HUD + FastAPI backend

Installationsbar web‑HUD för Jarvis, byggd med Next.js (App Router), React och Tailwind. Backend kör FastAPI. HUD:en är optimerad för snabb uppstart (Safe Boot) och kan packas som desktop‑app senare.

## Funktioner
- HUD‑paneler: system, väder, to‑do, diagnostics, journal/intent‑queue, media.
- Overlay‑moduler: kalender, mail, finans, påminnelser, plånbok (stub), video.
- Spotify‑integration (Web API + Web Playback SDK):
  - OAuth (popup), enhetslista, play/queue, sök, spellistor.
  - Auto‑init: vid sidladdning initieras spelaren och transfereras (med retry) om token finns. Journal visar “Spotify connected”.
  - Klient‑intent: “spela/starta …” söker och spelar första/korrekta träffen (stänger av shuffle, queue‑fallback vid behov).
- Safe Boot: kamera/röst/bakgrund kan centralt stängas av.

## Tech Stack
- Frontend: Next.js 15 (App Router), React 19, Tailwind CSS v4, next‑pwa.
- Backend: FastAPI, httpx, orjson, python‑dotenv, SQLite‑baserat minne.

## Snabbstart
1) Backend (.venv)
```
python3 -m venv .venv
source .venv/bin/activate
pip install fastapi "uvicorn[standard]" httpx orjson python-dotenv
uvicorn server.app:app --host 127.0.0.1 --port 8000
```

2) Frontend
```
cd web
npm install
npm run dev -- -p 3100
```
Öppna http://localhost:3100

## Spotify‑konfiguration
1) Skapa en app på Spotify Developer Dashboard.
2) Lägg till redirect URI: `http://127.0.0.1:3100/spotify/callback`.
3) Skapa `.env` i projektroten (läses av backend via python‑dotenv):
```
SPOTIFY_CLIENT_ID=xxxx
SPOTIFY_CLIENT_SECRET=xxxx
SPOTIFY_REDIRECT_URI=http://127.0.0.1:3100/spotify/callback
```
4) Kör backend, öppna HUD → “Connect Spotify”. Efter första login kommer auto‑initen att aktivera “Jarvis HUD” automatiskt och Journal visar “Spotify connected”. Om auto‑transfer inte hinner: klicka “Starta spelare” en gång.

## Projektstruktur
```
Jarvis/
├─ project_plan.md
├─ README.md
├─ requirements.md
├─ server/
│  ├─ app.py
│  └─ data/
├─ web/
│  ├─ app/
│  ├─ public/
│  ├─ next.config.mjs
│  └─ package.json
```

## Konfiguration
- Safe Boot: `web/app/page.js` → `const SAFE_BOOT = true` (aktiverad i fallback‑läget).
- PWA manifest: `web/public/manifest.json`.

## Fallback & Recovery
- Nyaste stabila Spotify‑läget (auto‑start):
```
git reset --hard fallback-spotify-autostart-2025-08-12 && git clean -fd
```
- Tidigare stabilt Spotify‑läge:
```
git reset --hard fallback-spotify-stable-2025-08-12 && git clean -fd
```

## Roadmap (kort)
- Intent‑router (backend/UI) som väljer mellan chat, HUD‑kontroll och media.
- RAG med MMR + reranker och profilminne (personas/preferenser).
- Röst: streaming STT/TTS, wake‑word, barge‑in.

## NLU/Agent‑router
- Se `npl_ml.md` för en komplett plan att införa en lättvikts NLU‑service, agent‑router och verktygslexikon (svenska). Inkluderar slot‑filling (tid/volym/språk), talord→siffror, vaga tidsuttryck, device‑fuzzy, NONE‑policy, validering + auto‑fix + retry, samt svenska few‑shots.

## Prestanda & Tillgänglighet
- ORJSON‑svar i backend, WS‑journal i HUD.
- Aria‑labels på knappar; unika SVG‑ids via `useId`.

## Licens
TBD
