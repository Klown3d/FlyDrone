# Borrador histórico de preregistro del gate confirmatorio

**Estado:** reemplazado por `confirmatory-gate-preregistration.md`. Se conserva para documentar la evolución del diseño y no debe utilizarse para ejecutar el gate.

## Hipótesis acotada

Con sensores no privilegiados y estabilización convencional, el readout FlyWire PFN/hDeltaB alcanzará una tasa de llegada útil y dependerá de su organización de fase/conectividad. No se plantea superioridad frente al sustituto directo.

## Condiciones

1. `flywire_hdelta`: conectividad intacta y fusión inercial 3D.
2. `direct_velocity_matched`: misma interfaz y regla de aceleración sin PFN/hDeltaB.
3. `type_side_block_connectivity_null`: misma cantidad de neuronas, grados binarios y conjunto de pesos por fila, con reconexión restringida dentro de PFNd/PFNv y lado. Se usarán al menos cinco semillas congeladas.
4. `conventional_navigation`: heading y amortiguación lateral convencionales.

PFL2 y confianza graduada permanecerán apagadas. Se conservarán la misma planta, sensores, metas, estabilizador y semillas entre condiciones.

## Tamaño y partición

Las condiciones intacta, directa y convencional tendrán al menos 100 vuelos: cuatro familias de perturbación por cinco bearings, cinco orientaciones relativas y una semilla por celda. Cada matriz nula se enfrentará a esos mismos 100 casos pareados. Las familias incluirán viento variable, pérdida desplazada en el tiempo, pérdidas intermitentes y ruido/sesgo inercial. Ningún caso del desarrollo anterior podrá reutilizarse.

## Métrica primaria

Tasa de llegada terminal válida de `flywire_hdelta`: dentro del radio de meta, velocidad menor al umbral y altura válida durante dos segundos, sin colisión.

Criterio funcional propuesto: al menos 90/100 éxitos. El umbral deberá justificarse y congelarse antes de generar resultados.

## Secuencia confirmatoria

Sólo si se cumple la métrica primaria:

1. Atribución: FlyWire debe superar la mediana de las matrices nulas en al menos 20 puntos porcentuales de éxito y no quedar por debajo del percentil 95 de su distribución. La regla exacta de intervalo entre matrices deberá congelarse antes de ejecutar.
2. Comparabilidad: el déficit frente al sustituto directo no debe superar 10 puntos porcentuales.
3. Seguridad: saturación de motores menor o igual al límite congelado y cero colisiones.

Esta secuencia evita seleccionar entre muchas métricas favorables. Si falla un paso, los posteriores serán descriptivos.

## Secundaria clave

Error angular absoluto mediano de la dirección hDeltaB durante pérdida y recuperación, con intervalo bootstrap pareado. No se interpretará como superioridad frente al readout directo porque el directo reproduce por definición la dirección sensorial.

## Exploratorias

Tiempo de llegada, eficiencia, desvío lateral, recuperación, error de velocidad, actividad PFN/hDeltaB, resultante, energía de control y resultados por perturbación. Se informarán efectos e intervalos; no rescatarán un gate primario fallido.

## Reglas de congelación

- Guardar hashes de código, configuración, conectividad y datos.
- Ejecutar una sola vez.
- No cambiar ganancias, filtros, umbrales ni duración después de observar resultados.
- Publicar vuelos fallidos y negativos.
- Marcar cualquier repetición posterior como un experimento nuevo.

## Interpretación prevista

Si FlyWire y el directo resultan equivalentes pero FlyWire supera al nulo, la conclusión será que la conectividad sostiene una representación funcional interpretable sin ventaja de rendimiento. Si el nulo iguala a FlyWire, la atribución al connectoma falla. Si FlyWire queda más de 10 puntos detrás del directo, no será competitivo aunque supere al nulo.
