"""Small pure helpers (kept free of widgets so they are easy to test)."""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

_INVALID_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


def sanitize_prefix(prefix: str) -> str:
    """Make a user supplied file name prefix safe for Windows file names."""
    cleaned = _INVALID_CHARS.sub("_", prefix or "").strip(" .")
    return cleaned


def build_output_path(folder: str | os.PathLike, prefix: str, ext: str,
                      now: datetime | None = None) -> Path:
    """Return a unique path like ``<folder>/<prefix>_20261015_143012.mp4``."""
    now = now or datetime.now()
    prefix = sanitize_prefix(prefix)
    stamp = now.strftime("%Y%m%d_%H%M%S")
    stem = f"{prefix}_{stamp}" if prefix else stamp
    ext = ext.lstrip(".")
    folder = Path(folder)
    candidate = folder / f"{stem}.{ext}"
    n = 2
    while candidate.exists():
        candidate = folder / f"{stem}_{n}.{ext}"
        n += 1
    return candidate


def format_duration(ms: int) -> str:
    """Format milliseconds as ``HH:MM:SS``."""
    total = max(0, int(ms) // 1000)
    h, rem = divmod(total, 3600)
    m, s = divmod(rem, 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


def format_bytes(n: int) -> str:
    size = float(max(0, n))
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if size < 1024 or unit == "TB":
            return f"{size:.0f} {unit}" if unit in ("B", "KB") else f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"


def free_space(folder: str | os.PathLike) -> int | None:
    """Free bytes on the drive holding ``folder`` (walks up to an existing parent)."""
    p = Path(folder)
    while not p.exists():
        if p.parent == p:
            return None
        p = p.parent
    try:
        return shutil.disk_usage(p).free
    except OSError:
        return None


def format_key(width: int, height: int, fps: float) -> str:
    return f"{width}x{height}@{fps:g}"


def open_in_explorer(path: str | os.PathLike, select: bool = False) -> None:
    """Open a folder (or reveal a file) in the system file manager."""
    path = str(path)
    if sys.platform == "win32":
        if select and os.path.isfile(path):
            subprocess.Popen(["explorer", "/select,", os.path.normpath(path)])
        else:
            os.startfile(os.path.normpath(path))  # type: ignore[attr-defined]
    elif sys.platform == "darwin":
        subprocess.Popen(["open", "-R", path] if select else ["open", path])
    else:
        target = os.path.dirname(path) if select and os.path.isfile(path) else path
        subprocess.Popen(["xdg-open", target])
