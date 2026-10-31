"""Nodo de teleoperación: /joy -> /cmd_vel, flipper, brazo, servicios. Ver mapping.py."""

from __future__ import annotations

import time

import rclpy
from rclpy.executors import ExternalShutdownException
from geometry_msgs.msg import Twist
from rclpy.node import Node
from sensor_msgs.msg import Joy
from std_msgs.msg import Bool, Float64, String, UInt8
from std_srvs.srv import SetBool

from carpincho_interfaces.msg import BaseStatus
from carpincho_interfaces.srv import SetNamedPose

from .mapping import TeleopConfig, TeleopMapper


class JoyTeleop(Node):
    def __init__(self) -> None:
        super().__init__("joy_teleop")
        cfg = TeleopConfig()
        cfg.speeds = tuple(self.declare_parameter("speeds", list(cfg.speeds)).value)
        cfg.turn_rate = tuple(self.declare_parameter("turn_rate", list(cfg.turn_rate)).value)
        cfg.deadzone = self.declare_parameter("deadzone", cfg.deadzone).value
        cfg.triggers_rest_at_one = self.declare_parameter("triggers_rest_at_one", True).value
        for k in list(cfg.axes):
            cfg.axes[k] = self.declare_parameter(f"axes.{k}", cfg.axes[k]).value
        for k in list(cfg.buttons):
            cfg.buttons[k] = self.declare_parameter(f"buttons.{k}", cfg.buttons[k]).value
        self.mapper = TeleopMapper(cfg)
        self.enabled = False
        self.last_joy = 0.0

        self.pub_cmd = self.create_publisher(Twist, "cmd_vel_teleop", 10)
        self.pub_flip_v = self.create_publisher(Float64, "flipper/velocity_cmd", 10)
        self.pub_flip_p = self.create_publisher(Float64, "flipper/position_cmd", 10)
        self.pub_jog = self.create_publisher(Twist, "arm/cartesian_jog", 10)
        self.pub_grip = self.create_publisher(Float64, "arm/gripper", 10)
        self.pub_lights = self.create_publisher(UInt8, "base/lights", 10)
        self.pub_mode = self.create_publisher(String, "teleop/mode", 10)
        self.pub_auto = self.create_publisher(Bool, "autonomy/request", 10)
        self.cli_enable = self.create_client(SetBool, "base/enable")
        self.cli_pose = self.create_client(SetNamedPose, "arm/set_named_pose")
        self.create_subscription(Joy, "joy", self.on_joy, 10)
        self.create_subscription(BaseStatus, "base/status", self.on_status, 10)
        self.create_timer(0.1, self.watchdog)

    def on_status(self, msg: BaseStatus) -> None:
        self.enabled = msg.motors_enabled

    def watchdog(self) -> None:
        # si el joystick se desconecta, frenamos (el driver de joy deja de publicar)
        if time.monotonic() - self.last_joy > 0.5:
            self.pub_cmd.publish(Twist())

    def on_joy(self, msg: Joy) -> None:
        self.last_joy = time.monotonic()
        o = self.mapper.update(list(msg.axes), list(msg.buttons))
        t = Twist()
        t.linear.x, t.angular.z = o.v, o.w
        self.pub_cmd.publish(t)
        if o.flipper_vel is not None:
            self.pub_flip_v.publish(Float64(data=o.flipper_vel))
        if o.flipper_pos is not None:
            self.pub_flip_p.publish(Float64(data=o.flipper_pos))
        if o.arm_jog is not None:
            j = Twist()
            j.linear.x, j.linear.y, j.linear.z, j.angular.y, j.angular.z, j.angular.x = o.arm_jog
            self.pub_jog.publish(j)
        if o.gripper is not None:
            self.pub_grip.publish(Float64(data=o.gripper))
        if o.lights is not None:
            self.pub_lights.publish(UInt8(data=o.lights))
        if o.mode_changed:
            self.pub_mode.publish(String(data=self.mapper.mode))
            self.get_logger().info(f"Modo: {self.mapper.mode.upper()}")
        if o.request_autonomy:
            self.pub_auto.publish(Bool(data=True))
            self.get_logger().info("Autonomía pedida: soltá el joystick (manos afuera)")
        if o.toggle_enable and self.cli_enable.service_is_ready():
            req = SetBool.Request()
            req.data = not self.enabled
            self.cli_enable.call_async(req)
        if o.named_pose and self.cli_pose.service_is_ready():
            req = SetNamedPose.Request()
            req.name = o.named_pose
            self.cli_pose.call_async(req)


def main() -> None:
    rclpy.init()
    node = JoyTeleop()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
