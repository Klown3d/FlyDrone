# Matriz de evidencia funcional

Esta tabla separa lo observado en moscas, lo inferido del connectoma y lo que FlyDrone propone trasladar al dron. La confianza se refiere a la función biológica general, no a que nuestro modelo ya la reproduzca.

| Población | Función biológica propuesta | Evidencia disponible | Confianza | Uso en FlyDrone y estado |
|---|---|---|---|---|
| EPG | Representación de heading mediante un bump de fase | Imagen funcional, comportamiento y anatomía | Alta | Codificación de rumbo; implementada, con entrada sensorial abstracta |
| Δ7 | Reformatea heading como patrón aproximadamente sinusoidal y aporta recurrencia/inhibición al PB | Connectoma, neurotransmisor y registros de entradas a PFL | Alta para reformateo; media para nuestra dinámica | Transferencia y recurrencia implementadas; dinámica literal aún insuficiente |
| PEN_a/PEN_b | Actualización del bump relacionada con rotación propia | Anatomía, connectoma y estudios funcionales del sistema compass | Alta para participación; media para pesos dinámicos exactos | Operadores implementados; mapa de fase pendiente de auditoría |
| PEG | Ruta recurrente que puede contribuir a estabilización del bump | Principalmente anatomía/connectoma y modelos | Media | Incluida en recurrencia; ablación actual no mostró necesidad bajo nuestro modelo |
| FC2 / entradas de meta | Patrón del fan-shaped body compatible con una representación objetivo | Anatomía y modelos; identidad y mecanismo completo de selección de meta no resueltos | Media-baja para FC2 como única fuente | El bump objetivo es suministrado por ingeniería; selección de meta fuera de alcance |
| PFL3L/R | Convierte relación heading–meta en steering lateralizado | Connectoma, imagen, patch-clamp y relación con velocidad de giro | Alta | Steering provisional implementado; reconstrucción completa pendiente |
| PFL2 | Se activa lejos de la meta, aumenta movimiento rotacional y reduce avance cerca de la antimeta | Imagen de calcio, patch-clamp, estimulación quimiogenética y modelo funcional | Media-alta | 12 neuronas y contactos Δ7/FC2 reconstruidos; gate prospectivo aprobado, 0/30 nulos igualan su correlación, pero un control angular logra navegación casi equivalente |
| PFNd/PFNv | Combina heading con componentes egocéntricos de movimiento | Imagen funcional, perturbaciones y anatomía | Alta | 61 neuronas reconstruidas; gate prospectivo aislado aprobado con direcciones y ruido nuevos |
| hΔB | Representa dirección allocéntrica de desplazamiento mediante suma vectorial PFN | Imagen funcional, perturbaciones y modelo cuantitativo | Alta | Gate confirmatorio v1: 95/100 metas con conectividad intacta frente a mediana 38/100 en cinco nulos estructuralmente restringidos; directo 97/100 y convencional 100/100 |

## Predicción específica para PFL2

Al retirar PFL2, el modelo debería tardar más en recuperarse de errores próximos a 180° y PFL3 debería conservar el sentido del giro. La prueba prospectiva reprodujo la predicción: 0,386 s de mejora mediana, 35/36 pares favorables y cero cambios de signo. La topología de fase aporta estructura frente a nulos, pero no una ventaja práctica frente a una fórmula angular explícita.

## Fuentes primarias principales

- Westeinde et al., 2024, *Transforming a head direction signal into a goal-oriented steering command*, Nature 626, 819–826: https://www.nature.com/articles/s41586-024-07039-2
- Lyu, Abbott y Maimon, 2022, *Building an allocentric travelling direction signal via vector computation*, Nature 601, 92–97: https://www.nature.com/articles/s41586-021-04067-0
- Hulse et al., 2021, *A connectome of the Drosophila central complex reveals network motifs suitable for flexible navigation and context-dependent action selection*, eLife: https://pmc.ncbi.nlm.nih.gov/articles/PMC9477501/

La evidencia publicada sobre PFL2 es más fuerte de lo que sugerían trabajos anteriores: el estudio de 2024 incluye imagen, electrophysiología y estimulación. La afirmación que permanece hipotética es que trasladar esa función al dron mejorará sus correcciones grandes.
