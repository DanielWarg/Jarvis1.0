## Harmony-implementering: Checklista

Kort mål: Inför Harmony Response Format end-to-end (kanaler: `analysis`, `commentary`, `final`) med server-side tool-exec och bibehållen router-först för snabba intents. Allt bakom feature-flaggor.

### Fas 0 – Baseline och säkerhetslina
- [x] Skapa branch `feature/harmony`
- [ ] Lägg env-flaggor i servern: `USE_HARMONY=false`, `USE_TOOLS=false`
- [ ] Lägg README-avsnitt: hur man togglar flaggor och kör lokalt
- [ ] Sätt upp `.venv` i `server/` och frys beroenden

```bash
cd server
python3 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -r requirements.txt || true
```

- [x] Skapa QA/acceptans-checklista-fil `docs/harmony_acceptance.md` (referera till kriterier längst ned i denna fil)

### Fas 1 – Harmony-adapter i servern
- [ ] Skapa adapter-lager i `server/app.py` som bygger Harmony-meddelanden (roller: `system`, `developer`, `user`)
- [ ] Instruktioner till modellen: resonemang i `analysis`, tool-calls i `commentary`, endast svar i `final`
- [ ] Parsning: extrahera endast kanal `final` till klient (filtrera bort `analysis`/`commentary`)
- [ ] Lägg debug-loggning i dev: roll + kanal (aldrig `analysis`-innehåll i prod)
- [ ] Enhetstest: given syntetiskt Harmony-svar → parsern ger rätt `final` och fångar `tool_call`

### Fas 2 – Verktygsregister och validering
- [x] Skapa `server/tools/registry.py` med verktygsspecar (namn, beskrivning, JSON-schema)
- [x] Implementera exekvering med Pydantic-validering (no-tool-if-unsure)
- [x] Första verktyg: `PLAY`, `PAUSE`, `SET_VOLUME`, `SAY`/`DISPLAY`
- [ ] Enhetstest: fel parametrar → vägran/klargörande, inte exekvering

### Fas 3 – Körsätt för gpt-oss lokalt
- [x] Välj körsätt: Transformers-gateway (rekommenderat) eller Ollama-adapter
- [x] Dokumentera valet i `docs/AGENT_README.md`
- [ ] Transformers: skapa liten gateway som accepterar Harmony-messages och returnerar kanaler/tool-calls
- [ ] Smoke-test: modell svarar i rätt kanaler (ingen läcka till UI)

### Fas 4 – Prompts och policys
- [ ] Skapa `server/prompts/system_prompts.py` (svenska, kort persona, capabilities, safety)
- [ ] Skapa developer-prompt: följ Harmony; "no-tool-if-unsure"; kort `final`
- [ ] Länka in i adapter-lagret

### Fas 5 – Router-först
- [ ] Behåll existerande NLU/router som förstaval (hög confidence → direkt exekvering)
- [ ] Lägg tröskel `NLU_CONFIDENCE_THRESHOLD` i env
- [ ] Lägre confidence/okända intents → skicka via Harmony + verktygsspec

### Fas 6 – Streaming och UI
- [ ] Servern streamar endast `final` till klient
- [ ] Lägg lätt metadata till UI: `tool_called`, `tool_result` (ingen `analysis`)
- [ ] Test: stream fallback → heltextsvar via `final`

### Fas 7 – Telemetri och loggning
- [ ] Logga p50/p95: tid till första `final`-token
- [ ] Logga: tid `tool_call` → `tool_result`, valideringsfel, no-tool-if-unsure
- [ ] Logga: router-vs-LLM hit-rate

### Fas 8 – Evals
- [ ] Skapa 20 kommandon som kräver verktyg (ska tool-callas)
- [ ] Skapa 20 rena chattfrågor (ska inte tool-callas)
- [ ] Skapa 10 fall med saknade parametrar (ska vägra/klargöra)
- [ ] Mål: ≥95% korrekt vägval, 0% `analysis`-läckage, p50 under mål för snabba intents

### Fas 9 – Utrullning i små PR:er
- [ ] PR1: flaggor + Harmony-adapter (final-extraktion/stream), inga verktyg
- [ ] PR2: tool-registry + validering kopplats, `USE_TOOLS=false`
- [ ] PR3: aktivera `USE_TOOLS=true` för 2–3 verktyg + "no-tool-if-unsure"
- [ ] PR4: router-först med tröskel
- [ ] PR5: telemetri + syntetiska evals

### Fas 10 – Dokumentation och runbooks
- [ ] Uppdatera `README.md`/`ARCHITECTURE.md`: hur Harmony funkar hos oss
- [ ] Runbook: lägga till nytt verktyg (spec, validator, exekverare, test)
- [ ] Felsökning: kanalläckage, valideringsfel, latensspikar

### Miljövariabler (läggs till och dokumenteras)
- [ ] `USE_HARMONY`, `USE_TOOLS`
- [ ] `HARMONY_REASONING_LEVEL=low|medium|high`
- [ ] `HARMONY_TEMPERATURE_COMMANDS=0.2`, `HARMONY_TEMPERATURE_CREATIVE=0.6`
- [ ] `NLU_CONFIDENCE_THRESHOLD`
- [ ] Lokal LLM: `TRANSFORMERS_MODEL_PATH` eller `OLLAMA_HOST`
- [ ] `MAX_TOKENS`, `TOP_P`, `LOG_LEVEL`

### Go-live Akzeptanskriterier (måste uppfyllas innan aktivering)
- [ ] "Pausa musiken" → router/Harmony-tool-call; UI får kort `final`-bekräftelse
- [ ] "Vad tycker du om låten?" → inga verktyg; endast `final`-text
- [ ] Otydlig fras ("kan du fixa det där?") → klargörande i `final`, ingen verktygskörning
- [ ] Saknade parametrar → vägran eller fråga; ingen chansning
- [ ] Telemetri: ≥95% korrekt vägval; 0% `analysis`-läckage; p50 under mål

---

Tips: Bocka av i ordning per fas. Håll PR:er små, bakom flaggor. Kör evals och akzeptans efter varje PR.


