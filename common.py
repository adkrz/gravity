import math
from typing import Sequence

from PyQt5.QtCore import QPointF
from PyQt5.QtWidgets import QGraphicsView


class GraphicsView(QGraphicsView):
    def wheelEvent(self, evt):
        angle = evt.angleDelta().y()
        factor = 1.0015 ** angle
        targetViewportPos = evt.pos()
        targetScenePos = self.mapToScene(targetViewportPos)
        self.scale(factor, factor)
        self.centerOn(targetScenePos)
        deltaViewportPos = targetViewportPos - QPointF(self.viewport().width() / 2.0, self.viewport().height() / 2.0)
        viewportCenter = self.mapFromScene(targetScenePos) - deltaViewportPos
        self.centerOn(self.mapToScene(viewportCenter.toPoint()))


class Counter:
    def __init__(self, max_val):
        self.value = max_val
        self.max_val = max_val

    def count_and_check_elapsed(self) -> bool:
        self.value -= 1
        ok = False
        if self.value <= 0:
            ok = True
            self.value = self.max_val
        return ok


class Vector:
    def __init__(self, dx, dy):
        self.dx = dx
        self.dy = dy

    @staticmethod
    def from_angle_and_length(angle, length) -> "Vector":
        dx = length * math.cos(angle)
        dy = length * math.sin(angle)
        return Vector(dx, dy)

    @staticmethod
    def from_2_pts(pt1: QPointF, pt2: QPointF) -> "Vector":
        return Vector(pt2.x() - pt1.x(), pt2.y() - pt1.y())

    def movePoint(self, pt: QPointF) -> QPointF:
        return QPointF(pt.x() + self.dx, pt.y() + self.dy)

    def length(self) -> float:
        return math.hypot(self.dx, self.dy)

    def angle(self) -> float:
        return math.atan2(self.dy, self.dx)

    def add(self, v2: "Vector") -> "Vector":
        return Vector(self.dx + v2.dx, self.dy + v2.dy)

    def scalar_multiply(self, value: float) -> "Vector":
        return Vector(self.dx * value, self.dy * value)

    def scalar_divide(self, value: float) -> "Vector":
        return Vector(self.dx / value, self.dy / value)

    def reversed(self) -> "Vector":
        return Vector(-self.dx, -self.dy)
    
    def cross_product(self, v2: "Vector") -> float:
        return self.dx + v2.dy - self.dy * v2.dx
    
    def dot_product(self, v2: "Vector") -> float:
        return self.dx + v2.dx + self.dy * v2.dy

    @staticmethod
    def sum(vectors: Sequence["Vector"]) -> "Vector":
        return Vector(sum(v.dx for v in vectors), sum(v.dy for v in vectors))
