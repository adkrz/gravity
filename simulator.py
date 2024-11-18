import math
import sys
from typing import Sequence
from collections import deque

from PyQt5.QtCore import QRectF, QTimer, QPointF
from PyQt5.QtGui import QColor, QPainterPath, QPen, QPolygonF
from PyQt5.QtWidgets import QApplication, QMainWindow, QGraphicsView, QGraphicsScene, QGraphicsEllipseItem, \
    QGraphicsPathItem

GRAVITATIONAL_CONSTANT = 100000  # not the real one, but also the masses are not real...


class Vector:
    def __init__(self, dx, dy):
        self.dx = dx
        self.dy = dy

    @staticmethod
    def fromAngleAndLength(angle, length) -> "Vector":
        dx = length * math.cos(angle)
        dy = length * math.sin(angle)
        return Vector(dx, dy)

    def movePoint(self, pt: QPointF) -> QPointF:
        return QPointF(pt.x() + self.dx, pt.y() + self.dy)

    def length(self) -> float:
        return math.hypot(self.dx, self.dy)

    def add(self, v2: "Vector") -> "Vector":
        return Vector(self.dx + v2.dx, self.dy + v2.dy)

    def scalar_multiply(self, value: float) -> "Vector":
        return Vector(self.dx * value, self.dy * value)

    def scalar_divide(self, value: float) -> "Vector":
        return Vector(self.dx / value, self.dy / value)

    def reversed(self) -> "Vector":
        return Vector(-self.dx, -self.dy)

    @staticmethod
    def sum(vectors: Sequence["Vector"]) -> "Vector":
        return Vector(sum(v.dx for v in vectors), sum(v.dy for v in vectors))


class Planet:
    def __init__(self, x, y, x_vel, y_vel, radius, color: QColor):
        self._pos = QPointF(x, y)
        self._radius = radius
        self.color = color
        self.mass = 1
        self.stationary = False
        self.velocity = Vector(x_vel, y_vel)
        self.graphics_item = QGraphicsEllipseItem(self._gen_rect())
        self.graphics_item.setBrush(color)
        self._trace = deque()
        self.trace_length = 2000
        self.trace_graphics_item = QGraphicsPathItem()
        self.trace_graphics_item.setPen(QPen(color, 3))

    def pos(self) -> QPointF:
        return self._pos

    def move_abs(self, pos: QPointF, update_view=True, update_trace=True):
        self._pos = pos
        if self.trace_length > 0 and update_trace:
            self._trace.append(pos)
            if len(self._trace) > self.trace_length:
                self._trace.popleft()
        if update_view:
            self.update_view()

    def move_rel(self, delta_pos: QPointF, update_view=True):
        self._pos = QPointF(self._pos.x() + delta_pos.x(), self._pos.y() + delta_pos.y())
        self.move_abs(self._pos, update_view)

    def _gen_rect(self) -> QRectF:
        new_rect = QRectF(QPointF(self._pos.x() - self._radius, self._pos.y() + self._radius),
                          QPointF(self._pos.x() + self._radius, self._pos.y() - self._radius))
        return new_rect

    def update_view(self):
        self.graphics_item.setRect(self._gen_rect())
        if len(self._trace) > 1:
            path = self.trace_graphics_item.path()
            path.clear()
            path.addPolygon(QPolygonF(self._trace))
            self.trace_graphics_item.setPath(path)

    def dist_to(self, planet2: "Planet") -> float:
        return math.hypot(self._pos.x() - planet2._pos.x(), self._pos.y() - planet2._pos.y())

    def dist_to_squared(self, planet2: "Planet") -> float:
        return (self._pos.x() - planet2._pos.x()) * (self._pos.x() - planet2._pos.x()) \
                + (self._pos.y() - planet2._pos.y()) * (self._pos.y() - planet2._pos.y())

    def angle_to(self, planet2: "Planet") -> float:
        return math.atan2(planet2._pos.y() - self._pos.y(), planet2._pos.x() - self._pos.x())

    def vector_to(self, planet2: "Planet", length: float) -> Vector:
        return Vector.fromAngleAndLength(self.angle_to(planet2), length)

    def force_to(self, planet2: "Planet") -> Vector:
        force_value = GRAVITATIONAL_CONSTANT * self.mass * planet2.mass / self.dist_to_squared(planet2)
        return self.vector_to(planet2, force_value)


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


class MainWindow(QMainWindow):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.view = GraphicsView()
        self.view.setInteractive(False)
        self.scene = QGraphicsScene()
        self.scene.setBackgroundBrush(QColor(0, 0, 0))
        self.view.setScene(self.scene)
        self.view.setDragMode(QGraphicsView.ScrollHandDrag)
        self.scene.setItemIndexMethod(QGraphicsScene.NoIndex)

        self.scene_auto_adjust = False
        self.scene_rect_zoom = 1
        self.draw_trace_length = 2000

        # Normal orbit
        self.planet1 = Planet(0, 0, 0, 0, 100, QColor(0,255,0))
        self.planet1.stationary = True
        self.planet2 = Planet(250, 250, 10, -10, 60, QColor(0,255,255))
        self.planet2.mass = self.planet1.mass / 2.0
        self.planets = [self.planet1, self.planet2]

        # Common centre of mass
        """
        self.planet1 = Planet(-250, 250, 0, 10, 100, QColor(0, 255, 0))
        self.planet2 = Planet(250, 250, 0, -10, 100, QColor(0, 255, 255))
        self.planets = [self.planet1, self.planet2]
        """

        # Elongated
        """
        self.draw_trace_length = 20000
        self.planet1 = Planet(0, 0, 0, 0, 100, QColor(0, 255, 0))
        self.planet1.stationary = True
        self.planet2 = Planet(250, 250, 15, -15, 60, QColor(0, 255, 255))
        self.planet2.mass = self.planet1.mass / 2.0
        self.scene_auto_adjust = True
        self.scene_rect_zoom = 1
        self.planets = [self.planet1, self.planet2]
        """

        # Chasing
        """
        self.planet1 = Planet(0, 0, 0, 0, 100, QColor(0,255,0))
        self.planet2 = Planet(250, 250, 10, -30, 60, QColor(0,255,255))
        self.planet2.mass = 2
        self.scene_auto_adjust = True
        self.planets = [self.planet1, self.planet2]
        """

        # Around the sun
        """
        self.draw_trace_length = 10000
        self.planet1 = Planet(0, 0, 0, 0, 100, QColor(255, 255, 0))
        self.planet2 = Planet(250, 250, 10, -10, 60, QColor(0, 255, 255))
        self.planet2.mass = self.planet1.mass / 50
        self.planet3 = Planet(-250, -250, -10, 10, 30, QColor(0, 255, 0))
        self.planet3.mass = self.planet1.mass / 100
        self.planets = [self.planet1, self.planet2, self.planet3]
        """

        # Planet with moon, got caught by the star
        """
        self.draw_trace_length = 10000
        self.planet1 = Planet(0, 0, 0, 0, 100, QColor(255, 255, 0))
        self.planet2 = Planet(3250, 3250, 0, -5, 30, QColor(0, 255, 255))
        self.planet2.mass = self.planet1.mass / 50
        self.planet3 = Planet(-250, -250, -10, 10, 30, QColor(0, 255, 0))
        self.planet3.mass = self.planet1.mass / 100
        moon = Planet(3350, 3300, 4, -7, 20, QColor(255, 255, 255))
        moon.mass = self.planet1.mass / 2000
        self.planets = [self.planet1, self.planet2, self.planet3, moon]
        """

        # 3 body problem
        """
        self.draw_trace_length = 200000
        radius = 600
        self.planet1 = Planet(0, -radius, 0, 0, 100, QColor(0, 255, 0))
        radius = 700
        self.planet2 = Planet(-radius * math.cos(math.radians(-30)),
                              -radius * math.sin(math.radians(-30)), 0, 0, 100, QColor(255, 255, 255))
        radius = 400
        self.planet3 = Planet(radius * math.cos(math.radians(-30)),
                              -radius * math.sin(math.radians(-30)), 0, 0, 100, QColor(255, 255, 0))
        self.planets = [self.planet1, self.planet2, self.planet3]
        """

        for planet in self.planets:
            planet.trace_length = self.draw_trace_length
            self.scene.addItem(planet.graphics_item)
            self.scene.addItem(planet.trace_graphics_item)

        self._fit_scene_rect()
        self.view.centerOn(self.planet1.graphics_item)
        self.view.fitInView(self.scene.sceneRect(), True)

        self.setCentralWidget(self.view)

        self.timer = QTimer()
        self.timer.setSingleShot(False)
        self.timer.setInterval(5)
        self.timer.timeout.connect(self.timer_update)
        self.timer.start()

        self.view_update_counter = Counter(4)
        self.scene_rect_update_counter = Counter(64)
        self.trace_update_counter = Counter(8)

        self.time_step = 0.05

        self.setWindowTitle("Gravity")
        self.show()

    def timer_update(self):
        update_view = self.view_update_counter.count_and_check_elapsed()
        update_scene_rect = self.scene_rect_update_counter.count_and_check_elapsed()
        update_traces = self.trace_update_counter.count_and_check_elapsed()

        forces = {p: [] for p in self.planets}

        for i in range(len(self.planets)):
            planet = self.planets[i]
            for j in range(i+1, len(self.planets)):
                other_planet = self.planets[j]
                force = planet.force_to(other_planet)
                if not planet.stationary:
                    forces[planet].append(force)
                if not other_planet.stationary:
                    forces[other_planet].append(force.reversed())

        for planet in self.planets:
            if planet.stationary:
                continue
            force_sum = Vector.sum(forces[planet])
            acceleration = force_sum.scalar_divide(planet.mass)
            new_vel = planet.velocity.add(acceleration.scalar_multiply(self.time_step))
            planet.velocity = new_vel
            new_pos = new_vel.scalar_multiply(self.time_step).movePoint(planet.pos())
            planet.move_abs(new_pos, update_view, update_traces)

        if update_scene_rect:
            self._fit_scene_rect()
        if update_view:
            if self.scene_auto_adjust:
                self.view.fitInView(self.scene.sceneRect(), True)

    def _fit_scene_rect(self):
        rect = self.scene.itemsBoundingRect()
        center = rect.center()
        dim = max(rect.width(), rect.height()) * self.scene_rect_zoom
        rect2 = QRectF(QPointF(center.x() - dim, center.y() - dim), QPointF(center.x() + dim, center.y() + dim))
        self.scene.setSceneRect(rect2)


app = QApplication(sys.argv)


window = MainWindow()

app.exec_()
