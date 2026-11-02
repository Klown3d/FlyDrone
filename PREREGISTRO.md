# Prerregistro prospectivo de FlyDrone

**Versión:** 0.6  
**Fecha:** 2026-10-10  
**Estado:** gates PFN/hΔB completados; interfaz sensorial de velocidad congelada  
**Alcance:** experimentos futuros posteriores a la auditoría PEN y al congelamiento del controlador.

## Separación de datos

Todas las velocidades, rumbos, semillas y vuelos ejecutados antes de esta fecha pertenecen a desarrollo o validación observada. Esto incluye el resultado de 4,42° de `phase_compass_symmetry_regularized_v3` y los 64 vuelos de pérdida de heading. No se usarán como confirmación final.

El conjunto prospectivo se generará una sola vez después de registrar los hashes del código, configuraciones y datos. La semilla maestra será `20260924`. El generador no guardará casos solapados con las listas explícitas de desarrollo actuales. Los valores concretos se escribirán automáticamente al iniciar la corrida sellada y no se usarán para ajustar el modelo.

## Condiciones mínimas para congelar este documento

- auditoría PEN terminada;
- modelo literal o regularizado seleccionado sin consultar la prueba prospectiva;
- parámetros y umbrales fijados;
- scripts de todas las condiciones y métricas probados con datos de desarrollo;
- hashes SHA-256 del código, datos y configuraciones añadidos aquí;
- cálculo de potencia o justificación final del número de semillas realizado con datos piloto.

Después del congelamiento, cualquier cambio creará una nueva versión y anulará el carácter confirmatorio de la corrida afectada.

## Tamaño experimental

- 30 semillas emparejadas por condición como mínimo.
- Grafos nulos: 30 por condición, con semillas `91000` a `91029`.
- Cada semilla usa exactamente el mismo escenario, ruido y perturbaciones para todos los controladores comparados.
- Si el análisis de potencia basado en los pilotos exige más de 30, se aumentará antes del congelamiento. Nunca se reducirá después de observar la prueba.

## Métricas primarias

1. **Brújula:** error angular absoluto mediano durante pérdida de señal externa.
2. **Steering:** tiempo de recuperación después de cambios de meta de 180°.
3. **Deriva:** error lateral acumulado bajo viento durante el intervalo perturbado.
4. **Navegación:** eficiencia de trayectoria entre episodios exitosos, acompañada siempre por tasa de éxito.

## Métricas secundarias

- percentil 90 y máximo de error angular;
- dirección correcta de actualización;
- resultante y contraste del bump;
- oscilación y sobrepaso;
- tiempo hasta la meta;
- distancia final y velocidad terminal;
- colisiones;
- latencia y factor de tiempo real.

## Predicciones y refutaciones

| Intervención | Predicción previa | Métrica principal afectada | Resultado que refuta la predicción |
|---|---|---|---|
| Sin Δ7 | El bump pierde estabilidad o contraste | deriva de fase y resultante | diferencia trivial frente al intacto y umbrales completos superados |
| Sin recurrencia | La fase no se mantiene durante la pérdida de cue | error durante dropout | error no aumenta materialmente y la resultante permanece estable |
| Sin PEN/update de velocidad | El signo o magnitud del giro interno deja de seguir velocidad angular | error angular y dirección correcta | desempeño equivalente al intacto dentro del margen preregistrado |
| Sin PFL3L/R | Se pierde la selección fiable del sentido de giro | dirección de steering | sentido correcto y tiempo de recuperación equivalentes al intacto |
| Sin PFL2 | Las correcciones grandes son más lentas, pero PFL3 conserva el sentido | recuperación a 180° | no aumenta el tiempo o se invierte sistemáticamente el sentido |
| Sin PFN/hΔB | Empeora la compensación de deriva con rumbo corporal correcto | error lateral con viento | compensación equivalente al intacto |
| Fase FC2 barajada | El punto estable deja de coincidir con la meta suministrada | error final respecto de meta | la meta se conserva pese al barajado |
| Pesos/fases barajados | Cae la estabilidad o el steering | métricas primarias del módulo | desempeño equivalente o superior al intacto |
| FlyWire regularizado vs. 30 nulos regularizados | FlyWire conserva una ventaja si su estructura aporta función | error angular y éxito | FlyWire cae dentro de la distribución nula sin efecto relevante |
| FlyWire literal vs. regularizado | La regularización mejora dinámica, pero debe cuantificarse su costo anatómico | error angular + distancia matricial | no mejora o requiere reemplazar la mayor parte de la estructura |

La predicción PFL2 se apoya en evidencia experimental de actividad, registro y estimulación en moscas; su transferencia a un dron sigue siendo una hipótesis que este proyecto puede refutar.

## Grafos nulos y regularización

Cada nulo conservará número de nodos, número de aristas, distribución de grados por lado y, cuando sea viable, distribución de pesos. Se generará mediante intercambios dirigidos que eviten autoaristas y duplicados. La circularización, normalización, búsqueda de parámetros y criterios serán idénticos para FlyWire y nulos.

Antes de la comparación se informará cuánto modifica la regularización mediante:

- correlación de entradas matriz a matriz;
- error de Frobenius normalizado;
- fracción de peso que cambia de celda;
- distribución de peso por desfase circular;
- preservación de pesos totales por fila y columna.

## Controles convencionales

- proporcional;
- PID;
- filtro complementario de rumbo + PID/proporcional;
- EKF + PID si se completa antes del congelamiento.

Todos reciben las mismas observaciones, ruido, demora y cortes. El esfuerzo de ajuste se declarará mediante número de candidatos y episodios de desarrollo utilizados.

## Análisis estadístico

- Comparaciones pareadas de dos condiciones: Wilcoxon signed-rank.
- Más de dos condiciones emparejadas: Friedman, seguido por comparaciones pareadas.
- Corrección por comparaciones múltiples: Holm.
- Tamaño de efecto: correlación biserial por rangos para pares; Cliff's delta cuando no haya emparejamiento válido.
- Intervalos de confianza del 95% por bootstrap pareado.
- Éxito/fracaso: McNemar para pares y un intervalo binomial de confianza por condición.
- Se publicarán valores individuales, medianas, intervalos, tamaños de efecto y resultados contrarios a las predicciones.

## Reglas de decisión

La significación estadística por sí sola no demostrará utilidad. Antes de congelar se fijará para cada métrica una diferencia mínima relevante basada en los pilotos. Una arquitectura sólo se atribuirá a FlyWire si supera tanto ese umbral como los nulos regularizados.

Si la red regularizada no supera a los nulos regularizados, la conclusión será que la regularización produjo la función mientras FlyWire aportó plausibilidad anatómica. Si el modelo literal corregido funciona, éste reemplazará a v3 como candidato principal. Si ninguno cumple los criterios, se reportará el resultado negativo y no se moverán los umbrales.

## Registro de congelamiento

### Brújula v4 — congelada el 2026-09-27 antes de ejecutar

Se fijaron 30 casos emparejados: cinco bearings objetivo por seis rumbos iniciales relativos, todos ausentes de las listas explícitas de desarrollo. Cada controlador recibe la misma semilla `20260924`, ruido, demora, viento y pérdida de heading de 6 s. La configuración tiene `run_once: true` y rechazará una segunda ejecución si ya existe el informe.

Criterios primarios fijados antes de observar la corrida:

- éxito de navegación de v4 ≥ 90%;
- error mediano durante dropout ≤ 25°;
- error máximo durante dropout ≤ 75°;
- mejora mediana frente a sample-and-hold ≥ 5°.

Los 30 pares satisfacen el mínimo ya fijado por este preregistro. Esta corrida se interpreta como gate prospectivo del módulo, no como estimación de alta precisión ni como comparación definitiva de superioridad frente a un estimador convencional.

| Elemento | SHA-256 |
|---|---|
| Protocolo `quadrotor_heading_dropout_v4_prospective.yaml` | `b8b4e09e29c737caa9680d0ae8d6bc80c047f6223c6d7c2302cae3bc3c0a1e18` |
| Configuración v4 | `61db9f17ddbc6c1f57de9ae12f1c5e8eb4382cab4980144638f34fae4fa2b589` |
| Estimador neuronal | `b3bfd991631f0396693c06b028dce1540d34249594a0aadf125407e2d4dc4cd4` |
| Simulador 6DoF | `03aa97f704da0136f55a19392adec985851fa7e3ff4a6e506cb4b3ad585591ef` |
| Generador de prueba | `1bb46b76a4e17b674982f8f794ff281c2b2b3e942687db92fb3d17cddfc3904a` |
| Transferencias PB→EB procesadas | `e2e6ce9a0f9533c4a3ff1c0c909d7d07fbfab7b7b00420a21f3aae30b489fe6f` |

### Resultado inmutable de la corrida v4

La corrida única terminó el 2026-09-27. V4 obtuvo 30/30 llegadas y error mediano de 23,68°, pero registró un máximo de 142,86° y sólo 2,21° de mejora entre medianas frente a sample-and-hold. Cumplió 2/4 criterios; el gate global falló. No se cambiaron umbrales ni parámetros después de observar los resultados.

Informe: `results/simulation/quadrotor_heading_dropout_v4_prospective/report.json`  
SHA-256: `654585c7d124ff698bb69cc6413ffbffc04b27679978cdf4833b6f43996907c6`

## Protocolo prospectivo PFL2 — congelado antes de ejecutar

**Fecha de congelamiento:** 2026-10-10  
**Estado al escribir esta sección:** no ejecutado; el directorio de salida no contiene el informe prospectivo.  
**Rol:** prueba única de la predicción PFL2 ya registrada, separada de los bancos usados para construir la activación y fijar la ganancia 0,5.

Se evaluarán 36 casos pareados por condición, combinando direcciones de meta `[-128°, -7°, 109°]`, errores iniciales `[-172°, -153°, 153°, 172°]` y tres escenarios nuevos de ruido, retraso y viento. Cada par recibe la misma semilla y perturbación en PFL3+PFL2 y PFL3 sola. La dinámica PFL2, su conectividad, la ganancia, la planta y los umbrales quedan congelados. El archivo tiene `run_once: true` y rechazará una segunda ejecución si ya existe el informe.

Criterios, todos obligatorios:

1. PFL3+PFL2 alcanza al menos 35/36 metas.
2. Su número de éxitos no es inferior al de PFL3 sola.
3. La mejora mediana pareada en tiempo de llegada es al menos 0,30 s.
4. Al menos dos de los tres escenarios muestran mejora mediana positiva.
5. La diferencia mediana pareada de eficiencia es al menos −0,005.
6. PFL2 no cambia el signo del primer comando PFL3 en ningún caso.

| Elemento congelado | SHA-256 |
|---|---|
| Protocolo `quadrotor_pfl2_prospective.yaml` | `15dfb02a66ffb286a99f090b38e7e5136194b268089f2e1f4f256a8650c5d6f5` |
| Interfaz `pfl2_steering.yaml` | `66c7c20f715c237ccd29f258f6c8b0b1c048ca175d8c4ad3daee7b71a1d9cf8b` |
| Modelo `pfl2_model.yaml` | `f2a7f08b4fc83c442b2d3a423e0b8ada9bd834fdc5c28fc04d28243ba7946865` |
| Ejecutor prospectivo | `2324b7c24f25568fcb47829c3412bc525ab61553ac6b47ca525e0cf2dfc10cad` |
| Simulador 6DoF | `3b01afae005822eac6a795e75025989c8eb72750c8fa1eee334234d45d0dc5f7` |
| Controlador PFL2 | `f02f1c77f78ca0c0d42629921cca486596ee475f2f1127c579566da261b1534f` |
| Modelo de contactos PFL2 | `60c3146da084308b104e14ab7d00ca887b3f054d65a3f05631f3b3310f3aab0b` |

El gate puede fallar y el resultado se conservará sin modificar parámetros ni umbrales. Un resultado positivo evaluará la utilidad de la modulación actual bajo perturbaciones nuevas; todavía no probará que la conectividad específica sea necesaria. Esa atribución requiere controles de conectividad posteriores y separados.

### Resultado inmutable de la corrida PFL2

La corrida única terminó el 2026-10-10 y conservó los hashes congelados. PFL3+PFL2 y PFL3 sola alcanzaron 36/36 metas. La mejora mediana pareada fue 0,386 s, con mejoras por escenario de 0,411 s, 0,420 s y 0,091 s. La diferencia mediana de eficiencia fue +0,00752, PFL2 no cambió ningún signo inicial y no hubo saturación de motores. Se cumplieron los seis criterios; el gate prospectivo fue aprobado.

Informe: `results/simulation/quadrotor_pfl2_steering_prospective/report.json`

Los análisis posteriores no forman parte del gate. Treinta permutaciones de fase no alcanzaron la correlación del mapa FlyWire con el error angular (FlyWire 0,981; mejor nulo 0,728; p empírico ≤ 0,032). Un control analítico con la misma ganancia consiguió un desempeño casi idéntico: su llegada mediana quedó 0,003 s por detrás de PFL2 y su eficiencia mediana pareada fue 0,00071 menor. Esto limita la atribución: la organización de fases FlyWire contiene la señal, pero la ventaja de navegación no es exclusiva del connectoma frente a una fórmula que recibe directamente el error angular.

## Protocolo prospectivo PFN/hΔB — congelado antes de ejecutar

**Fecha de congelamiento:** 2026-10-10  
**Estado al escribir esta sección:** no ejecutado; `results/neural/travel_direction_prospective/report.json` no existe.  
**Rol:** prueba única de generalización del candidato PFNd/PFNv→hΔB seleccionado durante desarrollo.

Se fijaron 720 transformaciones: ocho headings y diez direcciones egocéntricas ausentes de la grilla de desarrollo, tres velocidades y tres escenarios (`ideal`, ruido moderado y ruido fuerte). La semilla `20261010`, los casos, el modelo, los datos y los umbrales quedan congelados. La dirección verdadera se calcula con las entradas sin ruido; el modelo recibe las observaciones perturbadas. `run_once: true` impide reemplazar el resultado.

Los seis criterios son obligatorios:

1. Error mediano ideal ≤ 12°.
2. Error máximo ideal ≤ 30°.
3. Error mediano conjunto ≤ 18°.
4. Percentil 90 conjunto ≤ 35°.
5. Al menos 95% de los casos quedan dentro de 45°.
6. Resultante mínima ≥ 0,08.

| Elemento congelado | SHA-256 |
|---|---|
| Protocolo `travel_direction_prospective.yaml` | `50d8a0c9dada6616a0ae3c02702e9fdd25fc784a62102a3684d3bcb3acaa3b5b` |
| Configuración del modelo | `8d93ab7f9ae5e5a90a3a7cfaae7b91b91e89aec169bb4dc9e9ae20bcde14cf94` |
| Ejecutor prospectivo | `4eb7dbf922b8a51cd0e346d338dde23ea021e83350ea8dada05d5c756f633e1e` |
| Modelo PFN/hΔB | `2a54f602b48b98542ee750f5e63568922b3f3aef228bc0f84a0b55700dbaf16b` |
| Mapa de columnas | `c325529fbed40716ae5911b454eed4d72af5e8d39d7ac339eef1a394d753a5ca` |
| Conectividad FAFB 783 | `5e352dc7caf8bc3294dde90062971916b77e2e507fd99e119a0309f13f2875b3` |

Este gate sólo evalúa la transformación estática y tolerancia a ruido sensorial. No incluye retrasos temporales, dinámica del dron ni demuestra tasas fisiológicas reales. Si falla, el resultado se conserva y no se reajustan parámetros con estos casos.

### Resultado inmutable de la corrida PFN/hΔB

La corrida única terminó el 2026-10-10 y conservó todos los hashes congelados. Procesó 720 casos y aprobó los seis criterios. En el escenario ideal obtuvo 6,09° de error mediano y 22,73° máximo. En el conjunto completo obtuvo 8,38° de mediana, 21,30° en el percentil 90, 46,61° máximo, 99,58% dentro de 45° y resultante mínima 0,412. El escenario de ruido fuerte tuvo 10,42° de mediana y 98,75% dentro de 45°.

Informe: `results/neural/travel_direction_prospective/report.json`
SHA-256: `2138b15bb5b51e838e1da45fc1454c1d3f2f825da8e5b839b911ecce821942a8`

## Protocolo prospectivo PFN/hΔB 6DoF — congelado antes de ejecutar

**Fecha de congelamiento:** 2026-10-10  
**Estado al escribir esta sección:** no ejecutado; el informe prospectivo integrado no existe.

Se fijaron 30 casos por condición mediante cinco bearings, tres headings iniciales y dos escenarios nuevos con viento, ruido y demora. Se compararán hΔB, ausencia de compensación, velocidad lateral convencional y fases PFN barajadas, siempre con perturbaciones emparejadas. La corrida contiene 120 episodios y `run_once: true`.

Criterios obligatorios: hΔB logra al menos 27/30 llegadas; supera por seis llegadas a la condición ausente; reduce al menos 40% el desvío máximo mediano frente a ausencia; queda a no más de 0,40 m del convencional; reduce al menos 20% el desvío frente a fases barajadas; y su saturación máxima de motores no supera 10%.

| Elemento congelado | SHA-256 |
|---|---|
| Protocolo | `cedccad8c68bc2e32e54859e6335704bc466e54f5d74e7beb25fccd9be89bec2` |
| Interfaz de deriva | `9a07f85d7a91a753c5ff5584f0be94f99e8a58b89cea1aedf7d085a2da10d72` |
| Ejecutor | `1cbe43314503e990024d39838e1c87e8825d4c39c73a581a9f6a48fe3b9dfc26` |
| Controlador hΔB | `2717dade84b78a36c791854280fbcfaf0bfdc1e8717f7c157c3dcc66b6f25970` |
| Modelo PFN/hΔB | `2a54f602b48b98542ee750f5e63568922b3f3aef228bc0f84a0b55700dbaf16b` |
| Columnas | `c325529fbed40716ae5911b454eed4d72af5e8d39d7ac339eef1a394d753a5ca` |
| Conectividad | `5e352dc7caf8bc3294dde90062971916b77e2e507fd99e119a0309f13f2875b3` |

El gate puede fallar. No se cambiarán parámetros ni umbrales después de observarlo.

**Recuperación técnica registrada antes de calcular métricas:** los 120 vuelos terminaron y generaron `episodes.csv`, SHA-256 `c73da924a33783c3272c7cf608f95ddc2763023a7ae34c5535ce190153ff77f4`. El escritor falló al serializar un `numpy.bool` antes de imprimir métricas. No se repiten vuelos. Un recuperador que sólo lee ese CSV y aplica los criterios congelados tiene SHA-256 `0ffdd51031483c970bcd46d592c35fc3641233483105d83394df2bb79698a7e7`.

### Resultado inmutable del gate PFN/hΔB 6DoF

La corrida aprobó 6/6 criterios. hΔB alcanzó 30/30 metas; sin compensación y con fases PFN barajadas, 0/30; el convencional, 30/30. El desvío máximo mediano fue 1,309 m con hΔB, 5,235 m sin compensación, 17,500 m con fases barajadas y 1,217 m con control convencional. hΔB redujo el desvío 75,0% frente a ausencia y 92,5% frente al nulo, quedó 0,091 m detrás del convencional y no saturó motores. El informe conserva explícitamente la recuperación desde el CSV congelado.

Informe: `results/simulation/quadrotor_travel_direction_prospective/report.json`

## Protocolo prospectivo de velocidad por posición — congelado antes de ejecutar

**Fecha de congelamiento:** 2026-10-10  
**Estado al escribir:** no ejecutado; el informe no existe.

Se fijaron 30 casos por condición: cinco bearings, tres headings y dos escenarios nuevos. Uno combina viento con posición ruidosa y demorada; el otro interrumpe la actualización de velocidad durante 3,5 s. Se compararán hΔB con velocidad estimada por posición, hΔB con velocidad directa, ausencia de compensación y control convencional, para 120 vuelos emparejados.

Los siete criterios obligatorios son: al menos 27/30 llegadas estimadas; ventaja de seis llegadas frente a ausencia; reducción de deriva ≥40%; costo ≤0,50 m frente a velocidad directa; déficit máximo de tres llegadas frente a directa; al menos 13/15 llegadas durante el escenario de pérdida; saturación máxima ≤10%.

| Elemento congelado | SHA-256 |
|---|---|
| Protocolo | `7719c1295effd6f839eb80d8cdd949939aa0ecf7cba497a8d32628ba2cf3ae68` |
| Configuración del sensor | `a7e640e016f2a23855a8fedb82882305647e49867a9904a627ce6805df0c72c6` |
| Ejecutor | `7d9c40afd41feba3d41a356eb0b3e9e01e3e696ba2d86b94494e6e4a8d9f976c` |
| Sensor | `a49f2d7e09eff910da1f252f73c80fd521361596c1fd8c0b29d8c4183347bac5` |
| Interfaz hΔB | `5f7a11be0e7cb4759e4c871a387485d7275242c4ce67435cfdf7583d4ec698f8` |
| Modelo PFN/hΔB | `2a54f602b48b98542ee750f5e63568922b3f3aef228bc0f84a0b55700dbaf16b` |

El gate puede fallar y no se ajustarán estos parámetros con sus resultados.

### Resultado inmutable de velocidad por posición

La corrida única procesó 120 vuelos y aprobó 7/7 criterios. hΔB con velocidad estimada alcanzó 28/30 metas; hΔB con velocidad directa y el convencional, 30/30; ausencia de compensación, 1/30. La interfaz estimada redujo 66,9% el desvío máximo mediano frente a ausencia, quedó 0,336 m detrás de la velocidad directa y conservó 14/15 llegadas durante la pérdida prolongada. No hubo saturación. Su llegada mediana fue 16,674 s y eficiencia 0,474, peores que 14,792 s y 0,658 con velocidad directa.

Informe: `results/simulation/quadrotor_travel_sensor_prospective/report.json`

## Protocolo prospectivo de avance PFL2 — congelado antes de ejecutar

**Fecha de congelamiento:** 2026-10-10  
**Estado al escribir:** no ejecutado; `results/simulation/quadrotor_pfl2_advance_prospective/report.json` no existe.  
**Rol:** comprobar que una señal de avance derivada de la población PFL2 puede reemplazar al frenado angular analítico sin degradar materialmente la navegación.

Se fijaron 30 casos por condición mediante cinco bearings, tres headings relativos iniciales y dos escenarios no usados durante desarrollo. Se comparará `pfl2_advance` contra `angular_advance` con las mismas perturbaciones, PFL3 activo en ambas condiciones y 60 vuelos en total. La conversión cuadrática del índice PFL2 a velocidad y el frenado por distancia son decisiones de ingeniería explícitas, no propiedades fisiológicas conocidas. El archivo tiene `run_once: true`.

Los seis criterios obligatorios son: al menos 27/30 llegadas con PFL2; déficit máximo de dos llegadas frente al control angular; costo mediano de tiempo de llegada ≤0,50 s; costo mediano de eficiencia ≤0,03; costo mediano de desvío transversal ≤0,10 m; y saturación máxima de motores ≤10%.

| Elemento congelado | SHA-256 |
|---|---|
| Protocolo | `c0dbcb1ca19c17a66e5970983b3d8e87bb29ab3cd250407df35ae53a5beb3bed` |
| Configuración PFL2 avance | `6179a5efcf66badf1a8502a30a647e0f2ed45aaef39ce9ba7104a3ac68dde776` |
| Ejecutor prospectivo | `2f684d593a5d041cc8ba22f0da59131b84ec0696f2faabf1aef277b1b82a0c41` |
| Controlador de avance | `05e57f571fe34b368987814ca4962d4f91504785f23a63ed034fd8cb3395a388` |
| Interfaz PFL2 de steering | `66c7c20f715c237ccd29f258f6c8b0b1c048ca175d8c4ad3daee7b71a1d9cf8b` |

El gate puede fallar. El resultado se conservará sin ajustar parámetros ni umbrales con estos casos. Incluso si aprueba, demostrará equivalencia funcional de esta interfaz dentro del simulador; no probará que la regla cuadrática sea la transformación biológica real de PFL2.

### Resultado inmutable del avance PFL2

La corrida efectiva única terminó el 2026-10-11 y procesó 60 vuelos. PFL2 y el frenado angular alcanzaron 30/30 metas. PFL2 tuvo un costo mediano de 0,022 s en llegada, 0,00492 en eficiencia y 0,0044 m en desvío transversal; no hubo déficit de éxitos ni saturación. Aprobó los seis criterios. La tentativa anterior quedó suspendida antes de generar archivos y fue terminada sin informe ni episodios parciales.

Informe: `results/simulation/quadrotor_pfl2_advance_prospective/report.json`
SHA-256: `5c62f282732a0e1685895d68c0769ef5a87e5574ad3b90154277c84b11b791b3`

## Gate prospectivo del controlador integrado corregido — congelado antes de ejecutar

**Fecha de congelamiento:** 2026-10-11  
**Estado al escribir:** no ejecutado; `results/simulation/quadrotor_integrated_prospective/report.json` no existe.  
**Rol:** evaluar conjuntamente brújula v4, PFL3, PFL2, PFN/hΔB y el sensor de velocidad corregido después de cerrar el ciclo de desarrollo que detectó amplificación de ruido.

El conjunto fija 30 casos por condición: cinco bearings y tres headings iniciales bajo dos escenarios nuevos que combinan viento, ruido, demora, pérdida de heading y pérdida de velocidad. Se ejecutarán 120 vuelos emparejados: sistema FlyWire completo, ausencia de PFL2, ausencia de hΔB y navegación proporcional con heading giroscópico y amortiguación lateral convencional. La duración será 35 s. La ventana sensorial de 200 ms, los controladores y todos los umbrales quedan congelados.

Los ocho criterios son obligatorios:

1. El sistema completo alcanza al menos 27/30 metas.
2. Alcanza al menos 13/15 metas en cada escenario.
3. Su déficit frente al convencional no supera tres llegadas.
4. Su costo mediano de llegada frente al convencional no supera 8,0 s.
5. Su costo mediano de desvío transversal no supera 0,70 m.
6. Supera por al menos doce llegadas a la ablación sin hΔB.
7. Su déficit frente a la ablación sin PFL2 no supera dos llegadas.
8. La saturación máxima de motores no supera 10%.

| Elemento congelado | SHA-256 |
|---|---|
| Protocolo integrado | `0af767b7daafa4ce0262a74b4366754f1d5626140020f3b3d98ea381e34b4a2d` |
| Ejecutor prospectivo | `11f97eb1c8898f085404b8e3c32dee35dc484c3785ece57d0b593678e47b9e97` |
| Sensor de velocidad | `b389b7e85b4d35ace686283765e25e31545eb196a5bd4fe7defb6e6eb4bb9ded` |
| Configuración sensorial | `5f7589542ea6ad5efd3cc8295849d8032a733915bdc0e561f16a536b564b1c4a` |
| Controlador de avance PFL2 | `05e57f571fe34b368987814ca4962d4f91504785f23a63ed034fd8cb3395a388` |
| Controlador de deriva hΔB | `5f7a11be0e7cb4759e4c871a387485d7275242c4ce67435cfdf7583d4ec698f8` |

El gate puede fallar y el resultado se conservará sin cambiar parámetros ni umbrales. El control convencional usa un estimador de heading más fuerte y por eso no se interpreta como una comparación puramente anatómica. Aprobar demostraría robustez conjunta dentro de estos escenarios simulados, no superioridad sobre control convencional ni fidelidad fisiológica completa.

### Resultado inmutable del gate integrado corregido

La corrida única terminó el 2026-10-11 con 120 vuelos y conservó los hashes congelados. El sistema completo alcanzó 22/30 metas: 14/15 en el escenario moderado y 8/15 en el fuerte. El convencional obtuvo 30/30, la ablación sin PFL2 22/30 y la ablación sin hΔB 0/30. El sistema completo tuvo 25,284 s de llegada mediana, 1,366 m de desvío máximo mediano, 0,436 de eficiencia y cero saturación. La mediana de error de heading durante dropout fue 26,73°, frente a 3,38° convencional.

Se aprobaron cuatro de ocho criterios: costo de desvío, ventaja sobre ausencia de hΔB, déficit frente a ausencia de PFL2 y saturación. Fallaron éxitos totales, éxitos por escenario, déficit frente al convencional y costo de llegada. El gate integrado queda **fallido**. No se modifican parámetros ni umbrales con estos datos.

Informe: `results/simulation/quadrotor_integrated_prospective/report.json`  
SHA-256: `02ad306a699b4e4c9c2fca159a5ae8a473a59bc93a56bbdd062b2c18a5c27d69`
