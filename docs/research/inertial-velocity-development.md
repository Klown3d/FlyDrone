# Desarrollo de la interfaz de velocidad inercial

## Motivo

Los oráculos y el replay abierto localizaron el cuello de botella en la velocidad estimada y su transformación egocéntrica. La primera confianza graduada no resolvió el problema de forma consistente: obtuvo 8/12 llegadas frente a 7/12 con hDeltaB directo, cambió cinco fallos en éxitos pero también cuatro éxitos en fallos, y aumentó el tiempo de llegada. No se promueve.

La confianza no ocultó completamente el circuito: estuvo por debajo de 0,5 durante una mediana del 14,8% del vuelo, el respaldo dominó el 21,6% del tiempo y la contribución neuronal ponderada fue 78,7%. El resultado negativo indica que atenuar una entrada defectuosa no sustituye una mejor estimación.

## Candidato inercial

Se implementó un estimador que combina diferencias de posición con propagación por aceleración. Durante una pérdida mantiene la velocidad mediante la aceleración medida; cuando vuelve la posición corrige gradualmente sin convertir el desplazamiento acumulado en un pico. Es una capa de ingeniería separada del circuito PFN/hDeltaB.

### Primera prueba: aceleración en coordenadas mundiales

En 12 casos pareados:

| Condición | Éxitos | Error hDeltaB | Error dirección de velocidad | Llegada |
|---|---:|---:|---:|---:|
| Posición sola | 7/12 | 24,85° | 22,24° | 23,90 s |
| Fusión inercial | 12/12 | 7,93° | 7,35° | 17,68 s |
| Convencional | 12/12 | — | — | 17,21 s |

La fusión mejoró el error hDeltaB, la dirección de velocidad, la magnitud y el desvío lateral en los 12 pares. Este banco era favorable porque la aceleración ya estaba expresada en el marco mundial y no contenía sesgo persistente.

### Segunda prueba: acelerómetro corporal, heading estimado, ruido y sesgo

El simulador rotó la aceleración al marco corporal, añadió ruido y sesgo, y la devolvió al marco mundial mediante el heading estimado. El escenario fuerte incluyó 0,18 m/s² de ruido, sesgo de 0,05 y −0,04 m/s², pérdida de heading de 5,3 s y pérdida de posición de 4,8 s.

| Condición | Éxitos | Error hDeltaB | Error dirección de velocidad | Llegada |
|---|---:|---:|---:|---:|
| Posición sola | 6/12 | 24,52° | 23,75° | 25,78 s |
| Fusión inercial corporal | 11/12 | 12,46° | 7,76° | 18,39 s |
| Convencional | 12/12 | — | — | 17,42 s |

La fusión redujo el error hDeltaB en los 12 pares, con una mejora mediana de 10,05° y un intervalo bootstrap exploratorio de 5,93° a 15,18°. Redujo el error de dirección de velocidad en los 12 pares por una mediana de 16,86°. Cinco fallos de posición sola se convirtieron en éxitos; un caso falló con ambos. El desvío lateral mejoró en 8/12, con intervalo bootstrap que incluye cero, por lo que esa métrica todavía no muestra una ventaja consistente.

## Interpretación

La mejora coincide con la predicción del diagnóstico: al mejorar la señal de velocidad mejoran la decodificación hDeltaB, las llegadas y el tiempo. No prueba superioridad neuronal, porque el estimador es convencional y el controlador convencional continúa ligeramente por delante. Sí elimina gran parte de la diferencia sin reemplazar PFN/hDeltaB por un oráculo.

La segunda prueba sigue siendo una simulación simplificada. No modela todavía aceleración específica tridimensional completa, gravedad, calibración térmica, vibraciones de motor ni errores de actitud en roll y pitch. Los intervalos son exploratorios y los escenarios se observaron durante desarrollo.

## Decisión

Promover la fusión inercial corporal como candidato para congelación, pero no como resultado final. Mantener PFL2 y la confianza graduada apagadas. Antes del gate confirmatorio faltan:

1. Implementar un sustituto proporcional no neuronal perfectamente emparejado con PFN/hDeltaB.
2. Medir aceleración específica corporal 3D y transformarla con actitud estimada.
3. Preregistrar una sola métrica primaria, una secundaria clave y escenarios nuevos.
4. Ejecutar al menos 100 vuelos pareados por condición sin reajustar parámetros.

Resultados: `results/simulation/quadrotor_inertial_velocity_development/` y `results/simulation/quadrotor_inertial_body_development/`.
