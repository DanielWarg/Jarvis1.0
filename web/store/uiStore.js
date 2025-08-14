import { create } from "zustand";

export const useUIStore = create((set, get) => ({
  intentQueue: [],
  toolLog: [],
  diagnostics: { p50Final: 0, p95Final: 0, routerHitRate: 0, refusalRate: 0 },
  stream: { speaking: false, partialText: "", finalText: "" },

  startIntent: ({ id, userText }) =>
    set((s) => ({
      intentQueue: [
        { id, userText, route: null, tool: null, startedAt: Date.now(), status: "pending" },
        ...s.intentQueue,
      ],
      stream: { ...s.stream, speaking: true, finalText: "" },
    })),

  setMetaTool: (id, meta) =>
    set((s) => ({
      intentQueue: s.intentQueue.map((it) =>
        it.id === id
          ? { ...it, route: meta.source, tool: { name: meta.name, args: meta.args } }
          : it
      ),
    })),

  pushToolLog: (e) => set((s) => ({ toolLog: [e, ...s.toolLog].slice(0, 50) })),

  appendChunk: (id, chunk) =>
    set((s) => ({
      stream: { ...s.stream, finalText: s.stream.finalText + chunk },
      intentQueue: s.intentQueue.map((it) =>
        it.id === id ? { ...it, finalText: (it.finalText ?? "") + chunk } : it
      ),
    })),

  setFinal: (id, final) =>
    set((s) => ({
      stream: { ...s.stream, finalText: final },
      intentQueue: s.intentQueue.map((it) => (it.id === id ? { ...it, finalText: final } : it)),
    })),

  finishIntent: (id) =>
    set((s) => ({
      stream: { ...s.stream, speaking: false },
      intentQueue: s.intentQueue.map((it) =>
        it.id === id
          ? { ...it, finishedAt: Date.now(), totalLatencyMs: Date.now() - it.startedAt, status: "ok" }
          : it
      ),
    })),

  setRefused: (id, msg) =>
    set((s) => ({
      intentQueue: s.intentQueue.map((it) =>
        it.id === id ? { ...it, status: "refused", finalText: msg ?? it.finalText } : it
      ),
    })),

  setError: (id, err) =>
    set((s) => ({
      diagnostics: { ...s.diagnostics, lastError: err },
      stream: { ...s.stream, speaking: false },
      intentQueue: s.intentQueue.map((it) =>
        it.id === id ? { ...it, status: "error" } : it
      ),
    })),

  recomputeDiagnostics: () => {
    const q = get().intentQueue.filter((i) => i.totalLatencyMs);
    const lat = q.map((i) => i.totalLatencyMs).sort((a,b)=>a-b);
    const p = (p) => (lat.length ? lat[Math.floor(p * (lat.length - 1))] : 0);
    const router = get().toolLog.filter((t) => t.source === "router").length;
    const totalTools = get().toolLog.length || 1;
    const refusal = get().intentQueue.filter((i) => i.status === "refused").length;
    set({
      diagnostics: {
        p50Final: p(0.5), p95Final: p(0.95),
        routerHitRate: (router / totalTools) * 100,
        refusalRate: (refusal / (get().intentQueue.length || 1)) * 100,
        lastError: get().diagnostics.lastError,
      },
    });
  },
}));
