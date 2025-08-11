"use client";

// SAFE BOOT: minimal risk för "Initializing environment" i sandlådan
// - Ren JavaScript (ingen TS)
// - Inga externa bibliotek
// - Partikelbakgrund och röst/video kan stängas av centralt

import React, { useEffect, useMemo, useRef, useState, useContext, createContext, useId } from "react";

const SAFE_BOOT = true; // <-- slå PÅ för att garantera uppstart i sandbox. Kan sättas till false när allt funkar.

// ────────────────────────────────────────────────────────────────────────────────
// Ikoner (inline SVG)
const Svg = (p) => (<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" {...p} />);
const IconPlay = (p) => (<Svg {...p}><polygon points="5 3 19 12 5 21 5 3" /></Svg>);
const IconSkipBack = (p) => (<Svg {...p}><polyline points="19 20 9 12 19 4" /><line x1="5" y1="19" x2="5" y2="5" /></Svg>);
const IconSkipForward = (p) => (<Svg {...p}><polyline points="5 4 15 12 5 20" /><line x1="19" y1="5" x2="19" y2="19" /></Svg>);
const IconThermometer = (p) => (<Svg {...p}><path d="M14 14.76V3a2 2 0 0 0-4 0v11.76" /><path d="M8 15a4 4 0 1 0 8 0" /></Svg>);
const IconCloudSun = (p) => (<Svg {...p}><circle cx="7" cy="7" r="3" /><path d="M12 3v2M12 19v2M4.22 4.22 5.64 5.64M18.36 18.36 19.78 19.78M1 12h2M21 12h2" /></Svg>);
const IconCpu = (p) => (<Svg {...p}><rect x="9" y="9" width="6" height="6" /><rect x="4" y="4" width="16" height="16" rx="2" /></Svg>);
const IconDrive = (p) => (<Svg {...p}><rect x="2" y="7" width="20" height="10" rx="2" /><circle cx="6.5" cy="12" r="1" /><circle cx="17.5" cy="12" r="1" /></Svg>);
const IconActivity = (p) => (<Svg {...p}><polyline points="22 12 18 12 15 21 9 3 6 12 2 12" /></Svg>);
const IconMic = (p) => (<Svg {...p}><rect x="9" y="2" width="6" height="11" rx="3" /><path d="M12 13v6" /></Svg>);
const IconX = (p) => (<Svg {...p}><line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" /></Svg>);
const IconCheck = (p) => (<Svg {...p}><polyline points="20 6 9 17 4 12" /></Svg>);
const IconClock = (p) => (<Svg {...p}><circle cx="12" cy="12" r="9" /><path d="M12 7v6h5" /></Svg>);
const IconSettings = (p) => (<Svg {...p}><circle cx="12" cy="12" r="3" /></Svg>);
const IconBell = (p) => (<Svg {...p}><path d="M6 8a6 6 0 1 1 12 0v6H6z" /></Svg>);
const IconSearch = (p) => (<Svg {...p}><circle cx="11" cy="11" r="8" /><line x1="21" y1="21" x2="16.65" y2="16.65" /></Svg>);
const IconWifi = (p) => (<Svg {...p}><path d="M2 8c6-5 14-5 20 0" /><path d="M5 12c4-3 10-3 14 0" /><path d="M8.5 15.5c2-1.5 5-1.5 7 0" /><circle cx="12" cy="19" r="1" /></Svg>);
const IconBattery = (p) => (<Svg {...p}><rect x="2" y="7" width="18" height="10" rx="2" /><rect x="20" y="10" width="2" height="4" /></Svg>);
const IconGauge = (p) => (<Svg {...p}><circle cx="12" cy="12" r="9" /><line x1="12" y1="12" x2="18" y2="10" /></Svg>);
const IconCalendar = (p) => (<Svg {...p}><rect x="3" y="4" width="18" height="18" rx="2" /><line x1="3" y1="10" x2="21" y2="10" /></Svg>);
const IconMail = (p) => (<Svg {...p}><rect x="3" y="5" width="18" height="14" rx="2" /><polyline points="3 7 12 13 21 7" /></Svg>);
const IconDollar = (p) => (<Svg {...p}><path d="M12 2v20" /><path d="M17 7a4 4 0 0 0-4-4 4 4 0 1 0 0 8 4 4 0 1 1 0 8 4 4 0 0 1-4-4" /></Svg>);
const IconAlarm = (p) => (<Svg {...p}><circle cx="12" cy="13" r="7" /><path d="M12 10v4l2 2" /><path d="M5 3l3 3M19 3l-3 3" /></Svg>);
const IconCamera = (p) => (<Svg {...p}><rect x="3" y="7" width="18" height="14" rx="2" /><circle cx="12" cy="14" r="4" /></Svg>);

// ────────────────────────────────────────────────────────────────────────────────
// Utils
const safeUUID = () => (typeof crypto !== "undefined" && crypto.randomUUID ? crypto.randomUUID() : `id-${Math.random().toString(36).slice(2)}-${Date.now()}`);
const clampPercent = (v) => Math.max(0, Math.min(100, Number.isFinite(v) ? v : 0));

// ────────────────────────────────────────────────────────────────────────────────
// Error boundary + global catcher
class ErrorBoundary extends React.Component {
  constructor(props) { super(props); this.state = { error: null }; }
  static getDerivedStateFromError(error) { return { error }; }
  componentDidCatch(error, info) { console.error("HUD crashed:", error, info); }
  render() {
    if (this.state.error) {
      const message = String(this.state.error?.message || this.state.error || "Unknown error");
      return (
        <div className="min-h-screen bg-[#030b10] text-cyan-100 p-8">
          <h1 className="text-xl font-semibold text-cyan-200">HUD Error</h1>
          <p className="mt-2 text-cyan-300/80">{message}</p>
          <button className="mt-6 rounded-xl border border-cyan-400/30 px-3 py-1 text-xs hover:bg-cyan-400/10" onClick={() => (location.href = location.href)}>Ladda om</button>
        </div>
      );
    }
    return this.props.children;
  }
}
function useGlobalErrorCatcher() {
  const [globalError, setGlobalError] = useState(null);
  useEffect(() => {
    const onError = (e) => setGlobalError(e?.message || "Unhandled error");
    const onRej = (e) => setGlobalError(String(e.reason?.message || e.reason || "Unhandled rejection"));
    window.addEventListener("error", onError);
    window.addEventListener("unhandledrejection", onRej);
    return () => { window.removeEventListener("error", onError); window.removeEventListener("unhandledrejection", onRej); };
  }, []);
  return { globalError };
}

// ────────────────────────────────────────────────────────────────────────────────
// HUD primitives
const GlowDot = React.memo(({ className }) => (
  <span className={`relative inline-block ${className || ""}`}>
    <span className="absolute inset-0 rounded-full blur-[6px] bg-cyan-400/40" />
    <span className="absolute inset-0 rounded-full blur-[14px] bg-cyan-400/20" />
    <span className="relative block h-full w-full rounded-full bg-cyan-300" />
  </span>
));
const RingGauge = ({ size = 180, value, label, sublabel, icon, showValue = true }) => {
  const pct = clampPercent(value); const r = size * 0.42; const c = 2 * Math.PI * r; const dash = (pct / 100) * c;
  const gradId = useId();
  const glowId = useId();
  return (
    <div className="relative grid place-items-center" style={{ width: size, height: size }}>
      <svg width={size} height={size} className="-rotate-90">
        <defs>
          <linearGradient id={`grad-${gradId}`} x1="0%" y1="0%" x2="100%" y2="0%"><stop offset="0%" stopColor="#22d3ee" /><stop offset="100%" stopColor="#38bdf8" /></linearGradient>
          <filter id={`glow-${glowId}`} x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="4" result="coloredBlur" /><feMerge><feMergeNode in="coloredBlur" /><feMergeNode in="SourceGraphic" /></feMerge></filter>
        </defs>
        <circle cx={size / 2} cy={size / 2} r={r} stroke="#0ea5b7" strokeOpacity="0.25" strokeWidth={10} fill="none" strokeDasharray={c} />
        <circle cx={size / 2} cy={size / 2} r={r} stroke={`url(#grad-${gradId})`} strokeWidth={10} fill="none" strokeLinecap="round" strokeDasharray={`${dash} ${c - dash}`} style={{ transition: "stroke-dasharray .6s ease" }} filter={`url(#glow-${glowId})`} />
      </svg>
      <div className="absolute inset-0 grid place-items-center">
        <div className="text-center">
          {(label || sublabel || showValue) && (<>
            <div className="flex items-center justify-center gap-2 text-cyan-300">{icon}{label && <span className="text-xs uppercase tracking-widest opacity-80">{label}</span>}</div>
            {showValue && (<div className="text-4xl font-semibold text-cyan-100">{Math.round(pct)}<span className="text-cyan-400 text-xl">%</span></div>)}
            {sublabel && <div className="text-xs text-cyan-300/80 mt-1">{sublabel}</div>}
          </>)}
        </div>
      </div>
    </div>
  );
};
function Metric({ label, value, icon }) { return (<div className="text-center"><div className="flex items-center justify-center gap-2 text-xs text-cyan-300/80">{icon} {label}</div><div className="text-2xl font-semibold text-cyan-100">{Math.round(value)}%</div></div>); }
const Pane = React.memo(({ title, children, className, actions }) => (
  <div className={`relative rounded-2xl border border-cyan-500/20 bg-cyan-950/20 p-4 shadow-[0_0_60px_-20px_rgba(34,211,238,.5)] ${className || ""}`}>
    <div className="flex items-center justify-between mb-3"><div className="flex items-center gap-2"><GlowDot className="h-2 w-2" /><h3 className="text-cyan-200/90 text-xs uppercase tracking-widest">{title}</h3></div><div className="flex gap-2 text-cyan-300/70">{actions}</div></div>
    {children}
    <div className="pointer-events-none absolute inset-0 rounded-2xl ring-1 ring-inset ring-cyan-300/10" />
  </div>
));

// ────────────────────────────────────────────────────────────────────────────────
// Hooks (simulerad data)
function useSystemMetrics() { const [cpu, setCpu] = useState(37); const [mem, setMem] = useState(52); const [net, setNet] = useState(8); useEffect(() => { const id = setInterval(() => { setCpu((v) => clampPercent(v + (Math.random() * 10 - 5))); setMem((v) => clampPercent(v + (Math.random() * 6 - 3))); setNet((v) => clampPercent(v + (Math.random() * 14 - 7))); }, 1100); return () => clearInterval(id); }, []); return { cpu, mem, net }; }
function useTodos() { const [todos, setTodos] = useState([{ id: safeUUID(), text: "Setup weather API key", done: false }, { id: safeUUID(), text: "Connect voice input", done: false }]); const add = (text) => setTodos((ts) => [{ id: safeUUID(), text, done: false }, ...ts]); const toggle = (id) => setTodos((ts) => ts.map((t) => (t.id === id ? { ...t, done: !t.done } : t))); const remove = (id) => setTodos((ts) => ts.filter((t) => t.id !== id)); return { todos, add, toggle, remove }; }
function useWeatherStub() { const [w, setW] = useState({ temp: 21, desc: "Partly cloudy" }); useEffect(() => { const id = setInterval(() => { setW({ temp: Math.round(18 + Math.random() * 10), desc: ["Sunny", "Cloudy", "Partly cloudy", "Light rain"][Math.floor(Math.random() * 4)] }); }, 5000); return () => clearInterval(id); }, []); return w; }
function useVoiceInput() {
  const [transcript, setTranscript] = useState(""); const [isListening, setIsListening] = useState(false); const recRef = useRef(null);
  useEffect(() => { if (SAFE_BOOT) return; const SR = typeof window !== 'undefined' && (window.webkitSpeechRecognition || window.SpeechRecognition); if (!SR) return; const rec = new SR(); rec.lang = "sv-SE"; rec.continuous = false; rec.interimResults = true; rec.onresult = (e) => { const text = Array.from(e.results).map((r) => r[0].transcript).join(" "); setTranscript(text); }; rec.onend = () => setIsListening(false); recRef.current = rec; }, []);
  const start = () => { if (SAFE_BOOT) { alert("Röstinput avstängd i Safe Boot"); return; } try { recRef.current && recRef.current.start(); setIsListening(true); } catch (_) {} }; const stop = () => { if (!SAFE_BOOT) recRef.current && recRef.current.stop(); };
  return { transcript, isListening, start, stop };
}

// ────────────────────────────────────────────────────────────────────────────────
// Command Bus / UI‑state
const HUDContext = createContext(null);
function useHUD() { const ctx = useContext(HUDContext); if (!ctx) throw new Error("useHUD must be inside provider"); return ctx; }
function HUDProvider({ children }) {
  const [state, setState] = useState({ overlayOpen: false, currentModule: null, videoSource: undefined });
  const dispatch = (c) => { setState((s) => { switch (c.type) { case "SHOW_MODULE": return { ...s, overlayOpen: true, currentModule: c.module }; case "HIDE_OVERLAY": return { ...s, overlayOpen: false, currentModule: null }; case "TOGGLE_MODULE": return { ...s, overlayOpen: s.currentModule === c.module ? false : true, currentModule: s.currentModule === c.module ? null : c.module }; case "OPEN_VIDEO": return { ...s, overlayOpen: true, currentModule: "video", videoSource: c.source }; default: return s; } }); };
  useEffect(() => { if (typeof window === 'undefined') return; window.HUD = { showModule: (m, payload) => dispatch({ type: "SHOW_MODULE", module: m, payload }), hideOverlay: () => dispatch({ type: "HIDE_OVERLAY" }), openVideo: (source) => dispatch({ type: "OPEN_VIDEO", source }), toggle: (m) => dispatch({ type: "TOGGLE_MODULE", module: m }) }; }, []);
  return <HUDContext.Provider value={{ state, dispatch }}>{children}</HUDContext.Provider>;
}

// ────────────────────────────────────────────────────────────────────────────────
// Overlay + moduler
function Overlay() { const { state, dispatch } = useHUD(); if (!state.overlayOpen || !state.currentModule) return null; return (<div className="fixed inset-0 z-50 grid place-items-center pointer-events-none"><div className="pointer-events-auto relative w-[min(90vw,920px)] rounded-2xl border border-cyan-400/30 bg-cyan-950/60 backdrop-blur-xl p-5 shadow-[0_0_80px_-20px_rgba(34,211,238,.6)]"><button aria-label="Stäng" onClick={() => dispatch({ type: "HIDE_OVERLAY" })} className="absolute right-3 top-3 rounded-lg border border-cyan-400/30 px-2 py-1 text-xs hover:bg-cyan-400/10">Stäng</button>{state.currentModule === "calendar" && <CalendarView />}{state.currentModule === "mail" && <MailView />}{state.currentModule === "finance" && <FinanceView />}{state.currentModule === "reminders" && <RemindersView />}{state.currentModule === "wallet" && <WalletView />}{state.currentModule === "video" && <VideoView source={state.videoSource} />}</div></div>); }
function CalendarView() { const today = new Date(); const year = today.getFullYear(); const month = today.getMonth(); const firstDay = new Date(year, month, 1).getDay(); const daysInMonth = new Date(year, month + 1, 0).getDate(); const cells = Array.from({ length: (firstDay || 7) - 1 }).map((_,i) => ({k:`pad-${i}`, v:null})).concat(Array.from({ length: daysInMonth }, (_, i) => ({k:`day-${i+1}`, v:i+1}))); const weekdays = ['M','T','O','T','F','L','S']; return (<div><div className="mb-3 flex items-center gap-2 text-cyan-200"><IconCalendar className="h-4 w-4" /><h3 className="text-sm uppercase tracking-widest">Kalender – {today.toLocaleString(undefined, { month: "long", year: "numeric" })}</h3></div><div className="grid grid-cols-7 gap-2">{weekdays.map((d, i) => (<div key={`wd-${i}`} className="text-[10px] uppercase tracking-widest text-cyan-300/80 text-center">{d}</div>))}{cells.map((c) => (<div key={c.k} className={`h-16 rounded-lg border ${c.v ? 'border-cyan-400/20 bg-cyan-900/20' : 'border-transparent'} p-2 text-cyan-100 text-sm`}>{c.v || ''}</div>))}</div></div>); }
function MailView() { const mails = [{ id: safeUUID(), from: "Team", subject: "Välkommen till HUD", time: "09:12" }, { id: safeUUID(), from: "Finans", subject: "Veckorapport klar", time: "08:27" }, { id: safeUUID(), from: "Kalender", subject: "Möte 14:00", time: "07:50" }]; return (<div><div className="mb-3 flex items-center gap-2 text-cyan-200"><IconMail className="h-4 w-4" /><h3 className="text-sm uppercase tracking-widest">Mail</h3></div><ul className="divide-y divide-cyan-400/10">{mails.map(m => (<li key={m.id} className="py-2"><div className="text-cyan-100 text-sm">{m.subject}</div><div className="text-cyan-300/70 text-xs">{m.from} • {m.time}</div></li>))}</ul></div>); }
function MiniLine({ data }) { const max = Math.max(...data, 1); const pts = data.map((v,i)=> `${(i/(data.length-1))*100},${100-(v/max)*100}`).join(' '); return (<svg viewBox="0 0 100 100" className="h-20 w-full"><polyline points={pts} fill="none" stroke="currentColor" strokeWidth={2} className="text-cyan-300"/></svg>); }
function FinanceView() { const prices = Array.from({length:32},()=> 80+Math.round(Math.random()*40)); return (<div><div className="mb-3 flex items-center gap-2 text-cyan-200"><IconDollar className="h-4 w-4" /><h3 className="text-sm uppercase tracking-widest">Finans</h3></div><div className="rounded-xl border border-cyan-400/20 p-3 text-cyan-100"><div className="text-xs text-cyan-300/80">Demo-kurva (dummy)</div><MiniLine data={prices} /><div className="mt-2 text-xs text-cyan-300/80">Senast: {prices[prices.length-1]}</div></div></div>); }
function RemindersView() { const [items, setItems] = useState([{ id: safeUUID(), text: "Ring Alex 15:00", done: false }]); const [text, setText] = useState(""); return (<div><div className="mb-3 flex items-center gap-2 text-cyan-200"><IconAlarm className="h-4 w-4" /><h3 className="text-sm uppercase tracking-widest">Påminnelser</h3></div><div className="mb-2 flex gap-2"><input value={text} onChange={(e)=>setText(e.target.value)} onKeyDown={(e)=>{ if(e.key==='Enter' && text.trim()){ setItems([{id:safeUUID(), text, done:false}, ...items]); setText(''); } }} placeholder="Lägg till påminnelse…" className="w-full bg-transparent text-sm text-cyan-100 placeholder:text-cyan-300/40 focus:outline-none"/><button onClick={()=>{ if(text.trim()){ setItems([{id:safeUUID(), text, done:false}, ...items]); setText(''); } }} className="rounded-xl border border-cyan-400/30 px-3 py-1 text-xs hover:bg-cyan-400/10">Lägg till</button></div><ul className="space-y-2">{items.map(it=> (<li key={it.id} className="group flex items-center gap-2 rounded-lg border border-cyan-500/10 bg-cyan-900/10 p-2"><button aria-label="Växla status" onClick={()=> setItems(items.map(x=> x.id===it.id ? {...x, done:!x.done}:x))} className={`grid h-5 w-5 place-items-center rounded-md border ${it.done? 'border-cyan-300 bg-cyan-300/20':'border-cyan-400/30'}`}>{it.done && <IconCheck className="h-3 w-3"/>}</button><span className={`flex-1 text-sm ${it.done? 'line-through text-cyan-300/50':'text-cyan-100'}`}>{it.text}</span><button aria-label="Ta bort" onClick={()=> setItems(items.filter(x=> x.id!==it.id))} className="opacity-0 group-hover:opacity-100 transition-opacity"><IconX className="h-4 w-4 text-cyan-300/60"/></button></li>))}</ul></div>); }

// Video / JarvisCore / Bakgrund (Safe Boot aware)
function VideoView({ source }) { return (<div><div className="mb-3 flex items-center gap-2 text-cyan-200"><IconCamera className="h-4 w-4" /><h3 className="text-sm uppercase tracking-widest">Video</h3></div><VideoFeed source={source} /></div>); }
function VideoFeed({ source }) {
  const videoRef = useRef(null);
  const [err, setErr] = useState(null);
  const [usingWebcam, setUsingWebcam] = useState(false);
  useEffect(() => {
    if (SAFE_BOOT) return;
    if (typeof navigator === 'undefined' || typeof window === 'undefined') { setErr('Video kräver en webbläsare'); return; }
    let currentStream = null;
    async function start() {
      setErr(null);
      if (source?.kind === "remote" && source?.url) {
        if (videoRef.current) {
          videoRef.current.srcObject = null;
          videoRef.current.src = source.url;
          await videoRef.current.play().catch(()=>{});
        }
        setUsingWebcam(false);
        return;
      }
      try {
        const stream = await (navigator.mediaDevices?.getUserMedia ? navigator.mediaDevices.getUserMedia({ video: true, audio: false }) : null);
        if (!stream) throw new Error("Ingen åtkomst till kamera");
        currentStream = stream;
        if (videoRef.current) {
          videoRef.current.srcObject = stream;
          await videoRef.current.play().catch(()=>{});
        }
        setUsingWebcam(true);
      } catch (e) {
        setErr(e?.message ? e.message : String(e));
      }
    }
    start();
    return () => { if (currentStream) currentStream.getTracks().forEach(t=>t.stop()); };
  }, [source?.kind, source?.url]);
  if (SAFE_BOOT) {
    return (<div className="relative overflow-hidden rounded-xl border border-cyan-400/20 bg-cyan-900/20 p-6 text-cyan-300/80 text-sm">Video inaktiverad i Safe Boot-läge</div>);
  }
  return (<div className="relative overflow-hidden rounded-xl border border-cyan-400/20 bg-cyan-900/20"><video ref={videoRef} className="w-full aspect-video" playsInline muted /><div className="absolute bottom-0 right-0 m-2 rounded-md border border-cyan-400/30 bg-cyan-900/70 px-2 py-1 text-[10px] text-cyan-200">{usingWebcam? 'Källa: Webbkamera':'Källa: URL'}</div>{err && <div className="p-3 text-xs text-rose-300">{err}</div>}</div>);
}
function ThreeBGAdvanced() {
  const [particles, setParticles] = useState([]);
  useEffect(() => {
    if (SAFE_BOOT) return;
    const newParticles = Array.from({ length: 30 }, (_, i) => ({ id: i, x: Math.random() * 100, y: Math.random() * 100, z: Math.random() * 100, speed: 0.1 + Math.random() * 0.2, size: 1 + Math.random() * 1.5 }));
    setParticles(newParticles);
    let raf = 0;
    const tick = () => {
      setParticles(prev => prev.map(p => ({ ...p, y: p.y >= 100 ? -5 : p.y + p.speed, x: p.x + Math.sin(Date.now() * 0.001 + p.id) * 0.05 })));
      raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, []);
  if (SAFE_BOOT) {
    return (<div className="absolute inset-0 -z-10"><div className="absolute inset-0 bg-gradient-to-br from-cyan-500/5 via-transparent to-blue-900/10" /></div>);
  }
  return (<div className="absolute inset-0 -z-10"><div className="absolute inset-0 bg-gradient-to-br from-cyan-500/5 via-transparent to-blue-900/10" /><div className="absolute inset-0 overflow-hidden">{particles.map(p => (<div key={p.id} className="absolute rounded-full bg-cyan-400" style={{ left: `${p.x}%`, top: `${p.y}%`, width: `${p.size}px`, height: `${p.size}px`, opacity: 0.1 + (p.z / 100) * 0.2, transform: `scale(${0.5 + (p.z / 100) * 0.5})`, boxShadow: `0 0 ${p.size * 2}px rgba(34, 211, 238, ${0.1 + (p.z / 100) * 0.2})` }} />))}</div></div>);
}
function JarvisCore() {
  const [pulse, setPulse] = useState(0); const [activity, setActivity] = useState(0.3);
  useEffect(() => { if (SAFE_BOOT) return; const interval = setInterval(() => { setPulse(prev => (prev + 1) % 100); setActivity(0.2 + Math.random() * 0.6); }, 100); return () => clearInterval(interval); }, []);
  return (<div className="relative h-64 w-64"><div className="absolute inset-0 rounded-full bg-gradient-to-r from-cyan-500/10 via-cyan-400/5 to-cyan-500/10 animate-pulse" /><div className="absolute inset-0 rounded-full border-2 border-cyan-400/20" /><div className="absolute inset-4 rounded-full border border-cyan-400/15" /><div className="absolute inset-8 rounded-full border border-cyan-400/10" />{!SAFE_BOOT && (<div className="absolute inset-0 rounded-full animate-spin" style={{ background: `conic-gradient(from ${pulse * 3.6}deg, transparent, rgba(34,211,238,${activity * 0.8}), transparent)`, animationDuration: '6s' }} />)}<div className="absolute inset-12">{Array.from({ length: 8 }).map((_, i) => (<div key={i} className="absolute h-1 w-1 rounded-full bg-cyan-300" style={{ top: '50%', left: '50%', transform: `translate(-50%, -50%) rotate(${i * 45 + pulse * 2}deg) translateX(${15 + Math.sin(pulse * 0.1 + i) * 5}px)`, opacity: 0.4 + Math.sin(pulse * 0.05 + i) * 0.4, boxShadow: '0 0 4px rgba(34, 211, 238, 0.6)' }} />))}</div><div className="absolute inset-0 grid place-items-center"><div className="relative h-8 w-8 rounded-full bg-gradient-to-r from-cyan-400 to-blue-400" style={{ boxShadow: `0 0 ${15 + activity * 20}px rgba(34, 211, 238, ${0.4 + activity * 0.3})`, transform: `scale(${0.8 + activity * 0.3})` }}><div className="absolute inset-1 rounded-full bg-gradient-to-br from-white/20 to-transparent" /></div></div></div>);
}

// ────────────────────────────────────────────────────────────────────────────────
// Wallet View (stub utan MetaMask)
function WalletView() {
  return (
    <div>
      <div className="mb-3 flex items-center gap-2 text-cyan-200"><IconDollar className="h-4 w-4" /><h3 className="text-sm uppercase tracking-widest">Plånbok</h3></div>
      <div className="rounded-xl border border-cyan-400/20 p-4 bg-cyan-900/20 text-sm text-cyan-300/80">
        Plånboksintegration är avaktiverad. Vi lägger till anslutning senare.
      </div>
    </div>
  );
}

// ────────────────────────────────────────────────────────────────────────────────
// Diagnostics
function Diagnostics() { const [results, setResults] = useState([]); const { dispatch } = useHUD(); const run = () => { const out = []; try { out.push(clampPercent(-5) === 0 ? "PASS clamp <0" : "FAIL clamp <0"); out.push(clampPercent(150) === 100 ? "PASS clamp >100" : "FAIL clamp >100"); const a = safeUUID(); const b = safeUUID(); out.push(a !== b ? "PASS uuid unique" : "FAIL uuid unique"); if (typeof window !== 'undefined' && window.HUD) { window.HUD.showModule('calendar'); out.push('PASS HUD.showModule'); window.HUD.hideOverlay(); out.push('PASS HUD.hideOverlay'); } if (SAFE_BOOT) { out.push('SAFE_BOOT on'); } } catch (e) { out.push("Diagnostics error: " + (e && e.message ? e.message : String(e))); } setResults(out); }; return (<Pane title="Diagnostics"><button onClick={run} className="rounded-xl border border-cyan-400/30 px-3 py-1 text-xs hover:bg-cyan-400/10">Run tests</button><ul className="mt-3 space-y-1 text-xs text-cyan-300/80">{results.map((r, i) => (<li key={i}>{r}</li>))}</ul></Pane>); }

// ────────────────────────────────────────────────────────────────────────────────
// TodoList
function TodoList({ todos, onToggle, onRemove, onAdd }) {
  const [text, setText] = useState("");
  return (<div><div className="mb-3 flex gap-2"><input value={text} onChange={(e) => setText(e.target.value)} onKeyDown={(e) => { if (e.key === "Enter" && text.trim()) { onAdd(text.trim()); setText(""); } }} placeholder="Lägg till uppgift…" className="w-full bg-transparent text-sm text-cyan-100 placeholder:text-cyan-300/40 focus:outline-none" /><button onClick={() => { if (text.trim()) { onAdd(text.trim()); setText(""); } }} className="rounded-xl border border-cyan-400/30 px-3 py-1 text-xs hover:bg-cyan-400/10">Lägg till</button></div><ul className="space-y-2">{todos.map((t) => (<li key={t.id} className="group flex items-center gap-2 rounded-lg border border-cyan-500/10 bg-cyan-900/10 p-2"><button aria-label="Växla status" onClick={() => onToggle(t.id)} className={`grid h-5 w-5 place-items-center rounded-md border ${t.done ? 'border-cyan-300 bg-cyan-300/20' : 'border-cyan-400/30'}`}>{t.done && <IconCheck className="h-3 w-3" />}</button><span className={`flex-1 text-sm ${t.done ? 'line-through text-cyan-300/50' : 'text-cyan-100'}`}>{t.text}</span><button aria-label="Ta bort" onClick={() => onRemove(t.id)} className="opacity-0 group-hover:opacity-100 transition-opacity"><IconX className="h-4 w-4 text-cyan-300/60" /></button></li>))}</ul></div>);
}

// ────────────────────────────────────────────────────────────────────────────────
// Main HUD
export default function JarvisHUD() { return (<ErrorBoundary><HUDProvider><HUDInner /></HUDProvider></ErrorBoundary>); }
function HUDInner() {
  const { cpu, mem, net } = useSystemMetrics(); const weather = useWeatherStub(); const { todos, add, toggle, remove } = useTodos(); const { transcript, isListening, start, stop } = useVoiceInput(); const [query, setQuery] = useState(""); const { globalError } = useGlobalErrorCatcher(); const { dispatch } = useHUD();
  const [intents, setIntents] = useState([]);
  const [journal, setJournal] = useState([]);
  const wsRef = useRef(null);
  const dispatchRef = useRef(dispatch);
  useEffect(() => { dispatchRef.current = dispatch; }, [dispatch]);

  // WS-klient till backend
  useEffect(() => {
    const url = `ws://127.0.0.1:8000/ws/jarvis`;
    try {
      const ws = new WebSocket(url);
      wsRef.current = ws;
      ws.onopen = () => {
        setJournal((j) => [{ id: safeUUID(), ts: new Date().toISOString(), text: "WS connected" }, ...j].slice(0, 50));
      };
      ws.onmessage = (ev) => {
        try {
          const msg = JSON.parse(ev.data);
          if (msg.type === "hud_command" && msg.command) {
            setIntents((q) => [{ id: safeUUID(), ts: new Date().toISOString(), command: msg.command }, ...q].slice(0, 50));
            // Förväntar sig format { type: 'SHOW_MODULE', module: 'calendar' } etc.
            dispatchRef.current && dispatchRef.current(msg.command);
          } else if (msg.type === "hello" || msg.type === "heartbeat" || msg.type === "echo" || msg.type === "ack") {
            setJournal((j) => [{ id: safeUUID(), ts: new Date().toISOString(), text: JSON.stringify(msg) }, ...j].slice(0, 100));
          }
        } catch (_) {}
      };
      ws.onclose = () => {
        setJournal((j) => [{ id: safeUUID(), ts: new Date().toISOString(), text: "WS disconnected" }, ...j].slice(0, 50));
      };
    } catch (_) {}
    return () => { try { wsRef.current && wsRef.current.close(); } catch (_) {} };
  }, []);
  useEffect(() => { if (SAFE_BOOT) return; const id = setInterval(() => { if (typeof window !== 'undefined' && Math.random() < 0.07) dispatch({ type: "OPEN_VIDEO", source: { kind: "webcam" } }); }, 4000); return () => clearInterval(id); }, [dispatch]);
  const timeInit = useMemo(() => new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }), []); const [now, setNow] = useState(timeInit); useEffect(() => { const id = setInterval(() => setNow(new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })), 1000); return () => clearInterval(id); }, []);
  return (
    <div className="relative min-h-screen w-full overflow-hidden bg-[#030b10] text-cyan-100">
      <ThreeBGAdvanced />
      <div className="pointer-events-none absolute inset-0 [background:radial-gradient(ellipse_at_top,rgba(13,148,136,.15),transparent_60%),radial-gradient(ellipse_at_bottom,rgba(3,105,161,.12),transparent_60%)]" />
      <div className="pointer-events-none absolute inset-0 bg-[linear-gradient(#0e7490_1px,transparent_1px),linear-gradient(90deg,#0e7490_1px,transparent_1px)] bg-[size:40px_40px] opacity-10" />

      <div className="mx-auto max-w-7xl px-6 pt-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3 opacity-80"><IconWifi className="h-4 w-4" /><IconBattery className="h-4 w-4" /><IconBell className="h-4 w-4" /></div>
          <div className="flex items-center gap-2 text-cyan-300/80"><IconClock className="h-4 w-4" /><span className="tracking-widest text-xs uppercase" suppressHydrationWarning>{now}</span></div>
        </div>
        {globalError && (<div className="mt-3 rounded-xl border border-cyan-500/20 bg-cyan-900/20 p-3 text-xs text-cyan-300/90"><strong>Observerat globalt fel:</strong> {globalError}</div>)}
      </div>

      <div className="sticky top-4 z-40 mx-auto mt-4 flex w-full max-w-3xl items-center justify-center gap-2">
        <HUDButton icon={<IconCalendar className="h-4 w-4" />} label="Kalender" onClick={()=> dispatch({ type: "SHOW_MODULE", module: "calendar" })} />
        <HUDButton icon={<IconMail className="h-4 w-4" />} label="Mail" onClick={()=> dispatch({ type: "SHOW_MODULE", module: "mail" })} />
        <HUDButton icon={<IconDollar className="h-4 w-4" />} label="Finans" onClick={()=> dispatch({ type: "SHOW_MODULE", module: "finance" })} />
        <HUDButton icon={<IconAlarm className="h-4 w-4" />} label="Påminnelser" onClick={()=> dispatch({ type: "SHOW_MODULE", module: "reminders" })} />
        <HUDButton icon={<IconDollar className="h-4 w-4" />} label="Plånbok" onClick={()=> dispatch({ type: "SHOW_MODULE", module: "wallet" })} />
        <HUDButton icon={<IconCamera className="h-4 w-4" />} label="Video" onClick={()=> dispatch({ type: "OPEN_VIDEO", source: { kind: "webcam" } })} />
      </div>

      <main className="mx-auto grid max-w-7xl grid-cols-1 gap-6 px-6 pb-24 pt-4 md:grid-cols-12">
        <div className="md:col-span-3 space-y-6">
          <Pane title="System" actions={<IconSettings className="h-4 w-4" />}>
            <div className="grid grid-cols-3 gap-3">
              <Metric label="CPU" value={cpu} icon={<IconCpu className="h-3 w-3" />} />
              <Metric label="MEM" value={mem} icon={<IconDrive className="h-3 w-3" />} />
              <Metric label="NET" value={net} icon={<IconActivity className="h-3 w-3" />} />
            </div>
            <div className="mt-4 grid grid-cols-3 place-items-center">
              <RingGauge size={77} value={cpu} icon={<IconCpu className="h-3 w-3" />} showValue={false} />
              <RingGauge size={77} value={mem} icon={<IconDrive className="h-3 w-3" />} showValue={false} />
              <RingGauge size={77} value={net} icon={<IconGauge className="h-3 w-3" />} showValue={false} />
            </div>
          </Pane>

          <Pane title="Voice" actions={<IconMic className={`h-4 w-4 ${isListening ? "text-cyan-300" : "text-cyan-300/70"}`} />}>
            <div className="rounded-xl border border-cyan-500/20 p-3 bg-cyan-900/20">
              <div className="text-xs text-cyan-300/70">{transcript || (SAFE_BOOT ? "Safe Boot: röst av" : "Say: lägg till todo...")}</div>
              <div className="mt-3 flex gap-2">
                <button aria-label="Starta röst" onClick={start} className="rounded-xl border border-cyan-400/30 px-3 py-1 text-xs hover:bg-cyan-400/10">Start</button>
                {!SAFE_BOOT && <button aria-label="Stoppa röst" onClick={stop} className="rounded-xl border border-cyan-400/30 px-3 py-1 text-xs hover:bg-cyan-400/10">Stop</button>}
                <button aria-label="Lägg till i todo" onClick={()=>{ if(transcript.trim()) { add(transcript.trim()); } }} className="ml-auto rounded-xl border border-cyan-400/30 px-3 py-1 text-xs hover:bg-cyan-400/10">Add to To‑do</button>
              </div>
            </div>
          </Pane>

          <Diagnostics />
        </div>

        <div className="md:col-span-6 space-y-6">
          <Pane title="Jarvis Core">
            <div className="flex justify-center py-10"><JarvisCore /></div>
            <div className="mt-6 flex items-center gap-2">
              <IconSearch className="h-4 w-4 text-cyan-300/70" />
              <input value={query} onChange={(e) => setQuery(e.target.value)} onKeyDown={async (e) => {
                if (e.key === "Enter" && query.trim()) {
                  const body = { type: "USER_QUERY", payload: { query: query.trim() } };
                  try {
                    await fetch("http://127.0.0.1:8000/api/jarvis/command", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
                    setIntents((q) => [{ id: safeUUID(), ts: new Date().toISOString(), command: body }, ...q].slice(0, 50));
                  } catch (_) {}
                }
              }} placeholder="Fråga Jarvis…" className="w-full bg-transparent text-cyan-100 placeholder:text-cyan-300/40 focus:outline-none" />
              <button aria-label="Sök" onClick={async ()=> {
                if (!query.trim()) return;
                const body = { type: "USER_QUERY", payload: { query: query.trim() } };
                try {
                  await fetch("http://127.0.0.1:8000/api/jarvis/command", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
                  setIntents((q) => [{ id: safeUUID(), ts: new Date().toISOString(), command: body }, ...q].slice(0, 50));
                } catch (_) {}
              }} className="rounded-xl border border-cyan-400/30 px-3 py-1 text-xs hover:bg-cyan-400/10">Go</button>
              <button aria-label="Auto Decide" onClick={async ()=>{
                try{
                  const res = await fetch('http://127.0.0.1:8000/api/decision/pick_tool',{ method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({ candidates: ['SHOW_MODULE','OPEN_VIDEO','HIDE_OVERLAY'] })});
                  const j = await res.json();
                  const tool = (j && j.tool) || 'SHOW_MODULE';
                  let cmd;
                  if (tool === 'SHOW_MODULE') cmd = { type:'SHOW_MODULE', module:'calendar' };
                  else if (tool === 'OPEN_VIDEO') cmd = { type:'OPEN_VIDEO', source:{ kind:'webcam' } };
                  else cmd = { type:'HIDE_OVERLAY' };
                  setIntents((q)=>[{ id:safeUUID(), ts:new Date().toISOString(), command: cmd }, ...q].slice(0,50));
                  dispatchRef.current && dispatchRef.current(cmd);
                }catch(_){ }
              }} className="rounded-xl border border-cyan-400/30 px-3 py-1 text-xs hover:bg-cyan-400/10">Auto</button>
            </div>
          </Pane>

          <Pane title="Intent Queue">
            <ul className="space-y-2 text-xs text-cyan-300/80 max-h-56 overflow-auto">
              {intents.map((it) => (
                <li key={it.id} className="rounded border border-cyan-400/10 p-2">
                  <div className="text-cyan-400/80">{new Date(it.ts).toLocaleTimeString()}</div>
                  <pre className="whitespace-pre-wrap break-words text-cyan-200/90">{JSON.stringify(it.command)}</pre>
                  <div className="mt-2 flex gap-2">
                    <button aria-label="Feedback up" onClick={async ()=>{
                      try { await fetch("http://127.0.0.1:8000/api/feedback", { method:"POST", headers:{"Content-Type":"application/json"}, body: JSON.stringify({ kind: "tool", tool: it.command?.type || "hud_control", up: true })}); } catch(_){ }
                    }} className="rounded border border-cyan-400/30 px-2 py-0.5 text-[10px] hover:bg-cyan-400/10">👍</button>
                    <button aria-label="Feedback down" onClick={async ()=>{
                      try { await fetch("http://127.0.0.1:8000/api/feedback", { method:"POST", headers:{"Content-Type":"application/json"}, body: JSON.stringify({ kind: "tool", tool: it.command?.type || "hud_control", up: false })}); } catch(_){ }
                    }} className="rounded border border-cyan-400/30 px-2 py-0.5 text-[10px] hover:bg-cyan-400/10">👎</button>
                  </div>
          </li>
              ))}
            </ul>
          </Pane>

          <Pane title="Journal">
            <ul className="space-y-2 text-xs text-cyan-300/80 max-h-56 overflow-auto">
              {journal.map((it) => (
                <li key={it.id} className="rounded border border-cyan-400/10 p-2">
                  <div className="text-cyan-400/80">{new Date(it.ts).toLocaleTimeString()}</div>
                  <div className="text-cyan-200/90 break-words">{it.text}</div>
                  {it.memId && (
                    <div className="mt-2 flex gap-2">
                      <button aria-label="Memory up" onClick={async ()=>{
                        try { await fetch("http://127.0.0.1:8000/api/feedback", { method:"POST", headers:{"Content-Type":"application/json"}, body: JSON.stringify({ kind: "memory", id: it.memId, up: true })}); } catch(_){ }
                      }} className="rounded border border-cyan-400/30 px-2 py-0.5 text-[10px] hover:bg-cyan-400/10">👍</button>
                      <button aria-label="Memory down" onClick={async ()=>{
                        try { await fetch("http://127.0.0.1:8000/api/feedback", { method:"POST", headers:{"Content-Type":"application/json"}, body: JSON.stringify({ kind: "memory", id: it.memId, up: false })}); } catch(_){ }
                      }} className="rounded border border-cyan-400/30 px-2 py-0.5 text-[10px] hover:bg-cyan-400/10">👎</button>
                    </div>
                  )}
          </li>
              ))}
            </ul>
          </Pane>

          <Pane title="Sensors">
            <div className="grid gap-3 md:grid-cols-2">
              <div className="rounded-xl border border-cyan-400/20 p-3 overflow-hidden">
                <div className="text-xs text-cyan-300/80 mb-2">Send telemetry</div>
                <form onSubmit={async (e)=>{ e.preventDefault(); const fd=new FormData(e.currentTarget); const sensor=fd.get('sensor'); const value=parseFloat(fd.get('value')); if(!sensor||Number.isNaN(value)) return; try{ await fetch('http://127.0.0.1:8000/api/sensor/telemetry',{ method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({ sensor, value })}); setJournal((j)=>[{ id:safeUUID(), ts:new Date().toISOString(), text:`telemetry sent: ${sensor}=${value}`}, ...j].slice(0,100)); }catch(_){ } }} className="flex flex-wrap gap-2 items-center">
                  <input name="sensor" placeholder="sensor name" className="flex-1 min-w-0 bg-transparent text-sm text-cyan-100 placeholder:text-cyan-300/40 focus:outline-none border border-cyan-400/20 rounded px-2 py-1" />
                  <input name="value" type="number" step="any" placeholder="value" className="w-28 bg-transparent text-sm text-cyan-100 placeholder:text-cyan-300/40 focus:outline-none border border-cyan-400/20 rounded px-2 py-1" />
                  <button className="shrink-0 rounded-xl border border-cyan-400/30 px-3 py-1 text-xs hover:bg-cyan-400/10">Send</button>
                </form>
              </div>
              <div className="rounded-xl border border-cyan-400/20 p-3 overflow-hidden">
                <div className="text-xs text-cyan-300/80 mb-2">CV ingest (meta JSON)</div>
                <form onSubmit={async (e)=>{ e.preventDefault(); const fd=new FormData(e.currentTarget); const source=fd.get('source'); const meta=fd.get('meta'); try{ const parsed=meta?JSON.parse(meta):undefined; await fetch('http://127.0.0.1:8000/api/cv/ingest',{ method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({ source, meta: parsed })}); setJournal((j)=>[{ id:safeUUID(), ts:new Date().toISOString(), text:`cv.ingest: ${source}`}, ...j].slice(0,100)); }catch(err){ setJournal((j)=>[{ id:safeUUID(), ts:new Date().toISOString(), text:`cv.ingest error`}, ...j].slice(0,100)); } }} className="flex flex-wrap gap-2 items-center">
                  <input name="source" placeholder="source id" className="flex-1 min-w-0 bg-transparent text-sm text-cyan-100 placeholder:text-cyan-300/40 focus:outline-none border border-cyan-400/20 rounded px-2 py-1" />
                  <input name="meta" placeholder='{"objects":[{"name":"person","conf":0.9}]}' className="flex-1 min-w-0 bg-transparent text-sm text-cyan-100 placeholder:text-cyan-300/40 focus:outline-none border border-cyan-400/20 rounded px-2 py-1" />
                  <button className="shrink-0 rounded-xl border border-cyan-400/30 px-3 py-1 text-xs hover:bg-cyan-400/10">Send</button>
                </form>
              </div>
            </div>
          </Pane>

          <Pane title="Media">
            <div className="flex items-center gap-4">
              <button aria-label="Bakåt" className="rounded-full border border-cyan-400/30 p-2 hover:bg-cyan-400/10"><IconSkipBack className="h-4 w-4" /></button>
              <button aria-label="Spela" className="rounded-full border border-cyan-400/30 p-3 hover:bg-cyan-400/10"><IconPlay className="h-5 w-5" /></button>
              <button aria-label="Framåt" className="rounded-full border border-cyan-400/30 p-2 hover:bg-cyan-400/10"><IconSkipForward className="h-4 w-4" /></button>
              <div className="ml-auto text-xs text-cyan-300/70">0:00 / 3:45</div>
            </div>
          </Pane>
        </div>

        <div className="md:col-span-3 space-y-6">
          <Pane title="Weather" actions={<IconCloudSun className="h-4 w-4" />}>
            <div className="flex items-center gap-4">
              <IconThermometer className="h-10 w-10 text-cyan-300" />
              <div>
                <div className="text-3xl font-semibold">{weather.temp}°C</div>
                <div className="text-cyan-300/80 text-sm">{weather.desc}</div>
              </div>
            </div>
          </Pane>

          <Pane title="To‑do">
            <TodoList todos={todos} onToggle={toggle} onRemove={remove} onAdd={add} />
          </Pane>
        </div>
      </main>

      <Overlay />

      <footer className="pointer-events-none absolute inset-x-0 bottom-0 mx-auto max-w-7xl px-6 pb-8">
        <div className="grid grid-cols-5 gap-4 opacity-80">
          {["SYS", "NET", "AUX", "NAV", "CTRL"].map((t, i) => (
            <div key={i} className="relative h-14 overflow-hidden rounded-xl border border-cyan-500/20 bg-cyan-900/10">
              <div className="absolute inset-0 bg-[radial-gradient(circle_at_20%_20%,rgba(34,211,238,.15),transparent_50%)]" />
              <div className="absolute inset-0 grid place-items-center text-xs tracking-[.35em] text-cyan-200/70">{t}</div>
              <div className="absolute bottom-0 h-[2px] w-full bg-gradient-to-r from-cyan-500/0 via-cyan-500/60 to-cyan-500/0" />
            </div>
          ))}
        </div>
      </footer>
    </div>
  );
}

function HUDButton({ icon, label, onClick }) { return (<button aria-label={label} onClick={onClick} className="rounded-xl border border-cyan-400/30 bg-cyan-900/30 px-3 py-2 text-xs backdrop-blur hover:bg-cyan-400/10"><div className="flex items-center gap-2 text-cyan-200">{icon}<span className="tracking-widest uppercase">{label}</span></div></button>); }

// Named exports kan störa i vissa sandboxar – kommentera bort vid behov
export { clampPercent, safeUUID };
