"use client";
import { Card } from "../components/ui/card";
import { Button } from "../components/ui/button";

export function DiagnosticsPanel({ data, onRunTests }) {
  return (
    <Card className="p-3 space-y-3 bg-background/40 backdrop-blur">
      <div className="text-sm font-semibold opacity-80">DIAGNOSTICS</div>
      <div className="grid grid-cols-3 gap-2 text-center">
        <div><div className="text-xl">{Math.round(data.p50Final)} ms</div><div className="text-xs opacity-60">p50 final</div></div>
        <div><div className="text-xl">{Math.round(data.p95Final)} ms</div><div className="text-xs opacity-60">p95 final</div></div>
        <div><div className="text-xl">{data.routerHitRate.toFixed(0)}%</div><div className="text-xs opacity-60">router hit-rate</div></div>
      </div>
      <Button size="sm" onClick={onRunTests}>Run tests</Button>
    </Card>
  );
}