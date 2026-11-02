# Sensibilidad de orientación y configuración candidata

2026-09-16. FAFB/FlyWire 783. Sigue siendo un modelo provisional de orientación, sin dinámica de vuelo de dron.

## Ensayo que falló anteriormente

Meta −15°, error inicial −45°, semilla de ruido 784 del escenario perturbado original. En los últimos 2 s el error estuvo entre 7,45° y 10,10°, media 8,75°, desviación 0,69°. Superó el umbral de 10° en dos muestras; terminó en 8,50°. La misma condición ideal termina en 7,98°. No se observó divergencia en esa ventana: el fallo se explica por fluctuaciones sobre un sesgo cercano al umbral. Este análisis no demuestra estabilidad global ni elimina el sesgo de asignación/ganancia neuronal.

## Barrido

Se probaron ganancias de readout 0,01/0,02/0,04/0,08 rad/s por Hz, retrasos 0/150/300/500 ms y ruido gaussiano de heading de 3°, con semillas 783/784/785. Cada combinación usa las mismas 96 condiciones de metas y errores iniciales del ensayo anterior. El proporcional mantiene ganancia 1/s y comparte planta, saturación y realizaciones de ruido. Éxito mantiene la definición: todos los errores muestreados de los últimos 2 s dentro de ±10°.

| Ganancia neuronal | 0 ms | 150 ms | 300 ms | 500 ms |
|---|---:|---:|---:|---:|
| 0,01 | 99,31% | 99,31% | 98,96% | 98,96% |
| **0,02** | **100%** | **100%** | **100%** | **99,31%** |
| 0,04, anterior | 99,31% | 98,61% | 95,49% | 74,31% |
| 0,08 | 95,49% | 87,85% | 37,85% | 0% |

288 episodios por celda. El proporcional obtuvo 100% en los cuatro retrasos. El barrido ejecutó 5.760 episodios, incluidos 1.152 del baseline. La ganancia 0,01 no es automáticamente mejor: a tiempo finito algunos ensayos pueden no haber completado la orientación. La ganancia alta pierde robustez con retraso. No se ajustaron conexiones, fases, signos ni propiedades biológicas para mejorar esas celdas.

Se conserva exactamente la propagación neuronal sinusoidal mediante su forma armónica compleja. Una prueba numérica verifica equivalencia para matrices firmadas. Esto optimiza el cálculo, no cambia el modelo. Las trazas conservan heading real y observado, comandos, identificadores y tasas PFL3; las entradas EPG y desviaciones Δ7 son reconstruibles desde el heading observado, los ángulos guardados y las matrices originales. La planta y la actividad neuronal siguen siendo abstracciones de ingeniería y modelo, respectivamente.

## Comprobación con ruido nuevo

Se fijó la ganancia 0,02 antes de evaluar semillas 786/787/788, con retrasos de 150 y 300 ms. El modelo obtuvo **576/576 éxitos**, al igual que el proporcional. La mediana del error final neuronal fue 1,64° y 1,67° para cada retraso; el proporcional 0,34° y 0,38°.

Esta comprobación es independiente respecto de las realizaciones de ruido, **no respecto de metas, orientaciones iniciales ni planta**, que permanecen iguales. No es una demostración estadística de éxito universal. El conjunto adicional ejecutó 1.152 episodios entre los dos controladores. Se exploraron y comprobaron 6.912 episodios en esta etapa.

## Decisión

Se guarda `configs/orientation_candidate_v1.yaml` con ganancia 0,02, signo EPG −1 y fase global cero, conservando la configuración anterior. Es una **configuración de interfaz candidata**, no una nueva fisiología neuronal. Se propone 150 ms como retraso nominal de esta planta; se dispone de comprobaciones con 300 ms. El éxito finito no constituye un margen formal de estabilidad.

El siguiente paso puede ser una primera integración con una planta simplificada de dron simulado para mantener altura y orientarse hacia una meta. Debe declarar parámetros de ingeniería, preservar estabilización convencional independiente y comparar con el proporcional. Quedan abiertos la validación anatómica de 24 Δ7, estimación de sensores, recurrencia/dinámica neuronal, metas nuevas, sensibilidad al paso de integración y modelos de vuelo más realistas. El rendimiento proporcional superior en precisión permanece explícito.

## Reproducción

```powershell
.venv\Scripts\python.exe -m flydrone.neural.orientation_sensitivity
.venv\Scripts\python.exe -m flydrone.neural.orientation_sensitivity --config configs/orientation_held_out_noise.yaml
.venv\Scripts\python.exe -m flydrone.neural.orientation_closed_loop --config configs/orientation_candidate_v1.yaml
```

Los dos primeros experimentos se ejecutaron. El tercero queda listo para repetir el banco anterior con la configuración candidata; no se presenta como un experimento adicional ya ejecutado. Productos en `results/neural/orientation_sensitivity/` y `results/neural/orientation_held_out_noise/`: resúmenes, episodios, trazas NPZ, informes con hashes y semillas. Tres pruebas relevantes pasaron.
