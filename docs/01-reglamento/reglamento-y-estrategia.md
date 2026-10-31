# Reglamento y estrategia de puntaje

Fuente principal: **RoboCup Rescue Robot League, reglamento 2026D** (versión del 3/6/2026,
[rrl.robocup.org](https://rrl.robocup.org)). El reglamento cambia todos los años: **antes de cada
decisión importante, revisar la versión vigente**. Lo que sigue es un resumen de trabajo, no lo reemplaza.

> **FIRA**: hasta 2026, la "Emergency Service" de FIRA se jugó con drones (FIRA Air). Si en 2027 se abre
> una categoría de rescate terrestre, sus pruebas probablemente se inspiren en las mismas pruebas estándar
> del NIST que usa RoboCup. **Acción**: apenas se publiquen las reglas FIRA 2027, completar la tabla de la
> sección 6 y ajustar prioridades.

## 1. Lo esencial

| Tema | Regla (2026D) | Qué implica para el Carpincho |
|---|---|---|
| Peso | < 80 kg; asas seguras obligatorias | 17 kg estimados; 2 asas CH-09 |
| E-stop | Obligatorio | Hongo NC que corta motores y servos (ver electrónica) |
| Robot chico | Pasa por un hueco de 30 × 30 cm (premio aparte) | **No** apuntamos a "small" (414 mm de ancho) |
| Puertas de paso | Ancho del robot + 10 cm | El ancho real es lo que manda: no agregar nada que sobresalga |
| Operador | Sin ver el robot, solo por la interfaz | Cámaras, mapa, estado y audio en Foxglove |
| Tiempo | Turnos de 30 min: 5 de preparación, **10 de movilidad**, **10 de destreza**, 2 de sensores, 3 de salida | Practicar la secuencia completa con cronómetro |
| Resets | ≥ 2 min; tocar el robot es un reset; no se puede cambiar la configuración durante la prueba | Cambiar una pieza tiene que ser rápido y fácil |
| Cable (tether) | Permitido, con enrollador a bordo o un "cable handler" en la entrada | Plan B si falla el Wi-Fi: canal 2 del MDD10A previsto para un enrollador |
| Radio | Sin restricción (respetar leyes locales). Degradación opcional con puntos extra: hasta 5 Mbps, 10 % de pérdida y 100 ms | Video comprimido, autonomía que sigue sin enlace |
| Autonomía | Solo cómputo a bordo; el mapa y las detecciones se hacen en el robot | Todo corre en el Jetson; la notebook solo muestra |

## 2. Pruebas

### Movilidad (carriles)

Rampas cruzadas con discos deslizantes (0°/15°), K-rails (10 y 20 cm), grava (15°), stepfield cúbico,
"Traverse & Center" (pendiente de 15° y ancho variable), pallets con caños (escalones de 20 cm),
**escaleras de 35°/40°/45°** con 0, 2 o 4 barreras, puertas (picaporte a 90-120 cm, con cierre pesado) y
"Avoid Holes" (camino elevado; derribar postes suma 10 s de penalización).

- **Teleoperado: 1 punto por tramo** de punta a punta (ida = 1, vuelta = 1).
- **Autónomo (manos fuera de la interfaz): 15 puntos por tramo.** El operador puede tomar el control
  cuando quiera y ese tramo cuenta como teleoperado.
- Hasta 10 tramos en los 10 minutos de movilidad.
- Antes de las semifinales hay que **"desbloquear" cada carril**, sumando puntos en él durante las preliminares.

### Destreza (incluida en todos los carriles)

| Tarea | Lineal | Omni | Notas |
|---|---:|---:|---|
| Inspect (QR / hazmat) | 1 | 2 | Se puede hacer con una cámara del chasis; hay que entregar la imagen marcada y el texto |
| Touch (solo preliminares) | 2 | 4 | Contacto sostenido con una punta dentro del agujero |
| Insert (semis y finales) | 3 | 6 | Herramienta (eje de 6 mm) perpendicular, ≥ 25 mm adentro |
| Apretar E-stop | — | 8 | Solo omni; semis y finales |
| Girar válvula | — | 10 | Ídem |
| Insertar llave | — | 10 | Ídem |

- Los carriles lineales están a **60 cm** de altura; las tareas omni pueden estar a 60 cm o en el piso.
- **Multiplicadores**: aproximación teleoperada + manipulación autónoma (TA) = **×10**; las dos autónomas (AA) = **×20**.
  El brazo tiene que arrancar **guardado** en cada intento autónomo.
- Para puntuar destreza hay que haber puntuado ≥ 2 en movilidad.

### Cajón de víctimas (sensores, 2 min)

| Prueba | Pts | Cómo la resolvemos |
|---|---:|---|
| Agudeza térmica: anillos C concéntricos sobre un calentador, 2 niveles | 5 | Térmica 256×192 + paleta + aumento ×3 (`thermal_viewer`) |
| Reconocimiento parcial: hazmat | 4 | YOLO entrenado con etiquetas parcialmente tapadas (`hazmat_detector`) |
| Movimiento: blanco en disco giratorio, seguido 360° | 4 | Diferencia de cuadros + seguimiento (`motion_detector`), con el robot quieto |
| Muestreo de proximidad: imán | 3 | Sensor Hall SS49E en la punta de la pinza (`/arm/hall`) |
| QR | 2 | `qr_detector` (cámara de la pinza para los chicos) |
| Audio bidireccional (alfanumérico) | 2 | Micrófono + parlante, con pulsar para hablar (`operator/audio_ptt.sh`) |

Para puntuar el cajón hay que tener ≥ 2 puntos de movilidad y ≥ 2 de destreza.

### Laberinto: mapeo y detección de objetos

- 20 min para generar **2 mapas**: uno "rápido" (≤ 5 min) y uno "completo" (≤ 15 min).
- **Multiplicadores**: teleoperado ×1, con degradación de radio ×2, **autónomo ×5**.
- Entregables generados **automáticamente** (no se pueden editar) y copiados en ≤ 5 min:
  - **GeoTIFF 2D** con los colores del reglamento (obligatorio, no puntúa).
  - **PLY 3D** en ASCII: origen en el frente del robot a nivel del piso, robot mirando +Y, Z arriba.
    Puntaje = cobertura × 1/(1 + error global) × bonus (color ×1.25, temperatura ×1.6, ambos ×2).
  - **CSV de objetos**: AprilTag 41h12 (1 pt), hazmat (2), objetos reales (10: mochila, casco, matafuego,
    muñeco, garrafa), firma de calor (15). Se restan 3 por cada detección mal ubicada. Puntaje = DS/(1 + LE).
- Mapa 3D y CSV pesan 50 % cada uno. En el laberinto **no se puede pre-mapear**; en el resto de la arena, sí.

`carpincho_perception/mission_exporter` genera los tres archivos con el formato exacto (hay tests).

## 3. Dónde están los puntos

Se normaliza por carril (movilidad, destreza y exploración, hasta 100 % cada una) y se suman todos los carriles.
En la práctica:

1. **La autonomía en movilidad multiplica por 15.** Diez tramos teleoperados = 10 puntos; dos tramos autónomos = 30.
   Los carriles "fáciles" (rampas, grava, centrado, K-rail chico) con `lane_traverse` dan los puntos más baratos.
2. **Destreza TA (×10)**: el operador acerca el robot y el brazo inspecciona o toca solo. Con QR en un carril
   lineal: 1 pt × 10 = 10 por tarea. Apuntar a **Inspect lineal y omni autónomos** primero.
3. **Cajón de víctimas**: 20 puntos "fijos" que no requieren autonomía. Tenerlo resuelto desde H2.
4. **Laberinto**: la firma de calor (15) y los objetos reales (10) valen mucho; el PLY con color y temperatura
   duplica el puntaje del mapa.
5. Los carriles difíciles (escaleras, pallets de 30 cm) primero hay que **desbloquearlos** teleoperados.

## 4. Matriz de requisitos

| ID | Requisito | Fuente | Subsistema | Verificación |
|---|---|---|---|---|
| RQ-01 | Subir y bajar escalera de 45° con contrahuella de 20 cm | Movilidad | Tracción + flippers | Prueba P-MOB-05 |
| RQ-02 | Pasar pallets y caños de 20 cm (30 cm en la vivienda) | Movilidad | Flippers | P-MOB-04 |
| RQ-03 | Ancho total ≤ 0.5 m para pasar puertas de 90 cm con margen | Puertas | Chasis | Medición |
| RQ-04 | Llegar con la herramienta a 60 cm de altura e insertar ≥ 25 mm en perpendicular | Destreza | Brazo | P-DEX-02 |
| RQ-05 | Pinza que abra ≥ 10 cm y tome un eje de 6 mm | Destreza / carga | Brazo | P-DEX-03 |
| RQ-06 | Cámara térmica que resuelva 2 niveles de anillos concéntricos | Cajón | Percepción | P-SEN-01 |
| RQ-07 | Detección autónoma de hazmat con caja y nombre en pantalla | Cajón / inspect | Percepción | P-SEN-02 |
| RQ-08 | Seguir un blanco giratorio 360° | Cajón | Percepción | P-SEN-03 |
| RQ-09 | Detectar un imán con un sensor en la punta del manipulador | Cajón | Brazo + firmware | P-SEN-04 |
| RQ-10 | Audio half-duplex con pulsar para hablar | Cajón | Comunicaciones | P-SEN-05 |
| RQ-11 | GeoTIFF + PLY + CSV automáticos en < 5 min | Laberinto | Mapeo | P-MAP-02 |
| RQ-12 | Autonomía con cómputo 100 % a bordo, que sigue sin enlace | Autonomía | Autonomía | P-AUT-03 |
| RQ-13 | E-stop que corte los actuadores | Seguridad | Potencia | P-ELE-01 |
| RQ-14 | Asas seguras | Seguridad | Chasis | Inspección |
| RQ-15 | Guardar el brazo antes de cada intento autónomo | Destreza | Brazo | Pose `stow` |
| RQ-16 | Operar con 5 Mbps, 10 % de pérdida y 100 ms | Radio | Comunicaciones | P-COM-02 |

## 5. Qué NO se intenta en la v1 (y por qué)

- **Carga de varios kg** (2× el peso del omni): el brazo de servos no llega. Se podría intentar con objetos livianos.
- **Abrir puertas de picaporte**: la punta llega a ~0.92 m, justo en el límite inferior del picaporte (0.9-1.2 m).
  Queda para la v2 (prolongación del brazo o una herramienta específica).
- **Categoría small robot**: requeriría otro robot.

## 6. FIRA 2027 (completar cuando salga el reglamento)

| Pregunta | Respuesta FIRA 2027 | Impacto |
|---|---|---|
| ¿Hay categoría de rescate terrestre? | _pendiente_ | |
| Límites de tamaño y peso | _pendiente_ | |
| Pruebas de movilidad y escaleras | _pendiente_ | |
| Sensado de víctimas (térmica, QR, hazmat, audio) | _pendiente_ | |
| Mapeo y formato de entrega | _pendiente_ | |
| Reglas de radio y autonomía | _pendiente_ | |
