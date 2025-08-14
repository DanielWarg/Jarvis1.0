from __future__ import annotations

import time
from typing import Any, Dict, List


def _percentile(values: List[float], p: float) -> float:
    if not values:
        return 0.0
    arr = sorted(values)
    k = max(0, min(len(arr) - 1, int(round((p / 100.0) * (len(arr) - 1)))))
    return float(arr[k])


class Metrics:
    def __init__(self) -> None:
        self.reset()

    def reset(self) -> None:
        self.first_token_ms: List[float] = []
        self.final_latency_ms: List[float] = []
        self.tool_call_latency_ms: List[float] = []
        self.tool_calls_attempted: int = 0
        self.tool_validation_failed: int = 0
        self.router_hits: int = 0
        self.llm_hits: int = 0

    def _cap(self, arr: List[float], value: float, cap: int = 500) -> None:
        arr.append(float(value))
        if len(arr) > cap:
            del arr[: len(arr) - cap]

    def record_first_token(self, ms: float) -> None:
        self._cap(self.first_token_ms, ms)

    def record_final_latency(self, ms: float) -> None:
        self._cap(self.final_latency_ms, ms)

    def record_tool_call_attempted(self) -> None:
        self.tool_calls_attempted += 1

    def record_tool_validation_failed(self) -> None:
        self.tool_validation_failed += 1

    def record_tool_call_latency(self, ms: float) -> None:
        self._cap(self.tool_call_latency_ms, ms)

    def record_router_hit(self) -> None:
        self.router_hits += 1

    def record_llm_hit(self) -> None:
        self.llm_hits += 1

    def snapshot(self) -> Dict[str, Any]:
        return {
            "first_token_ms": {
                "count": len(self.first_token_ms),
                "p50": _percentile(self.first_token_ms, 50),
                "p95": _percentile(self.first_token_ms, 95),
            },
            "final_latency_ms": {
                "count": len(self.final_latency_ms),
                "p50": _percentile(self.final_latency_ms, 50),
                "p95": _percentile(self.final_latency_ms, 95),
            },
            "tool_call_latency_ms": {
                "count": len(self.tool_call_latency_ms),
                "p50": _percentile(self.tool_call_latency_ms, 50),
                "p95": _percentile(self.tool_call_latency_ms, 95),
            },
            "counters": {
                "tool_calls_attempted": self.tool_calls_attempted,
                "tool_validation_failed": self.tool_validation_failed,
                "router_hits": self.router_hits,
                "llm_hits": self.llm_hits,
            },
        }


metrics = Metrics()


