# FlyDrone

Proyecto de investigación sobre un modelo computacional de un circuito del central complex de *Drosophila melanogaster*, reconstruido con datos FlyWire, para navegación de un dron simulado.

**Estado:** extracción FAFB 783 y modelos EPG→Δ7→PFL3/PFL2 y PFNd/PFNv→hΔB evaluados. Existe un prototipo nativo con navegación espacial, sensores perturbados, planta 6DoF, ráfaga y obstáculo, junto con **286 esqueletos completos**. Cuatro gates prospectivos de atribución —PFN→hΔB, EPG→Δ7, Δ7→PFL3 y steering conjunto— compararon el circuito intacto contra 20 redes nulas emparejadas por gate. El intacto logró 12/12 en los cuatro; ninguna de 80 redes nulas lo igualó y todos los gates alcanzaron `p=1/21=0,0476`. Esto respalda capacidad y dependencia de partner identity connectómica dentro de la simulación, no superioridad convencional, causalidad biológica ni vuelo físico. Véanse la [síntesis de atribución](docs/research/connectome-attribution-synthesis.md), el [resultado confirmatorio PFN→hΔB](docs/research/confirmatory-gate-results.md) y los [controles y límites](docs/desktop-app.md).

La primera [planta rígida de quadrotor con seis grados de libertad](docs/research/quadrotor-6dof.md) está disponible como modo seleccionable en la aplicación: 64/64 episodios deterministas y 64/64 con ruido, retraso y ráfagas físicas. FlyWire gobierna yaw; un lazo convencional estabiliza actitud, altura y motores. El proporcional sigue siendo ligeramente más eficiente.

La primera [prueba 6DoF con obstáculo](docs/research/obstacle-navigation.md) conserva los intentos fallidos y valida la corrección con ángulos nuevos: 16/16 llegadas y 0/16 colisiones por controlador. La capa convencional elige una meta local segura; FlyWire sigue controlando solamente el yaw hacia ella.

La primera [ablación computacional del circuito en 6DoF](docs/research/circuit-ablation-6dof.md) aporta evidencia de atribución: intacto 16/16, sin Δ7 0/16, sin FC2 0/16, topología binaria 14/16, cinco grafos barajados 0/80 y cinco nulos con grados binarios preservados 7/80; el proporcional obtuvo 16/16. Los siete éxitos nulos se concentraron en dos direcciones. El resultado apoya que la organización específica importa dentro del modelo provisional, sin demostrar superioridad sobre control convencional ni equivalencia con una intervención biológica.

La localización posterior usó una semilla nueva común y modificó una proyección por vez en 6DoF: EPG→Δ7 obtuvo 0/16, Δ7→PFL3 0/16 y FC2→PFL3 1/16, frente a 16/16 intacto sobre las mismas geometrías. Las tres correspondencias contribuyen a la generalización del controlador.

En la [prueba de robustez de arquitectura](docs/research/circuit-ablation-6dof.md), el circuito intacto conservó 32/32 llegadas bajo ruido, retraso y ráfagas moderadas/fuertes; el nulo EPG→Δ7 obtuvo 0/32 y el nulo FC2→PFL3 1/32. Los parámetros neuronales y de la planta permanecieron congelados.

El [baseline PID de yaw](docs/research/pid-baseline.md) se ajustó sólo en cuatro geometrías de desarrollo y se congeló antes de la evaluación. Neuronal, PID y proporcional alcanzaron 48/48 metas reservadas. El PID fue más eficiente bajo perturbación fuerte; por ahora FlyDrone demuestra control funcional y dependencia de la arquitectura provisional, no superioridad frente a control convencional.

La [extensión recurrente de la brújula](docs/research/recurrent-compass-extraction.md) contiene 149 neuronas EPG/Δ7/PEN_a/PEN_b/PEG, 6.238 pares dirigidos y 44.492 sinapsis FAFB 783 con coordenadas verificadas. La revisión más reciente separa entrada PB y salida EB de PEN y recupera desplazamientos laterales opuestos de aproximadamente 49–55°.

El [primer gate de dinámica recurrente](docs/research/recurrent-dynamics.md) evaluó 288 configuraciones en tres variantes. Ninguna mantuvo un bump único y lo actualizó correctamente: las variantes fuertes conservaron actividad multimodal cuya fase poblacional se cancela. El banco temporal está implementado, pero la memoria funcional no está validada y permanece desconectada del dron; el siguiente requisito es reconstruir glomérulos PB, wedges/tiles EB y regiones NO.

La reconstrucción posterior [resuelta por 16 fases](docs/research/phase-compass-dynamics.md) superó el gate aislado. Esa v2 usaba un desplazamiento PEN de una cuña tomado de literatura. La v4 actual reemplaza ese operador manual por la diferencia lateral PEN_a PB→EB derivada de contactos y ya está integrada al dron; todavía necesita simetría regularizada y una prueba prospectiva cerrada.

Abrir la aplicación: ejecutar `Start-FlyDrone.ps1`, o `.venv\Scripts\python.exe -m flydrone.visualization.desktop`. [Controles y límites del prototipo](docs/desktop-app.md).

Comparar ensayos en una ventana 3D nativa: `Start-FlyDrone-Gates3D.ps1` o el
botón **Comparar ensayos 3D** de la aplicación. Muestra intacto/nulo en los tres
gates de steering y FlyWire/convencional en los seis casos del piloto OOD,
con actividad sincronizada y morfologías completas. [Guía del comparador](docs/gate-replay-3d.md).

Reproducir y comparar los 100 casos del gate confirmatorio en una ventana nativa: ejecutar `Start-FlyDrone-Replay.ps1`, o `.venv\Scripts\python.exe scripts\confirmatory_replay.py`. El visor incluye pausa, navegación entre casos, trayectoria, error de dirección y actividad PFN/hΔB sincronizada.

La revisión de llegada ejecutó [1.920 episodios adicionales](docs/research/arrival-confirmation.md). La política candidata corrigió los dos fallos conocidos; en un conjunto nuevo, tanto la política anterior como la candidata pasaron 320/320 por controlador, por lo que todavía no se demostró superioridad general. La aplicación muestra en vivo entrada observada, máximos EPG/Δ7/FC2, tasas PFL3 izquierda/derecha y comando de giro.

La [ablación de llegada](docs/research/arrival-ablation.md) añadió 2.560 episodios. Identificó al filtro como necesario bajo ruido+sesgo fuerte y a la recuperación como necesaria después de desplazar el dron; estos efectos aparecen en ambos controladores y pertenecen a la interfaz convencional, no a una ventaja neuronal.

- [Selección de circuito, evidencia y plan experimental](docs/research/circuit-selection.md).
- [Informe de extracción anatómica](docs/research/circuit-extraction.md).
- [Auditoría morfológica y mapeo funcional](docs/research/functional-mapping.md).
- [Modelo neuronal PFL3 de referencia](docs/model-assumptions.md).
- [Resultados del modelo ponderado por FlyWire](docs/research/connectome-model-results.md).
- [Hipótesis](docs/hypothesis.md).
- [Manifiesto de adquisición planificada](data/manifest.json).

Se reconstruyó el subgrafo ampliado EPG/Δ7/FC2/PFL2/PFL3 con 207 neuronas y 5.056 pares dirigidos. El resultado negativo inicial de propagación EPG se conserva en [la auditoría](docs/research/epg-delta7-audit.md). La revisión posterior identificó una inconsistencia del signo angular, respaldada por los métodos publicados: [diagnóstico de fase](docs/research/phase-diagnostic.md), [orientación dinámica](docs/research/orientation-closed-loop.md) y [sensibilidad de interfaz](docs/research/orientation-sensitivity.md). El modelo continúa provisional y no demuestra superioridad sobre el proporcional.

La [extensión PFL2](docs/research/pfl2-steering.md) usa 12 neuronas y conectividad Δ7/FC2B/C real para modular la magnitud del yaw sin cambiar el sentido elegido por PFL3. En desarrollo, PFL3+PFL2 mantuvo 16/16 llegadas y redujo 0,819 s el tiempo mediano frente a PFL3 sola.

PFL2 también puede [modular el avance de alto nivel](docs/research/pfl2-advance.md). En el gate prospectivo alcanzó 30/30 metas, igual que el frenado angular, con sólo 0,022 s de costo mediano y sin saturación. La transformación del índice PFL2 a velocidad es una regla de ingeniería documentada y conmutable en la aplicación.

La evaluación prospectiva posterior alcanzó 36/36 metas por condición y aprobó 6/6 criterios: PFL2 mejoró 0,386 s la llegada mediana y aumentó 0,0075 la eficiencia pareada sin cambiar el sentido del giro. Su organización de fases superó 30 nulos permutados, pero una fórmula angular con la misma ganancia rindió casi igual. El resultado demuestra una señal connectómica funcional e interpretable, no superioridad sobre un controlador convencional.

La [Fase 6 PFNd/PFNv→hΔB](docs/research/travel-direction-extraction.md) contiene 202 neuronas y 53.999 sinapsis. Recuperó ocho columnas PFN, doce hΔB y el desplazamiento dendrita–axón de medio FB. El gate prospectivo aislado aprobó 6/6 criterios en 720 transformaciones nuevas: 6,09° de error mediano ideal y 8,38° con los escenarios de ruido combinados. Quitar PFNd/PFNv o barajar fases degrada el modelo y 0/30 nulos de desarrollo igualaron al intacto.

La [integración de deriva](docs/research/travel-direction-drift-integration.md) ya cerró el bucle 6DoF y superó su gate prospectivo 6/6. Bajo viento, ruido y demora nuevos, hΔB alcanzó 30/30 metas frente a 0/30 sin compensación y 0/30 con fases PFN barajadas. Redujo el desvío máximo mediano 75,0% frente a ausencia y 92,5% frente al nulo. El convencional logró 30/30 y quedó 0,091 m por delante, por lo que el resultado demuestra utilidad y dependencia de la arquitectura del circuito, no superioridad sobre ingeniería convencional.

La [interfaz sensorial de velocidad](docs/research/travel-velocity-sensor.md) elimina el acceso de PFN/hΔB a la velocidad verdadera: la estima desde posiciones observadas. Su gate prospectivo aprobó 7/7 criterios, con 28/30 metas frente a 1/30 sin compensación y 14/15 éxitos durante una pérdida de velocidad de 3,5 s. La velocidad directa conserva mejor tiempo, eficiencia y desvío.

La revisión siguió la SKILL.md proporcionada para FlyDrone. Se usa `docs/research/circuit-selection.md` como documento canónico según la solicitud explícita; `docs/circuit-selection.md` conserva un enlace de compatibilidad con la estructura de la skill.

El cierre científico de esta versión está en [Análisis final de FlyDrone v1](docs/research/final-analysis-v1.md). Los 277 insumos congelados del gate y los hashes de sus 707 archivos de resultado se conservaron en `archive/confirmatory_v1/` para permitir desarrollo posterior sin perder reproducibilidad.

## Ver la actividad PFL3 en 3D

Desde PowerShell, en la raíz del proyecto:

```powershell
.\.venv\Scripts\python.exe -m flydrone.visualization.pfl3_viewer --open
```

La auditoría neuronal completa hasta el gate actual se reproduce con:

```powershell
.\.venv\Scripts\python.exe -m flydrone.neural.evaluate_epg_delta7
```

El comando genera y abre `results/visualization/pfl3-activity-3d.html`. El visor permite rotar y acercar los esqueletos, cambiar heading y objetivo, reproducir un giro y observar las tasas de las 24 PFL3 junto con la señal poblacional R−L. El selector permite alternar entre la referencia publicada y el modelo ponderado por FlyWire. Todavía no representa al dron ni al circuito completo.
### Diagnóstico de brújula online en 6DoF

La brújula recurrente ya está integrada al dron 6DoF y fue evaluada durante pérdidas temporales de rumbo. El dron recuperó y completó 16/16 vuelos, pero la fase neuronal no siguió correctamente la velocidad angular durante el corte; PID y proporcional con giroscopio fueron mucho más precisos. Véase `docs/research/heading-dropout-6dof.md`. Este resultado es diagnóstico y no respalda todavía una ventaja de FlyDrone.

El validador aislado multivelocidad se encuentra en `src/flydrone/neural/phase_velocity_validation.py`. Prueba ambos sentidos de giro, operadores PEN y un control con simetría rotacional antes de permitir otra integración con el dron; véase `docs/research/phase-velocity-validation.md`.
## Hoja de ruta

El plan completo, el estado actual y los criterios de salida de cada fase están documentados en `docs/research/project-roadmap.md`.

Las predicciones prospectivas y reglas de análisis están en `PREREGISTRO.md`; la fuerza de evidencia por población está resumida en `docs/research/evidence-matrix.md`.

La auditoría de índices PEN, la distancia introducida por la circularización y el control inicial con 30 nulos están documentados en `docs/research/pen-and-regularization-audit.md`.

La revisión posterior corrigió el principal error anatómico de esa auditoría: las transferencias PEN deben medirse desde entradas PB hacia salidas EB. La extracción recupera desplazamientos laterales opuestos de aproximadamente 49–55° y la aplicación ya usa un operador PEN_a derivado de esos contactos. Con parámetros v4 congelados, 0/30 mapas de fase nulos igualaron el resultado FlyWire (p empírico 0,032), pero la circularización relocaliza 58–60% del peso PEN. La variante v4 no es todavía una reconstrucción literal; véase `docs/research/cross-compartment-pen-model.md`.

La brújula regularizada ya puede inspeccionarse en la aplicación mediante el botón de pérdida de señal; detalles en `docs/research/desktop-phase-compass-integration.md`.

La [prueba prospectiva congelada de v4](docs/research/prospective-v4-dropout.md) ejecutó 120 vuelos 6DoF. V4 alcanzó 30/30 metas y 23,68° de error mediano durante un corte de 6 s, pero falló el gate global por un máximo de 142,86° y una mejora insuficiente frente a sample-and-hold. Los observadores de giroscopio obtuvieron aproximadamente 2,3–2,5°. El resultado se conserva sin reajustar umbrales: v4 es un prototipo funcional, no una brújula validada.
