# Validación multivelocidad de la brújula de fase

## Propósito

El modelo anterior se había ajustado con un único giro de +60°/s. Este ensayo separa la dinámica neuronal del dron y exige que la fase responda a ambos sentidos de giro y a varias velocidades. La intención es corregir la implementación antes de realizar nuevas pruebas de navegación.

## Condiciones implementadas

El barrido usa las transferencias de 16 fases derivadas de contactos FAFB/FlyWire para Δ7, PEG, PEN_a y PEN_b. Evalúa cuatro operadores de velocidad:

- desplazamiento de una cuña descrito en la literatura;
- diferencia PEN_a derecha–izquierda;
- diferencia PEN_b derecha–izquierda;
- combinación PEN_a/PEN_b.

Cada operador se prueba con las matrices FlyWire provisionales y con un control circularizado. La circularización conserva el peso total medio por desfase, pero fuerza simetría rotacional. Es una regularización de ingeniería y **no representa literalmente la anatomía medida**.

El desarrollo utiliza ±30, ±60 y ±90°/s en cuatro rumbos. El segundo conjunto utiliza ±15, ±45 y ±75°/s en otros cuatro rumbos. Se registran error mediano y percentil 90, dirección correcta, monotonicidad, resultante y contraste del bump. Como ese segundo conjunto influyó en decisiones posteriores, desde el 24 de septiembre de 2026 se clasifica como **validación observada**, no como prueba reservada final.

## Resultado inicial y refinamiento

El primer barrido de 112 configuraciones no produjo candidatos que cumplieran simultáneamente los umbrales de desarrollo. La mejor condición fue el control circularizado con el operador de una cuña, ganancia 2 y signo positivo:

- desarrollo: error mediano 21,98°, percentil 90 de 42,08°, dirección 100%;
- validación observada: error mediano 7,61°, percentil 90 de 35,90°, dirección 100%;
- monotonicidad de validación: 1,0;
- resultante mínima de validación: 0,624.

La mejor matriz FlyWire sin circularizar fue peor en desarrollo: error mediano 29,30° y percentil 90 de 44,72°. Los operadores obtenidos directamente de las diferencias PEN todavía no recuperan una actualización angular fiable.

Después se refinó la ganancia tras observar el comportamiento previo. Se evaluaron 224 configuraciones y dos superaron todos los criterios de desarrollo. La ganadora usa circularización, operador de una cuña, ganancia 1,5 y signo positivo. En el conjunto de validación observado obtuvo:

- error mediano: 4,42°;
- percentil 90 y error máximo: 32,42°;
- dirección correcta: 100%;
- monotonicidad: 1,0;
- resultante mínima: 0,629.

La configuración ejecutable quedó guardada como `configs/phase_compass_symmetry_regularized_v3.yaml`. Se mantiene separada del modelo v2 porque su simetría es una modificación de ingeniería. Los 4,42° son un resultado de validación útil para desarrollo, no una estimación imparcial de generalización.

## Interpretación

La simetría rotacional mejora de forma clara la dinámica. Esto indica que el mapa de fase provisional y su heterogeneidad son una fuente importante del bloqueo. No demuestra que el cerebro real necesite conexiones circularizadas; puede significar que la asignación anatómica EPG/PEN a 16 fases todavía es incompleta o que el modelo de tasa omite mecanismos fisiológicos que compensan esa heterogeneidad.

## Próximo paso

Antes de integrarla como candidata principal debe auditarse la asignación anatómica PEN y cuantificarse la magnitud de la circularización. Después se congelará el modelo y se generará, desde una semilla registrada, una prueba prospectiva que se ejecutará una sola vez.
