"""End-to-end recording through the real Qt/FFmpeg encoders with synthetic video + audio (no devices needed)."""

import pytest
from PySide6.QtMultimedia import QMediaRecorder

from wincam import capture
from wincam.rectest import record_synthetic


@pytest.mark.parametrize("preset", capture.PRESETS, ids=lambda p: p.key)
def test_preset_records_with_audio(qapp, tmp_path, preset):
    # Regression: bitrate presets used to leave the audio bitrate at -1 -> "Cannot open any audio codec".
    opts = capture.RecordOptions(bitrate_kbps=preset.bitrate_kbps)
    res = record_synthetic(str(tmp_path / f"{preset.key}.mp4"), opts, width=640, height=480, seconds=1)
    assert res.ok, res.errors
    assert res.size > 0


def test_custom_auto_bitrate_records_with_audio(qapp, tmp_path):
    opts = capture.RecordOptions(bitrate_kbps=0, quality=QMediaRecorder.Quality.NormalQuality)
    res = record_synthetic(str(tmp_path / "custom.mp4"), opts, seconds=1)
    assert res.ok, res.errors


def test_records_without_audio(qapp, tmp_path):
    res = record_synthetic(str(tmp_path / "silent.mp4"), capture.RecordOptions(bitrate_kbps=1500), audio=False,
                           seconds=1)
    assert res.ok, res.errors
