# Jarvis‑Vision 2.0 – Löpande README

Detta är en levande README som uppdateras löpande när vi gör framsteg. Följ `projektplan.md` för mål och arkitektur; denna fil fokuserar på hur du kör och vad som senast ändrats.

## Snabbstart (Core API)

- Aktivera virtualenv (zsh):
  - macOS (skapas redan):
    source .venv/bin/activate
- Installera beroenden:
  pip install -r requirements.txt
- Starta API (utveckling):
  uvicorn core.app.main:app --reload
- Hälso‑koll:
  GET http://localhost:8000/api/health

### Chat via Ollama (REST)

```bash
curl -s http://localhost:8000/api/chat \
  -H 'Content-Type: application/json' \
  -d '{"prompt":"Säg hej","model":"gpt-oss-20b","stream":false}'
```

### Chat via WebSocket

Skicka t.ex. denna text som första meddelande:

```json
{"prompt":"Säg hej","model":"gpt-oss-20b"}
```

## Projektstruktur

core/
  app/
    __init__.py
    main.py           # FastAPI app (health endpoint)
edge/
  agent.py            # Edge‑placeholder
web/
  package.json        # Next.js 14 skeleton (ej installerad ännu)
projektplan.md
README.md
requirements.txt

## Senaste ändringar

- Initierade projektstruktur `core/`, `edge/`, `web/`.
- Skapade `.venv` och basfiler för Core API och Edge‑agent.
- Lagt till `requirements.txt` (core/backend) och `web/package.json` (frontend).
- Uppdaterade checkrutor i `projektplan.md` för genomförda steg.

## Kommande (förslag)

- Core: definiera REST‑endpoints enligt plan (auth, chat, recipes, mealplan, shopping, cameras, events, users, system).
- Edge: MQTT‑heartbeat och RTSP‑placeholder.
- Web: initiera Next.js 14, lägg till Tailwind och shadcn/ui.
- Docker Compose för hel stack.

## Lokal modell (Ollama / GPT‑oss‑20b)

- Förutsätter att `ollama` är installerad och att modellen `gpt-oss-20b` finns lokalt.
- Snabbtest:
  ```bash
  ollama run gpt-oss-20b "Säg hej"
  ```
- Backend kommer att integrera mot Ollama för chat/recept enligt `projektplan.md` (REST + WS).
