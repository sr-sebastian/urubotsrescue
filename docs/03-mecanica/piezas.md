# Catálogo de piezas

_Generado por `tools/gen_docs.py` desde `cad/out/parts.json`. No editar a mano._

Robot **Carpincho URB-R1** · masa estimada **16.5 kg** · CG = [29.2, 1.0, 113.1] mm (en `base_footprint`).

Los archivos están en `cad/out/` (STEP para editar/inspeccionar, STL para imprimir, DXF para cortar). Las piezas marcadas *L/R* se usan a ambos lados: la del lado derecho es la misma pieza espejada (en placas planas, la misma pieza dada vuelta).

## Chasis y estructura

| Código | Pieza | Cant. | Material | Fabricación | Medidas (mm) | g/u | Archivos | Notas |
|---|---|---:|---|---|---|---:|---|---|
| CH-01 | Placa lateral | 2 | Al | Corte láser/agua Al 5052 4 mm | 490 × 4 × 160 | 741 | [STEP](../../cad/out/step/CH-01.step) [STL](../../cad/out/stl/CH-01.stl) [DXF](../../cad/out/dxf/CH-01.dxf) | Espejo para el lado derecho (misma pieza girada). |
| CH-02 | Placa exterior de oruga | 2 | Al | Corte láser Al 5052 3 mm | 380 × 3 × 82 | 226 | [STEP](../../cad/out/step/CH-02.step) [STL](../../cad/out/stl/CH-02.stl) [DXF](../../cad/out/dxf/CH-02.dxf) |  |
| CH-03 | Piso | 1 | Al | Corte láser Al 5052 3 mm | 440 × 229 × 3 | 777 | [STEP](../../cad/out/step/CH-03.step) [STL](../../cad/out/stl/CH-03.stl) [DXF](../../cad/out/dxf/CH-03.dxf) |  |
| CH-04 | Deck superior | 1 | PC | Policarbonato 4 mm (CNC/láser CO2 no!) o Al 3 mm | 490 × 238 × 4 | 541 | [STEP](../../cad/out/step/CH-04.step) [STL](../../cad/out/stl/CH-04.stl) [DXF](../../cad/out/dxf/CH-04.dxf) | El policarbonato NO se corta con láser CO2 (amarillea y es tóxico): router CNC o sierra. |
| CH-05 | Mamparo delantero | 1 | Al | Corte láser Al 3 mm | 3 × 229 × 157 | 268 | [STEP](../../cad/out/step/CH-05.step) [STL](../../cad/out/stl/CH-05.stl) [DXF](../../cad/out/dxf/CH-05.dxf) |  |
| CH-06 | Mamparo trasero (panel de conectores) | 1 | Al | Corte láser Al 3 mm | 3 × 229 × 157 | 270 | [STEP](../../cad/out/step/CH-06.step) [STL](../../cad/out/stl/CH-06.stl) [DXF](../../cad/out/dxf/CH-06.dxf) |  |
| CH-07 | Escuadra Al 20x20x2 | 4 | Al | Perfil comprado, cortar y agujerear con plantilla | 300 × 20 × 20 | 62 | — | La pieza se modela con la cara contra la placa lateral; ver guía de armado. |
| CH-08 | Separador placa lateral-exterior | 8 | Al | Tubo Al 12x2 cortado o PETG 100% | 12 × 12 × 37 | 9 | [STEP](../../cad/out/step/CH-08.step) [STL](../../cad/out/stl/CH-08.stl) |  |
| CH-09 | Asa de transporte | 2 | PLA-CF | Impresión 3D PLA-CF/PETG 100% relleno | 176 × 16 × 53 | 50 | [STEP](../../cad/out/step/CH-09.step) [STL](../../cad/out/stl/CH-09.stl) | Obligatoria por reglamento (asas seguras para mover el robot). |

## Tren motriz y orugas

| Código | Pieza | Cant. | Material | Fabricación | Medidas (mm) | g/u | Archivos | Notas |
|---|---|---:|---|---|---|---:|---|---|
| CH-10 | Separador de rodillo | 6 | PETG | Impresión 3D PETG 100% | 14 × 14 × 5 | 0 | [STEP](../../cad/out/step/CH-10.step) [STL](../../cad/out/stl/CH-10.stl) |  |
| DT-01 | Polea motriz trasera 60T HTD5M | 2 | PLA-CF | Impresión 3D PLA-CF/PETG, 5 perímetros, 50% gyroid. Competencia: Al 60-5M-25 + cubo | 101 × 101 × 31 | 122 | [STEP](../../cad/out/step/DT-01.step) [STL](../../cad/out/stl/DT-01.stl) | Chavetero 4 mm + 2 prisioneros M4 a 90°. |
| DT-02 | Polea delantera compuesta 60T+60T | 2 | PLA-CF | Impresión 3D PLA-CF, 5 perímetros, 50% gyroid | 101 × 101 × 65 | 249 | [STEP](../../cad/out/step/DT-02.step) [STL](../../cad/out/stl/DT-02.stl) | 2x rodamiento 6804-2RS. Gira libre sobre el tubo de flipper. |
| DT-03 | Rodillo de apoyo ø40 | 6 | PETG | Impresión 3D PETG, 4 perímetros, 40% | 46 × 46 × 27 | 22 | [STEP](../../cad/out/step/DT-03.step) [STL](../../cad/out/stl/DT-03.stl) | Rodamiento 608-2RS, eje bulón M8. |
| DT-05 | Taco de oruga (grouser) TPU | 206 | TPU | Impresión 3D TPU 95A, 100% relleno | 10 × 25 × 8 | 2 | [STEP](../../cad/out/step/DT-05.step) [STL](../../cad/out/stl/DT-05.stl) | 2x55 (orugas) + 2x38 (flippers) + 20 de repuesto |
| DT-06 | Polea 20T motor de tracción (HTD5M 15) | 2 | PLA-CF | Impresión 3D o Al comercial 20-5M-15 | 38 × 38 × 28 | 12 | [STEP](../../cad/out/step/DT-06.step) [STL](../../cad/out/stl/DT-06.stl) | Eje de motor 8 mm con D-flat: prisionero M4. |
| DT-07 | Polea 30T eje trasero (HTD5M 15) | 2 | PLA-CF | Impresión 3D o Al comercial 30-5M-15 | 54 × 54 × 28 | 28 | [STEP](../../cad/out/step/DT-07.step) [STL](../../cad/out/stl/DT-07.stl) |  |
| DT-08 | Soporte motor de tracción (tensable) | 2 | PLA-CF | Impresión 3D PLA-CF 6 perímetros 60% | 70 × 60 × 79 | 59 | [STEP](../../cad/out/step/DT-08.step) [STL](../../cad/out/stl/DT-08.stl) |  |
| REF-B1 | Correa HTD 1100-5M-25 (oruga) | 2 | belt | Comprado | 501 × 25 × 101 | 131 | — |  |
| REF-B2 | Tacos montados (oruga principal) | 2 | TPU | Ver DT-05 | 501 × 25 × 101 | 92 | — |  |
| REF-S1 | Eje motriz acero 12 mm (largo según params) | 2 | steel | Acero plata 12 mm h7, 2 chaveteros 4x2.5 (tornería) | 12 × 12 × 93 | 83 | — |  |

## Flippers

| Código | Pieza | Cant. | Material | Fabricación | Medidas (mm) | g/u | Archivos | Notas |
|---|---|---:|---|---|---|---:|---|---|
| DT-09 | Polea 14T motor de flipper (HTD5M 15) | 1 | Al | Al comercial 14-5M-15 (14T impresa no aguanta), bore 12 + chavetero | 28 × 28 × 28 | 12 | [STEP](../../cad/out/step/DT-09.step) [STL](../../cad/out/stl/DT-09.stl) |  |
| DT-10 | Polea 30T tubo de flipper (HTD5M 15) | 1 | PLA-CF | Impresión 3D PLA-CF 6 perímetros 60% | 54 × 54 × 34 | 27 | [STEP](../../cad/out/step/DT-10.step) [STL](../../cad/out/stl/DT-10.stl) | Cubo hacia el centro del robot. Pasador M5 pasante por el tubo (agujero ø5.2). |
| DT-11 | Soporte motor de flipper | 1 | PLA-CF | Impresión 3D PLA-CF 6 perímetros 60% | 84 × 60 × 111 | 88 | [STEP](../../cad/out/step/DT-11.step) [STL](../../cad/out/stl/DT-11.stl) |  |
| REF-B3 | Correa HTD 760-5M-25 (flipper) | 2 | belt | Comprado | 332 × 25 × 149 | 91 | — |  |
| REF-B4 | Tacos montados (flipper) | 2 | TPU | Ver DT-05 | 333 × 25 × 149 | 64 | — |  |
| REF-S2 | Tubo de flipper Al 6061 20x2 x 400 | 1 | Al | Tubo Al 20x2 cortado a medida, 2 agujeros ø5.2 por extremo | 20 × 20 × 410 | 348 | — |  |
| FL-01 | Brazo de flipper | 2 | Al | Corte láser/agua Al 6061 5 mm | 321 × 5 × 84 | 226 | [STEP](../../cad/out/step/FL-01.step) [STL](../../cad/out/stl/FL-01.stl) [DXF](../../cad/out/dxf/FL-01.dxf) |  |
| FL-02 | Cubo de flipper | 2 | Al | Torno Al 6061 (o PLA-CF 100% para prototipo) | 72 × 72 × 12 | 115 | [STEP](../../cad/out/step/FL-02.step) [STL](../../cad/out/stl/FL-02.stl) | Pasador: bulón M5x80 12.9 a través de cubo y tubo; 4x M5x20 al brazo. |
| DT-04 | Polea punta de flipper 36T | 2 | PLA-CF | Impresión 3D PLA-CF, 5 perímetros, 50% | 63 × 63 × 31 | 49 | [STEP](../../cad/out/step/DT-04.step) [STL](../../cad/out/stl/DT-04.stl) | 2x rodamiento 6900-2RS, eje bulón M10x60 8.8. |
| FL-05 | Alojamiento rodamiento 6804 | 2 | PLA-CF | Impresión 3D PLA-CF 100% | 62 × 55 × 13 | 11 | [STEP](../../cad/out/step/FL-05.step) [STL](../../cad/out/stl/FL-05.stl) |  |
| FL-04a | Engranaje 40T sensor (sobre tubo) | 1 | PETG | Impresión 3D PETG 100%, abrazadera M3 | 42 × 42 × 8 | 6 | [STEP](../../cad/out/step/FL-04a.step) [STL](../../cad/out/stl/FL-04a.stl) |  |
| FL-04b | Engranaje 40T con imán (AS5600) | 1 | PETG | Impresión 3D PETG 100% | 42 × 42 × 29 | 8 | [STEP](../../cad/out/step/FL-04b.step) [STL](../../cad/out/stl/FL-04b.stl) | Imán diametral 6x2.5 mm (viene con el módulo AS5600). |
| FL-04c | Soporte sensor de ángulo | 1 | PETG | Impresión 3D PETG 40% | 60 × 30 × 80 | 19 | [STEP](../../cad/out/step/FL-04c.step) [STL](../../cad/out/stl/FL-04c.stl) |  |
| REF-F1 | Eje de punta M10 | 2 | steel | Bulón M10x60 8.8 | 10 × 10 × 50 | 31 | — |  |

## Brazo manipulador

| Código | Pieza | Cant. | Material | Fabricación | Medidas (mm) | g/u | Archivos | Notas |
|---|---|---:|---|---|---|---:|---|---|
| AR-01 | Base del brazo | 1 | PLA-CF | Impresión 3D PLA-CF 6 per. 50% | 110 × 110 × 36 | 100 | [STEP](../../cad/out/step/AR-01.step) [STL](../../cad/out/stl/AR-01.stl) | Rodamiento lazy-susan 4" (100 mm) entre base y torreta. |
| AR-02 | Torreta + mejillas del hombro | 1 | PLA-CF | Impresión 3D PLA-CF 6 per. 60% | 104 × 164 × 69 | 122 | [STEP](../../cad/out/step/AR-02.step) [STL](../../cad/out/stl/AR-02.stl) | 2x 608-2RS eje hombro. 2 servos J2 en paralelo, GT2 20T->40T (2:1), correa cerrada GT2-6 de 140 mm. |
| AR-03 | Cubo del hombro (2x GT2 40T) | 1 | PLA-CF | Impresión 3D PLA-CF 100% | 32 × 96 × 59 | 47 | [STEP](../../cad/out/step/AR-03.step) [STL](../../cad/out/stl/AR-03.stl) | Eje 8 mm acero; tubo pegado con epoxi + pasador M3. |
| AR-08 | Tubo eslabón 1 (CF 20x18) | 1 | PLA-CF | Tubo fibra de carbono 20x18 cortado (o Al 20x1) | 20 × 20 × 202 | 16 | — |  |
| AR-04 | Codo inferior + servo J3 | 1 | PLA-CF | Impresión 3D PLA-CF 6 per. 60% | 61 × 118 × 80 | 110 | [STEP](../../cad/out/step/AR-04.step) [STL](../../cad/out/stl/AR-04.stl) | GT2 20T (horn) -> 40T (cubo codo), correa cerrada GT2-6 ≈172 mm: ajustar la posición del servo al largo comercial que consigas. |
| AR-05a | Cubo del codo (GT2 40T) | 1 | PLA-CF | Impresión 3D PLA-CF 100% | 30 × 58 × 55 | 30 | [STEP](../../cad/out/step/AR-05a.step) [STL](../../cad/out/stl/AR-05a.stl) |  |
| AR-09 | Tubo eslabón 2 (CF 20x18) | 1 | PLA-CF | Tubo fibra de carbono 20x18 cortado | 20 × 20 × 175 | 14 | — |  |
| AR-05b | Soporte servo muñeca J4 | 1 | PLA-CF | Impresión 3D PLA-CF 50% | 54 × 45 × 77 | 37 | [STEP](../../cad/out/step/AR-05b.step) [STL](../../cad/out/stl/AR-05b.stl) |  |
| AR-06 | Horquilla de muñeca + servo J5 | 1 | PLA-CF | Impresión 3D PLA-CF 50% | 62 × 54 × 94 | 46 | [STEP](../../cad/out/step/AR-06.step) [STL](../../cad/out/stl/AR-06.stl) |  |
| AR-07 | Pinza (dedos engranados) + cámara + Hall | 1 | PETG | Impresión 3D PETG 40%; almohadillas TPU | 94 × 59 × 74 | 56 | [STEP](../../cad/out/step/AR-07.step) [STL](../../cad/out/stl/AR-07.stl) | Ranura en V en los dedos para tomar el eje de 6 mm de la herramienta (tarea INSERT). |

## Electrónica y potencia

| Código | Pieza | Cant. | Material | Fabricación | Medidas (mm) | g/u | Archivos | Notas |
|---|---|---:|---|---|---|---:|---|---|
| MT-01 | Bandeja de electrónica | 1 | PETG | Impresión 3D PETG (2 mitades) o policarbonato 3 mm + columnas | 196 × 224 × 86 | 115 | [STEP](../../cad/out/step/MT-01.step) [STL](../../cad/out/stl/MT-01.stl) |  |
| MT-02 | Cuna de batería | 1 | PETG | Impresión 3D PETG 30% | 82 × 162 × 30 | 58 | [STEP](../../cad/out/step/MT-02.step) [STL](../../cad/out/stl/MT-02.stl) |  |
| MT-05 | Protección del E-stop | 1 | PETG | Impresión 3D PETG rojo | 58 × 60 × 22 | 10 | [STEP](../../cad/out/step/MT-05.step) [STL](../../cad/out/stl/MT-05.stl) |  |

## Sensores

| Código | Pieza | Cant. | Material | Fabricación | Medidas (mm) | g/u | Archivos | Notas |
|---|---|---:|---|---|---|---:|---|---|
| MT-03 | Mástil del LiDAR | 1 | PLA-CF | Base y plato impresos + tubo Al 25x2 | 72 × 72 × 186 | 63 | [STEP](../../cad/out/step/MT-03.step) [STL](../../cad/out/stl/MT-03.stl) |  |
| MT-04 | Cabezal de sensores frontal | 1 | PLA-CF | Impresión 3D PLA-CF 40% | 37 × 160 × 73 | 73 | [STEP](../../cad/out/step/MT-04.step) [STL](../../cad/out/stl/MT-04.stl) |  |
| MT-06 | Soporte cámara frontal | 1 | PETG | Impresión 3D PETG | 32 × 50 × 50 | 19 | [STEP](../../cad/out/step/MT-06.step) [STL](../../cad/out/stl/MT-06.stl) |  |

## Componentes comprados (referencia)

| Código | Pieza | Cant. | Material | Fabricación | Medidas (mm) | g/u | Archivos | Notas |
|---|---|---:|---|---|---|---:|---|---|
| REF-M1 | Motorreductor 775 24V planetario 42mm (tracción) | 2 | motor | Comprado | 44 × 44 × 167 | 750 | — |  |
| REF-M2 | Motorreductor 775 24V planetario 56mm 1:264 (flipper) | 1 | motor | Comprado | 56 × 56 × 187 | 750 | — |  |
| REF-SV | Servo Feetech STS3215 12 V (x7) | 7 | motor | Comprado | 45 × 25 × 39 | 55 | — |  |
| REF-BAT | Batería 6S Li-ion 21700 6S2P (≈10 Ah) | 1 | elec | Comprado | 70 × 150 × 50 | 1300 | — |  |
| REF-LID | Livox Mid-360 (LiDAR 3D) | 1 | sensor | Comprado | 65 × 65 × 65 | 265 | — |  |
| REF-DEP | Cámara de profundidad (Orbbec Gemini 2 / RealSense D435i) | 1 | sensor | Comprado | 26 × 90 × 25 | 300 | — |  |
| REF-THM | Cámara térmica USB 256x192 | 1 | sensor | Comprado | 20 × 26 × 26 | 60 | — |  |
| REF-ESTOP | E-stop hongo 22 mm NC | 1 | red | Comprado | 40 × 40 × 18 | 80 | — |  |
| REF-jetson | Jetson Orin Nano Super (devkit) | 1 | elec | Comprado | 103 × 90 × 35 | 280 | — |  |
| REF-esp32 | ESP32-S3 DevKitC-1 + placa base (PCB-01) | 1 | elec | Comprado | 46 × 70 × 18 | 60 | — |  |
| REF-buck_12v_pc | Buck 24->12 V 10 A (Jetson) | 1 | elec | Comprado | 50 × 60 × 22 | 120 | — |  |
| REF-buck_12v_arm | Buck 24->12 V 10 A (servos brazo) | 1 | elec | Comprado | 60 × 50 × 22 | 120 | — |  |
| REF-buck_5v | Buck 24->5 V 5 A (lógica/USB/LEDs) | 1 | elec | Comprado | 50 × 30 × 15 | 50 | — |  |
| REF-drv_traccion | Cytron MDD20A (tracción, 2 canales) | 1 | elec | Comprado | 84 × 22 × 62 | 120 | — |  |
| REF-drv_flipper | Cytron MDD10A (flipper + canal libre) | 1 | elec | Comprado | 63 × 22 × 60 | 80 | — |  |
| REF-fusibles | Caja fusibles ATO 6 vías | 1 | elec | Comprado | 60 × 45 × 30 | 80 | — |  |
| REF-rele_estop | Contactor/relé 40 A del E-stop | 1 | elec | Comprado | 40 × 30 × 30 | 100 | — |  |
| REF-hub_usb | Hub USB 3.0 alimentado 7 puertos | 1 | elec | Comprado | 90 × 30 × 15 | 120 | — |  |

## Parámetros de impresión 3D recomendados

| Material | Uso | Boquilla | Capa | Perímetros | Relleno | Notas |
|---|---|---|---|---:|---|---|
| PLA-CF | poleas, soportes de motor, brazo | 0.6 mm acero endurecido | 0.24 | 5-6 | 50-60 % gyroid | secar el filamento 6 h a 50 °C |
| PETG | rodillos, separadores, cajas | 0.4/0.6 | 0.2-0.28 | 4 | 30-40 % | |
| TPU 95A | tacos de oruga | 0.4 | 0.2 | — | 100 % | imprimir lento (20-25 mm/s), sin retracción |

**Insertos térmicos M3/M4** en vez de tuercas cautivas siempre que se pueda.
