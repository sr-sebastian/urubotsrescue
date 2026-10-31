import os
from glob import glob

from setuptools import find_packages, setup

PKG = "carpincho_arm"

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
    description="Driver del brazo C1 (servos Feetech STS3215), cinemática y poses.",
    license="MIT",
    tests_require=["pytest"],
    entry_points={
        "console_scripts": [
            "arm_driver = carpincho_arm.arm_driver:main",
        ],
    },
)
