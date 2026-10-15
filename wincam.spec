# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec for WinCam.  Build with:  pyinstaller wincam.spec --noconfirm
import re
from pathlib import Path

import PySide6
from PyInstaller.utils.win32.versioninfo import (
    FixedFileInfo, StringFileInfo, StringStruct, StringTable, VarFileInfo, VarStruct, VSVersionInfo,
)

ROOT = Path(SPECPATH)
VERSION = re.search(r'__version__\s*=\s*"([^"]+)"', (ROOT / "wincam" / "__init__.py").read_text()).group(1)
nums = tuple(int(x) for x in (VERSION.split(".") + ["0", "0", "0"])[:4])

# Make sure the Qt Multimedia backends (FFmpeg + Windows Media Foundation) and FFmpeg DLLs are bundled.
pyside_dir = Path(PySide6.__file__).parent
extra_binaries = []
for pattern in ("avcodec-*.dll", "avformat-*.dll", "avutil-*.dll", "swresample-*.dll", "swscale-*.dll"):
    extra_binaries += [(str(p), "PySide6") for p in pyside_dir.glob(pattern)]
extra_binaries += [(str(p), "PySide6/plugins/multimedia") for p in (pyside_dir / "plugins" / "multimedia").glob("*.dll")]

version_info = VSVersionInfo(
    ffi=FixedFileInfo(filevers=nums, prodvers=nums),
    kids=[
        StringFileInfo([StringTable("080404b0", [
            StringStruct("CompanyName", "WinCam"),
            StringStruct("FileDescription", "WinCam 摄像头录像"),
            StringStruct("FileVersion", VERSION),
            StringStruct("InternalName", "WinCam"),
            StringStruct("OriginalFilename", "WinCam.exe"),
            StringStruct("ProductName", "WinCam"),
            StringStruct("ProductVersion", VERSION),
        ])]),
        VarFileInfo([VarStruct("Translation", [0x0804, 1200])]),
    ],
)

a = Analysis(
    ["run.py"],
    pathex=[str(ROOT)],
    binaries=extra_binaries,
    datas=[("wincam/resources", "wincam/resources")],
    hiddenimports=["PySide6.QtMultimedia", "PySide6.QtMultimediaWidgets"],
    excludes=[
        "tkinter", "unittest", "pydoc", "PySide6.QtWebEngineCore", "PySide6.QtWebEngineWidgets",
        "PySide6.QtQuick3D", "PySide6.Qt3DCore", "PySide6.QtPdf", "PySide6.QtCharts",
        "PySide6.QtDataVisualization", "PySide6.QtGraphs", "PySide6.QtDesigner",
    ],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="WinCam",
    icon=str(ROOT / "wincam" / "resources" / "wincam.ico"),
    version=version_info,
    console=False,
    disable_windowed_traceback=False,
    upx=False,
)
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name="WinCam")
