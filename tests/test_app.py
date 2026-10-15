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
    assert config.get("app/reveal_after_recording") is True
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


def test_preset_format_picks_matching_height_at_30fps():
    choices = [choice(1920, 1080, 30), choice(1280, 720, 30), choice(640, 480, 30), choice(640, 480, 15),
               choice(848, 480, 30), choice(320, 240, 30)]
    best = capture.preset_format(choices, 480)
    assert (best.width, best.height, best.fps) == (848, 480, 30)
    assert capture.preset_format(choices, 720).height == 720


def test_preset_format_falls_back_to_nearest():
    choices = [choice(1280, 720, 30), choice(640, 360, 30)]
    assert capture.preset_format(choices, 480).height == 360  # 120 px away beats 240 px away
    assert capture.preset_format([], 480) is None


def test_new_defaults(config):
    assert config.get("video/preset") == "480p"
    assert capture.DEFAULT_PRESET == "480p"
    assert config.get("app/reveal_after_recording") is True
    assert config.get("app/tray_notifications") is True


def test_settings_custom_preset_unlocks_details(config):
    from wincam.settings_dialog import SettingsDialog

    formats = [choice(1280, 720, 30), choice(640, 480, 30)]
    dlg = SettingsDialog(config, formats=formats)
    assert not dlg.custom_format.isEnabled()  # 480p preset by default
    assert "640×480" in dlg.preset_info.text() and "1.5 Mbps" in dlg.preset_info.text()
    dlg.preset.setCurrentIndex(dlg.preset.findData("custom"))
    assert dlg.custom_format.isEnabled() and dlg.bitrate.isEnabled()
    dlg.custom_format.setCurrentIndex(dlg.custom_format.findData("1280x720@30"))
    dlg.bitrate.setCurrentIndex(dlg.bitrate.findData(4000))
    dlg.apply()
    assert config.get("video/preset") == "custom"
    assert config.get("video/format") == "1280x720@30"
    assert config.get("video/bitrate_kbps") == 4000
    shiboken6.delete(dlg)


def test_main_window_uses_preset_bitrate(config, tmp_path, qapp):
    from wincam.main_window import MainWindow

    config.set("app/save_dir", str(tmp_path))
    win = MainWindow(config)
    assert win._record_options().bitrate_kbps == 1500
    win.preset_combo.setCurrentIndex(win.preset_combo.findData("1080p"))
    assert config.get("video/preset") == "1080p"
    assert win._record_options().bitrate_kbps == 8000
    win.close()
    shiboken6.delete(win)
