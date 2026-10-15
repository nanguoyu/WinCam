from datetime import datetime

from wincam.utils import build_output_path, format_bytes, format_duration, free_space, sanitize_prefix


def test_format_duration():
    assert format_duration(0) == "00:00:00"
    assert format_duration(999) == "00:00:00"
    assert format_duration(61_000) == "00:01:01"
    assert format_duration(3_723_000) == "01:02:03"
    assert format_duration(-5) == "00:00:00"


def test_sanitize_prefix():
    assert sanitize_prefix('a<b>c:"d/e\\f|g?h*') == "a_b_c__d_e_f_g_h_"
    assert sanitize_prefix("  name. ") == "name"
    assert sanitize_prefix("") == ""


def test_build_output_path_unique(tmp_path):
    now = datetime(2026, 10, 15, 14, 30, 12)
    p1 = build_output_path(tmp_path, "WinCam", "mp4", now)
    assert p1.name == "WinCam_20261015_143012.mp4"
    p1.write_bytes(b"x")
    p2 = build_output_path(tmp_path, "WinCam", ".mp4", now)
    assert p2.name == "WinCam_20261015_143012_2.mp4"
    assert build_output_path(tmp_path, "", "jpg", now).name == "20261015_143012.jpg"


def test_format_bytes():
    assert format_bytes(500) == "500 B"
    assert format_bytes(1536) == "2 KB"
    assert format_bytes(5 * 1024**3) == "5.0 GB"


def test_free_space_walks_up(tmp_path):
    assert free_space(tmp_path / "does" / "not" / "exist") is not None
