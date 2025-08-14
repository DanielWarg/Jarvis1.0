"use client";
import { Card } from "../components/ui/card";
import { Badge } from "../components/ui/badge";
import { RouteIcon } from "./RouteIcon";

export function IntentQueue({ items }) {
  return (
    <Card className="p-3 space-y-2 bg-background/40 backdrop-blur">
      <div className="text-sm font-semibold opacity-80">INTENT QUEUE</div>
      <div className="space-y-2 max-h-64 overflow-auto pr-1">
        {items.map((it) => (
          <div key={it.id} className="grid grid-cols-[16px,1fr,auto] items-center gap-2">
            <RouteIcon source={it.route} />
            <div className="truncate">
              <div className="text-sm truncate">{it.userText}</div>
              {it.tool?.name && (
                <div className="text-xs opacity-60">
                  tool: <span className="opacity-90">{it.tool.name}</span>
                </div>
              )}
            </div>
            <div className="flex items-center gap-2">
              {typeof it.totalLatencyMs === "number" && (
                <Badge variant="outline">{Math.round(it.totalLatencyMs)} ms</Badge>
              )}
              <Badge
                className="capitalize"
                variant={it.status === "ok" ? "secondary" : it.status === "error" ? "destructive" : "outline"}
              >
                {it.status ?? "pending"}
              </Badge>
            </div>
          </div>
        ))}
      </div>
    </Card>
  );
}