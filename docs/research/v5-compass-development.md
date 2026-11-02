# Desarrollo del compass v5

Estado: **desarrollo; no confirmatorio**.

## Motivo

El diagnóstico prospectivo de 96 vuelos localizó el cuello de botella dominante en la ruta de heading: la condición v4 observada obtuvo 11/24 llegadas, mientras que sustituir sólo el heading por verdad del simulador rescató los 13 fallos. Ese resultado no valida ninguna solución futura.

## Candidato evaluado

El candidato conserva y actualiza el estado del compass EPG/PEN/PEG/Delta7 sustentado por conectividad FlyWire. Durante pérdida de la referencia externa, combina el heading decodificado de ese estado con integración de velocidad angular. El peso neuronal queda limitado por la coherencia entre ambas estimaciones y por la concentración de la actividad.

La integración giroscópica, el límite de peso y la función de coherencia son **decisiones de ingeniería**, no propiedades neuronales medidas. Por lo tanto, aun si mejora la navegación, la afirmación correcta será que una brújula FlyWire-grounded asistida por una capa inercial de ingeniería controla la navegación de alto nivel.

## Separación de datos

Los 24 casos por condición de este desarrollo usan bearings, headings y semillas distintos de los diagnósticos v4/v5 sellados. Se comparan:

1. compass neuronal v4;
2. candidato híbrido v5;
3. control de heading por integración giroscópica, manteniendo iguales PFL3, PFL2 y PFN/hDeltaB.

Estos casos pueden usarse para seleccionar o rechazar el candidato. Después de elegir y congelar un v5 será obligatorio generar una evaluación sellada nueva.

## Criterio de decisión de desarrollo

El candidato sólo merece congelación si mejora claramente la tasa de llegada y el error de heading respecto de v4, sin colisiones ni saturación, y si no queda materialmente por debajo del control giroscópico. No se asignará un valor p ni se formulará una conclusión confirmatoria con este conjunto.

## Resultado de desarrollo

Se ejecutaron 72 vuelos, 24 por condición:

| Condición | Llegadas | Error mediano durante pérdida | Desvío transversal máximo mediano | Eficiencia mediana |
|---|---:|---:|---:|---:|
| Compass neuronal v4 | 16/24 | 70,39° | 4,666 m | 0,377 |
| Híbrido v5 candidato | **24/24** | **4,30°** | **1,844 m** | **0,704** |
| Control giroscópico | **24/24** | **3,76°** | **1,844 m** | **0,702** |

No hubo colisiones ni saturación de motores. En el escenario más difícil, con pérdidas superpuestas, v4 obtuvo 0/8 y tanto el híbrido como el control giroscópico obtuvieron 8/8.

El candidato supera el criterio de selección de desarrollo: recuperó ocho llegadas y redujo fuertemente error y desvío. Sin embargo, su rendimiento casi idéntico al control giroscópico impide atribuir esa robustez a la dinámica neuronal. El resultado demuestra que la asistencia inercial corrige el cuello de botella localizado; no demuestra que el compass FlyWire sea superior a la integración inercial.

Antes de congelar v5 se añadió telemetría explícita para registrar, durante cada pérdida, el peso de la salida neuronal en la fusión, el heading neuronal y su desacuerdo con el giroscopio. Esta instrumentación debe estar activa en la próxima evaluación sellada.

## Auditoría de contribución neuronal

Se repitieron los 24 vuelos del candidato sin cambiar sus parámetros y se guardaron todas las trazas con la telemetría nueva. El resultado de rendimiento se reprodujo exactamente: 24/24 llegadas, error mediano de 4,30° y desvío transversal máximo mediano de 1,844 m.

Durante los intervalos de pérdida, el peso neuronal medio por vuelo tuvo:

- media: 0,066;
- mediana: 0,043;
- mínimo: 0,012;
- máximo: 0,154;
- máximo instantáneo típico: aproximadamente 0,159 sobre un límite configurado de 0,25.

La contribución fue menor en la condición superpuesta más difícil: mediana 0,024. Por lo tanto, la robustez observada pertenece principalmente a la integración giroscópica. El estado neuronal no está desconectado, pero tampoco domina la estimación cuando ambas fuentes discrepan.

## Decisión

Se mantienen dos objetivos separados:

1. **Candidato operacional v5 híbrido:** adecuado para continuar la aplicación 3D y para una futura evaluación sellada de robustez de sistema, con la etiqueta explícita de brújula FlyWire-grounded asistida por inercia.
2. **Línea científica de compass neuronal puro:** todavía debe mejorar la actualización de fase ante giros prolongados y demostrar una contribución causal por encima de un control giroscópico. No se considera resuelta por el híbrido.

Congelar el candidato híbrido no debe cerrar la segunda línea ni autoriza afirmar que la dinámica FlyWire superó al control inercial.
