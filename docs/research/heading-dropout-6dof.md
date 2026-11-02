# Brújula recurrente en el dron 6DoF: pérdida temporal de rumbo

## Objetivo

Esta etapa conectó la brújula recurrente de 16 fases con el dron simulado 6DoF. El ensayo pregunta si el estado neuronal puede mantener una estimación de rumbo cuando desaparece temporalmente la señal externa. El modelo neuronal entrega rumbo/steering de alto nivel; la estabilización de actitud y motores sigue siendo convencional.

## Interfaz implementada

La fase interna no posee un cero anatómico equivalente al norte del simulador. Por eso, mientras existe una señal de rumbo válida, el decodificador registra el par `rumbo externo ↔ fase interna`. Durante la pérdida de señal devuelve el último rumbo anclado más el desplazamiento relativo de la fase. Este anclaje es una calibración de ingeniería explícita; no cambia conexiones, pesos ni ganancias de la red.

La velocidad angular procede del mismo sensor simulado, con la misma demora y ruido, para la brújula neuronal y los observadores convencionales que integran giroscopio.

## Protocolo diagnóstico

- 64 vuelos simulados: 4 controladores × 8 condiciones angulares × 2 escenarios.
- Pérdidas de rumbo de 4 s y 8 s.
- Ruido de rumbo: 3° o 5°; ruido de velocidad angular: 2°/s o 3°/s.
- Demora sensorial: 100 ms o 150 ms; viento lateral durante el corte.
- Controladores: FlyWire + brújula recurrente, controlador neuronal con sample-and-hold, PID + giroscopio y proporcional + giroscopio.

Los casos se usaron para diagnosticar la interfaz y, después de observar el primer fallo absoluto de fase, para validar el anclaje. Por ello **no constituyen una confirmación final independiente**.

## Resultados

Todos los controladores alcanzaron la meta en 16/16 vuelos. Ese éxito terminal no significa que la brújula neuronal estimara correctamente el rumbo durante el corte.

| Controlador | Éxito | Error mediano, corte 4 s | Eficiencia mediana 4 s | Error mediano, corte 8 s | Eficiencia mediana 8 s |
|---|---:|---:|---:|---:|---:|
| FlyWire + brújula | 16/16 | 119.65° | 0.788 | 130.58° | 0.582 |
| Neural + mantener último rumbo | 16/16 | 30.94° | 0.757 | 43.76° | 0.529 |
| PID + giroscopio | 16/16 | 0.93° | 0.893 | 4.65° | 0.741 |
| Proporcional + giroscopio | 16/16 | 0.89° | 0.865 | 4.79° | 0.731 |

La red recupera la navegación cuando vuelve la señal externa, pero todavía no funciona como brújula online. Los baselines de giroscopio son claramente superiores en precisión y eficiencia.

## Causa identificada

El modelo dinámico v2 fue seleccionado con una única velocidad de desarrollo: +60°/s durante 1 s. Un barrido posterior mostró una respuesta no monotónica y asimétrica entre −90°/s y +90°/s. Por ejemplo, la misma configuración puede aproximar un giro de +60° y fallar para +30°, −30° o +90°.

La prueba de advección circular simple tampoco es aceptable: la recurrencia heterogénea del mapa provisional fija el bump a fases preferidas y vence el desplazamiento. Convertir la salida en una integración convencional de giroscopio ocultaría el fallo y eliminaría la atribución neuronal.

## Interpretación científica

Este resultado demuestra integración de software y recuperación tras pérdida sensorial, pero **no demuestra navegación superior ni una brújula funcional derivada del connectoma**. La persistencia estática del bump sí se conserva en el ensayo aislado. La transformación continua de velocidad angular a desplazamiento de fase sigue sin resolverse.

## Próximo paso concreto

Antes de repetir vuelos, hay que crear un ensayo de desarrollo separado que cubra ambos signos y varias velocidades angulares. Debe comparar: (1) los subtipos PEN por compartimento, (2) matrices circularizadas como control de simetría, y (3) el mapa FlyWire sin circularizar. Sólo una configuración que muestre fase aproximadamente monotónica, signo correcto y error acotado en velocidades reservadas pasará a una nueva evaluación 6DoF con bearings y semillas inéditos.

Archivos reproducibles: `configs/quadrotor_heading_dropout.yaml`, `results/simulation/quadrotor_heading_dropout/episodes.csv`, `summary.csv` y `report.json`.
