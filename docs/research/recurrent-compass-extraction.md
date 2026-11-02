# Extensión recurrente de la brújula

## Decisión

La memoria de orientación no debe asignarse a una única neurona ni implementarse usando solamente la recurrencia Δ7→Δ7. La evidencia experimental describe una representación distribuida de heading en EPG y bucles recurrentes con PEN_a/PEN_b y PEG. PEN_a aporta información relacionada con velocidad angular y Δ7 contribuye con inhibición que estabiliza la representación. La función específica de la recurrencia interna Δ7 sigue siendo incierta.

Fuentes primarias:

- [Kim et al., 2017](https://doi.org/10.1126/science.aal4835): persistencia y dinámica de atractor anular en la representación EPG.
- [Green et al., 2017](https://doi.org/10.1038/nature22343): PEN y actualización de la estimación angular durante giros.
- [Turner-Evans et al., 2020](https://doi.org/10.1016/j.neuron.2020.08.006): reconstrucción, transmisores y perturbaciones funcionales del circuito EPG/Δ7/PEN/PEG.
- [Hulse et al., 2021](https://doi.org/10.7554/eLife.66039): conectividad del central complex y función propuesta de los bucles EB–PB.

## Datos extraídos

Se creó una extracción secundaria de FAFB materialización 783. No reemplaza ni modifica el circuito de steering ya evaluado.

| Tipo | Neuronas |
|---|---:|
| EPG | 47 |
| Δ7 | 40 |
| PEN_a (PEN1) | 20 |
| PEN_b (PEN2) | 22 |
| PEG | 20 |
| **Total** | **149** |

El subgrafo contiene **6.238 pares dirigidos**, **44.492 contactos internos** y 28.719 filas de conexiones de borde. Todas las neuronas forman un único componente fuertemente conectado al conservar pares con al menos un contacto.

Conexiones destacadas por número de contactos:

| Proyección | Contactos |
|---|---:|
| PEN_a→EPG | 5.399 |
| PEN_b→EPG | 4.282 |
| EPG→PEN_b | 3.875 |
| EPG→Δ7 | 3.587 |
| EPG→PEG | 3.394 |
| Δ7→Δ7 | 3.202 |
| EPG→PEN_a | 2.868 |
| Δ7→PEN_b | 2.346 |

Las predicciones de neurotransmisor clasifican las 47 EPG, las 20 PEG y las 20 PEN_a como acetilcolinérgicas. Treinta y nueve de cuarenta Δ7 aparecen como glutamatérgicas. Existen dos excepciones de predicción —una Δ7 acetilcolinérgica y una PEN_b serotoninérgica— que deben auditarse antes de asignar signos célula por célula. Una predicción de transmisor no determina por sí sola la ganancia ni el efecto postsináptico.

## Auditoría de fase derivada de contactos

Para cada PEN/PEG se calculó una fase circular de entrada desde EPG y otra de salida hacia EPG, ponderadas exclusivamente por conteos de contactos. Las fases EPG heredan el mapa anatómico provisional PB usado por el controlador actual. No se ajustó el resultado contra steering ni contra desempeño del dron.

El cálculo inicial que agregaba neuropilos produjo desplazamientos medianos de aproximadamente +5–7° a la izquierda y −4° a la derecha en PEN. La auditoría posterior dentro de EB produjo medianas entre −0,60° y +1,34°, pero esa comparación también era incompleta: mezclaba el compartimento de salida con el de entrada. La revisión actual cruza entradas PB con salidas EB y recupera desplazamientos laterales opuestos de aproximadamente 49–55°; véase `cross-compartment-pen-model.md`.

Las concentraciones circulares medianas de entrada y salida de PEN dentro de EB se encuentran aproximadamente entre 0,89 y 0,96, indicando contactos agrupados en fase. Esto permite asignar una fase central anatómica, pero no revela por sí solo el desplazamiento dinámico publicado. PEG tiene menos contactos de salida hacia EPG y continúa sin una correspondencia columnar validada.

## Separación por neuropilo

La tabla publicada permite distinguir claramente tres zonas:

- PB contiene 98,6 % de Δ7→Δ7, 99,2 % de Δ7→EPG, 98,7 % de Δ7→PEN_a y 99,6 % de Δ7→PEN_b.
- EB contiene 90,7 % de EPG→PEN_a, 87,4 % de EPG→PEN_b, 98,1 % de PEN_a→EPG y 96,9 % de PEN_b→EPG.
- NO contiene 81,4 % de PEN_a→PEN_a y 90,0 % de PEN_b→PEN_b.

Esto respalda tratar la inhibición Δ7 en PB, los bucles locales EPG↔PEN en EB y buena parte de la recurrencia PEN en NO como compartimentos separados. No establece todavía dónde entra la velocidad angular ni qué contactos son causalmente necesarios.

También se extrajeron desde el archivo local publicado las coordenadas pre y postsinápticas de las **44.492 sinapsis**. La suma se verificó exactamente contra 6.911 combinaciones par–neuropilo de la extracción agregada. Una sinapsis sin etiqueta de neuropilo en la tabla de coordenadas se normalizó a `UNASGD`, la etiqueta equivalente de la tabla agregada; no pertenece a PB, EB ni NO.

## Información que falta

- Segmentar posiciones dentro de PB, EB y NO en glomérulos, wedges/tiles y regiones de NO; el neuropilo grueso ya está separado.
- Auditar las dos predicciones de neurotransmisor atípicas.
- Determinar qué señal del simulador representa la entrada de velocidad angular a PEN.
- Elegir constantes temporales, ganancias y no linealidades. El connectoma no las proporciona.
- Validar persistencia, unicidad del bump, deriva en oscuridad y actualización durante giros antes de usar esta red para controlar el dron.
- Añadir aferencias visuales si se quiere estudiar corrección por landmarks, sin confundirlas con la integración de movimiento propio.

## Archivos reproducibles

- Configuración: `configs/compass_recurrent_data.yaml`.
- Extracción: `data/processed/fafb783_recurrent_compass/`.
- Auditoría de fase: `configs/recurrent_compass_map.yaml` y `results/neural/recurrent_compass_map/`.
- Auditoría por neuropilo: `configs/recurrent_compartment_audit.yaml` y `results/neural/recurrent_compartment_audit/`.
- Coordenadas verificadas: `data/processed/fafb783_recurrent_compass/synapses.parquet`.
- Código: `src/flydrone/neural/recurrent_compass_map.py`.

## Próximo paso concreto

Inferir y auditar subcompartimentos dentro de PB, EB y NO usando las coordenadas verificadas, sin ajustar contra steering. Sólo después se construirá un modelo temporal mínimo. Su primera prueba será mantener y actualizar un bump de heading durante una interrupción sensorial; el dron permanecerá desconectado de ese candidato hasta que pase la prueba aislada.
