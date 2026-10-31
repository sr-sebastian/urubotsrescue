"""Comprueba que el xacro se expande y que existen los frames que usa el resto del software."""
import os
import subprocess
import xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.dirname(HERE)

REQUIRED_LINKS = ["base_footprint", "base_link", "flipper_link", "imu_link", "livox_frame",
                  "depth_cam_optical_frame", "thermal_optical_frame", "arm_base_link", "tool_tip",
                  "gripper_cam_optical_frame"]
REQUIRED_JOINTS = ["flipper_joint", "arm_j1", "arm_j2", "arm_j3", "arm_j4", "arm_j5", "gripper_joint"]


def expand():
    # el include usa $(find carpincho_description): lo resolvemos apuntando al árbol fuente
    src = open(os.path.join(PKG, "urdf", "carpincho.urdf.xacro")).read()
    src = src.replace("$(find carpincho_description)", PKG)
    tmp = os.path.join(HERE, "_tmp.urdf.xacro")
    with open(tmp, "w") as f:
        f.write(src)
    try:
        return subprocess.run(["xacro", tmp], check=True, capture_output=True, text=True).stdout
    finally:
        os.remove(tmp)


def test_xacro_expands_and_has_frames():
    root = ET.fromstring(expand())
    links = {l.get("name") for l in root.findall("link")}
    joints = {j.get("name") for j in root.findall("joint")}
    for name in REQUIRED_LINKS:
        assert name in links, name
    for name in REQUIRED_JOINTS:
        assert name in joints, name
    # árbol: un solo padre por link
    children = [j.find("child").get("link") for j in root.findall("joint")]
    assert len(children) == len(set(children))
