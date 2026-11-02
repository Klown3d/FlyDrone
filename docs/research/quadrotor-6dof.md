# Primera integración con quadrotor de seis grados de libertad

Fecha: 2026-09-19. Estado: primer banco determinista completado.

## Alcance

La nueva planta integra posición y velocidad en tres ejes, cuaternión de actitud, velocidades angulares, inercia rígida, gravedad, arrastre lineal/angular, cuatro motores con respuesta de primer orden, empuje y torques de roll/pitch/yaw. Usa marco mundial ENU y ejes corporales x hacia delante, y hacia la izquierda, z hacia arriba.

Todos los parámetros del vehículo son **valores de ingeniería genéricos no validados contra un dron real**. No se incluyen aerodinámica de hélices, efecto suelo, batería, flexibilidad estructural, turbulencia ni sensores imperfectos.

## Separación de responsabilidades

- **FlyWire provisional EPG→Δ7/FC2→PFL3:** produce exclusivamente la orden de velocidad yaw.
- **Control convencional:** altura, velocidad hacia delante, amortiguación lateral, actitud roll/pitch, mezcla de motores y estabilización angular.
- **Física:** la traslación horizontal sólo aparece mediante inclinación y empuje; no se actualiza x/y directamente.

Así, el circuito determina hacia dónde se orienta el avance, pero no se le atribuye estabilización de un quadrotor. El proporcional sustituye sólo la orden yaw y comparte todo lo demás.

## Diseño

Se probaron ocho direcciones de meta y cuatro errores iniciales de heading (32 casos por controlador), meta a 4 m y altura de 2 m. La física se integró a 500 Hz y la señal neuronal se actualizó a 50 Hz durante 25 s. Éxito exige permanecer los dos segundos finales dentro de 30 cm, velocidad ≤12 cm/s, altura ±10 cm y sin tocar el suelo.

## Resultados

| Controlador yaw | Éxitos | Distancia final mediana | Eficiencia de trayectoria mediana | Inclinación máxima | Saturación máxima de motores |
|---|---:|---:|---:|---:|---:|
| FlyWire provisional | **32/32** | 21,19 cm | 97,24% | 5,19° | 0% |
| Proporcional | **32/32** | 21,09 cm | 99,23% | 5,36° | 0% |

La eficiencia mínima neuronal fue 94,61%, frente a 98,30% proporcional. La distancia final máxima neuronal fue 23,04 cm, todavía dentro del umbral. Estos ensayos apoyan compatibilidad del controlador neuronal con una planta rígida 6DoF; **no muestran superioridad sobre el proporcional**.

## Productos reproducibles

- Configuración: `configs/quadrotor.yaml`, `configs/quadrotor_benchmark.yaml`.
- Episodios y resumen: `results/simulation/quadrotor_6dof/episodes.csv`, `summary.csv`.
- Trazas representativas: `neural-representative-trace.npz`, `proportional-representative-trace.npz`.
- Figura: `representative-comparison.png`.
- Informe con hashes: `report.json` y `data/manifest.json`.

## Robustez con parámetros congelados

Después del banco inicial se fijaron planta y ganancias y se evaluaron 64 episodios adicionales, ocho geometrías por escenario y controlador:

| Escenario | FlyWire | Proporcional | Eficiencia mediana FlyWire / proporcional | Inclinación máxima FlyWire / proporcional |
|---|---:|---:|---:|---:|
| Ruido 5 cm + 3° + retraso 100 ms | 8/8 | 8/8 | 97,58% / 99,83% | 5,21° / 5,60° |
| Ráfaga lateral 0,5 N, 4 s | 8/8 | 8/8 | 75,27% / 77,48% | 5,23° / 5,38° |
| Combinación moderada | 8/8 | 8/8 | 74,54% / 76,71% | 5,42° / 5,64° |
| 15 cm + 8° + 200 ms + ráfaga 1 N, 7 s | 8/8 | 8/8 | 55,77% / 57,62% | 10,47° / 9,54° |

No hubo saturación de motores. La combinación fuerte mantuvo éxito terminal, pero produjo trayectorias mucho menos eficientes y mayor inclinación. La distancia final pequeña en ese escenario no implica mejor control: el ruido prolonga y hace oscilar la aproximación, aumentando la oportunidad de cruzar cerca de la meta.

Los efectos fueron parecidos en ambos controladores y el proporcional conservó una ligera ventaja de eficiencia. Esto respalda robustez inicial del acoplamiento neuronal con la planta, no una ventaja de FlyWire.

## Límites y siguiente prueba

El modo 6DoF seleccionable ya fue incorporado a la aplicación. También se validó una primera [capa convencional de evasión de un obstáculo](obstacle-navigation.md): con la regla final congelada, el controlador neuronal y el proporcional lograron 16/16 casos nuevos sin colisiones. Las [ablaciones computacionales del circuito](circuit-ablation-6dof.md) mostraron 16/16 con la arquitectura intacta, 0/16 sin Δ7, 0/16 sin FC2 y 0/80 en cinco grafos barajados. Todavía faltan ruido específico de IMU, variación de masa/inercia, viento continuo, fallos de motor, múltiples distancias y obstáculos, y validación de parámetros contra un airframe.
