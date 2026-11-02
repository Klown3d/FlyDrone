# Sensibilidad local del controlador integrado v4

Se ejecutaron siete condiciones sobre los mismos cuatro casos de desarrollo:
dos metas, una orientación relativa y dos perfiles de perturbación. Todos los
parámetros restantes se conservaron. Son 28 vuelos diagnósticos y no un gate
confirmatorio.

| Condición | Llegadas | Mediana de máximo desvío lateral (m) | Mediana de llegada (s) |
|---|---:|---:|---:|
| Nominal | 4/4 | 1.719 | 22.789 |
| Ganancia steering ×0.8 | 4/4 | 1.892 | 23.947 |
| Ganancia steering ×1.2 | 4/4 | 1.559 | 25.870 |
| Ganancia deriva ×0.8 | 4/4 | 2.060 | 23.247 |
| Ganancia deriva ×1.2 | 4/4 | 1.525 | 23.899 |
| Constante temporal brújula 0.08 s | 4/4 | 1.610 | 22.830 |
| Constante temporal brújula 0.12 s | 4/4 | 1.879 | 23.169 |

La constante temporal nominal es 0.10 s. Las ganancias y constantes son
parámetros de ingeniería del modelo, no mediciones fisiológicas nuevas.

El resultado respalda tolerancia local a cambios de ±20% en tres parámetros
por separado sobre estos casos. No demuestra una región amplia de estabilidad,
robustez ante interacciones simultáneas ni persistencia de la ventaja sobre
nulos fuera del régimen de evaluación anterior. Cada condición contiene sólo
cuatro casos: el intervalo Wilson descriptivo del 95% para 4/4 es aproximadamente
51--100%, lo que muestra el límite del tamaño de muestra. Los casos son pareados
y reutilizados; no deben agruparse como 28 observaciones independientes.

Reproducción de la lógica:

- `scripts/run_integrated_sensitivity.py`
- `configs/integrated_v4_sensitivity.yaml`
- `configs/integrated_v4_tau_sensitivity.yaml`
- `configs/sensitivity_compass_tau080.yaml`
- `configs/sensitivity_compass_tau120.yaml`

Resultados conservados en `results/simulation/integrated_v4_sensitivity/` y
`results/simulation/integrated_v4_tau_sensitivity/`. El ejecutor rechaza sobrescribir
un informe terminado; una repetición debe usar otra salida versionada.
