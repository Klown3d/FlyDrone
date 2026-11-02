# FlyDrone: extracción anatómica del circuito FAFB 783

Fecha de extracción: **2026-09-13**. Estado: **anatomía extraída; correspondencia funcional pendiente**. Esta etapa no contiene dinámica neuronal, actividad simulada ni control de dron.

## Resultado

Se extrajo de FlyWire FAFB, materialización 783, el subgrafo inducido por las etiquetas exactas `EPG`, `Delta7`, `FC2A`, `FC2B`, `FC2C` y `PFL3` de la columna `hemibrain_type` de las anotaciones v2.1.0. Aunque la columna conserva nomenclatura de correspondencia con hemibrain, los nodos son `root_id` de FlyWire y las aristas provienen exclusivamente de la conectividad FAFB 783.

| Tipo anotado | Neuronas |
| --- | ---: |
| EPG | 47 |
| Delta7 | 40 |
| FC2A | 16 |
| FC2B | 28 |
| FC2C | 40 |
| PFL3 | 24 |
| **Total** | **195** |

Con umbral mínimo de una sinapsis por par de neuronas, el subgrafo contiene **4.414 aristas dirigidas** y **17.944 contactos sinápticos**. Las aristas aparecen en 4.600 filas cuando se conserva el neuropilo. Una componente débil contiene 194 neuronas; la neurona FC2C `720575940629923883`, marcada `outlier_seg` en la fuente, queda aislada dentro del subgrafo. El grafo tiene cuatro componentes fuertemente conexas: una de 192 neuronas y tres singletes.

No se excluyó el segundo FC2C marcado `outlier_seg` (`720575940622374783`). Ambos estados se conservan para análisis de sensibilidad. `EPGt` tiene cuatro células anotadas, pero se excluyó por ser una etiqueta distinta de `EPG`.

## Conectividad observada

Los principales grupos de conexiones internas por número de contactos son:

| Presináptica | Postsináptica | Aristas | Contactos |
| --- | --- | ---: | ---: |
| EPG | Delta7 | 928 | 3.587 |
| Delta7 | Delta7 | 982 | 3.202 |
| EPG | EPG | 501 | 2.899 |
| Delta7 | PFL3 | 238 | 2.326 |
| Delta7 | EPG | 327 | 1.568 |
| FC2A | PFL3 | 105 | 838 |
| FC2C | PFL3 | 203 | 801 |
| FC2B | PFL3 | 162 | 785 |
| EPG | PFL3 | 108 | 671 |
| PFL3 | PFL3 | 204 | 387 |

Por neuropilo, la mayor parte de los contactos internos está en PB (11.339), seguida por FB (2.981) y EB (2.572). También aparecen contactos en regiones de salida como LAL. Estas cifras son observaciones de la tabla anatómica, no pesos fisiológicos ni evidencia independiente de función.

Las 24 PFL3 tienen contactos de salida en un solo LAL dominante y dicho lado es contralateral al lado del soma: las 12 con soma derecho contactan LAL izquierdo y las 12 con soma izquierdo contactan LAL derecho. Esto permite registrar la lateralidad anatómica de terminales, pero todavía no asigna por sí solo el signo de giro funcional.

## Frontera y truncamiento

La extracción conserva **56.054 filas de frontera** que conectan una neurona seleccionada con una externa, correspondientes a **3.196 neuronas externas anotadas**. Ningún ID externo de esta frontera quedó sin anotación en el archivo fijado.

El circuito seleccionado recibe o envía gran parte de sus contactos hacia fuera. La mediana de la fracción de entrada excluida es 0,935 para EPG, entre 0,987 y 0,991 para los subtipos FC2, 0,746 para PFL3 y 0,118 para Delta7. La mediana de salida excluida varía entre 0,728 y 0,986 según el tipo. Por tanto, el subgrafo inducido es un módulo experimental, no un sistema nervioso cerrado. El modelo funcional deberá representar las entradas de frontera explícitamente o justificar cuáles se omiten.

Estas fracciones usan sólo conexiones entre neuronas incluidas en `proofread_connections_783.feather`. No cuantifican contactos con objetos no revisados ni compensan el umbral aplicado por el proveedor.

## Sensibilidad al umbral

| Contactos mínimos por par | Aristas | Contactos retenidos | Aisladas | Componentes débiles |
| ---: | ---: | ---: | ---: | ---: |
| 1 | 4.414 | 17.944 | 1 | 2 |
| 3 | 1.970 | 14.694 | 2 | 3 |
| 5 | 1.205 | 12.094 | 7 | 8 |
| 10 | 471 | 7.357 | 43 | 44 |

No se adopta todavía un umbral biológico. La matriz base conserva todas las conexiones reportadas; estos cortes quedan preparados para análisis de robustez.

## Archivos producidos

El directorio `data/processed/fafb783_epg_delta7_fc2_pfl3/` contiene:

- `nodes.csv`: 195 neuronas, anotaciones, grados, fuerzas, fracciones de frontera y lateralidad LAL observada.
- `edges.csv`: aristas internas por par y neuropilo, con conteos y probabilidades medias de neurotransmisor.
- `edges_by_pair.csv`: conteos sumados por par, sin confundir filas de distintos neuropilos.
- `boundary_edges.csv` y `boundary_nodes.csv`: frontera entrante y saliente a un salto.
- `class_connectivity.csv`: agregación descriptiva por tipo.
- `type_mapping.csv`: correspondencias anotadas; columnas funcionales y ángulos quedan explícitamente sin resolver.
- `circuit-report.json`: estadísticas, componentes, umbrales, conexiones dominantes y limitaciones.
- `provenance.json` y archivos `*.metadata.json`: versiones, hashes, fechas de recuperación, dependencias y citas.

Los datos crudos y procesados permanecen fuera del control de versiones mediante `.gitignore`. `data/manifest.json` registra sus rutas, tamaños y SHA-256 locales. La conectividad tiene licencia CC BY 4.0 según Zenodo. No se encontró una licencia explícita en la raíz del commit fijado de las anotaciones; se conserva atribución y queda pendiente aclarar sus términos de redistribución.

## Reproducción

Desde la raíz del proyecto:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-lock.txt
.\.venv\Scripts\python.exe -m pip install -e . --no-deps
.\.venv\Scripts\python.exe -m flydrone.data.acquire --workers 8
.\.venv\Scripts\python.exe -m flydrone.connectome.extract --config configs/data.yaml
.\.venv\Scripts\python.exe -m pytest -q
```

La adquisición rechaza cambios en versión, tamaño o checksum publicado, descargas HTML y artefactos fuera del manifiesto. La extracción valida tipos enteros, IDs revisados, esquema, valores nulos, conteos positivos y probabilidades de neurotransmisor. Los tests sintéticos no se presentan como datos FlyWire.

## Lo que falta para actividad neuronal

La anatomía confirma que el circuito seleccionado existe como subgrafo densamente conectado y que convergen rutas EPG/Delta7 y FC2 sobre PFL3. Aún faltan:

1. Resolver glomérulo PB, columna FB y ángulo preferido por neurona a partir de morfología y fuentes funcionales.
2. Validar qué subtipos FC2 participan en la señal objetivo observada experimentalmente.
3. Separar predicción de neurotransmisor de signo postsináptico; no convertir glutamato automáticamente en inhibición ni acetilcolina en un peso numérico.
4. Definir entradas de frontera, dinámica temporal y ganancias con procedencia y análisis de incertidumbre.
5. Reproducir fuera del lazo cerrado una propiedad publicada del circuito antes de animar actividad o usarla para steering.

El próximo paso concreto es una **auditoría morfológica y funcional de las 195 neuronas**, empezando por la asignación columnar de EPG/Delta7/PFL3 y la identidad funcional de FC2A/B/C. Sólo después se implementará un modelo de tasas y la visualización 3D de su actividad simulada.
