# Instalación del Jetson (y de la notebook del operador)

Objetivo: dejar un Jetson Orin Nano que, al encenderse, levante todo el software del robot.

## 1. Sistema base

1. Flashear **JetPack 6.x** (Ubuntu 22.04) con SDK Manager **en el NVMe** (no en la microSD).
2. Usuario `carpincho`, hostname `carpincho`. Modo de energía máximo:
   ```bash
   sudo nvpmodel -m 0 && sudo jetson_clocks      # "Super": 25 W
   ```
3. Red: IP fija `192.168.8.10` en la interfaz que va al router del robot. El Livox usa la red `192.168.1.x`:
   asignar también `192.168.1.50/24` a la Ethernet (alias) o usar un switch con VLAN. Ver la configuración
   de IP del Mid-360 en `livox_ros_driver2/config/MID360_config.json`.
4. Desactivar la suspensión, el escritorio gráfico si no se usa (`sudo systemctl set-default multi-user.target`)
   y las actualizaciones automáticas (no querés que se actualice el día de la competencia).

## 2. ROS 2 Humble

```bash
sudo apt update && sudo apt install -y software-properties-common curl
sudo curl -sSL https://raw.githubusercontent.com/ros/rosdistro/master/ros.key -o /usr/share/keyrings/ros-archive-keyring.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/ros-archive-keyring.gpg] http://packages.ros.org/ros2/ubuntu jammy main" | sudo tee /etc/apt/sources.list.d/ros2.list
sudo apt update
sudo apt install -y ros-humble-ros-base ros-humble-xacro ros-humble-robot-state-publisher \
  ros-humble-joint-state-publisher ros-humble-joy ros-humble-v4l2-camera ros-humble-cv-bridge \
  ros-humble-pointcloud-to-laserscan ros-humble-octomap-server ros-humble-apriltag-ros \
  ros-humble-foxglove-bridge ros-humble-topic-tools ros-humble-rmw-cyclonedds-cpp \
  ros-humble-tf2-geometry-msgs ros-humble-sensor-msgs-py \
  python3-colcon-common-extensions python3-serial python3-opencv python3-pip
```

## 3. Drivers de fuente

```bash
mkdir -p ~/ros2_ws/src && cd ~/ros2_ws/src
git clone https://github.com/sr-sebastian/urubotsrescue.git          # este repo
ln -s urubotsrescue/ros2_ws/src/* .                                     # paquetes carpincho_*
# Livox SDK2 + driver ROS 2
git clone https://github.com/Livox-SDK/Livox-SDK2.git ~/Livox-SDK2
cd ~/Livox-SDK2 && mkdir build && cd build && cmake .. && make -j4 && sudo make install
cd ~/ros2_ws/src && git clone https://github.com/Livox-SDK/livox_ros_driver2.git
# FAST-LIO (rama ROS 2)
git clone --recursive -b ROS2 https://github.com/hku-mars/FAST_LIO.git
# Cámara de profundidad: Orbbec
git clone https://github.com/orbbec/OrbbecSDK_ROS2.git
```

> El driver de Livox para ROS 2 se compila con su script (`./build.sh humble`) o, en un workspace común,
> siguiendo su README. Si FAST-LIO no encuentra `livox_ros_driver2`, compilá primero el driver y hacé `source`.

```bash
cd ~/ros2_ws
rosdep install --from-paths src --ignore-src -y
colcon build --symlink-install --cmake-args -DCMAKE_BUILD_TYPE=Release
echo "source ~/ros2_ws/install/setup.bash" >> ~/.bashrc
```

## 4. Percepción (YOLO con TensorRT)

```bash
pip3 install "ultralytics>=8.3"          # instala torch para Jetson: usar la rueda de NVIDIA para JetPack 6
yolo export model=hazmat_yolov8n.pt format=engine half=True imgsz=640   # en el Jetson, ~5 min
mkdir -p ~/modelos && mv hazmat_yolov8n.engine ~/modelos/
```

PyTorch para Jetson: instalar la rueda que publica NVIDIA para tu versión de JetPack (no la de PyPI).

## 5. Dispositivos y arranque automático

```bash
sudo cp ~/ros2_ws/src/urubotsrescue/ros2_ws/src/carpincho_bringup/udev/99-carpincho.rules /etc/udev/rules.d/
sudo udevadm control --reload && sudo udevadm trigger
ls -l /dev/carpincho_* /dev/video_*        # tienen que aparecer los symlinks
sudo usermod -aG dialout,video,plugdev carpincho
sudo cp ~/ros2_ws/src/urubotsrescue/ros2_ws/src/carpincho_bringup/systemd/carpincho.service /etc/systemd/system/
sudo systemctl enable --now carpincho
journalctl -u carpincho -f
```

Para las cámaras, primero hay que completar en la regla udev los `ID_PATH` reales
(`udevadm info -q property -n /dev/video0 | grep ID_PATH`), con cada cámara en un puerto fijo y marcado.

## 6. DDS y red

En **robot y notebook** (`~/.bashrc`):

```bash
export ROS_DOMAIN_ID=42
export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
export CYCLONEDDS_URI=file://$HOME/ros2_ws/install/carpincho_bringup/share/carpincho_bringup/config/cyclonedds.xml
```

Ajustar las IPs de los peers en `cyclonedds.xml`. Más detalles en [comunicaciones.md](comunicaciones.md).

## 7. Notebook del operador

Ubuntu 22.04 + ROS 2 Humble (`ros-humble-desktop`), el mismo workspace (solo hace falta compilar
`carpincho_interfaces` y `carpincho_teleop`) y **Foxglove Studio**. Joystick por USB (cable, no Bluetooth).

```bash
ros2 launch carpincho_bringup operator.launch.py
```

En Foxglove: *Open connection* → `ws://192.168.8.10:8765` → importar el layout `operator/foxglove_layout.json`.

## 8. Desarrollo sin robot (cualquier PC con Ubuntu 22.04/24.04)

```bash
python3 tools/fake_base.py                       # imprime /dev/pts/N
ros2 run carpincho_base base_bridge --ros-args -p port:=/dev/pts/N -p auto_enable:=true
ros2 run carpincho_arm arm_driver --ros-args --params-file ros2_ws/src/carpincho_arm/config/arm.yaml -p simulate:=true
ros2 launch carpincho_description display.launch.py     # URDF en RViz con sliders
```
