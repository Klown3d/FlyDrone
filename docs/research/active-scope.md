# Alcance activo: robustez y aplicación 3D

El alcance actual quedó cerrado al disponer de una aplicación 3D nativa verificable y un [análisis final integrado](final-analysis-integrated-v4.md).
Presentación pública, videos, publicación, instalador y dron físico quedan
pospuestos por decisión del usuario.

## Punto actual

- Circuito FAFB 783 extraído y navegación integrada v4 evaluada.
- Cuatro gates prospectivos de atribución cerrados y preservados.
- Aplicación nativa con vuelo interactivo y morfologías completas.
- Comparador 3D de ensayos preservados de los tres gates de steering.
- Comparador estable durante 16 vuelos completos, con cámaras general/A/B,
  selección individual de neuronas e identidad FlyWire visible.
- Diagnóstico local completo: 28 vuelos, 4/4 por variante con ganancias y τ ±20%.
- Piloto OOD completo: FlyWire 5/6, convencional 6/6, fallo preservado durante
  pérdidas sensoriales largas. No sustituye una evaluación amplia.
- Diagnóstico causal local del fallo OOD: reproducción exacta; heading verdadero
  rescata el caso, velocidad verdadera sola no. Es evidencia de un caso, no un
  resultado poblacional ni una nueva validación.
- El diagnóstico por oráculos está preservado con hashes y disponible en el
  comparador 3D como una categoría explícitamente post-hoc.

## Criterios de cierre de robustez

1. Informar sensibilidad de steering, deriva y constante temporal, con casos
   pareados y todos los resultados conservados.
2. Ejecutar un piloto fuera del régimen previo, incluido viento de signo
   invertido, mayor distancia y pérdidas sensoriales más largas.
3. Declarar el tamaño pequeño de estos diagnósticos y separar el piloto de
   una futura prueba confirmatoria con generador sellado.
4. Mantener explícitas la regularización de brújula y las capas convencionales.

## Criterios de cierre de aplicación

1. Vuelo interactivo nativo y reproducción de ensayos guardados accesibles
   desde la aplicación principal.
2. Geometría completa de las 286 morfologías descargadas, con filtros y cámara.
3. Pausa, reinicio, búsqueda temporal y velocidad de reproducción sincronizados.
4. Comparación intacto/nulo del mismo caso y estadísticas globales visibles.
5. Distinguir actividad guardada, reconstrucción algebraica y actividad no
   disponible, evitando inventar propagación por ramas.
6. Validar integridad de archivos y coincidencia del comando reconstruido
   con el comando de steering guardado.
7. Documentar límites y verificar renderizado y controles.

Pendientes posteriores a este bloque: ampliar casos con ambas trazas guardadas
en los gates. La comparación 3D de ablaciones, interacción de cámara e
inspección individual ya están implementadas. La
selección actual de casos está limitada por la política histórica de guardar
todas las fallas y sólo el primer éxito de cada condición; no se calcula una
tasa de éxito a partir de los casos disponibles para reproducción.
El piloto OOD sí conserva los seis pares completos y se puede comparar con
el convencional en 3D.

## Cierre

Las fases 9–11 se consideran cerradas para v4, no para una afirmación de robustez universal. La sensibilidad global, la validación sellada de v5, el empaquetado y el dron físico permanecen fuera de este cierre. El diagnóstico OOD amplio y el desarrollo inicial de v5 ya se ejecutaron, pero no constituyen validación de v5.

## Estado inmediato del compass v5 (2026-10-31)

- El diagnóstico prospectivo localizó el cuello de botella dominante en heading.
- Un candidato híbrido que conserva el estado FlyWire-grounded y lo fusiona con integración giroscópica pasó 24/24 casos de desarrollo, frente a 16/24 para v4 neuronal puro.
- La auditoría mostró un peso neuronal medio de 0,066 durante dropout; la mejora operacional se atribuye principalmente a la asistencia inercial.
- Próximo paso operacional: congelar el candidato híbrido y diseñar un gate sellado nuevo.
- Próximo paso científico: mejorar y probar por separado el compass neuronal puro; no usar el éxito híbrido como evidencia de superioridad neuronal.

