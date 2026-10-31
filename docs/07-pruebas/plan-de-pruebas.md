# Plan de pruebas

Cada prueba tiene un ID, un procedimiento y un criterio de aprobación **medible**. Los resultados van al
**registro de pruebas** (una planilla compartida con estas columnas: fecha · ID · versión de software
(`git describe`) · operador · resultado · tiempo · observaciones · video).

## Niveles

1. **Unitarias (PC, sin robot)**: `colcon test` + tests del firmware. Las corre la CI en cada PR.
2. **Banco**: subsistema aislado (motor en el aire, brazo atornillado a la mesa, sensores en un trípode).
3. **Integración**: robot completo en la arena casera.
4. **Simulacro**: misión de 20 min con reglas, cronómetro, juez y operador sin ver el robot.

## Pruebas de software sin robot

| ID | Qué | Cómo | Aprueba si |
|---|---|---|---|
| P-SW-01 | Tests de PC | `colcon test` y `test_host` del firmware | 0 fallas |
| P-SW-02 | Firmware compila | `pio run` | sin warnings nuevos |
| P-SW-03 | Teleop con la base simulada | `tools/fake_base.py` + `base_bridge` + joystick | `/odom` se mueve como el joystick; al soltar LB, para |
| P-SW-04 | Watchdog simulado | matar `joy_teleop` con el robot simulado andando | `v = 0` en < 0.6 s |
| P-SW-05 | Exportación de misión | `/mission/export` con un bag de la arena | los 3 archivos abren; formato validado |

## Electrónica

| ID | Qué | Aprueba si |
|---|---|---|
| P-ELE-01 | E-stop con los motores andando | las orugas paran en < 0.2 s, la Jetson sigue prendida, al soltar **no** arranca |
| P-ELE-02 | Consumo en reposo y con carga | coincide con el presupuesto ±20 %; nada calienta > 60 °C en 20 min |
| P-ELE-03 | Ruido | 20 min andando sin errores de CRC (`/base/status.crc_errors` estable) ni reinicios del ESP32 |
| P-ELE-04 | Batería baja | con fuente a 21.5 V: LED naranja; a 19.7 V: los motores se bloquean |

## Movilidad (en la arena casera, ver [arena-de-pruebas.md](arena-de-pruebas.md))

| ID | Prueba | Procedimiento | Aprueba si |
|---|---|---|---|
| P-MOB-01 | Rampa 15° y 30° | 10 tramos teleoperados | 10/10 sin intervención |
| P-MOB-02 | K-rails de 10 y 20 cm | 10 tramos | 9/10 |
| P-MOB-03 | Stepfield de 15 cm | 10 tramos | 8/10 |
| P-MOB-04 | Pallet + caño de 20 cm (y 30 cm) | 10 tramos | 8/10 (20 cm), 5/10 (30 cm) |
| P-MOB-05 | **Escalera de 45°** con contrahuella de 20 cm | 10 subidas + 10 bajadas | 9/10 sin vuelco; tiempo < 60 s por tramo |
| P-MOB-06 | Grava (15°) | 10 tramos | 8/10; las orugas no se salen |
| P-MOB-07 | Resistencia | 30 min seguidos en carriles variados | sin fallas mecánicas; temperatura de los motores < 70 °C |
| P-MOB-08 | Velocidad máxima y radio de giro | medir | ≥ 0.35 m/s; gira en el lugar |

## Destreza

| ID | Prueba | Aprueba si |
|---|---|---|
| P-DEX-01 | Inspect lineal (QR a 60 cm) teleoperado | 5 QR en < 3 min, el texto aparece en pantalla |
| P-DEX-02 | Touch / Insert: eje en un agujero a 60 cm | Touch 5/5; Insert ≥ 25 mm 4/5 |
| P-DEX-03 | Pinza: tomar el eje de 6 mm y un objeto de 300 g | 10/10 sin que se caiga |
| P-DEX-04 | Inspect TA (autónomo desde `stow`) | 4/5 QR leídos sin tocar el joystick |
| P-DEX-05 | Volver a `stow` desde cualquier pose | sin chocar el deck, el LiDAR ni el mástil |

## Sensores (cajón de víctimas)

| ID | Prueba | Aprueba si |
|---|---|---|
| P-SEN-01 | Térmica: calentador de manos con anillos C concéntricos (2 niveles) impresos en 3D | se distinguen los 2 niveles a 40 cm |
| P-SEN-02 | Hazmat parcialmente tapado (set completo, 30 % tapado) | ≥ 90 % de aciertos con caja y nombre |
| P-SEN-03 | Movimiento: disco giratorio a 30 rpm con un cuadrado | caja siguiendo el blanco 360° |
| P-SEN-04 | Imán (Hall en la punta) | detecta un imán de heladera a 1 cm (Δ > 2 mT) |
| P-SEN-05 | Audio bidireccional | se entiende una secuencia alfanumérica en los dos sentidos |
| P-SEN-06 | QR 2 cm a 20 cm (cámara de la pinza) | decodifica en < 2 s |

## Mapeo

| ID | Prueba | Aprueba si |
|---|---|---|
| P-MAP-01 | Deriva de FAST-LIO | 3 vueltas a la arena y volver al inicio: error < 10 cm |
| P-MAP-02 | Entregables del laberinto | GeoTIFF + PLY + CSV generados y copiados en < 3 min; formato OK |
| P-MAP-03 | Ubicación de los POIs | error medio < 0.25 m contra la cinta métrica en 5 objetos |

## Autonomía

| ID | Prueba | Aprueba si |
|---|---|---|
| P-AUT-01 | Carril plano autónomo | 10 tramos seguidos, sin intervención |
| P-AUT-02 | Carril con rampas, K-rail y grava | 6/10 tramos |
| P-AUT-03 | Corte de Wi-Fi en autónomo | sigue y completa el tramo |
| P-AUT-04 | El operador toma el control | cualquier movimiento del joystick corta la autonomía en < 0.1 s |
| P-AUT-05 | Laberinto autónomo (fase 3) | explora ≥ 70 % y vuelve al inicio en 15 min |

## Comunicaciones

| ID | Prueba | Aprueba si |
|---|---|---|
| P-COM-01 | Latencia de punta a punta (joystick → movimiento visible en el video) | < 250 ms |
| P-COM-02 | Radio degradada (5 Mbps, 10 % de pérdida, 100 ms) | se puede completar un carril teleoperado |
| P-COM-03 | Alcance | enlace estable a 30 m con 2 paredes en el medio |
