# Avance de alto nivel modulado por PFL2

## Alcance

Esta extensión usa el índice de actividad PFL2 ya derivado de la conectividad FlyWire para decidir cuánto debe avanzar el dron 6DoF. PFL3 conserva la selección del sentido de giro. El estabilizador convencional sigue resolviendo actitud, altura y mezcla de motores.

La evidencia experimental respalda que PFL2 está relacionada con la representación de la dirección opuesta a la meta y con la reducción de avance durante giros grandes. No conocemos una función fisiológica que transforme directamente esa actividad en metros por segundo. Por eso la regla implementada es una interfaz de ingeniería explícita:

`fracción de avance = (1 - índice antimeta PFL2)²`

La velocidad final también queda limitada por la distancia a la meta. La conectividad y la actividad que originan el índice son del modelo PFL2; el exponente, la escala métrica y el frenado por distancia no son propiedades neuronales medidas.

## Prueba de desarrollo

La comparación inicial incluyó 32 vuelos. PFL2 y el frenado angular alcanzaron 16/16 metas. PFL2 tuvo un costo mediano de 0,246 s, 0,012 en eficiencia y 0,008 m en desvío transversal. Estos datos se usaron para congelar un gate de equivalencia, no para reajustar la regla.

## Gate prospectivo

El protocolo se registró antes de ejecutar y fijó 30 casos por condición bajo dos escenarios nuevos de ruido, demora y viento. Los 60 vuelos quedaron en `results/simulation/quadrotor_pfl2_advance_prospective/`.

| Resultado | Angular | PFL2 |
|---|---:|---:|
| Llegadas | 30/30 | 30/30 |
| Tiempo mediano | 12,784 s | 12,806 s |
| Eficiencia mediana | 0,742 | 0,737 |
| Desvío transversal mediano | 1,079 m | 1,083 m |
| Saturación máxima | 0% | 0% |

PFL2 aprobó 6/6 criterios. El costo fue 0,022 s, 0,00492 de eficiencia y 0,0044 m de desvío, sin perder llegadas. Esto demuestra que, en los escenarios probados, la señal PFL2 puede reemplazar al cálculo angular de avance con desempeño prácticamente equivalente.

## Integración visible

La aplicación activa el avance PFL2 por defecto en modo 6DoF. La línea de actividad muestra `avance x…` y el botón **Avance PFL2 ON/OFF** permite ejecutar la ablación contra la regla angular. Cada registro guarda la velocidad deseada, la fracción aplicada y qué controlador estaba activo.

## Límite de la conclusión

El resultado valida una interfaz computacional, no una ley biológica de velocidad. Tampoco demuestra todavía que la topología exacta de PFL2 sea imprescindible para el desempeño: esa atribución requiere comparar la conectividad real con nulos que preserven actividad y grado. La navegación todavía usa capas convencionales para estabilidad física, altura, parada, evasión de obstáculos y seguridad.
