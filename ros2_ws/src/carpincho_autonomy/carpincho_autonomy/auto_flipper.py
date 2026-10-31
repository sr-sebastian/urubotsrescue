"""Flippers automáticos según el cabeceo del IMU. Activo con /flipper/auto (Bool) o en autonomía."""

from __future__ import annotations

import rclpy
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import Imu
from std_msgs.msg import Bool, Float64

from .lane_logic import AutoFlipper
from .lane_traverse import yaw_pitch


class AutoFlipperNode(Node):
    def __init__(self) -> None:
        super().__init__("auto_flipper")
        self.af = AutoFlipper()
        self.manual_on = False
        self.auto_on = False
        self.last_cmd = None
        self.pub = self.create_publisher(Float64, "/flipper/position_cmd", 10)
        self.create_subscription(Imu, "/imu/data", self.on_imu, qos_profile_sensor_data)
        self.create_subscription(Bool, "/flipper/auto", lambda m: setattr(self, "manual_on", m.data), 10)
        self.create_subscription(Bool, "/autonomy/active", lambda m: setattr(self, "auto_on", m.data), 10)

    def on_imu(self, m: Imu) -> None:
        if not (self.manual_on or self.auto_on):
            self.last_cmd = None
            return
        _, pitch = yaw_pitch(m.orientation)
        target = self.af.update(pitch, m.angular_velocity.y)
        if self.last_cmd is None or abs(target - self.last_cmd) > 1e-3:
            self.pub.publish(Float64(data=target))
            self.last_cmd = target
            self.get_logger().info(f"flippers -> {self.af.mode}")


def main() -> None:
    rclpy.init()
    n = AutoFlipperNode()
    try:
        rclpy.spin(n)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        n.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
