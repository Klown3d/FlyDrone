# Primera navegación hacia una meta espacial

2026-09-18. FlyWire/FAFB 783. Modelo neuronal provisional, planta de ingeniería simplificada.

## Comportamiento y separación de funciones

El circuito recibe heading y dirección absoluta de la meta, calculada como `atan2(y_meta−y, x_meta−x)`. EPG→Δ7→PFL3 produce steering, sin sustituirse por un error angular proporcional. El signo EPG, normalización y ganancia 0,02 conservan la configuración candidata anterior. Un módulo compartido calcula las actividades tanto en la aplicación como en el banco; una prueba verifica equivalencia con el modelo anterior.

El avance es convencional: velocidad máxima 0,6 m/s, reducción proporcional a distancia, penalización por desalineación, espera si el error supera 60° o la altura difiere más de 0,2 m, y respuesta de velocidad con τ=0,3 s. Al llegar dentro de 70% del radio de aceptación de 0,3 m y con velocidad ≤0,08 m/s, se activa parada persistente y se amortiguan las velocidades. No se modifica la posición para colocar el dron exactamente sobre la meta. Cambiar la meta libera la parada. Tras parar también se amortigua yaw; la dirección hacia el punto restante puede cambiar y su error angular ya no define éxito.

Estabilización vertical sigue siendo PD convencional. El movimiento horizontal es una aproximación de velocidad en el plano; no representa inclinación, dinámica de rotores, fuerzas aerodinámicas ni seis grados de libertad. No hay obstáculos. La aplicación conserva los 195 esqueletos completos y actividad global; no simula propagación dendrítica.

## Experimento ejecutado

12 direcciones de meta, distancia inicial 4 m, 8 errores iniciales: 96 condiciones por realización/controlador. Tiempo 30 s, paso 20 ms, altura inicial 0,7 m y objetivo 2 m. Escenario ideal y heading con ruido gaussiano de 3°/retraso 300 ms con semillas 792 y 793. Posición y dirección de meta son ideales; el avance convencional usa heading real para su gate. Por ello no se afirma navegación con sensores realistas.

Se comparan neuronal candidato, proporcional, una permutación de entradas EPG por fila (semilla 792) y convención angular anterior. El proporcional comparte avance, frenado y planta. El ruido es idéntico entre controladores por realización. La permutación preserva valores entrantes, no out-degree; una sola permutación no es una evaluación estadística completa.

Éxito: parada activada y distancia ≤0,3 m, velocidad ≤0,08 m/s y altura dentro de ±0,1 m durante los últimos 2 s, sin contacto muestreado con el suelo.

| Condición | Ideal | Ruido/retraso |
|---|---:|---:|
| Neuronal provisional | **96/96** | **192/192** |
| Proporcional | 96/96 | 192/192 |
| Entradas EPG permutadas | 14/96 (14,58%) | 26/192 (13,54%) |
| Convención anterior | 0/96 | 0/192 |

**1.152 episodios completados.** Mediana del tiempo de activación de parada: neuronal 10,09 s ideal/9,96 s perturbado; proporcional 9,71/9,57 s. Distancia final mediana neuronal 7,93/7,83 cm; proporcional 7,75/7,75 cm. No hay superioridad neuronal demostrada.

Longitud de trayectoria mediana entre ensayos exitosos: neuronal 4,03 m ideal/3,99 m perturbado; proporcional 3,99/3,95 m. El punto de parada acepta un radio y no exige tocar el punto geométrico. Se guarda `4 m / longitud` como razón nominal; puede superar uno por esa tolerancia y no debe interpretarse como eficiencia normalizada máxima uno. Faltan sensibilidad a radios, posiciones nuevas, estimación de posición, ruido de altitud, obstáculos y controles de conectividad más estrictos.

## Aplicación y reproducción

La aplicación ahora dibuja una meta espacial amarilla, mueve el dron en x/y, mantiene altura, muestra distancia y estado de llegada, dibuja trayectoria y permite cambiar meta. Avance, frenado y parada son ingeniería explícita, no funciones neuronales reconstruidas.

```powershell
.venv\Scripts\python.exe -m flydrone.visualization.desktop
.venv\Scripts\python.exe -m flydrone.simulation.benchmark_navigation
.venv\Scripts\python.exe -m pytest tests/test_navigation.py tests/test_hover.py tests/test_steering_interface.py -q
```

Configuración: `configs/navigation.yaml`. Productos: `results/simulation/navigation/` con episodios, resumen, informe, trayectorias x/y/z y actividad PFL3/Δ7. La meta inicial interactiva es (3,5; 2,0) m, distinta de la malla del banco. La comprobación nativa prueba esa meta con ambos controladores durante 20 s y genera `results/desktop/navigation-integration-check.json`. En esos dos ensayos llegó a 9,77 cm y 7,74 cm de la meta, respectivamente. Pasaron seis pruebas relacionadas y se verificó renderizado de la ventana.

Siguiente paso: verificar metas/posiciones iniciales nuevas y sensores de posición perturbados antes de añadir obstáculos. La revisión anatómica pendiente de Δ7 sigue abierta. Este hito muestra navegación espacial simplificada de un modelo FlyWire-grounded en simulación; no vuelo real ni control biológico completo.
