# Hoja de ruta de FlyDrone

## Objetivo del proyecto

Construir y evaluar un sistema de **steering autónomo condicionado por una meta dada** para un dron simulado, cuyo control de alto nivel provenga de un modelo computacional de circuitos del *central complex* de *Drosophila melanogaster*, reconstruido a partir de conectividad FlyWire y restringido por evidencia experimental. La selección autónoma de metas queda fuera del alcance del núcleo.

La red neuronal decidirá orientación, dirección de desplazamiento, steering, intensidad de corrección y, progresivamente, velocidad de navegación. La estabilización de vuelo, actitud, mezcla de motores y mecanismos de seguridad permanecerán en un controlador convencional.

## Arquitectura final prevista

```text
Sensores simulados
  heading · velocidad angular · flujo óptico · landmarks · viento
                              │
                              ▼
EPG · PEN · PEG · Δ7 — brújula y actualización de orientación
                              │
                              ▼
PFNd · PFNv · hΔB — dirección real de desplazamiento y deriva
                              │
                              ▼
FC2 / patrón de meta — bump objetivo suministrado por una entrada de ingeniería
                              │
                              ▼
PFL3L/R — dirección de giro · PFL2 — magnitud de giro y avance
                              │
                              ▼
Comandos de navegación de alto nivel
                              │
                              ▼
Estabilizador convencional — actitud, altura y motores
```

## Estado actual

**Alcance activo acordado:** robustez y aplicación 3D nativa. Presentación,
publicación, videos, empaquetado y dron físico quedan pospuestos. Véanse los
[criterios concretos de esta etapa](active-scope.md).

Avance reciente: [sensibilidad local](integrated-v4-local-sensitivity.md) de
28 vuelos sin fallos al variar ganancias y τ ±20%; [piloto OOD](ood-pilot-results.md)
con 5/6 FlyWire frente a 6/6 convencional, conservando el fallo por pérdidas
largas. El [comparador 3D nativo](../gate-replay-3d.md) permite observar los
tres gates de steering y los seis pares OOD desde la aplicación principal.
Superó una prueba de 16 vuelos completos con eventos reales de interfaz; permite
seguir ambos drones e inspeccionar tipo, root ID y actividad de cada neurona.

**Etapa actual: Fases 9, 10 y 11 cerradas para el alcance integrado v4.** El resultado y sus límites se consolidan en el [análisis final integrado](final-analysis-integrated-v4.md). OOD amplio, sensibilidad global y brújula v5 son trabajo futuro, no resultados atribuidos retroactivamente a v4.

El fallo OOD preservado ya fue reproducido exactamente y sometido a oráculos
pareados: heading verdadero recuperó la llegada, mientras velocidad verdadera
por sí sola no. El diagnóstico local queda cerrado; falta comprobar si el patrón
se generaliza en una matriz nueva antes de diseñar y evaluar una brújula v5.

El controlador integrado v4 logró 28/30 llegadas, frente a 30/30 para los controles directo y convencional. No se sostiene superioridad de rendimiento. Sin embargo, cuatro gates prospectivos separados mostraron dependencia de partner identity en PFN→hΔB, EPG→Δ7, Δ7→PFL3 y el steering conjunto: el intacto logró 12/12 en cada gate y ninguna de 80 redes nulas emparejadas lo igualó. Véase la [síntesis de atribución connectómica](connectome-attribution-synthesis.md).

Ya existe un dron 6DoF controlado en yaw por una ruta EPG–Δ7–FC2–PFL3 provisional. La brújula recurrente está implementada y el modelo literal mostró una actualización angular insuficiente. Se construyó una variante con simetría regularizada que alcanzó, en **validación reutilizada durante el desarrollo**, error mediano de 4,42°, dirección correcta del 100% y respuesta monotónica. Ese número no es un resultado final independiente. Su circularización es una transformación de ingeniería y no anatomía FlyWire literal.

La extracción PB→EB recuperó desplazamientos laterales opuestos de aproximadamente 49–55° y permitió integrar v4 con un operador PEN_a derivado de contactos. La circularización relocaliza 58–60% del peso PEN y v4 superó a 30/30 nulos de fase bajo parámetros congelados. En la prueba prospectiva 6DoF logró 30/30 llegadas y 23,68° de error mediano, pero falló 2/4 criterios por errores de cola de hasta 142,86° y mejora insuficiente frente a sample-and-hold. Los observadores convencionales de giroscopio quedaron cerca de 2,3–2,5°.

La extensión PFL2 incorpora 12 neuronas reales y sus contactos Δ7/FC2B/C. El gate de steering congelado alcanzó 36/36 metas por condición y mejoró 0,386 s la llegada mediana pareada. El gate separado de avance alcanzó 30/30 metas con PFL2 y con el control angular, con sólo 0,022 s de costo mediano. Ninguno de 30 nulos de fase reprodujo la correlación funcional FlyWire, aunque fórmulas angulares obtienen navegación prácticamente equivalente. PFL2 queda validada como señal funcional del modelo, sin evidencia de superioridad frente a readouts convencionales.

## Controles metodológicos obligatorios

1. Auditar el mapa PEN antes de aceptar la regularización como solución.
2. Medir cuánto cambia cada matriz al circularizarla: correlación, error normalizado, fracción de peso desplazado y estructura por desfase.
3. Aplicar exactamente la misma regularización a 30 grafos nulos con tamaño, pesos y grados comparables.
4. Tratar todos los rumbos y velocidades ya observados como desarrollo/validación.
5. Generar una prueba prospectiva nueva desde una semilla registrada y ejecutarla una sola vez después de congelar parámetros.
6. Comparar con proporcional y PID ya implementados, y añadir un estimador convencional fuerte —filtro complementario y, si el tiempo lo permite, EKF— con los mismos sensores y semillas.
7. Separar `meta suministrada` de `selección de meta`; FlyDrone demuestra steering hacia una meta dada.
8. Registrar predicciones, métrica primaria, refutaciones y análisis antes de la evaluación final en `PREREGISTRO.md`.

## Fase 0 — Hipótesis y selección del circuito

**Estado:** completada.

### Trabajo realizado

- Definición de la hipótesis y sus variables.
- Revisión del *central complex*.
- Selección de la ruta de orientación y steering.
- Identificación de EPG, Δ7, PEN, PEG, FC2 y PFL3.
- Separación entre evidencia experimental, inferencias y decisiones de ingeniería.

### Criterio de salida

Circuito primario seleccionado, datos accesibles y función respaldada por fuentes primarias.

## Fase 1 — Adquisición y trazabilidad FlyWire

**Estado:** completada para el circuito inicial; se ampliará al incorporar nuevas poblaciones.

### Trabajo realizado

- Dataset FAFB/FlyWire materialización 783 registrado.
- Identidades neuronales, conexiones, conteos sinápticos y esqueletos descargados.
- Manifiesto con versiones, hashes y procedencia.
- 286 esqueletos completos disponibles para visualización, incluidos PFL2, PFNd, PFNv y hΔB.

### Pendiente

- Incorporar PFNd, PFNv y hΔB cuando se amplíe el circuito.
- Registrar las nuevas extracciones sin mezclar versiones.

### Criterio de salida

Cada dato usado por el modelo puede rastrearse hasta su archivo, versión y fuente.

## Fase 2 — Reconstrucción del subgrafo

**Estado:** completada para la ruta inicial.

### Trabajo realizado

- Grafo dirigido y ponderado.
- Clasificación por tipo neuronal, lado y neuropilo.
- Transferencias de contactos por compartimento.
- Análisis de recurrencia, lateralidad y desfases de fase.
- Visualización de morfologías completas.

### Pendiente

- ~~Separar correctamente la entrada PB y la salida EB de PEN.~~ Completado; recupera desplazamientos laterales opuestos de aproximadamente 49–55°.
- Revisar la asignación de columnas y glomérulos de PEN célula por célula antes de congelar v4.
- Verificar fases individuales con evidencia anatómica adicional.
- ~~Extraer PFL2 y sus conexiones Δ7/FC2 relevantes.~~ Completado.
- Extraer PFN/hΔB.

### Criterio de salida

El grafo reproduce las poblaciones y desplazamientos anatómicos esperados, con incertidumbres explícitas.

## Fase 3 — Modelo neuronal mínimo

**Estado:** completada parcialmente.

### Trabajo realizado

- Modelo de tasas para EPG, Δ7, PEG y PEN.
- Bump de actividad persistente.
- Lectura circular de fase, resultante y contraste.
- Anclaje entre fase interna y rumbo externo.
- Ablaciones de Δ7, recurrencia, PEG y PEN.
- Pruebas contra pesos y fases aleatorizados.

### Resultado abierto

La matriz FlyWire cruda corregida por compartimentos mantiene actividad, pero todavía no supera todos los criterios. La versión v4 con simetría regularizada actualiza la fase en ambos sentidos usando la diferencia PEN_a PB→EB, aunque modifica la heterogeneidad anatómica.

### Criterio de salida definitivo

- Signo correcto en ambos sentidos.
- Respuesta monotónica con la velocidad.
- Error mediano menor de 10° en una prueba prospectiva no observada.
- Bump estable durante ausencia temporal de señal.
- Parámetros congelados antes de la evaluación cerrada.

## Fase 4 — Brújula neuronal integrada

**Estado:** cerrada como prototipo funcional con resultado prospectivo parcial. La variante v4 corregida PB→EB y regularizada está integrada y visible, pero no superó el gate prospectivo completo y no se considera una brújula validada.

### Tareas

1. ~~Corregir PEN como transferencia PB→EB y verificar lateralidad.~~ Completado.
2. Repetir el desarrollo del modelo literal con la extracción PB→EB.
3. ~~Cuantificar cuánto modifica la circularización corregida y contrastarla contra 30 grafos nulos regularizados.~~ Completado en desarrollo: cambio grande, pero 0/30 nulos igualan v4.
4. ~~Integrar `phase_compass_cross_compartment_v4` como variante etiquetada.~~ Completado para desarrollo y visualización.
5. Mantener el modelo FlyWire literal como condición separada.
6. Añadir en la aplicación:
   - rumbo real;
   - rumbo sensorial;
   - rumbo neuronal;
   - fase del bump;
   - resultante y contraste;
   - estado de señal externa.
7. Añadir un botón para interrumpir y restaurar la señal de rumbo.
8. Guardar la actividad neuronal completa junto con cada trayectoria.
9. ~~Congelar parámetros y ejecutar una sola prueba prospectiva con semilla registrada.~~ Ejecutada: 2/4 criterios, gate global fallido.

### Criterio de salida

La brújula controla el rumbo del dron y supera sample-and-hold en parte de los casos, pero el criterio definitivo no se alcanzó. Una futura v5 requerirá un protocolo nuevo; Fase 5 puede continuar sin presentar v4 como brújula validada.

## Fase 5 — Steering adaptativo PFL3/PFL2

**Estado:** completada como módulo funcional provisional; gate prospectivo 6/6 aprobado y controles de atribución ejecutados.

### Tareas

1. ~~Extraer PFL2 y sus conexiones relevantes.~~ Completado: 12 PFL2, 1.332 contactos Δ7 y 1.177 FC2B/C usados.
2. ~~Reconstruir Δ7/FC2 → PFL2 sin inventar aristas.~~ Completado como modelo de contactos normalizados.
3. ~~Representar la meta como una entrada separada y documentada.~~ Completado; continúa siendo entrada de ingeniería.
4. ~~Usar PFL3L/R para determinar la dirección del giro.~~ Completado.
5. ~~Probar en desarrollo que PFL2 aumenta la magnitud de corrección cuando el error es grande.~~ Completado: −0,725 s en heading y −0,819 s en 6DoF.
6. ~~Comprobar que quitar PFL2 enlentece correcciones grandes sin invertir el sentido indicado por PFL3.~~ Cumplido en desarrollo; 0 inversiones atribuibles a PFL2.
7. ~~Visualizar por separado PFL3L, PFL3R y PFL2.~~ Completado en la aplicación nativa.
8. ~~Congelar y ejecutar un conjunto prospectivo con ruido, retraso y ráfagas.~~ Completado: 72 episodios, 36/36 por condición y mejora mediana de 0,386 s.
9. ~~Comparar conectividad PFL2 contra fases barajadas y un control de ganancia sin connectoma.~~ Completado: 0/30 nulos igualaron la correlación FlyWire; el control angular rindió casi igual en navegación.

### Prueba principal

Cambios de meta de 30°, 90° y 180°, midiendo tiempo de recuperación, oscilación, sobrepaso y falso equilibrio cerca de la antimeta.

### Criterio de salida

El criterio se reprodujo prospectivamente: quitar PFL2 enlenteció las correcciones grandes sin alterar el sentido de PFL3. La organización de fases superó 30 nulos, pero la navegación fue casi indistinguible de una función angular diseñada a mano. La fase se cierra con esa limitación explícita.

## Fase 6 — Dirección de desplazamiento y compensación de deriva

**Estado:** modelo aislado e integración 6DoF aprobados prospectivamente.

### Circuito

PFNd/PFNv → hΔB, con entradas de heading y movimiento egocéntrico.

### Núcleo obligatorio y acotado

1. ~~Extraer las neuronas y transferencias FlyWire.~~ Completado: 202 neuronas, 6.196 pares y 53.999 sinapsis.
2. ~~Codificar velocidad frontal y lateral.~~ Completado en aislamiento mediante cuatro proyecciones publicadas; es una abstracción de ingeniería.
3. ~~Obtener estas señales inicialmente del estado simulado.~~ Completado y luego reemplazado en la aplicación por velocidad estimada desde posiciones observadas.
4. ~~Añadir ruido, sesgo y demora a esas velocidades.~~ Completado prospectivamente, incluyendo pérdida temporal de 3,5 s.
5. ~~Decodificar la dirección allocéntrica de desplazamiento.~~ Completado y aprobado prospectivamente en aislamiento.
6. ~~Comparar rumbo corporal contra trayectoria real.~~ Completado en el diagnóstico integrado.
7. ~~Usar la diferencia para compensar viento y deriva lateral.~~ Aprobado prospectivamente: 30/30 llegadas y 75,0% menos desvío frente a ausencia; con velocidad estimada, 28/30 y 66,9% menos desvío.

Este núcleo tendrá un máximo de dos ciclos de implementación y uno de corrección. Si no supera su criterio tras ese límite, se congelará el resultado y se continuará con ablaciones e informe.

### Criterio de salida

El sistema detecta que el dron se desplaza en una dirección diferente a la que apunta y genera una corrección coherente.

La extracción confirma 15.487 sinapsis PFNd→hΔB y 2.720 PFNv→hΔB, con cobertura de las 18 hΔB por ambas corrientes. El mapa recuperó ocho columnas PFN, doce hΔB y el desplazamiento de medio FB. El candidato obtuvo 6,32° de error mediano en desarrollo y superó 30 nulos de fase. En el gate prospectivo procesó 720 transformaciones nuevas, aprobó 6/6 criterios y obtuvo 6,09° ideal y 8,38° global bajo ruido. [Auditoría de Fase 6](travel-direction-extraction.md).

La integración 6DoF de desarrollo comparó hΔB, ausencia de compensación y velocidad lateral convencional. hΔB alcanzó 6/6 metas frente a 0/6 sin compensación y redujo 66,8% el desvío máximo mediano. El convencional también obtuvo 6/6 y mantuvo una ventaja pequeña. [Integración de deriva](travel-direction-drift-integration.md).

## Fase 7 — Extensiones sensoriales opcionales

**Estado:** en curso; velocidad por posición integrada y aprobada prospectivamente.

**Condición de inicio:** sólo se abre si el núcleo PFN/hΔB está congelado y las ablaciones principales están preparadas.

### Tareas opcionales

- ~~Landmark explícito para corregir la fase EPG.~~ Integrado como abstracción de bearing conocido; visión neuronal real pendiente.
- Flujo óptico frontal y lateral.
- Velocidad angular inercial.
- Señales equivalentes a flujo de aire cuando el experimento lo requiera.
- Confianza por modalidad y recuperación ante conflictos sensoriales.
- Documentación de cada codificador como respaldo biológico, abstracción computacional o conveniencia de ingeniería.

### Criterio de salida

La navegación no depende de acceso directo al estado perfecto del simulador y tolera la pérdida temporal de al menos una modalidad.

La interfaz explícita estima velocidad desde posiciones observadas y alimenta PFN/hΔB sin usar la velocidad verdadera. En el gate prospectivo obtuvo 28/30 llegadas, redujo 66,9% la deriva frente a ausencia y toleró 14/15 pérdidas de 3,5 s. [Interfaz sensorial](travel-velocity-sensor.md).

## Fase 8 — Navegación neuronal de alto nivel completa

**Estado:** cerrada para la versión v4 como controlador simulado de alto nivel. El gate integrado alcanzó 28/30, frente a 30/30 directo y convencional; no demuestra superioridad convencional.

### Responsabilidades neuronales previstas

- estimación de orientación;
- dirección real de desplazamiento;
- comparación entre rumbo y meta;
- selección del sentido de giro;
- intensidad adaptativa;
- velocidad de avance de alto nivel;
- compensación de deriva;
- recuperación ante cambios o pérdida de señales.

PFL2 ya reemplaza el frenado angular para la velocidad de avance en 6DoF. El gate prospectivo obtuvo 30/30 llegadas en ambas condiciones y aprobó 6/6 criterios, con un costo de sólo 0,022 s. [Avance PFL2](pfl2-advance.md).

El primer banco con pérdidas sensoriales superpuestas expuso ruido excesivo en la velocidad derivada de posición. Tras corregir readquisición y usar una ventana de 200 ms, el sistema completo pasó de 4/12 a 12/12 en los casos de desarrollo. Sigue siendo 5,73 s más lento que el convencional y la brújula v4 conserva errores grandes durante cortes. [Diagnóstico integrado](integrated-controller-development.md).

El gate nuevo obtuvo 22/30 llegadas completas frente a 30/30 convencionales. Sin hΔB cayó a 0/30; sin PFL2 mantuvo 22/30. Pasaron los criterios de desvío, dependencia de hΔB, equivalencia de éxitos sin PFL2 y saturación; fallaron robustez total, escenario fuerte, déficit convencional y tiempo. No se congela todavía el controlador final.

El diagnóstico causal posterior identificó la velocidad estimada como cuello de botella. Una confianza graduada sólo cambió 7/12 a 8/12 y fue rechazada. La fusión con acelerómetro corporal simulado, ruido, sesgo y heading estimado alcanzó 11/12 frente a 6/12 con posición sola y 12/12 convencionales; redujo el error hΔB en los 12 pares. Se promueve como candidato de desarrollo, no como resultado confirmatorio. [Desarrollo inercial](inertial-velocity-development.md).

El control directo perfectamente emparejado alcanzó 12/12 igual que FlyWire y fue ligeramente mejor en tiempo, eficiencia y desvío, resultado que se repitió con fuerza específica corporal 3D. No se sostiene una ventaja de rendimiento del connectoma. Los nulos PFN→hΔB ya están integrados: el intacto obtuvo 12/12, los nulos generales 0/12, 5/12 y 0/12, y los nulos que preservan tipo y lado 3/12, 10/12 y 2/12. Esto aporta evidencia de desarrollo favorable a la organización interna, todavía no confirmatoria. [Control emparejado](matched-drift-readout.md), [atribución al connectoma](connectome-null-development.md). El [preregistro confirmatorio](confirmatory-gate-preregistration-draft.md) continúa en borrador hasta congelar casos y semillas nuevos.

Una brújula híbrida posterior redujo el error durante dropout a cerca de 4°, pero logró 8/12 frente a 10/12 de v4. Atenuar también la corrección hΔB empeoró el desvío y fue descartado. La variante híbrida no se promueve; el próximo diagnóstico se concentra en PFN/hΔB durante la transición de velocidad. [Resultado híbrido](hybrid-compass-development.md).

### Responsabilidades convencionales permanentes

- estabilización de roll y pitch;
- control de altura;
- mezcla de motores;
- límites físicos;
- parada y failsafes;
- evitación de emergencia.

### Criterio de salida

La red determina todos los comandos de navegación de alto nivel y el estabilizador sólo los convierte en movimiento físicamente estable.

## Fase 9 — Evaluación y atribución biológica

**Estado:** cerrada para v4. Atribución prospectiva, sensibilidad local y piloto OOD están completos; sensibilidad global y OOD confirmatorio pasan a una futura v5.

Los cuatro gates usaron 20 redes nulas y 12 casos pareados por condición. El intacto obtuvo 12/12 en cada uno; ninguna de 80 nulas lo igualó y cada gate alcanzó `p=0,0476`. Las proyecciones específicas se alteraron por separado manteniendo intacta la otra etapa de steering. Estos resultados apoyan dependencia computacional de partner identity, no causalidad biológica ni superioridad frente a control convencional. [Síntesis completa](connectome-attribution-synthesis.md).

El gate PFN→hDeltaB ejecutó los 800 vuelos fijados: 100 casos nuevos para el circuito intacto, cinco reconexiones que preservan tipo/lado/grados/pesos, el sustituto directo y el convencional. El intacto obtuvo 95/100 frente a una mediana nula de 38/100, quedó a 2 puntos del directo y no produjo colisiones ni saturación. Aprobó los cuatro criterios jerárquicos. Véanse el [preregistro congelado](confirmatory-gate-preregistration.md), la [preparación de ejecución](confirmatory-execution-readiness.md) y el [resultado final](confirmatory-gate-results.md).

### Experimentos

- navegación ideal;
- ruido y demora sensorial;
- pérdida de heading;
- viento lateral y ráfagas;
- cambios de meta;
- deriva sin GPS;
- obstáculos;
- combinaciones de perturbaciones.

### Controles convencionales

- proporcional con el mismo heading observado;
- PID con el mismo heading observado;
- filtro complementario de heading + proporcional/PID;
- EKF + PID si queda dentro del alcance, con el mismo presupuesto explícito de ajuste;
- condiciones equivalentes con señal de heading interrumpida.

Todas las condiciones compartirán sensores, ruido, demoras, semillas y métricas.

### Ablaciones obligatorias

- sin Δ7;
- sin recurrencia;
- sin PEN;
- sin PFL2;
- sin PFN/hΔB;
- conexiones barajadas;
- fases barajadas;
- grafo aleatorio con tamaño y grado comparables;
- 30 grafos nulos regularizados con exactamente el mismo procedimiento aplicado a v3;
- FlyWire literal frente a modelo regularizado.

Antes de estas corridas se medirá la distancia entre matriz original y regularizada y se congelará `PREREGISTRO.md`.

### Métricas

- éxito y colisiones;
- error de rumbo y desplazamiento;
- tiempo hasta la meta;
- eficiencia de trayectoria;
- oscilación y sobrepaso;
- recuperación tras perturbaciones;
- latencia y factor de tiempo real;
- unidades y conexiones activas.

### Criterio de salida

Los resultados muestran qué capacidades dependen de la arquitectura neuronal, cuáles provienen de capas de ingeniería y cuáles no superan controles convencionales.

## Fase 10 — Aplicación final y presentación

**Estado:** cerrada para el alcance activo. Aplicación nativa estable, replay, inspección neuronal, vectores y exportación científica verificados. Instalador y presentación continúan pospuestos.

### Tareas

- Selector de modelo literal o regularizado.
- ~~Panel de sensores y señales perdidas.~~ Disponible con estado y errores.
- ~~Actividad 3D por población y neurona.~~ Disponible con selección blanca,
  tipo, root ID y valor temporal; no implica propagación por ramas.
- ~~Vectores de heading, desplazamiento y meta.~~ Disponibles. No se inventa un estado recurrente temporal EPG ausente de las trazas; se muestra la actividad algebraica reconstruida y se etiqueta como tal.
- ~~Reproducción, pausa y comparación de ensayos confirmatorios guardados.~~ Disponible en el visor nativo; falta integrarlo como panel dentro de la aplicación principal.
- ~~Exportación de métricas, trayectorias y actividad confirmatoria.~~ La vista interactiva exporta PNG, snapshot A/B, 286 neuronas por condición y metadata con hashes.
- Etiquetas visibles de `simulado`, `FlyWire-grounded` y `engineering`.
- Instalador o paquete ejecutable reproducible.

### Criterio de salida

Una persona puede ejecutar un experimento, observar el circuito, guardar los resultados y entender qué controla cada componente sin inspeccionar el código.

## Fase 11 — Análisis final

**Estado:** cerrada para v4 con el documento [final integrado](final-analysis-integrated-v4.md). OOD amplio, sensibilidad global y baseline EKF/PID totalmente emparejado quedan como requisitos de v5.

### Entregables

- ~~análisis estadístico confirmatorio PFN→hΔB;~~
- ~~figuras y tablas confirmatorias;~~
- ~~resultados de ablación/nulos PFN→hΔB;~~
- ~~limitaciones de v1;~~
- ~~guía de reproducción y preservación de v1;~~
- ~~declaración precisa de lo demostrado en v1;~~
- posibles pasos hacia un dron físico manteniendo el controlador de vuelo y los failsafes independientes.

## Orden de ejecución inmediato

1. ~~Cerrar el análisis del gate PFN→hΔB, auditar sus cinco fallos y preservar v1.~~ Completado.
2. ~~Congelar y evaluar v4 como controlador integrado de alto nivel.~~ Completado: 28/30 frente a 30/30 directo y convencional.
3. ~~Ejecutar gates prospectivos de partner identity para PFN→hΔB y steering.~~ Completado, incluidas EPG→Δ7 y Δ7→PFL3 por separado.
4. ~~Ejecutar un piloto fuera de distribución y localizar su fallo principal.~~
   Completado en seis casos pareados; el oráculo de heading rescató el único
   fallo en un diagnóstico local. Queda diseñar una evaluación amplia y sellada.
5. ~~Barrer localmente ganancias y constantes de tiempo ±20%.~~ Completado como
   diagnóstico pequeño; una sensibilidad amplia sigue pendiente.
6. Comparar el sistema completo con PID y un estimador convencional fuerte usando exactamente las mismas observaciones.
7. Decidir si se incorpora flujo óptico explícito o si se conserva la posición observada como interfaz declarada.
8. ~~Integrar comparación intacto/nulo en la aplicación.~~ Completado con cámaras,
   inspección neuronal, ablaciones y prueba repetida. Quedan más trazas pareadas;
   empaquetado y presentación permanecen pospuestos por alcance.

## Definición de éxito del proyecto

FlyDrone será exitoso si demuestra que un modelo de circuito identificable y trazable a FlyWire puede producir steering autónomo de alto nivel hacia una meta suministrada en un dron simulado, que sus señales internas corresponden a variables interpretables de orientación y movimiento, y que ablaciones preregistradas alteran el comportamiento de la manera prevista.

No es necesario que supere a todos los controladores convencionales en precisión absoluta. Sí debe demostrar una capacidad útil, medible y atribuible al circuito, sin presentar transformaciones de ingeniería como propiedades biológicas.
## Resultado cerrado: atribución PFN→hDeltaB

El desarrollo con dos familias de reconexiones dio paso al gate confirmatorio congelado de 800 vuelos. El intacto logró 95/100; cinco nulos que preservan tipo, lado, grados y pesos lograron 0/100, 63/100, 38/100, 1/100 y 46/100. La ventaja sobre la mediana nula fue de 57 puntos y se aprobaron los cuatro criterios jerárquicos. Véanse [el resultado confirmatorio](confirmatory-gate-results.md) y [el análisis final v1](final-analysis-v1.md).

