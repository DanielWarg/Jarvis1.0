import express from "express";
import cors from "cors";
import bodyParser from "body-parser";
import pino from "pino";
import fs from "node:fs";
import path from "node:path";
import { extractTimeSlots, extractVolumeSlots, extractLanguage, normalizeSv } from "../../jarvis-tools/src/router/slots.js";
import { ruleFirstClassify, ruleFirstRoute, mapIntentToTool } from "../../jarvis-tools/src/router/router.js";

const log = pino({ level: "info" });
const app = express();
app.use(cors());
app.use(bodyParser.json());

// Prefs/alias + korttidsminne (filbaserad)
const statePath = path.join(process.cwd(), 'data', 'state.json');
function loadState(){ try{ return JSON.parse(fs.readFileSync(statePath,'utf8')); }catch{ return { shortTerm: [], prefs: { deviceAliases: {}, favoriteArtists: [], preferredDevice: undefined } }; } }
function saveState(s:any){ try{ fs.mkdirSync(path.dirname(statePath), { recursive:true }); fs.writeFileSync(statePath, JSON.stringify(s,null,2)); }catch{} }
let state = loadState();
function pushShort(text:string, plan?:any){ state.shortTerm.unshift({ ts:new Date().toISOString(), text, plan }); state.shortTerm = state.shortTerm.slice(0,20); saveState(state); }
function resolveAlias(name:string){ const n = String(name||'').toLowerCase(); return state?.prefs?.deviceAliases?.[n] || n; }

app.get('/agent/prefs',(req,res)=>{ res.json({ ok:true, prefs: state.prefs||{} }); });
app.post('/agent/prefs',(req,res)=>{ const b=req.body||{}; state.prefs = { ...(state.prefs||{}), ...b, deviceAliases: state.prefs?.deviceAliases||{} }; saveState(state); res.json({ ok:true }); });
app.post('/agent/alias',(req,res)=>{ const a=String(req.body?.alias||'').toLowerCase().trim(); const c=String(req.body?.canonical||'').toLowerCase().trim(); if(!a||!c) return res.status(400).json({ ok:false, error:'alias_and_canonical_required' }); state.prefs = state.prefs||{}; state.prefs.deviceAliases = state.prefs.deviceAliases||{}; state.prefs.deviceAliases[a]=c; saveState(state); res.json({ ok:true }); });

app.post("/nlu/extract", (req, res) => {
  const text: string = String(req.body?.text ?? "");
  const slots = { ...extractTimeSlots(text), ...extractVolumeSlots(text) } as any;
  const lang = extractLanguage(text);
  if (lang) (slots as any).language = lang;
  const confidence = typeof slots.seconds === "number" || slots.to || slots.endpoint || typeof (slots as any).level === "number" || typeof (slots as any).delta === "number" || lang ? 0.9 : 0.5;
  res.json({ ok: true, slots, confidence });
});

app.post("/nlu/classify", (req, res) => {
  const text: string = String(req.body?.text ?? "");
  const m = ruleFirstClassify(text);
  if (!m) return res.json({ ok: true, intent: null, score: 0.0 });
  res.json({ ok: true, intent: m.intent, score: m.score, phrase: m.phrase });
});

app.post("/agent/route", async (req, res) => {
  const text: string = String(req.body?.text ?? "");
  // 1) Försök regel-först router
  let r = ruleFirstRoute(text) as any;
  if (r && r.name==='TRANSFER' && r.args && typeof r.args.device==='string') { r.args = { device: resolveAlias(r.args.device), alias: r.args.device }; }
  if (r) { pushShort(text, r); return res.json({ ok: true, plan: { tool: r.name, params: r.args }, confidence: 0.9, needs_confirmation: true }); }
  // 2) Minimal fallback för volym/mute om klassificering missar
  const slots = extractVolumeSlots(text) as any;
  const t = normalizeSv(text);
  if (typeof slots.level === "number") { const plan={ tool: "SET_VOLUME", params: { level: slots.level } }; pushShort(text, plan); return res.json({ ok: true, plan, confidence: 0.85, needs_confirmation: false }); }
  if (typeof slots.delta === "number") {
    // kortformer "höj 20%" / "sänk 15%"
    if (/\bh[oö]j\b/.test(t) && slots.delta > 0) { const plan={ tool: "SET_VOLUME", params: { delta: slots.delta } }; pushShort(text, plan); return res.json({ ok: true, plan, confidence: 0.8, needs_confirmation: false }); }
    if (/\bs[äa]nk\b/.test(t) && slots.delta < 0) { const plan={ tool: "SET_VOLUME", params: { delta: slots.delta } }; pushShort(text, plan); return res.json({ ok: true, plan, confidence: 0.8, needs_confirmation: false }); }
  }
  if (/\bmax(imum|imalt)?\b|\bhogsta\b|\bfull\s*volym\b|\bmax\s*volym\b|sa\s*hogt(\s*som\s*mojligt)?|sa\s*hogt\s*det\s*gar|pa\s*(hogsta|max)\b/.test(t)) { const plan={ tool: "SET_VOLUME", params: { level: 100 } }; pushShort(text, plan); return res.json({ ok: true, plan, confidence: 0.85, needs_confirmation: false }); }
  if (/\bmin(imum|imalt)?\b|\btyst\b/.test(t)) { const plan={ tool: "SET_VOLUME", params: { level: 0 } }; pushShort(text, plan); return res.json({ ok: true, plan, confidence: 0.85, needs_confirmation: false }); }
  if (/\b(mute|stang av ljudet|tysta|ljud av)\b/.test(t)) { const plan={ tool: "MUTE", params: {} }; pushShort(text, plan); return res.json({ ok: true, plan, confidence: 0.8, needs_confirmation: false }); }
  if (/\b(avmuta|slag? pa ljud|ljud pa|avdampa)\b/.test(t)) { const plan={ tool: "UNMUTE", params: {} }; pushShort(text, plan); return res.json({ ok: true, plan, confidence: 0.8, needs_confirmation: false }); }
  // 3) Annars LLM
  return res.json({ ok: true, plan: null, fallback: "llm" });
});

const PORT = Number(process.env.PORT ?? 7071);
app.listen(PORT, () => log.info({ PORT }, "NLU/Agent server up"));


