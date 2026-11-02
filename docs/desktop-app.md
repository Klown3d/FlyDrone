# Aplicación FlyDrone de escritorio — prototipo inicial

Aplicación nativa Panda3D/Python, sin navegador. Dos vistas: entorno del dron y **286 esqueletos de neuronas reales FlyWire 783**, incluidos PFL2, 40 PFNd, 21 PFNv y 18 hΔB. Se renderizan 934.479 vértices y 934.193 aristas sin muestreo ni deformación. Los esqueletos representan ramificaciones, no superficies celulares completas.

El circuito EPG→Δ7→FC2/PFL3 controla yaw y PFL2 modula giros grandes. En 6DoF, PFL2 también modula cuánto avanzar mediante una interfaz prospectivamente validada y conmutable. PFNd/PFNv→hΔB combina heading y velocidad egocéntrica para estimar la dirección real de desplazamiento; su salida puede reemplazar la amortiguación lateral convencional. La conversión de PFL2 a velocidad, la ganancia de corrección, frenado por distancia, altura, actitud y motores son capas de ingeniería declaradas. Configuraciones principales: `configs/desktop.yaml`, `configs/pfl2_steering.yaml`, `configs/pfl2_advance.yaml`, `configs/travel_direction_drift.yaml`, `configs/navigation_confirmed.yaml` y `configs/quadrotor.yaml`.

La velocidad PFN no proviene directamente del estado físico: se estima por diferencias de posición observada con `configs/travel_velocity_sensor.yaml`. El heading externo se deriva del bearing relativo a una baliza conocida mediante `configs/landmark_heading_sensor.yaml`. Ambas son entradas de ingeniería, no flujo óptico ni visión neuronal reconstruidos.

El botón **Avance PFL2 ON/OFF** alterna entre la salida PFL2 y el frenado angular analítico. La pantalla muestra la fracción `avance x…`; el CSV guarda `desired_speed_m_s`, `advance_fraction` y `pfl2_advance_enabled`.

**Modo plano:** movimiento vertical, yaw y velocidad directa en x/y, con roll/pitch restringidos. Se conserva para reproducir los bancos anteriores.

**Modo 6DoF:** integra posición/velocidad 3D, cuaternión, velocidades angulares, inercia, gravedad, arrastre, cuatro motores, empuje y torques. La geometría visible adopta roll, pitch y yaw calculados. Sus parámetros son genéricos y no están validados contra un airframe real; no incluye aerodinámica detallada, efecto suelo ni batería. Puede activar un cilindro naranja y una capa convencional de evasión; el punto local se muestra en cian mientras está activo.

La vista neuronal usa la paleta original del prototipo: verde significa valor cercano a cero, rojo valor positivo y azul desviación negativa. El verde no representa por sí mismo activación intensa. EPG/Δ7/FC2 son entradas o desviaciones firmadas; PFL3 son tasas no negativas y PFL2 usa actividad adimensional no negativa. No se simula propagación por cada rama. FC2A y dos FC2C excluidas permanecen con el color base, sin inventarles actividad. Con controlador proporcional, la actividad neuronal sigue calculándose como observación, pero PFL2 se desactiva y no gobierna el dron. Los subtipos Δ7 y glomérulos extremos continúan provisionales.

El panel verde expone la cadena calculada en cada paso: heading y meta observados; índices de actividad máxima EPG, Δ7 y FC2; suma de tasas PFL3 izquierda/derecha; señal poblacional R−L; actividad media e índice PFL2; escala aplicada; y comando yaw antes/después de modular. Un índice identifica una posición en los vectores del modelo, no un nuevo nombre anatómico ni una medición fisiológica. La frecuencia PFL3 proviene del modelo publicado adaptado; las otras actividades son variables adimensionales.

Cerca de la meta existe una singularidad geométrica: cuando el vector posición→meta se aproxima a cero, un desplazamiento diminuto puede cambiar su ángulo casi 180°. Para que ese artefacto no se presente como actividad neuronal, la interfaz conserva la última dirección fiable al entrar en un radio de 30 cm. La libera al superar 40 cm, dejando 10 cm de histéresis para evitar conmutación en el borde. El panel indica `retenida cerca de meta`. Es acondicionamiento de entrada de ingeniería y no memoria atribuida a EPG, Δ7, FC2 o PFL3.

## Abrir

La aplicación incluye el botón **Comparar ensayos 3D** para reproducir los
gates de steering con dos trayectorias y actividad sincronizada. Puede abrirse
directamente mediante `Start-FlyDrone-Gates3D.ps1`. [Controles y procedencia de
la actividad](gate-replay-3d.md).

Desde el proyecto, ejecutar `Start-FlyDrone.ps1`, o:

```powershell
.venv\Scripts\python.exe -m flydrone.visualization.desktop
```

Panda3D 1.10.16 está instalado en el entorno del proyecto. Para recrear dependencias: instalar el extra `desktop` de `pyproject.toml`. Todavía no se empaquetó un ejecutable independiente.

## Controles

- Iniciar/pausar: botón o espacio.
- Reiniciar: botón o R. Borra la traza actual no guardada.
- Cambiar meta: botón o G, nueva posición sobre un círculo, incrementos de 60°; libera la parada anterior.
- Neuronal/proporcional: botón; reinicia el ensayo para comparar desde el mismo estado.
- Sensor ideal/perturbado: botón; reinicia el ensayo y cambia la observación que recibe tanto el circuito como la lógica convencional de avance/llegada.
- Perturbar dron +0,6 m: desplaza físicamente el estado simulado en x para comprobar que la llegada deja de sostenerse, el control se reactiva y puede regresar.
- Planta plana/6DoF: reinicia y alterna entre el modelo reproducible anterior y la dinámica rígida con motores.
- Ráfaga 0,5 N: en modo 6DoF aplica durante cuatro segundos una fuerza mundial `[0, 0,5, 0]` N. El contador aparece junto a roll, pitch y motores; en modo plano no se aplica.
- Obstáculo seguro: en modo 6DoF activa un cilindro estático a mitad del trayecto. Una capa geométrica convencional elige el lado de menor giro y entrega una meta local al circuito neuronal. El panel la rotula `meta local convencional` y muestra la separación mínima; esto no representa percepción ni planificación biológica.
- Guardar ensayo: botón o S, guarda traza CSV y metadatos en `results/desktop/`.
- Deriva hDeltaB ON/OFF: alterna entre corrección neuronal y amortiguación lateral convencional en 6DoF.
- Velocidad PFN ON/OFF: interrumpe la modalidad de velocidad; el estimador decae y se recupera al reactivarla.
- Landmark ON/OFF: oculta el cue visual externo y deja la brújula en actualización interna.
- Brújula v4/v2: alterna PEN_a circularizado derivado de contactos y la variante con desplazamiento publicado. Ambas conservan parámetros dinámicos de ingeniería.
- Filtros PFN y hDeltaB: muestran las morfologías completas de esas poblaciones.

Los vectores sobre el dron son: verde, rumbo; celeste, movimiento medido; magenta, dirección decodificada por hΔB; naranja, aceleración correctiva.

El panel `hDeltaB · 12 columnas` agrega las 18 neuronas por su columna axonal provisional. Azul indica modulación negativa respecto de la línea base omitida, verde valor cercano a cero y rojo modulación positiva. No representa tasas absolutas ni propagación por las ramas.
- Todas/EPG/Δ7/FC2/PFL3/PFL2: filtrar clases del circuito.
- Flechas izquierda/derecha: rotar circuito; rueda: zoom.

Los campos `activity_<root_id>` guardan valores del modelo; las tasas PFL3 son Hz, las demás actividades son adimensionales firmadas. La traza también guarda posición y heading observados, meta real/observada, señal PFL3 R−L, modo sensorial y planta. En 6DoF añade los cuatro empujes. La actividad guardada corresponde a la observación previa a la actualización física. Los ensayos interactivos no deben confundirse con los bancos experimentales.

La política actual confirma llegada durante 0,4 s con posición filtrada y radio de entrada 12 cm, y permite reanudar si deja de sostenerse la estimación. Es control convencional configurable, no función neuronal. [Comparación, recuperación y límites](research/arrival-confirmation.md). Reiniciar la aplicación aplica esta actualización.

## Verificación

```powershell
.venv\Scripts\python.exe -m flydrone.visualization.desktop --smoke-test
.venv\Scripts\python.exe -m pytest tests/test_hover.py -q
```

La comprobación sin ventana renderiza capturas, exige exactamente 286 esqueletos completos y verifica navegación plana, recuperación, ráfaga y obstáculo. El ensayo 6DoF con hΔB llegó a 3,71 cm, con velocidad terminal prácticamente nula, inclinación máxima 5,28° y sin saturación. El ensayo con obstáculo llegó a 10,33 cm, sin colisión y con 0,35 m de margen. Productos: `results/desktop/desktop-preview.png`, `desktop-6dof-preview.png`, `desktop-obstacle-preview.png`, `geometry-report.json` y `navigation-integration-check.json`.

Además de los bancos planos y las ablaciones de llegada, se completaron 64 episodios 6DoF deterministas y 64 con [ruido, retraso y ráfagas físicas](research/quadrotor-6dof.md), todos exitosos. La primera [prueba de obstáculo](research/obstacle-navigation.md) logró 16/16 casos nuevos por controlador sin colisiones mediante una capa geométrica convencional. El proporcional conserva una ligera ventaja de eficiencia. La visualización completa no implica que se haya modelado toda la dinámica biológica del circuito.
