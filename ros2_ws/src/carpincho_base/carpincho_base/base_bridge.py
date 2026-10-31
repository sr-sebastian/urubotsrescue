"""Nodo puente ROS 2 <-> placa base ESP32.

Suscribe:
  /cmd_vel               geometry_msgs/Twist        velocidad del robot
  /flipper/position_cmd  std_msgs/Float64           ángulo objetivo del flipper [rad]
  /flipper/velocity_cmd  std_msgs/Float64           velocidad del flipper [rad/s]
  /base/lights           std_msgs/UInt8             focos 0..255
  /base/led_mode         std_msgs/UInt8             0 normal, 1 autónomo (azul)
Publica:
  /odom                  nav_msgs/Odometry          (y TF odom->base_footprint si publish_tf)
  /imu/data              sensor_msgs/Imu
  /joint_states          sensor_msgs/JointState     flipper_joint
  /battery               sensor_msgs/BatteryState
  /base/status           carpincho_interfaces/BaseStatus
  /arm/hall              std_msgs/Float32           sensor Hall de la punta [mT]
Servicios:
  /base/enable           std_srvs/SetBool           armar/desarmar motores
  /base/zero_flipper     std_srvs/Trigger           el ángulo actual es 0 (flipper horizontal)
"""

from __future__ import annotations

import math
import threading
import time

import rclpy
from rclpy.executors import ExternalShutdownException
from geometry_msgs.msg import TransformStamped, Twist
from nav_msgs.msg import Odometry as OdometryMsg
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy
from sensor_msgs.msg import BatteryState, Imu, JointState
from std_msgs.msg import Float32, Float64, UInt8
from std_srvs.srv import SetBool, Trigger
from tf2_ros import TransformBroadcaster

from carpincho_interfaces.msg import BaseStatus

from . import protocol as proto
from .kinematics import Odometry, TrackGeometry, quat_from_yaw, tracks_to_twist, twist_to_tracks, yaw_from_quat

try:
    import serial  # pyserial
except ImportError:  # pragma: no cover
    serial = None


class BaseBridge(Node):
    def __init__(self) -> None:
        super().__init__("base_bridge")
        p = self.declare_parameter
        self.port = p("port", "/dev/carpincho_base").value
        self.baud = p("baud", 921600).value
        self.geom = TrackGeometry(p("track_separation", 0.275).value, p("slip_factor", 1.6).value)
        self.v_max = p("max_speed", 0.4).value
        self.cmd_timeout = p("cmd_timeout", 0.5).value
        self.publish_tf = p("publish_tf", True).value
        self.use_imu_yaw = p("use_imu_yaw", True).value
        self.odom_frame = p("odom_frame", "odom").value
        self.base_frame = p("base_frame", "base_footprint").value
        self.imu_frame = p("imu_frame", "imu_link").value
        self.flip_joint = p("flipper_joint", "flipper_joint").value
        self.auto_enable = p("auto_enable", False).value
        self.pid = [p(k, v).value for k, v in (("kp", 0.8), ("ki", 4.0), ("kff", 2.38), ("max_accel", 1.0),
                                                ("flip_kp", 3.0), ("flip_max_vel", 1.5))]

        self.odom = Odometry()
        self.lock = threading.Lock()
        self.seq = 0
        self.ser = None
        self.rx = proto.Receiver()
        self.last_cmd_time = 0.0
        self.cmd = (0.0, 0.0)
        self.enabled = self.auto_enable
        self.lights = 0
        self.led_mode = 0
        self.last_state: proto.State | None = None
        self.last_aux: proto.Aux | None = None
        self.last_rx_time = 0.0
        self.prev_enc = None
        self.yaw0 = None
        self.imu_yaw = None
        self.counts_per_m = p("counts_per_m", 7 * 4 * 51 * 1.5 / (math.pi * 0.09549)).value
        self.enc_sign = (-1.0 if p("invert_left_encoder", False).value else 1.0,
                         -1.0 if p("invert_right_encoder", True).value else 1.0)

        qos = QoSProfile(depth=10, reliability=ReliabilityPolicy.RELIABLE)
        self.pub_odom = self.create_publisher(OdometryMsg, "odom", qos)
        self.pub_imu = self.create_publisher(Imu, "imu/data", qos)
        self.pub_js = self.create_publisher(JointState, "joint_states", qos)
        self.pub_batt = self.create_publisher(BatteryState, "battery", qos)
        self.pub_status = self.create_publisher(BaseStatus, "base/status", qos)
        self.pub_hall = self.create_publisher(Float32, "arm/hall", qos)
        self.tf = TransformBroadcaster(self) if self.publish_tf else None

        self.create_subscription(Twist, "cmd_vel", self.on_cmd_vel, 10)
        self.create_subscription(Float64, "flipper/position_cmd", self.on_flip_pos, 10)
        self.create_subscription(Float64, "flipper/velocity_cmd", self.on_flip_vel, 10)
        self.create_subscription(UInt8, "base/lights", self.on_lights, 10)
        self.create_subscription(UInt8, "base/led_mode", self.on_led_mode, 10)
        self.create_service(SetBool, "base/enable", self.on_enable)
        self.create_service(Trigger, "base/zero_flipper", self.on_zero_flipper)

        self.create_timer(0.02, self.tick_tx)      # 50 Hz comandos
        self.create_timer(0.2, self.tick_aux)      # 5 Hz luces/armado + heartbeat
        self.create_timer(1.0, self.tick_status)   # reconexión y diagnóstico
        threading.Thread(target=self.reader, daemon=True).start()

    # ------------------------------------------------------------------ serie
    def open_port(self) -> bool:
        if serial is None:
            self.get_logger().error("Falta pyserial: sudo apt install python3-serial")
            return False
        try:
            self.ser = serial.Serial(self.port, self.baud, timeout=0.05)
            self.get_logger().info(f"Conectado a la placa base en {self.port}")
            self.send(proto.CMD_GET_INFO)
            self.send(proto.CMD_CONFIG, proto.config(*self.pid))
            return True
        except Exception as e:  # noqa: BLE001
            self.ser = None
            self.get_logger().warn(f"No puedo abrir {self.port}: {e}", throttle_duration_sec=5.0)
            return False

    def send(self, msg_id: int, payload: bytes = b"") -> None:
        with self.lock:
            if self.ser is None:
                return
            try:
                self.ser.write(proto.build_frame(msg_id, self.seq, payload))
                self.seq = (self.seq + 1) & 0xFF
            except Exception as e:  # noqa: BLE001
                self.get_logger().error(f"Error escribiendo al ESP32: {e}")
                self.ser = None

    def reader(self) -> None:
        while rclpy.ok():
            if self.ser is None:
                time.sleep(0.5)
                continue
            try:
                data = self.ser.read(256)
            except Exception as e:  # noqa: BLE001
                self.get_logger().error(f"Se perdió el puerto serie: {e}")
                self.ser = None
                continue
            for pkt in self.rx.feed(data):
                self.last_rx_time = time.monotonic()
                self.dispatch(proto.parse(pkt))

    # ------------------------------------------------------------------ recepción
    def dispatch(self, m) -> None:
        if isinstance(m, proto.State):
            self.on_state(m)
        elif isinstance(m, proto.Imu):
            self.on_imu(m)
        elif isinstance(m, proto.Aux):
            self.last_aux = m
            self.pub_hall.publish(Float32(data=float(m.hall_mT)))
        elif isinstance(m, str):
            self.get_logger().info(f"[ESP32] {m}")

    def on_state(self, s: proto.State) -> None:
        now = self.get_clock().now().to_msg()
        if self.prev_enc is not None:
            dl = self.enc_sign[0] * (s.enc_left - self.prev_enc[0]) / self.counts_per_m
            dr = self.enc_sign[1] * (s.enc_right - self.prev_enc[1]) / self.counts_per_m
            yaw = None
            if self.use_imu_yaw and self.imu_yaw is not None:
                yaw = self.imu_yaw
            self.odom.update(dl, dr, self.geom, yaw)
        self.prev_enc = (s.enc_left, s.enc_right)
        self.last_state = s
        if s.faults & 0x80 and self.enabled:
            # el firmware se desarma solo con el E-stop; acá también, para que al soltar el hongo
            # el robot NO arranque hasta que el operador vuelva a armar (START)
            self.enabled = False
            self.get_logger().warn("E-STOP apretado: motores desarmados (re-armar con START)")

        v, w = tracks_to_twist(s.v_left, s.v_right, self.geom)
        od = OdometryMsg()
        od.header.stamp = now
        od.header.frame_id = self.odom_frame
        od.child_frame_id = self.base_frame
        od.pose.pose.position.x = self.odom.x
        od.pose.pose.position.y = self.odom.y
        qx, qy, qz, qw = quat_from_yaw(self.odom.yaw)
        od.pose.pose.orientation.x, od.pose.pose.orientation.y = qx, qy
        od.pose.pose.orientation.z, od.pose.pose.orientation.w = qz, qw
        od.twist.twist.linear.x = v
        od.twist.twist.angular.z = w
        # orugas: mucha incertidumbre en el giro
        od.pose.covariance[0] = od.pose.covariance[7] = 0.01
        od.pose.covariance[35] = 0.05
        od.twist.covariance[0] = 0.01
        od.twist.covariance[35] = 0.1
        self.pub_odom.publish(od)
        if self.tf is not None:
            t = TransformStamped()
            t.header = od.header
            t.child_frame_id = self.base_frame
            t.transform.translation.x = self.odom.x
            t.transform.translation.y = self.odom.y
            t.transform.rotation = od.pose.pose.orientation
            self.tf.sendTransform(t)

        js = JointState()
        js.header.stamp = now
        js.name = [self.flip_joint]
        js.position = [float(s.flip_angle)]
        js.velocity = [float(s.flip_vel)]
        self.pub_js.publish(js)

        b = BatteryState()
        b.header.stamp = now
        b.voltage = s.batt_mv / 1000.0
        b.current = -s.batt_ca / 100.0
        b.percentage = proto.battery_percent_6s(b.voltage) / 100.0
        b.power_supply_technology = BatteryState.POWER_SUPPLY_TECHNOLOGY_LION
        b.present = s.batt_mv > 5000
        self.pub_batt.publish(b)

    def on_imu(self, m: proto.Imu) -> None:
        msg = Imu()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = self.imu_frame
        msg.orientation.w, msg.orientation.x, msg.orientation.y, msg.orientation.z = m.qw, m.qx, m.qy, m.qz
        msg.angular_velocity.x, msg.angular_velocity.y, msg.angular_velocity.z = m.gx, m.gy, m.gz
        msg.linear_acceleration.x, msg.linear_acceleration.y, msg.linear_acceleration.z = m.ax, m.ay, m.az
        msg.orientation_covariance[0] = msg.orientation_covariance[4] = 0.01
        msg.orientation_covariance[8] = 0.02
        msg.angular_velocity_covariance[0] = msg.angular_velocity_covariance[4] = 1e-3
        msg.angular_velocity_covariance[8] = 1e-3
        msg.linear_acceleration_covariance[0] = msg.linear_acceleration_covariance[4] = 0.05
        msg.linear_acceleration_covariance[8] = 0.05
        self.pub_imu.publish(msg)
        yaw = yaw_from_quat(m.qw, m.qx, m.qy, m.qz)
        if self.yaw0 is None and (m.qw or m.qx or m.qy or m.qz):
            self.yaw0 = yaw
        if self.yaw0 is not None:
            self.imu_yaw = math.atan2(math.sin(yaw - self.yaw0), math.cos(yaw - self.yaw0))

    # ------------------------------------------------------------------ comandos
    def on_cmd_vel(self, msg: Twist) -> None:
        self.cmd = twist_to_tracks(msg.linear.x, msg.angular.z, self.geom, self.v_max)
        self.last_cmd_time = time.monotonic()

    def on_flip_pos(self, msg: Float64) -> None:
        self.send(proto.CMD_FLIPPER, proto.flipper(proto.FLIP_MODE_POSITION, msg.data))

    def on_flip_vel(self, msg: Float64) -> None:
        self.send(proto.CMD_FLIPPER, proto.flipper(proto.FLIP_MODE_VELOCITY, msg.data))

    def on_lights(self, msg: UInt8) -> None:
        self.lights = msg.data

    def on_led_mode(self, msg: UInt8) -> None:
        self.led_mode = msg.data

    def on_enable(self, req, res):
        self.enabled = bool(req.data)
        self.tick_aux()
        res.success = True
        res.message = "motores habilitados" if self.enabled else "motores deshabilitados"
        self.get_logger().info(res.message)
        return res

    def on_zero_flipper(self, req, res):
        self.send(proto.CMD_ZERO_FLIPPER)
        res.success = True
        res.message = "cero del flipper enviado (poné el flipper horizontal hacia adelante antes)"
        return res

    def tick_tx(self) -> None:
        if time.monotonic() - self.last_cmd_time > self.cmd_timeout:
            self.cmd = (0.0, 0.0)
        self.send(proto.CMD_DRIVE, proto.drive(*self.cmd))

    def tick_aux(self) -> None:
        self.send(proto.CMD_AUX, proto.aux(self.lights, self.led_mode, self.enabled))
        self.send(proto.CMD_HEARTBEAT, proto.heartbeat(int(time.monotonic() * 1000)))

    def tick_status(self) -> None:
        if self.ser is None:
            self.open_port()
        st = BaseStatus()
        st.header.stamp = self.get_clock().now().to_msg()
        st.link_ok = (time.monotonic() - self.last_rx_time) < 0.5
        st.crc_errors = self.rx.crc_errors
        s = self.last_state
        if s is not None:
            st.battery_voltage = s.batt_mv / 1000.0
            st.battery_current = s.batt_ca / 100.0
            st.battery_percent = proto.battery_percent_6s(st.battery_voltage)
            st.faults = s.faults
            st.fault_names = proto.fault_names(s.faults)
            st.estop_active = bool(s.faults & 0x80)
            st.motors_enabled = s.motors_enabled
            st.flipper_calibrated = s.flipper_calibrated
        if self.last_aux is not None:
            st.hall_mt = float(self.last_aux.hall_mT)
            st.mcu_temp = self.last_aux.board_temp_c10 / 10.0
            st.loop_us_max = self.last_aux.loop_us_max
        self.pub_status.publish(st)
        if not st.link_ok and self.ser is not None:
            self.get_logger().warn("Sin tramas del ESP32 (¿firmware? ¿cable USB?)", throttle_duration_sec=5.0)


def main() -> None:
    rclpy.init()
    node = BaseBridge()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        node.send(proto.CMD_DRIVE, proto.drive(0.0, 0.0))
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
