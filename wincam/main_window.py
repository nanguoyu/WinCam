"""Main application window."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QSize, Qt, QTimer
from PySide6.QtGui import QAction, QKeySequence, QShortcut
from PySide6.QtMultimedia import QMediaDevices, QMediaFormat, QMediaRecorder
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QSizePolicy,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from wincam import __app_name__, __version__, capture
from wincam.config import Config
from wincam.i18n import tr
from wincam.icons import icon
from wincam.settings_dialog import SettingsDialog, quality_enum
from wincam.utils import (
    build_output_path,
    format_bytes,
    format_duration,
    free_space,
    open_in_explorer,
)
from wincam.widgets import PreviewView, RecordButton

MIN_FREE_START = 300 * 1024 * 1024   # refuse to start below this
MIN_FREE_RECORDING = 150 * 1024 * 1024  # auto-stop below this


class MainWindow(QMainWindow):
    def __init__(self, config: Config):
        super().__init__()
        self.config = config
        self.setWindowTitle(__app_name__)
        self.setMinimumSize(720, 520)

        self._formats: list[capture.FormatChoice] = []
        self._countdown_left = 0
        self._close_after_stop = False
        self._force_quit = False
        self._last_saved = ""
        self._blink = True
        self._updating_devices = False

        self._build_ui()
        self._build_shortcuts()

        self.preview.set_mirror(self.config.get("video/mirror_preview"))
        self.controller = capture.CaptureController(self.preview.video_item, self)
        self.controller.set_volume(self.config.get("audio/volume"))
        self.controller.errorOccurred.connect(self._on_error)
        self.controller.recorderStateChanged.connect(self._on_recorder_state)
        self.controller.durationChanged.connect(self._on_duration)
        self.controller.recordingSaved.connect(self._on_saved)
        self.controller.snapshotSaved.connect(lambda p: self._status(tr("snapshot_saved", p), 6000))
        self.controller.cameraActiveChanged.connect(lambda _a: self._update_buttons())

        self._devices = QMediaDevices(self)
        self._devices.videoInputsChanged.connect(self._refresh_cameras)
        self._devices.audioInputsChanged.connect(self._refresh_mics)

        self._countdown_timer = QTimer(self, interval=1000)
        self._countdown_timer.timeout.connect(self._countdown_tick)
        self._blink_timer = QTimer(self, interval=500)
        self._blink_timer.timeout.connect(self._blink_tick)
        self._disk_timer = QTimer(self, interval=15000)
        self._disk_timer.timeout.connect(self._check_disk)

        self._apply_window_flags()
        self._update_folder_label()
        self._update_summary()
        self._refresh_mics()
        self._refresh_cameras()
        self._update_buttons()
        self._status(tr("ready"))

        geo = self.config.raw().value("window/geometry")
        if geo is not None:
            self.restoreGeometry(geo)
        else:
            self.resize(1000, 700)

    # ======================================================================
    # UI construction
    # ======================================================================
    def _build_ui(self) -> None:
        central = QWidget()
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # --- top bar: device pickers ------------------------------------
        top = QWidget(objectName="topBar")
        tl = QHBoxLayout(top)
        tl.setContentsMargins(12, 8, 12, 8)
        tl.setSpacing(8)

        tl.addWidget(self._icon_label("video", tr("camera")))
        self.camera_combo = QComboBox()
        self.camera_combo.setMinimumContentsLength(18)
        self.camera_combo.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self.camera_combo.setToolTip(tr("camera"))
        self.camera_combo.currentIndexChanged.connect(self._on_camera_selected)
        tl.addWidget(self.camera_combo, 3)

        self.format_combo = QComboBox()
        self.format_combo.setMinimumContentsLength(14)
        self.format_combo.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self.format_combo.setToolTip(tr("resolution"))
        self.format_combo.currentIndexChanged.connect(self._on_format_selected)
        tl.addWidget(self.format_combo, 2)

        tl.addSpacing(8)
        tl.addWidget(self._icon_label("mic", tr("microphone")))
        self.mic_combo = QComboBox()
        self.mic_combo.setMinimumContentsLength(16)
        self.mic_combo.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self.mic_combo.setToolTip(tr("microphone"))
        self.mic_combo.currentIndexChanged.connect(self._on_mic_selected)
        tl.addWidget(self.mic_combo, 3)

        tl.addSpacing(4)
        self.refresh_btn = self._tool_button("refresh", tr("refresh"), self._refresh_all)
        self.settings_btn = self._tool_button("gear", tr("settings") + " (Ctrl+,)", self._open_settings)
        self.about_btn = self._tool_button("info", tr("about"), self._about)
        for b in (self.refresh_btn, self.settings_btn, self.about_btn):
            tl.addWidget(b)
        root.addWidget(top)

        # --- preview ------------------------------------------------------
        self.preview = PreviewView()
        self.preview.doubleClicked.connect(self._toggle_fullscreen)
        root.addWidget(self.preview, 1)

        # --- bottom controls --------------------------------------------
        bottom = QWidget(objectName="bottomBar")
        bl = QHBoxLayout(bottom)
        bl.setContentsMargins(12, 10, 12, 10)

        left = QHBoxLayout()
        left.setSpacing(6)
        self.folder_btn = QToolButton(objectName="folderButton")
        self.folder_btn.setIcon(icon("folder"))
        self.folder_btn.setIconSize(QSize(18, 18))
        self.folder_btn.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.folder_btn.setToolTip(tr("open_folder"))
        self.folder_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.folder_btn.clicked.connect(self._open_folder)
        self.change_btn = QToolButton(objectName="linkButton")
        self.change_btn.setText(tr("change_folder"))
        self.change_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.change_btn.clicked.connect(self._choose_folder)
        left.addWidget(self.folder_btn)
        left.addWidget(self.change_btn)
        left.addStretch(1)

        center = QHBoxLayout()
        center.setSpacing(18)
        self.pause_btn = self._round_button("pause", tr("pause") + " (F10)", self._toggle_pause)
        self.record_btn = RecordButton()
        self.record_btn.setFixedSize(68, 68)
        self.record_btn.setToolTip(tr("record") + " (F9)")
        self.record_btn.clicked.connect(self._on_record_clicked)
        self.snap_btn = self._round_button("camera", tr("snapshot") + " (F8)", self._snapshot)
        center.addWidget(self.pause_btn)
        center.addWidget(self.record_btn)
        center.addWidget(self.snap_btn)

        right = QHBoxLayout()
        right.addStretch(1)
        self.time_label = QLabel("00:00:00", objectName="timeLabel")
        right.addWidget(self.time_label)

        lw, rw = QWidget(), QWidget()
        lw.setLayout(left)
        rw.setLayout(right)
        for w in (lw, rw):
            w.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        left.setContentsMargins(0, 0, 0, 0)
        right.setContentsMargins(0, 0, 0, 0)
        bl.addWidget(lw, 1)
        bl.addLayout(center)
        bl.addWidget(rw, 1)
        root.addWidget(bottom)

        self.setCentralWidget(central)

        # --- status bar ---------------------------------------------------
        sb = self.statusBar()
        sb.setSizeGripEnabled(True)
        self.summary_label = QLabel(objectName="summaryLabel")
        self.space_label = QLabel(objectName="spaceLabel")
        sb.addPermanentWidget(self.summary_label)
        sb.addPermanentWidget(self.space_label)

    def _icon_label(self, name: str, tooltip: str) -> QLabel:
        lbl = QLabel()
        lbl.setPixmap(icon(name).pixmap(QSize(20, 20)))
        lbl.setToolTip(tooltip)
        return lbl

    def _tool_button(self, name: str, tooltip: str, slot) -> QToolButton:
        b = QToolButton()
        b.setIcon(icon(name))
        b.setIconSize(QSize(20, 20))
        b.setToolTip(tooltip)
        b.setAutoRaise(True)
        b.clicked.connect(slot)
        return b

    def _round_button(self, name: str, tooltip: str, slot) -> QToolButton:
        b = QToolButton(objectName="roundButton")
        b.setIcon(icon(name))
        b.setIconSize(QSize(22, 22))
        b.setFixedSize(46, 46)
        b.setToolTip(tooltip)
        b.setCursor(Qt.CursorShape.PointingHandCursor)
        b.clicked.connect(slot)
        return b

    def _build_shortcuts(self) -> None:
        QShortcut(QKeySequence(Qt.Key.Key_F9), self, activated=self._on_record_clicked)
        QShortcut(QKeySequence(Qt.Key.Key_F10), self, activated=self._toggle_pause)
        QShortcut(QKeySequence(Qt.Key.Key_F8), self, activated=self._snapshot)
        QShortcut(QKeySequence(Qt.Key.Key_F11), self, activated=self._toggle_fullscreen)
        QShortcut(QKeySequence("Ctrl+,"), self, activated=self._open_settings)
        esc = QAction(self)
        esc.setShortcut(QKeySequence(Qt.Key.Key_Escape))
        esc.triggered.connect(lambda: self.isFullScreen() and self._toggle_fullscreen())
        self.addAction(esc)

    # ======================================================================
    # Devices
    # ======================================================================
    def _refresh_all(self) -> None:
        self._refresh_mics()
        self._refresh_cameras(force_restart=True)

    def _refresh_cameras(self, force_restart: bool = False) -> None:
        cams = QMediaDevices.videoInputs()
        current = self.camera_combo.currentData() or self.config.get("video/camera_id")
        keys = [capture.device_key(c) for c in cams]

        if self.controller.is_recording() and current not in keys:
            # The camera we are recording from was unplugged.
            self.controller.stop_recording()

        self._updating_devices = True
        self.camera_combo.clear()
        for c in cams:
            label = c.description()
            if capture.is_builtin(c):
                label += f"  ({tr('builtin')})"
            self.camera_combo.addItem(label, capture.device_key(c))
            self.camera_combo.setItemData(self.camera_combo.count() - 1, c.description(), Qt.ItemDataRole.ToolTipRole)
        self._updating_devices = False

        if not cams:
            self.camera_combo.addItem(tr("no_camera"), "")
            self.camera_combo.setEnabled(False)
            self.format_combo.clear()
            self.format_combo.setEnabled(False)
            self.controller.stop_camera()
            self.preview.set_message(tr("no_camera_hint"))
            self.preview.set_info("")
            self._update_buttons()
            return

        self.camera_combo.setEnabled(not self.controller.is_recording())
        if current in keys:
            idx = keys.index(current)
        else:
            default = QMediaDevices.defaultVideoInput()
            default_key = "" if default.isNull() else capture.device_key(default)
            idx = keys.index(default_key) if default_key in keys else 0

        same = (self.controller.camera is not None
                and capture.device_key(self.controller.camera.cameraDevice()) == keys[idx])
        self._updating_devices = True
        self.camera_combo.setCurrentIndex(idx)
        self._updating_devices = False
        if not same or force_restart:
            self._on_camera_selected(idx)

    def _on_camera_selected(self, idx: int) -> None:
        if self._updating_devices or idx < 0:
            return
        key = self.camera_combo.itemData(idx)
        dev = capture.find_camera(key) if key else None
        if dev is None:
            return
        self.config.set("video/camera_id", key)

        self._formats = capture.camera_formats(dev)
        saved = self.config.get("video/format")
        auto = capture.auto_format(self._formats)
        self._updating_devices = True
        self.format_combo.clear()
        auto_label = tr("auto")
        if auto is not None:
            auto_label += f" ({auto.width}×{auto.height} · {auto.fps:g} fps)"
        self.format_combo.addItem(auto_label, "")
        for f in self._formats:
            self.format_combo.addItem(f"{f.width} × {f.height}  ·  {f.fps:g} fps", f.key)
        sel = self.format_combo.findData(saved) if saved else 0
        self.format_combo.setCurrentIndex(max(0, sel))
        self.format_combo.setEnabled(not self.controller.is_recording() and bool(self._formats))
        self._updating_devices = False
        self._start_camera()

    def _on_format_selected(self, idx: int) -> None:
        if self._updating_devices or idx < 0:
            return
        self.config.set("video/format", self.format_combo.itemData(idx) or "")
        self._start_camera()

    def _selected_format(self) -> capture.FormatChoice | None:
        key = self.format_combo.currentData()
        if key:
            for f in self._formats:
                if f.key == key:
                    return f
        return capture.auto_format(self._formats)

    def _start_camera(self) -> None:
        key = self.camera_combo.currentData()
        dev = capture.find_camera(key) if key else None
        if dev is None:
            return
        choice = self._selected_format()
        self.preview.set_message("")
        self.controller.set_camera(dev, choice.fmt if choice else None)
        self.preview.set_info(f"{choice.width}×{choice.height} · {choice.fps:g} fps" if choice else "")
        self._update_buttons()

    def _refresh_mics(self) -> None:
        mics = QMediaDevices.audioInputs()
        default = QMediaDevices.defaultAudioInput()
        default_key = capture.device_key(default) if not default.isNull() else ""
        current = self.mic_combo.currentData()
        if current is None:
            current = self.config.get("audio/device_id")

        self._updating_devices = True
        self.mic_combo.clear()
        self.mic_combo.addItem(tr("no_audio"), "none")
        for m in mics:
            key = capture.device_key(m)
            label = m.description() + (tr("default_suffix") if key == default_key else "")
            self.mic_combo.addItem(label, key)
        idx = self.mic_combo.findData(current) if current else -1
        if idx < 0:
            # "" means "system default"; fall back to it, or to "no audio" if there is no mic at all.
            idx = self.mic_combo.findData(default_key) if default_key else -1
            if idx < 0:
                idx = 1 if mics else 0
        self.mic_combo.setCurrentIndex(idx)
        self.mic_combo.setEnabled(not self.controller.is_recording())
        self._updating_devices = False
        self._apply_mic()

    def _on_mic_selected(self, idx: int) -> None:
        if self._updating_devices or idx < 0:
            return
        self.config.set("audio/device_id", self.mic_combo.itemData(idx))
        self._apply_mic()

    def _apply_mic(self) -> None:
        key = self.mic_combo.currentData()
        if not key or key == "none":
            self.controller.set_audio_input(None)
        else:
            self.controller.set_audio_input(capture.find_audio_input(key))

    # ======================================================================
    # Recording
    # ======================================================================
    def _on_record_clicked(self) -> None:
        if self._countdown_left > 0:
            self._cancel_countdown()
            return
        if self.controller.is_recording():
            self.controller.stop_recording()
            return
        if not self.controller.camera_active():
            self.record_btn.setChecked(False)
            return
        seconds = self.config.get("app/countdown")
        if seconds > 0:
            self.record_btn.setChecked(False)
            self._countdown_left = seconds
            self.preview.set_countdown(seconds)
            self.record_btn.set_pending(True)
            self._status(tr("countdown_cancel"))
            self._countdown_timer.start()
        else:
            self._start_recording()

    def _countdown_tick(self) -> None:
        self._countdown_left -= 1
        self.preview.set_countdown(self._countdown_left)
        if self._countdown_left <= 0:
            self._countdown_timer.stop()
            self.record_btn.set_pending(False)
            self._start_recording()

    def _cancel_countdown(self) -> None:
        self._countdown_timer.stop()
        self._countdown_left = 0
        self.preview.set_countdown(0)
        self.record_btn.set_pending(False)
        self.record_btn.setChecked(False)
        self._status(tr("ready"))

    def _ensure_save_dir(self) -> Path | None:
        folder = Path(self.config.get("app/save_dir"))
        try:
            folder.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            QMessageBox.warning(self, tr("error"), tr("folder_error", f"{folder}\n{e}"))
            return None
        return folder

    def _record_options(self) -> capture.RecordOptions:
        c = self.config
        return capture.RecordOptions(
            container=capture.enum_by_name(QMediaFormat.FileFormat, c.get("video/container"),
                                           QMediaFormat.FileFormat.MPEG4),
            video_codec=capture.enum_by_name(QMediaFormat.VideoCodec, c.get("video/codec"),
                                             QMediaFormat.VideoCodec.Unspecified),
            audio_codec=capture.enum_by_name(QMediaFormat.AudioCodec, c.get("audio/codec"),
                                             QMediaFormat.AudioCodec.Unspecified),
            quality=quality_enum(c.get("video/quality")),
            bitrate_kbps=c.get("video/bitrate_kbps"),
        )

    def _start_recording(self) -> None:
        folder = self._ensure_save_dir()
        if folder is None:
            self.record_btn.setChecked(False)
            return
        free = free_space(folder)
        if free is not None and free < MIN_FREE_START:
            QMessageBox.warning(self, tr("error"), tr("low_space", format_bytes(free)))
            self.record_btn.setChecked(False)
            return
        opts = self._record_options()
        path = build_output_path(folder, self.config.get("app/file_prefix"),
                                 capture.container_suffix(opts.container))
        self.controller.start_recording(str(path), opts)

    def _toggle_pause(self) -> None:
        if self.controller.is_recording():
            self.controller.toggle_pause()

    def _on_recorder_state(self, state: QMediaRecorder.RecorderState) -> None:
        recording = state != QMediaRecorder.RecorderState.StoppedState
        paused = state == QMediaRecorder.RecorderState.PausedState
        self.record_btn.setChecked(recording)
        self.record_btn.setToolTip((tr("stop") if recording else tr("record")) + " (F9)")
        self.pause_btn.setIcon(icon("play" if paused else "pause"))
        self.pause_btn.setToolTip((tr("resume") if paused else tr("pause")) + " (F10)")
        for w in (self.camera_combo, self.format_combo, self.mic_combo, self.refresh_btn,
                  self.settings_btn, self.change_btn):
            w.setEnabled(not recording)
        if not recording:
            self.camera_combo.setEnabled(bool(self.camera_combo.currentData()))
            self.format_combo.setEnabled(bool(self._formats))

        if recording:
            self._blink = True
            self._blink_timer.start()
            self._disk_timer.start()
            self._status(tr("paused") if paused else tr("recording"))
            self.time_label.setProperty("recording", True)
            self._render_rec(self.controller.recorder.duration())
        else:
            self._blink_timer.stop()
            self._disk_timer.stop()
            self.preview.set_recording("")
            self.time_label.setProperty("recording", False)
            self.time_label.setText("00:00:00")
        self.time_label.style().unpolish(self.time_label)
        self.time_label.style().polish(self.time_label)
        self._update_buttons()

        if not recording and self._close_after_stop:
            QTimer.singleShot(0, self.close)

    def _render_rec(self, ms: int) -> None:
        text = format_duration(ms)
        self.time_label.setText(text)
        self.preview.set_recording(text, paused=self.controller.is_paused(), blink=self._blink)

    def _on_duration(self, ms: int) -> None:
        if not self.controller.is_recording():
            return
        self._render_rec(ms)
        limit = self.config.get("app/max_minutes")
        if limit > 0 and ms >= limit * 60_000:
            self.controller.stop_recording()

    def _blink_tick(self) -> None:
        self._blink = not self._blink
        self._render_rec(self.controller.recorder.duration())

    def _check_disk(self) -> None:
        free = free_space(self.config.get("app/save_dir"))
        self._update_space(free)
        if free is not None and free < MIN_FREE_RECORDING and self.controller.is_recording():
            self.controller.stop_recording()
            QMessageBox.warning(self, tr("error"), tr("low_space", format_bytes(free)))

    def _on_saved(self, path: str) -> None:
        self._last_saved = path
        self._status(tr("saved_to", path), 10000)
        self._update_space()
        if self.config.get("app/open_folder_after") and not self._close_after_stop:
            open_in_explorer(path, select=True)

    def _snapshot(self) -> None:
        if not self.controller.camera_active():
            return
        folder = self._ensure_save_dir()
        if folder is None:
            return
        path = build_output_path(folder, self.config.get("app/file_prefix"), self.config.get("snapshot/format"))
        self.controller.capture_snapshot(str(path))

    # ======================================================================
    # Misc UI
    # ======================================================================
    def _on_error(self, kind: str, message: str) -> None:
        if kind == "camera":
            self.preview.set_message(tr("camera_error", message))
            self._status(tr("error") + ": " + message)
            self._update_buttons()
        elif kind == "recorder":
            self.record_btn.setChecked(self.controller.is_recording())
            self._status(tr("error") + ": " + message)
            QMessageBox.warning(self, tr("error"), tr("recorder_error", message))
        else:
            self._status(tr("error") + ": " + message, 8000)

    def _update_buttons(self) -> None:
        cam_ok = self.controller.camera_active()
        recording = self.controller.is_recording()
        self.record_btn.setEnabled(cam_ok or recording)
        self.snap_btn.setEnabled(cam_ok)
        self.pause_btn.setEnabled(recording)

    def _status(self, text: str, timeout: int = 0) -> None:
        self.statusBar().showMessage(text, timeout)

    def _update_folder_label(self) -> None:
        folder = self.config.get("app/save_dir")
        fm = self.folder_btn.fontMetrics()
        self.folder_btn.setText(fm.elidedText(folder, Qt.TextElideMode.ElideMiddle, 300))
        self.folder_btn.setToolTip(f"{tr('open_folder')}\n{folder}")
        self._update_space()

    def _update_space(self, free: int | None = None) -> None:
        if free is None:
            free = free_space(self.config.get("app/save_dir"))
        if free is None:
            self.space_label.setText("")
            return
        warn = free < MIN_FREE_START
        self.space_label.setText(tr("low_space", format_bytes(free)) if warn else tr("free_space", format_bytes(free)))
        self.space_label.setProperty("warn", warn)
        self.space_label.style().unpolish(self.space_label)
        self.space_label.style().polish(self.space_label)

    def _update_summary(self) -> None:
        opts = self._record_options()
        parts = [capture.container_suffix(opts.container).upper()]
        if opts.video_codec != QMediaFormat.VideoCodec.Unspecified:
            parts.append(QMediaFormat.videoCodecDescription(opts.video_codec))
        parts.append(tr("q_" + opts.quality.name).split("（")[0].split(" (")[0])
        if opts.bitrate_kbps:
            parts.append(f"{opts.bitrate_kbps} kbps")
        self.summary_label.setText(" · ".join(parts))

    def _choose_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, tr("choose_folder"), self.config.get("app/save_dir"))
        if folder:
            self.config.set("app/save_dir", folder)
            self._update_folder_label()

    def _open_folder(self) -> None:
        folder = self._ensure_save_dir()
        if folder is None:
            return
        if self._last_saved and Path(self._last_saved).exists() and Path(self._last_saved).parent == folder:
            open_in_explorer(self._last_saved, select=True)
        else:
            open_in_explorer(folder)

    def _open_settings(self) -> None:
        if self.controller.is_recording():
            return
        dlg = SettingsDialog(self.config, self)
        if dlg.exec():
            dlg.apply()
            self.preview.set_mirror(self.config.get("video/mirror_preview"))
            self.controller.set_volume(self.config.get("audio/volume"))
            self._apply_window_flags()
            self._update_folder_label()
            self._update_summary()

    def _apply_window_flags(self) -> None:
        on_top = self.config.get("app/always_on_top")
        if bool(self.windowFlags() & Qt.WindowType.WindowStaysOnTopHint) != on_top:
            visible = self.isVisible()
            self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, on_top)
            if visible:
                self.show()

    def _toggle_fullscreen(self) -> None:
        if self.isFullScreen():
            self.showNormal()
        else:
            self.showFullScreen()

    def _about(self) -> None:
        QMessageBox.about(self, tr("about"),
                          tr("about_text").format(ver=__version__) + "<br><br>" + tr("shortcuts"))

    def closeEvent(self, event) -> None:
        if self._countdown_left > 0:
            self._cancel_countdown()
        if self.controller.is_recording() and not self._force_quit:
            if not self._close_after_stop:
                ans = QMessageBox.question(self, __app_name__, tr("confirm_exit"),
                                           QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                           QMessageBox.StandardButton.No)
                if ans != QMessageBox.StandardButton.Yes:
                    event.ignore()
                    return
                # Let the recorder finish writing the file, then close (with a safety timeout).
                self._close_after_stop = True
                self.controller.stop_recording()
                QTimer.singleShot(8000, self._force_close)
            event.ignore()
            return
        self.config.raw().setValue("window/geometry", self.saveGeometry())
        self.config.sync()
        self.controller.stop_camera()
        super().closeEvent(event)

    def _force_close(self) -> None:
        if self._close_after_stop and self.controller.is_recording():
            self._force_quit = True
            self.close()
