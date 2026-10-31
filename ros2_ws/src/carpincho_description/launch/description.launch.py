"""Solo robot_state_publisher (lo incluye el bringup del robot real)."""
import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import Command, LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():
    share = get_package_share_directory("carpincho_description")
    xacro_file = os.path.join(share, "urdf", "carpincho.urdf.xacro")
    with_arm = LaunchConfiguration("with_arm")
    desc = ParameterValue(Command(["xacro ", xacro_file, " with_arm:=", with_arm]), value_type=str)
    return LaunchDescription([
        DeclareLaunchArgument("with_arm", default_value="true"),
        Node(package="robot_state_publisher", executable="robot_state_publisher",
             parameters=[{"robot_description": desc, "publish_frequency": 30.0}],
             remappings=[("joint_states", "joint_states_merged")]),
        # junta /joint_states (flipper, del base_bridge) y /arm/joint_states (brazo)
        Node(package="joint_state_publisher", executable="joint_state_publisher",
             parameters=[{"source_list": ["joint_states", "arm/joint_states"], "rate": 30}],
             remappings=[("joint_states", "joint_states_merged")]),
    ])
