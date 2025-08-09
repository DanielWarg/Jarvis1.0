from __future__ import annotations

import os
from pathlib import Path
from typing import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Connection, Engine


def ensure_data_dir() -> Path:
    data_dir = Path(os.getenv("DATA_DIR", "./data")).resolve()
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir


def create_sqlite_engine() -> Engine:
    data_dir = ensure_data_dir()
    db_url = f"sqlite:///{data_dir}/core.db"
    engine = create_engine(db_url, connect_args={"check_same_thread": False})
    return engine


engine: Engine = create_sqlite_engine()


def ping_database() -> bool:
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


def get_connection() -> Generator[Connection, None, None]:
    with engine.connect() as conn:
        yield conn


