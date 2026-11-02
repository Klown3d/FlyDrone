# FlyDrone: selección de circuito y viabilidad científica

Fecha de revisión: **2026-09-12**. Estado de esta decisión: **fase 0 terminada**. Actualización del 2026-09-14: la extracción anatómica se completó y está documentada en [circuit-extraction.md](circuit-extraction.md). La entrada de objetivo primaria se refinó a FC2B/FC2C; la propagación explícita desde EPG fue probada y rechazada con los datos agregados actuales, como documenta [epg-delta7-audit.md](epg-delta7-audit.md). No se implementaron controladores ni simulador.

## 1. Hipótesis y alcance

> Un modelo computacional reconstruido a partir de la conectividad de un circuito funcional del *central complex* de *Drosophila melanogaster*, utilizando datos del connectoma FlyWire, puede generar señales de orientación y steering capaces de controlar autónomamente la navegación de un dron simulado, alcanzando un desempeño medible y comparable con controladores convencionales.

La primera prueba propuesta es **orientación hacia una dirección objetivo y navegación planar hacia un waypoint**, con velocidad de avance y estabilización convencionales. No constituye una demostración de vuelo biológico, navegación tridimensional general, selección autónoma de objetivos ni evitación neuronal de obstáculos.

La variable independiente será la arquitectura del controlador. Se medirán desempeño, robustez, costo computacional y dependencia de la conectividad real. Se distinguen dos preguntas:

1. **Utilidad:** ¿el sistema alcanza objetivos con desempeño útil y comparable al mejor baseline convencional?
2. **Atribución:** ¿la conectividad real aporta algo que desaparece o cambia de manera específica con controles anatómicos equiparados?

La superioridad sobre PID no es requisito lógico de la hipótesis original. Tampoco basta con no encontrar una diferencia significativa para afirmar equivalencia. Antes de evaluar, habrá que fijar márgenes de no inferioridad y un umbral de utilidad adecuados a la tarea. H0 de atribución: el grafo real no aporta una diferencia reproducible frente a grafos de control equiparados. Un resultado negativo también será un resultado del proyecto.

**Convención de evidencia:** **E** = evidencia experimental; **A** = anatomía reconstruida/documentada; **M** = interpretación o modelo de los autores; **P** = propuesta de ingeniería de FlyDrone; **?** = pendiente o incierto. Una conexión descrita en otro espécimen no se considerará una arista FlyWire hasta verificarla en la extracción.

Se siguió la `SKILL.md` facilitada por el usuario. Su ruta genérica `docs/circuit-selection.md` queda como enlace al presente documento: la solicitud explícita establece `docs/research/circuit-selection.md` como ubicación canónica.

## 2. Decisión y candidatos ordenados

**Principal: módulo de transformación rumbo–objetivo–giro EPG/Δ7 + FC2 → PFL3.** Extraer sus neuronas individuales, conexiones internas y fronteras de entrada/salida. Comenzar con estímulos poblacionales controlados en EPG y FC2; evaluar después una extensión que genere el rumbo con la brújula recurrente. El primer módulo no se presentará como estimador autónomo del rumbo.

**Alternativa: brújula recurrente EPG, PEN, PEG y Δ7**, con entrada visual simplificada y señal de rotación. Si la identificación columnar o la parametrización del comparador impide una prueba interpretable, esta alternativa permite validar orientación y memoria de rumbo. Su salida necesitará un controlador convencional de giro: eso reduce el alcance de la hipótesis que se puede probar.

| Prioridad | Circuito y señales | Evidencia relevante | Disponibilidad y dificultad | Decisión |
| --- | --- | --- | --- | --- |
| 1 | EPG/Δ7, FC2 y PFL3: rumbo y objetivo hacia salida lateralizada | Convergencia y función de comparación, con perturbaciones causales [S1, S2] | Tipos buscables mediante anotaciones FlyWire; identidades, subtipos y aristas por verificar. Requiere resolver columnas y lateralidad | Principal: relación directa con steering y frontera experimental acotada |
| 2 | EPG–PEN–PEG–Δ7, más aferencias visuales seleccionadas: brújula | Actividad persistente y actualización del rumbo [S3–S5] | Requiere correspondencias entre nomenclaturas PEN1/PEN2 y etiquetas del archivo; no fusionarlas automáticamente | Alternativa; también extensión posterior del principal |
| 3 | Comparador ampliado con PFL2 y red premotora LAL/DNa03 | PFL2 modula la intensidad de giro en grandes errores [S2] | Más neuronas fuera del CX y mayor incertidumbre funcional | Extensión para ganancia; no necesaria para primera extracción |
| 4 | PFNd/PFNv → hΔB, con señales de locomoción | Transformación de velocidad corporal a dirección de desplazamiento en el mundo [S6, S7] | Añade entradas de velocidad; no entrega por sí solo objetivo ni giro | Posponer hasta estudiar deriva lateral |
| 5 | hΔK–PFG y sus reguladores: memoria de dirección | Recurrencia y persistencia propuestas con fisiología en un preprint [S15]; contexto olfativo reciente [S14] | Correspondencia celular y salida a steering pendientes; evidencia de distinto grado | Interesante para memoria, menos directo para MVP |

La disponibilidad anterior significa que existen productos para buscar estos circuitos en FAFB; **no certifica todavía su composición exacta**. No se fijan cantidades de neuronas, conectividad ni tiempos de ejecución antes de medirlos. La selección es por alcance funcional y auditabilidad, no por un tamaño inventado.

## 3. Evidencia funcional y sus límites

| Fuente primaria | Qué se observó o estableció | Qué permite concluir y qué no |
| --- | --- | --- |
| Mussells Pires et al., 2024 [S1] | FC2 representa una dirección objetivo; activación focal modifica la orientación. PFL3 recibe entradas de EPG y FC2 y muestra sintonía conjunta. Manipulaciones de PFL3 afectan orientación dirigida | **E/A:** apoyo al comparador. **M:** su formalización computacional. Experimentos de caminata; no control de vuelo libre |
| Westeinde et al., 2024 [S2] | Imagen, registros eléctricos y estimulación relacionan PFL3 derecha/izquierda con giros correctivos; PFL2 interviene en la rapidez de giro ante grandes desviaciones | **E:** salida lateralizada y modulación de ganancia. Los desfases fisiológicos no deben reemplazarse por un desplazamiento anatómico ideal fijo. Usar versión corregida: la corrección de 2025 modifica identificación de una línea genética [S2c] |
| Seelig y Jayaraman, 2015 [S3] | Imagen de calcio durante caminata en realidad virtual: representación de azimut, seguimiento de referencias y persistencia sin ellas | **E:** rumbo y memoria angular. No equivale a posición XY ni a distancia recorrida |
| Turner-Evans et al., 2020 [S4] | Reconstrucción EM, perfiles de expresión y perturbaciones funcionales identifican mecanismos recurrentes de la brújula | **E/A:** base para probar persistencia y actualización; PEN1 aporta señales relacionadas con rotación y Δ7 participa en estabilización. No determina todos los parámetros de cada célula FlyWire |
| Hulse et al., 2021 [S5] | Connectoma del CX del **hemibrain**, con entradas, recurrencias y rutas de salida | **A:** guía anatómica y de nomenclatura; sus hipótesis de navegación no son todas pruebas funcionales. Sus IDs y pesos no pertenecen a FAFB |
| Lyu et al. y Lu et al., 2022 [S6, S7] | Fisiología y perturbaciones apoyan una representación de desplazamiento distinta del rumbo | **E:** justifica un futuro módulo para deriva. No demuestra un controlador completo de objetivos |

Actualización de búsqueda: el trabajo de 2026 sobre memoria e integración durante navegación olfativa aporta evidencia de persistencia de una señal de objetivo [S14]. El preprint hΔK–PFG [S15] ofrece una hipótesis mecanística más específica; la versión consultada está marcada **no revisada por pares**. También se identificó un artículo de 2026 sobre navegación olfativa vectorial [S16], pero sólo se verificó su resumen bibliográfico: no se extraen de él parámetros ni conexiones. Estos trabajos amplían posibilidades futuras sin resolver automáticamente la memoria de objetivos en FC2.

## 4. Neuronas, conexiones y límites de extracción

EB = ellipsoid body; PB = protocerebral bridge; FB = fan-shaped body; LAL = lateral accessory lobe; NO = noduli.

| Elementos | Papel y relación que se debe auditar | Tratamiento propuesto |
| --- | --- | --- |
| EPG | Representación del rumbo; entradas al comparador en PB [S1, S3] | Frontera de entrada controlada en el primer ensayo; incluir aristas reales internas del conjunto |
| Δ7 / Delta7 | Relés del sistema de rumbo; revisar EPG→Δ7 y Δ7→PFL3, además de recurrencias reales [S1, S4, S5] | No sustituir por una inhibición global uniforme inventada; conservar incertidumbre del signo por destino |
| FC2 | Señal objetivo y proyecciones hacia PFL3 en FB [S1] | Resolver todos los subtipos anotados y el alcance de la evidencia funcional; no suponer idéntica función para cada subtipo |
| PFL3 | Convergencia en PB/FB y salida a LAL [S1, S5] | Leer población según lado de terminales de salida, no según lado del soma |
| PEN, PEG y aferencias visuales | Bucle de brújula en EB/PB/NO; PEN1 y PEN2 no son intercambiables [S4, S5] | Sólo en alternativa/extensión, con diccionario explícito de equivalencias y validación |
| PFL2, DNa03 y socios LAL | Red ampliada para modulación de steering [S2, S5] | Registrar frontera anatómica; no atribuir al MVP una reconstrucción descendente que no implementa |

Las flechas son **relaciones a comprobar**, no una lista de aristas extraídas. El grafo ejecutable futuro incluirá todas las aristas observadas entre las células seleccionadas, incluidas las que no aparecen en este esquema. Un enlace que no aparezca en los datos no se añadirá para hacer funcionar el modelo.

**Contrato propuesto para M2 (extracción):**

1. Resolver una lista explícita de tipos/subtipos y `root_id` en la versión fijada. No usar coincidencias por prefijo sin revisar qué incluyen. Mantener etiquetas originales, alias bibliográficos y justificación por célula.
2. Extraer el subgrafo inducido EPG/Δ7/FC2/PFL3, con ambas lateralidades; no simetrizar ni reducir a una neurona por clase. Identificar por separado entradas y salidas a un salto como informe de frontera, sin incorporarlas automáticamente al modelo.
3. Conservar aristas por par y neuropilo. Para la matriz total sumar regiones una sola vez. PB, FB y EB son regiones de auditoría; filtrar exclusivamente por ellas podría eliminar conexiones relevantes de frontera.
4. Conservar la base con al menos una sinapsis reportada por par/neuropilo. Probar umbrales de 1, 3, 5 y 10 sobre el **total por par**, como elecciones de ingeniería; no como garantía de veracidad. Registrar censura ya aplicada por el proveedor.
5. Exportar tablas propuestas `nodes.csv`, `edges.csv`, `boundary_edges.csv`, `type_mapping.csv` y un informe. Registrar conteos, componentes débiles/fuertes, grados, fuerza, bucles, conexiones dominantes, asimetría y fracción de entrada/salida excluida por célula.
6. Preservar IDs como enteros de 64 bits o cadenas, nunca como flotantes. Validar referencias, duplicados, conteos positivos, nulos, regiones, pertenencia a proofreading y procedencia.

La orientación preferida de cada célula **no sale del orden de los IDs ni del ángulo geométrico del soma**. Se requiere asignación de glomérulos PB/columnas FB, evidencia morfológica y correspondencia funcional. Cada asignación tendrá fuente y confianza. Si no puede resolverse, se detiene la conversión funcional de esa célula o se declara una variante abstracta separada.

## 5. Datos reales y versión elegida

**Selección:** FlyWire **FAFB, materialización 783**; conectividad del archivo de publicación **783.0** en Zenodo, registro **10676866**. Anotaciones del proyecto de Schlegel, **v2.1.0**, commit `ebd66db2596fcc39c6950fb54ea3efa00f7fe8a0`, correspondiente a las publicaciones de 2024 según su changelog [D2, D3]. Esta elección prioriza trazabilidad de publicación. No se afirma que v2.1.0 sea la anotación más reciente: se verificó también v3.1.0; comparar revisiones será una sensibilidad futura, nunca una actualización silenciosa.

El FAQ oficial identifica FAFB v783 y recomienda archivos estáticos para análisis masivo. También lista BANC como otro dataset: una versión numéricamente mayor de BANC no es una actualización intercambiable de FAFB. Las anotaciones de Codex pueden evolucionar aunque el snapshot anatómico conserve el número [D1, D4].

**Acceso verificado:** `https://codex.flywire.ai/api/download?dataset=fafb` respondió HTTP 200 con HTML de inicio de sesión, no con el catálogo. Por ello no se verificaron aquí los encabezados ni filtros de sus CSV. El FAQ documenta `consolidated_cell_types`, `connections_princeton` y descargas CSV comprimidas mediante `api/download_resource`; no se inventan productos adicionales ni se utiliza scraping de la interfaz [D1]. Se verificaron metadatos públicos de Zenodo y documentación de anotaciones como alternativa oficial de los autores. No se descargaron los archivos del connectoma.

| Producto verificado en documentación/metadatos | Formato y contenido | Uso |
| --- | --- | --- |
| `Supplemental_file1_neuron_annotations.tsv`, commit fijado | TSV, 27.015.208 bytes; `root_id`, `cell_type`, `hemibrain_type`, `side`, `status`, `top_nt`, `top_nt_conf`, entre otros [D3] | Selección y auditoría de tipos; contenido aún sin cargar |
| `proofread_connections_783.feather` | Feather, 852.022.274 bytes. `pre_pt_root_id`, `post_pt_root_id`, `neuropil`, `syn_count`, seis probabilidades medias de neurotransmisor [D2] | Grafo dirigido; filas por par y región, con al menos una sinapsis |
| `proofread_root_ids_783.npy` | NumPy, 1.114.168 bytes [D2] | Validar pertenencia al conjunto revisado |
| `flywire_synapses_783.feather` | Feather, aproximadamente 9,49 GB: IDs pre/post, localización y predicciones [D2] | Sólo si hace falta inspección sináptica; no necesario para empezar |

Las tablas de conexiones describen contactos químicos detectados, no conductancias. Las predicciones de neurotransmisor son probabilísticas [S10]. El archivo sináptico completo incluye asociados no revisados y ya aplica umbrales de detección [D2]. No confundir ausencia en una tabla filtrada con ausencia biológica.

`data/manifest.json` deja estas versiones como **planificadas**, con fecha de consulta, metadatos publicados y hashes locales nulos. En M2 habrá que guardar URL efectiva, fecha/hora de recuperación, SHA-256 local, hash publicado, versión de anotaciones, esquema, licencia y cita. No escribir una fecha de descarga para archivos que aún no se descargaron.

## 6. Modelo computacional propuesto

**P: comenzar con un modelo de tasas con fuga, por neurona reconstruida**, con matriz dispersa y no linealidad explícita. Permite evaluar el cómputo poblacional con menos parámetros libres que un modelo de spikes. No presupone que una célula biológica sea una unidad puntual ni reproduce automáticamente su fisiología.

Una familia candidata, todavía sin valores asignados, es:

\[
\tau_i\dot r_i=-r_i+\phi_i\left(b_i+I_i(t)+\sum_j W_{ij}r_j\right),
\quad W_{ij}=s_{ij}\,g_{c(i),c(j)}\,f(N_{j\to i}).
\]

`N` será exclusivamente el conteo observado; filas de `W` son postsinápticas. `s` es el signo respaldado o incierto; `g`, `f`, `tau`, sesgo y no linealidad son parámetros/modelos por justificar. Se propone comparar conteo lineal y normalización por entrada, reteniendo siempre la matriz anatómica original. Normalizar sólo por entradas del subgrafo puede amplificar artificialmente conexiones marginales: documentar el denominador y cuantificar entradas omitidas.

Probar primero una rectificación suave o saturante como **P**, junto con la respuesta estacionaria descrita en los modelos de [S1, S2]. No copiar constantes sin localizar ecuación, unidades y condición experimental. No entrenar cada arista libremente como primera opción: calibrar un conjunto pequeño de ganancias por clase y verificar sensibilidad. Si la función sólo emerge tras ajustes arbitrarios por arista, la atribución anatómica será débil.

LIF queda como segunda opción si una propiedad validable exige spikes o tiempos que el modelo de tasas no explica. Compartimentos o conductancias detalladas sólo se justificarán con datos adicionales; más complejidad no sustituye parámetros ausentes. Una entrada de calcio medida tampoco se interpretará directamente como tasa sin un modelo de observación.

Antes del lazo cerrado, realizar barridos independientes de rumbo y objetivo, curvas de giro, perturbación unilateral y análisis de saturación. En la extensión de brújula probar persistencia sin referencia, desplazamiento del bump con rotación, deriva y recuperación. No imponer un bump continuo desde el simulador durante una prueba que pretende demostrar memoria recurrente.

## 7. Interfaz sensorial, lectura y arquitectura

```text
Observaciones simuladas + objetivo de misión
  → estimador/encoder explícito
  → poblaciones de entrada EPG y FC2
  → conexiones FlyWire del módulo de comparación
  → actividad de salida PFL3 en cada LAL
  → lectura fija → velocidad angular deseada
  → estabilizador convencional → dinámica simulada → observaciones
```

Es un diagrama de módulos propuestos, no un mapa de sinapsis. En la extensión recurrente, el encoder alimentará las aferencias de la brújula seleccionadas; EPG será entonces una salida interna.

| Entrada/salida | Transformación propuesta y unidades | Estatus y límite |
| --- | --- | --- |
| Rumbo estimado `theta` | Patrón circular sobre EPG, alineado mediante un único offset calibrado | Representación de rumbo: **E** [S3]. Inyección directa: **P**, omite percepción y brújula |
| Objetivo `g` | Patrón sobre FC2 en el mismo marco allocéntrico | Relación con objetivo: **E** [S1]. Generarlo desde un waypoint: **P**, no memoria aprendida |
| Landmark y giro propio | Azimut relativo del landmark en radianes y velocidad yaw en rad/s hacia las aferencias identificadas | Apoyo general de integración visual/automo­vimiento [S3, S4]; encoder exacto: **? / P** |
| Flujo óptico | Futuramente, estimación de velocidad corporal hacia un módulo PFN | Abstracción; no enviar RGB arbitrario ni equiparar flujo con velocidad sin hipótesis de profundidad |
| PFL3 | Diferencia de suma de actividad en terminales derechos e izquierdos, ganancia fija y saturación | Asimetría funcional: **E** [S2]; escala a rad/s: **P** |
| EPG para diagnóstico | Fase del vector poblacional y concentración circular | Decoder **P**; requiere mapa angular validado y criterio de bump ausente/ambiguo |

Para waypoints, `g = atan2(y_obj-y_est, x_obj-x_est)` es un cálculo de ingeniería externo. La misma estimación de posición se dará a los baselines. No suministrar el error angular ya calculado al módulo principal: la comparación es precisamente lo que se quiere evaluar.

Definir ejes explícitos: en la prueba planar propuesta, yaw positivo antihorario/izquierda; si se calcula actividad derecha menos izquierda, la ganancia al yaw tendrá signo negativo. Verificarlo con entradas conocidas antes de cerrar el lazo. Ni `side` del soma ni etiquetas históricas L/R garantizan el lado de la salida.

Una función circular del tipo `b + A*cos(theta-phi_i)`, seguida de rectificación, puede servir como estímulo artificial. `phi_i`, anchura, amplitud y offset quedan pendientes; no se asignarán fases uniformes y se llamarán anatomía. Registrar resultados con sensores perfectos como diagnóstico separado y con ruido/latencia como evaluación. El readout no accederá a posición, rumbo ni objetivo: sólo actividad neuronal.

Un estabilizador común podrá manejar actitud/altura, límites y seguimiento de velocidad. La velocidad de avance y el frenado cerca del waypoint serán iguales entre arquitecturas. En la primera tarea sin obstáculos, la colisión será salida del recinto; añadir obstáculos exige un planificador común declarado o ampliar la biología. No atribuir evitación de obstáculos a PFL3 sin demostrarla.

## 8. Datos faltantes y registro de parámetros TODO

| Pendiente | Qué aporta el connectoma | Qué falta y cómo resolverlo antes de ejecutar |
| --- | --- | --- |
| Identidad y correspondencia | Anotaciones por célula | Validar subtipos, aliases y discrepancias con hemibrain; tabla revisable |
| Mapa angular y lateralidad de salida | Morfología, regiones y contactos | Asignación columnar/glomerular y orientación funcional; no usar soma como sustituto |
| Signo postsináptico | Predicción de neurotransmisor | Receptores y efecto según célula destino. Glutamato no implica universalmente excitación; documentar fuente o ensayar hipótesis separadas |
| Eficacia sináptica | Conteo anatómico | Liberación, receptores, conductancia, saturación y normalización; conteo no es peso fisiológico |
| Dinámica intrínseca | No especificada por la tabla de aristas | `tau`, umbral, ganancia, adaptación, ruido y tasas basales; buscar medición específica o marcar elección de ingeniería |
| Transmisión y estado | Contactos químicos/predicciones | Retardos, plasticidad, neuromodulación, contactos eléctricos y dependencia del estado conductual |
| Entradas cortadas | Socios y fracción de contactos excluidos | Actividad de aferencias omitidas; sesgos de frontera y su sensibilidad |
| Meta y memoria | Candidatos anatómicos | Cómo se escribe/mantiene el objetivo; en MVP será externo, sin afirmar un mecanismo completo |
| Generalización | Un espécimen FAFB | Variabilidad entre animales/sexos y transferencia de caminata a dinámica de dron |

Cada futuro parámetro de `configs/neural_model.yaml` deberá tener valor, unidades, categoría **medido / inferido anatómicamente / elegido**, fuente precisa, condición experimental, rango de incertidumbre y método de calibración. Ningún valor queda establecido por este documento. Las inferencias no identificables deben producir familias de modelos, no una falsa reconstrucción única.

## 9. Baselines y diseño experimental

Todos los siguientes son **P**, para implementar después de reconstrucción y validación neuronal:

| Condición | Control y propósito |
| --- | --- |
| Proporcional/reglas | Error angular circular hacia el objetivo, zona muerta opcional y saturación comunes; mínimo funcional |
| PID | PID de error angular envuelto, anti-windup y tratamiento de discontinuidad; baseline convencional principal |
| Comparador analítico | `omega = k*sin(g-theta)` bajo los mismos límites; detecta si basta un cálculo trivial para igualar el modelo |
| Brújula FlyWire + control convencional | Separa beneficio de estimar rumbo del de transformarlo en steering |
| Grafo aleatorio equiparado | Mismas entradas, salidas, dinámica y presupuesto de calibración; prueba de atribución |
| RNN/MLP opcional | Capacidad y presupuesto registrados; mismas observaciones. RNN si se compara memoria |

Dividir escenarios en calibración, validación y test retenido. Igualar estimadores, acción permitida, frecuencia, límites, dinámica, objetivo y estabilizador. Comparar tanto rendimiento final como costo de ajuste. Una línea oracle con estado perfecto se etiqueta aparte; no se confronta como si tuviera los mismos sensores.

Propuesta inicial: rumbo constante, escalones de objetivo y recuperación tras empujes; luego waypoint en plano. Muestrear también errores cercanos a 180°, donde un comparador simétrico puede tener salida nula. Evaluar referencias ausentes, ruido, retardos y deriva lateral. Fijar semillas de escenarios emparejadas y semillas separadas de calibración/grafos; usar varios grafos sustitutos, no uno favorable.

Realizar un piloto para estimar variabilidad y dimensionar ensayos. Definir márgenes prácticos y tamaño de muestra antes del test; reportar diferencias emparejadas e intervalos de confianza del 95%, con bootstrap por episodio/escenario, no por frame. Reportar todos los fallos y no usar sólo trayectorias exitosas. Las semillas simuladas no son réplicas biológicas del connectoma.

## 10. Métricas y ablaciones

| Métrica | Definición propuesta |
| --- | --- |
| Éxito | Fracción de episodios dentro de radio `R_goal` durante `T_hold`, antes del plazo, sin colisión; valores a preregistrar |
| Colisión | Episodios con al menos una colisión / episodios totales; incluir salida de recinto y criterio geométrico |
| Error de rumbo | Media temporal y error final de `abs(wrap(g-theta))`; error del estimador respecto a verdad terreno por separado |
| Tiempo | Tiempo a objetivo, con timeout/censura explícitos; no promediar sólo éxitos como resultado principal |
| Trayectoria | Longitud; eficiencia distancia óptima factible/longitud observada. SPL: éxito multiplicado por distancia óptima/max(distancia óptima, longitud) |
| Robustez | Curvas de caída del desempeño frente a ruido, pérdida de referencia, retardo y perturbación; tiempo de recuperación |
| Costo | Latencia mediana/p95/p99 del paso neuronal y total; factor tiempo simulado/tiempo real, hardware y carga registrados |
| Arquitectura y función | Número de unidades/aristas, parámetros ajustados, fracción de conexiones excluidas; bump, drift, sintonía y balance lateral |

| Ablación/control | Qué se mantiene | Predicción o interpretación a evaluar |
| --- | --- | --- |
| Silenciar FC2 o sus salidas | Estímulo y readout fijos | Pérdida de flexibilidad ante cambios de objetivo; predicción del módulo propuesto |
| Silenciar PFL3 de un lado | Contralateral y fronteras fijas | Sesgo de giro coherente con lado de salida; comprobar sin reconfigurar signo |
| Eliminar recurrencia de brújula | Cues y ganancias iguales | Menor persistencia en oscuridad; sólo válido cuando EPG no está impuesto externamente |
| Permutar conteos entre aristas existentes | Topología, distribución global de pesos | Aísla distribución espacial de fuerza; no conserva necesariamente fuerza por nodo |
| Reconexionar con intercambios dirigidos | Nodos, grados de entrada/salida; restricciones de clase/neuropilo cuando sea viable | Aísla organización fina; informar si restricciones impiden aleatorización suficiente |
| Permutar correspondencias columna→salida | Tamaño, grado, pesos y energía de entradas | Evalúa geometría funcional. Una mera renumeración conjunta del grafo y encoder sería equivalente y no es una ablación |
| Eliminar fracción aleatoria equiparada | Igual cantidad de células o masa sináptica perdida | Controla daño inespecífico frente a eliminación de una clase |
| PFL2 ausente/presente | Mismo comparador base | Sólo en extensión: efecto sobre grandes errores y estabilidad |
| Umbrales, signos inciertos y normalización | Protocolo de evaluación | Sensibilidad a incertidumbre de datos/modelo |

Ejecutar ablaciones primero con parámetros congelados y luego con **igual presupuesto de recalibración** para controles y original. La primera prueba mide dependencia local; la segunda, si la arquitectura real ofrece una ventaja recuperable que no se explica por desajuste de escala. Una degradación tras cualquier lesión no demuestra especificidad biológica. Exigir convergencia entre controles equiparados, cambios de actividad previstos y desempeño; si el grafo aleatorio iguala al real, no afirmar atribución anatómica.

Guardar actividad por célula, estímulos, bump/lectura, acciones, verdad terreno y métricas, junto con commit, hashes de datos/configuración, semilla y versión de simulador. El error angular calculado para análisis no debe filtrarse a la lectura neuronal.

## 11. Riesgos y criterios de decisión

| Riesgo | Mitigación y condición de parada |
| --- | --- |
| Anotaciones no equivalentes entre fuentes | Fijar versión separada del snapshot; revisar aliases. No mezclar aristas hemibrain con FAFB |
| Modelo que funciona por el encoder o readout | Comparador analítico, readout sin acceso al objetivo, grafos sustitutos y pruebas sin recurrencia impuesta |
| Truncamiento destruye función | Cuantificar frontera; ampliar con justificación o reducir afirmación. No añadir conexiones ficticias |
| Parámetros libres dominan el resultado | Pocas ganancias, procedencia explícita, sensibilidad y calibración retenida |
| Anatomía con errores o conexiones débiles | Revisar estados y umbrales; reportar asimetrías originales en vez de corregirlas estéticamente |
| Confusión rumbo/desplazamiento | Separar ambas variables; dejar PFN/hΔB para extensión de deriva |
| Transferencia a dron no respaldada | Describir aplicación computacional simulada, con control convencional de bajo nivel |

**Viabilidad:** la extracción real y una prueba funcional acotada ya son reproducibles. El modelo PFL3 de referencia reproduce la transformación publicada, pero **todavía no está demostrada la ejecutabilidad funcional del subgrafo ponderado por FlyWire**, su estabilidad ni su desempeño. La consulta selectiva de coordenadas sinápticas por CAVE requiere un token; los archivos estáticos públicos mantienen una vía de adquisición.

## 12. Próximo paso definido en fase 0: M2

Esta etapa fue completada el 2026-09-13 con adquisición y reconstrucción anatómica reproducibles. Se descargaron las anotaciones fijadas, la conectividad agregada y la lista de IDs revisados; se verificaron hashes y esquema; y se produjo la selección EPG/Δ7/FC2/PFL3 con su frontera e informe. Véase [circuit-extraction.md](circuit-extraction.md).

Criterios de aceptación: cada nodo y arista tiene procedencia; ambos extremos se resuelven; nulos/discrepancias se informan; las rutas principales se contrastan; la lateralidad terminal y el estado del mapa columnar quedan explícitos; el grafo se regenera determinísticamente. Si falta una clase o una relación central, investigarlo antes de continuar, sin completar artificialmente la matriz.

El resultado habilitó la auditoría morfológica, el modelo PFL3 estacionario y el primer experimento ponderado por contactos descritos en [functional-mapping.md](functional-mapping.md), [model-assumptions.md](../model-assumptions.md) y [connectome-model-results.md](connectome-model-results.md). La prueba EPG posterior reveló que faltan coordenadas sinápticas y una dinámica Δ7 respaldada. **Todavía no se reconstruyó la dinámica completa EPG/Δ7 ni se comenzó el dron.**

## Fuentes científicas y de datos

Las citas siguientes son fuentes primarias o documentación de sus autores. Consulta: 2026-09-12. No se reproduce código ni figuras de terceros.

- **S1.** Mussells Pires, P., Zhang, L., Parache, V., Abbott, L. F. y Maimon, G. (2024). *Converting an allocentric goal into an egocentric steering signal*. Nature 626, 808–818. [Artículo y DOI](https://www.nature.com/articles/s41586-023-07006-3); [texto en PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC10881393/). Figuras 1–6 y métodos de modelo/perturbaciones.
- **S2.** Westeinde, E. A. et al. (2024). *Transforming a head direction signal into a goal-oriented steering command*. Nature 626, 819–826. [Artículo y DOI](https://www.nature.com/articles/s41586-024-07039-2). Figuras 1–4, datos extendidos y métodos.
- **S2c.** Westeinde et al. (2025). Corrección de S2. [Corrección](https://www.nature.com/articles/s41586-024-08245-8).
- **S3.** Seelig, J. D. y Jayaraman, V. (2015). *Neural dynamics for landmark orientation and angular path integration*. Nature 521, 186–191. [Artículo](https://www.nature.com/articles/nature14446).
- **S4.** Turner-Evans, D. B. et al. (2020). *The Neuroanatomical Ultrastructure and Function of a Biological Ring Attractor*. Neuron 108, 145–163.e10. [DOI](https://doi.org/10.1016/j.neuron.2020.08.006); [texto completo](https://pmc.ncbi.nlm.nih.gov/articles/PMC8356802/). Existe [errata de 2021](https://doi.org/10.1016/j.neuron.2021.04.016); revisar junto a métodos antes de trasladar parámetros.
- **S5.** Hulse, B. K. et al. (2021). *A connectome of the Drosophila central complex reveals network motifs suitable for flexible navigation and context-dependent action selection*. eLife 10:e66039. [Artículo](https://elifesciences.org/articles/66039). En particular circuitos de brújula, figuras 39, 63 y 73; distinguir propuesta funcional de anatomía.
- **S6.** Lyu, C., Abbott, L. F. y Maimon, G. (2022; online 2021). *Building an allocentric travelling direction signal via vector computation*. Nature 601, 92–97. [Artículo](https://www.nature.com/articles/s41586-021-04067-0).
- **S7.** Lu, J. et al. (2022; online 2021). *Transforming representations of movement from body- to world-centric space*. Nature 601, 98–104. [Artículo](https://www.nature.com/articles/s41586-021-04191-x).
- **S8.** Dorkenwald, S. et al. (2024). *Neuronal wiring diagram of an adult brain*. Nature. [Artículo](https://www.nature.com/articles/s41586-024-07558-y). Procedencia del connectoma y límites de reconstrucción.
- **S9.** Schlegel, P. et al. (2024). *Whole-brain annotation and multi-connectome cell typing of Drosophila*. Nature. [Artículo](https://www.nature.com/articles/s41586-024-07686-5).
- **S10.** Eckstein, N., Bates, A. S. et al. (2024). *Neurotransmitter classification from electron microscopy images at synaptic sites in Drosophila melanogaster*. Cell 187, 2574–2594.e23. [DOI](https://doi.org/10.1016/j.cell.2024.03.016).
- **S14.** Kathman, N. D., Lanz, A. J. y Nagel, K. I. (2026). *Neural dynamics for working memory and evidence integration during olfactory navigation in Drosophila*. Nature Communications 17, 9082. [Artículo](https://www.nature.com/articles/s41467-026-75945-2).
- **S15.** Lanz, A. J. et al. (2025). *Disinhibition of a recurrent attractor gates a persistent goal signal for navigation*. **Preprint**, versión consultada del 7 de octubre de 2025. [Texto y estado editorial](https://pmc.ncbi.nlm.nih.gov/articles/PMC12632281/).
- **S16.** *A vector-based strategy for olfactory navigation in Drosophila* (2026). Nature, DOI 10.1038/s41586-026-10827-7. [Registro PubMed](https://pubmed.ncbi.nlm.nih.gov/42486983/). Consulta limitada al resumen; lectura integral pendiente si se amplía a olfacción.
- **D1.** Codex/FlyWire. [FAQ oficial](https://codex.flywire.ai/faq), apartados datasets y acceso programático; [endpoint de catálogo consultado](https://codex.flywire.ai/api/download?dataset=fafb).
- **D2.** FlyWire Consortium. *FlyWire Whole-brain Connectome Connectivity Data*, versión 783.0. [Registro Zenodo 10676866](https://zenodo.org/records/10676866); [metadatos API](https://zenodo.org/api/records/10676866).
- **D3.** flyconnectome. [Anotaciones v2.1.0 fijadas por commit](https://github.com/flyconnectome/flywire_annotations/tree/ebd66db2596fcc39c6950fb54ea3efa00f7fe8a0); [diccionario de columnas de esa versión](https://github.com/flyconnectome/flywire_annotations/blob/ebd66db2596fcc39c6950fb54ea3efa00f7fe8a0/supplemental_files/Supplemental_files_columns.md); [changelog consultado en v3.1.0](https://github.com/flyconnectome/flywire_annotations/blob/8587524c1748ce5ef2080822a2fc890fc03bf597/README.md).
- **D4.** FlyWire. [Guía de versiones y anotaciones](https://home.flywire.ai/guidelines).
