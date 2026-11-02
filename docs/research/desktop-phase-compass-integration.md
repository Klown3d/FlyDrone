# Integración de la brújula de fase en la aplicación

## Estado

La aplicación de escritorio usa ahora `phase_compass_cross_compartment_v4` como estimador de heading que alimenta el steering EPG–Δ7–FC2–PFL3. PEN se extrae entre su entrada en PB y su salida en EB; la actualización angular usa la diferencia lateral PEN_a derivada de esos contactos. La variante está rotulada como regularizada y no reemplaza la reconstrucción FlyWire literal en los análisis científicos.

## Flujo de control

```text
heading sensorial disponible ─┐
                              ├─> brújula de fase regularizada ─> heading neuronal ─> steering
velocidad angular simulada ───┘
```

Cuando la señal externa está disponible, ésta calibra la relación entre fase interna y coordenadas del mundo. Cuando se interrumpe, el estimador continúa mediante la dinámica recurrente y la velocidad angular. La estabilización 6DoF y los motores permanecen convencionales.

## Interfaz

- Botón `Señal rumbo ON/OFF`.
- Rumbo neuronal en grados.
- Error entre rumbo neuronal y real.
- Confianza como resultante circular del bump.
- Estado visible de la señal externa.
- Registro por paso de rumbo sensorial, rumbo neuronal, resultante, contraste y disponibilidad de señal.

## Limitaciones

- La circularización sigue siendo necesaria; su distancia debe volver a medirse sobre las transferencias PB→EB corregidas.
- El estado neuronal mostrado es una actividad poblacional de tasa; no son potenciales de membrana medidos.
- La entrada de velocidad angular procede del simulador.
- La meta continúa siendo suministrada por una capa de ingeniería.
- Esta integración sirve para desarrollo y visualización; la prueba prospectiva todavía no fue ejecutada.

## Verificación

El smoke test de la aplicación volvió a completar navegación plana, navegación 6DoF, ráfaga y obstáculo. La suite completa contiene 88 pruebas aprobadas tras la integración.

Una comprobación específica de 3 s sin señal externa produjo 1500 pasos físicos, resultante mínima 0,627 y error máximo/final 23,30°. La dinámica permaneció numéricamente estable; este valor es diagnóstico y no una prueba prospectiva.

La corrección, las mediciones PB→EB y sus límites están documentados en `docs/research/cross-compartment-pen-model.md`.
