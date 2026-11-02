# Auditoría morfológica y mapeo funcional provisional

Fecha de corte: 2026-09-13. Dataset anatómico: FlyWire FAFB, materialization 783. Este documento separa datos observados, resultados derivados y supuestos pendientes. El modelo feedforward ponderado construido después se documenta en [connectome-model-results.md](connectome-model-results.md). No describe todavía un controlador de dron.

## Decisión

El circuito de trabajo queda refinado a **EPG → Δ7 → PFL3**, con **FC2B/FC2C → PFL3** como entrada de objetivo. FC2A se conserva como condición comparativa, pero no formará parte del modelo funcional primario en esta etapa.

La razón es experimental. Mussells Pires et al. midieron en FC2 una señal relacionada con el ángulo objetivo y mostraron que la activación focal cambia la dirección mantenida por la mosca. La caracterización anatómica de la línea usada es compatible con los subtipos **FC2B o FC2C**; el experimento no distingue cuál de ellos genera el efecto y no ofrece apoyo directo para incluir FC2A en la condición principal. Escribir “FC2” sin esa salvedad ocultaría una incertidumbre real [Mussells Pires et al., 2024](https://doi.org/10.1038/s41586-023-07006-3).

## Evidencia funcional que sí podemos usar

- EPG representa orientación angular mediante una actividad localizada cuya fase sigue el heading.
- FC2 mostró una actividad localizada estable relacionada con el objetivo durante menotaxis. La evidencia disponible corresponde a una línea con morfología FC2B/FC2C, no a una separación causal entre ambos subtipos.
- PFL3 recibe información de heading en el protocerebral bridge e información de objetivo en el fan shaped body. Su actividad depende conjuntamente de ambas variables.
- La diferencia poblacional entre terminales PFL3 derecha e izquierda en los lateral accessory lobes se relaciona con steering. La manipulación optogenética de PFL3 y el bloqueo de subconjuntos PFL3 aportan evidencia causal.
- El modelo publicado usa 24 PFL3: 12 que proyectan a cada LAL. Emplea 12 columnas funcionales, aunque los autores también evaluaron una interpretación de 9 columnas y obtuvieron resultados cualitativamente similares.

Estas afirmaciones y los parámetros del modelo de referencia proceden de [Mussells Pires et al., 2024](https://doi.org/10.1038/s41586-023-07006-3). La descripción anatómica más amplia de columnas FC y del circuito del central complex procede de [Hulse et al., 2021](https://doi.org/10.7554/eLife.66039).

## Datos observados en FlyWire 783

La extracción contiene 195 neuronas: 47 EPG, 40 Δ7, 16 FC2A, 28 FC2B, 40 FC2C y 24 PFL3. Entre neuronas seleccionadas, las entradas a PFL3 suman:

| Clase presináptica | Contactos hacia PFL3 |
|---|---:|
| Δ7 | 2,326 |
| FC2A | 838 |
| FC2C | 801 |
| FC2B | 785 |
| EPG | 671 |
| PFL3 | 387 |

La suma FC2B+FC2C es 1,586 contactos. Los valores son contactos anatómicos del archivo `proofread_connections_783.feather`; no son eficacias fisiológicas ni pesos funcionales.

Los 195 esqueletos 3D oficiales contienen 658,296 vértices y 658,101 aristas. Se midieron contra los volúmenes PB y FB del atlas fijado en el manifiesto. El resultado está en `morphology-features.csv` y su método en `morphology-report.json`.

## Mapeo PFL3

Los contactos agregados muestran 12 PFL3 con salida en LAL_L y 12 en LAL_R. En la convención del atlas, LAL_L ocupa coordenadas x menores que LAL_R. Al ordenar por la mediana x de los vértices dentro de FB por separado en ambas poblaciones, se obtienen 12 posiciones y exactamente un PFL3 de cada lado por posición.

`functional-mapping.csv` asocia provisionalmente esos pares con las 12 columnas y con los ángulos preferidos publicados. Este enlace es una **inferencia geométrica comprobable**, no una anotación funcional aportada por FlyWire. Los ángulos proceden del modelo publicado; la pertenencia de cada `root_id` FAFB a una columna se deriva aquí.

## Lo que permanece sin resolver

1. **Coordenadas de sinapsis.** La tabla local de conexiones está agregada por par y neuropilo. La tabla pública completa `flywire_synapses_783.feather` contiene posiciones, pero ocupa 9,492,998,242 bytes. La consulta selectiva mediante CAVE materialization 783 fue probada y rechazó el acceso por falta de token. No se guardó ninguna credencial.
2. **Etiquetas expertas por glomérulo/columna en FAFB.** Las etiquetas de tipo no asignan cada root ID a un glomérulo funcional. Las columnas geométricas son hipótesis derivadas de esqueletos.
3. **Signo sináptico efectivo.** Las predicciones de neurotransmisor no determinan por sí solas el signo sobre cada receptor. Δ7 es descrita como glutamatérgica y funcionalmente inversora sobre muchos blancos, pero no se aplicará un signo universal sin justificarlo por blanco.
4. **Ganancia y constantes temporales.** El connectoma no las contiene. Se usarán primero los parámetros explícitos del modelo PFL3 publicado, separados de cualquier parámetro de conveniencia.
5. **FC2B frente a FC2C.** La fisiología disponible no desambigua cuál de los dos subtipos porta la señal de objetivo. Deben evaluarse juntos, por separado y mediante ablación.
6. **Dos segmentos FC2C marcados como outlier.** `720575940622374783` y el aislado `720575940629923883` no deben entrar silenciosamente en conclusiones funcionales; se excluirán o evaluarán como sensibilidad documentada.

## Decisión sobre preparación del modelo

Se implementó un **modelo de referencia PFL3 de tasas** que reproduce la transformación heading–objetivo publicada y emite la diferencia R−L. Esto verificó el mapeo y el readout antes de usar los pesos FlyWire.

El experimento feedforward posterior incorporó la matriz anatómica Δ7/FC2→PFL3, declaró su normalización, probó los subtipos por separado y comparó contra 100 barajados. El resultado es compatible con la función publicada, pero todavía no representa todas las conexiones ni la dinámica de las 195 neuronas.

## Próximo paso concreto

La incorporación explícita EPG→Δ7 fue intentada y rechazada por la auditoría descrita en [epg-delta7-audit.md](epg-delta7-audit.md). El próximo paso es extraer coordenadas sinápticas PB para corregir y validar de forma independiente los mapas EPG, Δ7 y PFL3. Luego se añadirán recurrencia respaldada, ruido, retrasos y dinámica temporal antes de convertir R−L en velocidad de giro. La salida aún no está conectada a un dron.
