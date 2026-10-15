"""The settings dialog (general / video / audio)."""

from __future__ import annotations

from datetime import datetime

from PySide6.QtCore import Qt
from PySide6.QtMultimedia import QMediaFormat, QMediaRecorder
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSlider,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from wincam import capture
from wincam.config import DEFAULTS, Config, default_save_dir
from wincam.i18n import LANGUAGES, tr
from wincam.utils import build_output_path, format_bitrate

QUALITIES = ["LowQuality", "NormalQuality", "HighQuality"]
COUNTDOWN_PRESETS = [0, 3, 5, 10]
MAX_MINUTES_PRESETS = [0, 5, 10, 30, 60, 120]
BITRATE_PRESETS = [0, 1000, 2000, 4000, 8000, 16000]

TAB_GENERAL, TAB_VIDEO, TAB_AUDIO = range(3)


def preset_label(key: str) -> str:
    return tr("preset_" + key)


def describe_choice(choice: capture.FormatChoice | None, bitrate_kbps: int) -> str:
    """e.g. '640×480 · 30 fps · 1.5 Mbps · ≈ 12 MB/min'."""
    parts = []
    if choice is not None:
        parts.append(f"{choice.width}×{choice.height} · {choice.fps:g} fps")
    if bitrate_kbps > 0:
        parts.append(format_bitrate(bitrate_kbps))
        parts.append(tr("size_per_min", f"{capture.estimate_mb_per_minute(bitrate_kbps):.0f}"))
    else:
        parts.append(tr("bitrate_auto"))
    return " · ".join(parts)


class SettingsDialog(QDialog):
    def __init__(self, config: Config, parent=None, formats: list[capture.FormatChoice] | None = None,
                 initial_tab: int = TAB_GENERAL):
        super().__init__(parent)
        self.config = config
        self.formats = formats or []
        self.setWindowTitle(tr("settings"))
        self.setMinimumWidth(560)

        self.tabs = QTabWidget()
        self.tabs.addTab(self._build_general(), tr("tab_general"))
        self.tabs.addTab(self._build_video(), tr("tab_video"))
        self.tabs.addTab(self._build_audio(), tr("tab_audio"))

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
                                   | QDialogButtonBox.StandardButton.RestoreDefaults)
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText(tr("ok"))
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText(tr("cancel"))
        restore = buttons.button(QDialogButtonBox.StandardButton.RestoreDefaults)
        restore.setText(tr("restore_defaults"))
        restore.clicked.connect(self._restore_defaults)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        lay = QVBoxLayout(self)
        lay.addWidget(self.tabs)
        lay.addWidget(buttons)

        self._load()
        self.tabs.setCurrentIndex(initial_tab)

    # --- pages ------------------------------------------------------------
    @staticmethod
    def _form(parent: QWidget) -> QFormLayout:
        form = QFormLayout(parent)
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
        return form

    def _build_general(self) -> QWidget:
        w = QWidget()
        form = self._form(w)

        self.save_dir = QLineEdit()
        browse = QPushButton(tr("browse"))
        browse.clicked.connect(self._browse)
        row = QHBoxLayout()
        row.addWidget(self.save_dir, 1)
        row.addWidget(browse)
        form.addRow(tr("save_dir"), row)

        self.prefix = QLineEdit()
        self.prefix.setMaxLength(60)
        self.prefix.textChanged.connect(self._update_example)
        form.addRow(tr("file_prefix"), self.prefix)
        self.example = QLabel(objectName="hint")
        form.addRow("", self.example)

        self.countdown = QComboBox()
        self._fill_presets(self.countdown, COUNTDOWN_PRESETS, tr("seconds_off"), lambda v: f"{v}{tr('seconds')}")
        form.addRow(tr("countdown"), self.countdown)

        self.max_minutes = QComboBox()
        self._fill_presets(self.max_minutes, MAX_MINUTES_PRESETS, tr("seconds_off"), lambda v: f"{v}{tr('minutes')}")
        form.addRow(tr("max_minutes"), self.max_minutes)

        self.open_after = QCheckBox(tr("open_after"))
        form.addRow("", self.open_after)
        self.tray_notify = QCheckBox(tr("tray_notifications"))
        form.addRow("", self.tray_notify)
        self.minimize_to_tray = QCheckBox(tr("minimize_to_tray"))
        form.addRow("", self.minimize_to_tray)
        self.always_on_top = QCheckBox(tr("always_on_top"))
        form.addRow("", self.always_on_top)
        self.auto_update = QCheckBox(tr("auto_update"))
        form.addRow("", self.auto_update)

        self.language = QComboBox()
        for code, name in LANGUAGES.items():
            self.language.addItem(name, code)
        form.addRow(tr("language"), self.language)
        hint = QLabel(tr("language_restart").strip(" ()（）"), objectName="hint")
        form.addRow("", hint)
        return w

    def _build_video(self) -> QWidget:
        w = QWidget()
        outer = QVBoxLayout(w)

        # Recording quality: three common presets, or "custom" which unlocks the detailed options.
        quality_box = QGroupBox(tr("record_quality"))
        form = self._form(quality_box)
        self.preset = QComboBox()
        for p in capture.PRESETS:
            self.preset.addItem(preset_label(p.key), p.key)
        self.preset.addItem(preset_label(capture.CUSTOM), capture.CUSTOM)
        self.preset.currentIndexChanged.connect(self._update_video_state)
        form.addRow(tr("preset"), self.preset)
        self.preset_info = QLabel(objectName="hint")
        self.preset_info.setWordWrap(True)
        form.addRow("", self.preset_info)

        self.custom_format = QComboBox()
        self.custom_format.addItem(tr("auto"), "")
        for f in self.formats:
            self.custom_format.addItem(f"{f.width} × {f.height}  ·  {f.fps:g} fps", f.key)
        self.custom_format.currentIndexChanged.connect(self._update_video_state)
        form.addRow(tr("resolution"), self.custom_format)

        self.bitrate = QComboBox()
        self._fill_presets(self.bitrate, BITRATE_PRESETS, tr("bitrate_auto"), format_bitrate)
        self.bitrate.currentIndexChanged.connect(self._update_video_state)
        form.addRow(tr("bitrate"), self.bitrate)

        self.quality = QComboBox()
        for q in QUALITIES:
            self.quality.addItem(tr("q_" + q), q)
        form.addRow(tr("quality"), self.quality)
        self._custom_widgets = [self.custom_format, self.bitrate, self.quality]
        outer.addWidget(quality_box)

        other_box = QGroupBox(tr("file_and_preview"))
        form2 = self._form(other_box)
        self.container = QComboBox()
        for ff in capture.supported_containers():
            label = f"{capture.container_suffix(ff).upper()} — {QMediaFormat.fileFormatDescription(ff)}"
            self.container.addItem(label, ff.name)
        self.container.currentIndexChanged.connect(self._fill_codecs)
        self.container.currentIndexChanged.connect(self._update_example)
        form2.addRow(tr("container"), self.container)

        self.video_codec = QComboBox()
        form2.addRow(tr("video_codec"), self.video_codec)

        self.snapshot_format = QComboBox()
        self.snapshot_format.addItem("JPG", "jpg")
        self.snapshot_format.addItem("PNG", "png")
        form2.addRow(tr("snapshot_format"), self.snapshot_format)

        self.mirror = QCheckBox(tr("mirror"))
        form2.addRow("", self.mirror)
        outer.addWidget(other_box)
        outer.addStretch(1)
        return w

    def _build_audio(self) -> QWidget:
        w = QWidget()
        form = self._form(w)
        self.audio_codec = QComboBox()
        form.addRow(tr("audio_codec"), self.audio_codec)

        self.volume = QSlider(Qt.Orientation.Horizontal)
        self.volume.setRange(0, 100)
        self.volume_label = QLabel()
        self.volume_label.setMinimumWidth(40)
        self.volume.valueChanged.connect(lambda v: self.volume_label.setText(f"{v}%"))
        row = QHBoxLayout()
        row.addWidget(self.volume, 1)
        row.addWidget(self.volume_label)
        form.addRow(tr("volume"), row)
        return w

    # --- helpers ----------------------------------------------------------
    def _update_video_state(self) -> None:
        key = self.preset.currentData()
        custom = key == capture.CUSTOM
        for wdg in self._custom_widgets:
            wdg.setEnabled(custom)
        # Quality only matters when the bitrate is left on automatic.
        self.quality.setEnabled(custom and not self.bitrate.currentData())

        if custom:
            fkey = self.custom_format.currentData()
            choice = next((f for f in self.formats if f.key == fkey), None) if fkey \
                else capture.auto_format(self.formats)
            self.preset_info.setText(describe_choice(choice, self.bitrate.currentData() or 0))
        else:
            p = capture.find_preset(key)
            choice = capture.preset_format(self.formats, p.height) if p else None
            text = describe_choice(choice, p.bitrate_kbps if p else 0)
            if p and choice is not None and choice.height != p.height:
                text += "  " + tr("preset_nearest")
            self.preset_info.setText(text)

    def _fill_codecs(self) -> None:
        ff = capture.enum_by_name(QMediaFormat.FileFormat, self.container.currentData(), QMediaFormat.FileFormat.MPEG4)
        prev_v = self.video_codec.currentData() or self.config.get("video/codec")
        prev_a = self.audio_codec.currentData() or self.config.get("audio/codec")

        self.video_codec.clear()
        self.video_codec.addItem(tr("auto"), "Unspecified")
        for c in capture.supported_video_codecs(ff):
            self.video_codec.addItem(QMediaFormat.videoCodecDescription(c), c.name)
        self._select(self.video_codec, prev_v)

        self.audio_codec.clear()
        self.audio_codec.addItem(tr("auto"), "Unspecified")
        for c in capture.supported_audio_codecs(ff):
            self.audio_codec.addItem(QMediaFormat.audioCodecDescription(c), c.name)
        self._select(self.audio_codec, prev_a)

    @staticmethod
    def _fill_presets(combo: QComboBox, values: list[int], zero_text: str, fmt) -> None:
        combo.clear()
        for v in values:
            combo.addItem(zero_text if v == 0 else fmt(v), v)
        combo.setProperty("fmt", fmt)

    @staticmethod
    def _select_int(combo: QComboBox, value: int) -> None:
        idx = combo.findData(value)
        if idx < 0:  # a custom value (e.g. edited in wincam.ini): keep it selectable
            combo.addItem(combo.property("fmt")(value), value)
            idx = combo.count() - 1
        combo.setCurrentIndex(idx)

    @staticmethod
    def _select(combo: QComboBox, data) -> None:
        idx = combo.findData(data)
        combo.setCurrentIndex(max(idx, 0))

    def _browse(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, tr("choose_folder"), self.save_dir.text())
        if folder:
            self.save_dir.setText(folder)

    def _update_example(self) -> None:
        ff = capture.enum_by_name(QMediaFormat.FileFormat, self.container.currentData(), QMediaFormat.FileFormat.MPEG4)
        name = build_output_path("", self.prefix.text(), capture.container_suffix(ff),
                                 datetime(2026, 1, 1, 9, 30, 0)).name
        self.example.setText(tr("file_example", name))

    def _set_values(self, get) -> None:
        self.save_dir.setText(get("app/save_dir"))
        self.prefix.setText(get("app/file_prefix"))
        self._select_int(self.countdown, get("app/countdown"))
        self._select_int(self.max_minutes, get("app/max_minutes"))
        self.open_after.setChecked(get("app/reveal_after_recording"))
        self.tray_notify.setChecked(get("app/tray_notifications"))
        self.minimize_to_tray.setChecked(get("app/minimize_to_tray"))
        self.always_on_top.setChecked(get("app/always_on_top"))
        self.auto_update.setChecked(get("update/auto_check"))
        self._select(self.preset, get("video/preset"))
        fkey = get("video/format")
        if fkey and self.custom_format.findData(fkey) < 0:  # saved for a camera that is not plugged in now
            self.custom_format.addItem(fkey.replace("x", " × ").replace("@", "  ·  ") + " fps", fkey)
        self._select(self.custom_format, fkey)
        self._select_int(self.bitrate, get("video/bitrate_kbps"))
        q = self.quality.findData(get("video/quality"))
        self.quality.setCurrentIndex(q if q >= 0 else self.quality.findData("HighQuality"))
        self._select(self.container, get("video/container"))
        self._fill_codecs()
        self._select(self.video_codec, get("video/codec"))
        self._select(self.audio_codec, get("audio/codec"))
        self.mirror.setChecked(get("video/mirror_preview"))
        self._select(self.snapshot_format, get("snapshot/format"))
        self.volume.setValue(get("audio/volume"))
        self.volume_label.setText(f"{self.volume.value()}%")
        self._update_example()
        self._update_video_state()

    def _load(self) -> None:
        self._select(self.language, self.config.get("app/language"))
        self._set_values(self.config.get)

    def _restore_defaults(self) -> None:
        def get(key):
            if key == "app/save_dir":
                return default_save_dir()
            return DEFAULTS[key]

        self._set_values(get)

    def apply(self) -> None:
        c = self.config
        c.set("app/save_dir", self.save_dir.text().strip() or default_save_dir())
        c.set("app/file_prefix", self.prefix.text().strip())
        c.set("app/countdown", self.countdown.currentData())
        c.set("app/max_minutes", self.max_minutes.currentData())
        c.set("app/reveal_after_recording", self.open_after.isChecked())
        c.set("app/tray_notifications", self.tray_notify.isChecked())
        c.set("app/minimize_to_tray", self.minimize_to_tray.isChecked())
        c.set("app/always_on_top", self.always_on_top.isChecked())
        c.set("update/auto_check", self.auto_update.isChecked())
        c.set("app/language", self.language.currentData())
        c.set("video/preset", self.preset.currentData())
        c.set("video/format", self.custom_format.currentData() or "")
        c.set("video/bitrate_kbps", self.bitrate.currentData())
        c.set("video/quality", self.quality.currentData())
        if self.container.count():
            c.set("video/container", self.container.currentData())
        c.set("video/codec", self.video_codec.currentData() or "Unspecified")
        c.set("video/mirror_preview", self.mirror.isChecked())
        c.set("snapshot/format", self.snapshot_format.currentData())
        c.set("audio/codec", self.audio_codec.currentData() or "Unspecified")
        c.set("audio/volume", self.volume.value())
        c.sync()


def quality_enum(name: str) -> QMediaRecorder.Quality:
    return capture.enum_by_name(QMediaRecorder.Quality, name, QMediaRecorder.Quality.HighQuality)
