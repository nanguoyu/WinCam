"""Very small translation table (Chinese / English)."""

from __future__ import annotations

_LANG = "zh"

LANGUAGES = {"zh": "简体中文", "en": "English"}

_STRINGS: dict[str, tuple[str, str]] = {
    # key: (zh, en)
    "camera": ("摄像头", "Camera"),
    "resolution": ("分辨率", "Resolution"),
    "microphone": ("麦克风", "Microphone"),
    "no_audio": ("不录制声音", "No audio"),
    "no_camera": ("未检测到摄像头", "No camera found"),
    "no_camera_hint": ("未检测到摄像头\n请连接 USB 摄像头，或在 Windows 设置 → 隐私 → 相机 中允许桌面应用访问相机",
                       "No camera detected\nPlug in a USB camera, or allow desktop apps to use the camera in\nWindows Settings → Privacy → Camera"),
    "auto": ("自动", "Auto"),
    "default_suffix": ("（默认）", " (default)"),
    "builtin": ("内置", "Built-in"),
    "external": ("USB/外接", "USB/External"),
    "settings": ("设置", "Settings"),
    "refresh": ("刷新设备", "Refresh devices"),
    "record": ("开始录制", "Start recording"),
    "stop": ("停止录制", "Stop recording"),
    "pause": ("暂停", "Pause"),
    "resume": ("继续", "Resume"),
    "snapshot": ("拍照", "Snapshot"),
    "open_folder": ("打开保存目录", "Open save folder"),
    "change_folder": ("更改…", "Change…"),
    "save_to": ("保存到：", "Save to:"),
    "choose_folder": ("选择保存目录", "Choose save folder"),
    "ready": ("就绪", "Ready"),
    "recording": ("录制中", "Recording"),
    "paused": ("已暂停", "Paused"),
    "saved_to": ("已保存：{}", "Saved: {}"),
    "snapshot_saved": ("照片已保存：{}", "Snapshot saved: {}"),
    "free_space": ("可用空间 {}", "Free {}"),
    "low_space": ("磁盘空间不足（剩余 {}）", "Low disk space ({} left)"),
    "error": ("错误", "Error"),
    "camera_error": ("摄像头错误：{}\n\n如果摄像头被其他程序占用，请先关闭该程序；\n或检查 Windows 设置 → 隐私和安全性 → 相机。",
                     "Camera error: {}\n\nClose other apps that may be using the camera, or check\nWindows Settings → Privacy & security → Camera."),
    "recorder_error": ("录制错误：{}", "Recording error: {}"),
    "folder_error": ("无法创建保存目录：{}", "Cannot create save folder: {}"),
    "confirm_exit": ("正在录制，确定要停止录制并退出吗？", "Recording is in progress. Stop and exit?"),
    "exit": ("退出", "Exit"),
    "countdown_cancel": ("倒计时中…再次点击取消", "Counting down… click again to cancel"),
    "about": ("关于", "About"),
    "about_text": ("<b>WinCam {ver}</b><br>简洁易用的摄像头录像软件<br>适用于 Windows 10 / 11",
                   "<b>WinCam {ver}</b><br>A simple webcam recorder<br>for Windows 10 / 11"),
    "shortcuts": ("快捷键：F9 开始/停止 · F10 暂停/继续 · F8 拍照",
                  "Shortcuts: F9 start/stop · F10 pause/resume · F8 snapshot"),
    # settings dialog
    "tab_general": ("常规", "General"),
    "tab_video": ("视频", "Video"),
    "tab_audio": ("音频", "Audio"),
    "save_dir": ("保存目录", "Save folder"),
    "browse": ("浏览…", "Browse…"),
    "file_prefix": ("文件名前缀", "File name prefix"),
    "file_example": ("示例：{}", "Example: {}"),
    "language": ("界面语言", "Language"),
    "language_restart": ("（重启后生效）", " (applies after restart)"),
    "countdown": ("录制前倒计时", "Countdown before recording"),
    "seconds_off": ("关闭", "Off"),
    "seconds": (" 秒", " s"),
    "max_minutes": ("自动停止录制", "Auto stop after"),
    "minutes": (" 分钟", " min"),
    "open_after": ("录制完成后打开所在文件夹", "Open folder when recording finishes"),
    "always_on_top": ("窗口置顶", "Always on top"),
    "mirror": ("镜像预览（像照镜子一样，不影响录制文件）", "Mirror preview (does not affect the recording)"),
    "container": ("文件格式", "File format"),
    "video_codec": ("视频编码", "Video codec"),
    "quality": ("画质", "Quality"),
    "bitrate": ("码率", "Bitrate"),
    "bitrate_auto": ("自动（按画质）", "Auto (by quality)"),
    "snapshot_format": ("照片格式", "Snapshot format"),
    "audio_codec": ("音频编码", "Audio codec"),
    "volume": ("录音音量", "Input volume"),
    "q_VeryLowQuality": ("很低（文件最小）", "Very low (smallest file)"),
    "q_LowQuality": ("低", "Low"),
    "q_NormalQuality": ("标准", "Normal"),
    "q_HighQuality": ("高（推荐）", "High (recommended)"),
    "q_VeryHighQuality": ("很高（文件较大）", "Very high (large file)"),
    "restore_defaults": ("恢复默认", "Restore defaults"),
    "ok": ("确定", "OK"),
    "cancel": ("取消", "Cancel"),
}


def set_language(lang: str) -> None:
    global _LANG
    _LANG = lang if lang in LANGUAGES else "en"


def language() -> str:
    return _LANG


def tr(key: str, *args) -> str:
    pair = _STRINGS.get(key)
    if pair is None:
        return key
    text = pair[0] if _LANG == "zh" else pair[1]
    return text.format(*args) if args else text
