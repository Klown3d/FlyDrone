# Brújula dinámica resuelta por fase

## Resultado

El modelo aislado de 16 fases supera por primera vez el gate de persistencia y actualización. La estabilización usa transferencias de dos sinapsis derivadas de contactos FAFB 783 y separadas por neuropilo. La actualización usa el desplazamiento PEN de un wedge descrito experimentalmente; ese desplazamiento todavía no fue recuperado de nuestro mapa FAFB provisional.

Este resultado demuestra memoria dentro del **modelo computacional aislado**. Todavía no demuestra memoria de una mosca individual, superioridad sobre PID ni control del dron durante una pérdida sensorial.

## Construcción

Las 47 EPG se agruparon en 16 fases anatómicas. Para cada población intermedia se construyó una transferencia lineal EPG→interneurona→EPG normalizando por célula, sin ajustar contra el desempeño:

| Transferencia | Neuropilo | Desplazamiento mediano | Resultante mediana |
|---|---|---:|---:|
| Δ7 | PB | 146,82° | 0,436 |
| PEG | EB | −0,47° | 0,946 |
| PEN_a izquierda | EB | −0,20° | 0,822 |
| PEN_a derecha | EB | 1,67° | 0,814 |
| PEN_b izquierda | EB | 0,35° | 0,920 |
| PEN_b derecha | EB | 0,63° | 0,919 |

La estructura contiene realimentación local concentrada y una transferencia Δ7 amplia. Estas matrices sostienen el bump. La diferencia PEN_a izquierda−derecha extraída directamente no desplazó suficientemente la actividad. La variante final utiliza dos operadores circulares separados por un wedge, coherentes con la arquitectura experimental de PEN, con signo y ganancia ajustados sólo en desarrollo.

## Selección y evaluación

La búsqueda final evaluó 270 combinaciones globales de excitación, inhibición, bias, ganancia de velocidad y convención angular. No se modificaron conexiones individuales.

- 110/270 conservaron un bump bajo pérdida sensorial.
- 16/270 pasaron también la actualización angular.
- Parámetros seleccionados: excitación 6, inhibición 4, bias −1, velocidad 8 y signo angular −1.

En cuatro headings reservados nuevos:

- deriva mediana después de 3 s sin señal: **0,076°**;
- resultante circular mínima: **0,640**;
- contraste mínimo: aproximadamente **1,0**;
- error mediano tras integrar 60°: **4,70°**;
- dirección correcta: **4/4**.

## Ablaciones congeladas

| Condición | Persistencia | Actualización |
|---|---:|---:|
| Intacto | pasa | pasa |
| Sin inhibición Δ7 | falla | falla |
| Sin excitación recurrente | falla | falla |
| Sin PEG | pasa | pasa |
| Sin operador PEN | pasa | falla |
| Fases reorganizadas, 10 controles | 0/10 | 0/10 |

La ablación PEG no produce un déficit bajo estos parámetros. Por tanto, no se afirma que PEG sea necesario; puede ser redundante con los bucles PEN o requerir otras condiciones para mostrar su contribución. Las demás ablaciones apoyan una dependencia computacional de excitación local, inhibición amplia y actualización PEN.

## Límites

- El producto de matrices de contactos aproxima una transferencia de dos sinapsis; no es una medición fisiológica.
- Las ganancias, constante temporal, sigmoide y señal sensorial son de ingeniería.
- Los signos se asignan por tipo; dos predicciones atípicas individuales siguen pendientes de auditoría.
- El desplazamiento de un wedge de PEN proviene de literatura experimental, no de la fase calculada con nuestro mapa FAFB.
- Cuatro headings reservados son una primera validación, no una caracterización estadística completa.
- El modelo no recibe todavía optic flow ni landmarks y no está conectado al dron.

## Reproducibilidad

- Transferencias: `results/neural/phase_resolved_compass/`.
- Configuración final: `configs/phase_compass_dynamics_v2.yaml`.
- Resultados: `results/neural/phase_compass_dynamics_v2/`.
- Código dinámico: `src/flydrone/neural/phase_compass_dynamics.py`.
- Ablaciones: `src/flydrone/neural/phase_compass_ablation.py`.

## Próximo paso concreto

Congelar este candidato e integrarlo como estimador de heading en una prueba 6DoF reservada con interrupciones temporales del sensor. El steering EPG/Δ7/FC2→PFL3 recibirá la fase interna durante el dropout. PID y proporcional recibirán exactamente la misma última observación disponible. La métrica primaria será llegada sin colisión; deriva, recuperación, trayectoria y esfuerzo serán secundarias.
