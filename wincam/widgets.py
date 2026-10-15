"""Custom widgets: camera preview with overlays and the big record button."""

from __future__ import annotations

from PySide6.QtCore import QRectF, QSize, QSizeF, Qt, Signal
from PySide6.QtGui import QColor, QFont, QPainter, QPen, QTransform
from PySide6.QtMultimediaWidgets import QGraphicsVideoItem
from PySide6.QtWidgets import QAbstractButton, QFrame, QGraphicsScene, QGraphicsView

RED = QColor("#e5484d")


class PreviewView(QGraphicsView):
    """Shows the live camera picture (optionally mirrored) plus REC / countdown overlays."""

    doubleClicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setBackgroundBrush(QColor("#000000"))
        self.setViewportUpdateMode(QGraphicsView.ViewportUpdateMode.FullViewportUpdate)
        self.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        self.setMinimumSize(320, 180)

        self._scene = QGraphicsScene(self)
        self.setScene(self._scene)
        self.video_item = QGraphicsVideoItem()
        self.video_item.setAspectRatioMode(Qt.AspectRatioMode.KeepAspectRatio)
        self._scene.addItem(self.video_item)
        self.video_item.nativeSizeChanged.connect(lambda _s: self._layout())

        self._mirror = False
        self._message = ""
        self._rec_text = ""
        self._rec_paused = False
        self._rec_blink = True
        self._countdown = 0
        self._info = ""

    # --- public API -------------------------------------------------------
    def set_mirror(self, on: bool) -> None:
        self._mirror = bool(on)
        self._layout()

    def set_message(self, text: str) -> None:
        """Centered placeholder text (e.g. 'no camera'). Empty string hides it."""
        self._message = text
        self.video_item.setVisible(not text)
        self.viewport().update()

    def set_recording(self, text: str, paused: bool = False, blink: bool = True) -> None:
        self._rec_text = text
        self._rec_paused = paused
        self._rec_blink = blink
        self.viewport().update()

    def set_countdown(self, seconds: int) -> None:
        self._countdown = seconds
        self.viewport().update()

    def set_info(self, text: str) -> None:
        self._info = text
        self.viewport().update()

    # --- layout / painting ------------------------------------------------
    def _layout(self) -> None:
        r = self.viewport().rect()
        self._scene.setSceneRect(0, 0, r.width(), r.height())
        self.video_item.setPos(0, 0)
        self.video_item.setSize(QSizeF(r.width(), r.height()))
        if self._mirror:
            self.video_item.setTransform(QTransform(-1, 0, 0, 1, r.width(), 0))
        else:
            self.video_item.setTransform(QTransform())
        self.viewport().update()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._layout()

    def showEvent(self, event):
        super().showEvent(event)
        self._layout()

    def mouseDoubleClickEvent(self, event):
        self.doubleClicked.emit()
        super().mouseDoubleClickEvent(event)

    def drawForeground(self, painter: QPainter, rect) -> None:
        painter.save()
        painter.resetTransform()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        vr = self.viewport().rect()

        if self._message:
            painter.setPen(QColor("#9aa0a6"))
            f = QFont(self.font())
            f.setPointSizeF(f.pointSizeF() * 1.15)
            painter.setFont(f)
            painter.drawText(vr.adjusted(24, 24, -24, -24), Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap,
                             self._message)

        if self._rec_text:
            f = QFont(self.font())
            f.setBold(True)
            f.setPointSizeF(f.pointSizeF() * 1.2)
            painter.setFont(f)
            fm = painter.fontMetrics()
            label = self._rec_text
            w = fm.horizontalAdvance(label) + 44
            h = fm.height() + 14
            pill = QRectF(vr.width() - w - 16, 16, w, h)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(0, 0, 0, 150))
            painter.drawRoundedRect(pill, h / 2, h / 2)
            dot_c = pill.left() + 18, pill.center().y()
            if self._rec_paused:
                painter.setBrush(QColor("#f5a524"))
                painter.drawRect(QRectF(dot_c[0] - 5, dot_c[1] - 5, 3.5, 10))
                painter.drawRect(QRectF(dot_c[0] + 1.5, dot_c[1] - 5, 3.5, 10))
            elif self._rec_blink:
                painter.setBrush(RED)
                painter.drawEllipse(QRectF(dot_c[0] - 6, dot_c[1] - 6, 12, 12))
            painter.setPen(QColor("#ffffff"))
            painter.drawText(pill.adjusted(32, 0, -12, 0), Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
                             label)

        if self._info and not self._message:
            f = QFont(self.font())
            f.setPointSizeF(max(7.5, f.pointSizeF() * 0.9))
            painter.setFont(f)
            fm = painter.fontMetrics()
            w = fm.horizontalAdvance(self._info) + 20
            h = fm.height() + 8
            box = QRectF(12, vr.height() - h - 12, w, h)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(0, 0, 0, 120))
            painter.drawRoundedRect(box, 6, 6)
            painter.setPen(QColor("#d0d3d8"))
            painter.drawText(box, Qt.AlignmentFlag.AlignCenter, self._info)

        if self._countdown > 0:
            d = min(vr.width(), vr.height()) * 0.36
            circle = QRectF(vr.center().x() - d / 2, vr.center().y() - d / 2, d, d)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(0, 0, 0, 140))
            painter.drawEllipse(circle)
            f = QFont(self.font())
            f.setBold(True)
            f.setPixelSize(max(12, int(d * 0.55)))
            painter.setFont(f)
            painter.setPen(QColor("#ffffff"))
            painter.drawText(circle, Qt.AlignmentFlag.AlignCenter, str(self._countdown))

        painter.restore()


class RecordButton(QAbstractButton):
    """Large round record button: red dot when idle, red rounded square while recording."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.TabFocus)
        self._hover = False
        self._pending = False  # countdown in progress

    def nextCheckState(self) -> None:
        """Clicking must not toggle the look; the checked state follows the recorder state only."""

    def set_pending(self, on: bool) -> None:
        self._pending = on
        self.update()

    def sizeHint(self) -> QSize:
        return QSize(64, 64)

    def enterEvent(self, event):
        self._hover = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._hover = False
        self.update()
        super().leaveEvent(event)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        side = min(self.width(), self.height()) - 4
        outer = QRectF((self.width() - side) / 2, (self.height() - side) / 2, side, side)

        ring = QColor("#ffffff") if self.isEnabled() else QColor("#5f6368")
        if self._hover and self.isEnabled():
            ring = QColor("#ffffff")
            p.setBrush(QColor(255, 255, 255, 25))
        else:
            p.setBrush(Qt.BrushStyle.NoBrush)
        p.setPen(QPen(ring, 3))
        p.drawEllipse(outer.adjusted(1.5, 1.5, -1.5, -1.5))

        fill = RED if self.isEnabled() else QColor("#5f6368")
        if self._hover and self.isEnabled():
            fill = fill.lighter(112)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(fill)
        if self.isChecked():
            s = side * 0.36
            p.drawRoundedRect(QRectF(outer.center().x() - s / 2, outer.center().y() - s / 2, s, s), s * 0.18, s * 0.18)
        else:
            inset = side * (0.2 if not self._pending else 0.26)
            p.drawEllipse(outer.adjusted(inset, inset, -inset, -inset))

        if self.hasFocus():
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.setPen(QPen(QColor("#8ab4f8"), 1.5, Qt.PenStyle.DotLine))
            p.drawEllipse(outer)
        p.end()
