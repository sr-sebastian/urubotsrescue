# Documentación del Carpincho URB-R1

| # | Sección | Documentos |
|---|---|---|
| 00 | **Plan** | [Plan maestro](00-plan/plan-maestro.md) (objetivo, cronograma, roles, presupuesto, riesgos, decisiones) · [Backlog](00-plan/backlog.md) |
| 01 | **Reglamento** | [Reglamento y estrategia de puntaje](01-reglamento/reglamento-y-estrategia.md) (objetivo 2027; base 2026D hasta que salga el nuevo; matriz de requisitos, FIRA) |
| 02 | **Arquitectura** | [Arquitectura del sistema](02-arquitectura/arquitectura.md) (bloques, interfaces, grafo ROS, TF, estados y seguridad) |
| 03 | **Mecánica** | [Diseño mecánico](03-mecanica/diseno-mecanico.md) · [Piezas](03-mecanica/piezas.md) *(generado)* · [Cálculos](03-mecanica/calculos.md) *(generado)* · [Masa y CG](../cad/out/masa_cg.md) *(generado)* |
| 04 | **Electrónica** | [Electrónica, potencia y cableado](04-electronica/electronica.md) (E-stop, fusibles, pinout, arneses) · [BOM](../hardware/bom.md) |
| 05 | **Software** | [Instalación del Jetson](05-software/setup-jetson.md) · [Firmware y protocolo](05-software/firmware.md) · [ROS 2](05-software/ros2.md) · [Percepción](05-software/percepcion.md) · [Mapeo y autonomía](05-software/mapeo-y-autonomia.md) · [Comunicaciones y audio](05-software/comunicaciones.md) · [Calibración](05-software/calibracion.md) |
| 06 | **Armado** | [Guía de armado paso a paso](06-armado/guia-de-armado.md) |
| 07 | **Pruebas** | [Plan de pruebas](07-pruebas/plan-de-pruebas.md) · [Arena casera](07-pruebas/arena-de-pruebas.md) · [Checklists de competencia](07-pruebas/checklist-competencia.md) |
| 08 | **Errores** | [Solución de errores por síntoma](08-errores/solucion-de-errores.md) |

Los documentos *(generado)* se rehacen con `python cad/build.py && python tools/gen_docs.py`: no los edites a mano.
