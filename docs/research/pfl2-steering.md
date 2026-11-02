# Extensión PFL2 para steering adaptativo

## Pregunta y alcance

Esta etapa prueba una predicción concreta: una población PFL2 reconstruida con conectividad FAFB 783 puede aportar una señal de **magnitud de corrección** mientras PFL3 conserva la elección izquierda/derecha. La meta sigue siendo suministrada por el simulador. El estabilizador de actitud, altura y motores continúa siendo convencional.

El resultado es una implementación **FlyWire-grounded de desarrollo**. La identidad de las neuronas y los contactos son reales; la función de activación, la normalización y la ganancia que convierten actividad en escala de yaw son decisiones de ingeniería. No representan tasas de disparo medidas en esas 12 neuronas.

## Reconstrucción anatómica

Se amplió la extracción FAFB/FlyWire materialización 783 a 207 neuronas:

- 47 EPG;
- 40 Δ7;
- 16 FC2A, 28 FC2B y 40 FC2C;
- 12 PFL2, seis por lado;
- 24 PFL3.

El subgrafo contiene 5.056 pares dirigidos y 21.765 sinapsis entre las clases seleccionadas. Para PFL2 se recuperaron:

- 1.332 contactos Δ7→PFL2;
- 1.177 contactos FC2B/FC2C→PFL2 usados por el modelo;
- además, 395 FC2A→PFL2 y 528 EPG→PFL2, conservados en la extracción pero no usados en esta primera dinámica.

Cada PFL2 recibe contactos de las dos corrientes usadas. Las fases presinápticas se heredan del mapeo existente y se promedian circularmente con peso por número de contactos. La separación absoluta mediana entre las corrientes Δ7 y FC2 por PFL2 es 154,75°. Los resultantes mínimos son 0,781 para Δ7 y 0,822 para FC2. Esta observación anatómica es compatible con una comparación de rumbo y meta, pero por sí sola no demuestra la función fisiológica.

Los 207 esqueletos fueron descargados y verificados sin muestreo: 712.306 vértices y 712.099 aristas. PFL2 puede filtrarse y verse con su actividad en la aplicación nativa.

## Modelo computacional

Las matrices de entrada se forman directamente con conteos de contactos y se normalizan por fila. El modelo aplica a cada PFL2 una suma rectificada de las corrientes Δ7 y FC2B/C. La actividad poblacional se calibra entre un caso alineado y otro antialineado para obtener un índice adimensional de alejamiento de la meta.

Estas operaciones son abstracciones explícitas:

- rectificación de media onda;
- suma con igual escala de ambas corrientes;
- normalización por el máximo teórico;
- calibración poblacional alineado/antialineado;
- ganancia de steering fija de 0,5.

PFL3 determina el signo del comando. PFL2 sólo multiplica su magnitud por una escala entre 1,0 y 1,5; por construcción no puede invertir la dirección indicada por PFL3. No se realizó búsqueda de la ganancia sobre los casos de evaluación.

## Gate aislado

El modelo pasó el gate interno de desarrollo:

| Medida | Resultado |
|---|---:|
| Actividad mediana, heading y meta alineados | 0,0553 |
| Actividad mediana, antialineados | 0,2919 |
| Monotonicidad mínima de las dos ramas | 0,9945 |
| Gate aislado | aprobado |

En el banco de heading de 64 episodios, ambos modos llegaron en 32/32 casos. PFL2 no cambió el sentido inicial elegido por PFL3 en ningún caso. El tiempo mediano de asentamiento global bajó de 2,85 s a 2,40 s; para errores grandes bajó de 4,325 s a 3,600 s. La precisión de dirección fue 90,625% en ambos modos: los tres errores heredados pertenecen al modelo PFL3 cerca de la antimeta y PFL2 no los corrige ni los empeora.

## Ablación pareada en el dron 6DoF

Se ejecutaron 32 episodios deterministas, 16 con PFL3+PFL2 y los mismos 16 con PFL3 sola. Se usaron cuatro direcciones de meta y errores iniciales de ±150° y ±175°. La observación de heading fue ideal para aislar steering; el lazo interno convencional permaneció activo.

| Condición | Llegadas | Tiempo mediano | Eficiencia mediana | Distancia final mediana | Inclinación máxima | Saturación máxima |
|---|---:|---:|---:|---:|---:|---:|
| PFL3 sola | 16/16 | 10,528 s | 0,9770 | 0,2135 m | 5,19° | 0,0 |
| PFL3 + PFL2 | 16/16 | 9,709 s | 0,9883 | 0,2136 m | 5,48° | 0,0 |

La mejora mediana de llegada fue 0,819 s y el gate de desarrollo fue aprobado. Esto respalda que la señal PFL2 implementada puede acelerar correcciones grandes dentro del modelo actual. No demuestra todavía una ventaja general, significancia estadística, robustez a sensores imperfectos ni equivalencia con PFL2 biológica.

## Evidencia científica y límites

La interpretación funcional se apoya principalmente en Westeinde et al. (2024), que relaciona PFL2 con estados alejados de la meta y cambios en rotación/avance mediante imagen, electrofisiología y perturbaciones. Hulse et al. (2021) aporta la organización connectómica del central complex. La transferencia de esa función a la escala de yaw del dron es una hipótesis del proyecto.

Fuentes:

- Westeinde et al., 2024, *Transforming a head direction signal into a goal-oriented steering command*, Nature 626, 819–826: https://www.nature.com/articles/s41586-024-07039-2
- Hulse et al., 2021, *A connectome of the Drosophila central complex reveals network motifs suitable for flexible navigation and context-dependent action selection*, eLife: https://pmc.ncbi.nlm.nih.gov/articles/PMC9477501/

Persisten cuatro límites principales:

1. La activación PFL2 no es un modelo biofísico ni una tasa de disparo medida.
2. El uso de FC2B/C y la exclusión dinámica de FC2A deben validarse mejor.
3. El ensayo 6DoF es de desarrollo, determinista y pequeño.
4. PFL3 mantiene tres errores de dirección cerca de 180° en el banco aislado.

## Evaluación prospectiva congelada

Después de congelar configuración, código y seis criterios en `PREREGISTRO.md`, se ejecutó una sola corrida con 36 pares nuevos por condición. Combinó tres direcciones de meta, cuatro errores iniciales de ±153° y ±172°, y tres escenarios inéditos de ruido, retraso y viento.

PFL3+PFL2 y PFL3 sola alcanzaron 36/36 metas. PFL2 mejoró el tiempo en 35 de 36 pares; el único caso contrario fue de 0,002 s. La mejora mediana fue 0,386 s y su intervalo bootstrap exploratorio del 95% fue [0,296, 0,468] s. La eficiencia mediana pareada aumentó 0,00752. No cambió ningún signo inicial y no produjo saturación. Los seis criterios preregistrados se cumplieron.

| Escenario | Mejora mediana de llegada |
|---|---:|
| Ruido/retraso/viento moderado nuevo | 0,411 s |
| Combinación fuerte nueva | 0,420 s |
| Retraso con ráfaga tardía | 0,091 s |

Este resultado confirma de forma prospectiva que la modulación congelada aporta una mejora pequeña y consistente dentro del simulador actual.

## Controles de atribución posteriores

Se permutaron independientemente las columnas de fase Δ7 y FC2 en 30 controles. Cada nulo conservó exactamente los valores, totales por fila y distribución de contactos, pero rompió la identidad de fase presináptica. La correlación del índice FlyWire con una magnitud angular de referencia fue 0,981; el mejor nulo alcanzó 0,728 y ninguno igualó FlyWire (p empírico ≤ 0,032). El error absoluto medio fue 0,071 para FlyWire y al menos 0,195 para los nulos.

También se reemplazó el índice connectómico por la fórmula convencional `(1−cos(error))/2`, conservando casos, ganancia y límites. Este control obtuvo 36/36 llegadas y quedó sólo 0,003 s detrás de PFL2 en la mediana pareada; la diferencia de eficiencia fue −0,00071. En términos prácticos, ambos controladores fueron casi equivalentes.

Por tanto, los datos apoyan dos afirmaciones acotadas:

1. La correspondencia de fases de la conectividad PFL2 reconstruida contiene una señal organizada de alejamiento de la meta y supera nulos anatómicos razonables.
2. La mejora de navegación producida por esa señal no es exclusiva del connectoma; una función angular diseñada con acceso directo al error reproduce casi todo el efecto.

No se ha demostrado que FlyDrone sea superior a un controlador convencional. Su valor actual está en obtener desde una arquitectura biológica reconstruida una señal funcional interpretable y causalmente sensible a la organización de fases.

## Próximo paso concreto

Conservar PFL2 congelada y comenzar la Fase 6: extraer PFNd, PFNv y hΔB para representar dirección real de desplazamiento y deriva. PFL2 deberá repetirse más adelante con múltiples distancias y obstáculos, pero no requiere reajuste inmediato. La prioridad científica pasa a comprobar si una ruta PFN→hΔB basada en FlyWire mejora la compensación de viento lateral respecto de usar sólo el heading corporal.

## Artefactos reproducibles

- Extracción: `configs/data_pfl2_steering.yaml`.
- Modelo: `configs/pfl2_model.yaml` y `src/flydrone/neural/connectome_pfl2.py`.
- Interfaz de steering: `configs/pfl2_steering.yaml` y `src/flydrone/neural/pfl2_steering.py`.
- Gate aislado: `results/neural/pfl2_goal_misalignment/report.json`.
- Banco de heading: `results/neural/pfl2_steering_development/report.json`.
- Ablación 6DoF: `results/simulation/quadrotor_pfl2_steering_development/report.json`.
- Evaluación prospectiva: `results/simulation/quadrotor_pfl2_steering_prospective/report.json`.
- Nulos de fase: `results/neural/pfl2_connectivity_nulls/report.json`.
- Control analítico: `results/simulation/quadrotor_pfl2_analytic_control/report.json`.
- Figura resumen: `results/neural/pfl2-validation-summary.png`.
- Morfologías: `data/processed/fafb783_epg_delta7_fc2_pfl2_pfl3/morphology-index.json`.
