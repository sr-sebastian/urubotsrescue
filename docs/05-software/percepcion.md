# Percepción

## Cámaras y para qué se usa cada una

| Cámara | Tópico | Uso |
|---|---|---|
| RGB-D frontal (Orbbec Gemini 2 / RealSense) | `/depth_cam/color/image_raw` + profundidad alineada | hazmat, AprilTag, QR lejanos, **ubicación 3D de POIs** |
| Pinza (USB mini) | `/gripper_cam/image_raw` | QR chicos de Inspect, movimiento (cajón), aproximación fina del brazo |
| Térmica 256×192 | `/thermal/image_raw` (mono16) | anillos concéntricos (5 pts), firma de calor del laberinto (15 pts) |
| Gran angular frontal | `/cam_front/image_raw` | manejo |
| Trasera | `/cam_rear/image_raw` | marcha atrás y bajar escaleras |

## QR (`qr_detector`)

- OpenCV `QRCodeDetector` (multi). Si está `opencv-contrib-python`, usa el **WeChat QR**, que es mucho más
  robusto con códigos chicos, borrosos o inclinados.
- Publica la caja, el texto en `/qr/text` (cada texto nuevo una vez cada 5 s) y la imagen anotada.
- `upscale: 1.5` en la cámara de la pinza ayuda con los QR de las tareas Inspect. Acercarse a ~15-25 cm.

## Hazmat (`hazmat_detector`, YOLO)

1. **Dataset**: imprimir el set de etiquetas hazmat del reglamento en tamaño real. Sacar ≥ 3000 fotos con la
   cámara del robot, variando distancia (0.3-3 m), ángulo (±60°), luz (penumbra, focos, contraluz) y
   **tapando partes** (la prueba es de reconocimiento *parcial*). Agregar fondos de madera, como en la arena.
2. **Anotar** (Roboflow o CVAT), con una clase por etiqueta y el nombre exacto que pide el reglamento.
3. **Entrenar** en una PC con GPU o en Colab:
   ```bash
   # modelo nano de la versión vigente de Ultralytics (p. ej. yolo11n.pt / yolo26n.pt): usar el más nuevo estable
   yolo detect train model=yolo11n.pt data=hazmat.yaml imgsz=640 epochs=150 \
        mosaic=1.0 degrees=25 perspective=0.0008 hsv_v=0.5 erasing=0.4
   ```
   Meta: mAP50 ≥ 0.90 en validación **con fotos tomadas en otro día y con otra luz**.
4. **Exportar a TensorRT en el Jetson** (`format=engine half=True`) → medir los FPS reales en el Jetson (meta ≥ 8).
5. En la competencia: el día 1, sacar 200 fotos en la arena real y hacer un *fine-tune* de 20 épocas.

## Movimiento (`motion_detector`)

Diferencia contra un fondo con media exponencial y caja del blob más grande, con estela de seguimiento.
**Con el robot quieto**. Llamar `/motion/reset` antes de empezar. Si detecta ruido de la cámara: subir
`threshold` (25 → 35) o `min_area_frac`.

## Térmica (`thermal_viewer`)

- Las InfiRay P2 Pro / Topdon TC001 por UVC entregan imagen + datos de temperatura. Lo que necesitamos es el
  **modo Y16** (16 bits, temperatura cruda): `T[°C] = raw/64 − 273.15` (`raw_scale`, `raw_offset`). Si tu
  cámara entrega la imagen apilada (mitad imagen, mitad datos), recortar la mitad de datos en el nodo de la
  cámara o usar un nodo puente del fabricante.
- Paleta *inferno* con aumento ×3 (interpolación cúbica) y una cruz en el punto más caliente.
- Para los **anillos concéntricos** hace falta contraste: fijar el rango (`normalize_u8` con t_min/t_max ≈
  ambiente−2 … ambiente+15 °C) y acercarse a 30-40 cm.
- Firma de calor del laberinto: zona > mediana + 6 °C y > `heat_threshold_c` → `heat_sig` (15 pts en el CSV).

## AprilTags (laberinto)

`apriltag_ros` con familia **41h12** (`tagStandard41h12`), sobre la cámara RGB-D. Medir el tamaño real de
los tags en la competencia y poner `size`. Los tags se publican en TF; para el CSV conviene un nodo adaptador
que los pase a `/perception/detections` con `has_position=true` (ver backlog).

## Ubicación y deduplicación (`poi_manager`)

1. Una detección de la cámara RGB-D se ubica con la **mediana de la profundidad** en el 50 % central de la
   caja → punto 3D en el frame óptico → TF → `map`.
2. Sin profundidad (térmica): punto a `fallback_range` (0.6 m) sobre el eje óptico. Conviene acercarse.
3. Se **confirma** con 3 observaciones a menos de 0.5 m entre sí, y cada `(tipo, nombre)` se reporta **una vez**.
   El reglamento resta 3 puntos por cada detección mal ubicada: es mejor perder una que reportarla mal.
4. Se marca **A** (autónomo) o **T** (teleoperado) según `/autonomy/active`.
