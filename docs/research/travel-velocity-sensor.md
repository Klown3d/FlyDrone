# Interfaz sensorial de velocidad para PFN/hΔB

## Problema

El primer gate integrado entregaba a PFN/hΔB una velocidad retrasada y ruidosa, pero derivada directamente del estado verdadero del simulador. Eso demostraba la función del circuito, aunque dejaba una entrada privilegiada que no estaría disponible de esa forma en un dron real.

## Implementación

`PositionVelocityEstimator` calcula velocidad mundial por diferencias de posición observada, limita valores extremos y aplica un filtro exponencial. Durante pérdida de la modalidad, la estimación decae con una constante definida. Todo el bloque es una **abstracción sensorial de ingeniería**; no representa flujo óptico biológico ni una población neuronal reconstruida.

La aplicación usa esta estimación para alimentar PFNd/PFNv→hΔB. La velocidad verdadera del simulador ya no cruza esa interfaz.

## Diagnóstico de desarrollo

Se ejecutaron 24 vuelos 6DoF emparejados bajo ruido, demora, viento y una pérdida de velocidad de dos segundos.

| Condición | Llegadas | Desvío máximo mediano | Llegada mediana | Eficiencia mediana |
|---|---:|---:|---:|---:|
| Convencional | 6/6 | 1,031 m | 14,201 s | 0,714 |
| hΔB, velocidad directa | 6/6 | 1,147 m | 14,255 s | 0,699 |
| hΔB, velocidad por posición | 6/6 | 1,306 m | 15,368 s | 0,541 |
| Sin compensación | 0/6 | 4,055 m | — | — |

La interfaz no privilegiada redujo el desvío 67,8% frente a ausencia y costó 0,159 m respecto de la velocidad directa. Conservó todas las llegadas, pero tardó 1,11 s más y perdió eficiencia; esos costos no deben ocultarse.

## Gate prospectivo

El banco nuevo ejecutó 120 vuelos y aprobó 7/7 criterios. La interfaz por posición obtuvo 28/30 llegadas, frente a 30/30 para velocidad directa y control convencional, y 1/30 sin compensación. Redujo 66,9% el desvío frente a ausencia y logró 14/15 llegadas durante una pérdida de velocidad de 3,5 s.

El costo frente a velocidad directa fue 0,336 m de desvío máximo mediano, 1,882 s de llegada y una reducción de eficiencia mediana de 0,184. El resultado permite retirar la velocidad perfecta de la aplicación, pero no afirma que esta estimación sea equivalente a un sistema visual o inercial real.

## Corrección posterior por ruido combinado

El gate anterior corresponde a la versión original de diferencia entre muestras consecutivas. Al combinar pérdidas de heading y velocidad con ruido de posición, esa versión obtuvo 3/12 llegadas aun usando heading giroscópico. Se detectaron dos defectos de interfaz: la readquisición convertía el desplazamiento acumulado durante un corte en un pico de velocidad, y diferenciar ruido de 2–3,5 cm cada 20 ms producía velocidades espurias grandes.

La versión actual descarta la primera diferencia después de readquirir posición y calcula velocidad sobre una ventana de 200 ms antes del filtro exponencial. En los mismos casos de desarrollo, con toda la red y heading giroscópico, pasó de 3/12 a **11/12**. Con brújula v4 alcanzó **12/12**, aunque fue más lenta y menos eficiente que el convencional. Esta ventana se eligió después de observar el diagnóstico y por eso **la versión actual todavía requiere un gate prospectivo nuevo**; el 28/30 histórico no debe atribuirse automáticamente al sensor corregido.

## Artefactos

- Sensor: `src/flydrone/simulation/travel_velocity_sensor.py`.
- Configuración: `configs/travel_velocity_sensor.yaml`.
- Banco: `src/flydrone/simulation/benchmark_travel_velocity_sensor.py`.
- Resultado: `results/simulation/quadrotor_travel_sensor_development/report.json`.
- Resultado prospectivo: `results/simulation/quadrotor_travel_sensor_prospective/report.json`.
