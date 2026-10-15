"""Vector icons painted at runtime, so the app needs no icon font or image assets."""

from __future__ import annotations

import math
from functools import cache

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPainterPath, QPen, QPixmap

FG = QColor("#e8eaed")
DISABLED = QColor("#6b6f76")


def _paint(name: str, p: QPainter, color: QColor) -> None:
    """Draw icon ``name`` into a 24x24 logical box."""
    pen = QPen(color, 2.0, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
    p.setPen(pen)
    p.setBrush(Qt.BrushStyle.NoBrush)

    if name == "pause":
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(color)
        p.drawRoundedRect(QRectF(6, 5, 4, 14), 1.2, 1.2)
        p.drawRoundedRect(QRectF(14, 5, 4, 14), 1.2, 1.2)
    elif name == "play":
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(color)
        path = QPainterPath()
        path.moveTo(8, 5)
        path.lineTo(19, 12)
        path.lineTo(8, 19)
        path.closeSubpath()
        p.drawPath(path)
    elif name == "camera":  # photo camera (snapshot)
        path = QPainterPath()
        path.addRoundedRect(QRectF(3, 7, 18, 13), 2.5, 2.5)
        p.drawPath(path)
        p.drawLine(QPointF(8.5, 7), QPointF(10, 4.5))
        p.drawLine(QPointF(10, 4.5), QPointF(14, 4.5))
        p.drawLine(QPointF(14, 4.5), QPointF(15.5, 7))
        p.drawEllipse(QPointF(12, 13.5), 3.6, 3.6)
    elif name == "video":  # video camera
        p.drawRoundedRect(QRectF(3, 6.5, 12.5, 11), 2.2, 2.2)
        path = QPainterPath()
        path.moveTo(15.5, 10.5)
        path.lineTo(21, 7.5)
        path.lineTo(21, 16.5)
        path.lineTo(15.5, 13.5)
        p.drawPath(path)
    elif name == "mic":
        p.drawRoundedRect(QRectF(9, 3, 6, 11), 3, 3)
        path = QPainterPath()
        path.moveTo(5.5, 11)
        path.cubicTo(5.5, 19.5, 18.5, 19.5, 18.5, 11)
        p.drawPath(path)
        p.drawLine(QPointF(12, 17.5), QPointF(12, 21))
    elif name == "folder":
        path = QPainterPath()
        path.moveTo(3, 7)
        path.lineTo(3, 18)
        path.quadTo(3, 19.5, 4.5, 19.5)
        path.lineTo(19.5, 19.5)
        path.quadTo(21, 19.5, 21, 18)
        path.lineTo(21, 9.5)
        path.quadTo(21, 8, 19.5, 8)
        path.lineTo(11.5, 8)
        path.lineTo(9.5, 5.5)
        path.lineTo(4.5, 5.5)
        path.quadTo(3, 5.5, 3, 7)
        p.drawPath(path)
    elif name == "gear":
        path = QPainterPath()
        teeth = 8
        for i in range(teeth * 2):
            a0 = (i / (teeth * 2)) * 2 * math.pi
            a1 = ((i + 1) / (teeth * 2)) * 2 * math.pi
            r = 9.0 if i % 2 == 0 else 6.8
            pt0 = QPointF(12 + r * math.cos(a0), 12 + r * math.sin(a0))
            pt1 = QPointF(12 + r * math.cos(a1), 12 + r * math.sin(a1))
            if i == 0:
                path.moveTo(pt0)
            else:
                path.lineTo(pt0)
            path.lineTo(pt1)
        path.closeSubpath()
        p.setPen(QPen(color, 1.7, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
        p.drawPath(path)
        p.drawEllipse(QPointF(12, 12), 2.8, 2.8)
    elif name == "refresh":
        rect = QRectF(4.5, 4.5, 15, 15)
        path = QPainterPath()
        path.arcMoveTo(rect, 60)
        path.arcTo(rect, 60, 270)
        p.drawPath(path)
        # arrow head at the arc start (60 deg)
        tip = QPointF(12 + 7.5 * math.cos(math.radians(60)), 12 - 7.5 * math.sin(math.radians(60)))
        p.drawLine(tip, tip + QPointF(-4.2, -0.6))
        p.drawLine(tip, tip + QPointF(-0.4, 4.2))
    elif name == "info":
        p.drawEllipse(QPointF(12, 12), 9, 9)
        p.drawLine(QPointF(12, 11), QPointF(12, 16.5))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(color)
        p.drawEllipse(QPointF(12, 7.8), 1.3, 1.3)
    else:
        raise KeyError(name)


def _pixmap(name: str, size: int, color: QColor) -> QPixmap:
    pm = QPixmap(size, size)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.scale(size / 24.0, size / 24.0)
    _paint(name, p, color)
    p.end()
    return pm


@cache
def icon(name: str) -> QIcon:
    ic = QIcon()
    for size in (16, 20, 24, 32, 48, 64):
        ic.addPixmap(_pixmap(name, size, FG), QIcon.Mode.Normal)
        ic.addPixmap(_pixmap(name, size, DISABLED), QIcon.Mode.Disabled)
    return ic
