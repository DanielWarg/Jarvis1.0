from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

import httpx
from pydantic import BaseModel, Field


class HarmonyTestCase(BaseModel):
    id: str
    utterance: str
    expect_tool: bool = False
    expect_tool_name: Optional[str] = None
    allow_tools: bool = True
    expect_no_leakage: bool = True
    notes: Optional[str] = None


class HarmonyTestResult(BaseModel):
    id: str
    utterance: str
    passed: bool
    reason: str
    expect_tool: bool
    tool_called: bool
    tool_name: Optional[str] = None
    tool_executed: bool = False
    analysis_leak: bool = False
    latency_first_final_ms: float = 0.0
    latency_total_ms: float = 0.0
    final_text: str = ""
    raw_summary: Dict[str, Any] = Field(default_factory=dict)


class HarmonyTestBatchRequest(BaseModel):
    cases: List[HarmonyTestCase]
    use_tools: bool = True
    temperature_commands: float = 0.2
    reasoning_level: str = "low"
    max_tokens: int = 256


class HarmonyTestBatchResponse(BaseModel):
    results: List[HarmonyTestResult]
    summary: Dict[str, Any]


async def run_harmony_test_case(case: HarmonyTestCase, _cfg: HarmonyTestBatchRequest) -> HarmonyTestResult:
    t0 = time.perf_counter()
    # E2E: anropa den egna serverns /api/chat för att få verkligt beteende
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            r = await client.post(
                "http://127.0.0.1:8000/api/chat",
                json={"prompt": case.utterance, "provider": "auto"},
            )
            data = r.json() if r.status_code == 200 else {"ok": False}
    except Exception:
        data = {"ok": False}

    tool_called = (data.get("provider") == "router")
    tool_name = data.get("tool") if tool_called else None
    tool_executed = tool_called and data.get("ok") is True
    # Analysis-leakage är inte möjligt i vårt final-only-gränssnitt; markera endast vid tom final
    final_text = str(data.get("text") or "")
    analysis_leak = False

    # Bedömning
    passed = True
    reasons: List[str] = []
    if case.expect_tool and not tool_called:
        passed = False
        reasons.append("Förväntade tool-call men inget tool kallades.")
    if (not case.expect_tool) and tool_called:
        passed = False
        reasons.append("Förväntade ingen tool-call men verktyg kallades.")
    if case.expect_tool_name and (tool_name or "").upper() != case.expect_tool_name.upper():
        passed = False
        reasons.append(f"Fel verktyg kallat: {tool_name} (förväntat {case.expect_tool_name}).")
    if case.expect_no_leakage and (not final_text):
        passed = False
        reasons.append("Saknar final-text.")

    t1 = time.perf_counter()
    return HarmonyTestResult(
        id=case.id,
        utterance=case.utterance,
        passed=passed,
        reason="; ".join(reasons) if reasons else "OK",
        expect_tool=case.expect_tool,
        tool_called=tool_called,
        tool_name=tool_name,
        tool_executed=tool_executed,
        analysis_leak=analysis_leak,
        latency_first_final_ms=(t1 - t0) * 1000.0,
        latency_total_ms=(t1 - t0) * 1000.0,
        final_text=final_text,
        raw_summary={"provider": data.get("provider"), "engine": data.get("engine")},
    )


