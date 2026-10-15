"""Persistent settings (stored in the Windows registry, or wincam.ini for portable use)."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from PySide6.QtCore import QLocale, QSettings, QStandardPaths

from wincam import __app_name__


def _app_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def default_save_dir() -> str:
    movies = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.MoviesLocation)
    if not movies:
        movies = str(Path.home() / "Videos")
    return str(Path(movies) / __app_name__)


def default_language() -> str:
    return "zh" if QLocale.system().language() == QLocale.Language.Chinese else "en"


DEFAULTS: dict[str, object] = {
    "app/save_dir": None,  # computed lazily -> default_save_dir()
    "app/file_prefix": __app_name__,
    "app/language": None,  # computed lazily -> default_language()
    "app/countdown": 0,
    "app/max_minutes": 0,
    "app/open_folder_after": False,
    "app/always_on_top": False,
    "video/camera_id": "",
    "video/format": "",
    "video/container": "MPEG4",
    "video/codec": "Unspecified",
    "video/quality": "HighQuality",
    "video/bitrate_kbps": 0,
    "video/mirror_preview": True,
    "audio/device_id": "",
    "audio/codec": "Unspecified",
    "audio/volume": 100,
    "snapshot/format": "jpg",
}


class Config:
    """Thin typed wrapper around QSettings with defaults."""

    def __init__(self, settings: QSettings | None = None):
        if settings is None:
            ini = _app_dir() / "wincam.ini"
            if ini.exists() or os.environ.get("WINCAM_PORTABLE"):
                settings = QSettings(str(ini), QSettings.Format.IniFormat)
            else:
                settings = QSettings(__app_name__, __app_name__)
        self._s = settings

    def _default(self, key: str):
        if key == "app/save_dir":
            return default_save_dir()
        if key == "app/language":
            return default_language()
        return DEFAULTS[key]

    def get(self, key: str):
        default = self._default(key)
        value = self._s.value(key, default)
        if value is None:
            return default
        # QSettings (esp. INI) may hand back strings; coerce to the default's type.
        if isinstance(default, bool):
            if isinstance(value, str):
                return value.strip().lower() in ("1", "true", "yes", "on")
            return bool(value)
        if isinstance(default, int):
            try:
                return int(value)
            except (TypeError, ValueError):
                return default
        return str(value)

    def set(self, key: str, value) -> None:
        self._s.setValue(key, value)

    def sync(self) -> None:
        self._s.sync()

    def raw(self) -> QSettings:
        return self._s
