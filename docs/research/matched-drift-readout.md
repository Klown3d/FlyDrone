# Control emparejado de PFN/hDeltaB

## Pregunta

La ablación sin hDeltaB deja al controlador sin información de deriva y no prueba que la conectividad neuronal sea superior. Para responder esa crítica se construyó un sustituto no neuronal que recibe exactamente la misma velocidad estimada, heading, meta, umbral y ganancia. La única diferencia es el readout: FlyWire usa PFNd/PFNv→hDeltaB; el sustituto usa directamente la dirección del vector de velocidad y la misma regla de aceleración lateral.

## Desarrollo con aceleración corporal 2D

Las tres condiciones alcanzaron 12/12 llegadas. En la comparación pareada, FlyWire fue 0,084 s más lento, tuvo 0,028 menos eficiencia y 0,337 m más desvío lateral mediano que el sustituto. Los intervalos bootstrap exploratorios favorecieron al sustituto para eficiencia y desvío.

## Desarrollo con fuerza específica corporal 3D

La interfaz posterior simula fuerza específica corporal tridimensional, gravedad, inclinación, ruido y sesgo. Roll y pitch proceden del estimador convencional del estabilizador; yaw procede del estimador seleccionado.

| Condición | Éxitos | Llegada mediana | Eficiencia | Desvío máximo mediano |
|---|---:|---:|---:|---:|
| FlyWire hDeltaB | 12/12 | 19,40 s | 0,489 | 2,16 m |
| Velocidad directa emparejada | 12/12 | 18,93 s | 0,520 | 1,74 m |
| Navegación convencional | 12/12 | 17,75 s | 0,631 | 1,56 m |

En pares, FlyWire fue 0,154 s más lento, tuvo 0,034 menos eficiencia y 0,313 m más desvío lateral mediano. FlyWire fue más rápido sólo en 1/12 casos, más eficiente en 1/12 y tuvo menos desvío en 3/12. Ambos llegaron en los 12 casos.

## Conclusión permitida

PFN/hDeltaB proporciona una representación funcional e interpretable de dirección de desplazamiento y permite navegar bajo ruido, sesgo y pérdidas. No existe evidencia de que mejore el rendimiento frente a una transformación directa de la misma velocidad. En estos bancos, el sustituto emparejado fue ligeramente mejor.

Esto no elimina el valor del connectoma: los controles de fase y conectividad muestran que su organización interna importa para obtener la representación neuronal observada. Sí impide usar el rendimiento como argumento de superioridad. El aporte demostrado es trazabilidad anatómica, actividad neuronal interpretable y función comparable, no control óptimo.

Resultados completos:

- `results/simulation/quadrotor_matched_drift_readout_development/`
- `results/simulation/quadrotor_matched_drift_readout_3d_development/`

## Próximo control

El gate confirmatorio debe comparar FlyWire intacto, sustituto directo, conectividad PFN/hDeltaB permutada y controlador convencional con 100 vuelos pareados por condición. Ninguna condición podrá reajustarse después de congelar el preregistro.
