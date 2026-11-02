# Corrección anatómica PB→EB de PEN y modelo v4

## Hallazgo

La auditoría anterior calculaba las transferencias de PEN usando contactos de entrada y salida dentro de EB. Esa operación mezclaba el compartimento de entrada con el de salida y hacía desaparecer casi por completo el desplazamiento lateral esperado. No era evidencia de que PEN careciera de desplazamiento; era un error en la definición de la transferencia.

La extracción corregida trata cada neurona PEN como una proyección entre compartimentos:

```text
fase de entrada en PB → neurona PEN → fase de salida en EB
```

Esto concuerda con la anatomía publicada: P-EN recibe principalmente por arborizaciones dendríticas en PB y proyecta hacia EB y NO. La operación sigue siendo una transferencia lineal ponderada por contactos, no una medición de ganancia sináptica ni de dinámica de membrana.

Fuentes primarias:

- Hulse et al. (2021), conectoma del central complex: <https://pmc.ncbi.nlm.nih.gov/articles/PMC9477501/>.
- Wolff et al. (2019), descripción de compartimentos de entrada PB y salida EB/NO de P-EN: <https://elifesciences.org/articles/43482>.
- Evidencia funcional reciente de PEN1 en actualización del bump EPG: <https://elifesciences.org/articles/102230>.

## Datos recuperados de FAFB/FlyWire 783

| Proyección | Neuronas con entrada y salida válidas | Contactos de entrada PB | Contactos de salida EB | Desplazamiento mediano | Resultante mediana |
|---|---:|---:|---:|---:|---:|
| PEN_a izquierda | 10 | 101 | 2617 | +54,32° | 0,884 |
| PEN_a derecha | 10 | 115 | 2678 | −53,63° | 0,888 |
| PEN_b izquierda | 11 | 208 | 2012 | +54,73° | 0,929 |
| PEN_b derecha | 10 | 182 | 1919 | −48,64° | 0,928 |

Los signos opuestos por lado y las resultantes altas recuperan una estructura direccional que no aparecía al usar EB→EB. Los desplazamientos son mediciones del mapa de contactos bajo nuestra asignación de fase; no deben interpretarse como ángulos fisiológicos exactos sin validar glomérulos y subcompartimentos célula por célula.

Los artefactos reproducibles están en:

- `configs/phase_resolved_compass_cross_compartment.yaml`
- `results/neural/phase_resolved_compass_cross_compartment/report.json`
- `results/neural/phase_resolved_compass_cross_compartment/transfers.npz`

## Modelo dinámico v4

La variante integrada usa:

- Δ7 para inhibición recurrente;
- PEG y PEN_b izquierda/derecha para excitación recurrente;
- la diferencia entre las transferencias PEN_a derecha e izquierda para actualizar la fase con velocidad angular;
- contactos PB→EB para PEN;
- circularización de las matrices como regularización de simetría.

En desarrollo multivelocidad, esta configuración obtuvo dirección correcta en ambos sentidos y respuesta monotónica. En los headings de validación ya observados obtuvo error mediano de 12,51°, error p90/máximo de 19,17° y resultante mínima de 0,628. Como esos casos ya fueron inspeccionados, no constituyen la prueba prospectiva final.

La aplicación usa `configs/phase_compass_cross_compartment_v4.yaml`. Durante una comprobación de tres segundos sin señal externa, la actividad permaneció estable, con resultante mínima 0,627 y error final/máximo 23,30°. La suite completa pasó 88 pruebas y el smoke test de la aplicación completó todos sus escenarios.

## Qué está resuelto y qué no

La corrección resuelve el principal error anatómico conocido: PEN debe cruzar de PB a EB para estimar su desplazamiento. También permite que la dirección de actualización provenga de contactos PEN_a reales, en lugar del operador manual de una cuña usado en v3.

La reconstrucción todavía no es literal. Las matrices crudas no superan el gate completo; la variante funcional necesita circularización, que reemplaza heterogeneidad entre columnas por una simetría promedio. En las matrices PEN PB→EB corregidas, esa operación relocaliza entre 57,9% y 60,5% del peso y produce un error de Frobenius normalizado de 0,796–0,824. El cambio es grande y debe considerarse una parte central del modelo, no un ajuste menor. Tampoco conocemos a partir del connectoma estático las ganancias, constantes temporales, signos efectivos de todas las conexiones ni el modelo exacto de integración celular.

## Control con 30 mapas de fase nulos

Se congelaron el operador PEN_a, ganancia 0,5, signo −1, componentes excitatorios y circularización de v4. Luego se barajaron las etiquetas de fase EPG conservando neuronas, contactos y pesos.

| Condición | Error mediano | Cumple todos los criterios |
|---|---:|---:|
| FlyWire v4 | 12,39° | sí |
| Mediana de 30 nulos | 60,04° | 0/30 |
| Mejor nulo | 56,42° | no |

Ningún nulo igualó o mejoró la mediana FlyWire. Con la corrección de conteo +1, el p empírico unilateral es 0,032 tanto para la mediana como para el criterio conjunto. Esto apoya que la relación entre contactos y fases PB→EB contiene estructura útil para v4. Sigue siendo evidencia de desarrollo: las semillas, métricas y configuración ya fueron observadas, y la circularización modifica sustancialmente las matrices.

Por ello, el nombre correcto de v4 es **modelo informado por FlyWire, corregido por compartimentos y regularizado por simetría**. No es todavía una simulación fisiológica completa del cerebro de la mosca.

## Próximo paso concreto

Congelar configuración, hashes y predicciones de v4 y ejecutar una prueba prospectiva nueva de dropout 6DoF una sola vez, sin reajustar parámetros. La afirmación principal deberá separar dos hechos: la organización de fase PB→EB supera los nulos, pero la dinámica funcional depende de una regularización fuerte.
