"""CI helper: print small crops of Windows screenshots as base64 so they can be checked from the job log.

usage: python tools/ci_screens.py <screenshot.png> [<screenshot2.png> ...]
"""

import base64
import io
import sys

from PIL import Image


def emit(label: str, img: Image.Image, fmt: str = "PNG") -> None:
    buf = io.BytesIO()
    img.save(buf, fmt, **({"quality": 45} if fmt == "JPEG" else {"optimize": True}))
    print(f"=====BEGIN {label} {fmt}=====")
    data = base64.b64encode(buf.getvalue()).decode()
    for i in range(0, len(data), 3000):
        print(data[i:i + 3000])
    print(f"=====END {label}=====")


for path in sys.argv[1:]:
    im = Image.open(path).convert("RGB")
    w, h = im.size
    name = path.replace("\\", "/").rsplit("/", 1)[-1].rsplit(".", 1)[0]
    emit(f"{name}-taskbar", im.crop((0, h - 56, w, h)))
    emit(f"{name}-corner", im.crop((w - 420, h - 260, w, h)))
    small = im.copy()
    small.thumbnail((560, 560))
    emit(f"{name}-full", small, "JPEG")
