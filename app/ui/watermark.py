"""Red header/footer bar with a faint patriotic watermark (star + the
hammer-and-sickle emblem image) painted low-opacity into the background."""

from __future__ import annotations

import math

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QLinearGradient, QPainter, QPainterPath, QPixmap
from PySide6.QtWidgets import QFrame

from ..paths import ASSETS_DIR

BAR_GRADIENT_START = "#D42E2E"
BAR_GRADIENT_END = "#8E0E0E"

_PARTY_EMBLEM_PATH = ASSETS_DIR / "party_emblem.png"
_party_emblem_pixmap: QPixmap | None = None


def _star_path(cx: float, cy: float, outer_r: float) -> QPainterPath:
    inner_r = outer_r * 0.382
    path = QPainterPath()
    for i in range(10):
        r = outer_r if i % 2 == 0 else inner_r
        angle = math.radians(-90 + i * 36)
        x, y = cx + r * math.cos(angle), cy + r * math.sin(angle)
        if i == 0:
            path.moveTo(x, y)
        else:
            path.lineTo(x, y)
    path.closeSubpath()
    return path


def _party_emblem_pixmap_cached() -> QPixmap:
    global _party_emblem_pixmap
    if _party_emblem_pixmap is None:
        _party_emblem_pixmap = (
            QPixmap(str(_PARTY_EMBLEM_PATH)) if _PARTY_EMBLEM_PATH.exists() else QPixmap()
        )
    return _party_emblem_pixmap


class GradientBar(QFrame):
    """A red-gradient bar used for the app header/footer, with a faint
    patriotic watermark painted into the empty space."""

    def __init__(self, motifs=(), corner_radius: int = 0, align: str = "right", parent=None):
        super().__init__(parent)
        self._motifs = list(motifs)
        self._corner_radius = corner_radius
        self._align = align

    def paintEvent(self, event):  # noqa: N802 - Qt override
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        rect = QRectF(self.rect())

        clip = QPainterPath()
        if self._corner_radius:
            clip.addRoundedRect(rect, self._corner_radius, self._corner_radius)
        else:
            clip.addRect(rect)
        painter.setClipPath(clip)

        gradient = QLinearGradient(rect.topLeft(), rect.topRight())
        gradient.setColorAt(0.0, QColor(BAR_GRADIENT_START))
        gradient.setColorAt(1.0, QColor(BAR_GRADIENT_END))
        painter.fillPath(clip, gradient)

        self._paint_motifs(painter, rect)
        painter.end()

    def _paint_motifs(self, painter: QPainter, rect: QRectF) -> None:
        if not self._motifs:
            return
        painter.save()
        painter.setPen(Qt.NoPen)
        size = min(rect.height() * 0.62, 46)
        spacing = size * 2.2
        total_w = spacing * len(self._motifs)
        if self._align == "center":
            start_x = rect.center().x() - total_w / 2
        else:
            start_x = rect.right() - total_w - 20
        cy = rect.center().y()
        for i, motif in enumerate(self._motifs):
            cx = start_x + spacing * i + spacing / 2
            if cx - size < rect.left():
                continue
            if motif == "star":
                painter.setBrush(QColor(255, 224, 90, 46))
                painter.drawPath(_star_path(cx, cy, size))
            elif motif == "party":
                self._draw_party_emblem(painter, cx, cy, size)
        painter.restore()

    def _draw_party_emblem(self, painter: QPainter, cx: float, cy: float, size: float) -> None:
        pixmap = _party_emblem_pixmap_cached()
        if pixmap.isNull():
            return
        target_h = size * 2.1
        target_w = target_h * pixmap.width() / pixmap.height()
        scaled = pixmap.scaled(
            int(target_w), int(target_h), Qt.KeepAspectRatio, Qt.SmoothTransformation
        )
        painter.setOpacity(0.28)
        painter.drawPixmap(
            int(cx - scaled.width() / 2), int(cy - scaled.height() / 2), scaled
        )
        painter.setOpacity(1.0)
