# Banco de pruebas de la planta de escritorio

Fecha: 2026-09-18. FAFB/FlyWire 783. Modelo neuronal y anatomía provisionales.

Se evaluó la misma función de planta utilizada por la aplicación nativa: movimiento vertical con empuje limitado, gravedad, estabilizador PD convencional y orientación yaw con respuesta de primer orden. La simulación no representa aerodinámica completa, x/y, roll/pitch ni motores individuales. Altura y yaw están desacoplados en esta aproximación.

## Diseño

12 metas, 8 errores iniciales y 2 alturas iniciales (0,7 y 3,0 m): 192 condiciones por controlador y realización. Meta de altura: 2 m. Paso 20 ms, duración 20 s; ganancia neuronal candidata 0,02. El circuito conserva EPG→Δ7→PFL3 con conteos reales y input de meta FC2. El proporcional comparte planta, saturación y observaciones.

Escenarios: ideal (semilla 789 sin ruido) y heading con ruido gaussiano de 3° y retraso exacto de 300 ms (semillas 789/790/791). Altitud y meta se observan idealmente: no se probó ruido de altura ni estimación visual. Los mismos arrays de ruido se usan para ambos controladores dentro de cada escenario/semilla. Los ensayos ideales de ambas alturas comparten la tarea angular; contar ambas alturas no equivale a dos entornos de navegación independientes.

Éxito: todos los errores muestreados durante los últimos 2 s dentro de ±10° de heading y ±0,1 m de altura, sin contacto muestreado con el suelo. Se conserva una reacción de suelo que impide z negativo; no se usa para fijar artificialmente la altura al objetivo.

## Resultados

| Escenario | Controlador | Éxitos | Altura correcta | Contactos con suelo |
|---|---|---:|---:|---:|
| Ideal | Neuronal provisional | 192/192 | 100% | 0 |
| Ideal | Proporcional | 192/192 | 100% | 0 |
| Ruido y retraso | Neuronal provisional | 576/576 | 100% | 0 |
| Ruido y retraso | Proporcional | 576/576 | 100% | 0 |

**1.536 episodios completados.** El error final mediano neuronal ideal es 1,72°. En las tres realizaciones perturbadas es 1,86°/1,79°/1,85°; el proporcional obtiene 0,24°/0,22°/0,20°. Continúa sin demostrarse superioridad neuronal. Pasar este conjunto no prueba éxito universal ni resuelve la anatomía Δ7 pendiente.

La prueba confirma la integración de steering provisional con estabilización vertical convencional para esta planta restringida. No representa navegación autónoma ni validación de un vehículo físico. El cambio respecto del banco anterior es usar directamente la planta de escritorio, probar alturas iniciales y aplicar paso 20 ms; no se atribuye la diferencia de resultados a un factor aislado.

## Reproducibilidad

```powershell
.venv\Scripts\python.exe -m flydrone.simulation.benchmark_hover
.venv\Scripts\python.exe -m pytest tests/test_hover.py -q
```

Configuración: `configs/hover_benchmark.yaml`. Resultados en `results/simulation/hover_benchmark/`: informe con hashes, episodios, resumen y trazas NPZ con heading real/observado, altura, empuje, comandos, tasas PFL3, desviaciones Δ7 e IDs. Las entradas EPG y FC2 se pueden reconstruir desde observación y meta junto con la configuración original. En el baseline, las neuronas se calculan como observación del modelo, pero no controlan el giro.

Para acelerar el banco, la función de planta admite batches. Una prueba compara sus resultados con episodios individuales y exige igualdad numérica; la aplicación continúa utilizando estado escalar. Tres pruebas de planta pasaron: convergencia vertical, respuesta yaw y equivalencia batch/individual.

## Siguiente paso

Agregar desplazamiento horizontal a baja velocidad con estabilización convencional, una meta espacial y parada al alcanzarla. El circuito deberá orientar hacia la dirección de la meta, sin recibir el error angular directamente como sustituto de la red. Se declarará qué parte decide el avance y se comparará con el proporcional. Antes de obstáculos, medir alcance de meta, tiempo, trayectoria y dependencia de conexiones alteradas. La vista neuronal conservará geometría completa y actividad global modelada.
