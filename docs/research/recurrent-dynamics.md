# Primer gate de dinámica recurrente

> **Actualización:** este gate negativo usaba neuronas completas o neuropilos gruesos. La reconstrucción posterior por 16 fases logró persistencia y actualización; véase [phase-compass-dynamics.md](phase-compass-dynamics.md). Este documento se conserva para registrar el fallo y el cambio de representación.

## Objetivo

Comprobar, antes de conectar nada al dron, si la red FAFB EPG/Δ7/PEN/PEG puede mantener una representación única de heading sin señal sensorial y desplazarla durante una entrada de velocidad angular.

La matriz de contactos y los signos por tipo tienen base anatómica: acetilcolina se modeló excitatoria y Δ7 glutamatérgica como inhibitoria, de acuerdo con la evidencia resumida en [recurrent-compass-extraction.md](recurrent-compass-extraction.md). La constante temporal, ganancias, bias, sigmoide, señal sensorial e interfaz de velocidad angular son decisiones de ingeniería; no se presentan como fisiología medida.

## Gate previo

Cada candidato recibe durante 1 s una señal sensorial localizada sobre EPG. Después se evalúan:

1. **Persistencia:** 3 s sin señal; deriva mediana ≤15°, concentración circular mínima ≥0,2 y contraste mínimo ≥0,05.
2. **Actualización:** entrada PEN_a correspondiente a 60°/s durante 1 s; error mediano ≤30° y dirección correcta en todos los casos.

Los parámetros se eligieron sólo con cuatro headings de desarrollo. Cada variante usó headings reservados nuevos una vez seleccionado su candidato.

## Variantes probadas

| Variante | Configuraciones | Persistencia en desarrollo | Actualización completa |
|---|---:|---:|---:|
| Matriz completa, búsqueda inicial | 96 | 0 | 0 |
| Matriz completa, mayor ganancia/no linealidad | 96 | 0 | 0 |
| Matriz separada por PB/EB/NO | 96 | 0 | 0 |
| **Total** | **288** | **0** | **0** |

La primera variante reservada produjo 19,46° de deriva, concentración mínima 0,029 y error de giro de 33,35°. La segunda redujo la deriva a 7,39° y generó actividad intensa, pero la concentración siguió en 0,031 y la actualización falló. La variante por compartimentos produjo 25,59° de deriva, concentración 0,030 y error de giro de 36,16°.

## Interpretación

El fallo no es falta de actividad: las variantes de mayor ganancia llegan a contrastes cercanos a uno. El problema es que activan posiciones incompatibles y el vector poblacional se cancela. Por tanto, la red no mantiene un único bump de heading bajo este modelo.

Este resultado impide afirmar que FlyDrone ya tenga memoria neuronal. También muestra que normalizar conteos por neurona o separar solamente PB, EB y NO no basta. Los pares agregados mezclan contactos que pertenecen a wedges, tiles, glomérulos y subregiones distintas; esa estructura local es precisamente la que puede generar excitación cercana, desplazamientos laterales e inhibición amplia.

No se promoverá ninguna de estas variantes al controlador del dron. Repetir búsquedas de ganancias sobre la misma matriz aumentaría el riesgo de ajustar un patrón incorrecto sin resolver la anatomía.

## Productos

- Código: `src/flydrone/neural/recurrent_dynamics.py`.
- Configuraciones: `configs/recurrent_dynamics.yaml`, `configs/recurrent_dynamics_v2.yaml` y `configs/recurrent_dynamics_v3.yaml`.
- Grillas, parámetros elegidos e informes: `results/neural/recurrent_dynamics*/`.

## Próximo paso concreto

El paso indicado se ejecutó mediante matrices de 16 fases y transferencias separadas por neuropilo. El resultado está documentado en [phase-compass-dynamics.md](phase-compass-dynamics.md).
