from __future__ import annotations

import io
import json
import sqlite3
from typing import Iterable


def stream_dataset(db_path: str) -> Iterable[bytes]:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # Events
    for row in cur.execute("SELECT ts, topic, payload FROM events ORDER BY ts ASC"):
        record = {
            "kind": "event",
            "ts": row["ts"],
            "topic": row["topic"],
            "payload": row["payload"],
        }
        yield (json.dumps(record, ensure_ascii=False) + "\n").encode("utf-8")

    # Memories
    for row in cur.execute("SELECT ts, kind, text, score, tags FROM memories ORDER BY ts ASC"):
        record = {
            "kind": "memory",
            "ts": row["ts"],
            "type": row["kind"],
            "text": row["text"],
            "score": row["score"],
            "tags": row["tags"],
        }
        yield (json.dumps(record, ensure_ascii=False) + "\n").encode("utf-8")

    # Lessons
    for row in cur.execute("SELECT ts, text, score, tags FROM lessons ORDER BY ts ASC"):
        record = {
            "kind": "lesson",
            "ts": row["ts"],
            "text": row["text"],
            "score": row["score"],
            "tags": row["tags"],
        }
        yield (json.dumps(record, ensure_ascii=False) + "\n").encode("utf-8")

    # Tool stats (single summary line)
    for row in cur.execute("SELECT tool, success, fail FROM tool_stats ORDER BY tool ASC"):
        record = {
            "kind": "tool_stats",
            "tool": row["tool"],
            "success": row["success"],
            "fail": row["fail"],
        }
        yield (json.dumps(record, ensure_ascii=False) + "\n").encode("utf-8")

    conn.close()


