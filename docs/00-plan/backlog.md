# Backlog de tareas

Cada ítem se puede copiar como *issue* de GitHub (etiquetas: `mecánica`, `electrónica`, `firmware`,
`ros`, `percepción`, `autonomía`, `operación`, `gestión`). Entre paréntesis está la fase y, cuando
corresponde, de qué otras tareas depende.

## Gestión

- [ ] Confirmar fechas y reglas **2027** (RoboCup Rescue y FIRA): calificación, TDP, video y sede; seguir cada borrador del reglamento (F0, y todo el año)
- [ ] Armar el tablero de GitHub Projects con este backlog y asignar responsables (F0)
- [ ] Pedir presupuesto a UTEC / sponsors con [hardware/bom.md](../../hardware/bom.md) (F0)
- [ ] Hacer las compras largas: Livox Mid-360, Jetson Orin Nano, motores 775 (tracción 42 mm 1:51, flipper 56 mm 1:264), térmica y RGB-D (F0, **semana 1**)
- [ ] Buscar taller de corte láser/agua para el aluminio y pedir cotización con los DXF (F0)
- [ ] Escribir el TDP (Team Description Paper) a partir de esta documentación (F2)
- [ ] Grabar el video de calificación: escalera, destreza, mapa, cajón de víctimas (F2, depende de H2)
- [ ] Logística del viaje: baterías ≤ 100 Wh, valijas, seguros, visas (F4)

## Mecánica

- [ ] Revisar el CAD en equipo: interferencias, accesos para el destornillador, cables (F0)
- [ ] Medir el motor 775 real (PCD, eje, largo) y corregir `params.py` (F1, depende de compras)
- [ ] Imprimir de prueba la polea DT-01 y verificar el engrane con la correa HTD 5M (F1)
- [ ] Probar 3 métodos de fijación de los tacos (pegado PU, remache POP, tornillo + contratuerca) en un tramo de correa: tirar con dinamómetro y arrastrar sobre lija (F1)
- [ ] Mandar a cortar las placas CH-01..06 y FL-01 (F1)
- [ ] Armar el chasis, el tren motriz y los flippers según la [guía de armado](../06-armado/guia-de-armado.md) (F1)
- [ ] Prueba de banco del flipper: levantar el robot con +5 kg de lastre (F1)
- [ ] Imprimir y armar el brazo C1 (F2)
- [ ] Mecánica v2: incorporar lo aprendido (rigidez, accesos, peso) (F3)
- [ ] Juego de repuestos: 2 poleas de cada tipo, 1 correa de cada tipo, 20 tacos, 2 brazos de flipper (F4)

## Electrónica

- [ ] Esquemático del tablero de potencia (fusibles, contactor del E-stop, sensado) (F0)
- [ ] PCB-01 "placa base": ESP32-S3 + conectores JST-XH + divisores de encoder + INA226 (F1). Mientras tanto, perfboard
- [ ] Arneses con la tabla de cableado de [electronica.md](../04-electronica/electronica.md) y etiquetas (F1)
- [ ] Probar el E-stop: con el hongo apretado, los motores y servos quedan sin energía y la Jetson sigue prendida (F1)
- [ ] Medir los consumos reales y actualizar el presupuesto de potencia (F2)
- [ ] Packs de viaje 6S1P ≤ 100 Wh (F4)

## Firmware

- [ ] Flashear la placa base y verificar la telemetría con `tools/fake_base.py` vs la placa real (F1)
- [ ] Calibrar counts_per_m (5 m medidos) y el feed-forward del PI (F1)
- [ ] Calibrar el cero del flipper y su rango mecánico (F1)
- [ ] Watchdog: tirar del cable USB con el robot andando → tiene que frenar en < 0.3 s (F1)
- [ ] Opcional: corriente por motor (sensor ACS712 por canal) para detectar atascos de orugas (F3)

## ROS 2 (base, TF, teleop, comunicaciones)

- [ ] Instalar el Jetson según [setup-jetson.md](../05-software/setup-jetson.md) (F0)
- [ ] Teleop por Wi-Fi con Foxglove + joystick, medir la latencia de punta a punta (F1)
- [ ] Ajustar `slip_factor` girando 10 vueltas (F1)
- [ ] Audio bidireccional con pulsar para hablar ([comunicaciones.md](../05-software/comunicaciones.md)) (F2)
- [ ] Practicar con la caja de degradación de radio (5 Mbps, 10 % de pérdida, 100 ms) y ajustar el video (F2)
- [ ] Layout de Foxglove para el operador: 4 cámaras, térmica, mapa, estado y POIs (F2)

## Percepción

- [ ] Dataset hazmat: imprimir el set oficial y sacar ≥ 3000 fotos con distintas luces, ángulos y distancias (F2)
- [ ] Entrenar el modelo nano vigente de Ultralytics (YOLO11n / YOLO26n o el que esté al día) y exportarlo a TensorRT; meta: mAP50 ≥ 0.9 y ≥ 8 FPS en el Jetson (F2)
- [ ] Configurar la térmica (Y16) y verificar los anillos concéntricos con un calentador de manos (F2)
- [ ] QR chicos: probar la cámara de la pinza a 10-30 cm; ajustar `upscale` (F2)
- [ ] AprilTag 41h12 + ubicación en el mapa, con error < 0.3 m (F2)
- [ ] Detector de objetos reales del laberinto (mochila, casco, matafuego, muñeco, garrafa) (F3)

## Mapeo y autonomía

- [ ] FAST-LIO con el Mid-360 montado; verificar que el mapa no deriva en 3 vueltas de la arena (F2)
- [ ] Exportar GeoTIFF + PLY + CSV y validar el formato contra el reglamento (F2)
- [ ] Carril autónomo ida y vuelta en la arena (`lane_traverse`): 10 pasadas seguidas (F3)
- [ ] Flippers automáticos en rampas y K-rails (`auto_flipper`) (F3)
- [ ] Destreza TA: inspección autónoma de QR en carril lineal (el operador acerca el robot y el brazo hace el resto) (F3)
- [ ] Exploración autónoma del laberinto (Nav2 + exploración por fronteras) con retorno al inicio (F3)
- [ ] Comportamiento sin enlace: si se pierde el Wi-Fi > 2 s en autónomo, seguir; en teleop, frenar (F3)

## Operación

- [ ] Checklist de pista impreso y plastificado ([checklist-competencia.md](../07-pruebas/checklist-competencia.md)) (F2)
- [ ] 3 operadores con ≥ 20 h de práctica cada uno (F4)
- [ ] Simulacro completo con jueces "de mentira" y reglas reales (H3)
