# Comunicaciones, operador y audio

## 1. Red

```
[Notebook 192.168.8.20] ──Wi-Fi 5 GHz── [Router robot 192.168.8.1] ──Ethernet── [Jetson 192.168.8.10]
                                                                              └─ [Livox 192.168.1.1xx] (alias 192.168.1.50 en el Jetson)
```

- **Un router en el robot** (con antenas externas, arriba del deck) y **otro en la estación**, en modo cliente o
  puente. Canal 5 GHz **fijo** (36-48), ancho de 40 MHz (no 80: es más robusto con interferencia).
- SSID propio del equipo, con WPA2. Sin DHCP para los equipos del robot (IP fijas).
- En la competencia hay decenas de redes: el primer día, **escanear** (WiFi Analyzer) y elegir el canal más limpio.
- El reglamento permite **cable** (tether): el plan B es un cable Ethernet de 30 m con un enrollador (canal libre del MDD10A).

## 2. DDS (ROS 2 entre robot y notebook)

`carpincho_bringup/config/cyclonedds.xml`: **sin multicast** y con peers por IP. En la notebook solo
corren el joystick y `joy_teleop` (tópicos chicos). **Las imágenes no viajan por DDS**: van por Foxglove.

## 3. Foxglove (interfaz del operador)

- En el robot corre `foxglove_bridge` (puerto 8765). En la notebook, Foxglove Studio → `ws://192.168.8.10:8765`.
- Layout base: [`operator/foxglove_layout.json`](../../operator/foxglove_layout.json) (cámara frontal grande, pinza,
  térmica, trasera, mapa 3D con el robot, estado de la base, texto QR y estado de la autonomía).
- Usar las **imágenes comprimidas** (`.../image_raw/compressed`, paquete `image_transport_plugins`) y bajar la
  resolución y los FPS de las cámaras que no se están mirando.

### Presupuesto con radio degradada (5 Mbps, 10 % de pérdida, 100 ms)

| Flujo | Configuración | Mbps aprox. |
|---|---|---:|
| Cámara principal | JPEG 640×360 a 15 FPS, calidad 60 | 1.5 |
| Pinza o térmica (una a la vez) | 640×360 a 10 FPS | 0.8 |
| Mapa, TF, estado, POIs | Foxglove, 2-10 Hz | 0.3 |
| Audio (Opus 24 kbps) | | 0.03 |
| Joystick (DDS) | 20 Hz | 0.05 |
| **Total** | | **≈ 2.7** (deja margen) |

Practicar con la caja de degradación del TU Dortmund ([tudo-cni/vsting-sa](https://github.com/tudo-cni/vsting-sa))
o simularla en Linux con `tc netem` en el router o la notebook:

```bash
sudo tc qdisc add dev wlan0 root netem delay 100ms loss 10% rate 5mbit
sudo tc qdisc del dev wlan0 root            # sacarla
```

## 4. Audio bidireccional (prueba de 2 puntos)

Half-duplex con pulsar para hablar (lo permite el reglamento). Script: [`operator/audio_ptt.sh`](../../operator/audio_ptt.sh).

- **Robot → operador** (escucha ambiente, siempre abierta): micrófono USB del robot → Opus → UDP 5002.
- **Operador → robot** (mientras se mantiene apretada la tecla): micrófono de la notebook → Opus → UDP 5003 → parlante del robot.

```bash
# en el robot (lo puede lanzar el servicio systemd)
./operator/audio_ptt.sh robot 192.168.8.20
# en la notebook
./operator/audio_ptt.sh operador 192.168.8.10        # Enter = hablar / Enter = soltar
```

## 5. Si se corta el enlace

| Modo | Qué pasa |
|---|---|
| Teleoperado | `joy_teleop` deja de llegar → `lane_traverse` publica cero en 0.5 s → el ESP32 frena por watchdog |
| Autónomo | Sigue, porque todo el cómputo está a bordo. Al volver el enlace, el operador ve el estado en `/autonomy/lane_status` |
| Laberinto | El mapa y los POIs están en el robot; `/mission/export` se puede llamar cuando vuelva el enlace |
