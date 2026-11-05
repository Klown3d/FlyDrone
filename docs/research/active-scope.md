# Alcance activo: robustez y aplicación 3D

El alcance actual quedó cerrado al disponer de una aplicación 3D nativa verificable y un [análisis final integrado](final-analysis-integrated-v4.md).
Presentación pública, videos, publicación, instalador y dron físico quedan
pospuestos por decisión del usuario.

## Punto actual

- Circuito FAFB 783 extraído y navegación integrada v4 evaluada.
- Cuatro gates prospectivos de atribución cerrados y preservados.
- Aplicación nativa con vuelo interactivo y morfologías completas.
- Comparador 3D de ensayos preservados de los tres gates de steering.
- Comparador estable durante 16 vuelos completos, con cámaras general/A/B,
  selección individual de neuronas e identidad FlyWire visible.
- Diagnóstico local completo: 28 vuelos, 4/4 por variante con ganancias y τ ±20%.
- Piloto OOD completo: FlyWire 5/6, convencional 6/6, fallo preservado durante
  pérdidas sensoriales largas. No sustituye una evaluación amplia.
- Diagnóstico causal local del fallo OOD: reproducción exacta; heading verdadero
  rescata el caso, velocidad verdadera sola no. Es evidencia de un caso, no un
  resultado poblacional ni una nueva validación.
- El diagnóstico por oráculos está preservado con hashes y disponible en el
  comparador 3D como una categoría explícitamente post-hoc.

## Criterios de cierre de robustez

1. Informar sensibilidad de steering, deriva y constante temporal, con casos
   pareados y todos los resultados conservados.
2. Ejecutar un piloto fuera del régimen previo, incluido viento de signo
   invertido, mayor distancia y pérdidas sensoriales más largas.
3. Declarar el tamaño pequeño de estos diagnósticos y separar el piloto de
   una futura prueba confirmatoria con generador sellado.
4. Mantener explícitas la regularización de brújula y las capas convencionales.

## Criterios de cierre de aplicación

1. Vuelo interactivo nativo y reproducción de ensayos guardados accesibles
   desde la aplicación principal.
2. Geometría completa de las 286 morfologías descargadas, con filtros y cámara.
3. Pausa, reinicio, búsqueda temporal y velocidad de reproducción sincronizados.
4. Comparación intacto/nulo del mismo caso y estadísticas globales visibles.
5. Distinguir actividad guardada, reconstrucción algebraica y actividad no
   disponible, evitando inventar propagación por ramas.
6. Validar integridad de archivos y coincidencia del comando reconstruido
   con el comando de steering guardado.
7. Documentar límites y verificar renderizado y controles.

Pendientes posteriores a este bloque: ampliar casos con ambas trazas guardadas
en los gates. La comparación 3D de ablaciones, interacción de cámara e
inspección individual ya están implementadas. La
selección actual de casos está limitada por la política histórica de guardar
todas las fallas y sólo el primer éxito de cada condición; no se calcula una
tasa de éxito a partir de los casos disponibles para reproducción.
El piloto OOD sí conserva los seis pares completos y se puede comparar con
el convencional en 3D.

## Cierre

Las fases 9–11 se consideran cerradas para v4, no para una afirmación de robustez universal. La sensibilidad global, la validación sellada de v5, el empaquetado y el dron físico permanecen fuera de este cierre. El diagnóstico OOD amplio y el desarrollo inicial de v5 ya se ejecutaron, pero no constituyen validación de v5.

## Estado inmediato del compass v5 (2026-10-31)

- El diagnóstico prospectivo localizó el cuello de botella dominante en heading.
- Un candidato híbrido que conserva el estado FlyWire-grounded y lo fusiona con integración giroscópica pasó 24/24 casos de desarrollo, frente a 16/24 para v4 neuronal puro.
- La auditoría mostró un peso neuronal medio de 0,066 durante dropout; la mejora operacional se atribuye principalmente a la asistencia inercial.
- Próximo paso operacional: congelar el candidato híbrido y diseñar un gate sellado nuevo.
- Próximo paso científico: mejorar y probar por separado el compass neuronal puro; no usar el éxito híbrido como evidencia de superioridad neuronal.

## Gate operacional híbrido v5 (2026-11-02)

- Cerrado prospectivamente con **10/10 criterios aprobados**.
- Híbrido v5: 24/24; v4 neuronal: 12/24; giroscópico: 24/24; convencional: 24/24.
- Auditoría posterior: 316 hashes intactos, ambiente coincidente y 96/96 trazas válidas.
- Interpretación: solución operacional robusta asistida por inercia; no superioridad causal del compass neuronal.
- Resultado completo: [v5-hybrid-gate-results.md](v5-hybrid-gate-results.md).
- Integración 3D completada: 72 pares v5 auditados, tres comparaciones disponibles y error máximo de reconstrucción de steering `2,845×10⁻¹⁵ rad/s`.

## Extensión de navegación libre (2026-11-02)

- Gestor de metas temporales de ingeniería implementado sin modificar el controlador v5.
- Modos disponibles: punto, dirección manual, patrulla y exploración determinista de 25 celdas.
- Gate prospectivo v1 aprobado: **13/13 criterios**, 106 metas híbridas frente a 109 convencionales.
- Cero escapes, colisiones y saturaciones; geofence máximo 18,53% y captura de meta máxima 14,91%.
- Participación mínima: yaw neural 99,82% y hDeltaB 98,49%; la inercia dominó como máximo 13,33%.
- Los 12 pares están preservados y disponibles en el comparador 3D con metas dinámicas.
- Visión general y percepción de obstáculos múltiples permanecen pendientes.
- Alcance y límites: [free-navigation-extension.md](free-navigation-extension.md).
- Resultado sellado: [free-navigation-gate-v1-results.md](free-navigation-gate-v1-results.md).

## Percepción de distancia y evasión (actualizado 2026-11-04)

- Sensor raycast 2D determinista implementado: 31 rayos, 270°, 6 m y ruido reproducible.
- Detecta la primera intersección entre múltiples obstáculos circulares.
- Es ingeniería simulada, no cámara ni vía visual de la mosca.
- Ya interviene mediante mapa local, seguimiento de contorno, recuperación de waypoints bloqueados, gobernador de velocidad y rechazo de emergencia, aplicados por igual a ambos controladores.
- v6 quedó sin colisiones en 8 episodios y la repetición exacta del choque v5 pasó de −0,713 m a +0,437 m de holgura.
- v14 exploración obtuvo 4/4 éxitos de desarrollo, 9–13 metas y 0 colisiones con selección de celda cercana; esta selección es ingeniería y no memoria neuronal.
- v17, con rango omnidireccional simulado, es el mejor candidato unificado: 7/8 éxitos, cero colisiones y ambos controladores pasan patrulla; falla por 7,7 mm el margen de 0,15 m en un episodio FlyWire.
- Los ajustes escalares v18–v25 mejoraron reproducciones aisladas pero no generalizaron; algunos introdujeron nuevas colisiones. Se preservan como resultados negativos de desarrollo.
- La barrera predictiva sobre impactos observados ya está integrada opcionalmente y tiene pruebas unitarias y de vuelo. Rescató dos reproducciones críticas exactas (v26–v27), pero la matriz unificada v28 sólo logró 6/8: cero colisiones, convencional 4/4 y FlyWire 2/4, con un despeje mínimo de 0,039 m bajo viento.
- El diagnóstico v29–v33 mostró que la salida traslacional PFN→hDeltaB actual interfiere con la evasión de forma dependiente de la trayectoria: ablación, conmutación, ganancia y confianza rescatan casos distintos pero no generalizan juntas.
- v34 separó responsabilidades: EPG–Δ7–PFL3/PFL2 conserva rumbo, steering y avance; la estabilización lateral vuelve a una capa convencional con la misma amortiguación del baseline. FlyWire pasó 4/4 vuelos conocidos, sin colisiones y con holgura mínima global de 0,264 m. Es candidato de desarrollo, no gate ni evidencia de superioridad.
- v35 comparó FlyWire-v34 y el baseline en el mismo proceso: ambos pasaron 4/4 y tuvieron cero colisiones. FlyWire quedó en 12,5 frente a 13 metas medianas de exploración, con mayor cobertura (0,52 frente a 0,48); ambos completaron 4 metas de patrulla, con menor cobertura FlyWire (0,56 frente a 0,64). Estas diferencias no son inferenciales con dos vuelos por modo.
- El gate no está abierto. v35 cierra el desarrollo sobre estos cursos conocidos. Próximo paso: congelar v34, preregistrar escenarios nuevos y ejecutar una evaluación pareada fuera de desarrollo. En paralelo, la integración futura de hDeltaB requiere un readout/arbitraje nuevo; no se resolverá eligiendo una ganancia post-hoc.

## Gate prospectivo de obstáculos v1 (2026-11-04)

- Se congelaron 383 inputs antes de ejecutar 24 vuelos pareados en tres geometrías, dos headings y dos modos nuevos.
- El gate **no fue aprobado**: FlyWire v34 obtuvo 0/12 episodios completos y 24 metas frente a los mínimos de 10/12 y 84.
- FlyWire tuvo cero colisiones y quedó sólo seis metas debajo del convencional, pero su margen mínimo fue 0,014 m, la barrera intervino hasta 72,6% y el bloqueo alcanzó 78,6%.
- El baseline también falló ampliamente: 1/12, 30 metas y tres colisiones. Esto localiza el cuello de botella dominante en la planificación/seguridad compartida, no exclusivamente en el circuito FlyWire.
- La auditoría post-hoc encontró un defecto del diseño y del sistema: cada escenario contenía 6–7 celdas de exploración físicamente solapadas con obstáculos, y el gestor carecía de una regla para abandonar metas inaccesibles. En los bloqueos nominales la evasión permaneció activa hasta 96,7% y casi no liberó el contorno.
- El resultado 4/4 de v35 no generalizó; queda preservado como desarrollo sobre cursos conocidos.
- Resultado completo: [obstacle-navigation-gate-v1-results.md](obstacle-navigation-gate-v1-results.md).
- Próximo paso: diagnóstico post-hoc de liberación de contorno, bloqueo y representación de superficies. hDeltaB permanece fuera de alcance hasta resolver la capa común.
- Alcance: [range-perception-foundation.md](range-perception-foundation.md).

# Post-gate obstacle safety update (2026-11-05)

The obstacle gate v1 remains officially failed. Post-hoc development through v40 is documented in `docs/research/obstacle-navigation-postgate-development.md`. The current best safety candidate remains v39: it infers continuous surfaces from adjacent range hits and projects the fully composed acceleration command using closing speed. In the four-case diagnostic replay it produced zero collisions; FlyWire clearance was at least 0.238 m, but one FlyWire route completed only four targets and stalled for 15.4% of the episode. A v40 current-scan-only constraint recovered some progress but reintroduced one FlyWire collision, so it was rejected. Therefore v39 is a safety candidate, not yet a gate-v2 candidate. The next bottleneck is selective age/visibility-aware obstacle memory and the safety/progress tradeoff, not neural compass tuning.

Selective visibility-checked memory was subsequently tested through v43. v41 is the best balance: zero collisions, FlyWire median 11 targets, and median stall 4.6%, but one clearance remained 0.099 m. Single-case durations of 1.2 and 1.6 seconds produced non-monotonic clearance, so scalar memory tuning is stopped. The next step is per-constraint identity and contribution telemetry, not another duration sweep.

