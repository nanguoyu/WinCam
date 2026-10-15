"""Camera / microphone / recorder plumbing on top of Qt Multimedia."""

from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import QObject, QUrl, Signal
from PySide6.QtGui import QImage
from PySide6.QtMultimedia import (
    QAudioDevice,
    QAudioInput,
    QCamera,
    QCameraDevice,
    QCameraFormat,
    QImageCapture,
    QMediaCaptureSession,
    QMediaDevices,
    QMediaFormat,
    QMediaRecorder,
    QVideoFrameFormat,
)

from wincam.utils import format_key

ENCODE = QMediaFormat.ConversionMode.Encode

# Uncompressed formats first: cheaper to process than MJPEG at the same size/fps.
_PIXEL_PREFERENCE = {
    QVideoFrameFormat.PixelFormat.Format_NV12: 0,
    QVideoFrameFormat.PixelFormat.Format_YUYV: 1,
    QVideoFrameFormat.PixelFormat.Format_UYVY: 2,
    QVideoFrameFormat.PixelFormat.Format_YUV420P: 3,
    QVideoFrameFormat.PixelFormat.Format_Jpeg: 9,
}


def device_key(dev: QCameraDevice | QAudioDevice) -> str:
    return bytes(dev.id().data()).hex()


def find_camera(key: str) -> QCameraDevice | None:
    cams = QMediaDevices.videoInputs()
    for c in cams:
        if device_key(c) == key:
            return c
    return None


def find_audio_input(key: str) -> QAudioDevice | None:
    for a in QMediaDevices.audioInputs():
        if device_key(a) == key:
            return a
    return None


def is_builtin(dev: QCameraDevice) -> bool:
    if dev.position() in (QCameraDevice.Position.FrontFace, QCameraDevice.Position.BackFace):
        return True
    name = dev.description().lower()
    return any(w in name for w in ("integrated", "built-in", "builtin", "facetime"))


@dataclass(frozen=True)
class FormatChoice:
    key: str
    width: int
    height: int
    fps: float
    fmt: QCameraFormat


def camera_formats(dev: QCameraDevice) -> list[FormatChoice]:
    """Distinct (resolution, fps) choices, best first."""
    best: dict[str, tuple[int, QCameraFormat]] = {}
    for f in dev.videoFormats():
        size = f.resolution()
        fps = round(f.maxFrameRate(), 2)
        if size.isEmpty() or fps <= 0:
            continue
        key = format_key(size.width(), size.height(), fps)
        pref = _PIXEL_PREFERENCE.get(f.pixelFormat(), 5)
        if key not in best or pref < best[key][0]:
            best[key] = (pref, f)
    out = [FormatChoice(k, f.resolution().width(), f.resolution().height(), round(f.maxFrameRate(), 2), f)
           for k, (_p, f) in best.items()]
    out.sort(key=lambda c: (c.width * c.height, c.fps), reverse=True)
    return out


def auto_format(choices: list[FormatChoice]) -> FormatChoice | None:
    """Pick a sensible default: largest picture up to 1080p that still runs at >= 25 fps."""
    if not choices:
        return None
    smooth = [c for c in choices if c.fps >= 24.5 and c.width * c.height <= 1920 * 1080]
    if smooth:
        return max(smooth, key=lambda c: (c.width * c.height, c.fps))
    return max(choices, key=lambda c: (c.fps >= 14.5, c.width * c.height, c.fps))


def supported_containers() -> list[QMediaFormat.FileFormat]:
    video_capable = []
    for ff in QMediaFormat().supportedFileFormats(ENCODE):
        if QMediaFormat(ff).supportedVideoCodecs(ENCODE):
            video_capable.append(ff)
    return video_capable


def supported_video_codecs(container: QMediaFormat.FileFormat) -> list[QMediaFormat.VideoCodec]:
    return list(QMediaFormat(container).supportedVideoCodecs(ENCODE))


def supported_audio_codecs(container: QMediaFormat.FileFormat) -> list[QMediaFormat.AudioCodec]:
    return list(QMediaFormat(container).supportedAudioCodecs(ENCODE))


def enum_by_name(enum_cls, name: str, default):
    try:
        return enum_cls[name]
    except (KeyError, TypeError):
        return default


def container_suffix(container: QMediaFormat.FileFormat) -> str:
    suffix = QMediaFormat(container).mimeType().preferredSuffix()
    if suffix:
        return suffix
    return {
        QMediaFormat.FileFormat.MPEG4: "mp4",
        QMediaFormat.FileFormat.Matroska: "mkv",
        QMediaFormat.FileFormat.AVI: "avi",
        QMediaFormat.FileFormat.WMV: "wmv",
        QMediaFormat.FileFormat.QuickTime: "mov",
        QMediaFormat.FileFormat.WebM: "webm",
        QMediaFormat.FileFormat.Ogg: "ogv",
    }.get(container, "mp4")


@dataclass
class RecordOptions:
    container: QMediaFormat.FileFormat = QMediaFormat.FileFormat.MPEG4
    video_codec: QMediaFormat.VideoCodec = QMediaFormat.VideoCodec.Unspecified
    audio_codec: QMediaFormat.AudioCodec = QMediaFormat.AudioCodec.Unspecified
    quality: QMediaRecorder.Quality = QMediaRecorder.Quality.HighQuality
    bitrate_kbps: int = 0


class CaptureController(QObject):
    errorOccurred = Signal(str, str)          # kind ("camera"/"recorder"/"snapshot"), message
    recorderStateChanged = Signal(QMediaRecorder.RecorderState)
    durationChanged = Signal("qint64")         # ms
    recordingSaved = Signal(str)               # file path
    snapshotSaved = Signal(str)
    cameraActiveChanged = Signal(bool)

    def __init__(self, video_output: QObject, parent=None):
        super().__init__(parent)
        self.session = QMediaCaptureSession(self)
        self.session.setVideoOutput(video_output)
        self._video_output = video_output

        self.camera: QCamera | None = None
        self.audio_input: QAudioInput | None = None
        self._volume = 1.0

        self.recorder = QMediaRecorder(self)
        self.session.setRecorder(self.recorder)
        self.recorder.recorderStateChanged.connect(self._on_recorder_state)
        self.recorder.durationChanged.connect(lambda ms: self.durationChanged.emit(int(ms)))
        self.recorder.errorOccurred.connect(lambda _e, msg: self.errorOccurred.emit("recorder", msg))

        self.image_capture = QImageCapture(self)
        self.session.setImageCapture(self.image_capture)
        self.image_capture.imageSaved.connect(lambda _id, path: self.snapshotSaved.emit(path))
        self.image_capture.errorOccurred.connect(lambda _id, _e, msg: self.errorOccurred.emit("snapshot", msg))

        self._recording_path = ""

    # --- camera -----------------------------------------------------------
    def set_camera(self, dev: QCameraDevice | None, fmt: QCameraFormat | None) -> None:
        if self.camera is not None:
            self.camera.stop()
            self.session.setCamera(None)
            self.camera.deleteLater()
            self.camera = None
        if dev is None or dev.isNull():
            self.cameraActiveChanged.emit(False)
            return
        cam = QCamera(dev, self)
        if fmt is not None and not fmt.isNull():
            cam.setCameraFormat(fmt)
        cam.errorOccurred.connect(lambda _e, msg: self.errorOccurred.emit("camera", msg))
        cam.activeChanged.connect(self.cameraActiveChanged)
        self.session.setCamera(cam)
        self.camera = cam
        cam.start()

    def stop_camera(self) -> None:
        self.set_camera(None, None)

    def camera_active(self) -> bool:
        return self.camera is not None and self.camera.isActive()

    # --- audio ------------------------------------------------------------
    def set_audio_input(self, dev: QAudioDevice | None) -> None:
        if dev is None:
            self.session.setAudioInput(None)
            if self.audio_input is not None:
                self.audio_input.deleteLater()
            self.audio_input = None
            return
        if self.audio_input is None:
            self.audio_input = QAudioInput(self)
            self.audio_input.setVolume(self._volume)
            self.session.setAudioInput(self.audio_input)
        self.audio_input.setDevice(dev)

    def set_volume(self, percent: int) -> None:
        self._volume = max(0.0, min(1.0, percent / 100.0))
        if self.audio_input is not None:
            self.audio_input.setVolume(self._volume)

    # --- recording --------------------------------------------------------
    def is_recording(self) -> bool:
        return self.recorder.recorderState() != QMediaRecorder.RecorderState.StoppedState

    def is_paused(self) -> bool:
        return self.recorder.recorderState() == QMediaRecorder.RecorderState.PausedState

    def start_recording(self, path: str, opts: RecordOptions) -> None:
        fmt = QMediaFormat(opts.container)
        if opts.video_codec != QMediaFormat.VideoCodec.Unspecified \
                and opts.video_codec in supported_video_codecs(opts.container):
            fmt.setVideoCodec(opts.video_codec)
        if opts.audio_codec != QMediaFormat.AudioCodec.Unspecified \
                and opts.audio_codec in supported_audio_codecs(opts.container):
            fmt.setAudioCodec(opts.audio_codec)
        self.recorder.setMediaFormat(fmt)
        self.recorder.setQuality(opts.quality)
        if opts.bitrate_kbps > 0:
            self.recorder.setEncodingMode(QMediaRecorder.EncodingMode.AverageBitRateEncoding)
            self.recorder.setVideoBitRate(opts.bitrate_kbps * 1000)
        else:
            self.recorder.setEncodingMode(QMediaRecorder.EncodingMode.ConstantQualityEncoding)
            self.recorder.setVideoBitRate(-1)
        if self.camera is not None:
            cf = self.camera.cameraFormat()
            if not cf.isNull():
                self.recorder.setVideoResolution(cf.resolution())
                self.recorder.setVideoFrameRate(cf.maxFrameRate())
        self._recording_path = path
        self.recorder.setOutputLocation(QUrl.fromLocalFile(path))
        self.recorder.record()

    def stop_recording(self) -> None:
        if self.is_recording():
            self.recorder.stop()

    def toggle_pause(self) -> None:
        st = self.recorder.recorderState()
        if st == QMediaRecorder.RecorderState.RecordingState:
            self.recorder.pause()
        elif st == QMediaRecorder.RecorderState.PausedState:
            self.recorder.record()

    def _on_recorder_state(self, state: QMediaRecorder.RecorderState) -> None:
        self.recorderStateChanged.emit(state)
        if state == QMediaRecorder.RecorderState.StoppedState and self._recording_path:
            actual = self.recorder.actualLocation()
            path = actual.toLocalFile() if actual.isValid() and actual.isLocalFile() else self._recording_path
            self._recording_path = ""
            if self.recorder.error() == QMediaRecorder.Error.NoError:
                self.recordingSaved.emit(path)

    # --- snapshot ---------------------------------------------------------
    def capture_snapshot(self, path: str) -> None:
        if self.image_capture.isReadyForCapture():
            fmt = QImageCapture.FileFormat.PNG if path.lower().endswith(".png") else QImageCapture.FileFormat.JPEG
            self.image_capture.setFileFormat(fmt)
            self.image_capture.captureToFile(path)
            return
        # Fallback: grab the last frame shown in the preview.
        sink = self._video_output.videoSink() if hasattr(self._video_output, "videoSink") else None
        img = sink.videoFrame().toImage() if sink is not None else QImage()
        if img.isNull():
            self.errorOccurred.emit("snapshot", "no video frame available")
            return
        if img.save(path, quality=95):
            self.snapshotSaved.emit(path)
        else:
            self.errorOccurred.emit("snapshot", f"cannot write {path}")
