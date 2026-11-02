# Primera prueba de orientación en lazo cerrado

2026-09-16. FAFB/FlyWire 783. Modelo provisional; no vuelo ni navegación de dron.

Se fijó `epg_heading_sign: -1` y desfase global cero en una configuración versionada separada. La configuración anterior permanece como control negativo. Se usa la propagación real PB EPG→Δ7→PFL3, normalizada por contactos, con meta FC2 y diferencia poblacional derecha menos izquierda. El modelo neuronal es algebraico y sin recurrencia Δ7: esta prueba añade un lazo dinámico de orientación, no una fisiología neuronal dinámica validada.

## Diseño reproducible

12 metas × 8 errores iniciales = 96 episodios por condición. Duración 20 s; paso 50 ms. Dos escenarios: ideal y ruido gaussiano de heading de 3° con retraso de observación de 150 ms. Se evalúan modelo corregido, convención anterior, eliminación de meta, controlador proporcional y cinco permutaciones independientes de entradas EPG.

Señal neuronal a velocidad de giro: ganancia 0,04 rad/s por Hz y saturación 1,5 rad/s. Respuesta del actuador: filtro de primer orden con τ = 150 ms. Todos esos valores son ingeniería configurada, no parámetros medidos de Δ7 ni de un dron. Heading observado representa una abstracción sensorial ideal/perturbada; no se simula visión. El controlador proporcional comparte actuador, saturación y observaciones. La misma realización de ruido se utiliza para todas las condiciones dentro de cada escenario. Semilla 783; no se ajustaron parámetros a cada episodio.

Éxito: **todos los errores muestreados en los últimos 2 s son ≤10°**. También se guarda el primer comienzo de una ventana de 2 s dentro de tolerancia; este tiempo puede existir en un ensayo que falle al final y no se llama asentamiento definitivo.

## Resultados

| Condición | Éxito ideal | Éxito con ruido/retraso |
|---|---:|---:|
| FlyWire provisional, signo corregido | 100% (96/96) | 98,96% (95/96) |
| Convención anterior | 0% | 0% |
| Sin entrada de meta | 6,25% | 6,25% |
| Proporcional convencional | 100% | 100% |
| Cinco controles de entradas EPG permutadas | 0–9,38% | 0–9,38% |

Modelo corregido: mediana del error final 1,72° ideal y 1,49° perturbado; percentil 95 de 8,12° y 8,37°. Primer comienzo de ventana en tolerancia, mediana: 1,55 s ideal y 1,65 s perturbado.

Proporcional: error final mediano aproximadamente cero en ideal y 0,41° perturbado; percentil 95 perturbado 0,80°. El modelo FlyWire **no demuestra ventaja de precisión frente a este baseline**. Su menor tiempo mediano de primera ventana con estos parámetros tampoco constituye una comparación optimizada de rapidez: las ganancias no se emparejaron por respuesta dinámica.

1.728 episodios ejecutados en total. Los cinco controles de permutación preservan valores, suma de entrada e in-degree de cada fila, pero **no preservan out-degree**. Son evidencia preliminar de dependencia de la asignación de conexiones de este modelo, no atribución biológica definitiva. No se calcularon intervalos de confianza ni se probó una distribución de entornos.

## Productos y límites

`results/neural/orientation_closed_loop/report.json` conserva configuración, hashes, versión de datos y métricas. `episodes.csv` registra resultados individuales. Los archivos NPZ conservan trayectorias, comandos, tasas PFL3, desviaciones firmadas Δ7 e identificadores de neuronas por condición. Las tasas PFL3 son actividad calculada; no medidas in vivo. No se guardaron observaciones EPG individuales: pueden reconstruirse con las trayectorias, configuración, semilla y retraso del runner.

`orientation-replay.html` reproduce un ensayo fijado antes de inspeccionar resultados: meta +15°, error inicial +135°, tanto ideal como perturbado. Muestra orientación y tasas PFL3 guardadas. No muestra dinámica de dron ni actividad anatómica 3D.

La convergencia se ha comprobado para esta planta de orientación, malla de condiciones y parámetros. Quedan incertidumbre anatómica de 24 Δ7, sensibilidad a ganancias/timing, señales EPG no sinusoidales, estimación sensorial, dinámica de vuelo y controles más estrictos de conectividad. Los dos glomérulos extremos siguen sin etiquetas validadas.

## Reproducción y siguiente paso

```powershell
.venv\Scripts\python.exe -m flydrone.neural.orientation_closed_loop
.venv\Scripts\python.exe -m flydrone.visualization.orientation_replay
```

Configuración: `configs/orientation_closed_loop.yaml`. Cinco pruebas relacionadas pasaron, incluyendo consistencia temporal del actuador y error circular al cruzar ±180°.

**Siguiente paso:** ampliar sensibilidad de ganancia y retraso y analizar el episodio perturbado que falla. Después integrar el readout provisional en una planta de dron simulado con altura estabilizada, conservar el proporcional como baseline y mantener el nivel de afirmación de modelo provisional. Esta prueba completa la orientación dinámica inicial; todavía no cumple el hito de navegación del dron.
