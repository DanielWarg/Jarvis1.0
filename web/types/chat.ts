export type ToolMeta = {
  name: "PLAY" | "PAUSE" | "SET_VOLUME" | "DISPLAY" | "SAY" | string;
  args: Record<string, unknown>;
  source: "router" | "harmony";
  executed: boolean;
  latency_ms: number;
};

export type ChatSyncResponse = {
  ok?: boolean;
  text: string;
  meta?: { tool?: ToolMeta };
  provider?: "router" | "local" | "openai";
  engine?: string | null;
};

export type MetaEvent = { type: "meta"; meta: { tool?: ToolMeta } };
export type FinalEvent = { type: "final"; text: string };
export type ChunkEvent = { type: "chunk"; text: string };
export type DoneEvent = { type: "done"; provider?: string; memory_id?: number | null };
export type StreamEvent = MetaEvent | FinalEvent | ChunkEvent | DoneEvent;
