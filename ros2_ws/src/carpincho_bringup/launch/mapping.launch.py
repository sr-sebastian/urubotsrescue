"""Mapeo 3D con FAST-LIO (Livox Mid-360) + proyección 2D con octomap_server.

  FAST-LIO  -> /Odometry (camera_init->body), /Laser_map (nube registrada), /cloud_registered
  odom_relay -> TF map->odom->base_footprint
  octomap_server -> /projected_map (=/map, OccupancyGrid para el GeoTIFF y Nav2)
"""
import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    cfg = os.path.join(get_package_share_directory("carpincho_bringup"), "config")
    return LaunchDescription([
        Node(package="fast_lio", executable="fastlio_mapping", output="screen",
             parameters=[os.path.join(cfg, "fast_lio_mid360.yaml")]),
        Node(package="carpincho_base", executable="odom_relay", output="screen"),
        Node(package="octomap_server", executable="octomap_server_node", name="octomap_server",
             parameters=[os.path.join(cfg, "octomap.yaml")],
             remappings=[("cloud_in", "/cloud_registered"), ("projected_map", "/map")]),
    ])
