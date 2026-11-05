# Resultado: gate de navegación con obstáculos v1

Fecha de ejecución: **2026-11-04**. Veredicto: **gate no aprobado**.

El protocolo fue congelado antes de ejecutar 24 episodios pareados en tres geometrías, dos headings y dos modos nuevos. Los 383 inputs congelados conservaron sus hashes después de la ejecución y los 28 artefactos de resultado fueron preservados.

## Veredicto preregistrado

FlyWire v34 aprobó **0/12** episodios completos frente al mínimo de 10/12. Completó 24 metas frente al mínimo de 84. Fallaron 7 de 12 criterios:

- episodios exitosos;
- progreso total;
- mínimo por patrulla;
- mínimo por exploración;
- margen mínimo de 0,15 m;
- intervención acotada de la barrera;
- detención acotada.

Pasaron 5 criterios: déficit total frente al convencional, cero colisiones, cero escapes, actividad neural de yaw y cero saturación de motores.

## Resultados principales

| Métrica | FlyWire v34 | Convencional |
|---|---:|---:|
| Episodios | 12 | 12 |
| Éxitos completos | 0 | 1 |
| Metas totales | 24 | 30 |
| Colisiones | 0 | 3 |
| Holgura mínima | 0,014 m | −0,162 m |
| Máxima fracción detenido | 0,786 | 0,780 |
| Máxima intervención de barrera | 0,726 | 0,690 |

FlyWire quedó seis metas por debajo del convencional, dentro del margen comparativo preregistrado de ocho. No obstante, esto no representa buen desempeño de ninguno: ambos quedaron bloqueados de forma frecuente y el convencional colisionó tres veces.

En patrulla, FlyWire completó 14 metas totales frente a 15 convencionales; su mediana fue 3 frente a 2,5. En exploración, FlyWire completó 10 frente a 15 y ambos tuvieron mediana de una meta. La geometría y el heading inicial modificaron fuertemente el resultado.

## Interpretación

El gate no respalda la generalización operacional de v34 a estas geometrías nuevas. El 4/4 de desarrollo v35 estaba limitado a los dos cursos conocidos.

El fallo no puede atribuirse solamente al circuito FlyWire. El baseline comparte el mismo mapa, evasión, barrera y gestor de metas, y también falló 11/12 episodios, con tres colisiones. La causa dominante probable es una debilidad común de planificación local: seguimiento/liberación de contorno y representación puntual de superficies producen bloqueo prolongado o márgenes insuficientes en geometrías nuevas.

FlyWire mostró una propiedad favorable limitada: evitó colisiones en los 12 episodios mientras el convencional tuvo tres. Esto es descriptivo y no fue una hipótesis de superioridad preregistrada. Su margen mínimo de 0,014 m sigue siendo inaceptable respecto del criterio de 0,15 m.

## Auditoría post-hoc de alcanzabilidad

Después de cerrar y preservar el gate se auditó la geometría contra las metas fijas del gestor. La auditoría no cambia el veredicto, pero limita su interpretación causal.

- En el escenario nominal, 6 celdas de exploración se solapaban con volúmenes inflados de obstáculos.
- En viento positivo, 6 celdas de exploración y un waypoint de patrulla se solapaban.
- En viento negativo, 7 celdas de exploración se solapaban.

Por ejemplo, la celda `(-2, 2)` quedó a 0,50 m del centro `(-2,4, 1,7)` de radio 0,50 m. Con radio del vehículo y aceptación de meta, esa celda es físicamente inaccesible. En los dos episodios nominales de exploración FlyWire, la evasión permaneció activa 93,6–96,1%, hubo dos waypoints de contorno y cero liberaciones; el dron quedó frente a la meta inaccesible. El baseline mostró el mismo patrón.

El protocolo no preregistró una verificación de alcanzabilidad de metas ni el sistema disponía de una regla para abandonar metas persistentemente bloqueadas. Por tanto, el gate evalúa correctamente el sistema completo tal como existía —que no puede manejar metas inaccesibles—, pero no constituye una comparación limpia del steering FlyWire frente al convencional. El cuello de botella principal es compartido y está en el gestor/planificador de ingeniería.

## Próximo ciclo permitido

El gate queda cerrado y no se reajusta. Un ciclo v2 debe usar estos resultados sólo como diagnóstico de desarrollo y reservar otras geometrías para la siguiente evaluación prospectiva.

Prioridades:

1. reproducir los bloqueos con trazas del gate sin modificar el resultado preservado;
2. identificar por qué el waypoint de contorno no se libera o se replantea;
3. reemplazar puntos aislados por segmentos/ocupación continua observada;
4. aplicar la seguridad al mando final mediante una restricción factible;
5. probar la corrección en un conjunto de desarrollo separado;
6. congelar un nuevo gate únicamente después de demostrar generalización en varias geometrías de desarrollo.

No corresponde reincorporar hDeltaB durante este ciclo: el cuello de botella fue compartido por ambos controladores y debe resolverse primero en la capa de planificación y seguridad.

