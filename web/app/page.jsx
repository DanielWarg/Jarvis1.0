"use client";

import { JarvisCore } from "../components/JarvisCore";
import { IntentQueue } from "../components/IntentQueue";
import { ToolStats } from "../components/ToolStats";
import { DiagnosticsPanel } from "../components/Diagnostics";
import { useUIStore } from "../store/uiStore";

export default function Page() {
  const items = useUIStore((s) => s.intentQueue);
  const tools = useUIStore((s) => s.toolLog);
  const diag = useUIStore((s) => s.diagnostics);

  return (
    <div className="grid grid-cols-3 gap-4 p-6">
      <div className="col-span-2 space-y-4">
        <JarvisCore />
        <IntentQueue items={items} />
      </div>
      <div className="space-y-4">
        <ToolStats items={tools} />
        <DiagnosticsPanel
          data={diag}
          onRunTests={async () => {
            await fetch(
              `${process.env.NEXT_PUBLIC_API_BASE ?? "http://127.0.0.1:8000"}/harmony/test`,
              {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ cases: [], use_tools: true }),
              }
            ).catch(() => {});
          }}
        />
      </div>
    </div>
  );
}