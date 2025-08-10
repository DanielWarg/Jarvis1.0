# Requirements — Jarvis HUD

This document defines product and technical requirements for the web HUD that can later be packaged as a desktop application.

## Goals
- Fast, installable PWA with minimal friction (Safe Boot by default).
- Simple path to desktop packaging (Electron/Tauri) without major changes.

## Use Cases
- Power User: monitor metrics, open modules, quick actions.
- Developer: run locally in sandbox, toggle features, test UI without permissions.

## Functional Requirements
1. Shell & Layout
   - Top quick‑access buttons; footer status blocks.
2. Modules
   - System: CPU/MEM/NET gauges/metrics.
   - Voice: capture (stub in Safe Boot) and add to To‑do.
   - Jarvis Core animation.
   - Media controls (demo).
   - Weather: temp + description (stub).
   - To‑do: add/toggle/remove.
   - Overlay pages: Calendar, Mail (dummy), Finance (mini chart), Reminders, Wallet (stub), Video (webcam/URL; disabled in Safe Boot).
3. Diagnostics: self‑checks.
4. PWA: manifest + service worker in production.

## Non‑Functional Requirements
- Performance: TTI < 2s on modern hardware.
- Reliability: error boundary + global unhandled error capture.
- Accessibility: aria labels; good contrast; keyboard focusable.
- i18n readiness: minimal copy; future i18n possible.
- Privacy/Security: no privileged APIs by default; Safe Boot avoids prompts.

## Technical Requirements
- Node >= 18
- Next.js 15, React 19, Tailwind v4
- PWA via `next-pwa` (disabled in dev)
- Unique SVG ids via `useId`
- `SAFE_BOOT` flag in `web/app/page.js`

## Desktop Packaging
- Electron/Tauri wrapper loads the HUD.
- Acceptance: PWA and desktop wrapper share the same code without UI regressions.

## Future Extensions
- Real data (system monitor API, weather API)
- WebSocket live events
- AuthN/AuthZ for privileged tools
- Voice STT/TTS (with consent)
- Wallet via WalletConnect (mobile) or EIP‑6963 (desktop)

## Constraints & Risks
- iOS PWAs limited in background execution.
- Browser permission prompts for camera/mic require user interaction.

## Acceptance Criteria
- PWA installs on Chrome/Edge.
- Production build emits valid SW and manifest.
- Safe Boot default: renders without permission prompts; interactive HUD.
- Desktop wrapper loads HUD and modules function.
