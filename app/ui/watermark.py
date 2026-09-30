"""Red header/footer bar with faint patriotic watermark motifs (star, lotus,
hammer & sickle) painted low-opacity into the background."""

from __future__ import annotations

import math

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QLinearGradient, QPainter, QPainterPath
from PySide6.QtWidgets import QFrame

BAR_GRADIENT_START = "#D42E2E"
BAR_GRADIENT_END = "#8E0E0E"


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


def _lotus_path(cx: float, cy: float, r: float, petals: int = 8) -> QPainterPath:
    path = QPainterPath()
    for i in range(petals):
        angle = math.radians(i * (360.0 / petals) - 90)
        perp = angle + math.pi / 2
        tip_x, tip_y = cx + r * math.cos(angle), cy + r * math.sin(angle)
        base_x, base_y = cx + r * 0.18 * math.cos(angle), cy + r * 0.18 * math.sin(angle)
        w = r * 0.24
        wx, wy = w * math.cos(perp), w * math.sin(perp)
        petal = QPainterPath()
        petal.moveTo(base_x + wx, base_y + wy)
        petal.quadTo(tip_x + wx * 0.4, tip_y + wy * 0.4, tip_x, tip_y)
        petal.quadTo(tip_x - wx * 0.4, tip_y - wy * 0.4, base_x - wx, base_y - wy)
        petal.quadTo(cx, cy, base_x + wx, base_y + wy)
        path.addPath(petal)
    center = QPainterPath()
    center.addEllipse(QRectF(cx - r * 0.14, cy - r * 0.14, r * 0.28, r * 0.28))
    path.addPath(center)
    path.setFillRule(Qt.WindingFill)
    return path


def _party_emblem_path(cx: float, cy: float, r: float) -> QPainterPath:
    """Simplified hammer-and-sickle silhouette."""
    path = QPainterPath()

    outer = QRectF(cx - r * 0.15, cy - r * 0.95, r * 1.7, r * 1.7)
    inner = QRectF(cx + 0.13 * r, cy - r * 0.67, r * 1.22, r * 1.22)
    path.moveTo(cx + r * 0.55, cy - r * 0.85)
    path.arcTo(outer, 70, 230)
    path.lineTo(cx - r * 0.02, cy + r * 0.28)
    path.arcTo(inner, 300, -230)
    path.closeSubpath()

    x0, y0 = cx - r * 0.58, cy + r * 0.75
    x1, y1 = cx + r * 0.55, cy - r * 0.55
    dx, dy = x1 - x0, y1 - y0
    length = math.hypot(dx, dy) or 1.0
    ux, uy = dx / length, dy / length
    px, py = -uy, ux

    hw = r * 0.09
    handle = QPainterPath()
    handle.moveTo(x0 + px * hw, y0 + py * hw)
    handle.lineTo(x1 + px * hw, y1 + py * hw)
    handle.lineTo(x1 - px * hw, y1 - py * hw)
    handle.lineTo(x0 - px * hw, y0 - py * hw)
    handle.closeSubpath()

    # Head: a crossbar centered on the handle tip, perpendicular to it.
    cross_len, cross_thick = r * 0.62, r * 0.30
    head = QPainterPath()
    corners = [(-1, -1), (1, -1), (1, 1), (-1, 1)]
    for j, (slong, sshort) in enumerate(corners):
        x = x1 + px * (cross_len / 2) * slong + ux * (cross_thick / 2) * sshort
        y = y1 + py * (cross_len / 2) * slong + uy * (cross_thick / 2) * sshort
        if j == 0:
            head.moveTo(x, y)
        else:
            head.lineTo(x, y)
    head.closeSubpath()

    path.addPath(handle)
    path.addPath(head)
    path.setFillRule(Qt.WindingFill)
    return path


_MOTIF_DRAWERS = {"star": _star_path, "lotus": _lotus_path, "party": _party_emblem_path}
_MOTIF_COLORS = {
    "star": QColor(255, 224, 90, 46),
    "lotus": QColor(255, 255, 255, 38),
    "party": QColor(255, 224, 90, 40),
}


class GradientBar(QFrame):
    """A red-gradient bar used for the app header/footer, with a few faint
    patriotic motifs painted into the empty space on the right."""

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
        spacing = size * 2.0
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
            draw = _MOTIF_DRAWERS.get(motif)
            if not draw:
                continue
            painter.setBrush(_MOTIF_COLORS.get(motif, QColor(255, 255, 255, 40)))
            painter.drawPath(draw(cx, cy, size))
        painter.restore()
