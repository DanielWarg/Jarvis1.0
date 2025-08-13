import { normalizeSv, extractTimeSlots, extractVolumeSlots, extractLanguage } from "./slots.js";

type Match = { intent: string; score: number; phrase: string };

const LEXICON: Record<string, string[]> = {
  PLAY: ["spela", "spela upp", "starta", "fortsätt"],
  PAUSE: ["pausa", "lägg på paus"],
  STOP: ["stop", "stopp", "stoppa", "avsluta"],
  NEXT: ["nästa", "hoppa över"],
  PREV: ["föregående", "gå tillbaka"],
  SEEK_FWD: ["spola fram", "hoppa fram"],
  SEEK_BACK: ["spola tillbaka", "hoppa tillbaka"],
  SEEK_TO: ["hoppa till", "gå till", "spela från"],
  VOL_UP: ["höj volymen", "höj volym", "ök[aå] volym", "starkare", "högre", "skruva upp"],
  VOL_DOWN: ["sänk volymen", "sänk volym", "minska volym", "lägre", "tystare", "skruva ner", "dämpa"],
  SET_VOL: ["volym", "sätt volymen till", "ställ volymen på", "volym procent"],
  MUTE: ["mute", "stäng av ljudet", "tysta", "ljud av"],
  UNMUTE: ["avmuta", "slå på ljud", "ljud på", "avdämpa"],
  // kortformer utan "volym" för fraser som "höj 20%" / "sänk 15%"
  VOL_UP_SHORT: ["höj"],
  VOL_DOWN_SHORT: ["sänk"],
  SET_VOL_MAX: ["max", "maximalt", "högsta"],
  SET_VOL_MIN: ["min", "minimalt", "tyst"],
};

function scoreMatch(input: string, phrase: string): number {
  const a = normalizeSv(input);
  const b = normalizeSv(phrase);
  if (a === b) return 1.0;
  if (a.includes(b) || b.includes(a)) return 0.9;
  const aSet = new Set(a.split(" "));
  const bSet = new Set(b.split(" "));
  const overlap = [...aSet].filter(x => bSet.has(x)).length / Math.max(aSet.size, bSet.size);
  return Math.min(0.85, overlap);
}

export function ruleFirstClassify(input: string): Match | null {
  let best: Match | null = null;
  for (const [intent, synonyms] of Object.entries(LEXICON)) {
    for (const s of synonyms) {
      const score = scoreMatch(input, s);
      if (!best || score > best.score) best = { intent, score, phrase: s };
    }
  }
  return best && best.score >= 0.6 ? best : null;
}

export type RoutedCall = { name: string; args: any };

export function mapIntentToTool(input: string, intent: string): RoutedCall | null {
  const t = normalizeSv(input);
  switch (intent) {
    case "PLAY": return { name: "PLAY", args: {} };
    case "PAUSE": return { name: "PAUSE", args: {} };
    case "STOP": return { name: "STOP", args: {} };
    case "NEXT": return { name: "NEXT", args: {} };
    case "PREV": return { name: "PREV", args: {} };
    case "SEEK_FWD": {
      const slots = extractTimeSlots(t);
      return { name: "SEEK", args: { direction: "FWD", seconds: slots.seconds ?? 10 } };
    }
    case "SEEK_BACK": {
      const slots = extractTimeSlots(t);
      return { name: "SEEK", args: { direction: "BACK", seconds: slots.seconds ?? 10 } };
    }
    case "SEEK_TO": {
      const slots = extractTimeSlots(t);
      if (slots.endpoint === "START") return { name: "SEEK", args: { position: 0 } };
      if (slots.endpoint === "END") return { name: "SEEK", args: { position: 1 } };
      if (slots.endpoint) return { name: "SEEK", args: { endpoint: slots.endpoint } };
      if (slots.to) return { name: "SEEK", args: { to: slots.to } };
      return null;
    }
    case "VOL_UP":
    case "VOL_UP_SHORT": {
      const s = extractVolumeSlots(t);
      if (typeof (s as any).level === 'number') return { name: "SET_VOLUME", args: { level: (s as any).level } };
      const delta = typeof s.delta === 'number' ? s.delta : 10; return { name: "SET_VOLUME", args: { delta } };
    }
    case "VOL_DOWN":
    case "VOL_DOWN_SHORT": {
      const s = extractVolumeSlots(t);
      if (typeof (s as any).level === 'number') return { name: "SET_VOLUME", args: { level: (s as any).level } };
      const delta = typeof s.delta === 'number' ? -Math.abs(s.delta) : -10; return { name: "SET_VOLUME", args: { delta } };
    }
    case "SET_VOL": {
      const s = extractVolumeSlots(t); if (typeof s.level === 'number') return { name: "SET_VOLUME", args: { level: s.level } }; return null;
    }
    case "SET_VOL_MAX": return { name: "SET_VOLUME", args: { level: 100 } };
    case "SET_VOL_MIN": return { name: "SET_VOLUME", args: { level: 0 } };
    case "MUTE": return { name: "MUTE", args: {} };
    case "UNMUTE": return { name: "UNMUTE", args: {} };
    default: return null;
  }
}

export function ruleFirstRoute(input: string): RoutedCall | null {
  const m = ruleFirstClassify(input);
  if (!m) return null;
  return mapIntentToTool(input, m.intent);
}

