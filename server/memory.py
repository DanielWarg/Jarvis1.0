from __future__ import annotations

import sqlite3
import os
from datetime import datetime
from typing import Optional


class MemoryStore:
    def __init__(self, db_path: str) -> None:
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.db_path = db_path
        self._init()

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        return conn

    def _init(self) -> None:
        with self._conn() as c:
            c.execute(
                """
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ts TEXT NOT NULL,
                    topic TEXT NOT NULL,
                    payload TEXT
                )
                """
            )
            c.execute("CREATE INDEX IF NOT EXISTS idx_events_topic_ts ON events(topic, ts)")
            c.execute(
                """
                CREATE TABLE IF NOT EXISTS memories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ts TEXT NOT NULL,
                    kind TEXT NOT NULL,         -- 'text' | 'image' (future)
                    text TEXT,                  -- for kind='text'
                    score REAL DEFAULT 0.0,
                    tags TEXT                   -- JSON string of tags/metadata
                )
                """
            )
            c.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_memories_text ON memories(text)
                """
            )
            c.execute(
                """
                CREATE TABLE IF NOT EXISTS lessons (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ts TEXT NOT NULL,
                    text TEXT NOT NULL,
                    score REAL DEFAULT 0.0,
                    tags TEXT
                )
                """
            )
            c.execute(
                """
                CREATE TABLE IF NOT EXISTS tool_stats (
                    tool TEXT PRIMARY KEY,
                    success INTEGER DEFAULT 0,
                    fail INTEGER DEFAULT 0
                )
                """
            )
            c.execute(
                """
                CREATE TABLE IF NOT EXISTS cv_frames (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ts TEXT NOT NULL,
                    source TEXT,
                    meta TEXT                -- JSON (objects, notes)
                )
                """
            )
            c.execute(
                """
                CREATE TABLE IF NOT EXISTS sensor_timeseries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ts TEXT NOT NULL,
                    sensor TEXT NOT NULL,
                    value REAL,
                    meta TEXT                -- JSON
                )
                """
            )
            c.execute("CREATE INDEX IF NOT EXISTS idx_sensor_ts ON sensor_timeseries(sensor, ts)")

    def ping(self) -> bool:
        try:
            with self._conn() as c:
                c.execute("SELECT 1")
            return True
        except Exception:
            return False

    def append_event(self, topic: str, payload: Optional[str]) -> None:
        ts = datetime.utcnow().isoformat() + "Z"
        with self._conn() as c:
            c.execute(
                "INSERT INTO events (ts, topic, payload) VALUES (?, ?, ?)",
                (ts, topic, payload),
            )

    # --- Memories (text) ---
    def upsert_text_memory(self, text: str, score: float = 0.0, tags_json: Optional[str] = None) -> int:
        ts = datetime.utcnow().isoformat() + "Z"
        with self._conn() as c:
            cur = c.execute(
                "INSERT INTO memories (ts, kind, text, score, tags) VALUES (?, 'text', ?, ?, ?)",
                (ts, text, score, tags_json),
            )
            return int(cur.lastrowid)

    def retrieve_text_memories(self, query: str, limit: int = 5):
        # Simple LIKE-based retrieval as a baseline; embeddings can replace this later
        like = f"%{query}%"
        with self._conn() as c:
            cur = c.execute(
                """
                SELECT id, ts, kind, text, score, tags
                FROM memories
                WHERE kind='text' AND (text LIKE ?)
                ORDER BY score DESC, ts DESC
                LIMIT ?
                """,
                (like, limit),
            )
            rows = cur.fetchall()
            cols = [d[0] for d in cur.description]
            return [dict(zip(cols, r)) for r in rows]

    def update_memory_score(self, mem_id: int, delta: float) -> None:
        with self._conn() as c:
            c.execute("UPDATE memories SET score = COALESCE(score,0) + ? WHERE id = ?", (delta, mem_id))

    def update_tool_stats(self, tool: str, success: bool) -> None:
        with self._conn() as c:
            # Upsert-like behavior for SQLite
            c.execute("INSERT OR IGNORE INTO tool_stats(tool, success, fail) VALUES (?, 0, 0)", (tool,))
            if success:
                c.execute("UPDATE tool_stats SET success = success + 1 WHERE tool = ?", (tool,))
            else:
                c.execute("UPDATE tool_stats SET fail = fail + 1 WHERE tool = ?", (tool,))

    def get_tool_stats(self, tool: str):
        with self._conn() as c:
            cur = c.execute("SELECT success, fail FROM tool_stats WHERE tool = ?", (tool,))
            row = cur.fetchone()
            if not row:
                return 0, 0
            return int(row[0] or 0), int(row[1] or 0)

    # --- Perception/Sensors ---
    def add_cv_frame(self, source: str, meta_json: str) -> int:
        ts = datetime.utcnow().isoformat() + "Z"
        with self._conn() as c:
            cur = c.execute(
                "INSERT INTO cv_frames (ts, source, meta) VALUES (?, ?, ?)",
                (ts, source, meta_json),
            )
            return int(cur.lastrowid)

    def add_sensor_telemetry(self, sensor: str, value: float, meta_json: str = None) -> int:
        ts = datetime.utcnow().isoformat() + "Z"
        with self._conn() as c:
            cur = c.execute(
                "INSERT INTO sensor_timeseries (ts, sensor, value, meta) VALUES (?, ?, ?, ?)",
                (ts, sensor, value, meta_json),
            )
            return int(cur.lastrowid)


