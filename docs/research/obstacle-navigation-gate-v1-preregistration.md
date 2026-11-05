# Preregistro: gate de navegación con obstáculos v1

Fecha prevista de congelación: **2026-11-04**. Este documento, la configuración, el código, los datos procesados y el ambiente se bloquean por SHA-256 antes de ejecutar un solo episodio del gate.

## Hipótesis operacional

El candidato v34, que conserva orientación y steering/avance FlyWire-grounded mediante EPG–Δ7–PFL3/PFL2 y asigna la estabilización lateral rápida a la capa convencional, puede navegar cursos de obstáculos simulados nuevos con seguridad, progreso y desempeño no marcadamente inferior a un controlador convencional pareado.

PFN→hDeltaB no tiene autoridad traslacional en v34. Percepción de distancia, mapa local, evasión, barrera predictiva, geofence, gestor de metas y estabilización son capas de ingeniería. El gate no prueba visión biológica, planificación de la mosca, superioridad neuronal ni preparación para vuelo físico.

## Separación del desarrollo

El desarrollo v1–v35 utilizó otras geometrías, nombres de escenario, semillas y, en el bloque de obstáculos reciente, heading relativo de 19°. Este gate usa tres geometrías nuevas de seis obstáculos, semillas `20940101–20940103` y headings `-37°` y `137°`. Ningún resultado de estos episodios se inspecciona antes de congelar.

Los parámetros v34 permanecen sin cambios: PFN→hDeltaB ablado, amortiguación lateral de ingeniería 2,0 s⁻¹ y el mismo sensor, evasión y barrera de v35. Un fallo no autoriza modificar el gate; cualquier corrección requerirá un protocolo nuevo y otros casos.

## Diseño

- dos controladores: FlyWire v34 y navegación convencional;
- dos modos: patrulla y exploración;
- tres escenarios: nominal, viento positivo y viento negativo;
- dos headings iniciales;
- 12 episodios por controlador, 24 en total;
- 90 segundos simulados por episodio;
- planta, sensores, seguridad, metas, perturbaciones y semillas pareadas;
- todas las trazas preservadas.

## Métrica primaria

La métrica primaria es el número de episodios FlyWire que cumplen la regla de éxito congelada: al menos 4 metas en patrulla o 5 en exploración, cobertura de exploración al menos 0,25, escape no mayor que 0,02, cero colisión y despeje mínimo de 0,15 m. Deben aprobar al menos 10 de 12 episodios.

## Criterios jerárquicos

El gate pasa sólo si se cumplen todos:

1. al menos 10/12 episodios FlyWire exitosos;
2. al menos 84 metas FlyWire en total;
3. al menos 4 metas en cada episodio FlyWire de patrulla;
4. al menos 5 metas en cada episodio FlyWire de exploración;
5. déficit total frente al convencional no mayor que 8 metas;
6. despeje mínimo FlyWire de al menos 0,15 m;
7. cero colisiones FlyWire;
8. escape máximo no mayor que 0,02;
9. barrera activa como máximo 0,35 de cualquier episodio FlyWire;
10. detención máxima no mayor que 0,10;
11. comando neural de yaw activo al menos 0,99;
12. cero saturación de motores.

La comparabilidad es operacional y limitada; no es una prueba estadística formal de no inferioridad. Los análisis por modo, viento, cobertura, clearance e intervención son secundarios y se reportarán completos.

## Interpretación

Un pase respaldará que v34 generaliza operacionalmente a estos cursos nuevos dentro de su arquitectura híbrida declarada. Un fallo se conservará como resultado negativo. Ningún resultado puede atribuirse a hDeltaB, porque su salida traslacional está ablada.

