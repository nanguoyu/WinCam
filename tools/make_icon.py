"""Generate wincam/resources/wincam.png and wincam.ico (run once; outputs are committed).

The drawing lives in wincam.icons.render_app_icon so the exe icon and the runtime window icon match.
"""

import io
import sys
from pathlib import Path

from PIL import Image
from PySide6.QtCore import QBuffer, QIODevice
from PySide6.QtGui import QGuiApplication, QImage

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from wincam.icons import render_app_icon  # noqa: E402

OUT = Path(__file__).resolve().parent.parent / "wincam" / "resources"
SIZES = [16, 20, 24, 32, 40, 48, 64, 128, 256]


def to_pil(img: QImage) -> Image.Image:
    buf = QBuffer()
    buf.open(QIODevice.OpenModeFlag.WriteOnly)
    img.save(buf, "PNG")
    return Image.open(io.BytesIO(bytes(buf.data()))).convert("RGBA")


def main() -> None:
    QGuiApplication(sys.argv)
    OUT.mkdir(parents=True, exist_ok=True)
    frames = {s: to_pil(render_app_icon(s)) for s in SIZES}
    frames[256].save(OUT / "wincam.png")
    # Render every size natively (crisper than letting Pillow downscale the 256 px image).
    frames[256].save(OUT / "wincam.ico", format="ICO", sizes=[(s, s) for s in SIZES],
                     append_images=[frames[s] for s in SIZES[:-1]])
    print("written", OUT)


if __name__ == "__main__":
    main()
