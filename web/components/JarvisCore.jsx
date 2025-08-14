"use client";
import * as React from "react";
import { Card } from "../components/ui/card";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { useUIStore } from "../store/uiStore";

export function JarvisCore() {
  const [prompt, setPrompt] = React.useState("");
  const startIntent = useUIStore((s) => s.startIntent);
  const setMetaTool = useUIStore((s) => s.setMetaTool);
  const pushToolLog = useUIStore((s) => s.pushToolLog);
  const setFinal = useUIStore((s) => s.setFinal);
  const appendChunk = useUIStore((s) => s.appendChunk);
  const finishIntent = useUIStore((s) => s.finishIntent);

  const controllerRef = React.useRef(null);

  const onSend = async () => {
    const id = crypto.randomUUID();
    startIntent({ id, userText: prompt });

    // STREAM (rekommenderat)
    controllerRef.current?.abort();
    controllerRef.current = new AbortController();

    try {
      const r = await fetch(`${process.env.NEXT_PUBLIC_API_BASE ?? "http://127.0.0.1:8000"}/api/chat/stream`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text: prompt, stream: true }),
        signal: controllerRef.current.signal
      });

      const reader = r.body.getReader();
      const decoder = new TextDecoder();
      let buf = "";

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        buf += decoder.decode(value, { stream: true });
        const parts = buf.split("\n\n");
        for (let i = 0; i < parts.length - 1; i++) {
          const line = parts[i].trim();
          if (!line.startsWith("data:")) continue;
          const json = line.slice(5).trim();
          try {
            const ev = JSON.parse(json);
            if (ev.type === "meta" && ev.meta.tool) {
              const m = ev.meta.tool;
              setMetaTool(id, m);
              pushToolLog({
                t: Date.now(),
                name: m.name,
                source: m.source,
                args: m.args,
                executed: m.executed,
                latencyMs: m.latency_ms,
                status: m.executed ? "ok" : "error",
              });
            } else if (ev.type === "chunk") {
              appendChunk(id, ev.text);
            } else if (ev.type === "final") {
              setFinal(id, ev.text);
            } else if (ev.type === "done") {
              finishIntent(id);
            }
          } catch {}
        }
        buf = parts[parts.length - 1];
      }
    } catch (err) {
      if (err.name !== "AbortError") {
        console.error("Stream error:", err);
      }
    }

    setPrompt("");
  };

  const onAbort = () => {
    controllerRef.current?.abort();
  };

  return (
    <Card className="p-4 bg-background/40 backdrop-blur space-y-3">
      <div className="text-sm font-semibold opacity-80">JARVIS CORE</div>
      <div className="flex gap-2">
        <Input
          className="flex-1 bg-transparent"
          placeholder="Fråga Jarvis…"
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              onSend();
            }
          }}
        />
        <Button onClick={onSend}>Go</Button>
        <Button variant="outline" onClick={onAbort}>Stop</Button>
      </div>
    </Card>
  );
}