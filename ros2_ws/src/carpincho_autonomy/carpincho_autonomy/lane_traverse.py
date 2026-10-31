"""Nodo de travesía autónoma de carril + multiplexor de comandos (teleop siempre tiene prioridad).

Suscribe: /scan (LaserScan, de pointcloud_to_laserscan o LiDAR 2D), odom_topic (Odometry),
          /imu/data (Imu), /qr/text (String), /cmd_vel_teleop (Twist), /autonomy/request (Bool)
Publica:  /cmd_vel (Twist), /autonomy/active (Bool), /autonomy/lane_status (LaneStatus),
          /base/led_mode (UInt8: 1 = autónomo)
Servicios: /autonomy/start (Trigger), /autonomy/stop (Trigger)

Regla de oro: si el operador mueve el joystick, la autonomía se corta al instante (y ese tramo
pasa a contar como teleoperado).
"""

from __future__ import annotations

import math
import time

import rclpy
from rclpy.executors import ExternalShutdownException
from geometry_msgs.msg import Twist
from nav_msgs.msg import Odometry
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import Imu, LaserScan
from std_msgs.msg import Bool, String, UInt8
from std_srvs.srv import Trigger

from carpincho_interfaces.msg import LaneStatus

from .lane_logic import LaneParams, LaneTraverse, sector_distance


def yaw_pitch(q):
    yaw = math.atan2(2 * (q.w * q.z + q.x * q.y), 1 - 2 * (q.y * q.y + q.z * q.z))
    pitch = math.asin(max(-1.0, min(1.0, 2 * (q.w * q.y - q.z * q.x))))
    return yaw, pitch


class LaneNode(Node):
    def __init__(self) -> None:
        super().__init__("lane_traverse")
        lp = LaneParams()
        for k, v in vars(lp).items():
            setattr(lp, k, self.declare_parameter(k, v).value)
        self.end_qr_text = self.declare_parameter("end_qr_text", "").value   # vacío = cualquier QR
        self.logic = LaneTraverse(lp)
        self.active = False
        self.dist = 0.0
        self.last_xy = None
        self.yaw = 0.0
        self.pitch = 0.0
        self.scan = None
        self.teleop = Twist()
        self.teleop_t = 0.0

        self.pub_cmd = self.create_publisher(Twist, "/cmd_vel", 10)
        self.pub_active = self.create_publisher(Bool, "/autonomy/active", 10)
        self.pub_status = self.create_publisher(LaneStatus, "/autonomy/lane_status", 10)
        self.pub_led = self.create_publisher(UInt8, "/base/led_mode", 10)
        self.create_subscription(LaserScan, "/scan", lambda m: setattr(self, "scan", m), qos_profile_sensor_data)
        self.create_subscription(Odometry, self.declare_parameter("odom_topic", "/odom").value, self.on_odom, 20)
        self.create_subscription(Imu, "/imu/data", self.on_imu, qos_profile_sensor_data)
        self.create_subscription(String, "/qr/text", self.on_qr, 10)
        self.create_subscription(Twist, "/cmd_vel_teleop", self.on_teleop, 10)
        self.create_subscription(Bool, "/autonomy/request", lambda m: self.set_active(m.data), 10)
        self.create_service(Trigger, "/autonomy/start", self.srv_start)
        self.create_service(Trigger, "/autonomy/stop", self.srv_stop)
        self.create_timer(0.05, self.tick)

    def on_odom(self, m: Odometry) -> None:
        x, y = m.pose.pose.position.x, m.pose.pose.position.y
        if self.last_xy is not None:
            self.dist += math.hypot(x - self.last_xy[0], y - self.last_xy[1])
        self.last_xy = (x, y)

    def on_imu(self, m: Imu) -> None:
        self.yaw, self.pitch = yaw_pitch(m.orientation)

    def on_qr(self, m: String) -> None:
        if self.active and (not self.end_qr_text or self.end_qr_text in m.data):
            self.logic.end_qr()

    def on_teleop(self, m: Twist) -> None:
        self.teleop = m
        self.teleop_t = time.monotonic()
        if self.active and (abs(m.linear.x) > 0.02 or abs(m.angular.z) > 0.05):
            self.get_logger().warn("El operador tomó el control: autonomía cancelada")
            self.set_active(False)

    def set_active(self, on: bool) -> None:
        if on and not self.active:
            self.logic.start(self.yaw, self.dist, time.monotonic())
            self.get_logger().info("Autonomía de carril: INICIO")
        if not on and self.active:
            self.logic.abort("detenida")
        self.active = on
        self.pub_active.publish(Bool(data=on))
        self.pub_led.publish(UInt8(data=1 if on else 0))

    def srv_start(self, req, res):
        self.set_active(True)
        res.success, res.message = True, "autonomía iniciada"
        return res

    def srv_stop(self, req, res):
        self.set_active(False)
        res.success, res.message = True, "autonomía detenida"
        return res

    def tick(self) -> None:
        if not self.active:
            # mux: pasa el comando del operador (se frena solo si deja de llegar)
            cmd = self.teleop if time.monotonic() - self.teleop_t < 0.5 else Twist()
            self.pub_cmd.publish(cmd)
            return
        left = right = front = None
        s = self.scan
        if s is not None:
            left = sector_distance(s.ranges, s.angle_min, s.angle_increment, math.radians(60), math.radians(120))
            right = sector_distance(s.ranges, s.angle_min, s.angle_increment, math.radians(-120), math.radians(-60))
            front = sector_distance(s.ranges, s.angle_min, s.angle_increment, math.radians(-15), math.radians(15))
        v, w = self.logic.step(time.monotonic(), self.yaw, self.dist, self.pitch, left, right, front)
        t = Twist()
        t.linear.x, t.angular.z = v, w
        self.pub_cmd.publish(t)
        st = self.logic.s
        ls = LaneStatus()
        ls.header.stamp = self.get_clock().now().to_msg()
        ls.state, ls.traverses_done = st.state, st.traverses_done
        ls.distance = float(self.dist - st.start_dist)
        ls.lateral_error, ls.heading_error = float(st.lateral_error), float(st.heading_error)
        ls.last_event = st.event
        self.pub_status.publish(ls)
        if st.state in ("DONE", "ABORT"):
            self.get_logger().info(f"Autonomía terminó: {st.state} ({st.event})")
            self.set_active(False)


def main() -> None:
    rclpy.init()
    n = LaneNode()
    try:
        rclpy.spin(n)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        n.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
