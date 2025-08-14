"use client";
import { Card } from "../components/ui/card";
import { Badge } from "../components/ui/badge";
import { Tooltip, TooltipTrigger, TooltipContent } from "../components/ui/tooltip";

export function ToolStats({ items }) {
  return (
    <Card className="p-3 space-y-3 bg-background/40 backdrop-blur">
      <div className="text-sm font-semibold opacity-80">TOOL STATS</div>
      <div className="space-y-2 max-h-56 overflow-auto pr-1">
        {items.map((t, idx) => (
          <div key={t.t + "" + idx} className="flex items-center justify-between gap-2">
            <div className="truncate">
              <Tooltip>
                <TooltipTrigger asChild>
                  <div className="text-sm truncate">{t.name}</div>
                </TooltipTrigger>
                <TooltipContent>
                  <pre className="text-xs max-w-[260px] whitespace-pre-wrap">
                    {JSON.stringify(t.args, null, 2)}
                  </pre>
                </TooltipContent>
              </Tooltip>
              <div className="text-xs opacity-60">source: {t.source}</div>
            </div>
            <div className="flex items-center gap-2">
              <Badge variant={t.executed ? "secondary" : "destructive"}>
                {t.executed ? "ok" : "error"}
              </Badge>
              <Badge variant="outline">{Math.round(t.latencyMs)} ms</Badge>
            </div>
          </div>
        ))}
      </div>
    </Card>
  );
}