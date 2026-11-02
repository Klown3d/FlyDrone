# Diagnóstico de fase EPG → Δ7 → PFL3

Fecha: 2026-09-16. Datos: FAFB/FlyWire, materialización 783. Estado: diagnóstico reproducible; no controlador aprobado.

La prioridad de revisar el mapeo angular fue acertada. El hallazgo principal es una posible inversión de la convención angular entre EPG y PFL3: invertir únicamente las fases EPG mejora mucho el steering del modelo estático. Un desplazamiento global no había corregido el fallo. Una reflexión `θ → −θ` invierte el sentido de recorrido del círculo; no equivale a sumar una constante de fase.

## Datos y control de extracción

Se procesó por lotes `data/raw/flywire_synapses_783.feather`, previamente verificado contra el MD5 oficial. Se conservaron los contactos del PB cuyos dos extremos pertenecen a las 195 neuronas seleccionadas: **11.339 contactos, IDs únicos y cero discrepancias por par** respecto de `edges.csv`. La extracción no añade umbrales de confianza. Coordenadas pre/post en nanómetros, identificadores, neuropilo y predicciones de neurotransmisores están disponibles. No existe campo de área sináptica. `cleft_score` y `connection_score` no son medidas de área ni de eficacia funcional.

Productos: `data/processed/fafb783_epg_delta7_fc2_pfl3/pb-synapses.parquet`, archivo de procedencia y tabla de discrepancias. La procedencia conserva los metadatos del original y el hash del producto.

## La media circular no sustituye por sí sola una fase anatómica incorrecta

Para pesos normalizados por neurona receptora:

`z_j = Σ_i w_ji exp(i θ_i)`, `φ_j = arg(z_j)`, `R_j = |z_j|`.

Entonces `Σ_i w_ji cos(H−θ_i) = R_j cos(H−φ_j)`.

El modelo anterior ya implementaba el miembro izquierdo. Implementamos el derecho y verificamos igualdad con error máximo **9,02 × 10⁻¹⁶**. Usar `cos(H−φ_j)` sin `R_j` modificaría la amplitud: ya no sería una ablación de fase únicamente. Cuando el resultante es cero, la fase no tiene interpretación definida. La fase calculada depende de las fases EPG asumidas; el connectoma solo no mide preferencias de heading.

La variante continua proyecta el centroide de contactos presinápticos EPG sobre una polilínea de anclas PB obtenidas de la geometría anterior e interpola sus fases desenrolladas. Usa exclusivamente anatomía, sin optimizar contra PFL3 o steering. **No es una anotación glomerular independiente:** conserva las mismas anclas provisionales y usa solo contactos internos del circuito seleccionado. No se denomina regresión circular validada.

## Contraste con fuentes

[Hulse et al., figura 20 y métodos](https://elifesciences.org/articles/66039) describen entradas EPG→Δ7 aproximadamente cosenoidales y salidas Δ7 concentradas en dos o tres glomérulos separados por siete posiciones. Su análisis agrupa Δ7 por glomérulos de salida, alinea perfiles y propaga actividad mediante matrices de contactos. Explicitan la omisión de no linealidades y recurrencia en esa aproximación. El estudio usa hemibrain: sus subtipos no son etiquetas verificadas de nuestras neuronas FAFB.

Guardamos `delta7-glomerular-contact-profiles.csv` con perfiles de entrada/salida frente a anclas provisionales. **No afirmamos reproducir los subtipos publicados.** Las anclas EPG cubren PB02–PB17, de modo que no permiten etiquetar correctamente salidas a PB01/PB18. Además, faltan socios externos al circuito. La validación completa exige anotar esos glomérulos y comparar perfiles de salida completos; un desacuerdo de clustering puede proceder del etiquetado, de la extracción incompleta o de diferencias entre individuos, y no demuestra automáticamente un bug.

El [código original de Mussells Pires et al.](https://doi.org/10.5281/zenodo.10232698), `analysis/model.py`, líneas 37–50, aplica `thetaPB = -wrap(thetaPB + 180)` y utiliza ese vector para construir las preferencias PFL3. Nuestro mapa EPG provisional recorría fases en sentido creciente mientras las preferencias PFL3 importadas seguían el sentido invertido. Esto motiva verificar la reflexión; aún queda comprobar la correspondencia anatómica de anclas y el desplazamiento EPG/Δ7. Fuente experimental: [Mussells Pires et al., 2024](https://doi.org/10.1038/s41586-023-07006-3).

## Comparación controlada inicial

Se conserva el camino PB EPG→Δ7→PFL3, el input de meta FC2, los conteos y el readout derecha menos izquierda. Se evalúan 12 metas y 361 headings relativos por meta. Dirección correcta excluye |error| < 5° y > 170°. El equilibrio reportado requiere pendiente negativa; si no existe, queda ausente. Se elige el equilibrio estable más próximo a la meta: esta métrica no mide su cuenca de atracción.

No se ajusta un desfase global para calcular estos resultados. Por eso la referencia anterior aquí es 87,66°, frente a aproximadamente 85° en el informe con calibración global. Todas estas condiciones tienen equilibrio estable detectado para las 12 metas.

| Condición | Error medio de equilibrio | Dirección correcta |
|---|---:|---:|
| Binning anterior, transferencia Δ7 lineal | 87,66° | 50,90% |
| Misma entrada expresada como fase circular + resultante | 87,66° | 50,90% |
| Fases EPG continuas desde centroides sinápticos | 87,69° | 50,88% |
| Continua + recurrencia normalizada, ganancia 1 | 87,73° | 50,83% |
| Continua + sigmoide centrada | 87,81° | 50,83% |
| Binning anterior con sentido angular EPG invertido | **2,65°** | **99,77%** |
| Continua con sentido angular EPG invertido | 2,89° | 99,75% |
| Continua invertida + recurrencia | 3,52° | 99,60% |
| Continua invertida + sigmoide | 2,84° | 99,72% |

El desacuerdo de fases PFL3 después de un ajuste global, usado solo como diagnóstico independiente de la tabla de steering, pasa de 82,18° a 15,98° con reflexión. El desfase ajustado en esa variante es 0,50°. No corresponde presentar 2,65° de error poblacional como precisión de fase de cada neurona.

## Recurrencia y no linealidad: supuestos explícitos

Se añade la matriz real de 3.158 contactos Δ7→Δ7, normalizada por suma de entrada de cada receptora. La prueba lineal calcula exactamente el estado estacionario de `τ dx/dt = −x + u − W_DD x`, ganancia 1. El margen mínimo de parte real de los autovalores de `I + W_DD` es 0,7832: este modelo lineal converge para cualquier τ positivo. No se elige una constante temporal ni se afirma reproducir transitorios biológicos. El signo inhibitorio uniforme Δ7→Δ7 es un supuesto funcional de la prueba, no una medición de receptores de cada par.

La sigmoide centrada se implementa como `tanh(x)` y se compara con el mismo modelo sin recurrencia. Ganancia, normalización y pendiente son decisiones de ingeniería configuradas; las variables Δ7 son desviaciones firmadas, no tasas de disparo negativas. La salida PFL3 conserva la softplus del modelo anterior. Cambiar todas las transferencias a la vez confundiría factores.

También se guardan condiciones de recurrencia y sigmoide sobre la variante reflejada en el informe JSON para evaluar esos factores cuando el steering ya funciona. La comparación conteo frente a área queda explícitamente **no ejecutable con esta tabla**.

## Alcance causal y riesgos

La intervención angular aislada demuestra sensibilidad causal del modelo actual a su convención de entrada y explica la mayor parte del fallo estático observado. No identifica por sí sola las preferencias biológicas reales. El error medio cercano a 90° no bastaba para diagnosticar un desfase: también puede producirse por reflexión, mezclas de mapas o pérdida de dependencia de la meta.

Todavía faltan validación completa de subtipos, incertidumbre de anclas, sensibilidad a ganancias, controles de conectividad aleatorizada con la convención corregida, metas/heading de resolución independiente, forma de bump EPG no sinusoidal y navegación dinámica. Se mantiene el candidato anterior y sus resultados históricos para comparar. No se modifica todavía el controlador principal ni se integra el dron.

## Reproducción y siguiente paso

Desde el proyecto:

```powershell
.venv\Scripts\python.exe -m flydrone.data.extract_static_pb
.venv\Scripts\python.exe -m flydrone.neural.phase_diagnostic
```

Configuración: `configs/phase_diagnostic.yaml`. Resultados, fases, perfiles, trazas PFL3 y desviaciones Δ7 por condición: `results/neural/phase_diagnostic/`. El informe conserva hashes. Las pruebas sintéticas verifican identidad circular y rechazo de cruces inestables; no se usan como evidencia biológica.

**Próximo paso concreto:** completar un mapa anatómico PB de 18 glomérulos usando contactos de entrada/salida completos de EPG, Δ7 y PFL3, verificar su orientación respecto de la figura y del código publicado, y después repetir las ablaciones con esa convención fijada y controles de conectividad. Solo entonces promover la corrección al modelo funcional. El resultado de hoy cambia la prioridad: primero resolver la convención angular, antes de aumentar la complejidad dinámica.
