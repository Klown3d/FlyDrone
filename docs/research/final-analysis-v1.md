# Análisis final de FlyDrone v1

## Resumen ejecutivo

FlyDrone v1 demuestra que un modelo computacional trazable a circuitos del *central complex* de *Drosophila melanogaster* puede generar comandos útiles de navegación de alto nivel para un quadrotor simulado. El resultado más fuerte es el gate confirmatorio PFN→hΔB: 95/100 llegadas con la conectividad FlyWire intacta frente a una mediana de 38/100 en cinco redes reconectadas que conservaron restricciones estructurales importantes. El protocolo fue congelado antes de ejecutar 800 vuelos y aprobó sus cuatro criterios jerárquicos.

El proyecto no demuestra que el connectoma supere a la ingeniería convencional. El sustituto directo alcanzó 97/100 y el controlador convencional 100/100. La contribución comprobada es otra: capacidad funcional, interpretabilidad y dependencia medible de la organización conectómica dentro de la simulación.

## Hipótesis evaluada

> Un modelo computacional reconstruido a partir de la conectividad de un circuito funcional del *central complex* de *Drosophila melanogaster*, utilizando datos del connectoma FlyWire, puede generar señales de orientación y steering capaces de controlar autónomamente la navegación de un dron simulado, alcanzando un desempeño medible y comparable con controladores convencionales.

La hipótesis queda respaldada parcialmente y con límites precisos:

- **Generación de señales útiles:** respaldada para PFL3, PFL2 y PFN/hΔB en los bancos correspondientes.
- **Navegación autónoma simulada:** respaldada; la red controla decisiones de alto nivel y una capa convencional estabiliza el vehículo.
- **Desempeño comparable:** respaldado para el gate PFN/hΔB bajo el margen preregistrado respecto del sustituto directo; no equivale a superioridad.
- **Dependencia de la arquitectura FlyWire:** respaldada confirmatoriamente para PFN→hΔB dentro del modelo v1.
- **Circuito completo como controlador único:** todavía no cerrado; las evidencias de los módulos provienen de gates separados.

## Qué fue reconstruido

### Orientación y steering

El modelo incluye EPG, Δ7, PEN_a/PEN_b, PEG, FC2, PFL3 y PFL2. EPG/Δ7 aportan una representación de heading; PFL3 transforma la relación entre heading y meta en una señal lateralizada de giro; PFL2 modula intensidad/avance ante errores angulares grandes. La meta FC2 se suministra mediante una interfaz de ingeniería: FlyDrone no modela todavía cómo una mosca elige su objetivo.

### Dirección de desplazamiento y deriva

La reconstrucción PFNd/PFNv→hΔB contiene 202 neuronas, 6.196 pares dirigidos y 53.999 sinapsis. Combina heading con componentes egocéntricos de movimiento para obtener una dirección allocéntrica de desplazamiento. En el dron, esa señal se usa para compensar la diferencia entre la dirección hacia la que apunta y la dirección en la que realmente se mueve bajo viento.

### Visualización

La aplicación nativa representa el dron, sus señales y 286 esqueletos neuronales completos. La actividad visual es una codificación de las variables del modelo sobre morfologías reales; no es una medición de calcio ni una simulación biofísica detallada.

## Arquitectura ejecutada

```text
observaciones simuladas
        ↓
codificadores explícitos de heading, meta y movimiento
        ↓
modelos FlyWire-grounded del central complex
        ↓
yaw, avance y compensación de deriva de alto nivel
        ↓
estabilizador convencional de actitud/altura + mezcla de motores
        ↓
planta rígida de quadrotor 6DoF
```

Esta división es deliberada. Las neuronas no generan PWM de motores: producen señales de navegación; el controlador de vuelo conserva estabilidad y seguridad.

## Evidencia acumulada

| Componente | Evidencia principal | Estado |
|---|---|---|
| EPG→Δ7→PFL3 | Navegación 6DoF, ablaciones y nulos de proyección | Funcional, todavía provisional biológicamente |
| Recurrencia EPG/Δ7/PEN/PEG | Gate aislado v4 y dropout | Prototipo; no iguala observadores de giroscopio |
| PFL2 | Gate prospectivo 30/30 y respuesta a cambios grandes | Funcional; fórmula angular rindió casi igual |
| PFNd/PFNv→hΔB aislado | 720 transformaciones nuevas; 6/6 criterios | Aprobado prospectivamente |
| PFN/hΔB en 6DoF | 30/30, reducción de deriva y controles nulos | Aprobado prospectivamente |
| PFN/hΔB confirmatorio | 800 vuelos; 95/100 intacto; mediana nula 38/100 | Aprobado confirmatoriamente |
| Control integrado completo | Primer gate 22/30 y 4/8 criterios fallidos | Pendiente de v2 |

## Resultado confirmatorio central

El gate `flydrone_pfn_hdelta_confirmatory_v1` usó casos, bearings, headings y semillas no utilizados para construir los nulos de desarrollo. Incluyó cinco reconexiones que preservaban tipo PFN, lado, grados y distribución de pesos, más un sustituto directo y un controlador convencional.

- FlyWire intacto: 95/100.
- Nulos: 0/100, 63/100, 38/100, 1/100 y 46/100.
- Mediana nula: 38/100; percentil 95: 59,6/100.
- Ventaja del intacto sobre la mediana: 57 puntos porcentuales.
- Directo pareado: 97/100; déficit FlyWire: 2 puntos, dentro del margen de 10.
- Convencional: 100/100.
- Seguridad: 0 colisiones y 0 saturación máxima registrada.

Los cinco nulos aumentaron de forma pareada el error de dirección respecto del intacto; los intervalos bootstrap del aumento fueron positivos en todos los casos. El detalle y las figuras se encuentran en [Resultado confirmatorio PFN→hΔB v1](confirmatory-gate-results.md).

## Análisis de fallos

Los cinco fallos FlyWire no son choques ni pérdida total de navegación. En todos se alcanzó y sostuvo al menos una vez la condición de llegada, pero el vehículo volvió a salir del radio antes de terminar. Tres ocurrieron durante pérdida larga de heading y dos durante pérdida larga de velocidad. Dos también fallaron con el control directo pareado.

Este patrón localiza el problema residual en la retención de meta y las transiciones de recuperación sensorial. Debe abordarse en v2 con un conjunto nuevo y sellado; cambiar ahora la política invalidaría la interpretación confirmatoria de v1.

## Capas biológicas y capas de ingeniería

### Respaldado por connectoma/literatura

- identidades y morfologías neuronales;
- conectividad y conteos sinápticos usados para las matrices;
- organización funcional general de EPG, Δ7, PFL3, PFL2, PFN y hΔB;
- lectura poblacional de heading, steering y dirección de desplazamiento.

### Inferido o regularizado

- asignaciones de fase cuando la anatomía no fija por sí sola una fase funcional única;
- simplificaciones de las transferencias y dinámica de tasas;
- normalizaciones necesarias para comparar poblaciones.

### Ingeniería explícita

- sensores simulados, filtrado y fusión inercial;
- selección y codificación de la meta;
- ganancias y constantes temporales no medidas;
- transformación del readout en aceleración/yaw;
- control de roll, pitch, altura, motores y failsafes;
- criterios de llegada y recuperación.

## Afirmaciones permitidas

- “Un modelo FlyWire-grounded de PFN→hΔB controló compensación de deriva en un dron simulado y obtuvo 95/100 llegadas en un protocolo confirmatorio congelado.”
- “El rendimiento dependió de la organización de la conectividad dentro de este modelo: cinco reconexiones estructuralmente restringidas rindieron entre 0% y 63%, frente a 95% del intacto.”
- “FlyDrone ofrece actividad neuronal interpretable y trazable a neuronas reales mientras controla navegación de alto nivel.”

## Afirmaciones no permitidas

- “El cerebro completo de una mosca controla el dron.”
- “FlyDrone supera a PID o al controlador convencional.”
- “Cada parámetro dinámico es biológicamente medido.”
- “La simulación demuestra que funcionará igual en un dron físico.”
- “Las neuronas reemplazan al controlador de vuelo y a los mecanismos de seguridad.”

## Reproducibilidad y preservación

Los insumos congelados se conservaron en:

`archive/confirmatory_v1/flydrone_pfn_hdelta_confirmatory_v1_frozen_inputs.zip`

SHA-256 del archivo:

`8b0dce46e194bf31f613308ccc19f44c91ff2520276cb7774b39cddde32b40e9`

El archivo contiene los 277 insumos registrados por el lock. `archive/confirmatory_v1/preservation-manifest.json` contiene hashes de los 707 archivos de resultado, incluidos los 700 trazados, sin duplicarlos. El análisis derivado se regenera con:

```powershell
.\.venv\Scripts\python.exe scripts\analyze_confirmatory_results.py
```

La aplicación se abre con:

```powershell
.\Start-FlyDrone.ps1
```

El reproductor nativo de los 100 casos confirmatorios compara FlyWire con el sustituto directo, permite avanzar/pausar y sincroniza trayectoria, error y actividad PFN/hΔB:

```powershell
.\.venv\Scripts\python.exe scripts\confirmatory_replay.py
```

Para inspeccionar una reconexión específica se puede usar, por ejemplo:

```powershell
.\.venv\Scripts\python.exe scripts\confirmatory_replay.py --controller-b null_rewire_block_130027
```

El error angular se oculta cuando la velocidad es menor que 0,05 m/s porque la dirección de un vector casi nulo no está definida; esto evita interpretar ruido angular de llegada como un fallo neuronal.

La suite actual contiene 139 pruebas y finaliza sin fallos. El reproductor también pasó su prueba visual de carga y renderizado.

## Riesgos pendientes

1. La brújula recurrente v4 todavía es inferior a observadores convencionales durante pérdidas de heading.
2. La entrada de meta y parte de la interfaz sensorial son abstracciones de ingeniería, no circuitos sensoriales reconstruidos.
3. El gate confirmatorio aísla PFN/hΔB; no demuestra que todos los módulos juntos mantengan la misma atribución.
4. Los cinco fallos señalan fragilidad de retención tras pérdidas largas.
5. Falta validar latencia y estabilidad con un simulador/autopiloto estándar o un airframe físico.

## Siguiente versión

La v2 debe integrar EPG/Δ7, PFL3, PFL2 y PFN/hΔB en un único controlador de alto nivel; congelar casos nuevos con viento, pérdida sensorial, cambios de meta y obstáculos; y ejecutar ablaciones emparejadas por módulo. Después corresponde completar replay/exportación en la aplicación y, sólo si la simulación integrada aprueba, conectar la salida de alto nivel a un autopiloto con failsafes independientes.

## Veredicto

FlyDrone v1 alcanzó el objetivo científico mínimo fuerte: un subcircuito identificable, reconstruido con conectividad real, produjo navegación simulada útil y su organización específica importó bajo controles preregistrados. El proyecto todavía no está terminado como producto ni como controlador neuronal integrado completo, pero ya dejó de ser solamente una demostración visual o una red “inspirada en moscas”: posee un resultado confirmatorio reproducible y limitado con honestidad.
