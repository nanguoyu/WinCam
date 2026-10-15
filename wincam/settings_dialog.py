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
from wincam.utils import build_output_path

QUALITIES = ["VeryLowQuality", "LowQuality", "NormalQuality", "HighQuality", "VeryHighQuality"]
COUNTDOWN_PRESETS = [0, 3, 5, 10]
MAX_MINUTES_PRESETS = [0, 1, 5, 10, 15, 30, 60, 120, 240]
BITRATE_PRESETS = [0, 1000, 2500, 5000, 8000, 12000, 20000, 40000]


class SettingsDialog(QDialog):
    def __init__(self, config: Config, parent=None):
        super().__init__(parent)
        self.config = config
        self.setWindowTitle(tr("settings"))
        self.setMinimumWidth(520)

        tabs = QTabWidget()
        tabs.addTab(self._build_general(), tr("tab_general"))
        tabs.addTab(self._build_video(), tr("tab_video"))
        tabs.addTab(self._build_audio(), tr("tab_audio"))

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
        lay.addWidget(tabs)
        lay.addWidget(buttons)

        self._load()

    # --- pages ------------------------------------------------------------
    def _build_general(self) -> QWidget:
        w = QWidget()
        form = QFormLayout(w)
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)

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
        self.example = QLabel()
        self.example.setObjectName("hint")
        form.addRow("", self.example)

        self.countdown = QComboBox()
        self._fill_presets(self.countdown, COUNTDOWN_PRESETS, tr("seconds_off"), tr("seconds"))
        form.addRow(tr("countdown"), self.countdown)

        self.max_minutes = QComboBox()
        self._fill_presets(self.max_minutes, MAX_MINUTES_PRESETS, tr("seconds_off"), tr("minutes"))
        form.addRow(tr("max_minutes"), self.max_minutes)

        self.open_after = QCheckBox(tr("open_after"))
        form.addRow("", self.open_after)
        self.always_on_top = QCheckBox(tr("always_on_top"))
        form.addRow("", self.always_on_top)

        self.language = QComboBox()
        for code, name in LANGUAGES.items():
            self.language.addItem(name, code)
        form.addRow(tr("language"), self.language)
        hint = QLabel(tr("language_restart").strip(" ()（）"))
        hint.setObjectName("hint")
        form.addRow("", hint)
        return w

    def _build_video(self) -> QWidget:
        w = QWidget()
        form = QFormLayout(w)
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)

        self.container = QComboBox()
        for ff in capture.supported_containers():
            label = f"{capture.container_suffix(ff).upper()} — {QMediaFormat.fileFormatDescription(ff)}"
            self.container.addItem(label, ff.name)
        self.container.currentIndexChanged.connect(self._fill_codecs)
        self.container.currentIndexChanged.connect(self._update_example)
        form.addRow(tr("container"), self.container)

        self.video_codec = QComboBox()
        form.addRow(tr("video_codec"), self.video_codec)

        self.quality = QComboBox()
        for q in QUALITIES:
            self.quality.addItem(tr("q_" + q), q)
        form.addRow(tr("quality"), self.quality)

        self.bitrate = QComboBox()
        self._fill_presets(self.bitrate, BITRATE_PRESETS, tr("bitrate_auto"), " kbps")
        form.addRow(tr("bitrate"), self.bitrate)

        self.mirror = QCheckBox(tr("mirror"))
        form.addRow("", self.mirror)

        self.snapshot_format = QComboBox()
        self.snapshot_format.addItem("JPG", "jpg")
        self.snapshot_format.addItem("PNG", "png")
        form.addRow(tr("snapshot_format"), self.snapshot_format)
        return w

    def _build_audio(self) -> QWidget:
        w = QWidget()
        form = QFormLayout(w)
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
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
    def _fill_presets(combo: QComboBox, values: list[int], zero_text: str, suffix: str) -> None:
        combo.clear()
        for v in values:
            combo.addItem(zero_text if v == 0 else f"{v}{suffix}", v)
        combo.setProperty("suffix", suffix)

    @staticmethod
    def _select_int(combo: QComboBox, value: int) -> None:
        idx = combo.findData(value)
        if idx < 0:  # a custom value (e.g. edited in wincam.ini): keep it selectable
            combo.addItem(f"{value}{combo.property('suffix')}", value)
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

    def _load(self) -> None:
        c = self.config
        self.save_dir.setText(c.get("app/save_dir"))
        self.prefix.setText(c.get("app/file_prefix"))
        self._select_int(self.countdown, c.get("app/countdown"))
        self._select_int(self.max_minutes, c.get("app/max_minutes"))
        self.open_after.setChecked(c.get("app/open_folder_after"))
        self.always_on_top.setChecked(c.get("app/always_on_top"))
        self._select(self.language, c.get("app/language"))
        self._select(self.container, c.get("video/container"))
        self._fill_codecs()
        self._select(self.video_codec, c.get("video/codec"))
        self._select(self.audio_codec, c.get("audio/codec"))
        self._select(self.quality, c.get("video/quality"))
        self._select_int(self.bitrate, c.get("video/bitrate_kbps"))
        self.mirror.setChecked(c.get("video/mirror_preview"))
        self._select(self.snapshot_format, c.get("snapshot/format"))
        self.volume.setValue(c.get("audio/volume"))
        self.volume_label.setText(f"{self.volume.value()}%")
        self._update_example()

    def _restore_defaults(self) -> None:
        self.save_dir.setText(default_save_dir())
        self.prefix.setText(DEFAULTS["app/file_prefix"])
        self._select_int(self.countdown, DEFAULTS["app/countdown"])
        self._select_int(self.max_minutes, DEFAULTS["app/max_minutes"])
        self.open_after.setChecked(DEFAULTS["app/open_folder_after"])
        self.always_on_top.setChecked(DEFAULTS["app/always_on_top"])
        self._select(self.container, DEFAULTS["video/container"])
        self._fill_codecs()
        self._select(self.video_codec, DEFAULTS["video/codec"])
        self._select(self.audio_codec, DEFAULTS["audio/codec"])
        self._select(self.quality, DEFAULTS["video/quality"])
        self._select_int(self.bitrate, DEFAULTS["video/bitrate_kbps"])
        self.mirror.setChecked(DEFAULTS["video/mirror_preview"])
        self._select(self.snapshot_format, DEFAULTS["snapshot/format"])
        self.volume.setValue(DEFAULTS["audio/volume"])

    def apply(self) -> None:
        c = self.config
        c.set("app/save_dir", self.save_dir.text().strip() or default_save_dir())
        c.set("app/file_prefix", self.prefix.text().strip())
        c.set("app/countdown", self.countdown.currentData())
        c.set("app/max_minutes", self.max_minutes.currentData())
        c.set("app/open_folder_after", self.open_after.isChecked())
        c.set("app/always_on_top", self.always_on_top.isChecked())
        c.set("app/language", self.language.currentData())
        if self.container.count():
            c.set("video/container", self.container.currentData())
        c.set("video/codec", self.video_codec.currentData() or "Unspecified")
        c.set("video/quality", self.quality.currentData())
        c.set("video/bitrate_kbps", self.bitrate.currentData())
        c.set("video/mirror_preview", self.mirror.isChecked())
        c.set("snapshot/format", self.snapshot_format.currentData())
        c.set("audio/codec", self.audio_codec.currentData() or "Unspecified")
        c.set("audio/volume", self.volume.value())
        c.sync()


def quality_enum(name: str) -> QMediaRecorder.Quality:
    return capture.enum_by_name(QMediaRecorder.Quality, name, QMediaRecorder.Quality.HighQuality)
