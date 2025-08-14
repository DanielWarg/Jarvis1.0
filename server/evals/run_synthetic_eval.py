from __future__ import annotations

import json
import time
from typing import Any, Dict, List

import httpx


def eval_once(item: Dict[str, Any]) -> Dict[str, Any]:
    text = item["text"]
    kind = item["kind"]
    t0 = time.time()
    with httpx.Client(timeout=10.0) as client:
        # Först försök router-först via API (återanvänder serverns logik)
        r = client.post("http://127.0.0.1:8000/api/chat", json={"prompt": text, "provider": "auto"})
    dt = (time.time() - t0) * 1000
    try:
        j = r.json()
    except Exception:
        j = {"ok": False}
    return {"latency_ms": dt, "resp": j, "kind": kind, "text": text}


def main() -> None:
    items: List[Dict[str, Any]] = []
    with open("server/evals/synthetic.jsonl", "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                items.append(json.loads(line))
            except Exception:
                continue
    results = [eval_once(it) for it in items]
    # Summera baserat på förväntningar
    total = len(results)
    tool_ok = 0
    chat_ok = 0
    missing_ok = 0
    for it, r in zip(items, results):
        resp = r.get("resp") or {}
        txt = (resp.get("text") or "").lower()
        if it["kind"] == "tool_required":
            # heuristik: kolla om router-svar eller kort bekräftelse finns
            if resp.get("provider") in {"router"} or any(k in txt for k in ["pausar", "spelar upp", "volym"]):
                tool_ok += 1
        elif it["kind"] == "chat_only":
            # inga verktyg → bara text ok
            if resp.get("provider") in {"openai", "local"} or (resp.get("ok") and resp.get("text")):
                chat_ok += 1
        elif it["kind"] == "missing_params":
            # ska vägra eller be om klargörande (text finns, men inga router-verktyg)
            if resp.get("provider") in {"openai", "local"} or (resp.get("ok") and resp.get("text")):
                missing_ok += 1
    print(json.dumps({
        "n": total,
        "tool_hit_rate": tool_ok / max(1, len([x for x in items if x["kind"] == "tool_required"])),
        "chat_only_rate": chat_ok / max(1, len([x for x in items if x["kind"] == "chat_only"])),
        "missing_params_ok_rate": missing_ok / max(1, len([x for x in items if x["kind"] == "missing_params"])),
        "avg_latency_ms": sum(r["latency_ms"] for r in results) / max(1, total)
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()


