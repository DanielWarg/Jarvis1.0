## Agent – Lokalt körsätt för gpt-oss (Fas 3)

Mål: Kör gpt-oss:20B lokalt med Harmony-kompatibelt gränssnitt. Rekommenderat: Transformers-gateway.

### Alternativ A (Rekommenderat): Transformers-gateway med Harmony

Fördelar: Kanalgaranti, enkel loggning, full kontroll.

1) Skapa Python-venv (om ej finns)
```bash
cd server
python3 -m venv .venv
source .venv/bin/activate
pip install -U pip
```

2) Installera nödvändigt (exempel – anpassa efter GPU/CPU)
```bash
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu
pip install transformers accelerate einops sentencepiece safetensors
# Harmony-stöd (se Cookbook/openai-harmony)
pip install openai-harmony
```

3) Kör en minimal gateway som accepterar Harmony-meddelanden och returnerar kanaler

Skapa en liten FastAPI-app (externt repo/skript) som:
- Tar `messages: [{role, content}]` och ev. `tools`.
- Kör modellen via Transformers.
- Returnerar endast `final` till klient och behåller `analysis`/`commentary` server-side.

4) Konfigurera Jarvis att använda gatewayn
```bash
export USE_HARMONY=true
export USE_TOOLS=false
# Pekar lokalt mot gateway-endpoint om skiljt från nuvarande (annars låt /api/chat använda Harmony-meddelanden)
```

5) Smoke-test
- Mata ett testprompt som ska ge `[FINAL]...[/FINAL]` och verifiera att `final` extraheras korrekt och att inga `analysis`-delar når UI.

### Alternativ B: Ollama + minimal adapter

Fördel: Enkelt om Ollama redan används. Nackdel: Inget inbyggt Harmony-stöd.

1) Använd befintliga `/api/generate` men bygg en strikt prompt:
- Prefixa med system/dev-instruktioner och kräv att modellen omsluter slutsvar i `[FINAL]...[/FINAL]` (gjort i `server/app.py` när `USE_HARMONY=true`).
- OBS: Detta är en kompromiss tills riktig Harmony-gateway används.

2) Smoke-test
- Kontrollera att modellen konsekvent producerar `[FINAL]...[/FINAL]` och att parsern i servern plockar final korrekt.

### Noteringar
- Harmony med full tool-calling kräver server-side exekvering (fas 2); vi har registry och exec-endpoint bakom flagga.
- Höj inte temperatur för kommandon. Använd `HARMONY_TEMPERATURE_COMMANDS=0.2` som default.
- Dokumentera GPU/CPU-val och modellens viktväg i teamets infra-docs.


