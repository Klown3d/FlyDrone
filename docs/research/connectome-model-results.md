# Primer modelo PFL3 ponderado por FlyWire

Fecha: 2026-09-13. Estado: experimento neuronal feedforward terminado. No incluye dinámica temporal, recurrencia completa, sensores ni dron.

## Pregunta

¿Los contactos reales Δ7/FC2→PFL3 de FlyWire 783 conservan la transformación heading–objetivo cuando sustituyen las entradas ideales del modelo PFL3 publicado?

## Construcción

- **Unidades de salida:** los 24 PFL3 FAFB ya mapeados provisionalmente a 12 columnas y dos LAL.
- **Heading:** 40 Δ7 con 2,326 contactos reales hacia PFL3.
- **Objetivo primario:** 28 FC2B y 38 FC2C utilizables, con 1,586 contactos reales hacia PFL3. Se excluyeron los dos FC2C marcados como `outlier_seg`.
- **Pesos:** conteo de contactos FlyWire, normalizado por separado dentro de cada corriente de entrada de cada PFL3.
- **No linealidad:** la softplus y los parámetros ajustados por [Mussells Pires et al. (2024)](https://doi.org/10.1038/s41586-023-07006-3).
- **Readout:** suma PFL3 que proyecta a LAL derecho menos suma hacia LAL izquierdo.

La normalización por fila es una decisión computacional. No representa una ganancia sináptica medida.

## Resultados

Se evaluaron 12 objetivos distribuidos cada 30° y 361 orientaciones relativas por objetivo.

| Condición | Error medio del equilibrio | Máximo | Dirección correcta | Correlación con referencia |
|---|---:|---:|---:|---:|
| FC2B+FC2C | 6.94° | 13.87° | 99.07% | 0.985 |
| FC2B solo | 3.85° | 7.90° | 99.65% | 0.987 |
| FC2C solo | 12.00° | 20.60° | 97.24% | 0.972 |
| FC2A, comparación | 37.29° | 48.01° | 83.84% | 0.821 |
| Δ7 eliminado | sin equilibrio detectable | — | 50.00% | ≈0 |
| FC2 eliminado | 90.00° | 165.15° | 49.90% | ≈0 |

En 100 controles con los pesos barajados dentro de cada fila, conservando el número de entradas, los ceros y el multiconjunto de pesos de cada PFL3, el error medio fue **88.38°** y la dirección correcta **50.18%**. Es decir, el resultado principal desaparece cuando se rompe qué neurona presináptica aporta cada peso.

## Interpretación permitida

La topografía de los contactos FlyWire Δ7/FC2→PFL3 es compatible con una transformación útil de heading y objetivo. Dentro de este mapeo provisional, la correspondencia entre pesos y neuronas importa: el mismo contenido de pesos barajado no conserva la función.

El mejor resultado de FC2B solo es una observación del modelo, no evidencia de que FC2B sea el único subtipo funcional en la mosca. Puede depender de la asignación geométrica de columnas, de los dos FC2C excluidos y de la normalización elegida.

## Límites que impiden una afirmación más fuerte

1. Los ángulos Δ7 se infieren mediante una media circular ponderada de sus propias conexiones hacia PFL3. Esto usa estructura FlyWire real, pero no constituye validación independiente de la topografía Δ7.
2. Las columnas FC2 y PFL3 se asignaron geométricamente desde esqueletos, no desde etiquetas expertas o coordenadas de sinapsis.
3. La auditoría posterior sí propagó EPG explícitamente y rechazó las variantes feedforward probadas: véase [epg-delta7-audit.md](epg-delta7-audit.md). La recurrencia Δ7 y la dinámica temporal siguen pendientes.
4. Los conteos anatómicos no equivalen automáticamente a eficacia sináptica.
5. No se ajustó un controlador ni se evaluó navegación. Estas métricas describen solamente la transformación neuronal estacionaria.
6. Los 100 barajados son controles computacionales deterministas; todavía no constituyen una prueba estadística completa con familias de grafos nulos.

## Reproducibilidad

```powershell
.\.venv\Scripts\python.exe -m flydrone.neural.evaluate_connectome --shuffle-seeds 100
```

La configuración está en `configs/connectome_model.yaml`, el resumen en `results/neural/connectome_weighted_pfl3/report.json` y todas las trazas contienen el readout; las seis condiciones principales conservan además la tasa de cada PFL3.

## Próximo paso

Extraer coordenadas sinápticas PB para validar las asignaciones EPG, Δ7 y PFL3. La etapa EPG→Δ7 sólo se promoverá al controlador cuando supere esa validación independiente. Después se probarán ruido sensorial, retrasos y una dinámica temporal declarada antes de convertir R−L en un comando de steering.
