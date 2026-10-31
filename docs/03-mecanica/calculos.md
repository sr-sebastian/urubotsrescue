# Cálculos de diseño

_Generado por `tools/gen_docs.py` desde `params.py`. Valores de diseño: validarlos midiendo en el prototipo (ver docs/07-pruebas)._

## 1. Geometría principal

| Magnitud | Valor |
|---|---:|
| axle_dist | 400.0 mm |
| axle_z | 58.4 mm |
| track_pd | 95.5 mm |
| body_len | 490.0 mm |
| length_tracks | 519.1 mm |
| length_flippers_ext | 759.3 mm |
| width_total | 414.0 mm |
| height_deck | 194.0 mm |
| flip_len | 259.3 mm |
| y_track_c | 137.5 mm |
| y_flip_c | 171.5 mm |

Las correas son de largo comercial y las distancias entre ejes se **calculan** para que calcen (`params.center_for_belt`):

- Oruga principal: HTD 1100-5M sobre 2 poleas de 60T → distancia entre ejes 400.0 mm.
- Flipper: HTD 760-5M sobre 60T + 36T → largo de flipper 259.3 mm.
- Altura de eje sobre el piso (con tacos de 8 mm): 58.4 mm.

## 2. Tracción (subir escalera de 45° con 20 kg)

- Fuerza para subir: m·g·sen45°·1.3 = **180 N**
- Torque por oruga en la polea (r = 47.7 mm): **4.31 N·m**
- Disponible por oruga (775 + 1:51, η 80 %, correa 1.5:1): nominal ≈ **6.1 N·m**, arranque ≈ 61 N·m → margen nominal 1.4×
- Velocidad máxima sin carga: **0.39 m/s** (el firmware limita a 0.4 m/s)
- Historia: la v0 usaba 1:27 (0.74 m/s) y daba solo 0.8× del torque nominal necesario: se pasó a 1:51.
- Corriente: en escalera cada motor tira ≈ 6-9 A (MDD20A soporta 20 A continuos por canal).

## 3. Flipper

- Torque para levantar la mitad delantera (palanca 259 mm): **25.4 N·m**
- Disponible (775 + 1:264, η 70 %, correa 2.14:1): ≈ **40 N·m** nominal
- Velocidad: ≈ 64 °/s (90° en ≈ 1.4 s)
- Protección: la correa HTD 15 mm salta antes de romper la reductora, y el firmware corta por atasco (1.5 s sin moverse con >50 % de PWM).

## 4. Escaleras del reglamento (45°, contrahuella 20 cm)

- Distancia entre narices de escalón sobre la pendiente: 283 mm
- Largo de apoyo con flippers extendidos: 659 mm → apoya en **2.3 narices** a la vez (≥ 2 = no se hamaca).
- Ver `cad/out/masa_cg.md` para el ángulo de vuelco con el CG actual.

## 5. Autonomía eléctrica

| Consumo | W |
|---|---:|
| Jetson Orin Nano (modo 25 W, promedio) | 18 |
| Livox Mid-360 | 6.5 |
| Cámara de profundidad | 2.5 |
| Térmica + 3 cámaras USB | 4 |
| Router 5 GHz | 6 |
| ESP32 + sensores + LEDs | 4 |
| Brazo (promedio en tareas) | 15 |
| Tracción (promedio en carriles) | 60 |
| Flipper (promedio) | 8 |
| **Total promedio** | **124** |

Batería 6S2P 21700 (21.6 V × 10 Ah, 85 % útil) = 184 Wh → **≈ 89 min** de uso continuo. Una prueba dura 20 min: con 3 baterías alcanza para todo el día rotando la carga.

Picos: tracción en escalera ≈ 2 × 9 A + flipper 6 A + brazo 4 A + electrónica 3 A ≈ **31 A** → fusible principal de 40 A y BMS de ≥ 40 A continuos.

## 6. Brazo (STS3215 a 12 V: 2.9 N·m de arranque)

- Brazo horizontal extendido con 200 g en la punta: hombro **4.5 N·m**, codo **2.1 N·m**.
- Hombro: 2 servos × 2.9 N·m × 2:1 = 11.6 N·m de arranque (39 % usado).
- Codo: 1 servo × 2.9 × 2:1 = 5.8 N·m (36 % usado).
- Regla práctica: no sostener el brazo totalmente horizontal más de ~30 s (los STS se calientan); trabajar con el codo flexionado.
- Alcance horizontal desde el eje J1: 655 mm. Altura máxima de la punta sobre el piso: 0.93 m (carriles lineales a 0.60 m: OK; picaportes a 0.9-1.2 m: solo en el límite).
- Carga útil máxima recomendada: 300 g (el desafío de carga del reglamento con objetos de varios kg **no** es objetivo de esta versión).
