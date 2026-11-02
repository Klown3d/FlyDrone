# Ablaciones computacionales del circuito en planta 6DoF

Fecha: 2026-09-20. Estado: primer banco cerrado completado con parámetros congelados.

## Pregunta

¿La navegación del controlador provisional depende de la organización EPG→Δ7/FC2→PFL3 derivada de FlyWire, o cualquier conjunto de pesos con tamaño y magnitudes parecidas produciría el mismo resultado?

Esta prueba extiende al lazo de navegación los controles estacionarios descritos en [connectome-model-results.md](connectome-model-results.md). La anatomía, la interpretación de FC2/PFL3 y la no linealidad se basan en datos FlyWire FAFB 783 y en el modelo publicado de Mussells Pires et al. ([Nature 2024](https://doi.org/10.1038/s41586-023-07006-3)). Las intervenciones de este documento son **ablaciones computacionales**, no experimentos realizados en moscas.

## Diseño

Se usó la misma planta rígida 6DoF y el mismo estabilizador convencional en todas las condiciones. El circuito sólo ordena velocidad yaw. Se probaron cuatro direcciones de meta nuevas (−146,25°, −56,25°, 33,75° y 123,75°), cruzadas con errores iniciales de heading −165°, −75°, 75° y 165°: 16 episodios por condición, 30 s por episodio, meta a 4 m y 2 m de altura.

El éxito exige permanecer los dos segundos finales dentro de 30 cm, con velocidad ≤12 cm/s, altura dentro de ±10 cm y sin tocar el suelo. La eficiencia de trayectoria sólo se calcula para episodios exitosos. Para los fallos se informa progreso terminal normalizado: `1 − distancia final / 4 m`.

## Condiciones

- **FlyWire intacto:** pesos normalizados de contactos EPG→Δ7, Δ7→PFL3 y FC2→PFL3.
- **Sin Δ7:** la corriente de heading aportada por Δ7 se fija en cero; FC2 permanece intacta.
- **Sin FC2:** la corriente de meta se fija en cero; EPG→Δ7 permanece intacta.
- **Topología binaria:** se conservan exactamente las conexiones no nulas, pero todas las entradas presentes dentro de cada fila reciben el mismo peso. Esto elimina la multiplicidad relativa de contactos.
- **Cinco grafos barajados:** se permutan de forma independiente los valores dentro de cada fila para las tres proyecciones. Cada neurona postsináptica conserva el número de ceros, el multiconjunto de pesos y su suma de entrada, pero se rompe la correspondencia con identidades presinápticas.
- **Cinco grafos reconfigurados con grados fijos:** intercambios bipartitos 2×2 conservan exactamente el grado binario de entrada y salida de cada neurona y, además, el multiconjunto y la suma de pesos de cada fila. Cada proyección recibe diez intercambios aceptados por arista. No se conserva la suma ponderada de salida de cada columna.
- **Proporcional:** sustituye únicamente el comando yaw; comparte planta, avance y estabilizador.

El primer barajado preserva las estadísticas de entrada por fila, pero no el grado de salida. El segundo control resuelve esa limitación para los grados binarios y permite medir cuánta función puede surgir de una red aleatoria con la misma secuencia de grados.

## Resultado 6DoF

| Condición | Episodios | Llegadas | Progreso terminal mediano | Eficiencia mediana entre éxitos |
|---|---:|---:|---:|---:|
| FlyWire intacto | 16 | **16 (100%)** | 94,64% | 0,969 |
| Sin Δ7 | 16 | **0** | 0,90% | — |
| Sin FC2 | 16 | **0** | 1,34% | — |
| Topología binaria | 16 | **14 (87,5%)** | 93,54% | 0,741 |
| Grafos barajados, cinco semillas | 80 | **0** | 11,04% | — |
| Reconfigurados con grados fijos, cinco semillas | 80 | **7 (8,75%)** | 14,36% | 0,724 |
| Proporcional | 16 | **16 (100%)** | 94,77% | 0,991 |

Los cinco barajados produjeron 0/16 para cada semilla, no sólo 0/80 al agrupar. Sus medianas de progreso variaron entre 0,69% y 75,14%, lo que muestra que algunos grafos generaron movimiento hacia la meta pero ninguno consiguió llegada y frenado.

Los nulos con grados fijos produjeron 0/16, 0/16, 5/16, 0/16 y 2/16. Sus siete éxitos no fueron navegación general: cinco correspondieron a una sola semilla, que resolvió los cuatro headings hacia 33,75° y sólo un caso hacia 123,75°; la otra semilla resolvió dos headings hacia 123,75°. Ningún nulo llegó hacia −146,25° o −56,25°. Esto muestra soluciones direccionales accidentales, no una transformación uniforme equivalente a la intacta.

Los dos fallos de topología binaria ocurrieron para la meta −146,25° con errores iniciales −165° y +165°. Terminaron a 0,687 m y 0,398 m, todavía moviéndose a 0,202 m/s y 0,157 m/s. El modelo intacto resolvió ambos casos.

![Ablaciones del circuito en 6DoF](../../results/simulation/quadrotor_circuit_ablation/circuit-ablation.png)

## Diagnóstico de orientación

Se ejecutó además un lazo de heading sin traslación, durante los mismos 30 s. Exige error ≤10° durante los dos segundos finales.

| Condición | Éxitos de orientación | Error final absoluto mediano |
|---|---:|---:|
| FlyWire intacto | 16/16 | 1,88° |
| Sin Δ7 | 0/16 | 118,30° |
| Sin FC2 | 1/16 | 108,00° |
| Topología binaria | 8/16 | 10,02° |
| Cinco barajados | 5/80 | variable por semilla |
| Cinco reconfigurados con grados fijos | 5/80 | variable por semilla |
| Proporcional | 16/16 | ≈0° |

Que la topología binaria alcance 14 metas espaciales pero sólo estabilice 8 headings muestra que “llegar” y “reproducir orientación” no son equivalentes. La lógica convencional reduce el avance cuando el error angular es grande y frena cerca de la meta; por eso puede aceptar una orientación terminal que el diagnóstico estricto rechaza.

Los éxitos aislados sin FC2 o con grafos barajados son compatibles con equilibrios accidentales para una combinación concreta; no recuperan la función general y no produjeron llegadas 6DoF.

## Localización por proyección

Como selección previa a nuevos vuelos, se reconfiguró una sola proyección por vez con el mismo algoritmo que preserva grados. Se evaluaron cinco semillas y 16 casos de orientación por semilla:

| Proyección reconfigurada | Éxitos de orientación | Tasa |
|---|---:|---:|
| EPG→Δ7 | 2/80 | 2,50% |
| Δ7→PFL3 | 5/80 | 6,25% |
| FC2→PFL3 | 9/80 | 11,25% |

![Nulos separados por proyección](../../results/neural/projection_specific_degree_null/projection-null.png)

La correspondencia específica importa en las tres corrientes. EPG→Δ7 produjo la menor recuperación accidental en este diagnóstico, pero las diferencias entre 2, 5 y 9 éxitos no establecen por sí solas una jerarquía biológica: las matrices tienen tamaños y densidades diferentes y todavía falta la comparación 6DoF emparejada.

### Confirmación 6DoF con semilla nueva

Después del diagnóstico se congeló una semilla común nueva, 931, que no participó en la selección anterior. Se reconfiguró una sola proyección por condición y se conservaron intactas las otras dos:

| Proyección reconfigurada | Llegadas | Progreso terminal mediano |
|---|---:|---:|
| EPG→Δ7 | **0/16** | 1,41% |
| Δ7→PFL3 | **0/16** | 2,29% |
| FC2→PFL3 | **1/16** | 6,58% |

El único éxito de FC2→PFL3 correspondió a meta −146,25° y error inicial −75°, con eficiencia 0,772. No constituye navegación general. La arquitectura intacta había resuelto 16/16 sobre las mismas geometrías. Por tanto, alterar cualquiera de las tres correspondencias reduce fuertemente la navegación; el resultado no puede explicarse sólo por una de las corrientes.

## Robustez con dos nulos congelados

Se mantuvieron el circuito intacto y los nulos EPG→Δ7 y FC2→PFL3 de semilla 931. Cada condición recorrió las mismas 16 geometrías bajo cada escenario, con observaciones perturbadas idénticas para el mismo caso:

| Escenario | FlyWire intacto | EPG→Δ7 reconfigurada | FC2→PFL3 reconfigurada |
|---|---:|---:|---:|
| Moderado: ruido 5 cm y 3°, retraso 100 ms, ráfaga 0,5 N durante 4 s | **16/16** | 0/16 | 1/16 |
| Fuerte: ruido 15 cm y 8°, retraso 200 ms, ráfaga 1 N durante 7 s | **16/16** | 0/16 | 0/16 |

La eficiencia mediana del intacto entre vuelos exitosos fue 0,769 en el escenario moderado y 0,536 en el fuerte. La perturbación fuerte alargó notablemente la trayectoria, aunque no redujo la tasa de llegada. El único éxito nulo moderado correspondió a meta 123,75° y error inicial 75°, con distancia final 0,295 m, apenas dentro del radio de 0,3 m. Es una geometría distinta del éxito nulo ideal; no hay recuperación consistente de la función.

La mediana de progreso terminal de EPG→Δ7 fue −1,96% en moderado y −42,68% en fuerte: el dron llegó a terminar más lejos que al comenzar. La de FC2→PFL3 fue 29,29% y −20,37%. Estas cifras describen sólo el comportamiento de la simulación y no implican que las neuronas biológicas respondan así al viento.

El banco guarda cada bloque de 16 episodios con el hash de la configuración para reanudarlo si se interrumpe. Los 96 episodios completos y el informe están en `results/simulation/quadrotor_projection_robustness/`, configurados por `configs/quadrotor_projection_robustness.yaml`.

## Interpretación permitida

Dentro de este modelo provisional y estos 16 casos:

1. Las corrientes Δ7 y FC2 son necesarias: retirar cualquiera elimina la navegación.
2. La identidad de las conexiones importa: cinco reasignaciones por fila eliminan todas las llegadas; cinco nulos que además preservan grados de entrada y salida sólo logran 7/80 y sus éxitos se concentran en dos direcciones.
3. La topología binaria conserva gran parte de la función, pero las multiplicidades de contactos mejoran robustez y eficiencia en los casos extremos probados.
4. El FlyWire intacto iguala la tasa de éxito del proporcional, aunque el proporcional conserva mayor eficiencia mediana.

Esto aporta evidencia de atribución computacional a la arquitectura utilizada. No demuestra que la dinámica real de la mosca funcione exactamente así, ni que FlyWire sea superior a un controlador convencional.

## Límites

- El mapeo glomerular Δ7 sigue siendo provisional.
- No se modela recurrencia Δ7→Δ7, plasticidad ni constantes temporales medidas.
- Los conteos de contactos se usan como pesos relativos; no son eficacias fisiológicas.
- El control por fila no preserva grados de salida; el control estricto sí preserva grados binarios, pero no suma ponderada de salida por neurona.
- Son 16 geometrías deterministas sin ruido, obstáculos ni viento.
- El criterio de llegada no exige orientación final exacta.
- La planta y el airframe continúan siendo genéricos.

## Reproducibilidad

```powershell
.\.venv\Scripts\python.exe -m flydrone.simulation.benchmark_circuit_ablation
.\.venv\Scripts\python.exe -m flydrone.neural.evaluate_circuit_ablation
.\.venv\Scripts\python.exe -m flydrone.simulation.plot_circuit_ablation
```

Configuraciones principales: `configs/quadrotor_circuit_ablation.yaml`, `configs/circuit_ablation_orientation.yaml`, `configs/quadrotor_degree_null.yaml`, `configs/degree_null_orientation.yaml`, `configs/quadrotor_projection_null.yaml` y `configs/quadrotor_projection_robustness.yaml`. Hay 384 episodios 6DoF y 480 diagnósticos de orientación entre los bancos de atribución y robustez. Los informes y sus hashes están registrados en `data/manifest.json`.

## Próximo paso

Añadir un baseline PID de yaw ajustado en casos de desarrollo y evaluarlo sin reajustes en las geometrías y perturbaciones de este banco. Después repetir la comparación con obstáculo y sensores imperfectos.
