# Modelo neuronal PFL3 de referencia

Estado: implementado y verificado el 2026-09-13. Este modelo evalúa una transformación neural de orientación y objetivo. No está conectado a un simulador ni produce comandos físicos.

## Alcance

El modelo contiene las 24 identidades PFL3 extraídas de FlyWire FAFB 783. Cada neurona se asocia provisionalmente con una de 12 columnas funcionales y con el LAL al que proyecta. Las tasas se calculan con el modelo algebraico publicado por [Mussells Pires et al. (2024)](https://doi.org/10.1038/s41586-023-07006-3):

`r_i = a · log(1 + exp(b · (cos(H − Hpref_i) + d·cos(G − Gpref_i) + c)))`

`H` es heading, `G` es objetivo y los ángulos preferidos dependen de la columna y del lado PFL3. El readout es la suma de tasas que proyectan al LAL derecho menos la suma que proyecta al izquierdo.

## Procedencia de cada elemento

| Elemento | Valor | Estado |
|---|---:|---|
| PFL3 | 24 root IDs FAFB 783 | Dato FlyWire |
| Organización | 12 pares PFL3 | Inferencia geométrica compatible con la anatomía publicada |
| `d` | 0.63 | Ajuste publicado |
| `a` | 29.23 Hz | Ajuste publicado |
| `b` | 2.17 | Ajuste publicado |
| `c` | −0.70 | Ajuste publicado |
| `Hpref`, `Gpref` | Listas de 24/12 ángulos | Modelo connectómico publicado; asignación a root IDs FAFB inferida |
| Readout | R−L | Respaldado por fisiología y modelo publicado |
| Constante temporal | Ninguna | El modelo es estacionario; no se inventó dinámica |
| Conversión a yaw | Ninguna | Se deja para la interfaz de control posterior |

## Qué demuestra la verificación

El barrido determinista de heading con objetivo 0° genera cero R−L en 0°, simetría impar con error numérico `2.62×10⁻14 Hz` y una magnitud máxima de `134.51 Hz` para la suma poblacional diferencial. Se guardaron las 24 tasas por muestra, además de las sumas izquierda y derecha, en `results/neural/published_pfl3_reference/heading-sweep.csv`.

Esta prueba confirma que la implementación reproduce la transformación del modelo de referencia y que cada valor puede visualizarse sobre el esqueleto 3D de su root ID. No prueba todavía que los pesos sinápticos de FlyWire sean necesarios para la transformación.

## Riesgos y pruebas pendientes

- El orden de root IDs PFL3 por columna es inferido desde esqueletos. Se probarán permutaciones y el esquema alternativo de 9 columnas.
- Los parámetros publicados provienen de ajustes en moscas caminando. Su valor no se extrapolará directamente a dinámica de vuelo.
- La variante feedforward posterior ya usa contactos FlyWire y compara FC2B+FC2C, cada subtipo por separado y FC2A como control; sus resultados están en [connectome-model-results.md](research/connectome-model-results.md).
- La propagación explícita EPG→Δ7 no reprodujo el mapa PFL3 y quedó rechazada como candidato funcional; el resultado y sus límites están en [epg-delta7-audit.md](research/epg-delta7-audit.md).
- Los signos y la normalización de contactos deben quedar configurados y etiquetados por procedencia.
- Una futura constante temporal será tomada de datos o declarada como parámetro de ingeniería; no se presentará como propiedad biológica medida.

## Visualización 3D prevista

El archivo de actividad usa columnas `rate_hz_<root_id>`, por lo que cada frame colorea directamente el esqueleto 3D correspondiente. El visor actual muestra las 24 PFL3 y permite alternar entre este modelo de referencia y el primer modelo ponderado por FlyWire. La versión posterior añadirá PB/FB/EB/LAL como contexto, EPG, Δ7 y FC2, además del cuerpo simulado.
