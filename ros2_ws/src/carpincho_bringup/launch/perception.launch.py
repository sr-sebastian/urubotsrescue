"""Percepción: detectores sobre las cámaras + POIs + exportador de misión."""
import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node

DETS = ("detections", "/perception/detections")


def generate_launch_description():
    cfg = os.path.join(get_package_share_directory("carpincho_bringup"), "config", "perception.yaml")
    color = "/depth_cam/color/image_raw"
    return LaunchDescription([
        DeclareLaunchArgument("mission", default_value="Prelim1"),
        Node(package="carpincho_perception", executable="qr_detector", name="qr_front", parameters=[cfg],
             remappings=[("image", color), DETS, ("image_annotated", "/qr_front/image")]),
        Node(package="carpincho_perception", executable="qr_detector", name="qr_gripper", parameters=[cfg],
             remappings=[("image", "/gripper_cam/image_raw"), DETS, ("image_annotated", "/qr_gripper/image")]),
        Node(package="carpincho_perception", executable="hazmat_detector", name="hazmat", parameters=[cfg],
             remappings=[("image", color), DETS, ("image_annotated", "/hazmat/image")]),
        Node(package="carpincho_perception", executable="motion_detector", name="motion", parameters=[cfg],
             remappings=[("image", "/gripper_cam/image_raw"), DETS, ("image_annotated", "/motion/image")]),
        Node(package="carpincho_perception", executable="thermal_viewer", name="thermal_viewer", parameters=[cfg],
             remappings=[DETS]),
        Node(package="apriltag_ros", executable="apriltag_node", name="apriltag", parameters=[cfg],
             remappings=[("image_rect", color), ("camera_info", "/depth_cam/color/camera_info")]),
        Node(package="carpincho_perception", executable="poi_manager", parameters=[cfg]),
        Node(package="carpincho_perception", executable="mission_exporter", parameters=[
            cfg, {"mission": LaunchConfiguration("mission")}]),
    ])
