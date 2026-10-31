# CAD paramétrico (CadQuery)

```bash
pip install -r requirements.txt     # CadQuery (≈ 300 MB, incluye OpenCascade)
python build.py                     # todo (≈ 1-2 min)
python build.py --fast              # sin el STEP del ensamble completo
python build.py --only DT-01,FL-01  # solo esas piezas (no regenera el ensamble)
python -m carpincho_cad.params      # imprime las dimensiones principales
```

| Archivo | Contenido |
|---|---|
| `carpincho_cad/params.py` | **Todas** las dimensiones y posiciones. Cambiar acá, nunca en las piezas |
| `carpincho_cad/common.py` | Registro de piezas (`Part`, `Placement`), polea HTD 5M, engranaje |
| `carpincho_cad/chassis.py` | Placas laterales y exteriores, piso, deck, mamparos, asas, separadores |
| `carpincho_cad/drivetrain.py` | Poleas, rodillos, tacos, soportes de motor, correas (cálculo de largos) |
| `carpincho_cad/flipper.py` | Brazos de flipper, cubos, alojamientos, sensor de ángulo |
| `carpincho_cad/arm.py` | Brazo C1 con la cadena cinemática para ubicarlo en cualquier pose |
| `carpincho_cad/mounts.py` | Bandeja de electrónica, cuna de batería, mástil del LiDAR, cabezal, E-stop |
| `out/` | Generado: `step/`, `stl/`, `dxf/`, `carpincho.glb`, `carpincho_ensamble.step`, `parts.json`, `masa_cg.md` |

Coordenadas: mm, X adelante, Y izquierda, Z arriba, origen en el piso bajo el centro entre ejes
(= `base_footprint` del URDF). Las piezas compradas (motores, correas, sensores) se modelan como
referencias simples para ver interferencias y calcular el CG; no se exportan para fabricar.

Para agregar una pieza: escribir una función que devuelva un `cq.Workplane`, agregarla con un `Part(...)` en el
`parts()` del módulo (código único, material, proceso, ubicaciones) y correr `build.py`.
