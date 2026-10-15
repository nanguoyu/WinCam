"""Record a short synthetic clip (generated video + audio) through the real recorder pipeline.

Needs no camera or microphone, so it runs in CI on Windows (real Media Foundation / FFmpeg encoders) and in tests.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

from PySide6.QtCore import QEventLoop, QSize, QTimer, QUrl
from PySide6.QtGui import QColor, QImage
from PySide6.QtMultimedia import (
    QAudioBuffer,
    QAudioBufferInput,
    QAudioFormat,
    QMediaCaptureSession,
    QMediaRecorder,
    QVideoFrame,
    QVideoFrameInput,
)

from wincam.capture import RecordOptions, configure_recorder


@dataclass
class RecordResult:
    ok: bool
    errors: list[str]
    size: int


def record_synthetic(path: str, opts: RecordOptions, width: int = 640, height: int = 480, fps: int = 30,
                     seconds: float = 2.0, audio: bool = True, timeout_s: float = 30.0) -> RecordResult:
    if os.path.exists(path):
        os.remove(path)
    session = QMediaCaptureSession()
    recorder = QMediaRecorder()
    session.setRecorder(recorder)
    video_in = QVideoFrameInput()
    session.setVideoFrameInput(video_in)
    audio_in = QAudioBufferInput() if audio else None
    if audio_in is not None:
        session.setAudioBufferInput(audio_in)

    configure_recorder(recorder, opts, QSize(width, height), fps)
    recorder.setOutputLocation(QUrl.fromLocalFile(path))

    errors: list[str] = []
    loop = QEventLoop()
    recorder.errorOccurred.connect(lambda _e, msg: errors.append(msg))
    recorder.recorderStateChanged.connect(
        lambda st: st == QMediaRecorder.RecorderState.StoppedState and QTimer.singleShot(100, loop.quit))

    afmt = QAudioFormat()
    afmt.setSampleRate(48000)
    afmt.setChannelCount(1)  # many webcam mics are mono
    afmt.setSampleFormat(QAudioFormat.SampleFormat.Int16)
    samples_per_frame = 48000 // fps
    silence = bytes(2 * samples_per_frame)

    total = int(seconds * fps)
    frame_us = 1_000_000 // fps
    count = [0]

    def push() -> None:
        i = count[0]
        if i >= total:
            pusher.stop()
            recorder.stop()
            return
        img = QImage(width, height, QImage.Format.Format_RGB32)
        img.fill(QColor.fromHsv((i * 6) % 360, 160, 200))
        frame = QVideoFrame(img)
        frame.setStartTime(i * frame_us)
        frame.setEndTime((i + 1) * frame_us)
        video_in.sendVideoFrame(frame)
        if audio_in is not None:
            audio_in.sendAudioBuffer(QAudioBuffer(silence, afmt, i * frame_us))
        count[0] += 1

    pusher = QTimer()
    pusher.timeout.connect(push)
    recorder.record()
    pusher.start(5)
    QTimer.singleShot(int(timeout_s * 1000), loop.quit)
    if recorder.recorderState() != QMediaRecorder.RecorderState.StoppedState or not errors:
        loop.exec()
    pusher.stop()
    if recorder.recorderState() != QMediaRecorder.RecorderState.StoppedState:
        errors.append("timed out")
        recorder.stop()

    size = os.path.getsize(path) if os.path.exists(path) else 0
    return RecordResult(ok=not errors and size > 0, errors=errors, size=size)
