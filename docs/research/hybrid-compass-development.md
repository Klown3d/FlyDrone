# Brújula híbrida y confianza sensorial

## Objetivo

El gate integrado mostró 26,73° de error mediano durante pérdida de heading con la brújula v4, frente a 3,38° con integración giroscópica. Se probó una fusión que mantiene activa la dinámica EPG/PEN y usa la integración inercial como referencia durante ausencia del landmark.

La salida híbrida combina ambas fases circularmente. El peso neuronal máximo durante dropout es 0,25 y disminuye cuando la fase neuronal discrepa de la inercial. Estos valores y la fusión son decisiones de ingeniería; no se presentan como conectividad biológica. Al reaparecer el landmark, ambos estados se vuelven a anclar.

También se probó un gobernador que reduce el avance hasta 35% cuando falta velocidad o cae la concordancia de heading. PFL3, PFL2 y PFN/hΔB permanecen activos.

## Primer banco de desarrollo

Se ejecutaron 48 vuelos nuevos bajo dos combinaciones de pérdidas, ruido y viento.

| Condición | Éxitos | Error de heading durante dropout | Llegada mediana | Desvío mediano |
|---|---:|---:|---:|---:|
| Híbrida + confianza de avance | 8/12 | ≈4° | 28,903 s | 2,836 m |
| Híbrida sin confianza | 6/12 | ≈4° | 29,793 s | 1,945 m |
| v4 neuronal | 10/12 | 24,7–40,1° | 24,808 s | 1,544 m |
| Red con gyro | 6/12 | 2,6–4,4° | 30,328 s | 1,958 m |

La fusión redujo fuertemente el error angular, pero no mejoró la navegación. El gobernador añadió dos llegadas frente a la híbrida sola, aunque aumentó desvío y siguió por debajo de v4.

## Segunda iteración descartada

Se intentó usar la misma confianza para suspender la corrección lateral hΔB durante la pérdida de velocidad. Obtuvo 7/12 frente a 6/12 sin confianza, pero elevó el desvío mediano a 3,232 m. El viento quedó menos compensado y el cambio fue descartado del código activo.

## Decisión

La brújula híbrida y el gobernador de avance quedan como prototipos de desarrollo, no como controlador principal. No se abre un gate prospectivo: no superaron a v4 en éxitos, tiempo ni desvío. El resultado también demuestra que reducir el error de heading de forma aislada no garantiza mejor navegación cuando PFN/hΔB y el estimador de velocidad interactúan.

El siguiente diagnóstico debe estudiar el error vectorial de PFN/hΔB durante cortes y la transición al recuperar velocidad, en vez de seguir ajustando pesos de fusión de heading.
