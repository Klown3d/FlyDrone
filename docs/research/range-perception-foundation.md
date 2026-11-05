# Base de percepción de distancia

Actualizado: **2026-11-04**. Estado: **sensor y evasión conectados al control en desarrollo exploratorio; gate todavía no abierto**.

Se implementó un sensor planar de 31 rayos sobre 270°, alcance máximo de 6 m y ruido reproducible. Calcula la primera intersección con múltiples obstáculos circulares y entrega ángulos, distancias y máscara de impacto.

Es una capa de ingeniería explícita (`engineering_simulated_raycast`): no es una cámara, no reconoce objetos, no representa retina/lóbulos ópticos de *Drosophila* y no modifica el circuito FlyWire-grounded. El planificador sólo recibe pose observada y rayos; las posiciones reales de los obstáculos se usan para simular el sensor y evaluar colisión/holgura, no para escoger la trayectoria.

## Implementación actual

- mapa local cuantizado con memoria de 2,5 s;
- waypoints de seguimiento de contorno fijos en coordenadas globales, separados de la meta de misión;
- histéresis de lado, replanificación de waypoints bloqueados y liberación sostenida de la ruta directa;
- gobernador de velocidad basado en distancia;
- umbral de candidato coherente con distancia de parada y horizonte mínimo;
- rechazo de emergencia acotado a 0,90 m/s² para contrarrestar deriva hacia un obstáculo;
- telemetría de intervención, distancia mínima, puntos del mapa, fracción de velocidad y aceleración de seguridad.

Todos estos elementos son de ingeniería y se aplican por igual al controlador FlyWire-grounded y al convencional. No constituyen memoria, planificación o visión neuronal.

## Desarrollo v1–v6

Las tandas v1–v6 son exploratorias y no deben usarse como gate confirmatorio.

- v1 detectó los obstáculos, pero los ocho episodios colisionaron: faltaba frenado suficiente.
- v2 eliminó las colisiones en sus ocho episodios, a costa de bloqueo casi total.
- v3 añadió persistencia de lado; conservó bloqueos y registró colisiones aisladas.
- v4 fijó el waypoint en el mundo y eliminó el objetivo móvil, pero mantuvo una contradicción: podía generar un waypoint dentro de la zona donde el gobernador impedía avanzar. Hubo 0/8 éxitos de desarrollo y una colisión convencional.
- v5 hizo coherentes selección, parada y horizonte. Mejoró el avance en algunos casos, pero mantuvo 0/8 éxitos; FlyWire no colisionó y el convencional colisionó una vez bajo viento. La comparación entre controladores no es concluyente por el tamaño y por tratarse de desarrollo.
- v6 añadió rechazo lateral de emergencia. En ocho episodios hubo 0 colisiones y holgura mínima positiva por grupo entre 0,334 y 0,605 m, pero 0/8 éxitos: patrulla completó 0 metas y exploración tuvo mediana de 2 metas por grupo.

La repetición exacta del episodio convencional que había colisionado en v5 cambió de una holgura mínima de **−0,713 m** a **+0,437 m**, sin colisión. Es evidencia causal local de que el rechazo resuelve ese choque concreto, no prueba de seguridad general. El episodio sólo completó 2 metas y estuvo detenido 60,04% del tiempo.

## Diagnóstico vigente

El problema de seguridad por deriva lateral quedó corregido en el caso reproducido. Entre v7 y v10 se incorporaron seguimiento tangencial de contorno, replanificación de objetivos bloqueados y liberación tras 0,6 s de corredor directo libre. En la comparación nominal FlyWire, patrulla progresó de 0 metas en v7 a 3 en v10; el caso con viento seguía en 0.

v11 acortó la rampa de desaceleración de 2,0 a 1,5 m sin cambiar la distancia de parada de 0,90 m. El caso con viento pasó a 4 metas y éxito de desarrollo para ambos controladores, con 0 colisiones. El bloqueo mediano bajó a 1,3% FlyWire y 1,7% convencional. El caso nominal quedó por debajo del criterio: 3 metas FlyWire y 1 convencional.

v12 mostró que exploración ya no estaba inmovilizada, pero sólo completaba 2–3 metas. La causa era el orden aleatorio de las 25 celdas, que producía saltos de hasta casi 10 m. Se añadió una configuración nueva, sin modificar la histórica, que selecciona la celda no visitada más cercana con desempate sembrado.

v14, con esa política y un límite exploratorio de velocidad de 0,75, obtuvo **4/4 éxitos de desarrollo**, 9–13 metas, 0 colisiones y bloqueo mediano de 0,6% FlyWire / 1,0% convencional. La holgura mínima FlyWire fue sólo **0,032 m**, por lo que el candidato no está listo para congelarse. La mejora de secuenciación es una propiedad de la capa de ingeniería y no evidencia a favor del connectoma.

## Desarrollo de margen v15–v25

Se fijó un criterio de desarrollo de **0,15 m de holgura mínima**, además de cero colisiones. Los reportes nuevos guardan el hash efectivo de la configuración y hashes de sensor, evasión, comportamiento y fuentes relevantes.

- v15, con velocidad 0,65 y sensor de 270°, obtuvo 4/8 éxitos y reprodujo una colisión trasera convencional de −0,224 m.
- v16 reemplazó el sensor por 41 rayos únicos sobre 360°. La repetición exacta pasó a +0,165 m y éxito; es un LiDAR 2D simulado de ingeniería, no visión de mosca.
- v17 unificó ambos modos con el sensor omnidireccional: 7/8 éxitos, cero colisiones y ambos controladores pasaron patrulla. El único fallo fue FlyWire exploración nominal con 0,142 m, 7,7 mm bajo el criterio.
- v18–v19 aumentaron distancia de parada. El caso aislado mejoró, pero la matriz cayó a 4/8 y produjo nuevos acercamientos; se descartó.
- v20–v22 probaron fuerza constante y rechazo condicionado por velocidad. Las reproducciones aisladas mejoraron, pero la matriz v22 cayó a 4/8 e incluyó una colisión convencional; se descartaron.
- v23 añadió sesgo radial hacia afuera al contorno. En el caso aislado redujo la holgura a 0,049 m al modificar la ruta entre varios obstáculos; se descartó.
- v24–v25 aumentaron la reserva lateral de puntos mapeados. El caso aislado pasó con 0,165 m y 20 metas, pero la matriz v25 sólo logró 5/8 e introdujo una colisión leve; se descartó como solución general.

Estas pruebas muestran que optimizar un umbral escalar sobre los mismos dos cursos cambia la trayectoria y traslada el fallo entre obstáculos. El mejor candidato unificado sigue siendo v17 (7/8, cero colisiones), pero tampoco está listo para un gate.

El próximo rediseño debe representar explícitamente el volumen del vehículo: inflar los impactos del mapa por `radio del dron + margen requerido` y planificar sobre esa ocupación, o aplicar una barrera geométrica predictiva. Debe usar únicamente rayos, pose y velocidad observados; la geometría real de los obstáculos seguirá reservada para evaluación.

La base de esa barrera se implementó en `range_safety_barrier.py`: proyecta 0,8 s del movimiento, trata cada impacto observado con un despeje de 0,40 m y produce una corrección acotada antes de invadirlo. Está conectada de forma opcional al planificador y expone telemetría propia; las configuraciones históricas siguen sin activarla.

## Desarrollo de barrera v26–v28

La integración se probó primero en dos reproducciones exactas, cambiando únicamente la barrera:

- v26 corrigió el único fallo de v17: FlyWire exploración nominal pasó de 0,142 m a **0,196 m**, completó 15 metas y no colisionó. La barrera estuvo activa 21,29% del vuelo.
- v27 mantuvo resuelto el choque convencional con viento: **0,243 m**, 13 metas y cero colisiones. La barrera estuvo activa 20,22%.

La matriz unificada v28 mostró que esos rescates locales **no generalizan todavía**. Terminó 6/8, sin colisiones. El convencional aprobó sus cuatro vuelos. FlyWire falló los dos vuelos con viento: patrulla completó 3/4 metas y exploración 10 metas; en esta última la holgura real cayó a **0,039 m**. La barrera sí detectó riesgo (despeje proyectado mínimo 0,00048 m y fracción de velocidad mínima 0), pero la corrección acotada no impuso una restricción dura sobre la aceleración nominal y el viento.

Esto separa dos problemas. La discretización de impactos deja huecos entre muestras de una misma superficie, y la corrección aditiva actual puede competir con navegación, deriva y perturbaciones. El siguiente diseño no debe ser otro ajuste escalar: debe construir ocupación continua a partir de impactos vecinos o proyectar el mando nominal sobre una restricción de barrera que garantice no acercamiento. Seguirá usando sólo observaciones; la geometría real de obstáculos continuará reservada para evaluación.

## Diagnóstico FlyWire v29–v34

Se aisló además una interacción entre la salida traslacional PFN→hDeltaB y la navegación entre obstáculos. En el par de fallos FlyWire con viento de v28, la ablación hDeltaB v29 pasó 2/2: patrulla subió de 3 a 4 metas y exploración de 10 a 12, con 0,154 m de holgura. Esto no demuestra que hDeltaB sea inútil; demuestra que su readout actual no se integra de forma robusta con evasión.

- v30 suspendió hDeltaB sólo durante evasión. Recuperó patrulla pero causó una colisión en exploración; se descartó la conmutación abrupta.
- v31 barrió ganancias continuas 0,5, 1,0 y 1,5 s⁻¹. Ninguna pasó ambos modos: el resultado depende de la trayectoria y no justifica elegir un valor post-hoc.
- v32 conectó el gobernador de confianza ya existente. No resolvió el par y produjo una colisión en exploración; su criterio de confianza no captura esta interacción.
- v33 probó la ablación en la matriz completa. FlyWire pasó 3/4: mejoró ambos vuelos con viento, pero patrulla nominal cayó a 2 metas porque conservaba amortiguación lateral 0,25 s⁻¹ diseñada para coexistir con hDeltaB.
- v34 mantuvo EPG–Δ7–PFL3/PFL2 para rumbo, steering y avance, dejó PFN→hDeltaB ablado y usó la misma amortiguación lateral de bajo nivel 2,0 s⁻¹ del estabilizador convencional. Pasó **4/4**, con cero colisiones, 12–13 metas en exploración, 4/4 metas en patrulla y holgura mínima global **0,264 m**.

v34 es el mejor candidato FlyWire para este bloque de obstáculos, pero sigue siendo desarrollo sobre escenarios conocidos. Su afirmación válida es modular: el steering y avance FlyWire-grounded funcionan con una capa convencional de estabilización lateral. No prueba todavía que hDeltaB pueda controlar compensación de deriva de forma segura entre obstáculos ni que FlyWire supere al baseline.

## Comparación pareada v35

v35 ejecutó v34 y el baseline convencional dentro del mismo proceso, con percepción, barrera, estabilización lateral, escenarios y semillas idénticos. Ambos lograron **4/4**, cero colisiones y cero escapes.

- Exploración: FlyWire completó una mediana de 12,5 metas frente a 13,0 convencional; cobertura 0,52 frente a 0,48; holgura mínima 0,264 m frente a 0,243 m.
- Patrulla: ambos completaron 4 metas; cobertura FlyWire 0,56 frente a 0,64; holgura mínima 0,288 m frente a 0,366 m.
- FlyWire permaneció detenido 3,38% del tiempo en patrulla frente a 1,13% convencional. La intervención mediana de la barrera fue menor en FlyWire en ambos modos, pero con cuatro vuelos no permite una conclusión poblacional.

El resultado elimina la inferioridad evidente observada en v28, pero no demuestra equivalencia estadística ni superioridad. Los escenarios son conocidos y el tamaño es mínimo. v35 cierra el ajuste sobre este conjunto; los parámetros de v34 no deben cambiarse después de observar una evaluación nueva.

## Lo que falta antes de un gate

1. sustituir la barrera aditiva de puntos por ocupación continua observada y una restricción explícita sobre el mando nominal;
2. conservar el umbral de 0,15 m sin reajustarlo después de observar resultados;
3. evaluar patrulla y exploración juntas con una única configuración;
4. medir por separado cuánto tiempo dominan contorno, gobernador, geofence y rechazo de emergencia;
5. congelar código, parámetros, métrica primaria y criterios de aprobación;
6. generar escenarios y semillas nuevos que no se usen durante el desarrollo;
7. ejecutar una evaluación sellada y reportar distribuciones, no vuelos elegidos.

Una vía visual connectómica sería un proyecto científico separado. No se inferirá visión biológica a partir de este raycast.
