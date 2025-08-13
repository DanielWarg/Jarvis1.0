## ✅ NLU/ML Implementation Checklist – Jarvis

### Fas 1 – Grundfiler och datamodell

- [x] Skapa `data/nlu/intents.jsonl` med 10 intents × 20 exempel + 50 NONE-exempel. (220 exempel)
- [x] Implementera `server/nlu/src/train_nlu.ts` – liten klassificerare (Bayes över tokeniserad text).
- [x] Implementera `server/nlu/src/serve.ts` – endpoint `/classify` som returnerar `{intent, score}`.
- [x] Lägg in lexikon för tider, enheter, rum, volym. (tider/volym klara; device‑alias påbörjat)

### Fas 2 – Slot Extractors (rules‑first)

- [x] `slots.ts` – Rensa regex från onödiga `\` och fixa felaktiga grupper. (volym/tid förbättrade; "från början" → START)
- [x] Implementera tid (relativ/absolut, “strax över”, “ett par minuter”). (sek/min + vaga uttryck + HMS)
- [x] Implementera volym/mängd (procent, steg upp/ner).
- [ ] Implementera plats/rum (vardagsrum, kök).
- [ ] Implementera device/media (TV, Spotify, lampa).
- [ ] Enhetstester: minst 10 för tid, 6 för volym, 6 för rum/device.

### Fas 3 – Verktyg & Validering

- [x] `tools.ts` – Zod‑validering för parametrar (alla media‑verktyg).
- [x] Skapa mappning intent → verktyg. (PLAY, PAUSE, STOP, SEEK, SET_VOLUME, MUTE/UNMUTE, SHUFFLE, REPEAT, QUEUE, TRANSFER)
- [x] Säkerställ att alla `params` är validerade innan exekvering. (Zod i `jarvis-tools/src/schema/tools.ts` + agent)

### Fas 4 – Agent Router

- [x] `router.ts` – Rensa escape‑tecken (synonymer + prioritering för CAST).
- [x] Implementera POST `/agent/route`:
  - [x] Extract → Classify → MapIntentToTool → Validate(Zod).
  - [x] Returnera `{plan, confidence, needs_confirmation:true}` eller `{fallback:"llm"}`.
  - [x] Logga till `data/logs/agent_traces.jsonl`.
  - [x] ML‑fallback (`/classify`) med NONE‑policy och tröskel.

### Fas 5 – Minne & RAG

- [x] Korttidsminne (senaste 20 kommandon + state) i agent.
- [x] Enkel preferens‑store (alias/enhetsval/favoritartister) i agent.
- [ ] Retrieval + MMR vid LLM‑fallback.

### Fas 6 – Kvalitetskontroll

- [x] Eval‑script med micro/macro‑F1 och latens (se `server/nlu/src/eval.ts`).
- [ ] Slot‑F1 ≥ 0.9 (tid, volym).
- [ ] Latens p50 < 120 ms utan LLM.
- [ ] “Refuse when unsure” fungerar i ≥95% av farliga kommandon.


