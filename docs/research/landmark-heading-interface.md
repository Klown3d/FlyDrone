# Interfaz de landmark para heading

## Alcance

La aplicación ya no presenta el cue externo como heading sin procedencia. Simula una baliza fija con bearing mundial conocido. El sensor genera el bearing relativo observado y reconstruye heading mediante la diferencia circular. El botón `Landmark ON/OFF` entrega u oculta ese cue al estimador de fase.

Esta es una **abstracción computacional de percepción**. No procesa píxeles, no reconstruye neuronas visuales y no demuestra reconocimiento biológico de landmarks. Sirve para hacer explícita la fuente externa que corrige EPG.

## Implementación

- Sensor: `src/flydrone/simulation/landmark_heading_sensor.py`.
- Configuración: `configs/landmark_heading_sensor.yaml`.
- Baliza visible: dirección mundial 70° y distancia de visualización 4,5 m.
- Modo perturbado: ruido gaussiano de 3° aplicado al bearing relativo.
- Salida: cue circular de heading para `PhaseCompassEstimator`.

Las pruebas verifican recuperación de heading a ambos lados de ±180° y que el ruido se aplica a la observación relativa. El smoke test de la aplicación completa navegación plana, 6DoF, ráfaga y obstáculo con esta interfaz.

## Limitación y próximo paso

Conocer el bearing mundial de la baliza presupone un mapa. Una extensión posterior podría probar landmarks ambiguos, cambios de identidad o una observación visual real. Eso requeriría otro gate y no se presentará como parte del connectoma central hasta reconstruir la vía sensorial correspondiente.
