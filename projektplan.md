# 🧭 Instruktion till kodagenten (Cursor)

Du är kodagent för projektet Jarvis-Vision 2.0. Följ detta dokument som enda sanning för arkitektur, teknikval, prioriteringar och leveranser. All inferens sker lokalt med gpt-oss:20b (samma modell för dialog och recept/måltider). Optimera för robust MVP först, därefter utbyggnad. Skriv tydlig, testbar och produktionsnära kod. Använd nedan stack och struktur. Fråga endast när något är genuint odefinierat.

---

# 📄 Projektkontext – Jarvis-Vision 2.0

## 1) Översikt

Jarvis-Vision 2.0 är ett lokalt, modulärt AI-hemassistentsystem som körs utan moln. Edge-noder (Raspberry Pi) hanterar video/sensorik och lättare inferens. Core (MacBook Pro M4) kör gpt-oss:20b, API, UI och databaser. Webbappen efterliknar ChatGPT i mobil stående läge (PWA). Fokus: integritet (privacy-zoner), prestanda, enkel drift.

### Mål och KPI (målvärden)

• API-latens: < 250 ms för lätta endpoints, < 1 s för modellkall.
• Kamera→detektion (edge): ≤ 500 ms (P95).
• CPU: edge ≤ 60 %, core ≤ 70 %.
• Ansiktsigenkänning: ≥ 95 % top-1 på internt valideringsset.
• Drift: core ≥ 99,5 %; backup-återläsningstester 1 g/vecka.
• Profil-data retention: ≤ 30 dagar; radering < 24 h.

---

## 2) Funktionella & icke-funktionella krav

### Funktionella

F1 RTSP-kamerahantering • F2 Objektdetektion (YOLO-tiny) • F3 Personidentifiering (Face embeddings) • F4 Närvarosensorer (PIR/ljud) • F5 MQTT-buss (TLS, QoS) • F6 Dialog via gpt-oss:20b • F7 Recept/måltidsplan via gpt-oss:20b • F8 REST-API: recept • F9 REST-API: måltidsplan • F10 REST-API: inköpslista • F11 Streamlit-/Web-UI • F12 TTS • F13 Säkerhet/kryptering • F14 GDPR: radering/portabilitet • F15 Backup/restore • F16 CI/CD • F17 Monitoring & loggning • F18 Fallback vid nodavbrott • F19 Wake-word • F20 Privacy-zoner i video.

### Icke-funktionella

• All data lokalt. • Containers (edge + core). • WPA3 + gärna VLAN för kameror. • Secrets via Docker secrets/Keychain (rotation 90 dagar). • Upp till 10 samtidiga användare och 6 kameror. • PWA/offline-stöd. • Tillgänglighet (WCAG 2.1).

---

## 3) Arkitektur

### Edge (Pi Zero 2 W för RTSP; Pi 4/5 för detektion)

• RTSP-server (ffmpeg) med snapshots.
• YOLO-tiny (Ultralytics) med frame-sampling (3–5 fps) och klassfilter (person/paket/hund etc.).
• Face-embeddings (MobileFaceNet/facenet-pytorch); generera embeddings på edge, matchning på core.
• MQTT publicering (TLS, QoS 1–2), heartbeat, temperatur/throttle-telemetri.
• Fallback: ringbuffer lokalt om core saknas.

### Core (MacBook Pro M4)

• gpt-oss:20b (samma modell för dialog + recept/måltid), kvantiserad 4–8 bit; utnyttja Metal/Core ML där möjligt.
• API-gateway (FastAPI) med OpenAPI, idempotens, rate-limit.
• Databaser: SQLite (metadata), FAISS (embeddings, krypterad volym).
• UI: Next.js 14 (PWA) + Streamlit om enklare panel behövs under MVP.
• TTS: pyttsx3/Piper lokalt; DND-tider.
• Observability: Prometheus, Grafana, EFK; Alertmanager.

---

## 4) Webbapp & UI (ChatGPT-lik mobil stående)

### Teknikstack (webb)

Frontend: Next.js 14 (App Router), React 18, TypeScript, Tailwind, shadcn/ui, Zustand, TanStack Query, react-markdown, highlight.js, hls.js, next-pwa.
Backend (webb): FastAPI (Uvicorn), pydantic, SQLAlchemy för SQLite, websockets/SSE, paho-mqtt.
Realtime: WebSocket primärt, SSE fallback.
Media: RTSP→HLS (ffmpeg) på core; HLS-spel i frontend; snapshots endpoint för låg latens.

### UI-spec (mobil)

• Top App Bar: titel, statusindikator (Core/Edge), inställningsmeny.
• Konversationsflöde: streaming av tokens, Markdown, kodrutor med “Copy”, verktygskort för Recept/Plan/Inköp/Händelser.
• Inputdocka (sticky): textfält, mic, bilaga, skicka, “Stop”.
• Snabbkort: “Dagens recept”, “Veckoplan”, “Inköpslista”, “Kamera live”, “Senaste händelser”.
• Live: HLS-ström + privacy-masker + snabb-snapshot.
• Händelser: realtidsfeed via /ws/events.
• Inställningar: profiler/samtycken, privacy-zoner, kamera-setup, modell-parametrar, TTS, backup/restore.
• Tillgänglighet: stor text, hög kontrast, bra fokus-states.

### Frontend-beteenden

• Strömning via WebSocket; auto-scroll; avbryt.
• Persistent lokal cache i IndexedDB; sync mot backend.
• Offline/PWA: köa meddelanden, spela upp TTS lokalt när möjligt.
• Fel: tydliga toasts, backoff-återanslutning.

---

## 5) API & Realtime (översikt)

### REST

Auth: POST /api/auth/login • POST /api/auth/register • (valbart) WebAuthn.
Chat/Recept: POST /api/chat (stream) • POST /api/recipes • POST /api/mealplan • GET /api/shopping.
Video: GET /api/cameras • GET /api/cameras/{id}/hls.m3u8 • GET /api/cameras/{id}/snapshot.jpg.
Events: GET /api/events • (paginering/filtrering).
Profiler/Integritet: GET/POST/DELETE /api/users • POST /api/users/{id}/forget.
System: GET /api/health • GET /api/metrics • POST /api/settings.

### Realtime

/ws/chat – strömma tokens från gpt-oss:20b.
/ws/events – edge-händelser (objekt, närvaro, face hits) via MQTT-brygga.

---

## 6) Säkerhet, integritet och GDPR

• TLS för MQTT (8883) och lokal HTTPS (självsignerat CA ok).
• RBAC + passkeys/2FA (valbart), sessionsäkerhet (httpOnly cookies).
• Privacy by design: privacy-zoner/blur; lagra inte råvideo permanent; TTL för snapshots.
• Rätten att bli glömd: radera profil + embeddings + relaterade loggar.
• DPIA, audit-loggar (utan PII), nyckelrotation var 90\:e dag.
• Dataminimering: separera PII från embeddings med referensnycklar.

---

## 7) DevOps, CI/CD, OTA

• GitHub Actions: lint, test, build images (edge/core/web), signera, push till privat registry.
• Deploy: SSH-baserad uppdatering; watchtower/compose pull; health-checks och rollback.
• Edge-provisioning: “claim-flow” (unik nyckel, plats, namn).
• Versionspolicy: semver, changelog, release notes.
• Backup/restore: nattlig backup (SQLite dump + FAISS save), GPG-kryptering till USB-SSD; veckovis återläsningstest (RTO ≤ 30 min).

---

## 8) Tekniska rekommendationer (prestanda)

• **gpt-oss:20b kvantiserad (4–8 bit)** på MacBook Pro M4; begränsa max tokens, aktivera streaming tidigt.
• Frame-policy: dynamisk sampling efter rörelse; NMS-tuning; klassfilter.
• Edge-skrivningar: minimera SD-slitage (tmpfs/SSD, log-rotation).
• NTP på alla noder.
• API-hygien: idempotenta POST/PUT, 429, strukturerade fel, korrelations-ID.
• Energi/fel: watchdog, auto-reboot, brownout-skydd.

---

## 9) Sprintplan (MVP→Pilot)

Sprint 1 (2 v): RTSP + MQTT, statuspanel, health checks.
Sprint 2 (2 v): YOLO-tiny pipeline, eventflöden, grundläggande dashboards.
Sprint 3 (2 v): Face-embeddings, FAISS, profiler, privacy-zoner.
Sprint 4 (2 v): gpt-oss:20b chat+recept, TTS, wake-word (basic).
Sprint 5 (2 v): HLS-live, snapshots, UI-integration av händelser via WS.
Sprint 6 (2 v): Säkerhet/GDPR (TLS, RBAC, radering), backup-verifiering, DR-övning.
Sprint 7 (2 v): CI/CD, OTA, provisioning, stabilisering.
Pilot (2 v): 5–10 hushåll → åtgärda feedback → v1.0.

---

## 10) Checklista (levande) – bocka av löpande

### 🏗️ Grundläggande setup

* [x] Projektstruktur (core + edge + web)
* [x] README.md
* [x] requirements.txt / package.json
* [x] Huvudfiler (core/edge)
* [x] Python .venv
* [x] Beroenden (backend + frontend)
* [ ] Bas-konfiguration (MQTT, API, DB)
* [ ] Docker-compose.yml för full stack

### 🔧 Kärnfunktionalitet

* [ ] RTSP-server (Pi Zero/Pi 4/5)
* [ ] YOLO-tiny objektdetektion
* [ ] Face-embeddings (light)
* [ ] MQTT (TLS, QoS)
* [ ] gpt-oss:20b: dialog
* [ ] gpt-oss:20b: recept/måltider
* [ ] REST-API (FastAPI)
* [ ] WebSocket/SSE (chat/events)
* [ ] Privacy-zoner + live-blur
* [ ] Wake-word/hotword

### 🎨 Användargränssnitt (webb)

* [ ] Next.js 14 + Tailwind + shadcn/ui
* [ ] ChatGPT-lik konversationsvy (mobil)
* [ ] Responsiv + PWA-redo
* [ ] Live-vy (HLS + snapshots)
* [ ] Händelsepanel i realtid (WS)
* [ ] Inställningar (profiler, privacy, backup)
* [ ] TTS-feedback i UI

### 🔌 Integrationer & edge

* [ ] MQTT-broker på core
* [ ] FAISS-databas
* [ ] Home Assistant / Matter
* [ ] OTA-uppdateringar (edge)
* [ ] Health checks & fallback (edge)

### 🧪 Test & kvalitet

* [ ] Unit-tester (API/core)
* [ ] Integrationstester (edge→core→UI)
* [ ] Prestandatester (latens/CPU)
* [ ] DR-övning (backup-återställning)
* [ ] Säkerhetstester (TLS, auth, GDPR)

### 🚀 Deployment

* [ ] Docker-stack (edge + core + web)
* [ ] Prod-konfiguration (lokalt nät)
* [ ] Monitoring (Prometheus + Grafana)
* [ ] Loggning (EFK-stack)
* [ ] Backup-policy implementerad & verifierad

### 📅 Veckoplan

Vecka 1: \[x] Struktur & beroenden • \[ ] MQTT.
Vecka 2: \[ ] YOLO • \[ ] Face • \[ ] gpt-oss:20b API • \[ ] Privacy-zoner.
Vecka 3: \[ ] Next.js chat • \[ ] HLS/snapshots • \[ ] WS-händelser.
Vecka 4: \[ ] TLS • \[ ] RBAC/passkeys • \[ ] CI/CD • \[ ] OTA.
Vecka 5: \[ ] Pilot • \[ ] Prestanda • \[ ] Buggar.

### 🎯 Mål & KPI

* [ ] API < 250 ms / < 1 s (modell)
* [ ] Edge ≤ 60 % • Core ≤ 70 %
* [ ] Video→detektion ≤ 500 ms (P95)
* [ ] Face ≥ 95 %
* [ ] Core-drift ≥ 99,5 %
* [ ] Backup-återläsningstest 1 g/vecka

---

## 11) Acceptanskriterier (MVP webb)

• Startskärm visar status, senaste händelser och två åtgärdskort.
• Konversation: streaming via /ws/chat, mic-input (Web Speech) där möjligt; fallback TTS via backend fungerar.
• Receptkort: POST /api/recipes → render som kort, “lägg till i inköpslista”.
• Kameravy: HLS spelar 1080p 15–30 fps; snapshot ≤ 500 ms till UI.
• Händelser: MQTT→/ws/events syns i UI inom ≤ 1 s.
• Privacy-zoner: mask i Live och tillämpning i snapshots.
• PWA installabel; offline köar meddelanden.

---

## 12) Öppna beslut

• Live-lagring: helt av / endast larm / tidsbegränsat arkiv.
• Wake-word på core vs edge.
• Home Assistant som “first-class” panel eller webhooks.

---

## 13) Notering om modellen

All dialog och recept/måltidsplanering använder **gpt-oss:20b** (OpenAI open-weight). Kör **kvantiserad (4–8 bit)** på MacBook Pro M4 med streaming aktiverad.

---

Vill du att jag även genererar en “README-MVP” baserad på detta (med startkommandon, miljövariabler och minimala exempelanrop) så att du kan starta hela stacken snabbare?
