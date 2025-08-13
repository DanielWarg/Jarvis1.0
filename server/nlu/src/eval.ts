import fs from 'node:fs';
import path from 'node:path';
import natural from 'natural';

type Sample = { text: string; intent: string };

const dataPath = path.resolve(process.cwd(), '../../data/nlu/intents.jsonl');

function loadDataset(): Sample[] {
  const lines = fs.readFileSync(dataPath, 'utf8').split(/\r?\n/).filter(Boolean);
  return lines.map(l => { try { return JSON.parse(l) as Sample; } catch { return null as any; } }).filter(Boolean);
}

function shuffle<T>(arr: T[]): T[] { return [...arr].sort(() => Math.random() - 0.5); }

function f1Score(yTrue: string[], yPred: string[]) {
  const labels = Array.from(new Set([...yTrue, ...yPred]));
  let microTP = 0, microFP = 0, microFN = 0;
  const perLabel: Record<string, { tp: number; fp: number; fn: number }> = {};
  for (const l of labels) perLabel[l] = { tp: 0, fp: 0, fn: 0 };
  for (let i = 0; i < yTrue.length; i++) {
    const t = yTrue[i]; const p = yPred[i];
    if (t === p) { perLabel[t].tp++; microTP++; }
    else { perLabel[p]?.fp++; perLabel[t].fn++; microFP++; microFN++; }
  }
  const macro = labels.reduce((acc, l) => {
    const { tp, fp, fn } = perLabel[l];
    const prec = tp + fp === 0 ? 0 : tp / (tp + fp);
    const rec = tp + fn === 0 ? 0 : tp / (tp + fn);
    const f1 = prec + rec === 0 ? 0 : (2 * prec * rec) / (prec + rec);
    return acc + f1;
  }, 0) / labels.length;
  const microPrec = microTP + microFP === 0 ? 0 : microTP / (microTP + microFP);
  const microRec = microTP + microFN === 0 ? 0 : microTP / (microTP + microFN);
  const microF1 = microPrec + microRec === 0 ? 0 : (2 * microPrec * microRec) / (microPrec + microRec);
  const acc = yTrue.filter((t, i) => t === yPred[i]).length / yTrue.length;
  return { acc, microF1, macroF1: macro };
}

function evaluateOnce(train: Sample[], test: Sample[]) {
  const clf = new (natural as any).BayesClassifier();
  for (const s of train) clf.addDocument(s.text, s.intent);
  clf.train();
  const gold: string[] = []; const pred: string[] = [];
  const t0 = Date.now();
  for (const s of test) { gold.push(s.intent); pred.push(clf.classify(s.text)); }
  const latencyMs = (Date.now() - t0) / Math.max(1, test.length);
  const { acc, microF1, macroF1 } = f1Score(gold, pred);
  return { acc, microF1, macroF1, latencyMs };
}

function kFoldEval(samples: Sample[], k = 5) {
  const data = shuffle(samples);
  const foldSize = Math.max(1, Math.floor(data.length / k));
  const results = [] as any[];
  for (let i = 0; i < k; i++) {
    const start = i * foldSize;
    const end = i === k - 1 ? data.length : (i + 1) * foldSize;
    const test = data.slice(start, end);
    const train = [...data.slice(0, start), ...data.slice(end)];
    results.push(evaluateOnce(train, test));
  }
  const avg = (key: string) => results.reduce((a, r) => a + r[key], 0) / results.length;
  return { acc: avg('acc'), microF1: avg('microF1'), macroF1: avg('macroF1'), latencyMs: avg('latencyMs') };
}

const ds = loadDataset();
const out = kFoldEval(ds, 5);
console.log(JSON.stringify({ n: ds.length, ...out }, null, 2));


