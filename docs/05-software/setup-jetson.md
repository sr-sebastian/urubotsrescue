# Instalación del Jetson (y de la notebook del operador)

Objetivo: dejar un Jetson Orin Nano que, al encenderse, levante todo el software del robot.

## 1. Sistema base y versión de ROS

**Objetivo: ROS 2 Jazzy** (LTS hasta mayo de 2029). Humble termina su soporte en mayo de 2027, justo antes de la
competencia: no arrancar un proyecto 2027 con Humble.

Jazzy necesita Ubuntu 24.04. Al momento de comprar, fijate qué JetPack hay para Orin:

| Caso | Cómo instalar |
|---|---|
| **Hay JetPack con Ubuntu 24.04 para Orin** (la línea JetPack 7.x) | ROS 2 Jazzy nativo por apt (sección 2). Es lo más simple |
| **Solo JetPack 6 (Ubuntu 22.04)** | ROS 2 Jazzy dentro de un contenedor Docker Ubuntu 24.04 con `--runtime nvidia --network host --privileged -v /dev:/dev` (sección 2b) |

1. Flashear el JetPack elegido con SDK Manager **en el NVMe** (no en la microSD).
2. Usuario `carpincho`, hostname `carpincho`. Modo de energía máximo:
   ```bash
   sudo nvpmodel -m 0 && sudo jetson_clocks      # máximo rendimiento (modo "Super" en el Orin Nano)
   ```
3. Red: IP fija `192.168.8.10` en la interfaz que va al router del robot. El Livox usa la red `192.168.1.x`:
   asignar también `192.168.1.50/24` a la Ethernet (alias) o usar un switch con VLAN. Ver la configuración
   de IP del Mid-360 en `livox_ros_driver2/config/MID360_config.json`.
4. Desactivar la suspensión, el escritorio gráfico si no se usa (`sudo systemctl set-default multi-user.target`)
   y las actualizaciones automáticas (no querés que se actualice el día de la competencia).

## 2. ROS 2 Jazzy (nativo, Ubuntu 24.04)

```bash
sudo apt update && sudo apt install -y software-properties-common curl
sudo curl -sSL https://raw.githubusercontent.com/ros/rosdistro/master/ros.key -o /usr/share/keyrings/ros-archive-keyring.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/ros-archive-keyring.gpg] http://packages.ros.org/ros2/ubuntu noble main" | sudo tee /etc/apt/sources.list.d/ros2.list
sudo apt update
sudo apt install -y ros-jazzy-ros-base ros-jazzy-xacro ros-jazzy-robot-state-publisher \
  ros-jazzy-joint-state-publisher ros-jazzy-joy ros-jazzy-v4l2-camera ros-jazzy-cv-bridge \
  ros-jazzy-pointcloud-to-laserscan ros-jazzy-octomap-server ros-jazzy-apriltag-ros \
  ros-jazzy-foxglove-bridge ros-jazzy-topic-tools ros-jazzy-rmw-cyclonedds-cpp \
  ros-jazzy-tf2-geometry-msgs ros-jazzy-sensor-msgs-py ros-jazzy-image-transport-plugins \
  python3-colcon-common-extensions python3-serial python3-opencv python3-pip
```

Si algún paquete no está publicado para Jazzy en ese momento, compilarlo de fuente en el workspace.

## 2b. ROS 2 Jazzy en Docker (si el Jetson tiene JetPack 6)

```bash
# imagen base con CUDA/TensorRT para Jetson + Ubuntu 24.04 (ver jetson-containers de dusty-nv para la vigente)
docker run -d --name carpincho --restart unless-stopped --runtime nvidia --network host --privileged \
  -v /dev:/dev -v $HOME/ros2_ws:/ros2_ws -v $HOME/modelos:/modelos <imagen-jazzy-l4t> sleep infinity
docker exec -it carpincho bash        # adentro: instalar como en la sección 2 y compilar el workspace
```

`--network host` es necesario para DDS y el Livox; `--privileged -v /dev:/dev`, para el ESP32, los servos y las cámaras.
El servicio systemd (sección 5) en ese caso hace `docker exec carpincho ros2 launch ...`.

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

> El driver de Livox para ROS 2 se compila con su script (`./build.sh <distro>`, si ya soporta Jazzy) o con colcon
> en el mismo workspace, siguiendo su README. Si FAST-LIO no encuentra `livox_ros_driver2`, compilá primero el driver y hacé `source`.

```bash
cd ~/ros2_ws
rosdep install --from-paths src --ignore-src -y
colcon build --symlink-install --cmake-args -DCMAKE_BUILD_TYPE=Release
echo "source ~/ros2_ws/install/setup.bash" >> ~/.bashrc
```

## 4. Percepción (YOLO con TensorRT)

```bash
pip3 install ultralytics                 # torch para Jetson: usar la rueda de NVIDIA para tu JetPack (no la de PyPI)
yolo export model=hazmat_yolo_n.pt format=engine half=True imgsz=640   # en el Jetson, ~5 min
mkdir -p ~/modelos && mv hazmat_yolo_n.engine ~/modelos/
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

Ubuntu 24.04 + ROS 2 Jazzy (`ros-jazzy-desktop`), el mismo workspace (solo hace falta compilar
`carpincho_interfaces` y `carpincho_teleop`) y **Foxglove Studio**. Joystick por USB (cable, no Bluetooth).

```bash
ros2 launch carpincho_bringup operator.launch.py
```

En Foxglove: *Open connection* → `ws://192.168.8.10:8765` → importar el layout `operator/foxglove_layout.json`.

## 8. Desarrollo sin robot (cualquier PC con Ubuntu 24.04 + Jazzy)

```bash
python3 tools/fake_base.py                       # imprime /dev/pts/N
ros2 run carpincho_base base_bridge --ros-args -p port:=/dev/pts/N -p auto_enable:=true
ros2 run carpincho_arm arm_driver --ros-args --params-file ros2_ws/src/carpincho_arm/config/arm.yaml -p simulate:=true
ros2 launch carpincho_description display.launch.py     # URDF en RViz con sliders
```
