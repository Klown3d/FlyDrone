# Ablación de la política de llegada

Plan fijado antes de ejecutar el banco. Fecha: 2026-09-19.

## Pregunta

¿Qué componente de ingeniería de la política candidata —filtro de posición, radio de entrada estricto, confirmación temporal o recuperación— explica su comportamiento? Esta prueba no evalúa propiedades neuronales ni modifica EPG, Δ7, FC2 o PFL3.

## Diseño

Se usan 64 geometrías nuevas, semilla de casos 798 y cuatro escenarios: ideal, ruido leve, ruido+sesgo de 20 cm y desplazamiento físico de 60 cm inmediatamente después de la primera llegada. Ambos controladores reciben las mismas observaciones y perturbaciones. El estado real se usa para dinámica y puntuación, no para decidir llegada.

La política completa se compara con cuatro ablaciones, cambiando un solo elemento:

| Variante | Único cambio |
|---|---|
| Completa | Filtro τ=0,3 s; entrada 12 cm; confirmación 0,4 s; recuperación activa |
| Sin filtro | La observación actual sustituye directamente la posición filtrada |
| Entrada amplia | Radio de entrada 21 cm en lugar de 12 cm |
| Sin confirmación | Una observación válida puede confirmar llegada inmediatamente |
| Sin recuperación | La llegada queda enclavada después de una perturbación |

Cada variante comprende 512 episodios: 64 casos × cuatro escenarios × dos controladores. Total previsto: 2.560 episodios. El criterio físico de éxito se mantiene: radio real 30 cm, velocidad ≤8 cm/s, altura dentro de ±10 cm y permanencia terminal de dos segundos.

## Interpretación prevista

- Un descenso únicamente al retirar un componente identifica su contribución dentro de este conjunto.
- Resultados iguales no demuestran que el componente sea inútil fuera de las perturbaciones probadas.
- El escenario de desplazamiento es el contraste principal para recuperación.
- Diferencias compartidas por ambos controladores pertenecen principalmente a la política convencional de llegada.
- No se ajustarán parámetros después de observar este banco; cualquier prueba posterior usará nuevas semillas.

## Resultados

Se completaron los 2.560 episodios previstos. Cada celda muestra éxitos neuronal/proporcional sobre 64 casos.

| Variante | Ideal | Ruido leve | Sesgo + ruido | Desplazamiento después de llegar |
|---|---:|---:|---:|---:|
| Completa | 64/64 | 64/64 | 64/64 | 64/64 |
| Sin filtro | 64/64 | 64/64 | **0/0** | 64/64 |
| Entrada amplia | 64/64 | 64/64 | **63/64** | 64/64 |
| Sin confirmación | 64/64 | 64/64 | 64/64 | 64/64 |
| Sin recuperación | 64/64 | 64/64 | 64/64 | **0/0** |

En la fila sin filtro, los 128 fallos con sesgo+ruido fueron `no_valid_terminal_hold`: la mediana de distancia final quedó dentro del radio físico (22,84 cm neuronal; 22,58 cm proporcional), pero la observación ruidosa no sostuvo una llegada válida durante los dos segundos terminales. El filtro es, por tanto, decisivo para estabilidad del criterio bajo la perturbación fuerte probada.

La entrada amplia produjo un solo fallo neuronal: caso 43, detenido a 30,0038 cm, apenas fuera del radio físico de 30 cm. El radio estricto aporta una protección pequeña pero medible en este conjunto.

Retirar la confirmación temporal no redujo la tasa de éxito. Sí dejó medianas finales algo mayores en ideal (7,21/7,10 cm frente a 5,41/5,27 cm de la política completa), porque la política sin espera enclava llegada antes. No se demuestra que 0,4 s sea necesario para éxito en estos escenarios; puede conservarse como protección ante observaciones transitorias hasta una prueba específica más adversa.

Sin recuperación, los 128 ensayos desplazados quedaron detenidos fuera de la meta, con medianas de 62,56 cm neuronal y 61,96 cm proporcional. La recuperación es causalmente necesaria para la perturbación posterior a llegada que se diseñó para probarla.

Los efectos principales aparecen en ambos controladores. Se atribuyen a la interfaz sensorial y a la política convencional de llegada, no a una ventaja de la arquitectura FlyWire. Sólo se usó una semilla sensorial por escenario y 64 geometrías; los porcentajes no deben extrapolarse a perturbaciones no probadas.

Productos: `results/simulation/arrival_ablation_*`, con episodios, trazas, fallos e informes reproducibles; resumen conjunto en `results/simulation/arrival_ablation_summary.csv`.

## Decisión

Conservar filtro τ=0,3 s, radio de entrada 12 cm y recuperación. La confirmación de 0,4 s se conserva provisionalmente por seguridad frente a falsos positivos breves, pero no se le atribuye mejora de tasa de éxito en este banco. La siguiente etapa puede comenzar la planta de quadrotor con seis grados de libertad manteniendo esta interfaz congelada.
