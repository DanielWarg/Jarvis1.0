import os
import json
from datetime import datetime
from typing import Any, Dict, List

import httpx


SERVER_URL = os.getenv("SERVER_URL", "http://127.0.0.1:8000")
ENDPOINT = f"{SERVER_URL}/harmony/test"
REPORT_DIR = os.getenv("HARMONY_REPORT_DIR", "tests/reports")
os.makedirs(REPORT_DIR, exist_ok=True)


def build_test_cases() -> List[Dict[str, Any]]:
    chat_cases = [
        {"id": "chat_1", "utterance": "Vad tycker du om den här låten?", "expect_tool": False},
        {"id": "chat_2", "utterance": "Kan du sammanfatta skillnaden mellan pausera och stoppa?", "expect_tool": False},
        {"id": "chat_3", "utterance": "Vad är klockan i Stockholm om tre timmar från nu, ungefär?", "expect_tool": False},
        {"id": "chat_4", "utterance": "Hur skulle du förklara barge-in för en nybörjare?", "expect_tool": False},
        {"id": "chat_5", "utterance": "Ge mig ett kort tips för att få bättre ljudkvalitet vid inspelning.", "expect_tool": False},
    ]
    tool_ok = [
        {"id": "tool_ok_1", "utterance": "Pausa musiken nu tack.", "expect_tool": True, "expect_tool_name": "PAUSE"},
        {"id": "tool_ok_2", "utterance": "Spela upp musiken igen.", "expect_tool": True, "expect_tool_name": "PLAY"},
        {"id": "tool_ok_3", "utterance": "Sätt volymen till 30 procent.", "expect_tool": True, "expect_tool_name": "SET_VOLUME"},
    ]
    tool_bad = [
        {"id": "tool_bad_1", "utterance": "Sätt volymen till högt.", "expect_tool": True, "expect_tool_name": "SET_VOLUME"},
        {"id": "tool_bad_2", "utterance": "Visa ett kort.", "expect_tool": True, "expect_tool_name": "DISPLAY"},
    ]
    unclear = [
        {"id": "unclear_1", "utterance": "Kan du fixa det där?", "expect_tool": False},
        {"id": "unclear_2", "utterance": "Gör det bara bra.", "expect_tool": False},
    ]
    return chat_cases + tool_ok + tool_bad + unclear


def run_batch(cases: List[Dict[str, Any]], use_tools: bool = True) -> Dict[str, Any]:
    payload = {
        "cases": [
            {
                "id": c["id"],
                "utterance": c["utterance"],
                "expect_tool": c.get("expect_tool", False),
                "expect_tool_name": c.get("expect_tool_name"),
                "allow_tools": c.get("allow_tools", True),
                "expect_no_leakage": c.get("expect_no_leakage", True),
                "notes": c.get("notes"),
            }
            for c in cases
        ],
        "use_tools": use_tools,
        "temperature_commands": float(os.getenv("HARMONY_TEMPERATURE_COMMANDS", "0.2")),
        "reasoning_level": os.getenv("HARMONY_REASONING_LEVEL", "low"),
        "max_tokens": int(os.getenv("HARMONY_MAX_TOKENS", "256")),
    }
    with httpx.Client(timeout=60.0) as client:
        r = client.post(ENDPOINT, json=payload)
        r.raise_for_status()
        return r.json()


def summarize(report: Dict[str, Any]) -> str:
    results = report["results"]
    passed = sum(1 for r in results if r["passed"])
    failed = len(results) - passed
    lines: List[str] = []
    lines.append(f"# Harmony E2E Rapport – {datetime.utcnow().isoformat()}Z")
    lines.append("")
    lines.append(
        f"Totalt: {len(results)}  |  Passed: {passed}  |  Failed: {failed}  |  Pass rate: {report['summary']['pass_rate']}%"
    )
    lines.append("")
    lines.append("| ID | Expect Tool | Tool Called | Tool Name | Passed | Latency (ms) | Reason |")
    lines.append("|----|-------------|-------------|-----------|--------|--------------|--------|")
    for r in results:
        lines.append(
            f"| {r['id']} | {r['expect_tool']} | {r['tool_called']} | {r.get('tool_name') or ''} | {r['passed']} | {int(r['latency_total_ms'])} | {r['reason']} |"
        )
    lines.append("")
    lines.append("## Misslyckade fall (om några)")
    for r in results:
        if not r["passed"]:
            lines.append(f"- {r['id']}: {r['utterance']}  →  {r['reason']}")
    return "\n".join(lines)


def main() -> None:
    cases = build_test_cases()
    report = run_batch(cases, use_tools=True)
    stamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    json_path = os.path.join(REPORT_DIR, f"harmony_report_{stamp}.json")
    md_path = os.path.join(REPORT_DIR, f"harmony_report_{stamp}.md")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(summarize(report))
    print(f"OK – rapport sparad:\nJSON: {json_path}\nMD:   {md_path}")


if __name__ == "__main__":
    main()


