# Confirmación y recuperación de llegada

2026-09-18. Se modifica un componente de ingeniería convencional; no cambia el circuito FlyWire ni sus pesos, fases o ganancias.

## Política candidata

La política anterior activaba parada persistente con una sola observación dentro de 21 cm y velocidad estimada ≤8 cm/s. Se conserva en `configs/navigation.yaml` como control.

La candidata, `configs/navigation_confirmed.yaml`, combina:

- Estimación de posición filtrada exponencialmente con τ=0,3 s, exclusivamente para decidir llegada/salida.
- Radio de entrada más conservador de 12 cm y velocidad estimada ≤8 cm/s.
- Evidencia sostenida durante 0,4 s antes de declarar llegada.
- Reanudación del movimiento si la distancia estimada filtrada supera 30 cm durante 0,4 s.

El movimiento usa observaciones sin sustituirlas por posición real. La puntuación de éxito usa estado real y conserva radio físico 30 cm, velocidad final, altura y ventana terminal anteriores. No hay ajuste artificial de posición ni ensanchamiento del criterio de éxito.

Estos valores son decisiones de ingeniería después de examinar fallos previos. Se evalúa el paquete completo: **no se ha aislado cuánto aporta el filtro, el radio menor, la confirmación o la recuperación por separado**. Una posición persistentemente sesgada no se vuelve correcta por filtrar o esperar.

## Comparaciones ejecutadas

| Conjunto | Política | Neuronal | Proporcional |
|---|---|---:|---:|
| 64 geometrías anteriores × realizaciones ideales/perturbadas | Anterior, resultado conservado | 318/320 | 320/320 |
| Mismo conjunto | Candidata | **320/320** | **320/320** |
| 64 geometrías nuevas y semillas 796/797 | Anterior | 320/320 | 320/320 |
| Mismas geometrías y realizaciones nuevas | Candidata | **320/320** | **320/320** |

Se ejecutaron **1.920 episodios adicionales**: 640 de diagnóstico con candidata y 640 por política en el conjunto nuevo. La alternativa quedó fijada antes de evaluar geometrías/ruido nuevos. Se usan posiciones iniciales nuevas, distancias 2/5/8 m, ruido de heading y posición, sesgo 20 cm y los retrasos del banco anterior. No se eligieron metas nuevas según sus resultados.

La candidata corrige los dos fallos conocidos y mantiene éxito en el conjunto nuevo. **En el conjunto nuevo ambas políticas pasan todos los ensayos:** no se ha demostrado una mejora general de tasa de éxito ni superioridad del circuito frente al proporcional. La mediana de distancia final neuronal ideal nueva pasa de 7,97 a 5,41 cm y con ruido leve de 5,40 a 3,84 cm; hay un radio de entrada menor y una espera adicional, por lo que no se atribuye esa diferencia solo a confirmación temporal ni se afirma mejora gratuita de rapidez.

Con ruido y sesgo, la candidata queda a aproximadamente 19,98 cm de mediana (neuronal) y 19,99 cm (proporcional). Eso conserva el efecto del sesgo. No se ha demostrado observabilidad del error absoluto ni recuperación frente a cualquier perturbación.

## Verificación y aplicación

Ocho pruebas relacionadas pasaron: navegación/hover, duración de confirmación, reanudación cuando deja de sostenerse la observación y rechazo de una observación falsa breve. Las pruebas de recuperación son sintéticas y separadas de los resultados de FlyWire; en los bancos no se inyectó una perturbación posterior a la parada para validar recuperación dinámica específica.

La aplicación de escritorio selecciona la candidata mediante `configs/desktop.yaml`. Para aplicarla a una ventana ya abierta hay que reiniciar la aplicación; no se modifica en caliente un ensayo. La interfaz permite alternar observación ideal/perturbada y aplicar un desplazamiento físico de +0,6 m en x. Para evitar que el ángulo indefinido posición→meta haga oscilar artificialmente FC2/PFL3 al llegar, conserva la última dirección fiable dentro de 30 cm y la libera fuera de 40 cm. Esto es acondicionamiento convencional de la entrada, no dinámica neuronal. Con 16 posiciones sintéticas a 8 cm de la meta, la dirección retenida y la señal PFL3 mostraron variación 0 en la comprobación determinista. Después de la perturbación, confirmó salida y nueva llegada a 9,49 cm de la meta. Es un solo ensayo ideal de integración, no una evaluación de robustez. La geometría neuronal sigue completa.

## Reproducción y productos

```powershell
.venv\Scripts\python.exe -m flydrone.simulation.generalize_navigation --config configs/arrival_confirmed.yaml
.venv\Scripts\python.exe -m flydrone.simulation.generalize_navigation --config configs/arrival_held_out.yaml
.venv\Scripts\python.exe -m flydrone.simulation.generalize_navigation --config configs/arrival_legacy_held_out.yaml
```

Productos en `results/simulation/arrival_confirmed/`, `arrival_held_out/` y `arrival_legacy_held_out/`: casos, episodios, resúmenes, fallos, informes con hashes y trazas reales/observadas y neuronales. Los resultados negativos originales siguen en `navigation_generalization/`.

Las ablaciones independientes ya se completaron: [diseño, resultados y decisión](arrival-ablation.md). El filtro y la recuperación resultaron necesarios en sus perturbaciones específicas; el radio estricto evitó un fallo marginal; la confirmación temporal no cambió la tasa de éxito del banco. **Siguiente paso:** integrar una planta de quadrotor con seis grados de libertad manteniendo congelada esta interfaz. Obstáculos y anatomía Δ7 pendiente siguen fuera de esta etapa.
