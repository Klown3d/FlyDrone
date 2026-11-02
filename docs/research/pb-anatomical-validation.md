# Verificación anatómica del PB y signo angular

Fecha: 2026-09-16. FAFB/FlyWire 783. Este paso verifica datos y convenciones; no integra el dron.

## Hallazgo respaldado por la fuente

En los métodos de [Mussells Pires et al. (2024)](https://doi.org/10.1038/s41586-023-07006-3), sección del modelo poblacional PFL3, los autores explican que el signo negativo de las preferencias proviene de convertir ángulos referidos al ellipsoid body a ángulos de heading: bump EPG y heading tienen signos opuestos. El [código archivado](https://doi.org/10.5281/zenodo.10232698) aplica la misma inversión junto con un desplazamiento global. El texto completo utilizado se conserva en `data/raw/literature/PMC10881393.xml`.

Nuestra configuración EPG provisional expresaba las fases en sentido creciente mientras las preferencias PFL3 ya incorporaban la inversión. Por tanto, la reflexión probada tiene justificación de fuente, además de mejorar el steering estático. **La conversión de signo está respaldada; la identificación de cada glomérulo FAFB y su origen de fase todavía no están completamente validados.** No son dos preguntas equivalentes.

## Extracción sin el recorte de socios

Se extrajeron todos los contactos etiquetados PB que tienen al menos un extremo en las 195 neuronas seleccionadas. Incluye socios externos; no implica que se hayan anotado todos ellos.

- 105.003 contactos únicos en el producto completo con frontera.
- 11.339 contactos internos, con cero discrepancias por par frente a la tabla agregada.
- Mismo original estático 783 y metadatos/checksums preservados.
- No se añadieron umbrales ni pesos funcionales.

Archivos: `data/processed/fafb783_epg_delta7_fc2_pfl3/pb-synapses-with-boundary.parquet` y su `.provenance.json`.

## Validación EPG

Para cada una de las 47 EPG se calculó la mediana xyz de **todos sus contactos presinápticos del PB**, incluyendo socios externos. Se aplicó Ward con 16 grupos y ordenamiento por el arco PB, sin utilizar el readout, las preferencias PFL3 ni el resultado de steering.

**Las 47 de 47 asignaciones coinciden** con las etiquetas obtenidas anteriormente de los esqueletos. Esto aporta una segunda representación anatómica consistente. Utiliza el mismo algoritmo y la misma hipótesis de 16 posiciones ocupadas; no equivale a validación por un atlas glomerular independiente o un experto.

La tabla por neurona conserva centros, cantidad de contactos y comparación de etiquetas: `results/morphology/pb-contact-validation/epg-contact-vs-skeleton-columns.csv`.

## Δ7 y PFL3: qué pudimos comprobar

Guardamos perfiles de todos sus contactos PB de entrada y salida, asignando el ancla EPG más cercana. Las asignaciones a PB02/PB17 quedan marcadas como ambiguas respecto de PB01/PB18. **No extrapolamos glomérulos extremos ni afirmamos haber identificado subtipos Δ7.** La distancia espacial al ancla se conserva para inspección.

Como diagnóstico adicional, ajustamos constante + seno + coseno a los conteos EPG→Δ7 agrupados por columna. La mediana de R² es **0,3493**. Es un ajuste a perfiles individuales sin alineación ni promedio entre subtipos, distinto del procedimiento de [Hulse et al., figura 20](https://elifesciences.org/articles/66039). Por ello no debe compararse directamente con su perfil poblacional ni interpretarse como aprobación del modelo sinusoidal. Indica que queda estructura sin explicar.

Hulse describe salidas separadas por siete glomérulos; la figura suplementaria de Mussells Pires utiliza un esquema de ocho posiciones, con casos de nueve y reglas de asignación según dendritas. Es necesario establecer cómo se corresponden sus convenciones de numeración antes de convertir esas distancias en una prueba automática. No imponemos una distancia universal para etiquetar las neuronas reales.

## Decisión y próximo paso

La inversión del signo se sostiene como **corrección de convención candidata respaldada por literatura**. Se conserva en el harness diagnóstico. El mapa completo y los subtipos siguen pendientes, así que no se promueve todavía al controlador principal.

La siguiente tarea es visualizar los contactos presinápticos Δ7 completos sobre el arco PB, localizar los compartimentos de salida extremos y verificar las 18 posiciones con un atlas/etiquetado anatómico trazable. Debe conservarse incertidumbre para cada asignación. Después se fijará una configuración angular versionada y se repetirán los controles de conectividad y las pruebas dinámicas.

## Reproducción y verificación

```powershell
.venv\Scripts\python.exe -m flydrone.data.extract_static_pb --include-boundary
.venv\Scripts\python.exe -m flydrone.morphology.validate_pb_contacts
```

Informe: `results/morphology/pb-contact-validation/report.json`. Seis pruebas relacionadas con morfología, filtrado y diagnóstico de fase pasaron. Los conteos del producto real también se verificaron contra la tabla agregada. No se ejecutó navegación ni se cambiaron conexiones o propiedades biológicas.
