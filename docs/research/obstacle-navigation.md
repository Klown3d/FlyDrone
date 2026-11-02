# Navegación 6DoF con un obstáculo

Fecha: 2026-09-19. Estado: primera capa de seguridad geométrica validada en casos no usados para corregirla.

## Pregunta y alcance

La prueba pregunta si el steering provisional basado en FlyWire puede conducir la planta 6DoF alrededor de un obstáculo cuando una capa convencional le entrega una meta local segura. El obstáculo es un cilindro vertical idealizado mediante un círculo horizontal; no hay percepción por cámara, SLAM ni reconstrucción tridimensional.

La división funcional es explícita:

- la capa convencional detecta si el segmento a la meta cruza el obstáculo y elige un punto intermedio;
- el modelo EPG→Δ7/FC2→PFL3 compara heading y dirección de ese punto y produce exclusivamente velocidad yaw;
- los controladores convencionales regulan avance, altura, roll, pitch y motores;
- el baseline proporcional reemplaza únicamente la orden yaw.

Por tanto, estos experimentos no atribuyen detección ni planificación de obstáculos al circuito de la mosca.

## Geometría

La meta está a 4 m y 2 m de altura. El obstáculo se ubica a mitad del trayecto, con radio 0,55 m. La envolvente horizontal del dron se aproxima con radio 0,30 m, se exige margen de 0,20 m y el punto lateral añade 0,45 m. Los valores son decisiones de ingeniería y no parámetros biológicos ni medidas de un airframe real.

Se considera colisión cuando la separación entre el centro del dron y la superficie del obstáculo, descontando el radio del vehículo, cae por debajo de cero. El criterio de llegada conserva los requisitos del banco 6DoF: dos segundos finales dentro de 30 cm, velocidad ≤12 cm/s, altura ±10 cm y sin colisión.

## Desarrollo preservado

### v1: lado fijo

El planificador calculaba dos puntos geométricamente válidos pero, en igualdad de longitud, elegía siempre el mismo lado. En ocho casos por controlador:

| Controlador yaw | Llegadas | Colisiones | Separación mediana | Eficiencia mediana |
|---|---:|---:|---:|---:|
| FlyWire provisional | 5/8 | 3/8 | 0,374 m | 0,708 |
| Proporcional | 8/8 | 0/8 | 0,365 m | 0,731 |

Las tres colisiones neuronales ocurrieron con error inicial de −120°. El mismo conjunto con +120° no colisionó. Este patrón direccional indicó una interacción entre el lado elegido y el giro requerido.

### v2: retener el punto intermedio

Se probó la hipótesis de que el punto se liberaba demasiado pronto. Retenerlo hasta aproximarse a 0,25 m no cambió las tres colisiones neuronales y redujo el baseline proporcional a 4/8 llegadas por agotamiento del tiempo, aunque sin colisiones. La hipótesis quedó rechazada y el resultado se conserva en `results/simulation/quadrotor_6dof_obstacles_v2_diagnostic/`.

### v3: lado compatible con el rumbo

La corrección final puntúa ambos puntos seguros por el valor absoluto del giro inicial y elige el menor. Para una meta hacia delante, un dron orientado a +120° usa el paso superior y uno orientado a −120° usa el inferior. Esta regla sólo decide la meta local; no modifica pesos, actividad ni dinámica neuronal.

Al repetir los ocho casos de desarrollo, ambos controladores lograron 8/8 llegadas y cero colisiones. Esta repetición es diagnóstico, no validación independiente.

## Prueba con casos no usados

Con la regla v3 congelada se evaluaron direcciones de meta −157,5°, −67,5°, 22,5° y 112,5°, cruzadas con errores iniciales −150°, −45°, 45° y 150°. Ninguno de esos ángulos se utilizó en v1–v3. Fueron 16 episodios por controlador, con semilla 821.

| Controlador yaw | Llegadas | Colisiones | Separación mediana | Eficiencia mediana | Inclinación máxima |
|---|---:|---:|---:|---:|---:|
| FlyWire provisional | **16/16** | **0/16** | 0,500 m | 0,729 | 7,12° |
| Proporcional | **16/16** | **0/16** | 0,536 m | 0,744 | 7,10° |

La prueba apoya que el steering neuronal provisional puede seguir metas locales alrededor de este obstáculo bajo la planta simulada. El proporcional también resolvió todos los casos y conservó una ligera ventaja de eficiencia y separación mediana. No hay evidencia de superioridad neuronal.

![Evolución del planificador](../../results/simulation/quadrotor_6dof_obstacles_v3_held_out/obstacle-progression.png)

## Reproducibilidad

- v1: `configs/quadrotor_obstacles.yaml` y `results/simulation/quadrotor_6dof_obstacles/`.
- v2 diagnóstico: `configs/quadrotor_obstacles_v2_diagnostic.yaml`.
- v3 diagnóstico: `configs/quadrotor_obstacles_v3_diagnostic.yaml`.
- v3 casos no usados: `configs/quadrotor_obstacles_v3_held_out.yaml`.
- Geometría y selección: `src/flydrone/simulation/obstacles.py`.
- Ejecutor: `src/flydrone/simulation/benchmark_obstacles.py`.
- Cada carpeta contiene episodios CSV, resumen e informe con hashes; `data/manifest.json` registra los productos.

## Límites y siguiente prueba

Sólo se probó un obstáculo estático, circular y perfectamente conocido. Faltan múltiples obstáculos, formas no circulares, posición imperfecta del obstáculo, replanteamiento en movimiento, viento combinado con evasión y evaluación con un simulador externo. El paso inmediato es exponer el obstáculo y el punto local en la aplicación de escritorio, y luego construir un banco con geometrías múltiples manteniendo los parámetros v3 congelados.
