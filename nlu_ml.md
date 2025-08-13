Instruktion till Cursor – Skapa/uppdatera följande filer med exakt innehåll:

BEGIN FILE: /jarvis-tools/package.json
{
"name": "jarvis-tools",
"version": "1.1.0",
"type": "module",
"private": true,
"scripts": {
"build": "tsc",
"start": "node dist/index.js",
"dev": "tsx src/index.ts",
"test\:router": "tsx src/index.ts --test",
"test\:none": "tsx src/index.ts --test-none"
},
"dependencies": {
"ajv": "^8.17.1",
"ajv-formats": "^3.0.1",
"lodash": "^4.17.21",
"minimist": "^1.2.8",
"node-fetch": "^3.3.2",
"pino": "^9.4.0",
"string-normalizer": "^2.0.1",
"zod": "^3.23.8",
"leven": "^3.1.0"
},
"devDependencies": {
"tsx": "^4.16.3",
"typescript": "^5.5.4"
}
}
END FILE

BEGIN FILE: /jarvis-tools/tsconfig.json
{
"compilerOptions": {
"target": "ES2022",
"module": "ES2022",
"moduleResolution": "Bundler",
"outDir": "dist",
"rootDir": "src",
"strict": true,
"esModuleInterop": true,
"resolveJsonModule": true,
"skipLibCheck": true
},
"include": \["src"]
}
END FILE

BEGIN FILE: /jarvis-tools/src/lexicon/sv\_media\_commands.json
{
"language": "sv",
"version": "1.1.0",
"intents": {
"PLAY": \["spela", "spela upp", "starta", "starta uppspelning", "börja", "kör", "sätt igång", "återuppta", "fortsätt", "fortsätt spela", "resume", "spela vidare", "återstarta", "fortsätt där jag var", "fortsätt från senast"],
"PAUSE": \["pausa", "paus", "stoppa tillfälligt", "stanna till", "frys", "håll upp", "lägg på paus"],
"STOP": \["stoppa", "stopp", "avsluta", "avbryt", "sluta spela", "avsluta uppspelning"],
"SEEK\_FWD": \["spola fram", "snabbspola fram", "hoppa fram", "gå framåt", "framåt", "framspolning", "skrolla fram", "skjut fram", "vrid fram", "snabbfram", "skippa fram", "lite fram", "en bit fram"],
"SEEK\_BACK": \["spola tillbaka", "snabbspola bak", "hoppa tillbaka", "gå bakåt", "bakåt", "backa", "backspola", "skrolla bak", "vrid bak", "lite tillbaka", "en bit tillbaka"],
"SEEK\_TO": \["hoppa till", "gå till", "spela från", "börja vid", "sök till tid", "scrubba till", "hoppa till början", "hoppa till slutet", "gå till markering", "hoppa till bokmärke", "hoppa till kapitel"],
"NEXT": \["nästa", "nästa spår", "nästa kapitel", "nästa video", "hoppa över", "skippa", "fram ett spår", "hoppa till nästa", "nästa i kön", "nästa video i kön"],
"PREV": \["föregående", "föregående spår", "föregående kapitel", "bak ett spår", "gå tillbaka ett steg"],
"REPEAT\_ON": \["repetera", "upprepa", "loopa", "spela i loop", "repetera låt", "repetera spår", "repetera allt", "repetera en", "slå på upprepning"],
"REPEAT\_OFF": \["repetera av", "stäng av upprepning", "slå av upprepning"],
"SHUFFLE\_ON": \["slumpa", "shuffle", "blanda", "blanda låtar", "slumpmässig ordning", "slå på shuffle"],
"SHUFFLE\_OFF": \["blanda av", "shuffle av", "stäng av shuffle"],
"VOL\_UP": \["höj volymen", "öka volym", "starkare", "högre", "skruva upp", "volym upp", "maxa volym"],
"VOL\_DOWN": \["sänk volymen", "minska volym", "lägre", "tystare", "skruva ner", "volym ner", "dämpa"],
"SET\_VOL": \["volym", "sätt volymen till", "ställ volymen på", "volym nivå", "volym procent", "normal volym", "standardvolym"],
"MUTE": \["mute", "stäng av ljudet", "tysta", "ljud av"],
"UNMUTE": \["avmuta", "slå på ljud", "ljud på", "avdämpa"],
"SPEED\_UP": \["öka hastigheten", "snabbare", "spela snabbare", "tempo upp", "1.25x", "1.5x", "2x"],
"SPEED\_DOWN": \["sakta ner", "långsammare", "halv hastighet", "tempo ner", "0.5x", "0,5x"],
"SPEED\_NORMAL": \["normal hastighet", "återställ hastighet"],
"QUALITY\_SET": \["ändra kvalitet", "byt upplösning", "sänk kvalitet", "höj kvalitet", "auto-kvalitet", "bästa kvalitet", "4k", "1080p", "720p", "hdr på", "hdr av", "dolby vision på", "dolby vision av"],
"FULLSCREEN\_ON": \["helskärm", "fullskärm", "maximera", "gå till helskärm", "helscreen", "helt skärm"],
"FULLSCREEN\_OFF": \["lämna helskärm", "avsluta helskärm", "minimera", "fönsterläge"],
"SUBS\_ON": \["slå på undertexter", "undertexter på", "textning på", "visa text", "cc på"],
"SUBS\_OFF": \["stäng av undertexter", "undertexter av", "textning av", "dölj text", "cc av"],
"SUBS\_LANG": \["svenska undertexter", "engelska undertexter", "byt undertextspråk", "nästa undertext"],
"AUDIO\_TRACK": \["byt ljudspår", "nästa ljudspår", "föregående ljudspår", "svenska ljudspår", "engelskt ljudspår", "originalspråk", "dubbning"],
"CAST\_START": \["casta", "spela på tv", "skicka till chromecast", "airplay", "spela på högtalare", "koppla till enhet", "casta till vardagsrummet", "casta i köket", "spela på sovrummet"],
"CAST\_STOP": \["koppla från", "avbryt casting", "sluta casta"],
"QUEUE\_SHOW": \["visa kö", "spelkö", "köläge"],
"QUEUE\_ADD": \["lägg till i kö", "lägg den här i kö", "lägg till låten i kön"],
"QUEUE\_REMOVE": \["ta bort från kö", "ta bort första i kön", "ta bort nuvarande från kö"],
"QUEUE\_CLEAR": \["rensa kö", "töm kön"],
"SKIP\_INTRO": \["hoppa över intro", "skippa intro"],
"SKIP\_RECAP": \["hoppa över recap", "skippa recap"],
"SKIP\_ADS": \["hoppa över reklam", "skippa reklam"]
},
"fuzzy": {
"typo\_variants": \["full skärm", "helt skärm", "shufle", "shuffla", "muute", "volm", "undirtexter", "undertext", "texter"],
"compound\_hints": \["undertext", "undertexter", "textning", "fullskärm", "helscreen"]
}
}
END FILE

BEGIN FILE: /jarvis-tools/src/lexicon/devices.json
{
"version": "1.0.0",
"aliases": {
"vardagsrummet": \["tv vardagsrum", "chromecast vardagsrum", "living room tv"],
"köket": \["kökshögtalare", "sonos kök", "kitchen speaker"],
"sovrummet": \["sovrumstv", "bedroom tv"],
"kontoret": \["kontorsskärm", "office display"]
}
}
END FILE

BEGIN FILE: /jarvis-tools/src/schema/tools.ts
import { z } from "zod";
export const base = z.object({ requestId: z.string().optional() });
export const SeekArgs = base.extend({
direction: z.enum(\["FWD","BACK"]).optional(),
seconds: z.number().int().nonnegative().optional(),
position: z.number().nonnegative().max(1).optional(),
to: z.string().regex(/^(\d{1,2}:)?\d{1,2}:\d{2}\$/).optional(),
chapter: z.number().int().positive().optional(),
endpoint: z.enum(\["START","END","INTRO","RECAP","ADS"]).optional()
});
export const VolumeArgs = base.extend({
level: z.number().int().min(0).max(100).optional(),
delta: z.number().int().min(-100).max(100).optional(),
mute: z.boolean().optional()
});
export const LangArgs = base.extend({ language: z.string().optional() });
export type ToolName =
\| "PLAY" | "PAUSE" | "STOP"
\| "SEEK" | "NEXT" | "PREV"
\| "SET\_VOLUME" | "MUTE" | "UNMUTE"
\| "SET\_SPEED" | "SET\_QUALITY"
\| "FULLSCREEN\_ON" | "FULLSCREEN\_OFF"
\| "SUBS\_ON" | "SUBS\_OFF" | "SUBS\_LANG"
\| "AUDIO\_TRACK" | "CAST\_START" | "CAST\_STOP"
\| "QUEUE\_SHOW" | "QUEUE\_ADD" | "QUEUE\_REMOVE" | "QUEUE\_CLEAR";
export const ToolSchemas: Record\<ToolName, z.ZodTypeAny> = {
PLAY: base, PAUSE: base, STOP: base,
SEEK: SeekArgs, NEXT: base, PREV: base,
SET\_VOLUME: VolumeArgs, MUTE: base, UNMUTE: base,
SET\_SPEED: z.object({ rate: z.number().min(0.25).max(3) }).merge(base),
SET\_QUALITY: z.object({ quality: z.string() }).merge(base),
FULLSCREEN\_ON: base, FULLSCREEN\_OFF: base,
SUBS\_ON: base, SUBS\_OFF: base, SUBS\_LANG: LangArgs,
AUDIO\_TRACK: LangArgs,
CAST\_START: z.object({ device: z.string().optional() }).merge(base),
CAST\_STOP: base,
QUEUE\_SHOW: base,
QUEUE\_ADD: z.object({ query: z.string() }).merge(base),
QUEUE\_REMOVE: z.object({ index: z.number().int().min(0).optional(), query: z.string().optional() }).merge(base),
QUEUE\_CLEAR: base
};
export function validateTool(name: ToolName, args: any) {
const schema = ToolSchemas\[name];
if (!schema) throw new Error(`Unknown tool: ${name}`);
return schema.parse(args ?? {});
}
END FILE

BEGIN FILE: /jarvis-tools/src/router/slots.ts
import \_ from "lodash";
const NUMBER\_WORDS: Record\<string, number> = {
"noll":0,"en":1,"ett":1,"ettan":1,"två":2,"tva":2,"tre":3,"fyra":4,"fem":5,"sex":6,"sju":7,"åtta":8,"atta":8,"nio":9,"tio":10,
"elva":11,"tolv":12,"tretton":13,"fjorton":14,"femton":15,"sexton":16,"sjutton":17,"arton":18,"nitton":19,"tjugo":20,
"trettio":30,"fyrtio":40,"femtio":50,"sextio":60,"sjuttio":70,"åttio":80,"nittio":90,"hundra":100
};
function wordsToNumber(tokens: string\[]): number | undefined {
let total = 0; let matched = false;
for (const t of tokens) {
if (t in NUMBER\_WORDS) { total += NUMBER\_WORDS\[t]; matched = true; }
else if (/^\d+\$/.test(t)) { total += parseInt(t,10); matched = true; }
}
return matched ? total : undefined;
}
export function normalizeSv(s: string) {
const lower = s.toLowerCase().normalize("NFD").replace(/\p{Diacritic}/gu, "");
return lower.replace(/\s+/g, " ").trim();
}
function vagueToSeconds(text: string): number | undefined {
const t = normalizeSv(text);
if (/\bett par\b/.test(t)) return 120;
if (/\benh\[aä]lv\b/.test(t)) return 30;
if (/\ben stund\b/.test(t)) return 45;
if (/\bstrax under minuten\b/.test(t)) return 50;
if (/\bstrax \[oå]ver minuten\b/.test(t)) return 70;
return undefined;
}
export function extractTimeSlots(text: string) {
const t = normalizeSv(text);
const slots: any = {};
const secRel = /(\d{1,3})\s\*(sek|sekunder|s)\b/;
const minRel = /(\d{1,3})\s\*(min|minuter|m)\b/;
const mSec = t.match(secRel);
if (mSec) slots.seconds = parseInt(mSec\[1], 10);
const mMin = t.match(minRel);
if (mMin) slots.seconds = (slots.seconds ?? 0) + parseInt(mMin\[1], 10) \* 60;
if (!slots.seconds) {
const tokens = t.split(/\s+/);
const num = wordsToNumber(tokens);
if (num && /\b(min|minuter|minute?n)\b/.test(t)) slots.seconds = num \* 60;
else if (num && /\b(sek|sekunder|sekund)\b/.test(t)) slots.seconds = num;
}
if (!slots.seconds) {
const vague = vagueToSeconds(t);
if (vague) slots.seconds = vague;
}
const halfMin = /\benh? och en halv minut\b/;
if (halfMin.test(t)) slots.seconds = 90;
const toHMS = /\b(?\:till|vid|pa)\s\*((?:\d{1,2}:)?\d{1,2}:\d{2})\b/;
const mTo = t.match(toHMS);
if (mTo) slots.to = mTo\[1];
if (/(ga|hoppa)\still\sborjan|\bborja\som\b/.test(t)) slots.endpoint = "START";
if (/(ga|hoppa)\still\s*slutet|eftertexter\b/.test(t)) slots.endpoint = "END";
const chap = t.match(/kapitel\s*(\d{1,3})/);
if (chap) slots.chapter = parseInt(chap\[1], 10);
if (/\bintro\b/.test(t)) slots.endpoint = "INTRO";
if (/\brecap\b/.test(t)) slots.endpoint = "RECAP";
if (/\breklam\b/.test(t)) slots.endpoint = "ADS";
return slots;
}
export function extractVolumeSlots(text: string) {
const t = normalizeSv(text);
const slots: any = {};
const levelPct = /(?\:satt|stall)\svolym(?\:en)?\s(?\:till|pa)\s\*(\d{1,3})\s\*%?/;
const levelBare = /\bvolym(?\:en)?\s\*(\d{1,3})\b/;
const deltaUp = /\b(h\[öo]j|oka|skruva upp)\s\*(\d{1,3})?\b/;
const deltaDown = /\b(s\[äa]nk|skruva ner|minska|d\[äa]mpa)\s\*(\d{1,3})?\b/;
let m = t.match(levelPct) || t.match(levelBare);
if (m) {
const v = Math.max(0, Math.min(100, parseInt(m\[1], 10)));
slots.level = v;
return slots;
}
m = t.match(deltaUp);
if (m) slots.delta = parseInt(m\[2] ?? "10", 10);
m = t.match(deltaDown);
if (m) slots.delta = -parseInt(m\[2] ?? "10", 10);
return slots;
}
export function extractLanguage(text: string) {
const t = normalizeSv(text);
if (/\bsvensk/.test(t)) return "svenska";
if (/\bengelsk/.test(t)) return "engelska";
return undefined;
}
export function isAffirmative(text: string) {
const t = normalizeSv(text);
return /\b(ja|k\[öo]r|kor)\b/.test(t);
}
export function isNegative(text: string) {
const t = normalizeSv(text);
return /\b(nej|stopp|avbryt)\b/.test(t);
}
END FILE

BEGIN FILE: /jarvis-tools/src/router/router.ts
import lexicon from "../lexicon/sv\_media\_commands.json" assert { type: "json" };
import devices from "../lexicon/devices.json" assert { type: "json" };
import { normalizeSv, extractTimeSlots, extractVolumeSlots, extractLanguage } from "./slots.js";
import { validateTool, ToolName } from "../schema/tools.js";
import leven from "leven";
type Match = { intent: string; score: number; phrase: string };
function scoreMatch(input: string, phrase: string): number {
const a = normalizeSv(input);
const b = normalizeSv(phrase);
if (a === b) return 1.0;
if (a.includes(b) || b.includes(a)) return 0.9;
const aSet = new Set(a.split(" "));
const bSet = new Set(b.split(" "));
const overlap = \[...aSet].filter(x => bSet.has(x)).length / Math.max(aSet.size, bSet.size);
return Math.min(0.85, overlap);
}
export function ruleFirstClassify(input: string): Match | null {
let best: Match | null = null;
for (const \[intent, synonyms] of Object.entries(lexicon.intents)) {
for (const s of synonyms as string\[]) {
const score = scoreMatch(input, s);
if (!best || score > best.score) best = { intent, score, phrase: s };
}
}
return best && best.score >= 0.6 ? best : null;
}
export type RoutedCall = { name: ToolName; args: any; rationale?: string };
function resolveDeviceAlias(input: string): string | undefined {
const t = normalizeSv(input);
for (const \[room, aliases] of Object.entries(devices.aliases as Record\<string, string\[]>)) {
if (t.includes(room)) return room;
for (const alias of aliases) {
const dist = leven(t, normalizeSv(alias));
if (dist <= 2 || t.includes(normalizeSv(alias))) return room;
}
}
return undefined;
}
export function mapIntentToTool(input: string, intent: string, context?: { focus?: "player"|"chapters"|"queue"; }): RoutedCall | null {
const t = normalizeSv(input);
switch (intent) {
case "PLAY": return { name: "PLAY", args: {} };
case "PAUSE": return { name: "PAUSE", args: {} };
case "STOP": return { name: "STOP", args: {} };
case "SEEK\_FWD": {
const slots = extractTimeSlots(t);
const seconds = slots.seconds ?? 10;
return { name: "SEEK", args: { direction: "FWD", seconds } };
}
case "SEEK\_BACK": {
const slots = extractTimeSlots(t);
const seconds = slots.seconds ?? 10;
return { name: "SEEK", args: { direction: "BACK", seconds } };
}
case "SEEK\_TO": {
const slots = extractTimeSlots(t);
if (slots.endpoint === "START") return { name: "SEEK", args: { position: 0 } };
if (slots.endpoint === "END") return { name: "SEEK", args: { position: 1 } };
if (slots.endpoint === "INTRO") return { name: "SEEK", args: { endpoint: "INTRO" } };
if (slots.endpoint === "RECAP") return { name: "SEEK", args: { endpoint: "RECAP" } };
if (slots.endpoint === "ADS") return { name: "SEEK", args: { endpoint: "ADS" } };
if (slots.to) return { name: "SEEK", args: { to: slots.to } };
if (slots.chapter) return { name: "SEEK", args: { chapter: slots.chapter } };
return null;
}
case "NEXT": {
if (context?.focus === "chapters") return { name: "SEEK", args: { chapter: (Number.NaN) } };
return { name: "NEXT", args: {} };
}
case "PREV": {
if (context?.focus === "chapters") return { name: "SEEK", args: { chapter: (Number.NaN) } };
return { name: "PREV", args: {} };
}
case "REPEAT\_ON": return { name: "SET\_QUALITY", args: { quality: "repeat\:on" } };
case "REPEAT\_OFF": return { name: "SET\_QUALITY", args: { quality: "repeat\:off" } };
case "SHUFFLE\_ON": return { name: "SET\_QUALITY", args: { quality: "shuffle\:on" } };
case "SHUFFLE\_OFF": return { name: "SET\_QUALITY", args: { quality: "shuffle\:off" } };
case "VOL\_UP": {
const slots = extractVolumeSlots(t);
const delta = slots.delta ?? 10;
return { name: "SET\_VOLUME", args: { delta } };
}
case "VOL\_DOWN": {
const slots = extractVolumeSlots(t);
const delta = slots.delta ?? -10;
return { name: "SET\_VOLUME", args: { delta } };
}
case "SET\_VOL": {
const slots = extractVolumeSlots(t);
if (typeof slots.level === "number") return { name: "SET\_VOLUME", args: { level: slots.level } };
return null;
}
case "MUTE": return { name: "MUTE", args: {} };
case "UNMUTE": return { name: "UNMUTE", args: {} };
case "SPEED\_UP": return { name: "SET\_SPEED", args: { rate: 1.25 } };
case "SPEED\_DOWN": return { name: "SET\_SPEED", args: { rate: 0.75 } };
case "SPEED\_NORMAL": return { name: "SET\_SPEED", args: { rate: 1.0 } };
case "QUALITY\_SET": return { name: "SET\_QUALITY", args: { quality: "auto" } };
case "FULLSCREEN\_ON": return { name: "FULLSCREEN\_ON", args: {} };
case "FULLSCREEN\_OFF": return { name: "FULLSCREEN\_OFF", args: {} };
case "SUBS\_ON": return { name: "SUBS\_ON", args: {} };
case "SUBS\_OFF": return { name: "SUBS\_OFF", args: {} };
case "SUBS\_LANG": {
const lang = extractLanguage(t);
return { name: "SUBS\_LANG", args: { language: lang ?? "svenska" } };
}
case "AUDIO\_TRACK": {
const lang = extractLanguage(t);
return { name: "AUDIO\_TRACK", args: { language: lang } };
}
case "CAST\_START": {
const device = resolveDeviceAlias(t);
return { name: "CAST\_START", args: device ? { device } : {} };
}
case "CAST\_STOP": return { name: "CAST\_STOP", args: {} };
case "QUEUE\_SHOW": return { name: "QUEUE\_SHOW", args: {} };
case "QUEUE\_ADD": return { name: "QUEUE\_ADD", args: { query: input } };
case "QUEUE\_REMOVE": return { name: "QUEUE\_REMOVE", args: { query: input } };
case "QUEUE\_CLEAR": return { name: "QUEUE\_CLEAR", args: {} };
case "SKIP\_INTRO": return { name: "SEEK", args: { endpoint: "INTRO" } };
case "SKIP\_RECAP": return { name: "SEEK", args: { endpoint: "RECAP" } };
case "SKIP\_ADS": return { name: "SEEK", args: { endpoint: "ADS" } };
default: return null;
}
}
export function ruleFirstRoute(input: string, context?: { focus?: "player"|"chapters"|"queue"; }): RoutedCall | null {
const m = ruleFirstClassify(input);
if (!m) return null;
const call = mapIntentToTool(input, m.intent, context);
if (!call) return null;
validateTool(call.name as any, call.args);
return call as RoutedCall;
}
END FILE

BEGIN FILE: /jarvis-tools/src/llm/llm.ts
import fetch from "node-fetch";
import { ToolSchemas, ToolName, validateTool } from "../schema/tools.js";
type LlmTool = { name: ToolName; description: string; schema: any; };
function zodToJsonSchema(\_: any): any { return { type: "object", additionalProperties: true }; }
export function availableTools(): LlmTool\[] {
return Object.entries(ToolSchemas).map((\[name, schema]) => ({
name: name as ToolName,
description: `Tool ${name}`,
schema: zodToJsonSchema(schema)
}));
}
function systemPrompt() {
return `Du är en svensk verktygsrouter för en mediaspelare. Du får en användarfråga och ska ENBART välja ett verktyg från listan och returnera strikt JSON:
{"tool":"<TOOL_NAME>","args":{...},"explanation":"kort svensk förklaring"}
Om du inte säkert kan välja, returnera exakt: {"tool":"NONE","args":{},"explanation":"Oklart."}
Tillgängliga verktyg:
PLAY, PAUSE, STOP, SEEK, NEXT, PREV, SET_VOLUME, MUTE, UNMUTE, SET_SPEED, SET_QUALITY, FULLSCREEN_ON, FULLSCREEN_OFF, SUBS_ON, SUBS_OFF, SUBS_LANG, AUDIO_TRACK, CAST_START, CAST_STOP, QUEUE_SHOW, QUEUE_ADD, QUEUE_REMOVE, QUEUE_CLEAR.
Parametrar:
SEEK: { "direction":"FWD|BACK"?, "seconds":int?, "to":"HH:MM:SS|M:SS"?, "position":0..1?, "chapter":int?, "endpoint":"START|END|INTRO|RECAP|ADS"? }
SET_VOLUME: { "level":0..100?, "delta":-100..100? }
SET_SPEED: { "rate":0.25..3 }
SET_QUALITY: { "quality":string }
SUBS_LANG/AUDIO_TRACK: { "language":string }
CAST_START: { "device"?:string }
Regler:
Extrahera svenska slots: sek/min/procent, språk, "intro/recap/reklam".
Svara ALLTID med strikt JSON, ingen förklarande text utanför JSON.
Vid osäkerhet → "NONE".
Använd siffror, inte "1.5x" utan {"rate":1.5}.
Few-shot exempel:
Input: "hoppa fram 30 sek" → {"tool":"SEEK","args":{"direction":"FWD","seconds":30},"explanation":"Hoppar fram 30 sekunder."}
Input: "till 1:23" → {"tool":"SEEK","args":{"to":"1:23"},"explanation":"Hoppar till 1:23."}
Input: "sänk volymen 15" → {"tool":"SET_VOLUME","args":{"delta":-15},"explanation":"Sänker volymen 15 steg."}
Input: "volym 25%" → {"tool":"SET_VOLUME","args":{"level":25},"explanation":"Sätter volymen till 25%."}
Input: "svenska undertexter" → {"tool":"SUBS_LANG","args":{"language":"svenska"},"explanation":"Byter undertextspråk till svenska."}
Input: "byt till engelskt ljud" → {"tool":"AUDIO_TRACK","args":{"language":"engelska"},"explanation":"Byter ljudspår till engelska."}
Input: "helt skärm" → {"tool":"FULLSCREEN_ON","args":{},"explanation":"Går till helskärm."}
Input: "hoppa över intro" → {"tool":"SEEK","args":{"endpoint":"INTRO"},"explanation":"Hoppar över introt."}`.trim();
}
function parseLlmJson(s: string): any | null {
try {
const start = s.indexOf("{");
const end = s.lastIndexOf("}");
if (start >= 0 && end > start) return JSON.parse(s.slice(start, end + 1));
} catch {}
return null;
}
function autoFixArgs(tool: ToolName, args: any): any {
const fixed: any = { ...(args ?? {}) };
if (tool === "SET\_SPEED" && typeof fixed.rate === "string") {
const m = fixed.rate.match(/\[\d.,]+/);
if (m) fixed.rate = parseFloat(m\[0].replace(",", "."));
}
if (tool === "SET\_VOLUME") {
if (typeof fixed.level === "string") {
const m = fixed.level.match(/(\d{1,3})/);
if (m) fixed.level = parseInt(m\[1], 10);
}
if (typeof fixed.delta === "string") {
const m = fixed.delta.match(/-?\d{1,3}/);
if (m) fixed.delta = parseInt(m\[0], 10);
}
}
if (tool === "SEEK") {
if (typeof fixed.seconds === "string") {
const m = fixed.seconds.match(/-?\d{1,4}/);
if (m) fixed.seconds = parseInt(m\[0], 10);
}
}
return fixed;
}
export async function llmFallbackRoute(userInput: string) {
const body = {
model: "gpt-oss:20b",
messages: \[
{ role: "system", content: systemPrompt() },
{ role: "user", content: `Användarkommando: "${userInput}"` }
],
options: { temperature: 0.1 }
};
const res = await fetch("[http://localhost:11434/api/chat](http://localhost:11434/api/chat)", {
method: "POST",
headers: { "Content-Type": "application/json" },
body: JSON.stringify(body)
});
if (!res.ok) throw new Error(`LLM error: ${res.status} ${await res.text()}`);
const data: any = await res.json();
const text: string = data?.message?.content ?? "";
let obj = parseLlmJson(text);
if (!obj || !obj.tool) return null;
if (obj.tool === "NONE") return null;
let tool = obj.tool as ToolName;
let args = autoFixArgs(tool, obj.args ?? {});
try {
validateTool(tool, args);
return { name: tool, args, rationale: obj.explanation ?? "" };
} catch {
const repairBody = {
model: "gpt-oss:20b",
messages: \[
{ role: "system", content: `Givet verktyget ${tool} och följande JSON-schema, svara ENDAST med giltiga "args": ${JSON.stringify({})}.` },
{ role: "user", content: `Korrigera args så de validerar: ${JSON.stringify(args)}` }
],
options: { temperature: 0.0 }
};
const res2 = await fetch("[http://localhost:11434/api/chat](http://localhost:11434/api/chat)", {
method: "POST",
headers: { "Content-Type": "application/json" },
body: JSON.stringify(repairBody)
});
const data2: any = await res2.json();
const obj2 = parseLlmJson(data2?.message?.content ?? "");
if (obj2) {
args = autoFixArgs(tool, obj2);
try {
validateTool(tool, args);
return { name: tool, args, rationale: obj.explanation ?? "" };
} catch { return null; }
}
return null;
}
}
END FILE

BEGIN FILE: /jarvis-tools/src/index.ts
import { ruleFirstRoute } from "./router/router.js";
import { llmFallbackRoute } from "./llm/llm.js";
import pino from "pino";
import minimist from "minimist";
const log = pino({ level: "info" });
export async function routeCommand(input: string, context?: { focus?: "player"|"chapters"|"queue"; }) {
const r1 = ruleFirstRoute(input, context);
if (r1) {
log.info({ input, tool: r1.name, args: r1.args }, "Rule-first hit");
return r1;
}
const r2 = await llmFallbackRoute(input);
if (r2) {
log.info({ input, tool: r2.name, args: r2.args }, "LLM fallback hit");
return r2;
}
log.warn({ input }, "No route matched");
return { name: "NONE", args: {}, rationale: "Kunde inte tolka kommandot." };
}
if (import.meta.url === `file://${process.argv[1]}`) {
const argv = minimist(process.argv.slice(2));
const testsBasic = \[
"spela upp","pausa","stoppa","hoppa fram 30 sek","hoppa tillbaka en halv minut","hoppa ett par minuter fram","till 1:23","gå till slutet",
"höj volymen 15","volym 25%","stäng av ljudet","svenska undertexter","byt till engelskt ljud","helt skärm","casta till vardagsrummet",
"blanda låtar","repetera låt","hoppa över intro","hoppa över reklam","nästa video i kön"
];
const testsNone = \[ "kan du göra något kul", "vad borde jag se ikväll", "fixa det där" ];
const testInputs = argv.test ? testsBasic : argv\["test-none"] ? testsNone : \[process.argv.slice(2).join(" ") || "hoppa fram 30 sek"];
(async () => { for (const input of testInputs) { const result = await routeCommand(input, { focus: "player" }); console.log(JSON.stringify({ input, result }, null, 2)); } })();
}
END FILE

BEGIN FILE: /jarvis-tools/README.md
Nytt i 1.1.0
• Vaga svenska tidsuttryck (“ett par minuter”, “en halv minut”, “en stund”) → sekunder.
• Talord → siffror (“trettio sekunder”, “en och en halv minut”).
• Device-lexikon med fuzzy-match för CAST (“vardagsrummet”, “sonos kök”).
• Extra intents: SKIP\_INTRO/RECAP/ADS. NONE-policy kvar.
• LLM-fallback med svenska few-shots, auto-fix och ett validerings-retry.
• Disambiguering av “nästa/föregående” via context.focus (player/chapters/queue).

Snabbstart

1. Krav: Node 18+, Ollama lokalt med “gpt-oss:20b” (ollama serve; ollama pull gpt-oss:20b).
2. Installera: npm i (eller pnpm i).
3. Testa: npm run dev (interaktivt), npm run test\:router, npm run test\:none.
4. Integrera: routeCommand(text, { focus }) → koppla ToolName till din spelare. Validering via Zod.

Tips
• Lägg dina verkliga enhetsalias i lexicon/devices.json.
• Lägg fler svenska synonymer/felstavningar i sv\_media\_commands.json.
• Logga NONE/mismatch → lägg till i lexikonet.
END FILE

BEGIN FILE: /server/package.json
{
"name": "jarvis-server",
"version": "0.1.0",
"private": true,
"type": "module",
"scripts": {
"dev": "tsx src/index.ts",
"build": "tsc",
"start": "node dist/index.js"
},
"dependencies": {
"express": "^4.19.2",
"pino": "^9.4.0",
"cors": "^2.8.5",
"body-parser": "^1.20.2",
"node-fetch": "^3.3.2",
"minimist": "^1.2.8"
},
"devDependencies": {
"tsx": "^4.16.3",
"typescript": "^5.5.4"
}
}
END FILE

BEGIN FILE: /server/tsconfig.json
{
"compilerOptions": {
"target": "ES2022",
"module": "ES2022",
"moduleResolution": "Bundler",
"outDir": "dist",
"rootDir": "src",
"strict": true,
"esModuleInterop": true,
"skipLibCheck": true
},
"include": \["src"]
}
END FILE

BEGIN FILE: /server/src/nlu.ts
import type { Request, Response } from "express";
import { normalizeSv, extractTimeSlots, extractVolumeSlots, extractLanguage } from "../../jarvis-tools/src/router/slots.js";
import { ruleFirstClassify } from "../../jarvis-tools/src/router/router.js";
// En enkel, datasets-agnostisk klassificerare: kombinera rule-first med små exempel från klient (valfritt).
type IntentOut = { intent: string|null; score: number; phrase?: string };
export function postExtract(req: Request, res: Response) {
const text: string = String(req.body?.text ?? "");
const slots: any = {
...extractTimeSlots(text),
...extractVolumeSlots(text)
};
const lang = extractLanguage(text);
if (lang) slots.language = lang;
const confidence =
typeof slots.seconds === "number" || slots.to || slots.endpoint || typeof slots.level === "number" || typeof slots.delta === "number" || lang
? 0.9 : 0.5;
res.json({ slots, confidence });
}
export function postClassify(req: Request, res: Response) {
const text: string = String(req.body?.text ?? "");
const rf = ruleFirstClassify(text);
if (!rf) return res.json({ intent: null, score: 0.0 });
return res.json({ intent: rf.intent, score: rf.score, phrase: rf.phrase });
}
END FILE

BEGIN FILE: /server/src/agent.ts
import type { Request, Response } from "express";
import fetch from "node-fetch";
import { routeCommand } from "../../jarvis-tools/src/index.js";
type Plan = { plan?: { tool: string; params: any }; confidence?: number; needs\_confirmation?: boolean; fallback?: "llm"; reason?: string; context?: any };
async function callNLU(path: string, body: any) {
const res = await fetch(`http://localhost:7071${path}`, {
method: "POST",
headers: { "Content-Type": "application/json" },
body: JSON.stringify(body)
});
if (!res.ok) throw new Error(`NLU ${path} failed: ${res.status}`);
return res.json();
}
export async function postRoute(req: Request, res: Response) {
const text: string = String(req.body?.text ?? "");
try {
const \[extract, classify] = await Promise.all(\[
callNLU("/nlu/extract", { text }),
callNLU("/nlu/classify", { text })
]);
const score = Number(classify?.score ?? 0);
const intent = classify?.intent as string | null;
// Om media-intent mappas, använd jarvis-tools direkt (rule-first/LLM) för verktygsanrop:
if (score >= 0.7 && intent) {
const r = await routeCommand(text, { focus: "player" });
if (r && r.name !== "NONE") {
return res.json({ plan: { tool: r.name, params: r.args }, confidence: Math.min(0.95, score), needs\_confirmation: true });
}
}
// LLM-fallback via jarvis-tools (strikt tool calling)
const r2 = await routeCommand(text, { focus: "player" });
if (r2 && r2.name !== "NONE") {
return res.json({ plan: { tool: r2.name, params: r2.args }, confidence: 0.75, needs\_confirmation: true });
}
// Ingen tolkning → be HUD fråga om förtydligande eller skicka till generell LLM
return res.json({ fallback: "llm", reason: "low\_nlu\_score", context: { recent: \[], extract } } as Plan);
} catch (e: any) {
return res.status(500).json({ error: String(e?.message ?? e) });
}
}
END FILE

BEGIN FILE: /server/src/index.ts
import express from "express";
import cors from "cors";
import bodyParser from "body-parser";
import pino from "pino";
import { postExtract, postClassify } from "./nlu.js";
import { postRoute } from "./agent.js";
const log = pino({ level: "info" });
const app = express();
app.use(cors());
app.use(bodyParser.json());
app.post("/nlu/extract", postExtract);
app.post("/nlu/classify", postClassify);
app.post("/agent/route", postRoute);
const PORT = Number(process.env.PORT ?? 7071);
app.listen(PORT, () => log.info({ PORT }, "Jarvis server up"));
END FILE

BEGIN FILE: /README-JARVIS-NLU-AGENT.md
Jarvis NLU + Agent – snabbstart (Next.js HUD orörd)

1. Krav: Node 18+, Ollama igång lokalt (ollama serve) och modellen gpt-oss:20b nedladdad (ollama pull gpt-oss:20b).
2. Installera:
   cd jarvis-tools && npm i && cd ..
   cd server && npm i && cd ..
3. Kör:
   i terminal A: cd server && npm run dev (server på [http://localhost:7071](http://localhost:7071))
   i terminal B: cd jarvis-tools && npm run test\:router
4. HUD-koppling (klientsidan):
   POST till [http://localhost:7071/agent/route](http://localhost:7071/agent/route) med body {"text":"<ASR-text>"}.
   Visa “Dry-run: Jag tänker göra <tool>(<params>). Kör?” med Bekräfta/Avbryt.
   Vid Bekräfta: anropa din mediaspelares adapter enligt verktygsnamn/parametrar.
5. Loggning & förbättring:
   Lägg till loggar i HUD med serverresponsen. Spara NONE/fallback-case för att utöka lexikonet.
6. Utöka intents:
   Lägg synonymer i jarvis-tools/src/lexicon/sv\_media\_commands.json. Lägg enhetsalias i jarvis-tools/src/lexicon/devices.json.
7. Guardrails:
   Visa alltid dry-run och kräv bekräftelse före åtgärd. Vid osäkerhet (fallback) – be om förtydligande.

Testexempel
“hoppa fram 30 sek”, “hoppa ett par minuter fram”, “till 1:23”, “svenska undertexter”, “helt skärm”, “casta till vardagsrummet”, “hoppa över intro”.

Arkitektur i korthet
HUD (Next.js) → /agent/route → (NLU /extract + /classify) → jarvis-tools rule-first → ev. LLM-fallback → plan {tool, params} → HUD (dry-run).

Tips
• Sätt focus: "player|chapters|queue" i agenten om du vill påverka “nästa/föregående”.
• NONE-svar = träningstillfälle: lägg nya fraser i lexikonet eller öka few-shots i llm.ts.
END FILE



1. Starta Ollama (om inte igång): ollama serve och säkerställ att modellen gpt-oss:20b är nedladdad.
2. I projektroten: cd jarvis-tools && npm i && npm run test\:router för snabba sanity-tests.
3. I en ny terminal: cd server && npm i && npm run dev för att starta NLU/agent på [http://localhost:7071](http://localhost:7071).
4. Från HUD: POST /agent/route med texten från ASR och visa dry-run.


