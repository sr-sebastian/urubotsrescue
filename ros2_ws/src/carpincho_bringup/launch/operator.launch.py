"""Estación de operador (notebook): joystick + teleop. La visualización va por Foxglove Studio
(conectar a ws://<ip-robot>:8765, layout en operator/foxglove_layout.json) o RViz.

    ros2 launch carpincho_bringup operator.launch.py
"""
import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    teleop_cfg = os.path.join(get_package_share_directory("carpincho_teleop"), "config", "teleop.yaml")
    rviz_cfg = os.path.join(get_package_share_directory("carpincho_description"), "rviz", "carpincho.rviz")
    return LaunchDescription([
        DeclareLaunchArgument("rviz", default_value="false"),
        Node(package="joy", executable="joy_node", name="joy_node", parameters=[teleop_cfg]),
        Node(package="carpincho_teleop", executable="joy_teleop", parameters=[teleop_cfg], output="screen"),
        Node(package="rviz2", executable="rviz2", arguments=["-d", rviz_cfg], condition=IfCondition(LaunchConfiguration("rviz"))),
    ])
