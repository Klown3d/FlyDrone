# Preregistro del gate operacional híbrido v5

Fecha de congelación prevista: 2026-10-31. Estado inicial: **no ejecutado**.

## Pregunta

¿El candidato híbrido v5 conserva navegación robusta bajo pérdidas prolongadas de heading y velocidad en casos nuevos, sin quedar materialmente por debajo de un control giroscópico que mantiene iguales los módulos neuronales downstream?

Este gate evalúa robustez operacional del sistema. No prueba que la dinámica del compass FlyWire sea superior al giroscopio ni que su contribución sea causal.

## Condiciones

1. `full_hybrid_v5`: estado de compass FlyWire-grounded fusionado con integración giroscópica de ingeniería; steering PFL3/PFL2 y deriva PFN/hDeltaB.
2. `neural_v4_reference`: compass neuronal v4 sin fusión inercial, con el resto idéntico.
3. `gyro_heading_control`: integración giroscópica para heading, conservando PFL3/PFL2 y PFN/hDeltaB.
4. `conventional_navigation`: navegación proporcional convencional.

## Matriz sellada

- 4 bearings × 2 headings iniciales × 3 escenarios = 24 vuelos por condición.
- 96 vuelos totales, duración máxima de 50 s y meta a 7 m.
- Bearings, headings y semillas sin intersección con v4, el piloto OOD, el diagnóstico v5 ni el desarrollo del híbrido.
- Tres escenarios: pérdida larga de heading, pérdidas largas superpuestas y pérdida tardía con readquisición.

## Criterios primarios congelados

El gate pasa sólo si se cumplen simultáneamente:

1. híbrido ≥22/24 llegadas;
2. híbrido ≥7/8 en cada escenario;
3. déficit frente al control giroscópico ≤1 llegada;
4. ventaja frente a v4 neuronal ≥4 llegadas;
5. error mediano durante dropout ≤10°;
6. costo de desvío transversal frente al giroscópico ≤0,40 m;
7. peso neuronal mediano durante dropout ≥0,01 y máximo ≤0,250001;
8. cero colisiones y cero saturación de motores para el híbrido.

El umbral mínimo de peso sólo verifica que la rama neuronal no esté desconectada. No constituye evidencia de que mejore el rendimiento. Las comparaciones con el controlador convencional son descriptivas.

## Integridad

Antes de ejecutar se generará un lock con hashes SHA-256 de configuración, preregistro, código, ambiente y datos procesados. `run_once: true` impide sobrescribir el resultado. Cualquier cambio exige un protocolo nuevo.
