# Revisión de compartimentos de salida Δ7

Fecha: 2026-09-16. FAFB/FlyWire 783. Seguimiento de `pb-anatomical-validation.md`.

Se compararon las dos anclas PB con mayor cantidad de contactos presinápticos para cada una de las 40 Δ7 con los patrones de `glom_sorter_delta7` del código archivado de [Mussells Pires et al.](https://doi.org/10.5281/zenodo.10232698), archivo `analysis/em.py`. Se usa la correspondencia geométrica provisional PB01..PB09 = L9..L1 y PB10..PB18 = R1..R9. No es una nueva anotación oficial FAFB.

## Resultado

| Categoría diagnóstica | Neuronas |
|---|---:|
| Pareja compatible con patrón publicado, sin anclas extremas y ≥80% de contactos en ambas anclas | 16 |
| Requiere revisión de compartimentos | 13 |
| Pareja que incluye anclas extremas ambiguas | 11 |

El umbral 80% es una elección de ingeniería para priorizar revisión, no una definición biológica de subtipo. Los patrones de tres salidas no pueden validarse tomando solo las dos mayores. Las etiquetas de compatibilidad indican candidatos, **no subtipos verificados**. Se conserva la fracción de contactos y la pareja completa por neurona.

Un ejemplo es `720575940606137004`: las dos anclas dominantes PB06/PB14 corresponden provisionalmente a L4/R5, patrón presente en el código publicado. Estas anclas reúnen aproximadamente 90,3% de sus contactos PB de salida. No implica que todos los contactos restantes sean ruido: pueden reflejar límites entre anclas, arborización real o errores de asignación.

La diferencia absoluta entre índices PB se reporta explícitamente; no se confunde con la cantidad de glomérulos intermedios. Esto evita convertir la diferencia de lenguaje entre publicaciones en un criterio automático de rechazo. No queda resuelta por ello la correspondencia completa de sus atlas.

## Inspección 3D

Se generó `results/morphology/delta7-compartments/delta7-contacts-3d.html`: permite seleccionar cada Δ7, rotar la nube de sus contactos presinápticos reales y compararla con las 16 anclas EPG. Muestra coordenadas anatómicas en micrómetros, **no activación neuronal**. No coloca ni extrapola etiquetas PB01/PB18.

Por neurona se muestran hasta 900 contactos elegidos sin reemplazo con semilla 783. Las estadísticas usan todos los contactos; el muestreo se limita a la vista. La página funciona localmente sin dependencias remotas.

## Decisión para avanzar

La revisión anatómica completa permanece abierta. La conversión angular de signo ya tiene respaldo explícito en los métodos experimentales y el modelo estático produce steering correcto bajo entradas ideales. Por ello hay información suficiente para **iniciar una prueba dinámica del modelo provisional de orientación**, manteniendo el nivel de afirmación y las limitaciones. No se requiere presentar subtipos extremos ficticios para esa prueba, porque el modelo utiliza matrices reales por identificador y fases de entrada EPG, no etiquetas funcionales de cada Δ7.

Esto distingue dos hitos: comprobar estabilidad en lazo cerrado del modelo provisional y validar la reconstrucción anatómica completa. El segundo no queda cumplido por iniciar el primero. Antes de integrar el dron debemos verificar convergencia desde distintas orientaciones, ruido/retrasos y dependencia de las conexiones frente a controles alterados. Ninguna prueba dinámica se ejecutó en esta revisión.

## Reproducción

```powershell
.venv\Scripts\python.exe -m flydrone.morphology.delta7_compartments
```

Configuración: `configs/delta7_compartments.yaml`. Tabla de candidatos, informe y hashes: `results/morphology/delta7-compartments/`. Las pruebas relacionadas comprueban la convención de índices y orden de nombres; los resultados de las neuronas reales se reportan aparte.

**Próximo paso concreto:** fijar una configuración candidata EPG con el signo de heading corregido, preservar la anterior como control negativo y ejecutar un banco de orientación dinámica con entradas ideales y perturbadas. Sus ganancias y tiempos de respuesta deben declararse como ingeniería, sin atribuirlos a fisiología medida de Δ7.
