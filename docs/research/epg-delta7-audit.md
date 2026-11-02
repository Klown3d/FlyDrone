# Auditoría explícita EPG→Δ7→PFL3

Fecha: 2026-09-14. Estado: candidato feedforward rechazado. Este resultado es un gate científico: no se incorpora la etapa EPG al controlador hasta resolver los datos faltantes.

## Pregunta

¿La propagación de una señal de heading por los contactos reales EPG→Δ7→PFL3 de FlyWire 783 reproduce la topografía de heading PFL3 usada por el modelo publicado?

## Corrección del mapa EPG

El análisis anterior dividía las 47 EPG en 18 grupos usando sólo la mediana en x de sus esqueletos dentro del PB. Eso era incorrecto por dos motivos:

1. El código de análisis de [Mussells Pires et al. (2024)](https://doi.org/10.5281/zenodo.10232698) marca como ausentes para EPG las ROI 1 y 18 de la máscara experimental de 18 glomérulos. EPG ocupa los 16 glomérulos centrales.
2. Los extremos del PB de FAFB se curvan en profundidad. Esqueletos de glomérulos vecinos pueden compartir x y separarse en y/z.

La nueva asignación agrupa las medianas xyz mediante Ward en 16 grupos y recorre el arco 3D del PB. Produce PB02–PB17 con 2–4 EPG por columna y grupos morfológicamente coherentes con las anotaciones DM1–DM4. Sigue siendo una **inferencia geométrica**, no una etiqueta experta ni una medición de densidad sináptica.

Los ángulos EPG se derivaron de Extended Data Fig. 5 y del código archivado del artículo: separaciones de 45° dentro de cada lado y 22,5° entre los dos glomérulos centrales. La fase absoluta entre el bump y el heading es arbitraria entre animales; por ello la auditoría permite ajustar una sola fase global y reporta ese ajuste.

## Datos FlyWire usados

Sólo se incluyeron conexiones en el neuropilo PB:

| Proyección | Pares con conexión | Contactos | Neuronas postsinápticas alcanzadas |
|---|---:|---:|---:|
| EPG→Δ7 | 928 | 3.582 | 40/40 Δ7 |
| Δ7→Δ7 | 980 | 3.158 | 40/40 Δ7 |
| Δ7→PFL3 | 238 | 2.303 | 24/24 PFL3 |
| EPG→PFL3 | 100 | 654 | 24/24 PFL3 |

Los signos usados son EPG excitatorio y Δ7 inhibitorio, de acuerdo con las identidades de neurotransmisor respaldadas por la literatura y las predicciones del dataset. El conteo de contactos se normaliza por neurona receptora dentro de cada corriente; esta normalización es una decisión computacional, no una eficacia sináptica medida.

## Condiciones y resultado

Se probaron tres transferencias lineales mínimas:

- EPG→Δ7→PFL3;
- EPG→PFL3 directa;
- ambas vías combinadas según la fracción de contactos EPG y Δ7 que recibe cada PFL3.

| Condición | Residuo medio de topografía PFL3 tras una fase global | Error medio de equilibrio | Dirección correcta | Correlación con referencia |
|---|---:|---:|---:|---:|
| Vía Δ7 | 82,18° | 84,91° | 52,21% | 0,088 |
| EPG directa | 85,55° | 87,76° | 51,53% | 0,070 |
| Combinada por contactos | 83,04° | 85,70° | 51,86% | 0,076 |

La fase global se ajustó contra el mapa PFL3 provisional, por lo que estos valores ya son favorables al candidato y no constituyen validación independiente. Aun así, ninguna ruta supera de manera útil el nivel cercano al azar. El resultado no demuestra que el circuito biológico falle; demuestra que **nuestras asignaciones por esqueleto, el modelo lineal feedforward y los conteos agregados no bastan para reconstruir su función**.

También cambia la interpretación del experimento Δ7/FC2→PFL3 anterior. Sus ángulos Δ7 se obtuvieron a partir de las propias salidas Δ7→PFL3; por eso aquel buen resultado era compatibilidad interna y no una reconstrucción independiente de la señal desde EPG.

## Recurrencia Δ7

La recurrencia Δ7→Δ7 es grande y está presente en los datos: 3.158 contactos PB. No se simuló. El connectoma no determina por sí solo la ganancia recurrente, la constante de fuga, la función de transferencia ni el estado basal. Elegirlos para mejorar el resultado equivaldría a introducir propiedades no respaldadas.

## Gate y próximo paso

No se conectará todavía esta etapa a sensores ni a un dron. El próximo paso concreto es extraer las coordenadas de las sinapsis PB de los root IDs seleccionados. Con ellas se podrá:

1. asignar glomérulos usando dónde ocurren EPG→Δ7, Δ7→Δ7 y Δ7/EPG→PFL3;
2. validar o corregir de forma independiente las columnas PFL3;
3. separar contactos dentro del PB de ramas de paso;
4. construir una matriz por glomérulo antes de introducir recurrencia.

La tabla completa `flywire_synapses_783.feather` pesa 9,49 GB. La alternativa práctica es una consulta CAVE autenticada de los 195 root IDs o una exportación seleccionada desde Codex. El repositorio no contiene credenciales.

El extractor selectivo ya está preparado en `flydrone.data.acquire_synapse_coordinates`. Usa la vista fijada `valid_synapses_nt_np_v6`, divide los 195 IDs en lotes reanudables, exige que ambos participantes pertenezcan al circuito y conserva sólo PB. Requiere `caveclient` en Python 3.12 y la variable de entorno `FLYWIRE_CAVE_TOKEN`; el token nunca se escribe en disco ni en el manifiesto.

## Reproducibilidad

```powershell
.\.venv\Scripts\python.exe -m flydrone.morphology.analyze
.\.venv\Scripts\python.exe -m flydrone.neural.evaluate_epg_delta7
```

Cuando exista una credencial CAVE, la extracción se ejecuta desde un entorno Python 3.12 con:

```powershell
python -m flydrone.data.acquire_synapse_coordinates
```

El informe de máquina está en `results/neural/epg_delta7_audit/report.json`; las tres trazas guardan la tasa de cada PFL3 para toda combinación evaluada de heading y objetivo.
