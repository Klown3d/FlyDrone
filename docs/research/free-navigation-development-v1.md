# Desarrollo de navegación libre v1

Fecha: **2026-11-02**. Estado: **benchmark exploratorio completado; no es un gate prospectivo**.

## Pregunta

¿Puede el gestor de comportamiento de ingeniería encadenar metas temporales de patrulla y exploración mientras el controlador FlyWire-grounded mantiene el control de alto nivel del quadrotor 6-DoF?

La arquitectura evaluada fue:

`gestor de comportamiento de ingeniería → meta temporal → EPG/Δ7/FC2/PFL3 + PFL2 + PFN/hΔB → steering/avance/deriva → estabilizador convencional`

El gestor no representa planificación, visión ni memoria biológica. El estabilizador de actitud, altitud y motores sigue siendo convencional. La brújula híbrida usa asistencia inercial de ingeniería durante pérdida de heading.

## Diseño

- 2 controladores: `flywire_hybrid` y `conventional_navigation`;
- 2 modos: patrulla y exploración determinista;
- 2 escenarios: nominal y perturbado;
- 90 s simulados por episodio;
- 8 episodios totales;
- trazas completas a frecuencia de control;
- misma planta 6-DoF y mismas metas para ambos controladores.

La heurística se escribió antes de ejecutar: patrulla requería al menos 4 metas; exploración, al menos 6 metas y 30% de cobertura; ambos requerían no escapar del espacio más del 2% del tiempo. Es una regla de desarrollo y no una métrica primaria preregistrada.

## Resultado

| Controlador | Modo | Éxitos de desarrollo | Mediana de metas | Cobertura mediana | Tiempo estancado mediano |
|---|---:|---:|---:|---:|---:|
| FlyWire híbrido | patrulla | 2/2 | 7,5 | 64% | 12,8% |
| Convencional | patrulla | 2/2 | 7,5 | 62% | 19,8% |
| FlyWire híbrido | exploración | 1/2 | 7,5 | 62% | 13,6% |
| Convencional | exploración | 1/2 | 8,0 | 60% | 19,9% |

Los dos fallos ocurrieron en exploración perturbada: ambos controladores completaron 5 metas, por debajo del umbral de 6. No se cambió el umbral después del resultado. Ningún episodio salió del espacio de trabajo, colisionó o saturó motores.

En el híbrido, el comando neural de yaw estuvo activo en 99,84–100% de las muestras y la población hΔB tuvo actividad no nula en 90,89–98,44%. La integración inercial dominó la estimación de heading durante 11,11% de los episodios perturbados, coincidente con la pérdida sensorial programada. Por eso el resultado demuestra participación continua del circuito, pero no atribuye toda la robustez a la brújula neural.

## Interpretación

El resultado es positivo para la integración: el sistema encadenó metas sin reiniciar el quadrotor y el controlador FlyWire-grounded fue comparable con el convencional en esta muestra pequeña. No hay evidencia de superioridad. La menor fracción estancada del híbrido es una observación exploratoria con sólo dos episodios por modo y no debe tratarse como efecto confirmado.

La cobertura no es suficiente por sí sola: el viento puede aumentar el área recorrida sin mejorar la tarea. El futuro gate debe usar metas completadas o tasa de metas como resultado primario, con cobertura y estancamiento como métricas secundarias.

## Próximo paso

1. ampliar el desarrollo a headings y semillas adicionales;
2. fijar una tasa primaria de metas completadas por minuto y un margen de comparabilidad frente al convencional;
3. mantener como criterios de seguridad escape, colisiones y saturación;
4. congelar escenarios nuevos que no se utilicen durante desarrollo;
5. ejecutar una única vez el gate de navegación libre.

## Artefactos

- configuración: `configs/free_navigation_development.yaml`;
- episodios: `results/simulation/free_navigation_development_v1/episodes.csv`;
- resumen: `results/simulation/free_navigation_development_v1/summary.csv`;
- reporte y hashes: `results/simulation/free_navigation_development_v1/report.json`;
- trazas: `results/simulation/free_navigation_development_v1/traces/`.
