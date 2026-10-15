"""Application entry point: theme, icon, language, main window."""

from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QIcon, QPalette
from PySide6.QtWidgets import QApplication

from wincam import __app_name__, __version__
from wincam.config import Config
from wincam.i18n import set_language

STYLE = """
QMainWindow, QDialog { background: #1e1f22; }
QWidget { color: #e8eaed; }
#topBar, #bottomBar { background: #26272b; }
#topBar { border-bottom: 1px solid #34363b; }
#bottomBar { border-top: 1px solid #34363b; }
QStatusBar { background: #1b1c1f; color: #9aa0a6; }
QStatusBar QLabel { color: #9aa0a6; padding: 0 8px; }
QStatusBar QLabel[warn="true"] { color: #f5a524; }
QStatusBar::item { border: none; }

QComboBox, QLineEdit, QSpinBox {
    background: #303136; border: 1px solid #3c3e44; border-radius: 6px;
    padding: 5px 8px; min-height: 20px; selection-background-color: #3b6fd8;
}
QComboBox:hover, QLineEdit:hover, QSpinBox:hover { border-color: #55585f; }
QComboBox:focus, QLineEdit:focus, QSpinBox:focus { border-color: #5b8def; }
QComboBox:disabled, QLineEdit:disabled, QSpinBox:disabled { color: #6b6f76; background: #2a2b2f; }
QComboBox::drop-down { border: none; width: 22px; }
QComboBox QAbstractItemView {
    background: #2b2c31; border: 1px solid #3c3e44; selection-background-color: #3b6fd8; outline: 0;
    padding: 4px;
}

QPushButton {
    background: #34363b; border: 1px solid #44474d; border-radius: 6px; padding: 6px 14px;
}
QPushButton:hover { background: #3d3f45; }
QPushButton:pressed { background: #2c2e32; }
QPushButton:default { background: #3b6fd8; border-color: #3b6fd8; }
QPushButton:default:hover { background: #4a7de6; }

QToolButton { border: none; border-radius: 6px; padding: 5px; }
QToolButton:hover { background: #393b40; }
QToolButton:pressed { background: #2c2e32; }
QToolButton#roundButton { background: #34363b; border-radius: 23px; }
QToolButton#roundButton:hover { background: #42444a; }
QToolButton#roundButton:disabled { background: #2a2b2f; }
QToolButton#folderButton { color: #c4c7cc; padding: 5px 8px; }
QToolButton#linkButton { color: #8ab4f8; padding: 5px 6px; }
QToolButton#linkButton:disabled { color: #6b6f76; }
QLabel#timeLabel {
    font-family: "Consolas", "Cascadia Mono", "DejaVu Sans Mono", monospace;
    font-size: 15pt; color: #9aa0a6; padding-right: 4px;
}
QLabel#timeLabel[recording="true"] { color: #ff6b6f; }
QLabel#hint { color: #8b9097; }

QTabWidget::pane { border: 1px solid #34363b; border-radius: 6px; top: -1px; background: #232428; }
QTabBar::tab {
    background: transparent; padding: 7px 16px; margin-right: 2px; color: #9aa0a6;
    border-top-left-radius: 6px; border-top-right-radius: 6px;
}
QTabBar::tab:selected { background: #232428; color: #e8eaed; border: 1px solid #34363b; border-bottom: none; }
QCheckBox { spacing: 8px; }
QSlider::groove:horizontal { height: 4px; background: #3c3e44; border-radius: 2px; }
QSlider::sub-page:horizontal { background: #5b8def; border-radius: 2px; }
QSlider::handle:horizontal { background: #e8eaed; width: 14px; margin: -6px 0; border-radius: 7px; }
QToolTip { background: #2b2c31; color: #e8eaed; border: 1px solid #44474d; padding: 4px 6px; }
QMessageBox QLabel { min-width: 280px; }
"""


def resource_path(name: str) -> Path:
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent))
    return base / "wincam" / "resources" / name


def _dark_palette() -> QPalette:
    pal = QPalette()
    roles = {
        QPalette.ColorRole.Window: "#1e1f22",
        QPalette.ColorRole.WindowText: "#e8eaed",
        QPalette.ColorRole.Base: "#303136",
        QPalette.ColorRole.AlternateBase: "#2a2b2f",
        QPalette.ColorRole.Text: "#e8eaed",
        QPalette.ColorRole.Button: "#34363b",
        QPalette.ColorRole.ButtonText: "#e8eaed",
        QPalette.ColorRole.Highlight: "#3b6fd8",
        QPalette.ColorRole.HighlightedText: "#ffffff",
        QPalette.ColorRole.ToolTipBase: "#2b2c31",
        QPalette.ColorRole.ToolTipText: "#e8eaed",
        QPalette.ColorRole.Link: "#8ab4f8",
        QPalette.ColorRole.PlaceholderText: "#7d8188",
    }
    for role, color in roles.items():
        pal.setColor(role, QColor(color))
    for role in (QPalette.ColorRole.Text, QPalette.ColorRole.ButtonText, QPalette.ColorRole.WindowText):
        pal.setColor(QPalette.ColorGroup.Disabled, role, QColor("#6b6f76"))
    return pal


def _set_windows_app_id() -> None:
    if sys.platform == "win32":
        try:
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(f"{__app_name__}.Recorder.{__version__}")
        except Exception:
            pass


def create_app(argv: list[str] | None = None) -> QApplication:
    _set_windows_app_id()
    QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    app = QApplication.instance() or QApplication(argv if argv is not None else sys.argv)
    app.setApplicationName(__app_name__)
    app.setApplicationVersion(__version__)
    app.setOrganizationName(__app_name__)
    app.setStyle("Fusion")
    app.setPalette(_dark_palette())
    if sys.platform == "win32":
        app.setFont(QFont("Microsoft YaHei UI", 9))
    app.setStyleSheet(STYLE)
    ico = resource_path("wincam.ico")
    png = resource_path("wincam.png")
    if ico.exists() or png.exists():
        app.setWindowIcon(QIcon(str(ico if ico.exists() else png)))
    return app


def selftest(out_path: str) -> int:
    """Write a JSON report about the multimedia backend (used by CI on the frozen exe)."""
    import json

    from PySide6.QtMultimedia import QMediaDevices, QMediaFormat

    from wincam import capture

    containers = capture.supported_containers()
    report = {
        "version": __version__,
        "containers": [c.name for c in containers],
        "video_codecs": {c.name: [v.name for v in capture.supported_video_codecs(c)] for c in containers},
        "audio_codecs": {c.name: [a.name for a in capture.supported_audio_codecs(c)] for c in containers},
        "cameras": [d.description() for d in QMediaDevices.videoInputs()],
        "microphones": [d.description() for d in QMediaDevices.audioInputs()],
    }
    report["ok"] = QMediaFormat.FileFormat.MPEG4 in containers
    Path(out_path).write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    return 0 if report["ok"] else 1


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv if argv is None else argv)
    app = create_app(argv)
    if "--selftest" in argv:
        i = argv.index("--selftest")
        return selftest(argv[i + 1] if i + 1 < len(argv) else "wincam-selftest.json")
    config = Config()
    set_language(config.get("app/language"))

    from wincam.main_window import MainWindow  # import after the language is set

    win = MainWindow(config)
    win.show()
    return app.exec()
