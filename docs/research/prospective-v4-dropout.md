# Prueba prospectiva congelada de la brújula v4

## Pregunta

¿La brújula v4 corregida PB→EB mantiene una estimación útil del rumbo durante seis segundos sin señal externa en un vuelo 6DoF con ruido, demora y viento?

## Congelamiento

El protocolo, código, transferencias, umbrales y hashes se registraron en `PREREGISTRO.md` antes de ejecutar. La configuración `configs/quadrotor_heading_dropout_v4_prospective.yaml` contiene `run_once: true`; una segunda ejecución sobre el mismo directorio es rechazada.

Se evaluaron 30 casos inéditos por condición: cinco bearings objetivo y seis rumbos relativos iniciales. Los cuatro controladores recibieron exactamente la misma semilla, observaciones, ruido, demora, viento y corte de heading. En total se simularon 120 vuelos de 25 s.

## Criterios preregistrados

1. Éxito de v4 ≥ 90%.
2. Error mediano durante dropout ≤ 25°.
3. Error máximo durante dropout ≤ 75°.
4. Mejora frente a sample-and-hold ≥ 5°.

El gate sólo se consideraba superado si los cuatro criterios se cumplían.

## Resultado

| Controlador | Éxito | Error mediano durante dropout | Máximo | Eficiencia mediana |
|---|---:|---:|---:|---:|
| FlyWire v4 | 30/30 | 23,68° | 142,86° | 0,728 |
| Neural + sample-and-hold | 30/30 | 25,88° | 179,90° | 0,612 |
| Neural + giroscopio integrado | 30/30 | 2,27° | 10,47° | 0,732 |
| PID + giroscopio integrado | 30/30 | 2,55° | 11,58° | 0,771 |

V4 cumplió dos criterios: éxito y mediana absoluta. Falló el máximo y la mejora mínima. La diferencia entre las medianas agregadas fue 2,21°; el análisis emparejado posterior mostró una mejora mediana de 4,78° y v4 superó a sample-and-hold en 23/30 casos. Ambas medidas quedan por debajo de los 5° preregistrados.

Catorce de 30 casos tuvieron error mediano mayor a 25° y nueve superaron 75° de error máximo. El peor caso fue bearing −163° con rumbo relativo inicial +101°: mediana 68,56° y máximo 142,86°. Los fallos de cola se concentraron en algunas combinaciones de fase inicial y sentido de corrección, aunque todos los vuelos recuperaron la señal y llegaron a la meta.

## Decisión

**El gate prospectivo global falló.** V4 es una mejora parcial respecto de mantener el último rumbo y conserva navegación terminal, pero todavía no es una brújula robusta. No supera a la integración convencional de giroscopio, que obtuvo aproximadamente una décima parte del error mediano y errores máximos menores de 12°.

Este resultado no invalida el hallazgo anatómico PB→EB ni el control con 30 mapas de fase nulos. Demuestra que esos resultados aislados no bastan para generalizar de manera uniforme en vuelo 6DoF.

## Estado del módulo

La Fase 4 queda cerrada como **prototipo funcional con resultado prospectivo parcial**. La aplicación puede seguir usando v4 para visualización y desarrollo, con la etiqueta regularizada. No debe presentarse como brújula validada ni como alternativa superior a un observador convencional.

Una futura v5 deberá ser un ciclo correctivo nuevo y explícito. El primer objetivo será diagnosticar la dependencia de fase inicial y reducir los errores de cola sin consultar nuevamente esta prueba como conjunto de ajuste. Cualquier v5 requerirá nuevos casos y un nuevo preregistro.

Artefactos: `results/simulation/quadrotor_heading_dropout_v4_prospective/episodes.csv`, `summary.csv`, trazas y `report.json`. SHA-256 del informe: `654585c7d124ff698bb69cc6413ffbffc04b27679978cdf4833b6f43996907c6`.
