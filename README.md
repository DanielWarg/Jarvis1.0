# Jarvis HUD — Next.js PWA

An installable web HUD for the Jarvis project, built with Next.js (App Router), React, and Tailwind. It starts fast in sandboxed environments (Safe Boot) and can be packaged as a desktop app later with minimal changes.

## Overview
- HUD UI: system metrics, voice input (stub), diagnostics, weather, to‑do list.
- Overlay modules: calendar, mail, finance, reminders, wallet (stub), video.
- Safe Boot: camera/voice/background visuals disabled by default.
- No MetaMask/Web3 code (wallet is a stub).

## Tech Stack
- Next.js 15 (App Router)
- React 19
- Tailwind CSS v4
- next-pwa (PWA enabled in production)

## Quick Start
1) Development
```
cd web
npm install
npm run dev -- -p 3100
```
Open http://localhost:3100

2) Production
```
cd web
npm run build
npm start
```

## Structure
```
Jarvis/
├─ project_plan.md
├─ README.md
├─ requirements.md
├─ web/
│  ├─ app/
│  ├─ public/
│  ├─ next.config.mjs
│  └─ package.json
└─ .gitignore
```

## Configuration
- Safe Boot toggle: `web/app/page.js` → `const SAFE_BOOT = true`.
- PWA manifest: `web/public/manifest.json`.

## Desktop Packaging (planned)
- Electron or Tauri (desktop). Capacitor optional (mobile).

See `requirements.md` for details.

## Deployment
- Recommended: Vercel. Alternative: Node hosting for Next.js 15.

## Accessibility & Performance
- Aria labels on icon buttons.
- Unique SVG ids via `useId`.

## License
TBD.
