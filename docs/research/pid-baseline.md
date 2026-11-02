# Baseline PID de yaw

## Pregunta

Esta etapa pregunta si el controlador neuronal provisional EPG→Δ7/FC2→PFL3 ofrece una ventaja medible frente a un controlador convencional más completo que el proporcional usado hasta ahora. La comparación se limita al **yaw**: en los tres casos, los lazos convencionales de la planta estabilizan actitud, altura, velocidad y motores.

El PID es un baseline de ingeniería. Sus parámetros no representan propiedades neuronales ni biológicas.

## Separación entre ajuste y evaluación

Se definieron cuatro geometrías de desarrollo que no aparecen en la evaluación reservada: bearings de −101,25° y 78,75°, combinados con errores iniciales de −120° y 120°. Todas incluyen ruido de posición y heading, 120 ms de retraso y una ráfaga lateral de 0,65 N.

La búsqueda estaba fijada antes de observar los casos reservados:

- `Kp`: 0,8 o 1,1 s⁻¹;
- `Ki`: 0,02 o 0,06 s⁻²;
- `Kd`: 0,03 o 0,08;
- velocidad angular máxima: 1,5 rad/s;
- límite integral: 0,75 rad·s;
- constante del filtro derivativo: 0,12 s.

Las ocho combinaciones alcanzaron 4/4 metas. El desempate predefinido usó, en orden, éxitos, eficiencia mediana de trayectoria, progreso terminal y distancia final. Ganó `Kp=1,1`, `Ki=0,06`, `Kd=0,08`. Desde ese punto los parámetros quedaron congelados.

El controlador usa el error angular circular más corto. La derivada se filtra, el primer paso no produce *derivative kick* y la integración se detiene cuando empuja más hacia una saturación. Estas decisiones son convencionales y están explícitas en el código; no se atribuyen a FlyWire.

## Evaluación reservada

Se evaluaron 16 combinaciones reservadas de bearing y heading inicial en cada condición. PID y proporcional se ejecutaron de nuevo. Los resultados neuronales intactos se reutilizaron de experimentos congelados que emplearon las mismas geometrías, planta y perturbaciones.

| Condición | Controlador | Llegadas | Eficiencia mediana | Distancia final mediana | Inclinación máxima |
|---|---:|---:|---:|---:|---:|
| Ideal | Neuronal | 16/16 | 0,9694 | 0,2143 m | 5,16° |
| Ideal | PID | 16/16 | 0,9915 | 0,2119 m | 5,38° |
| Ideal | Proporcional | 16/16 | 0,9911 | 0,2092 m | 5,35° |
| Moderada | Neuronal | 16/16 | 0,7688 | 0,1637 m | 7,28° |
| Moderada | PID | 16/16 | 0,7860 | 0,1610 m | 5,59° |
| Moderada | Proporcional | 16/16 | 0,7687 | 0,1621 m | 5,57° |
| Fuerte | Neuronal | 16/16 | 0,5360 | 0,0545 m | 11,63° |
| Fuerte | PID | 16/16 | 0,5973 | 0,0338 m | 10,14° |
| Fuerte | Proporcional | 16/16 | 0,5769 | 0,0350 m | 10,11° |

La tasa de éxito no distingue a los controladores: todos obtuvieron 48/48. En ideal, PID y proporcional son casi iguales y ambos trazan caminos más cortos que el neuronal. Con perturbación moderada, PID mejora la eficiencia media pareada frente al proporcional en 0,0200; su intervalo *bootstrap* del 95 % fue [0,0134, 0,0264]. Frente al neuronal, la diferencia media fue 0,0055 y el intervalo [−0,0353, 0,0409], por lo que estos casos no establecen una diferencia clara. Con perturbación fuerte, PID mejora 0,0204 frente al proporcional, intervalo [0,0171, 0,0239], y 0,0584 frente al neuronal, intervalo [0,0412, 0,0776].

Los intervalos remuestrean los 16 pares deterministas. Los valores de Wilcoxon guardados son exploratorios y no están corregidos por comparaciones múltiples. No equivalen a réplicas físicas, poblaciones de moscas ni evidencia de superioridad biológica.

## Interpretación

El resultado positivo es que el circuito neuronal intacto sigue controlando el yaw y alcanza todas las metas, incluso bajo la condición fuerte. Las ablaciones y nulos anteriores muestran además que ese comportamiento depende de la organización provisional derivada de FlyWire dentro del modelo.

El resultado limitante es igualmente claro: el circuito no supera al baseline convencional. El PID congelado iguala su confiabilidad y produce trayectorias más eficientes en la condición fuerte. Por lo tanto, la afirmación respaldada continúa siendo **control funcional y dependencia de arquitectura**, no ventaja de desempeño.

Este contraste ayuda a orientar el siguiente trabajo. Afinar sólo la ganancia de salida neuronal podría optimizar la trayectoria, pero no demostraría una ventaja de la arquitectura. La siguiente prueba de mayor valor debe exigir adaptación o generalización que no haya sido usada para ajustar ninguno de los controladores, por ejemplo perturbaciones temporales nuevas, múltiples obstáculos móviles o cambios de dinámica de la planta. Debe conservarse el PID congelado.

## Reproducibilidad

- Configuración y partición: `configs/pid_baseline.yaml`.
- Fuentes de la comparación pareada: `configs/pid_comparison.yaml`.
- Implementación PID: `src/flydrone/simulation/yaw_pid.py`.
- Selección y vuelos reservados: `src/flydrone/simulation/benchmark_pid.py`.
- Comparación pareada: `src/flydrone/simulation/analyze_pid_comparison.py`.
- Parámetros elegidos: `results/simulation/pid_baseline/selected_pid.yaml`.
- Episodios y ranking: `results/simulation/pid_baseline/`.
- Informe trazable: `results/simulation/pid_baseline/comparison_report.json`.

## Próximo paso concreto

Diseñar antes de ejecutar una matriz fuera de distribución con cambios de masa/inercia, ráfagas temporales no vistas y obstáculos móviles. Ejecutar sin reajustes al neuronal, PID y proporcional. La métrica primaria debe fijarse antes de correrla: tasa de llegada sin colisión; eficiencia de trayectoria y esfuerzo de control quedan como métricas secundarias.
