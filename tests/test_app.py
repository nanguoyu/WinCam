import shiboken6
from PySide6.QtMultimedia import QCameraFormat, QMediaFormat

from wincam import capture
from wincam.config import default_save_dir


def choice(w, h, fps):
    return capture.FormatChoice(f"{w}x{h}@{fps:g}", w, h, fps, QCameraFormat())


def test_auto_format_prefers_smooth_1080p():
    choices = [choice(3840, 2160, 30), choice(1920, 1080, 30), choice(1920, 1080, 5), choice(1280, 720, 60)]
    best = capture.auto_format(choices)
    assert (best.width, best.height, best.fps) == (1920, 1080, 30)


def test_auto_format_falls_back_when_nothing_smooth():
    choices = [choice(1920, 1080, 5), choice(640, 480, 15)]
    assert capture.auto_format(choices).width == 640
    assert capture.auto_format([]) is None


def test_container_suffix(qapp):
    assert capture.container_suffix(QMediaFormat.FileFormat.MPEG4) == "mp4"
    assert capture.container_suffix(QMediaFormat.FileFormat.Matroska) == "mkv"


def test_enum_by_name():
    assert capture.enum_by_name(QMediaFormat.FileFormat, "Matroska", None) == QMediaFormat.FileFormat.Matroska
    assert capture.enum_by_name(QMediaFormat.FileFormat, "nope", 1) == 1


def test_config_defaults_and_types(config):
    assert config.get("app/save_dir") == default_save_dir()
    assert config.get("app/countdown") == 0
    config.set("app/countdown", "5")
    config.set("video/mirror_preview", "false")
    assert config.get("app/countdown") == 5
    assert config.get("video/mirror_preview") is False


def test_settings_dialog_roundtrip(config, tmp_path):
    from wincam.settings_dialog import SettingsDialog

    dlg = SettingsDialog(config)
    dlg.save_dir.setText(str(tmp_path))
    dlg.prefix.setText("Lesson")
    dlg.countdown.setCurrentIndex(dlg.countdown.findData(3))
    dlg.mirror.setChecked(False)
    dlg.apply()
    assert config.get("app/save_dir") == str(tmp_path)
    assert config.get("app/file_prefix") == "Lesson"
    assert config.get("app/countdown") == 3
    assert config.get("video/mirror_preview") is False
    assert "Lesson_" in dlg.example.text()
    shiboken6.delete(dlg)  # parentless widget: destroy before QApplication goes away


def test_main_window_starts_without_camera(config, tmp_path, qapp):
    from wincam.main_window import MainWindow

    config.set("app/save_dir", str(tmp_path / "out"))
    win = MainWindow(config)
    win.show()
    qapp.processEvents()
    assert not win.controller.is_recording()
    # With no camera the record button is disabled; clicking it must be a harmless no-op.
    win._on_record_clicked()
    assert not win.controller.is_recording()
    assert win.mic_combo.count() >= 1
    win.close()
    shiboken6.delete(win)
