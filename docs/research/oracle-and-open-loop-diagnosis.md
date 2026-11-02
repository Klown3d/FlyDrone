# Diagnóstico causal de la cadena PFN/hDeltaB

## Estado

Diagnóstico de desarrollo completado el 11 de octubre de 2026. No constituye todavía un gate confirmatorio. PFL2 permaneció apagada. Los valores verdaderos del simulador se usaron solamente como oráculos para localizar el fallo; no son entradas válidas para el controlador final.

## Pregunta

El controlador integrado había alcanzado 22/30 vuelos, frente a 30/30 del convencional. El objetivo de estas pruebas fue separar cuatro posibles fuentes: heading, velocidad, transformación egocéntrica y readout final. Todas las variantes usaron los mismos casos, semillas, ruido y pérdidas.

## Oráculos en lazo cerrado

| Condición | Éxitos | Error mediano de dirección hDeltaB | Llegada mediana |
|---|---:|---:|---:|
| Señales estimadas | 7/8 | 26,74° | 26,32 s |
| Heading verdadero | 8/8 | 28,09° | 28,02 s |
| Velocidad verdadera | 8/8 | 4,42° | 16,93 s |
| Heading y velocidad verdaderos | 8/8 | 5,97° | 16,90 s |
| Ángulo egocéntrico verdadero | 8/8 | 8,71° | 16,98 s |
| Dirección allocéntrica verdadera en el readout | 8/8 | 0,00° | 16,93 s |

Reemplazar solamente el heading no redujo el error interno. Reemplazar solamente la velocidad produjo casi todo el beneficio de reemplazar ambas entradas. El readout final alcanzó buen rendimiento con información correcta. La causa dominante es, por tanto, la velocidad estimada y su transformación a movimiento egocéntrico, no la brújula ni la regla final de aceleración.

## Replay abierto

PFN/hDeltaB se ejecutó en modo sombra sobre trayectorias controladas convencionalmente. Su salida no se aplicó al dron. La máxima separación entre trayectorias pareadas fue exactamente 0,0 m, lo que verifica el desacople físico.

| Condición de sombra | Error mediano hDeltaB | Recuperación mediana |
|---|---:|---:|
| Señales estimadas | 9,26° | 1,88 s |
| Heading verdadero | 9,67° | 1,89 s |
| Velocidad verdadera | 4,18° | 0,00 s |
| Ángulo egocéntrico verdadero | 5,41° | 0,08 s |

Con señales estimadas, los ocho episodios mostraron una divergencia sostenida superior a 30°: siete comenzaron durante la pérdida de posición y uno antes. El mismo patrón apareció con heading verdadero. Con velocidad verdadera no apareció divergencia sostenida. El error existe antes de que hDeltaB pueda modificar la trayectoria; el lazo cerrado lo amplifica, pero no lo origina.

## Instrumentación

Las trazas se guardan a 50 Hz e incluyen posición real y observada, velocidad real y estimada, señal de heading cruda, neuronal e inercial, entradas efectivas entregadas al circuito, actividad de 61 PFN y 18 hDeltaB, dirección decodificada, corrección lateral, disponibilidad y edad de la posición, y motores. El informe distingue el error crudo del sensor del error de la entrada efectiva cuando se usa un oráculo.

Resultados completos:

- `results/simulation/quadrotor_oracle_diagnostics/report.json`
- `results/simulation/quadrotor_oracle_diagnostics/episodes.csv`
- `results/simulation/quadrotor_open_loop_replay/report.json`
- `results/simulation/quadrotor_open_loop_replay/episodes.csv`

## Solución preparada y trabajo pendiente

Se implementó una primera capa de confianza graduada, declarada explícitamente como ingeniería. Reduce confianza con la antigüedad de la posición, el desacuerdo de heading y la incoherencia direccional; baja rápido, recupera lento, conserva una corrección de respaldo que decae, y limita magnitud y tasa de cambio. Sus pruebas unitarias pasaron, pero la evaluación de vuelo fue interrumpida antes de completarse y no se reportan datos parciales.

La comparación de confianza se completó después: produjo 8/12 llegadas frente a 7/12 con hDeltaB directo y 12/12 convencionales, pero intercambió cinco fallos por éxitos y cuatro éxitos por fallos. No se promovió. La fusión posterior con aceleración corporal ruidosa y sesgada alcanzó 11/12 frente a 6/12 con posición sola, reduciendo en los 12 pares el error de velocidad y hDeltaB. El desarrollo continúa en [inertial-velocity-development.md](inertial-velocity-development.md).
