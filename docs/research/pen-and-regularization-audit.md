# Auditoría PEN y atribución de la regularización

## Preguntas

1. ¿El fallo del modelo literal se explica por un desplazamiento simple de índices PEN?
2. ¿Cuánto modifica la circularización las transferencias FlyWire?
3. ¿La estructura FlyWire regularizada conserva propiedades que no aparecen al regularizar fases aleatorias?

Todas las pruebas de este documento son de desarrollo. No sustituyen la evaluación prospectiva definida en `PREREGISTRO.md`.

> **Revisión posterior:** esta auditoría utilizó transferencias PEN dentro de EB. Después se identificó que la comparación funcional correcta debe cruzar la entrada PB con la salida EB. La extracción corregida recupera desplazamientos laterales opuestos de aproximadamente 49–55°. Los resultados siguientes se conservan como registro del diagnóstico anterior y no deben extrapolarse a v4. Véase `cross-compartment-pen-model.md`.

## Auditoría de índices PEN

Se probaron desplazamientos simétricos de −2, −1, 0, +1 y +2 columnas sobre PEN_a, PEN_b o ambas. Para cada hipótesis se evaluaron operadores PEN y el operador de una cuña, ambos signos y múltiples ganancias sobre ±30, ±60 y ±90°/s.

- Candidatos evaluados: 832.
- Candidatos que cumplieron todos los criterios: 0.
- Mejor respuesta cualitativamente coherente: desplazar PEN_b dos columnas en sentido negativo, operador de una cuña, ganancia 1,5.
- Resultado de ese candidato: error mediano 23,45°, p90 55,62°, dirección 100%, monotonicidad 1,0.
- Modelo sin desplazamiento: error mediano 29,30°, p90 44,72°, dirección 100%, monotonicidad 1,0.

Algunos desplazamientos reducen la mediana, pero empeoran mucho los errores de cola. No hay justificación para declarar que ±1 o ±2 columnas corrigen el mapa. La revisión siguiente debe volver a la anatomía y no seleccionar un roll por rendimiento.

## Magnitud de la circularización

| Matriz | Correlación de entradas | Error de Frobenius normalizado | Fracción mínima de peso relocalizado |
|---|---:|---:|---:|
| Δ7 | 0,719 | 0,466 | 0,221 |
| PEG | 0,826 | 0,524 | 0,288 |
| PEN_a izquierda | 0,819 | 0,491 | 0,225 |
| PEN_a derecha | 0,794 | 0,526 | 0,248 |
| PEN_b izquierda | 0,832 | 0,503 | 0,250 |
| PEN_b derecha | 0,821 | 0,520 | 0,248 |

En las matrices EB→EB anteriores, la regularización relocaliza como mínimo entre 22% y 29% del peso, y el cambio normalizado ronda 0,47–0,53. Es una modificación sustancial. Esas cifras deben recalcularse sobre PB→EB; tanto v3 como v4 deben llamarse `FlyWire-informed symmetry-regularized`, no reconstrucción literal.

## Treinta nulos regularizados

Cada nulo conserva el grafo neuronal completo, tipos, lados, contactos y pesos; sólo baraja las fases EPG antes de reconstruir las transferencias. Después recibe la misma circularización y el mismo presupuesto de ajuste que FlyWire.

Resultado de desarrollo:

- FlyWire regularizado: error mediano 12,37°, p90 19,42°, dirección 100%, monotonicidad 1,0; cumple todos los criterios.
- Mediana de los errores medianos nulos: 18,95°.
- Mejor mediana nula: 7,86°.
- Nulos con mediana igual o menor que FlyWire: 3/30; p empírico unilateral 0,129.
- Nulos que cumplen simultáneamente todos los criterios: 0/30; p empírico con corrección +1: 0,032.

La conclusión correcta tiene dos partes: FlyWire no gana si se mira sólo la mediana, pero sí es la única condición que combina error, dirección, monotonicidad y estabilidad bajo los criterios fijados. Este patrón justifica continuar investigando la estructura FlyWire; todavía no permite una afirmación confirmatoria porque el protocolo y los umbrales pertenecen al desarrollo.

## Próximo paso

- Verificar anatómicamente lateralidad y glomérulos PEN célula por célula.
- No elegir más desplazamientos basados en rendimiento.
- Congelar la extracción corregida o declarar el mapa actual como provisional.
- Repetir el contraste FlyWire/nulos dentro de la prueba prospectiva, sin reajustar umbrales.
