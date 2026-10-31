import os
from glob import glob

from setuptools import find_packages, setup

PKG = "carpincho_autonomy"

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
    description="Comportamientos autónomos: travesía de carril ida/vuelta, flippers automáticos.",
    license="MIT",
    tests_require=["pytest"],
    entry_points={
        "console_scripts": [
            "lane_traverse = carpincho_autonomy.lane_traverse:main",
            "auto_flipper = carpincho_autonomy.auto_flipper:main",
        ],
    },
)
