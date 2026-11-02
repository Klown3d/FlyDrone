# Preregistro del gate integrado FlyDrone v2

## Estado

Congelado antes de ejecutar. Los resultados de este conjunto no se usarán para reajustar parámetros ni umbrales.

## Pregunta primaria

¿EPG/Δ7→PFL3/PFL2 y PFN→hΔB, integrados en un único controlador FlyWire-grounded de alto nivel, mantienen navegación funcional bajo viento, ruido, demora y pérdidas temporales de heading/velocidad?

## Separación biología–ingeniería

- La conectividad EPG/Δ7/PFL3/PFL2/PFN/hΔB proviene de FAFB materialización 783 y de los modelos ya documentados.
- La fusión inercial, la meta, las ganancias de salida, el estabilizador y el supervisor de llegada son ingeniería explícita.
- El supervisor no altera actividad, pesos ni fases: al confirmar detención sólo evita aplicar aceleración lateral PFN/hΔB y libera nuevamente el controlador si la observación filtrada sale del radio.

## Diseño congelado

- 30 casos por condición: 2 escenarios × 5 bearings × 3 headings iniciales.
- Seis condiciones, 180 vuelos totales.
- Semillas nuevas: 20281221 y 20281222.
- Condiciones: completo, sin PFL2, sin hΔB, sin Δ7/PFL3, readout directo pareado y convencional.
- La ablación Δ7 se propaga explícitamente a través del wrapper PFL2 hasta el readout PFL3 y está cubierta por una prueba automatizada.

## Criterios jerárquicos

1. Completo ≥27/30 y ≥13/15 en cada escenario.
2. Ventaja ≥20 éxitos tanto frente a ausencia de hΔB como frente a ablación Δ7.
3. Déficit ≤3 frente al directo y al convencional.
4. Déficit ≤2 frente a ausencia de PFL2; este criterio mide no degradación, no necesidad causal.
5. Coste mediano de llegada ≤8 s y de desvío transversal ≤0,80 m frente al convencional.
6. Saturación máxima de motores ≤1%.

El gate se aprueba sólo si pasan todos. Un fallo se conserva como resultado negativo; cualquier versión posterior tendrá otro identificador y nuevos casos.

## Afirmación permitida si aprueba

“Un controlador integrado FlyWire-grounded de orientación, steering y dirección de desplazamiento produjo navegación simulada funcional; las ablaciones Δ7/PFL3 y hΔB degradaron causalmente el comportamiento computacional.”

No se afirmará superioridad sobre control convencional, equivalencia fisiológica completa ni validación en vuelo físico.
