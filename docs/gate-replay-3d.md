# Comparador nativo 3D de ensayos preservados

Ejecutar `Start-FlyDrone-Gates3D.ps1` desde el proyecto o pulsar **Comparar
ensayos 3D** en la aplicación principal. También:

```powershell
.venv\Scripts\python.exe -m flydrone.visualization.gate_replay_3d
```

La ventana muestra dos drones sobre las trayectorias guardadas del mismo caso:
A intacto en verde y B nulo en naranja. La meta es amarilla. El selector permite
alternar los gates EPG→Delta7, Delta7→PFL3 y steering conjunto, y elegir entre
las 20 semillas nulas de cada gate. Las estadísticas de llegada corresponden al
gate completo; el resultado del caso seleccionado se muestra por separado.

El selector **Piloto OOD** permite recorrer seis pares completos de FlyWire y
control convencional, incluido un fallo de FlyWire bajo pérdidas largas.
En el convencional, la geometría queda en su color neutro: no se le asigna
actividad neuronal de control que no fue registrada ni usada.

El selector **Diagnostico OOD** reproduce exactamente la geometría fallida y
la compara con tres intervenciones privilegiadas: heading verdadero, velocidad
verdadera y ambos. Se etiqueta como oráculo post-hoc; sirve para localizar el
fallo y no representa un controlador utilizable ni una nueva validación.

La vista neuronal contiene los 286 esqueletos completos, sin muestreo:
934.479 vértices y 934.193 aristas. Los filtros muestran poblaciones individuales.
Se conserva la paleta de la aplicación: verde cerca de cero, rojo positivo y
azul negativo; PFL3/PFL2 pasan de verde oscuro a amarillo y rojo al aumentar.

## Controles

- Reproducir/pausar: botón o espacio.
- Reiniciar: botón o R.
- Buscar tiempo: barra temporal o flechas (un segundo).
- Velocidad: selector 0.5×, 1×, 2× o 4×.
- Actividad A/B: cambia el circuito cuyos colores se muestran.
- Rotar circuito: botones inferiores; rueda para zoom.
- Caso anterior/siguiente: sólo recorre pares de trazas que están guardados.
- Exportar vista: botón o E; guarda captura, snapshot A/B, actividad neuronal y
  metadata con hashes bajo `results/desktop/gate-replay-exports/`.
- Escape: cerrar.

Las posiciones, yaw, velocidades, sensores y comandos se leen de los ensayos;
no se vuelve a simular el vuelo. Se presenta el yaw registrado; roll y pitch
no estaban almacenados y no se inventan. La trayectoria completa se ve desde
el inicio como referencia de la reproducción.

Sobre cada dron se muestran tres vectores sincronizados con la traza: heading
observado en cyan, dirección de viaje decodificada por hΔB en magenta y
dirección instantánea a la meta en amarillo. El panel informa además el error
de heading y, cuando ambas velocidades tienen magnitud suficiente, el error de
dirección de la velocidad estimada. En el controlador convencional la dirección
hΔB no existe y ese vector se oculta; no se inventa actividad neuronal.

PFN/hDeltaB usa la actividad guardada. La actividad algebraica EPG/Delta7/FC2,
PFL3 y PFL2 se recalcula desde heading y meta guardados, con la misma variante
de conectividad. Antes de mostrarla se exige que su salida de yaw coincida con
el comando registrado (tolerancia 1e-8 rad/s). Esto no reconstruye el estado
temporal interno del atractor EPG ni propagación por las ramas. Las neuronas
sin actividad definida conservan el color base.

Cada exportación contiene `view.png`, `snapshot.csv`, `neural-activity.csv` y
`metadata.json`. La tabla neuronal contiene 286 root IDs para A y 286 para B,
con tipo, población, valor, unidad y procedencia. No duplica ni modifica las
trazas experimentales preservadas.

Los SHA-256 de `episodes.csv` y cada traza se comparan con el manifiesto de
preservación del gate. Un archivo ausente o alterado produce un error explícito.
También se verifican los datos, configuraciones y fuentes neuronales de la
reconstrucción. Si el generador histórico de nulos tiene una interfaz anterior,
se carga su fuente original desde el ZIP preservado, comprobando tanto el hash
del ZIP como el del archivo. Esto mantiene el generador exacto del gate conjunto.

## Límite de disponibilidad

Los gates guardaron todas las fallas y sólo el primer éxito por condición.
Por eso muchos selectores tienen un único caso pareado disponible. Este visor
no usa esa selección incompleta para estimar éxito: muestra las estadísticas
de todos los episodios y declara la disponibilidad limitada de trazas.

## Verificación

```powershell
.venv\Scripts\python.exe -m pytest tests/test_gate_replay_data.py -q
.venv\Scripts\python.exe -m flydrone.visualization.gate_replay_3d --smoke-test --audit-all
```

El segundo comando comprueba las 60 redes nulas de los tres gates y genera
seis capturas (intacto/nulo por gate), junto con el informe de verificación en
`results/desktop/gate-replay-3d/`. El comparador no modifica los archivos
experimentales preservados.

La verificación también recorre los seis casos OOD y genera dos capturas de
esa comparación, para ocho capturas totales.

El selector **Navegación libre v1** reproduce los 12 pares sellados de patrulla
y exploración. La meta amarilla cambia con la traza, sin reiniciar el dron. El
panel informa la magnitud instantánea de la captura de meta y del geofence;
ambas son capas de ingeniería y no actividad neuronal. Las estadísticas del
selector muestran 106 metas para FlyWire híbrido y 109 para el convencional,
no una tasa de llegada heredada del benchmark de waypoint único.

El selector **Ablaciones v4** compara el circuito intacto con Delta7
ablacionada, la ruta PFN/hDeltaB desconectada y PFL2 desconectada. Sólo muestra
casos con trazas exactamente pareadas: tres para Delta7, tres para PFN/hDeltaB y
dos para PFL2. Es disponibilidad de reproducción, no el tamaño del experimento
global. La reconstrucción carga la función de steering desde el archivo congelado
de v4 y comprueba su hash antes de asignar actividad a las morfologías.

Con ablaciones y oráculos, el smoke test genera doce capturas básicas. La
auditoría completa recorre **155 combinaciones renderizadas** entre redes nulas,
casos OOD, oráculos, ablaciones, v5 y navegación libre v1.

### Prueba de eventos en ventana real

Controles de cámara del mundo: `C` alterna vista general, seguimiento del dron A
y seguimiento del dron B; `A/D` giran, `W/S` acercan o alejan y `Inicio` restaura
la vista general. El seguimiento usa la posición guardada de cada dron y no
modifica su trayectoria. Los botones de rotación y la rueda existentes siguen
controlando el panel neuronal.

`N/M` o los botones **Neurona -/+** recorren las neuronas de la población
visible. La seleccionada se dibuja en blanco y el panel informa su tipo anotado,
FlyWire root ID y valor en el instante actual. EPG, Delta7, FC2, PFL3 y PFL2 se
marcan como reconstruidas desde las entradas guardadas; PFN y hDeltaB se marcan
como registradas en la traza. Para el control convencional se muestra actividad
no definida. Los valores sin unidad experimental se denominan `unidad del
modelo`; no se presentan como potencial de membrana ni tasa biológica medida.

Con `PYTHONPATH=src`, ejecutar:

```powershell
.venv\Scripts\python.exe scripts/check_replay_live.py
```

Agregar `--cycles 4` recorre veinticuatro vuelos completos y repite los controles
de cámara y eventos de la barra en cada caso.

Abre una ventana nativa y recorre seis vuelos pareados completos a velocidad
4x, uno por conjunto de ensayos. Luego verifica cambios de actividad, filtros,
rotación, zoom, selección de casos y desplazamiento temporal mediante eventos
reales de DirectGUI. Se cierra automáticamente al terminar y guarda
`results/desktop/gate-replay-3d/live-stability.json` sólo al superar las comprobaciones.
Una ejecución bloqueada debe detenerse externamente; no puede confiarse en un
temporizador dentro del mismo bucle de eventos bloqueado.

El bloqueo corregido provenía de eventos diferidos de la barra temporal: la
actualización programática generaba otra notificación después de desactivar la
bandera de protección. Ahora se ignoran notificaciones que no cambian el tiempo.
Las hipótesis iniciales de saturación por geometría no quedaron confirmadas.
La vista vuelve a mostrar los 286 esqueletos completos, agrupados en siete lotes,
con todos sus 934.479 vértices y 934.193 aristas. Las actualizaciones visuales
están limitadas; no se alteran las trazas científicas almacenadas.
# Gate híbrido v5

La categoría `Gate híbrido v5` reproduce los 24 casos sellados y permite comparar el híbrido con:

- compass neuronal v4;
- heading giroscópico manteniendo PFL3/PFL2 y PFN/hDeltaB;
- navegación convencional.

Las 96 trazas están preservadas con hashes. El visor verifica cada archivo antes de cargarlo. Para el híbrido muestra cinco vectores:

- cyan: heading fusionado usado por el control;
- verde: heading decodificado del compass neuronal;
- violeta: heading integrado por giroscopio;
- magenta: dirección de viaje decodificada por hDeltaB;
- amarillo: dirección de la meta.

El panel indica el peso neuronal instantáneo y el desacuerdo neuronal–giroscópico. Un peso bajo significa que la capa de ingeniería domina la fusión; no significa que el resto del circuito neuronal esté desactivado.

