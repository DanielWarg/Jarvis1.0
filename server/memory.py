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


