# Análisis final integrado de FlyDrone v4

## Veredicto

FlyDrone v4 cumple el objetivo científico del alcance actual: un modelo computacional trazable a circuitos FlyWire del *central complex* genera steering, avance y compensación de deriva útiles para un quadrotor 6DoF simulado. El control neuronal es de alto nivel; estabilización, actitud, motores, sensores y seguridad siguen siendo ingeniería convencional.

El proyecto demuestra capacidad funcional e importancia de conectividad dentro del modelo. No demuestra superioridad frente al control convencional, una reproducción biofísica completa ni robustez global fuera de distribución.

## Hipótesis y resultado

- El controlador FlyWire-grounded llegó en 28/30 vuelos integrados.
- Los controles directo y convencional lograron 30/30; no existe ventaja de rendimiento a su favor.
- Ablacionar Delta7 produjo 0/30 y desconectar PFN/hΔB produjo 4/30; sin PFL2 se obtuvieron 29/30.
- Cuatro gates prospectivos detectaron dependencia de partner identity en PFN→hΔB, EPG→Δ7, Δ7→PFL3 y steering conjunto.
- El resultado confirmatorio más fuerte sigue siendo PFN→hΔB: 95/100 frente a una mediana de 38/100 entre cinco reconexiones restringidas.

## Sistema evaluado

```text
observaciones simuladas
  → EPG/Delta7/PEN/PEG: orientación regularizada
  → FC2: meta suministrada por ingeniería
  → PFL3/PFL2: sentido, intensidad y avance
  → PFNd/PFNv/hΔB: dirección de desplazamiento y deriva
  → comandos de yaw y aceleración de alto nivel
  → estabilizador convencional y planta 6DoF
```

Se usó FAFB/FlyWire materialización 783. La aplicación contiene 286 esqueletos descargados completos, con 934.479 vértices y 934.193 aristas. La visualización codifica variables del modelo sobre morfologías reales; no es calcio observado, potencial de membrana ni propagación biofísica por ramas.

## Jerarquía de evidencia

### Confirmatoria

El gate PFN→hΔB congelado ejecutó 800 vuelos. FlyWire obtuvo 95/100; cinco nulos restringidos obtuvieron 0, 63, 38, 1 y 46/100. El sustituto directo logró 97/100 y el convencional 100/100. No hubo colisiones ni saturación. Este gate respalda atribución connectómica para ese subcircuito dentro de la simulación.

### Prospectiva

El gate integrado v4 ejecutó 180 vuelos y aprobó sus 10 criterios. FlyWire obtuvo 28/30, llegada mediana de 23,096 s, eficiencia 0,4649 y desvío máximo mediano de 1,974 m. El convencional obtuvo 30/30, 20,330 s, eficiencia 0,6011 y 1,396 m. El costo de FlyWire fue 2,766 s y 0,579 m; no hubo saturación.

En cuatro gates de atribución, el intacto obtuvo 12/12 en cada uno. Se probaron 20 redes nulas por gate y ninguna igualó 12/12. Las mejores obtuvieron 6/12 para PFN→hΔB, 6/12 para EPG→Δ7, 8/12 para Δ7→PFL3 y 7/12 para steering conjunto. Cada gate tiene rango empírico p=1/21=0,047619; esos valores no se combinan como si fueran experimentos independientes.

### Diagnóstica

La sensibilidad local OAT produjo 28/28 éxitos al variar ganancias y constante temporal ±20%, cuatro casos por variante. Es favorable pero no cubre interacciones ni sensibilidad global.

En el piloto OOD, FlyWire logró 5/6 y el convencional 6/6. El desvío máximo mediano fue 8,143 frente a 2,236 m y el error de heading durante corte fue 60,43° frente a 2,64°. Un diagnóstico post-hoc reprodujo exactamente el fallo: heading verdadero rescató la llegada, velocidad verdadera sola no y ambos verdaderos sí. Esto localiza un caso; no aumenta la tasa OOD ni valida una v5.

## Qué depende de qué

| Capa | Estado |
|---|---|
| Identidades, morfologías, conexiones y conteos sinápticos | FlyWire-grounded |
| Función general de EPG, Delta7, PFL3, PFL2, PFN y hΔB | Respaldada por literatura |
| Fases incompletas, normalizaciones y simetría circular | Inferidas/regularizadas |
| Constantes temporales y ganancias no medidas | Parámetros de ingeniería |
| Meta FC2, sensores, fusión, arrival supervisor y readout | Ingeniería explícita |
| Roll, pitch, altura, motores y failsafes | Control convencional |

La conectividad real importa en los gates ejecutados, pero parte del desempeño proviene necesariamente de interfaces y regularización. Las ablaciones muestran necesidad dentro de esta arquitectura; no convierten cada parámetro en biología.

## Aplicación y reproducibilidad

El comparador nativo reproduce trazas preservadas, muestra dos drones, filtros, actividad por neurona, root ID FlyWire, sensores, cámaras y vectores de heading, viaje hΔB y meta. Los oráculos se etiquetan como post-hoc. La geometría completa se mantiene en siete lotes de render.

La exportación interactiva guarda PNG, snapshot A/B, actividad de 286 neuronas por condición y metadatos con procedencia y SHA-256, sin copiar ni modificar las trazas fuente. La aplicación superó 79 combinaciones renderizadas, seis replays en ventana real y la suite completa de 157 pruebas.

No se representa un estado recurrente EPG temporal que no haya sido guardado. EPG/Delta7/FC2/PFL3/PFL2 se etiquetan como reconstrucción algebraica desde entradas preservadas; PFN/hΔB se etiquetan como actividad registrada.

## Afirmaciones permitidas y no permitidas

Se puede afirmar que un modelo FlyWire-grounded controló navegación de alto nivel de un dron simulado, obtuvo 28/30 llegadas y mostró dependencia de conectividad en los gates ejecutados. No se puede afirmar que el cerebro completo de una mosca controla el dron, que FlyDrone supera al convencional, que la brújula v4 es robusta globalmente, que los oráculos son sensores utilizables o que la simulación garantiza vuelo físico.

## Cierre de fases 9–11

- **Fase 9, cerrada para v4:** baselines, ablaciones, cuatro gates de partner identity, sensibilidad local, piloto OOD y diagnóstico del fallo.
- **Fase 10, cerrada para el alcance activo:** aplicación 3D nativa verificable, morfologías completas, replay, inspección individual, vectores y exportación con procedencia. Instalador y presentación permanecen pospuestos.
- **Fase 11, cerrada para v4:** síntesis integrada, jerarquía de evidencia, limitaciones, reproducibilidad y separación entre biología e ingeniería.

Este cierre no equivale a finalizar todas las líneas futuras. Una evaluación OOD amplia y sellada, sensibilidad global, PID/EKF totalmente emparejado, flujo óptico, una brújula v5 y el dron físico forman el programa posterior.

## Próximo paso

Si el proyecto continúa, corresponde preregistrar una v5 antes de modificar la brújula: generador OOD sellado, geometrías nuevas, oráculos separados de la evaluación y baseline convencional con exactamente las mismas observaciones. La integración física sólo debe ocurrir después y con autopiloto y failsafes independientes.
