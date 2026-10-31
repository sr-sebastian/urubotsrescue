"""Lanza TODO lo que corre en el robot (Jetson):

    ros2 launch carpincho_bringup robot.launch.py                 # completo
    ros2 launch carpincho_bringup robot.launch.py lio:=false      # sin FAST-LIO (odometría de orugas)
    ros2 launch carpincho_bringup robot.launch.py arm:=false sensors:=false   # banco de pruebas

Argumentos: arm, sensors, perception, lio (FAST-LIO + mapa), autonomy, mission ("Prelim1"...)
"""
import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.conditions import IfCondition, UnlessCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def share(pkg, *p):
    return os.path.join(get_package_share_directory(pkg), *p)


def generate_launch_description():
    arm, sensors, perception = LaunchConfiguration("arm"), LaunchConfiguration("sensors"), LaunchConfiguration("perception")
    lio, autonomy, mission = LaunchConfiguration("lio"), LaunchConfiguration("autonomy"), LaunchConfiguration("mission")
    inc = lambda pkg, f, cond, args=None: IncludeLaunchDescription(  # noqa: E731
        PythonLaunchDescriptionSource(share(pkg, "launch", f)), condition=IfCondition(cond),
        launch_arguments=(args or {}).items())
    return LaunchDescription([
        DeclareLaunchArgument("arm", default_value="true"),
        DeclareLaunchArgument("sensors", default_value="true"),
        DeclareLaunchArgument("perception", default_value="true"),
        DeclareLaunchArgument("lio", default_value="true"),
        DeclareLaunchArgument("autonomy", default_value="true"),
        DeclareLaunchArgument("mission", default_value="Prelim1"),

        IncludeLaunchDescription(PythonLaunchDescriptionSource(share("carpincho_description", "launch",
                                                                     "description.launch.py")),
                                 launch_arguments={"with_arm": arm}.items()),
        # base: si hay FAST-LIO, la TF odom->base la publica odom_relay
        Node(package="carpincho_base", executable="base_bridge", output="screen", condition=IfCondition(lio),
             parameters=[share("carpincho_base", "config", "base.yaml"), {"publish_tf": False}]),
        Node(package="carpincho_base", executable="base_bridge", output="screen", condition=UnlessCondition(lio),
             parameters=[share("carpincho_base", "config", "base.yaml"), {"publish_tf": True}]),
        Node(package="carpincho_arm", executable="arm_driver", output="screen", condition=IfCondition(arm),
             parameters=[share("carpincho_arm", "config", "arm.yaml")]),

        inc("carpincho_bringup", "sensors.launch.py", sensors),
        inc("carpincho_bringup", "mapping.launch.py", lio),
        inc("carpincho_bringup", "perception.launch.py", perception, {"mission": mission}),

        Node(package="carpincho_autonomy", executable="lane_traverse", condition=IfCondition(autonomy),
             parameters=[share("carpincho_autonomy", "config", "autonomy.yaml")]),
        Node(package="carpincho_autonomy", executable="auto_flipper", condition=IfCondition(autonomy)),
        # sin autonomía igual hace falta pasar /cmd_vel_teleop -> /cmd_vel
        Node(package="topic_tools", executable="relay", name="cmd_relay", condition=UnlessCondition(autonomy),
             arguments=["/cmd_vel_teleop", "/cmd_vel"]),
        # puente para la estación de operador (Foxglove Studio por WebSocket, comprime bien por radio)
        Node(package="foxglove_bridge", executable="foxglove_bridge",
             parameters=[{"port": 8765, "send_buffer_limit": 20000000, "max_qos_depth": 5}]),
    ])
