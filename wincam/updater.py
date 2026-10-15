"""Update check against the project's GitHub Releases (public API, no account needed)."""

from __future__ import annotations

import json
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import QObject, QUrl, Signal
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkProxyFactory, QNetworkReply, QNetworkRequest

from wincam import __app_name__, __version__

REPO = "nanguoyu/WinCam"
RELEASES_PAGE = f"https://github.com/{REPO}/releases/latest"
LATEST_API = f"https://api.github.com/repos/{REPO}/releases/latest"


def parse_version(text: str) -> tuple[int, ...]:
    """'v1.2.0' -> (1, 2, 0). Non-numeric suffixes ('-beta') are ignored."""
    nums = re.findall(r"\d+", (text or "").strip().lstrip("vV").split("-")[0])
    return tuple(int(n) for n in nums[:4]) or (0,)


def is_newer(latest: str, current: str | None = None) -> bool:
    a, b = parse_version(latest), parse_version(current if current is not None else __version__)
    width = max(len(a), len(b))
    return a + (0,) * (width - len(a)) > b + (0,) * (width - len(b))


def is_installed_copy() -> bool:
    """True when running from the Inno Setup install (it puts an uninstaller next to the exe)."""
    if not getattr(sys, "frozen", False):
        return False
    return any(Path(sys.executable).resolve().parent.glob("unins*.exe"))


@dataclass
class ReleaseInfo:
    version: str
    page_url: str
    download_url: str
    notes: str


def release_from_json(data: dict, installed: bool) -> ReleaseInfo:
    tag = str(data.get("tag_name") or "")
    page = str(data.get("html_url") or RELEASES_PAGE)
    want = "-Setup.exe" if installed else "-portable.zip"
    download = page
    for asset in data.get("assets") or []:
        name = str(asset.get("name") or "")
        if name.endswith(want):
            download = str(asset.get("browser_download_url") or page)
            break
    notes = str(data.get("body") or "").strip()
    return ReleaseInfo(version=tag.lstrip("vV"), page_url=page, download_url=download, notes=notes)


class UpdateChecker(QObject):
    """Asynchronous check. Emits exactly one of updateAvailable / upToDate / failed per check()."""

    updateAvailable = Signal(object)  # ReleaseInfo
    upToDate = Signal(str)            # latest version
    failed = Signal(str)              # error text

    def __init__(self, parent=None, url: str | None = None):
        super().__init__(parent)
        # Respect the Windows / corporate proxy settings.
        QNetworkProxyFactory.setUseSystemConfiguration(True)
        self._nam = QNetworkAccessManager(self)
        self._url = url or os.environ.get("WINCAM_UPDATE_URL") or LATEST_API
        self._reply: QNetworkReply | None = None

    def is_running(self) -> bool:
        return self._reply is not None

    def check(self) -> None:
        if self._reply is not None:
            return
        req = QNetworkRequest(QUrl(self._url))
        req.setRawHeader(b"Accept", b"application/vnd.github+json")
        req.setRawHeader(b"User-Agent", f"{__app_name__}/{__version__}".encode())
        req.setTransferTimeout(15000)
        self._reply = self._nam.get(req)
        self._reply.finished.connect(self._on_finished)

    def _on_finished(self) -> None:
        reply, self._reply = self._reply, None
        if reply is None:
            return
        try:
            if reply.error() != QNetworkReply.NetworkError.NoError:
                self.failed.emit(reply.errorString())
                return
            data = json.loads(bytes(reply.readAll().data()).decode("utf-8"))
            info = release_from_json(data, is_installed_copy())
            if not info.version:
                self.failed.emit("no release found")
            elif is_newer(info.version):
                self.updateAvailable.emit(info)
            else:
                self.upToDate.emit(info.version)
        except (ValueError, TypeError, AttributeError) as e:
            self.failed.emit(f"bad response: {e}")
        finally:
            reply.deleteLater()
