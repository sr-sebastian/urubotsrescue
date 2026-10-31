# Lista de materiales (BOM)

_Generado desde `hardware/bom.csv` por `tools/gen_docs.py`._

Precios **orientativos en USD** (oct. 2026, sin envío ni impuestos). Antes de comprar, confirmar disponibilidad y tiempos de envío a Uruguay: lo importado puede tardar 4-8 semanas.

| Subsistema | Ítem | Especificación | Cant. | USD c/u | USD total | Notas |
|---|---|---|---:|---:|---:|---|
| computo | Jetson Orin Nano Super Developer Kit 8GB | JetPack 6 (Ubuntu 22.04) | 1 | 249 | 249 | Corre ROS 2 Humble + YOLO (TensorRT) |
| computo | SSD NVMe M.2 2280 256 GB | PCIe Gen3 | 1 | 30 | 30 | El sistema va en el NVMe (no en microSD) |
| computo | ESP32-S3-DevKitC-1 N8R8 | USB nativo | 2 | 15 | 30 | 1 de repuesto ya flasheado |
| potencia | Batería 6S2P 21700 (≈10 Ah) con BMS 40 A | 22.2 V nominal / 25.2 V cargada | 3 | 120 | 360 | 1 en uso + 1 cargando + 1 de reserva |
| potencia | Cargador balanceador 6S ≥ 200 W | ISDT / ToolkitRC / SkyRC | 1 | 60 | 60 | Cargar siempre dentro de bolsa ignífuga |
| potencia | Bolsa ignífuga para baterías |  | 2 | 10 | 20 |  |
| potencia | Pulsador de parada de emergencia hongo 22 mm NC | con bloque NC+NO | 1 | 8 | 8 | Reglamento: E-stop obligatorio |
| potencia | Relé/contactor DC 24 V 40 A (bobina 24 V) | tipo automotriz 24 V o contactor DC | 1 | 8 | 8 | El E-stop corta la bobina = corta motores y servos |
| potencia | Interruptor principal 30 A | rocker o llave rotativa | 1 | 6 | 6 |  |
| potencia | Portafusibles ATO 6 vías + fusibles | 40/20/15/10/5/3 A | 1 | 12 | 12 |  |
| potencia | Shunt 2 mΩ 40 A + módulo INA226 | I2C 0x40 | 1 | 10 | 10 |  |
| potencia | Convertidor DC-DC 24→12 V 10 A | entrada 9-36 V | 2 | 15 | 30 | Uno para Jetson+hub; otro para servos del brazo |
| potencia | Convertidor DC-DC 24→5 V 5 A |  | 1 | 8 | 8 | ESP32 + LEDs + sensores 5 V |
| potencia | Conectores XT60/XT30 + JST-XH + Dupont + GX12 | kit | 1 | 25 | 25 | Ver estándar de conectores en docs/04 |
| potencia | Cable siliconado 12/16/18/22 AWG (rojo/negro) | 2 m de cada | 1 | 25 | 25 |  |
| motores | Motorreductor 775 24 V planetario 42 mm 1:51 con encoder Hall | ≈118 rpm, ≥4 N·m nominal, eje ≥30 mm | 2 | 45 | 90 | Tracción. Verificar PCD 32 mm, M4 y rpm reales del 775 |
| motores | Motorreductor 775 24 V con reductora planetaria 56 mm 1:264 | ≈23 rpm, par nominal de la reductora ≥ 20 N·m, eje 12 mm | 1 | 70 | 70 | Flipper (+ correa 14T→30T) |
| motores | Cytron MDD20A | 2 canales, 20 A, 6-30 V | 1 | 35 | 35 | Tracción |
| motores | Cytron MDD10A | 2 canales, 10 A, 5-30 V | 1 | 25 | 25 | Flipper + canal libre |
| transmision | Correa HTD 1100-5M-25 | 220 dientes | 4 | 20 | 80 | 2 + 2 repuesto |
| transmision | Correa HTD 760-5M-25 | 152 dientes | 4 | 15 | 60 | 2 + 2 repuesto |
| transmision | Correa HTD 300-5M-15 | 60 dientes | 3 | 8 | 24 | tracción izquierda + flipper (+1 rep.) |
| transmision | Polea HTD 14-5M-15 de aluminio (bore 12 + chavetero) | motor del flipper | 2 | 10 | 20 | 1 + 1 repuesto |
| transmision | Correa HTD 425-5M-15 | 85 dientes | 2 | 8 | 16 | tracción derecha (+1 rep.) |
| transmision | Rodamiento 6804-2RS (20x32x7) |  | 8 | 3 | 24 | 2 placas + 4 en poleas delanteras + 2 rep. |
| transmision | Rodamiento 6900-2RS (10x22x6) |  | 6 | 2 | 12 | poleas de punta de flipper |
| transmision | Rodamiento 608-2RS (8x22x7) |  | 12 | 1 | 12 | 6 rodillos + 4 brazo + 2 rep. |
| transmision | Rodamiento con brida KFL001 (eje 12) |  | 4 | 4 | 16 | eje motriz trasero |
| transmision | Rodamiento MR105-2RS (5x10x4) |  | 2 | 1 | 2 | sensor de ángulo del flipper |
| transmision | Eje acero plata 12 mm h7 x 1 m | + chavetas 4x4 | 1 | 15 | 15 |  |
| transmision | Tubo Al 6061 20x2 x 1 m | eje de flippers | 1 | 10 | 10 |  |
| transmision | Bulonería (M10x60 8.8 x2; M8x60 x8; M5 y M4 surtido; M3 + insertos térmicos) | kit | 1 | 40 | 40 |  |
| estructura | Corte láser/agua de placas de aluminio | 5052 4 mm (CH-01 x2), 3 mm (CH-02 x2, CH-03, CH-05, CH-06), 6061 5 mm (FL-01 x2) | 1 | 150 | 150 | Enviar DXF de cad/out/dxf |
| estructura | Policarbonato 4 mm 500x300 | deck CH-04 | 1 | 20 | 20 | Corte con router o sierra (NO láser CO2) |
| estructura | Perfil ángulo Al 20x20x2 x 2 m |  | 1 | 10 | 10 |  |
| estructura | Tubo Al 25x2 x 0.3 m | mástil LiDAR | 1 | 5 | 5 |  |
| estructura | Filamento PLA-CF (fibra de carbono) | 1 kg | 2 | 30 | 60 | poleas y soportes |
| estructura | Filamento PETG | 1 kg | 2 | 20 | 40 |  |
| estructura | Filamento TPU 95A | 1 kg | 1 | 30 | 30 | tacos de oruga (≈210) |
| sensores | Livox Mid-360 | LiDAR 3D 360° + IMU | 1 | 749 | 749 | FAST-LIO y PLY del laberinto |
| sensores | Cámara de profundidad Orbbec Gemini 2 (o RealSense D435i) | RGB-D | 1 | 234 | 234 | Alineada al color para ubicar POIs |
| sensores | Cámara térmica USB 256x192 (InfiRay P2 Pro / Topdon TC001) | UVC Y16 | 1 | 250 | 250 | Tarea térmica (5 pts) + firma de calor del laberinto |
| sensores | Cámara USB 1080p gran angular (ELP o similar) | MJPG | 2 | 35 | 70 | frontal + trasera |
| sensores | Cámara USB mini (endoscopio/módulo 1080p) | para la pinza | 1 | 25 | 25 | inspección y QR chicos |
| sensores | IMU BNO055 (módulo) | I2C 0x28 | 1 | 25 | 25 |  |
| sensores | Módulo AS5600 + imán diametral | salida analógica | 2 | 4 | 8 |  |
| sensores | Sensor Hall lineal SS49E |  | 5 | 0 | 2 | Tarea de proximidad con imán (3 pts) |
| sensores | Placa de audio USB + micrófono + parlante 3 W |  | 1 | 25 | 25 | Audio bidireccional (2 pts) |
| sensores | Tira WS2812 8 LEDs + 2 focos LED 12 V 3 W + módulo MOSFET |  | 1 | 13 | 13 |  |
| comunicaciones | Router de viaje 5 GHz con antenas externas (GL.iNet GL-MT3000 o similar) | robot | 1 | 90 | 90 | Ethernet al Jetson |
| comunicaciones | Router/AP 5 GHz estación de operador |  | 1 | 90 | 90 | Mismo SSID dedicado; canal fijo |
| comunicaciones | Hub USB 3.0 alimentado 7 puertos | entrada 12 V | 1 | 30 | 30 | Cámaras y adaptadores |
| comunicaciones | Joystick tipo Xbox con cable |  | 2 | 40 | 80 | 1 de repuesto |
| brazo | Servo Feetech STS3215 12 V (30 kg·cm) | bus serie TTL | 8 | 18 | 144 | 7 + 1 de repuesto |
| brazo | Adaptador de bus serie Waveshare Bus Servo Adapter (A) | USB | 1 | 8 | 8 |  |
| brazo | Tubo de fibra de carbono 20x18 x 1 m |  | 1 | 15 | 15 | eslabones |
| brazo | Correas GT2 6 mm cerradas (140 y ≈172 mm) + poleas GT2 20T |  | 1 | 15 | 15 |  |
| brazo | Rodamiento giratorio "lazy susan" 4 pulgadas |  | 1 | 5 | 5 |  |
| varios | Imanes de neodimio 10x3 + espuma + velcro + precintos + termocontraíble | kit | 1 | 20 | 20 |  |
| varios | Contingencia (≈10%) |  | 1 | 300 | 300 | repuestos que se rompen en la competencia |

## Resumen por subsistema

| Subsistema | USD |
|---|---:|
| sensores | 1402 |
| potencia | 572 |
| transmision | 331 |
| varios | 320 |
| estructura | 315 |
| computo | 309 |
| comunicaciones | 290 |
| motores | 220 |
| brazo | 187 |
| **Total** | **3946** |

## Si el presupuesto no alcanza

- **LiDAR**: empezar con el EAI X2L / RPLIDAR que ya tiene el equipo (mapa 2D) y la cámara de profundidad para la nube 3D (RTAB-Map). Se pierde calidad en el PLY del laberinto.
- **Térmica**: MLX90640 (32x24, ≈60 USD) por I2C. Alcanza para la firma de calor, pero es justo para los anillos concéntricos de la prueba de agudeza térmica.
- **Cómputo**: la Jetson Nano del LIMO sirve para desarrollo (ROS 2 en contenedor), pero no da para FAST-LIO + YOLO a la vez.
- **Brazo**: imprimir un SO-101 (también usa STS3215) para empezar a practicar destreza mientras se fabrica el C1.
