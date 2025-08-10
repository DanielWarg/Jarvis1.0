from __future__ import annotations

import random
from typing import Dict, List, Optional

from .memory import MemoryStore


class EpsilonGreedyBandit:
    def __init__(self, memory: MemoryStore, epsilon: float = 0.1) -> None:
        self.memory = memory
        self.epsilon = epsilon

    def pick(self, candidates: List[str]) -> str:
        if not candidates:
            raise ValueError("No candidates")
        # Explore
        if random.random() < self.epsilon:
            return random.choice(candidates)
        # Exploit: pick highest success rate from tool_stats
        best_tool: Optional[str] = None
        best_rate: float = -1.0
        for tool in candidates:
            s, f = self.memory.get_tool_stats(tool)
            total = s + f
            rate = (s / total) if total > 0 else 0.0
            if rate > best_rate:
                best_rate = rate
                best_tool = tool
        return best_tool or random.choice(candidates)


def simulate_first(command: Dict) -> Dict[str, float]:
    # Minimal, placeholder risk/utility scorer; extend later with model-based scoring
    ctype = (command or {}).get("type", "").lower()
    # Low risk for HUD control; higher for actions that could be destructive
    if ctype in {"show_module", "hide_overlay", "open_video"}:
        return {"risk": 0.05, "utility": 0.6}
    return {"risk": 0.2, "utility": 0.5}


