# Checklists de competencia

Imprimir, plastificar y usar con fibrón al agua. **Una persona lee en voz alta, otra hace y confirma.**

## A. Al llegar a la sede (día 0)

- [ ] Inventario de la valija (robot, repuestos, herramientas, cargadores, routers, joysticks ×2, notebook ×2)
- [ ] Baterías a 3.8 V/celda (almacenamiento) → cargar las de mañana
- [ ] Escanear el Wi-Fi y elegir canal; configurar los 2 routers
- [ ] Encendido completo + prueba de E-stop
- [ ] Fotos de la arena real, de las etiquetas y de la iluminación → dataset para el *fine-tune* de hazmat
- [ ] Medir los carriles (largo entre zonas) → `lane_length` por carril en `autonomy.yaml`
- [ ] Pre-mapear los carriles si está permitido (fuera del laberinto)

## B. Antes de cada prueba (en el paddock, T−15 min)

- [ ] Batería **cargada** (≥ 24.6 V) y amarrada
- [ ] Bulones marcados con pintura: ninguno se movió
- [ ] Orugas: tensión, tacos completos (reponer si falta alguno)
- [ ] Flipper calibrado (`/base/zero_flipper` con nivel)
- [ ] Brazo en `stow`, cámaras limpias (paño de microfibra)
- [ ] `ros2 launch` sin errores; `/base/status`: `link_ok`, sin fallas
- [ ] Foxglove conectado con el layout correcto; latencia del video OK
- [ ] Audio: probar ida y vuelta
- [ ] `mission:=<nombre de la misión>` correcto y `/mission/start` listo (si es laberinto)
- [ ] Repuestos de la pista en la caja: batería extra, correa, 10 tacos, polea, fusibles

## C. En la zona de inicio (5 min de preparación)

- [ ] Robot en la zona de inicio, **mirando a lo largo del carril**
- [ ] E-stop liberado; armar (START) y luces encendidas
- [ ] Brazo en `stow` (obligatorio para la destreza autónoma)
- [ ] El operador en la estación, sin ver el robot. El "proctor" listo
- [ ] Si se va a hacer autonomía: avisar al proctor **antes** de apretar GUIDE y soltar el joystick

## D. Durante la prueba

- **Movilidad (10 min)**: primero 1 ida y vuelta teleoperada (asegura los 2 puntos que habilitan la destreza),
  después **autónomo**. Si el autónomo falla 2 veces seguidas, seguir teleoperado.
- **Destreza (10 min)**: empezar por las tareas que ya salieron en el día de pista. Nada de improvisar.
- **Cajón de víctimas (2 min)**: robot **quieto**; orden: QR → hazmat → térmica → movimiento → imán → audio.
- Reset: se puede pedir; dura ≥ 2 min. Usarlo si el robot quedó trabado y se pierde más tiempo que eso.

## E. Laberinto

- [ ] `/mission/start` en el punto de inicio **antes** de moverse
- [ ] Mapa rápido (≤ 5 min) → `/mission/export` → copiar
- [ ] Mapa completo (≤ 15 min) → `/mission/export` → `./operator/fetch_mission.sh` → USB de los jueces en < 5 min
- [ ] **No abrir ni editar** los archivos antes de entregarlos

## F. Después de cada prueba

- [ ] Anotar el puntaje y qué falló, con la hora (para buscarlo en el bag/log)
- [ ] Batería a cargar; revisar la temperatura de motores y drivers
- [ ] Inspección rápida: tacos, correas, bulones marcados, cables
- [ ] `git` con el estado del software usado en esa prueba (`git describe` en el registro)

## G. Caja de repuestos de la pista (mínimo)

| Ítem | Cant. |
|---|---:|
| Batería cargada | 1 |
| Correa de oruga (1100) y de flipper (760) | 1 + 1 |
| Tacos de TPU + remaches + adhesivo rápido | 20 |
| Polea DT-01 y DT-02 | 1 + 1 |
| Servo STS3215 con el ID marcado | 1 |
| Fusibles ATO 3/5/10/20/40 A | 2 c/u |
| ESP32 flasheado + cable USB | 1 |
| Bulonería, precintos, cinta, llaves Allen | kit |
