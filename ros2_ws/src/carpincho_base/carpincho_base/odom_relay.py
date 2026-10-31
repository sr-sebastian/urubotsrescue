"""Convierte la odometría LiDAR-inercial de FAST-LIO en TF odom -> base_footprint.

FAST-LIO publica /Odometry como camera_init -> body, donde `body` es el IMU del Livox (livox_frame).
Nuestro árbol ya tiene base_footprint -> ... -> livox_frame, así que no podemos dejar que FAST-LIO
publique TF (livox_frame tendría dos padres). Este nodo calcula:

    T_odom_base(t) = T_base_livox · T_ci_body(t) · T_base_livox⁻¹

(el frame odom coincide con base_footprint al arrancar) y publica odom->base_footprint + /odom_lio.
Además publica map->odom identidad: con FAST-LIO el mapa ya está en el frame odom.
Poner publish_tf: false en base_bridge cuando se usa este nodo.
"""

from __future__ import annotations

import rclpy
from rclpy.executors import ExternalShutdownException
from geometry_msgs.msg import TransformStamped
from nav_msgs.msg import Odometry
from rclpy.node import Node
from tf2_ros import Buffer, StaticTransformBroadcaster, TransformBroadcaster, TransformListener

from .se3 import compose, from_msg, invert


class OdomRelay(Node):
    def __init__(self) -> None:
        super().__init__("odom_relay")
        self.base = self.declare_parameter("base_frame", "base_footprint").value
        self.lidar = self.declare_parameter("lidar_frame", "livox_frame").value
        self.odom = self.declare_parameter("odom_frame", "odom").value
        self.map = self.declare_parameter("map_frame", "map").value
        self.tf_buf = Buffer()
        self.tf_listener = TransformListener(self.tf_buf, self)
        self.tfb = TransformBroadcaster(self)
        self.static = StaticTransformBroadcaster(self)
        self.T_bl = None
        self.pub = self.create_publisher(Odometry, "odom_lio", 10)
        self.create_subscription(Odometry, "/Odometry", self.on_odom, 50)
        t = TransformStamped()
        t.header.frame_id, t.child_frame_id = self.map, self.odom
        t.transform.rotation.w = 1.0
        self.static.sendTransform(t)

    def on_odom(self, m: Odometry) -> None:
        if self.T_bl is None:
            try:
                tr = self.tf_buf.lookup_transform(self.base, self.lidar, rclpy.time.Time())
            except Exception:  # noqa: BLE001
                self.get_logger().warn("Esperando TF base_footprint->livox_frame", throttle_duration_sec=2.0)
                return
            self.T_bl = (
                (tr.transform.translation.x, tr.transform.translation.y, tr.transform.translation.z),
                (tr.transform.rotation.w, tr.transform.rotation.x, tr.transform.rotation.y, tr.transform.rotation.z),
            )
        p, q = m.pose.pose.position, m.pose.pose.orientation
        T_cb = from_msg((p.x, p.y, p.z), (q.w, q.x, q.y, q.z))
        T = compose(compose(self.T_bl, T_cb), invert(self.T_bl))
        (x, y, z), (qw, qx, qy, qz) = T
        t = TransformStamped()
        t.header.stamp = m.header.stamp
        t.header.frame_id, t.child_frame_id = self.odom, self.base
        t.transform.translation.x, t.transform.translation.y, t.transform.translation.z = x, y, z
        t.transform.rotation.w, t.transform.rotation.x = qw, qx
        t.transform.rotation.y, t.transform.rotation.z = qy, qz
        self.tfb.sendTransform(t)
        o = Odometry()
        o.header = t.header
        o.child_frame_id = self.base
        o.pose.pose.position.x, o.pose.pose.position.y, o.pose.pose.position.z = x, y, z
        o.pose.pose.orientation = t.transform.rotation
        o.twist = m.twist
        self.pub.publish(o)


def main() -> None:
    rclpy.init()
    n = OdomRelay()
    try:
        rclpy.spin(n)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        n.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
