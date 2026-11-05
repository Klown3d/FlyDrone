# Preregistro: gate operacional de navegación libre v1

Fecha de congelación prevista: **2026-11-02**. El protocolo se congela antes de ejecutar los casos descritos aquí.

## Hipótesis operacional

Un controlador de alto nivel FlyWire-grounded puede encadenar metas temporales de patrulla y exploración en un quadrotor 6-DoF simulado, con progreso, seguridad y desempeño comparables a un controlador convencional bajo condiciones nominales y perturbadas.

Este gate no prueba planificación, visión o memoria de la mosca y no prueba superioridad de la red neural. El gestor de metas, la captura de destino, el geofence, la fusión sensorial y el estabilizador son capas de ingeniería declaradas.

## Separación de desarrollo

Los desarrollos v1–v3 usaron headings `-103°`, `-47°`, `127°`, `-151°` y `31°`, y semillas `20910101–20910102`. El gate usa headings `-119°` y `73°`, semillas `20920101–20920103` y tres escenarios nuevos. Ningún resultado de estos casos se inspecciona antes de congelar.

## Diseño

- 2 controladores: FlyWire híbrido y navegación convencional;
- 2 modos: patrulla y exploración;
- 3 escenarios: nominal, viento positivo con pérdidas y viento negativo con pérdidas;
- 2 headings iniciales;
- 12 episodios por controlador, 24 en total;
- 90 segundos simulados por episodio;
- mismas metas, planta y perturbaciones pareadas;
- todas las trazas preservadas.

## Métrica primaria

La métrica primaria es el número total de metas completadas por el controlador FlyWire híbrido en sus 12 episodios. Debe ser al menos 90. Además, ningún episodio puede completar menos de 5 metas.

## Criterios jerárquicos

El gate pasa sólo si se cumplen todos:

1. al menos 90 metas híbridas en total;
2. al menos 5 metas híbridas en cada episodio;
3. mediana de al menos 7 metas en patrulla;
4. mediana de al menos 7 metas en exploración;
5. déficit total frente al convencional no mayor que 6 metas;
6. escape máximo del espacio no mayor que 2% del episodio;
7. geofence activo como máximo 25% de cualquier episodio híbrido;
8. captura de meta activa como máximo 20% de cualquier episodio híbrido;
9. comando neural de yaw activo al menos 99% de cada episodio híbrido;
10. actividad hΔB no nula al menos 90% de cada episodio híbrido;
11. dominio de la rama inercial de heading no mayor que 18%;
12. cero colisiones;
13. cero saturación de motores.

No se modifican umbrales ni se reetiquetan episodios después de ejecutar. Un fallo se conserva como resultado negativo y cualquier corrección posterior requiere otro protocolo y casos nuevos.

## Límites de la conclusión

Un pase respaldaría navegación libre operacional simulada con participación continua del circuito FlyWire-grounded y asistencia de seguridad acotada. No demostraría que la mosca planifica la misión, que el connectoma sea superior al controlador convencional, ni que el sistema esté listo para vuelo físico.

