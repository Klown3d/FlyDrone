# Controlador integrado bajo pérdidas sensoriales

## Pregunta

¿Los módulos que funcionaron por separado siguen navegando cuando coinciden viento, ruido, demora y pérdidas temporales de heading y velocidad?

## Banco de desarrollo

Se ejecutaron 48 vuelos sobre seis geometrías y dos escenarios combinados. El sistema completo usó brújula v4, PFL3, PFL2 para giro y avance, PFN/hΔB y velocidad obtenida de posiciones observadas. Se comparó contra ausencia de PFL2, ausencia de hΔB y navegación convencional.

El primer resultado fue negativo: sistema completo 4/12, sin PFL2 5/12, sin hΔB 0/12 y convencional 12/12. hΔB era claramente necesario bajo viento, mientras PFL2 no explicaba el fallo.

## Diagnóstico causal

Extender el vuelo de 28 a 35 s sólo elevó el sistema completo a 6/12. Reemplazar la brújula v4 por integración giroscópica redujo el error de heading fuerte de 38,6° a 4,75°, pero logró apenas 3/12 después de corregir la readquisición. En cambio, dar velocidad directa a la misma red produjo 12/12. Esto localizó el bloqueo principal en el estimador por posición.

La diferencia entre posiciones consecutivas amplificaba ruido centimétrico al dividirlo por 20 ms. Además, la primera muestra después de un corte generaba un pico falso. Se corrigieron ambas causas mediante readquisición sin derivada y una ventana de diferencia de 200 ms.

## Resultado posterior a la corrección

| Condición | Éxitos | Llegada mediana | Eficiencia mediana | Desvío mediano |
|---|---:|---:|---:|---:|
| Red completa, brújula v4, sensor corregido | 12/12 | 21,917 s | 0,469 | 1,297 m |
| Red completa, gyro, sensor corregido | 11/12 | 24,042 s | 0,388 | 1,444 m |
| Red completa, gyro, velocidad directa | 12/12 | 16,470 s | 0,711 | 1,193 m |
| Convencional | 12/12 | 16,189 s | 0,686 | 1,149 m |

La red integrada recuperó todas las llegadas con v4, pero permanece 5,73 s detrás del convencional y recorre trayectorias menos eficientes. El error de heading durante la pérdida fuerte sigue alto con v4: 39,5° de mediana frente a aproximadamente 4° con gyro. El resultado es desarrollo, no confirmación.

## Decisión

Se conserva el sensor corregido porque elimina artefactos físicos. Los resultados prospectivos de la versión anterior permanecen históricos. Antes de promover el sistema integrado se requiere un conjunto nuevo, congelado y no usado durante esta corrección. La brújula v4 continúa siendo el segundo límite principal y no debe presentarse como superior a un observador giroscópico.

## Gate prospectivo posterior

Se congelaron 30 casos inéditos por condición y se ejecutaron 120 vuelos. El gate integrado falló: aprobó 4/8 criterios.

| Condición | Éxitos | Llegada mediana | Eficiencia | Desvío mediano |
|---|---:|---:|---:|---:|
| FlyWire completo | 22/30 | 25,284 s | 0,436 | 1,366 m |
| Sin PFL2 | 22/30 | 22,840 s | 0,478 | 1,407 m |
| Sin hΔB | 0/30 | — | — | 5,540 m |
| Convencional | 30/30 | 16,765 s | 0,670 | 1,208 m |

El sistema completo mantuvo 14/15 llegadas en perturbación moderada, pero sólo 8/15 en la fuerte. hΔB mostró dependencia causal clara: quitarlo eliminó todas las llegadas y cuadruplicó aproximadamente el desvío. PFL2 no cambió la cantidad de éxitos y añadió 2,44 s frente a la condición sin PFL2. El sistema quedó 8,52 s detrás del convencional. La brújula v4 acumuló 26,73° de error mediano durante dropout, frente a 3,38° convencional.

La conclusión actual es mixta: el sensor corregido y hΔB aportan una compensación funcional medible, pero el controlador integrado todavía no tolera de forma suficiente pérdidas sensoriales fuertes y no está listo para congelarse como versión final.
