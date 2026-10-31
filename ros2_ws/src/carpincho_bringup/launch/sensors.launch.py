"""Drivers de sensores: Livox Mid-360, cámara de profundidad, cámaras USB, térmica y /scan.

Los nombres de /dev/video_* los crea la regla udev (udev/99-carpincho.rules).
depth_driver: "orbbec" (Gemini 2 / Dabai) o "realsense" (D435i).
lio: con FAST-LIO el driver Livox publica CustomMsg (lo que pide FAST-LIO) y el /scan sale de la nube
     /cloud_registered_body de FAST-LIO. Sin FAST-LIO, el driver publica PointCloud2 en /livox/lidar.
"""
import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.conditions import IfCondition, LaunchConfigurationEquals, UnlessCondition
from launch.substitutions import LaunchConfiguration
from launch.launch_description_sources import AnyLaunchDescriptionSource, PythonLaunchDescriptionSource
from launch_ros.actions import Node


def usb_cam(name, dev, w=1280, h=720, fps=30, fmt="MJPG"):
    return Node(package="v4l2_camera", executable="v4l2_camera_node", namespace=name, name=name,
                parameters=[{"video_device": dev, "image_size": [w, h], "pixel_format": fmt,
                             "camera_frame_id": f"{name}_optical_frame", "time_per_frame": [1, fps]}])


def generate_launch_description():
    cfg = os.path.join(get_package_share_directory("carpincho_bringup"), "config")
    lio = LaunchConfiguration("lio")
    actions = [
        DeclareLaunchArgument("depth_driver", default_value="orbbec"),
        DeclareLaunchArgument("lio", default_value="true"),
        usb_cam("cam_front", "/dev/video_front"),
        usb_cam("cam_rear", "/dev/video_rear", 640, 480, 15),
        usb_cam("gripper_cam", "/dev/video_gripper", 1280, 720, 30),
        # térmica UVC en modo Y16 (temperatura cruda). Para P2 Pro/TC001 ver docs/05-software/percepcion.md
        Node(package="v4l2_camera", executable="v4l2_camera_node", namespace="thermal", name="thermal",
             parameters=[{"video_device": "/dev/video_thermal", "pixel_format": "Y16",
                          "output_encoding": "mono16", "camera_frame_id": "thermal_optical_frame"}],
             remappings=[("image_raw", "/thermal/image_raw")]),
        # 3D -> 2D para centrar en carriles y para el mapa 2D
        Node(package="pointcloud_to_laserscan", executable="pointcloud_to_laserscan_node", condition=IfCondition(lio),
             parameters=[os.path.join(cfg, "scan.yaml")],
             remappings=[("cloud_in", "/cloud_registered_body"), ("scan", "/scan")]),
        Node(package="pointcloud_to_laserscan", executable="pointcloud_to_laserscan_node", condition=UnlessCondition(lio),
             parameters=[os.path.join(cfg, "scan.yaml")],
             remappings=[("cloud_in", "/livox/lidar"), ("scan", "/scan")]),
    ]
    try:
        livox_dir = os.path.join(get_package_share_directory("livox_ros_driver2"), "launch_ROS2")
        # msg_ = CustomMsg (FAST-LIO) · rviz_ = PointCloud2
        actions.append(IncludeLaunchDescription(PythonLaunchDescriptionSource(
            os.path.join(livox_dir, "msg_MID360_launch.py")), condition=IfCondition(lio)))
        actions.append(IncludeLaunchDescription(PythonLaunchDescriptionSource(
            os.path.join(livox_dir, "rviz_MID360_launch.py")), condition=UnlessCondition(lio)))
    except Exception:  # noqa: BLE001
        print("[sensors] livox_ros_driver2 no instalado: sin LiDAR")
    try:
        ob = os.path.join(get_package_share_directory("orbbec_camera"), "launch", "gemini2.launch.py")
        actions.append(IncludeLaunchDescription(PythonLaunchDescriptionSource(ob),
                                                condition=LaunchConfigurationEquals("depth_driver", "orbbec"),
                                                launch_arguments={"camera_name": "depth_cam",
                                                                  "depth_registration": "true"}.items()))
    except Exception:  # noqa: BLE001
        print("[sensors] orbbec_camera no instalado")
    try:
        rs = os.path.join(get_package_share_directory("realsense2_camera"), "launch", "rs_launch.py")
        actions.append(IncludeLaunchDescription(AnyLaunchDescriptionSource(rs),
                                                condition=LaunchConfigurationEquals("depth_driver", "realsense"),
                                                launch_arguments={"camera_name": "depth_cam", "align_depth.enable": "true",
                                                                  "pointcloud.enable": "false"}.items()))
    except Exception:  # noqa: BLE001
        print("[sensors] realsense2_camera no instalado")
    return LaunchDescription(actions)
