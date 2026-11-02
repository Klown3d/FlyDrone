# Metas nuevas y estimación imperfecta de posición

Fecha: 2026-09-18. FlyWire/FAFB 783. Modelo provisional; planta espacial simplificada.

## Qué cambió en la evaluación

Se conservaron pesos, fases, ganancias e interfaz neuronal. Se generaron 64 casos nuevos con posiciones iniciales en [−3,3] m por eje, direcciones continuas de meta y heading inicial, y distancias de 2/5/8 m. Los mismos casos se comparten entre escenarios y controladores; están guardados en `cases.csv`. No se ajustaron parámetros a sus resultados. Las geometrías nuevas usan semilla 794.

La posición estimada determina tanto la dirección de meta que recibe el circuito como el avance, frenado y confirmación de llegada convencionales. Ya no se usa posición real para resolver estas decisiones en el banco perturbado. La velocidad observada es exacta pero retrasada; altitud es ideal, al igual que la ubicación de la meta. El estado real se conserva para la planta y la evaluación. No se simula visión ni un estimador de posición realista.

Escenarios: ideal; ruido IID de posición 5 cm y heading 3°, retraso configurado 150 ms (implementado **160 ms** al discretizar a 20 ms); ruido de posición 15 cm, sesgo fijo por episodio de magnitud 20 cm en dirección aleatoria, heading 3° y retraso 300 ms. Las condiciones perturbadas usan semillas 794/795. Ruido y sesgo son idénticos entre controladores por realización. La semilla de generación de geometrías coincide numéricamente con una realización de observación; este diseño no se presenta como un muestreo independiente exhaustivo de entornos y sensores.

Duración 30 s y paso 20 ms. Éxito conserva el criterio previo de parada, distancia real ≤30 cm, velocidad ≤8 cm/s y altura correcta durante los últimos 2 s, sin contacto muestreado con suelo. No se relajó el umbral al observar fallos.

## Resultados de 640 episodios

| Escenario | Neuronal | Proporcional |
|---|---:|---:|
| Geometrías nuevas, sensores ideales | 64/64 | 64/64 |
| Ruido leve de posición | 128/128 | 128/128 |
| Sesgo y ruido de posición | **126/128 (98,44%)** | **128/128** |

Distancia final mediana neuronal: 8,07 cm ideal, 5,64 cm con ruido leve y 19,89 cm con sesgo. Proporcional: 7,75/4,97/19,97 cm. La mediana algo menor del circuito en la condición de sesgo no compensa sus dos fallos ni demuestra ventaja. La comparación actual sigue sin apoyar superioridad neuronal.

## Casos que fallaron

Ambos corresponden al escenario con sesgo, semilla 794 y controlador neuronal:

- Caso 21, distancia inicial 2 m: quedó detenido a **31,65 cm**. La parada se activó a 6,52 s; la posición estimada indicaba 5,31 cm de distancia, frente a 32,22 cm reales antes de actualizar la planta.
- Caso 28, distancia inicial 5 m: quedó a **30,03 cm**, apenas fuera del umbral fijado. Parada a 12,32 s; distancia estimada 20,26 cm frente a 30,01 cm reales antes de actualizar la planta.

El módulo convencional activa una parada persistente al cumplir el criterio en una observación. Las trazas muestran que ambas paradas se activaron fuera del radio físico objetivo y permanecieron activas; no son divergencias hacia infinito. La trayectoria neuronal y el error de estimación interactúan con esa política: no se atribuye el fallo exclusivamente a conectividad ni se declara que el problema carezca de componente neuronal. El proporcional utiliza la misma política y no falló en este conjunto.

Un sesgo absoluto no se puede eliminar simplemente promediando ruido IID: aun con confirmación temporal, la posición puede seguir equivocada. Esto limita cualquier promesa de precisión real basada solo en la posición estimada.

## Productos y verificación

```powershell
.venv\Scripts\python.exe -m flydrone.simulation.generalize_navigation
.venv\Scripts\python.exe -m pytest tests/test_navigation.py tests/test_hover.py tests/test_steering_interface.py -q
```

Configuración: `configs/navigation_generalization.yaml`. Productos en `results/simulation/navigation_generalization/`: casos, episodios, resumen, fallos, diagnóstico de eventos e informe con hashes. Las trazas NPZ conservan posición real/observada, heading, comandos, parada persistente, sesgo, tasas PFL3 y desviaciones Δ7 por ID.

La función compartida de navegación admite observación explícita; su comportamiento anterior y la aplicación actual siguen usando observación ideal por defecto. **Los modos sensoriales perturbados todavía no se agregaron a la interfaz de escritorio.** Siete pruebas relacionadas pasaron, incluyendo una que demuestra que la llegada se decide por observación y no por posición privilegiada.

## Decisión y siguiente paso

Se confirma generalización inicial a esta muestra de metas nuevas y tolerancia al ruido leve. El resultado con sesgo queda parcialmente fallido y debe preservarse como tal. Son pocas geometrías/realizaciones, sin inferencia estadística fuerte y con dinámica restringida; la anatomía Δ7 permanece provisional.

Antes de obstáculos: implementar y comparar una confirmación temporal de llegada y una política que permita recuperar movimiento cuando la evidencia estimada de llegada deje de sostenerse, sin utilizar posición real para decidirlo. Separar explícitamente el tratamiento del ruido aleatorio y del sesgo persistente, guardar la política anterior como control y evaluar realizaciones nuevas después de fijar la alternativa. Después incorporar esos escenarios a la aplicación.
