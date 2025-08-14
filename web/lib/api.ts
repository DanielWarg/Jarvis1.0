import type { ChatSyncResponse, StreamEvent, ToolMeta } from "@/types/chat";

const API = process.env.NEXT_PUBLIC_API_BASE ?? "http://127.0.0.1:8000";

export async function chatOnce(prompt: string): Promise<ChatSyncResponse> {
  const r = await fetch(`${API}/api/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text: prompt, stream: false }),
  });
  return await r.json();
}

/** Enkel SSE-parse (POST->SSE kräver ev. serverändring; om ni redan har POST-stream, bygg reader/NDJSON) */
export async function chatStream(
  prompt: string,
  onEvent: (ev: StreamEvent) => void,
  signal?: AbortSignal
) {
  const r = await fetch(`${API}/api/chat/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text: prompt, stream: true }),
    signal,
  });
  const reader = r.body!.getReader();
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
        const ev = JSON.parse(json) as StreamEvent;
        onEvent(ev);
      } catch {}
    }
    buf = parts[parts.length - 1];
  }
}
