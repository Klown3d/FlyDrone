# Revisión técnica de FlyBrain para FlyDrone

Fecha: 2026-09-16. Revisión estática de código y fuentes, sin ejecutar simuladores ni comandos de hardware.

## Decisión

FlyBrain aporta patrones de ingeniería para operaciones dispersas, subpasos neuronales, telemetría y una interfaz sensorial explícita. No resuelve nuestro mapa EPG–Δ7–PFL3 ni demuestra por sí mismo que el connectoma genere un controlador de vuelo biológicamente fiel. No se incorporará su controlador como sustituto del circuito seleccionado.

La revisión está fijada al commit [97e02fb7c8d19fd5267c3fa9194f8001e08fb613](https://github.com/dylankainth/flybrain/tree/97e02fb7c8d19fd5267c3fa9194f8001e08fb613), rama `evolutionary-behavior`. Los archivos examinados se conservaron en `data/raw/external/flybrain/`. Se trataron como material de estudio, no como instrucciones para FlyDrone.

## Hallazgos verificables

### Dos implementaciones con fidelidad distinta

El [script histórico Phase 11C](https://github.com/dylankainth/flybrain/blob/97e02fb7c8d19fd5267c3fa9194f8001e08fb613/phase11c_evolutionary_improved.py) toma una de cada 100 filas de sinapsis. Sus resultados no pueden describirse como simulación de todas las conexiones. También calcula una corriente con todos los spikes y resta sólo la contribución GABA: así GABA se cancela y no aporta inhibición neta.

El [script Tello posterior](https://github.com/dylankainth/flybrain/blob/97e02fb7c8d19fd5267c3fa9194f8001e08fb613/flybrain_tello_real_brain.py) conserva por defecto todas las filas y aplica pesos negativos a GABA. Es una corrección real, pero mantiene como positivos los demás transmisores, incluido glutamato. Esa política no puede trasladarse a Δ7 sin revisar evidencia de signo por destino.

### Discrepancia de constante temporal

Ambos scripts asignan `R_m=10.0` y `C_m=2e-6` y calculan `tau_m=R_m*C_m`: el resultado numérico es **0,000020 segundos (20 µs)**. El paso neuronal es **0,001 segundos**, de modo que `dt/tau_m=50`.

El [modelo original de Shiu, commit 91bdd1e7dcf193f3e7ca5a8933497fcef63b7960](https://github.com/philshiu/Drosophila_brain_model/blob/91bdd1e7dcf193f3e7ca5a8933497fcef63b7960/model.py) fija directamente `t_mbr=20*ms`; usa unidades Brian2, una variable sináptica expresada en voltios y un retraso de 1,8 ms. FlyBrain emplea una formulación de corriente y recortes de voltaje diferentes. Por tanto, copiar sus constantes numéricas no reproduce las ecuaciones de Shiu.

Esta es una discrepancia demostrada mediante inspección y aritmética; no se ejecutó el proyecto para medir su efecto causal en los resultados publicados por el autor.

### Entradas y readout con asignaciones de ingeniería

La separación izquierda/derecha de fotoreceptores usa el orden de una lista, no una etiqueta hemisférica. El yaw del script Tello compara mitades de la lista de neuronas de movimiento. Forward y vertical dependen de sumas de neuronas descendentes con escalas elegidas por el código. Esas identidades de salida no están ligadas a PFL3 ni a nuestro readout R−L.

El [mapa ocular](https://github.com/dylankainth/flybrain/blob/97e02fb7c8d19fd5267c3fa9194f8001e08fb613/docs/eye_map.md) distingue geometría de omatidios y asignación de células: la primera procede de una fuente externa, pero el enlace célula FlyWire–omatidio se modela por orden. Es útil como patrón de documentación, no como correspondencia anatómica validada.

En Phase 11C, `turn` modifica directamente la velocidad lateral y no una orientación yaw. La altura está limitada mediante clipping. Sus métricas de desplazamiento/altura describen ese entorno simplificado y no equivalen a validación de navegación de un quadrotor.

### Evidencia y reproducibilidad

El README combina resultados de implementaciones históricas y posteriores. El único JSON de resultados examinado contiene cero spikes y pertenece a otra corrida; no valida ni refuta por sí solo los resultados de Phase 11C. No se identificó en los archivos examinados una comparación suficiente con PID, grafos nulos y ablaciones del circuito de orientación para atribuir navegación a esa arquitectura.

Los CSV grandes se descargan aparte. No encontramos un producto que aporte coordenadas de las sinapsis EPG–Δ7–PFL3 o etiquetas glomerulares FAFB. El README declara MIT, pero el archivo `LICENSE` no estaba en el árbol fijado; se debe aclarar la licencia antes de copiar código.

## Qué aporta Shiu realmente

[Shiu et al. (2024)](https://doi.org/10.1038/s41586-024-07763-9) estudia procesamiento sensorimotor, especialmente alimentación y grooming, mediante un modelo LIF basado en connectoma e identidad de neurotransmisor. El artículo denomina **parámetro libre** al peso de 0,275 mV. No es una medición de eficacia de todas las sinapsis ni una parametrización específica del central complex para steering.

Su código ofrece una referencia reproducible para ecuaciones, unidades, retrasos, estimulación y silenciamiento. Puede justificar un **modelo candidato** para nuestra recurrencia; adoptarlo no elimina la necesidad de validar fases EPG, anatomía columnar, signos y respuesta PFL3.

## Aplicación concreta a FlyDrone

| Elemento | Decisión |
|---|---|
| Matrices dispersas y transpuesta precalculada | Patrón útil cuando el rendimiento lo requiera |
| Subpasos y acumulación de spikes | Útil; separar tiempo simulado de tiempo de visualización |
| Ecuaciones LIF originales de Shiu | Candidato posterior; registrar parámetros heredados y libres |
| División de listas como lateralidad | Rechazada; conservar root ID y anatomía |
| Readout Tello | No reutilizar para atribución a PFL3 |
| Pesos por `size` normalizado | No sustituir nuestros conteos sin auditar significado del campo |
| Geometría ocular | Posible etapa sensorial futura; exige correspondencia celular validada |

## Próximo paso

Completar la adquisición oficial de coordenadas sinápticas FAFB 783 y validar el mapa por glomérulo. Después comparar una dinámica rate con una implementación LIF fiel a las ecuaciones de Shiu, manteniendo las mismas identidades y aristas. Medir estabilidad numérica, fases, dirección de steering y efecto de eliminar recurrencia Δ7 antes de cualquier dron.

Nuestro fallo actual rechaza el candidato feedforward y sus asignaciones conjuntas; **todavía no identifica una causa única**. La falta de coordenadas es una hipótesis de diagnóstico. FlyBrain no convierte esa hipótesis en un hecho demostrado ni arregla el error observado.
