import os
from glob import glob

from setuptools import find_packages, setup

PKG = "carpincho_base"

setup(
    name=PKG,
    version="0.1.0",
    packages=find_packages(exclude=["test"]),
    data_files=[
        ("share/ament_index/resource_index/packages", ["resource/" + PKG]),
        ("share/" + PKG, ["package.xml"]),
        (os.path.join("share", PKG, "config"), glob("config/*")),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="UruBots",
    maintainer_email="urubots@utec.edu.uy",
    description="Puente serie entre ROS 2 y la placa base ESP32 (orugas, flipper, IMU, batería).",
    license="MIT",
    tests_require=["pytest"],
    entry_points={
        "console_scripts": [
            "base_bridge = carpincho_base.base_bridge:main",
            "odom_relay = carpincho_base.odom_relay:main",
        ],
    },
)
