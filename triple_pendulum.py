import math
import sys
from collections import deque

from PyQt5.QtCore import QRectF, QTimer, QPointF
from PyQt5.QtGui import QColor, QPolygonF
from PyQt5.QtWidgets import QApplication, QMainWindow, QGraphicsView, QGraphicsScene, QGraphicsPathItem, \
    QGraphicsLineItem

from common import GraphicsView, Counter, Vector

G = 9.81


class Pendulum:
    def __init__(self, x_hinge, y_hinge, length, mass, initial_angle_rad, color):
        self._pt1 = QPointF(x_hinge, y_hinge)
        self._center = None
        self._pt2 = None
        self.length = length
        self.mass = mass
        self.moment_of_inertia = mass * length * length / 3.0
        self._angle = initial_angle_rad
        self.angular_velocity = 0
        self.angular_acceleration = 0
        self.graphics_item = QGraphicsLineItem(0, 0, 1, 1)
        self.graphics_item.setPen(color)
        self.update_view()

    @property
    def pt1(self) -> QPointF:
        return self._pt1

    @pt1.setter
    def pt1(self, value: QPointF):
        self._pt1 = value
        self._center = None
        self._pt2 = None

    def point_at_length(self, l: float) -> QPointF:
        return QPointF(self.pt1.x() + l * math.cos(self.angle),
                       self.pt1.y() + l * math.sin(self.angle))

    @property
    def pt2(self) -> QPointF:
        if self._pt2 is None:
            self._pt2 = self.point_at_length(self.length)
        return self._pt2

    @property
    def center(self) -> QPointF:
        if self._center is None:
            self._center = self.point_at_length(self.length / 2.0)
        return self._center

    def torque(self, hinge_pt) -> float:
        x_dist = self.center.x() - hinge_pt.x()
        force = self.mass * G
        return force * x_dist

    def update_view(self):
        pt2 = self.pt2
        self.graphics_item.setLine(self.pt1.x(), self.pt1.y(), pt2.x(), pt2.y())

    @property
    def angle(self) -> float:
        return self._angle

    @angle.setter
    def angle(self, value: float):
        self._angle = value
        self._center = None
        self._pt2 = None


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

        self.pendulum = Pendulum(0, 0, 100, 50, math.radians(-30), QColor(0, 255, 0))
        
        self.pendulum2 = Pendulum(self.pendulum.pt2.x(), self.pendulum.pt2.y(), 50, 50, math.radians(90), QColor(0, 0, 255))
        
        self.pendulum3 = Pendulum(self.pendulum2.pt2.x(), self.pendulum2.pt2.y(), 50, 50, math.radians(90),
                                  QColor(0, 255, 255))
        
        self.pendulum_chain = [self.pendulum, self.pendulum2, self.pendulum3]
        for p in self.pendulum_chain:
            self.scene.addItem(p.graphics_item)

        self.trace_length = 2000
        self.trace_points = deque()
        self.trace = QGraphicsPathItem()
        self.trace.setPen(QColor(255, 0, 0))
        self.scene.addItem(self.trace)

        self.scene_rect_zoom = 2
        self._fit_scene_rect()
        self.view.centerOn(self.pendulum.graphics_item)
        self.view.fitInView(self.scene.sceneRect(), True)

        self.setCentralWidget(self.view)

        self.timer = QTimer()
        self.timer.setSingleShot(False)
        self.timer.setInterval(10)
        self.timer.timeout.connect(self.timer_update)
        self.timer.start()

        self.view_update_counter = Counter(4)
        self.scene_rect_update_counter = Counter(64)
        self.trace_update_counter = Counter(8)

        self.time_step = 0.05

        self.setWindowTitle("Pendulum")
        self.show()

    def timer_update(self):
        update_view = self.view_update_counter.count_and_check_elapsed()

        new_angles = []
        new_accels = []
        for i in range(len(self.pendulum_chain)):
            current = self.pendulum_chain[i]
            current_rotation_pt = current.pt1
            trq = sum(pp.torque(current_rotation_pt) for pp in self.pendulum_chain[i:])
            if i > 0:
                previous = self.pendulum_chain[i-1]
                linear_accel = previous.angular_acceleration * previous.length
                linear_accel_vector = Vector.from_angle_and_length(previous.angle + math.radians(90), linear_accel)
                inertia_force = linear_accel_vector.scalar_multiply(current.mass)
                r = Vector.from_2_pts(current.pt1, current.center)
                inertia_trq = r.cross_product(inertia_force)
                trq -= inertia_trq
            accel = trq / current.moment_of_inertia
            new_accels.append(accel)
            current.angular_velocity = current.angular_velocity + accel * self.time_step
            new_angle = current.angle + current.angular_velocity * self.time_step
            new_angles.append(new_angle)
        for i in range(len(self.pendulum_chain)):
            self.pendulum_chain[i].angle = new_angles[i]
            self.pendulum_chain[i].angular_acceleration = new_accels[i]
            if i > 0:
                self.pendulum_chain[i].pt1 = self.pendulum_chain[i - 1].pt2

        self.trace_points.append(self.pendulum_chain[-1].pt2)
        if len(self.trace_points) > self.trace_length:
            self.trace_points.popleft()

        if update_view:
            for p in self.pendulum_chain:
                p.update_view()
            if len(self.trace_points) > 1:
                path = self.trace.path()
                path.clear()
                path.addPolygon(QPolygonF(self.trace_points))
                self.trace.setPath(path)

    def _fit_scene_rect(self):
        rect = self.scene.itemsBoundingRect()
        center = rect.center()
        dim = max(rect.width(), rect.height()) * self.scene_rect_zoom
        rect2 = QRectF(QPointF(center.x() - dim, center.y() - dim), QPointF(center.x() + dim, center.y() + dim))
        self.scene.setSceneRect(rect2)


app = QApplication(sys.argv)

window = MainWindow()

app.exec_()
