export function normalizeSv(s: string) {
  const lower = s.toLowerCase().normalize("NFD").replace(/\p{Diacritic}/gu, "");
  return lower.replace(/\s+/g, " ").trim();
}

const NUMBER_WORDS: Record<string, number> = {
  "noll": 0, "en": 1, "ett": 1, "två": 2, "tva": 2, "tre": 3, "fyra": 4, "fem": 5,
  "sex": 6, "sju": 7, "åtta": 8, "atta": 8, "nio": 9, "tio": 10, "elva": 11, "tolv": 12,
  "tretton": 13, "fjorton": 14, "femton": 15, "sexton": 16, "sjutton": 17, "arton": 18,
  "nitton": 19, "tjugo": 20, "trettio": 30, "fyrtio": 40, "femtio": 50, "sextio": 60,
  "sjuttio": 70, "åttio": 80, "nittio": 90, "hundra": 100
};

function wordsToNumber(tokens: string[]): number | undefined {
  let total = 0; let matched = false;
  for (const t of tokens) {
    if (t in NUMBER_WORDS) { total += NUMBER_WORDS[t]; matched = true; }
    else if (/^\d+$/.test(t)) { total += parseInt(t, 10); matched = true; }
  }
  return matched ? total : undefined;
}

function vagueToSeconds(text: string): number | undefined {
  const t = normalizeSv(text);
  if (/\bett par\b/.test(t)) return 120;
  if (/\benh[aä]lv\b/.test(t)) return 30;
  if (/\ben stund\b/.test(t)) return 45;
  return undefined;
}

export function extractTimeSlots(text: string) {
  const t = normalizeSv(text);
  const slots: any = {};
  const secRel = /(\d{1,3})\s*(sek|sekunder|s)\b/;
  const minRel = /(\d{1,3})\s*(min|minuter|m)\b/;
  const mSec = t.match(secRel);
  if (mSec) slots.seconds = parseInt(mSec[1], 10);
  const mMin = t.match(minRel);
  if (mMin) slots.seconds = (slots.seconds ?? 0) + parseInt(mMin[1], 10) * 60;
  if (!slots.seconds) {
    const tokens = t.split(/\s+/);
    const num = wordsToNumber(tokens);
    if (num && /\b(min|minuter|minute?n)\b/.test(t)) slots.seconds = num * 60;
    else if (num && /\b(sek|sekunder|sekund)\b/.test(t)) slots.seconds = num;
  }
  if (!slots.seconds) {
    const vague = vagueToSeconds(t);
    if (vague) slots.seconds = vague;
  }
  // specialfall: "en halv minut" = 30 sek
  if (!slots.seconds && /\ben halv minut\b/.test(t)) slots.seconds = 30;
  const toHMS = /\b(?:till|vid|pa)\s*((?:\d{1,2}:)?\d{1,2}:\d{2})\b/;
  const mTo = t.match(toHMS);
  if (mTo) slots.to = mTo[1];
  if (/(ga|hoppa)\s*till\s*borjan|\bborja\s*om\b/.test(t)) slots.endpoint = "START";
  if (/\bfr[aå]n\s*(borjan|start(en)?)\b/.test(t)) slots.endpoint = "START";
  if (/(ga|hoppa)\s*till\s*slutet|eftertexter\b/.test(t)) slots.endpoint = "END";
  if (/\bintro\b/.test(t)) slots.endpoint = "INTRO";
  if (/\brecap\b/.test(t)) slots.endpoint = "RECAP";
  if (/\breklam\b/.test(t)) slots.endpoint = "ADS";
  return slots;
}

export function extractVolumeSlots(text: string) {
  const t = normalizeSv(text);
  const slots: any = {};
  const levelPct = /(?:satt|stall)\s*volym(?:en)?\s*(?:till|pa)\s*(\d{1,3})\s*%?/;
  const levelBare = /\bvolym(?:en)?\s*(\d{1,3})\b/;
  const setToPct = /\b(h[öo]j|s[äa]nk)\s*(?:volym(?:en)?)?\s*(?:till|pa)\s*(\d{1,3})\s*%?/;
  const deltaUp = /\b(h[öo]j|ok[aå]|oka|skruva upp)\s*(\d{1,3})?\s*%?/;
  const deltaDown = /\b(s[äa]nk|skruva ner|minska|d[äa]mpa)\s*(\d{1,3})?\s*%?/;
  let m = t.match(levelPct) || t.match(levelBare);
  if (m) { slots.level = Math.max(0, Math.min(100, parseInt(m[1], 10))); return slots; }
  m = t.match(setToPct); if (m) { slots.level = Math.max(0, Math.min(100, parseInt(m[2], 10))); return slots; }
  // max/min utan siffra
  if (/(\bmax(imum|imalt)?\b|\bhogsta\b|\b100\s*%\b|\bhundra\s*procent\b|\bfull\s*volym\b|\bmax\s*volym\b|sa\s*hogt(\s*som\s*mojligt)?|sa\s*hogt\s*det\s*gar|pa\s*(hogsta|max)\b)/.test(t)) {
    slots.level = 100; return slots;
  }
  if (/(\bmin(imum|imalt)?\b|\btyst\b|\b0\s*%\b|\bnoll\s*procent\b)/.test(t)) {
    slots.level = 0; return slots;
  }
  m = t.match(deltaUp); if (m) slots.delta = parseInt(m[2] ?? "10", 10);
  m = t.match(deltaDown); if (m) slots.delta = -parseInt(m[2] ?? "10", 10);
  return slots;
}

export function extractLanguage(text: string) {
  const t = normalizeSv(text);
  if (/\bsvensk/.test(t)) return "svenska";
  if (/\bengelsk/.test(t)) return "engelska";
  return undefined;
}

// ────────────────────────────────────────────────────────────────────────────────
// Room & Device slots
import { createRequire } from "node:module";
const require = createRequire(import.meta.url);
const devicesJson: { canonical: string[]; aliases: Record<string, string> } = require("../lexicon/devices.json");

const ROOM_ALIASES: Record<string, string> = {
  "vardagsrummet": "vardagsrummet",
  "vardagsrum": "vardagsrummet",
  "v-rum": "vardagsrummet",
  "köket": "köket",
  "koket": "köket",
  "kök": "köket",
  "sovrummet": "sovrummet",
  "sovrum": "sovrummet",
  "kontoret": "kontoret",
  "office": "kontoret"
};

function normalizeRoom(token: string): string | undefined {
  const t = normalizeSv(token);
  return ROOM_ALIASES[t];
}

function normalizeDevice(token: string): string | undefined {
  const t = normalizeSv(token);
  const aliases = devicesJson.aliases;
  const canonical = devicesJson.canonical;
  if (aliases && aliases[t]) return aliases[t];
  if (canonical && canonical.includes(t)) return t;
  return undefined;
}

export function extractRoomSlot(text: string): string | undefined {
  const t = normalizeSv(text);
  // mönster: "i köket", "i vardagsrummet", "till sovrummet", "på kontoret"
  const m = t.match(/\b(?:i|pa|på|till)\s+([a-zåäö\-]+)\b/);
  if (m) {
    const room = normalizeRoom(m[1]);
    if (room) return room;
  }
  // fristående nämning
  for (const [alias, canon] of Object.entries(ROOM_ALIASES)) {
    if (t.includes(alias)) return canon;
  }
  return undefined;
}

export function extractDeviceSlot(text: string): string | undefined {
  const t = normalizeSv(text);
  // direkta träffar
  const tokens = t.split(/[^a-z0-9åäö]+/).filter(Boolean);
  for (const tok of tokens) {
    const dev = normalizeDevice(tok);
    if (dev) return dev;
  }
  // frasmönster: "spela på X", "casta till X"
  const m = t.match(/\b(?:pa|på|till)\s+([a-zåäö0-9\-\s]{2,})$/);
  if (m) {
    const guess = normalizeDevice(m[1].trim());
    if (guess) return guess;
  }
  return undefined;
}

