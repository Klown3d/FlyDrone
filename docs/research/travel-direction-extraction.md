# Fase 6 — Extracción PFNd/PFNv→hΔB

## Pregunta funcional

La brújula EPG/Δ7 representa hacia dónde está orientado el animal, pero un dron puede desplazarse en otra dirección por viento o inercia. La Fase 6 busca reconstruir una señal separada de **dirección allocéntrica de desplazamiento** para medir esa diferencia antes de intentar compensarla.

Lu et al. (2022) identificaron PFNd y PFNv como poblaciones que combinan heading y velocidad traslacional egocéntrica. Ambas convergen en hΔB mediante una organización compatible con transformar movimiento corporal a coordenadas del mundo. El estudio midió la actividad funcional y mostró que el bump hΔB cambia con la dirección de traslación. Esto respalda la selección del circuito, pero no proporciona automáticamente los parámetros dinámicos de nuestro modelo ni demuestra su función en vuelo.

Fuente primaria: Lu et al., 2022, *Transforming representations of movement from body- to world-centric space*, Nature 601, 98–104: https://www.nature.com/articles/s41586-021-04191-x

Fuente connectómica complementaria: Hulse et al., 2021, *A connectome of the Drosophila central complex reveals network motifs suitable for flexible navigation and context-dependent action selection*: https://pmc.ncbi.nlm.nih.gov/articles/PMC9477501/

## Extracción FAFB 783

La extracción secundaria usa la misma materialización y anotación fijadas para FlyDrone. No reemplaza el circuito principal ni mezcla versiones.

| Clase | Neuronas | Predicción de neurotransmisor en FAFB 783 |
|---|---:|---|
| EPG | 47 | 47 acetilcolina |
| Δ7 | 40 | 39 glutamato, 1 acetilcolina |
| IbSpsP | 30 | 30 acetilcolina |
| LNO1 | 4 | 3 GABA, 1 acetilcolina |
| LNO2 | 2 | 1 glutamato, 1 GABA |
| PFNd | 40 | 40 acetilcolina |
| PFNv | 21 | 21 acetilcolina |
| hΔB | 18 | 18 acetilcolina |

En total son 202 neuronas, 6.196 pares dirigidos, 53.999 sinapsis internas y 36.403 filas de frontera. Las etiquetas de neurotransmisor son predicciones por neurona; la inconsistencia dentro de LNO1/LNO2 impide asignar un único signo funcional sin evidencia adicional.

## Rutas relevantes recuperadas

| Proyección | Pares dirigidos | Sinapsis | Cobertura postsináptica |
|---|---:|---:|---:|
| Δ7→PFNd | 262 | 1.506 | 40/40 |
| Δ7→PFNv | 139 | 606 | 21/21 |
| EPG→PFNd | 130 | 907 | 38/40 |
| EPG→PFNv | 67 | 283 | 20/21 |
| LNO1→PFNd | 76 | 1.219 | 40/40 |
| LNO1→PFNv | 42 | 2.593 | 21/21 |
| LNO2→PFNd | 40 | 3.985 | 40/40 |
| LNO2→PFNv | 13 | 16 | 13/21 |
| IbSpsP→PFNd | 139 | 826 | 40/40 |
| IbSpsP→PFNv | 68 | 307 | 21/21 |
| PFNd→hΔB | 390 | 15.487 | 18/18 |
| PFNv→hΔB | 115 | 2.720 | 18/18 |

La convergencia PFN→hΔB publicada está claramente presente: todas las PFNd y PFNv seleccionadas contribuyen, y las 18 hΔB reciben ambas corrientes. La asimetría de contactos entre PFNd y PFNv es un dato anatómico; todavía no debe interpretarse como una ganancia funcional porque conteo sináptico y eficacia fisiológica no son equivalentes.

## Datos disponibles

- Identidades, lados y anotaciones FAFB 783.
- Conteos sinápticos dirigidos entre todas las clases seleccionadas.
- Predicción de neurotransmisor por neurona.
- Conexiones de frontera para buscar entradas omitidas.
- 53.999 coordenadas sinápticas internas extraídas y verificadas exactamente contra los conteos: 19.822 en FB, 16.529 en NO y 14.672 en PB, además de 2.621 en EB y contactos menores en otros neuropilos.

## Información faltante

1. Asignación célula por célula a glomérulos PB y columnas/layers FB.
2. Fase funcional de cada PFNd, PFNv y hΔB.
3. Separación de compartimentos presinápticos y postsinápticos en cada proyección.
4. Signo efectivo y fuerza fisiológica de LNO1/LNO2/IbSpsP sobre PFN.
5. Transferencia cuantitativa entre velocidad frontal/lateral del dron y actividad de las entradas egocéntricas.
6. Constantes temporales, no linealidades, ruido y saturación neuronal.
7. Regla de readout que convierta el bump hΔB en una dirección sin usar directamente la respuesta correcta del simulador.

## Mapa de columnas recuperado

Siguiendo el procedimiento publicado, PFNd y PFNv se agruparon en ocho columnas verticales por la mediana x de sus contactos de salida en FB. Los axones hΔB se agruparon en doce columnas usando posiciones presinápticas; sus dendritas se localizaron con contactos PFNv, porque la literatura indica que PFNv termina en la región dendrítica mientras PFNd contacta ambas regiones.

El mapa recuperó el desplazamiento de medio FB esperado: la mediana dendrita−axón fue seis de doce columnas. Diecisiete de las 18 hΔB quedaron a ±1 columna de ese desplazamiento y las 18 quedaron a ±2. FAFB contiene 18 hΔB con esta etiqueta frente a 19 en el hemibrain publicado; la célula faltante o diferencia de anotación permanece como incertidumbre.

Estas columnas son hipótesis geométricas derivadas de coordenadas, no anotaciones FlyWire directas. Se conservan en `travel-direction-columns.csv` con su procedencia.

## Arquitectura candidata implementada en aislamiento

```text
heading EPG/Δ7 ───────┐
                     ├─ PFNd/PFNv ──contactos FAFB──> hΔB ──> dirección de desplazamiento
velocidad corporal ── LNO1/LNO2/IbSpsP
```

El primer modelo usa modulaciones cosenoidales respecto de una línea base no modelada. Las fases PFN se heredan de contactos Δ7; las amplitudes son proyecciones positivas de la velocidad egocéntrica sobre los cuatro ejes publicados de 44,5°, −41,5°, −131,5° y 136,5°. Las 61 PFN se proyectan a las 18 hΔB con conteos FAFB sin normalizar, y la salida se decodifica sobre las doce columnas axonales. Una rotación global se fija con heading cero y movimiento frontal.

La actividad firmada significa desviación respecto de una línea base, no tasas negativas de disparo. La codificación de velocidad, la línea base omitida y el anclaje global son abstracciones computacionales. El modelo fue elegido después de comparar variantes de activación y normalización, por lo que su resultado es desarrollo y no prospectivo.

## Gate aislado propuesto

- Probar movimiento frontal, lateral y hacia atrás bajo al menos ocho headings.
- Medir error circular entre dirección de desplazamiento simulada y fase hΔB.
- Exigir equivariancia: rotar heading y movimiento juntos debe rotar la salida en el mismo ángulo.
- Comparar contra fases PFN barajadas y matrices con contactos uniformados.
- Tratar como refutación una salida que simplemente copie heading o velocidad egocéntrica.

## Resultado del gate de desarrollo

Sobre 128 combinaciones de headings y movimientos egocéntricos no usadas para el anclaje:

| Métrica | Resultado |
|---|---:|
| Error absoluto mediano | 6,32° |
| Error absoluto máximo | 23,27° |
| Casos dentro de 45° | 128/128 |
| Resultante mínima | 0,425 |

El candidato aprobó 4/4 criterios de desarrollo. La salida rota con heading, cambia con el movimiento egocéntrico y conserva su fase cuando sólo cambia la velocidad.

### Atribución computacional

| Condición | Error mediano | Error máximo | Dentro de 45° |
|---|---:|---:|---:|
| Intacto | 6,32° | 23,27° | 100% |
| Sin PFNd | 35,24° | 168,75° | 54,7% |
| Sin PFNv | 41,16° | 177,34° | 51,6% |
| Fase de heading colapsada | 89,91° | 179,37° | 25,0% |

Treinta permutaciones de fase dentro de cada población y lado conservaron neuronas, pesos y grupos, pero rompieron la correspondencia heading→contacto. Ninguna igualó al intacto: el mejor nulo obtuvo 20,64°, la mediana nula fue 77,22° y p empírico ≤ 0,032. Son ablaciones computacionales, no intervenciones biológicas.

## Atajo de fase rechazado

Se probó un diagnóstico barato antes de construir dinámica. La fase PFN obtenida como media circular de contactos Δ7 fue concentrada para la mayoría de las células (resultante mediana 0,959 en PFNd y 0,933 en PFNv). Sin embargo, colapsar después todas las entradas PFNd de cada hΔB a otra media circular produjo una resultante mediana de sólo 0,200. Esto no significa que la ruta carezca de señal: concuerda con una convergencia de múltiples componentes vectoriales. Sí demuestra que asignar una única fase hΔB por promedio global borraría la estructura. Ese atajo queda rechazado y registrado en `travel-direction-phase-diagnostic.json`.

## Próximo paso concreto

El candidato se congeló antes de una corrida única de 720 casos con headings, direcciones egocéntricas y magnitudes no usadas, más ruido sensorial moderado y fuerte. Aprobó los seis criterios: en ideal obtuvo 6,09° de error mediano y 22,73° máximo; en el conjunto completo, 8,38° de mediana, 21,30° de percentil 90 y 99,58% dentro de 45°. La resultante mínima fue 0,412. El informe inmutable está en `results/neural/travel_direction_prospective/report.json`.

La Fase 6 quedó posteriormente **integrada y aprobada prospectivamente en 6DoF**. El gate de deriva obtuvo 30/30 llegadas y redujo 75,0% el desvío frente a ausencia. Una prueba sensorial posterior reemplazó la velocidad verdadera por diferencias de posición observada: logró 28/30 llegadas, 66,9% menos desvío y 14/15 éxitos durante una pérdida de 3,5 s. Véanse [integración de deriva](travel-direction-drift-integration.md) e [interfaz de velocidad](travel-velocity-sensor.md).

## Artefactos

- Configuración: `configs/data_travel_direction.yaml`.
- Grafo: `data/processed/fafb783_travel_direction/`.
- Auditoría reproducible: `src/flydrone/neural/travel_direction_audit.py`.
- Informe: `data/processed/fafb783_travel_direction/travel-direction-audit.json`.
- Coordenadas: `data/processed/fafb783_travel_direction/synapses.csv.gz` y su informe `.report.json`.
- Columnas: `data/processed/fafb783_travel_direction/travel-direction-columns.csv`.
- Modelo: `configs/travel_direction_model.yaml` y `src/flydrone/neural/travel_direction_model.py`.
- Gate: `results/neural/travel_direction_development/report.json`.
- Ablaciones: `results/neural/travel_direction_ablation/report.json`.
- Gate prospectivo: `configs/travel_direction_prospective.yaml` y `results/neural/travel_direction_prospective/report.json`.
