# Preregistro diagnóstico de heading para FlyDrone v5

## Propósito

Evaluar prospectivamente si el patrón observado en un único fallo OOD se repite en una matriz nueva: reemplazar heading por verdad privilegiada del simulador rescata casos que no son rescatados por reemplazar sólo velocidad.

Este protocolo es diagnóstico de desarrollo. Los oráculos no son controladores utilizables, no se comparan como rendimiento convencional y sus vuelos no se agregan a las tasas confirmatorias de v4.

## Congelación

Antes de ejecutar se congelan configuración, código, datos procesados, ambiente y este documento. Se ejecuta una sola vez. No se modificará la brújula v4 entre congelación y corrida.

## Matriz

- 4 bearings nuevos: −149°, −61°, 29° y 119°.
- 2 headings relativos nuevos: −121° y 49°.
- 3 escenarios nuevos: pérdida larga de heading, pérdidas superpuestas y pérdida tardía con readquisición.
- 24 casos por condición y 96 vuelos totales.
- Distancia a meta: 7 m; duración: 50 s.

Condiciones pareadas:

1. `observed_v4`: brújula y velocidad observadas.
2. `diagnostic_true_heading`: heading verdadero para steering y PFN/hΔB; velocidad observada.
3. `diagnostic_true_velocity`: brújula v4; velocidad verdadera sólo para PFN/hΔB.
4. `diagnostic_true_heading_velocity`: ambas entradas verdaderas.

## Predicciones congeladas

El diagnóstico se considera informativo y coherente con la hipótesis de heading sólo si:

1. `observed_v4` produce al menos cuatro fallos, para disponer de casos rescatables.
2. Heading verdadero rescata al menos la mitad de los fallos observados.
3. Heading verdadero rescata más fallos observados que velocidad verdadera sola.
4. La condición combinada no obtiene más de un éxito menos que heading verdadero.
5. Ninguna condición produce colisiones ni saturación de motores.

Si no hay cuatro fallos observados, el resultado será inconcluso, no evidencia de robustez. Si velocidad verdadera rescata tanto o más que heading, la localización previa no generaliza.

## Métricas

Éxito, rescate pareado, distancia terminal, máximo desvío, error de heading durante pérdida, tiempo de llegada, colisiones y saturación. Los análisis por escenario son secundarios.

## Límites

Los casos se eligieron después del piloto v4 pero antes de esta corrida. El protocolo puede guiar desarrollo de v5; no valida una brújula v5 futura. Una evaluación final requerirá otro conjunto sellado después de congelar el modelo nuevo.
