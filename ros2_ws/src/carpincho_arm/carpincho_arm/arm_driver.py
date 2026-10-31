"""Driver ROS 2 del brazo C1 (servos Feetech STS3215 por bus serie).

Publica:   /arm/joint_states     sensor_msgs/JointState  (arm_j1..arm_j5, gripper)
           /arm/tip_pose         geometry_msgs/PoseStamped (punta, en arm_base_link)
Suscribe:  /arm/joint_command    sensor_msgs/JointState  objetivos articulares [rad]
           /arm/cartesian_jog    geometry_msgs/Twist     linear xyz [m/s], angular.y = pitch [rad/s],
                                                         angular.z = giro de base [rad/s],
                                                         angular.x = giro de muñeca J5 [rad/s]
           /arm/gripper          std_msgs/Float64        0 = cerrada, 1 = abierta (105 mm)
Servicios: /arm/set_named_pose   carpincho_interfaces/SetNamedPose
           /arm/torque           std_srvs/SetBool
"""

from __future__ import annotations

import math
import time

import rclpy
from rclpy.executors import ExternalShutdownException
from geometry_msgs.msg import PoseStamped, Twist
from rclpy.node import Node
from sensor_msgs.msg import JointState
from std_msgs.msg import Float64
from std_srvs.srv import SetBool

from carpincho_interfaces.srv import SetNamedPose

from . import feetech as ft
from .kinematics import ArmGeometry, Unreachable, clamp_joints, fk, ik, interpolate

JOINTS = ["arm_j1", "arm_j2", "arm_j3", "arm_j4", "arm_j5"]
TICK_PER_RAD = ft.TICKS_PER_REV / (2 * math.pi)


class JointMap:
    """Conversión ángulo de articulación <-> ticks de uno o más servos."""

    def __init__(self, ids, ratio, signs, zeros):
        self.ids, self.ratio, self.signs, self.zeros = list(ids), ratio, list(signs), list(zeros)

    def to_ticks(self, angle: float) -> dict[int, int]:
        return {sid: int(round(z + s * self.ratio * angle * TICK_PER_RAD))
                for sid, s, z in zip(self.ids, self.signs, self.zeros)}

    def from_ticks(self, ticks: int) -> float:
        # usamos el primer servo como referencia
        return (ticks - self.zeros[0]) / (self.signs[0] * self.ratio * TICK_PER_RAD)


class ArmDriver(Node):
    def __init__(self) -> None:
        super().__init__("arm_driver")
        p = self.declare_parameter
        self.port = p("port", "/dev/carpincho_arm").value
        self.baud = p("baud", 1_000_000).value
        self.rate = p("rate", 50.0).value
        self.max_joint_vel = p("max_joint_vel", 1.2).value          # rad/s
        self.simulate = p("simulate", False).value                 # sin hardware: eco de comandos
        self.geom = ArmGeometry(p("h0", 0.085).value, p("l1", 0.26).value, p("l2", 0.24).value,
                                p("l3", 0.14).value)
        self.maps: list[JointMap] = []
        for j in JOINTS:
            ids = p(f"{j}.ids", [1]).value
            self.maps.append(JointMap(ids, p(f"{j}.ratio", 1.0).value,
                                      p(f"{j}.signs", [1] * len(ids)).value,
                                      p(f"{j}.zeros", [2048] * len(ids)).value))
            lo, hi = p(f"{j}.min", -math.pi).value, p(f"{j}.max", math.pi).value
            self.geom.limits[j.replace("arm_", "")] = (lo, hi)
        self.grip_id = p("gripper.id", 7).value
        self.grip_closed = p("gripper.closed", 1500).value
        self.grip_open = p("gripper.open", 2600).value
        self.poses = {}
        for name in p("pose_names", ["stow", "ready"]).value:
            self.poses[name] = [math.radians(v) for v in p(f"poses.{name}", [0.0] * 5).value]

        self.q = [0.0] * 5            # posición medida
        self.q_target = None          # objetivo actual
        self.traj: list[list[float]] = []
        self.grip = 0.0
        self.jog = None
        self.jog_time = 0.0
        self.bus = None
        self.torque_on = False

        self.pub_js = self.create_publisher(JointState, "arm/joint_states", 10)
        self.pub_tip = self.create_publisher(PoseStamped, "arm/tip_pose", 10)
        self.create_subscription(JointState, "arm/joint_command", self.on_joint_cmd, 10)
        self.create_subscription(Twist, "arm/cartesian_jog", self.on_jog, 10)
        self.create_subscription(Float64, "arm/gripper", self.on_gripper, 10)
        self.create_service(SetNamedPose, "arm/set_named_pose", self.on_named_pose)
        self.create_service(SetBool, "arm/torque", self.on_torque)
        self.connect()
        self.create_timer(1.0 / self.rate, self.tick)

    # ------------------------------------------------------------------ hardware
    def connect(self) -> None:
        if self.simulate:
            self.get_logger().info("Modo simulado: sin bus serie")
            self.q = list(self.poses.get("stow", [0.0] * 5))
            self.torque_on = True
            return
        try:
            self.bus = ft.Bus(self.port, self.baud)
        except Exception as e:  # noqa: BLE001
            self.get_logger().error(f"No puedo abrir {self.port}: {e}")
            return
        missing = [sid for m in self.maps for sid in m.ids if not self.bus.ping(sid)]
        if not self.bus.ping(self.grip_id):
            missing.append(self.grip_id)
        if missing:
            self.get_logger().error(f"Servos que no responden: {missing} (¿alimentación 12 V? ¿IDs?)")
        self.read_state()
        self.set_torque(True)

    def set_torque(self, on: bool) -> None:
        self.torque_on = on
        if self.bus is None:
            return
        for m in self.maps:
            for sid in m.ids:
                self.bus.torque(sid, on)
        self.bus.torque(self.grip_id, on)
        if on:
            self.q_target = list(self.q)   # no saltar al encender

    def read_state(self) -> None:
        if self.bus is None:
            return
        for i, m in enumerate(self.maps):
            t = self.bus.read_position(m.ids[0])
            if t is not None:
                self.q[i] = m.from_ticks(t)
        g = self.bus.read_position(self.grip_id)
        if g is not None and self.grip_open != self.grip_closed:
            self.grip = (g - self.grip_closed) / (self.grip_open - self.grip_closed)

    def write_targets(self, q: list[float]) -> None:
        if self.simulate:
            self.q = list(q)
            return
        if self.bus is None or not self.torque_on:
            return
        goals = {}
        for m, a in zip(self.maps, q):
            goals.update(m.to_ticks(a))
        goals[self.grip_id] = int(self.grip_closed + self.grip * (self.grip_open - self.grip_closed))
        self.bus.sync_goal(goals)

    # ------------------------------------------------------------------ comandos
    def plan_to(self, q_goal: list[float], duration: float = 0.0) -> None:
        q_goal = clamp_joints(q_goal, self.geom)
        start = self.q_target or self.q
        dmax = max(abs(a - b) for a, b in zip(q_goal, start))
        t = max(duration, dmax / self.max_joint_vel, 0.1)
        self.traj = interpolate(start, q_goal, max(1, int(t * self.rate)))

    def on_joint_cmd(self, msg: JointState) -> None:
        goal = list(self.q_target or self.q)
        for name, pos in zip(msg.name, msg.position):
            if name in JOINTS:
                goal[JOINTS.index(name)] = pos
        self.plan_to(goal)

    def on_jog(self, msg: Twist) -> None:
        self.jog = msg
        self.jog_time = time.monotonic()

    def on_gripper(self, msg: Float64) -> None:
        self.grip = min(1.0, max(0.0, msg.data))

    def on_named_pose(self, req, res):
        if req.name not in self.poses:
            res.success, res.message = False, f"pose desconocida: {req.name} (hay: {list(self.poses)})"
            return res
        self.jog = None
        self.plan_to(self.poses[req.name], req.duration)
        res.success, res.message = True, f"yendo a {req.name}"
        return res

    def on_torque(self, req, res):
        self.set_torque(req.data)
        res.success, res.message = True, "torque " + ("ON" if req.data else "OFF")
        return res

    # ------------------------------------------------------------------ lazo
    def apply_jog(self, dt: float) -> None:
        if self.jog is None or time.monotonic() - self.jog_time > 0.3:
            self.jog = None
            return
        base = self.q_target or self.q
        x, y, z, pitch = fk(base, self.geom)
        j = self.jog
        # lineal en el frame del brazo (rotado por J1 para que "adelante" sea hacia donde apunta)
        c, s = math.cos(base[0]), math.sin(base[0])
        x += (j.linear.x * c - j.linear.y * s) * dt
        y += (j.linear.x * s + j.linear.y * c) * dt
        z += j.linear.z * dt
        pitch += j.angular.y * dt
        try:
            q = ik(x, y, z, pitch, self.geom, j5=base[4] + j.angular.x * dt)
            q[0] += j.angular.z * dt
            self.q_target = clamp_joints(q, self.geom)
            self.traj = []
        except Unreachable:
            pass   # el operador ve que no se mueve; no spameamos el log

    def tick(self) -> None:
        dt = 1.0 / self.rate
        self.read_state()
        if self.traj:
            self.q_target = self.traj.pop(0)
        else:
            self.apply_jog(dt)
        if self.q_target is not None:
            self.write_targets(self.q_target)
        now = self.get_clock().now().to_msg()
        js = JointState()
        js.header.stamp = now
        js.name = JOINTS + ["gripper_joint"]
        js.position = [float(v) for v in self.q] + [0.0525 * self.grip]   # dedo prismático equivalente
        self.pub_js.publish(js)
        x, y, z, pitch = fk(self.q, self.geom)
        ps = PoseStamped()
        ps.header.stamp = now
        ps.header.frame_id = "arm_base_link"
        ps.pose.position.x, ps.pose.position.y, ps.pose.position.z = x, y, z
        # orientación: yaw = J1, pitch de la herramienta respecto de la horizontal
        yaw, pt = self.q[0], pitch - math.pi / 2
        cy, sy, cp, sp = math.cos(yaw / 2), math.sin(yaw / 2), math.cos(pt / 2), math.sin(pt / 2)
        ps.pose.orientation.w, ps.pose.orientation.x = cy * cp, -sy * sp
        ps.pose.orientation.y, ps.pose.orientation.z = cy * sp, sy * cp
        self.pub_tip.publish(ps)


def main() -> None:
    rclpy.init()
    node = ArmDriver()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
