import os
from glob import glob

from setuptools import find_packages, setup

PKG = "carpincho_perception"

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
    description="Percepción: QR, hazmat (YOLO), movimiento, térmica, POIs y exportación de mapas RRL.",
    license="MIT",
    tests_require=["pytest"],
    entry_points={
        "console_scripts": [
            "qr_detector = carpincho_perception.qr_detector:main",
            "hazmat_detector = carpincho_perception.hazmat_detector:main",
            "motion_detector = carpincho_perception.motion_detector:main",
            "thermal_viewer = carpincho_perception.thermal_viewer:main",
            "poi_manager = carpincho_perception.poi_manager:main",
            "mission_exporter = carpincho_perception.mission_exporter:main",
        ],
    },
)
