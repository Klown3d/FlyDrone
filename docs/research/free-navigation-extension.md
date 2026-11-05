# Extensión de navegación libre

Fecha: **2026-11-03**. Estado: **interfaz implementada y gate prospectivo operacional v1 aprobado**.

## Objetivo

Permitir que la aplicación produzca metas temporales sin exigir que el usuario coloque manualmente un único punto. La extensión se ubica antes del controlador neural:

`gestor de comportamiento de ingeniería → meta temporal → circuito FlyWire-grounded → steering/avance/deriva → estabilizador convencional`

El gestor no representa neuronas de decisión, memoria espacial ni visión de la mosca. Su salida es una abstracción computacional explícita.

## Modos implementados

1. **Punto:** conserva la navegación validada hacia una meta fija.
2. **Dirección:** proyecta continuamente una meta tres metros por delante en una dirección elegida por el operador.
3. **Patrulla:** recorre cuatro waypoints configurables y avanza cuando entra en el radio de aceptación.
4. **Exploración:** recorre determinísticamente una grilla de 25 celdas dentro de un área de 8 × 8 m. La semilla y el orden son reproducibles.

Todos los modos producen exactamente la misma interfaz `target_xy_m`; no modifican pesos, dinámica ni readouts del circuito neural.

## Aplicación 3D

- Botón `Modo` y tecla `B`: alternan punto, dirección, patrulla y exploración.
- Botón `Cambiar meta` y tecla `G`:
  - rota la meta en modo punto;
  - rota 60° la dirección manual;
  - salta al siguiente destino en patrulla o exploración.
- El panel muestra modo, índice del objetivo y total de objetivos.
- Las trazas registran modo, índice, destinos visitados, total y procedencia.

## Verificación actual

- 5 pruebas unitarias del gestor;
- integración con navegación existente compilada y probada;
- smoke test de la aplicación completo;
- los cuatro modos produjeron comandos de yaw neuronales finitos;
- dirección, patrulla y exploración cambiaron la meta como estaba previsto;
- el modo punto conservó la meta original;
- la procedencia quedó etiquetada como `engineering_behavior_manager`.

Esto demuestra corrección de la interfaz, no desempeño autónomo prolongado. Todavía no se midieron cobertura, colisiones, eficiencia ni recuperación en modo libre.

## Visión y obstáculos

La exploración actual usa posición simulada y una grilla conocida. No ve el entorno. La aplicación ya posee una capa geométrica convencional para un obstáculo, pero aún no existe percepción general mediante cámara, profundidad o raycasts.

La siguiente fase debe incorporar sensores simulados de distancia y un mapa local limitado. Sólo después corresponde evaluar una cámara simulada y, en una línea científica separada, investigar vías visuales FlyWire-grounded.

## Gate completado

El gate v1 congeló escenarios, headings, semillas y umbrales antes de ejecutar 24 vuelos. Midió:

- cobertura del área;
- colisiones y margen mínimo;
- porcentaje de objetivos temporales completados;
- distancia y tiempo por celda nueva;
- tiempo bloqueado;
- intervención de respaldos de ingeniería;
- actividad y comandos del circuito FlyWire durante cada transición.

El desarrollo v1 obtuvo 6/8 éxitos y reveló bloqueo bajo viento. V2 añadió captura de meta explícita pero expuso escapes en exploración. V3 incorporó un geofence convencional acotado y cerró 16/16 casos de desarrollo. El gate posterior, con casos nuevos, aprobó 13/13 criterios: 106 metas híbridas frente a 109 convencionales, cero escapes/colisiones/saturaciones y participación neural continua. Véanse [Desarrollo v1](free-navigation-development-v1.md) y [resultado prospectivo v1](free-navigation-gate-v1-results.md).

Los modos pueden describirse ahora como navegación libre operacional validada **en esta simulación**. No deben describirse como planificación neural, visión biológica ni preparación para vuelo físico.

## Próximo bloque

Agregar percepción simulada de distancia y obstáculos múltiples como capa de ingeniería separada, con métricas de detección, margen mínimo, colisiones e intervención. Una vía visual FlyWire-grounded es una investigación posterior distinta y no debe inferirse del gestor actual.
