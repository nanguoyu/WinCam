"""Generate wincam/resources/wincam.png and wincam.ico (run once; outputs are committed)."""

import io
import sys
from pathlib import Path

from PIL import Image
from PySide6.QtCore import QBuffer, QIODevice, QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QGuiApplication, QImage, QLinearGradient, QPainter, QRadialGradient

OUT = Path(__file__).resolve().parent.parent / "wincam" / "resources"


def render(size: int) -> QImage:
    img = QImage(size, size, QImage.Format.Format_ARGB32)
    img.fill(Qt.GlobalColor.transparent)
    p = QPainter(img)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.scale(size / 256.0, size / 256.0)

    bg = QLinearGradient(0, 0, 256, 256)
    bg.setColorAt(0, QColor("#4f8cff"))
    bg.setColorAt(1, QColor("#2a4fd6"))
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(bg)
    p.drawRoundedRect(QRectF(12, 12, 232, 232), 54, 54)

    # lens
    p.setBrush(QColor("#ffffff"))
    p.drawEllipse(QPointF(128, 128), 76, 76)
    p.setBrush(QColor("#1d2633"))
    p.drawEllipse(QPointF(128, 128), 58, 58)
    glass = QRadialGradient(QPointF(112, 110), 60)
    glass.setColorAt(0, QColor("#4a6a9a"))
    glass.setColorAt(1, QColor("#101722"))
    p.setBrush(glass)
    p.drawEllipse(QPointF(128, 128), 40, 40)
    p.setBrush(QColor(255, 255, 255, 170))
    p.drawEllipse(QPointF(112, 112), 11, 11)

    # record dot
    p.setBrush(QColor("#ffffff"))
    p.drawEllipse(QPointF(200, 56), 26, 26)
    p.setBrush(QColor("#e5484d"))
    p.drawEllipse(QPointF(200, 56), 19, 19)
    p.end()
    return img


def to_pil(img: QImage) -> Image.Image:
    buf = QBuffer()
    buf.open(QIODevice.OpenModeFlag.WriteOnly)
    img.save(buf, "PNG")
    return Image.open(io.BytesIO(bytes(buf.data())))


def main() -> None:
    QGuiApplication(sys.argv)
    OUT.mkdir(parents=True, exist_ok=True)
    big = to_pil(render(256))
    big.save(OUT / "wincam.png")
    big.save(OUT / "wincam.ico", sizes=[(16, 16), (20, 20), (24, 24), (32, 32), (40, 40), (48, 48),
                                        (64, 64), (128, 128), (256, 256)])
    print("written", OUT)


if __name__ == "__main__":
    main()
