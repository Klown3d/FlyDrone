# Diagnóstico por oráculos del fallo OOD preservado

## Pregunta

El piloto OOD dejó un fallo con pérdida simultánea y prolongada de heading y
velocidad. Este diagnóstico pregunta qué observación, sustituida de forma
aislada por la verdad privilegiada del simulador, basta para rescatar exactamente
esa geometría.

No es una nueva evaluación de rendimiento. Los oráculos no son sensores
disponibles para el controlador y los resultados no se suman al 5/6 del piloto.

## Reproducción

Se reconstruyó el caso de meta a 107°, heading relativo inicial de −137° y
semilla efectiva 20400113. La condición observada reprodujo el resultado
original exactamente:

- fallo en ambas ejecuciones;
- distancia final: 11,2178 m en ambas;
- máximo desvío transversal: 24,4780 m en ambas.

La coincidencia evita atribuir diferencias a una semilla distinta.

## Intervenciones pareadas

| Condición diagnóstica | Resultado | Distancia final (m) | Máximo desvío (m) | Error mediano de heading durante corte |
|---|---:|---:|---:|---:|
| Observaciones originales | Fallo | 11,218 | 24,478 | 88,30° |
| Heading verdadero | Llegada | 0,171 | 2,067 | 5,49° |
| Velocidad verdadera | Fallo | 1,883 | 14,825 | 96,74° |
| Heading y velocidad verdaderos | Llegada | 0,177 | 2,122 | 5,47° |

El heading verdadero se aplicó tanto al steering como a la entrada angular de
PFN/hΔB. La velocidad verdadera sólo reemplazó la entrada de movimiento del
modelo de deriva; la brújula neuronal continuó controlando steering.

## Interpretación

Para este único caso preservado, corregir heading es suficiente para recuperar
la llegada; corregir velocidad por sí sola no lo es. La explicación dominante
queda localizada en la vía de heading o en su uso posterior, no en la estimación
de velocidad por sí sola. El oráculo combinado también llega y lo hace antes,
lo que indica que la velocidad todavía afecta eficiencia, aunque no explica el
fallo binario principal.

Esto no demuestra todavía que el mismo mecanismo explique todos los fallos ni
que una modificación de la brújula vaya a generalizar. Es una intervención de
un caso, diseñada después de observar el piloto. La conclusión válida es local:
**la verdad de heading rescata este fallo; la verdad de velocidad sola no**.

## Artefactos

- Configuración: `configs/quadrotor_integrated_v4_ood_failure_oracles.yaml`.
- Corridas y trazas: `results/simulation/quadrotor_integrated_v4_ood_failure_oracles/`.
- Resultado resumido: `diagnosis.json`.
- Métricas por etapa sensorial: `epoch_metrics.csv`.
- Trayectorias y error angular: `oracle_diagnosis.png`.
- Regeneración del análisis: `scripts/analyze_ood_failure_oracles.py`.
- Preservación posterior: `archive/integrated_v4_ood_failure_oracles/`.
- Reproducción visual: selector **Diagnostico OOD** del comparador 3D.

Los hashes de configuración, episodios y cuatro trazas están incluidos en
`diagnosis.json`.

## Próximo experimento correcto

Antes de cambiar parámetros, debe diseñarse una matriz diagnóstica más amplia
con varias geometrías nuevas y cuatro condiciones pareadas: observada, heading
verdadero, velocidad verdadera y ambos verdaderos. Si el patrón se repite, una
v5 de la brújula podrá desarrollarse en escenarios separados y luego evaluarse
en un conjunto OOD sellado nuevo. No se debe reajustar v4 usando el caso que
produjo este diagnóstico y luego presentarlo como validación independiente.
