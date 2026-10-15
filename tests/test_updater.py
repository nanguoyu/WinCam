import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest
import shiboken6
from PySide6.QtCore import QEventLoop, QTimer

from wincam import __version__
from wincam.updater import ReleaseInfo, UpdateChecker, is_newer, parse_version, release_from_json

RELEASE = {
    "tag_name": "v9.9.0",
    "html_url": "https://github.com/nanguoyu/WinCam/releases/tag/v9.9.0",
    "body": "Bug fixes",
    "assets": [
        {"name": "WinCam-9.9.0-portable.zip", "browser_download_url": "https://example.invalid/portable.zip"},
        {"name": "WinCam-9.9.0-Setup.exe", "browser_download_url": "https://example.invalid/Setup.exe"},
    ],
}


def test_parse_and_compare_versions():
    assert parse_version("v1.2.3") == (1, 2, 3)
    assert parse_version("1.10.0-beta") == (1, 10, 0)
    assert is_newer("1.10.0", "1.9.9")
    assert is_newer("v1.1.1", "1.1.0")
    assert is_newer("1.2", "1.1.9")
    assert not is_newer("1.1.0", "1.1.0")
    assert not is_newer("1.1", "1.1.0")
    assert not is_newer("1.0.9", "1.1.0")


def test_release_picks_installer_or_portable():
    assert release_from_json(RELEASE, installed=True).download_url.endswith("Setup.exe")
    info = release_from_json(RELEASE, installed=False)
    assert info.download_url.endswith("portable.zip")
    assert info.version == "9.9.0" and info.notes == "Bug fixes"
    # No matching asset -> fall back to the release page.
    assert release_from_json({"tag_name": "v2.0.0", "html_url": "https://x/rel"}, True).download_url == "https://x/rel"


class _Handler(BaseHTTPRequestHandler):
    payload: bytes = b""
    status = 200

    def do_GET(self):  # noqa: N802
        self.send_response(self.status)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(self.payload)

    def log_message(self, *args):
        pass


@pytest.fixture
def fake_github():
    server = HTTPServer(("127.0.0.1", 0), _Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield server
    server.shutdown()


def _run_check(qapp, server, payload: dict | None, status: int = 200):
    _Handler.payload = json.dumps(payload or {}).encode()
    _Handler.status = status
    checker = UpdateChecker(url=f"http://127.0.0.1:{server.server_port}/latest")
    result = {}
    loop = QEventLoop()
    checker.updateAvailable.connect(lambda info: (result.update(kind="update", info=info), loop.quit()))
    checker.upToDate.connect(lambda v: (result.update(kind="latest", version=v), loop.quit()))
    checker.failed.connect(lambda e: (result.update(kind="failed", error=e), loop.quit()))
    QTimer.singleShot(10000, loop.quit)
    checker.check()
    loop.exec()
    shiboken6.delete(checker)
    return result


def test_checker_reports_new_version(qapp, fake_github):
    res = _run_check(qapp, fake_github, RELEASE)
    assert res["kind"] == "update" and res["info"].version == "9.9.0"


def test_checker_reports_up_to_date(qapp, fake_github):
    res = _run_check(qapp, fake_github, {**RELEASE, "tag_name": f"v{__version__}"})
    assert res == {"kind": "latest", "version": __version__}


def test_checker_reports_failure(qapp, fake_github):
    assert _run_check(qapp, fake_github, {"message": "Not Found"}, status=404)["kind"] == "failed"


def test_main_window_update_prompt_and_skip(config, tmp_path, qapp):
    from wincam.main_window import MainWindow

    config.set("app/save_dir", str(tmp_path))
    win = MainWindow(config)
    info = ReleaseInfo("9.9.0", "https://x/page", "https://x/Setup.exe", "")
    win.updater.updateAvailable.emit(info)
    assert win.toast is not None and win.toast.isVisible() and win.toast.kind == "update"
    win._skip_update(info)
    win.toast.hide()
    assert config.get("update/skipped") == "9.9.0"
    win.updater.updateAvailable.emit(info)  # skipped version -> no prompt
    assert not win.toast.isVisible()
    win.close()
    shiboken6.delete(win)
