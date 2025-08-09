from __future__ import annotations

import json
import os
import shutil
import subprocess
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import List, Optional


DATA_DIR = Path(os.getenv("DATA_DIR", "./data")).resolve()
CAMERAS_FILE = DATA_DIR / "cameras.json"


@dataclass
class Camera:
    id: str
    url: str
    name: Optional[str] = None


def _load_all() -> List[Camera]:
    if not CAMERAS_FILE.exists():
        return []
    try:
        raw = json.loads(CAMERAS_FILE.read_text())
        return [Camera(**c) for c in raw]
    except Exception:
        return []


def _save_all(cameras: List[Camera]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    CAMERAS_FILE.write_text(json.dumps([asdict(c) for c in cameras], ensure_ascii=False, indent=2))


def list_cameras() -> List[Camera]:
    return _load_all()


def get_camera(camera_id: str) -> Optional[Camera]:
    for c in _load_all():
        if c.id == camera_id:
            return c
    return None


def upsert_camera(cam: Camera) -> None:
    cams = _load_all()
    found = False
    for i, c in enumerate(cams):
        if c.id == cam.id:
            cams[i] = cam
            found = True
            break
    if not found:
        cams.append(cam)
    _save_all(cams)


def ffmpeg_available() -> bool:
    return shutil.which("ffmpeg") is not None


def capture_snapshot_jpeg(rtsp_url: str, timeout_sec: float = 4.0) -> Optional[bytes]:
    if not ffmpeg_available():
        return None
    try:
        # En enda frame till stdout som JPEG
        proc = subprocess.run(
            [
                "ffmpeg",
                "-rtsp_transport",
                "tcp",
                "-y",
                "-i",
                rtsp_url,
                "-frames:v",
                "1",
                "-q:v",
                "2",
                "-f",
                "image2",
                "-",
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            timeout=timeout_sec,
            check=False,
        )
        if proc.returncode == 0 and proc.stdout:
            return proc.stdout
        return None
    except Exception:
        return None


