# Resultado del gate operacional híbrido v5

Fecha de ejecución: **2026-10-31**. Fecha de auditoría post-ejecución: **2026-11-02**. Estado: **gate prospectivo aprobado, 10/10 criterios**.

## Alcance de la afirmación

Este resultado valida robustez operacional en simulación de un controlador de alto nivel **FlyWire-grounded asistido por integración inercial de ingeniería**. No demuestra que el compass neuronal sea superior al giroscopio ni que su contribución durante dropout sea causal para el rendimiento.

## Integridad

El protocolo fue congelado antes de ejecutar. La auditoría posterior comprobó:

- 316 archivos congelados, sin cambios de hash;
- mismo Python y mismas versiones de seis dependencias registradas;
- 96 episodios: 24 por cada una de cuatro condiciones;
- 96 trazas presentes, sin claves faltantes ni inesperadas;
- cada traza tiene 2500 pasos y columnas consistentes;
- cero archivos de traza inválidos;
- informe automático con 10/10 criterios verdaderos.

El comando genérico `verify` rechaza correctamente un directorio `run_once` ya poblado, por lo que no sirve como auditor posterior. La comprobación posterior se realizó de forma independiente y de sólo lectura contra el lock original.

## Resultado primario

| Condición | Llegadas | Error heading durante dropout | Desvío transversal máximo | Eficiencia | Tiempo de llegada |
|---|---:|---:|---:|---:|---:|
| Híbrido v5 | **24/24** | 4,87° | 1,987 m | 0,630 | 31,616 s |
| Compass neuronal v4 | 12/24 | 77,95° | 9,517 m | 0,386 | 13,188 s* |
| Heading giroscópico, circuito downstream igual | **24/24** | 4,14° | 1,998 m | 0,649 | 31,619 s |
| Convencional | **24/24** | 4,12° | 1,838 m | 0,716 | 31,538 s |

\* La mediana v4 se calcula sólo sobre sus 12 llegadas y no implica que v4 sea globalmente más rápido.

El híbrido obtuvo 8/8 en cada escenario. V4 obtuvo 6/8 con pérdida larga de heading, 6/8 con pérdida tardía y 0/8 con pérdidas superpuestas.

## Criterios congelados

| Criterio | Umbral | Observado | Estado |
|---|---:|---:|---|
| Llegadas híbridas | ≥22/24 | 24/24 | aprobado |
| Mínimo por escenario | ≥7/8 | 8/8 | aprobado |
| Déficit frente a giroscopio | ≤1 | 0 | aprobado |
| Ventaja frente a v4 | ≥4 | 12 | aprobado |
| Error mediano de heading | ≤10° | 4,87° | aprobado |
| Costo transversal frente a giroscopio | ≤0,40 m | −0,011 m | aprobado |
| Peso neuronal mediano | ≥0,01 | 0,041 | aprobado |
| Peso neuronal máximo | ≤0,250001 | 0,160 | aprobado |
| Colisiones híbridas | 0 | 0 | aprobado |
| Saturación máxima | 0 | 0 | aprobado |

## Comparaciones pareadas secundarias

Estas comparaciones no fueron criterios inferenciales preregistrados y se informan como análisis secundarios:

- híbrido frente a v4: 12 pares discordantes favorables al híbrido y ninguno favorable a v4; McNemar exacto bilateral `p = 0,000488`;
- diferencia mediana híbrido−giroscopio en error de heading: 0,304°; bootstrap pareado 95% [−0,201°, 0,580°];
- diferencia mediana en desvío máximo: 0,000 m; bootstrap 95% [−0,0015 m, 0,000 m];
- diferencia mediana en llegada: 0,000 s; bootstrap 95% [0,000 s, 0,002 s];
- diferencia mediana en eficiencia: 0,00135; bootstrap 95% [−0,00096, 0,00300].

El híbrido y el control giroscópico son operacionalmente casi indistinguibles en esta matriz. Esto es consistente con una fusión que reduce el peso neuronal cuando las fuentes discrepan.

## Contribución neuronal observada

El peso neuronal medio durante dropout, calculado por vuelo, tuvo media 0,063, mediana 0,041 y rango 0,018–0,145. El máximo instantáneo global fue 0,160. La rama neuronal permaneció activa y acotada, pero la estimación estuvo dominada por la integración inercial.

Un vuelo alcanzó error mediano de dropout de 23,62°, aunque el agregado permaneció bajo el umbral. Esto impide afirmar uniformidad perfecta caso por caso y debe conservarse para inspección visual.

## Qué quedó demostrado

1. La corrección híbrida generalizó a una matriz nueva congelada: 24/24 frente a 12/24 de v4.
2. El controlador FlyWire-grounded asistido mantuvo steering autónomo de alto nivel sin colisiones ni saturación.
3. La solución no pagó un costo medible importante frente al control giroscópico en llegada o trayectoria.
4. Las trazas permiten distinguir y cuantificar la contribución neuronal y la capa inercial.

## Qué no quedó demostrado

1. Que el compass neuronal puro sea robusto ante pérdidas prolongadas; v4 volvió a fallar.
2. Que la actividad del compass mejore al control giroscópico; el gate no fue diseñado para esa atribución y los rendimientos fueron casi idénticos.
3. Que el sistema esté listo para un dron físico o para condiciones no simuladas.
4. Que la robustez cubra escenarios fuera de los tres perfiles sellados.

## Próximo paso

Integrar las 96 trazas como categoría `Gate híbrido v5` en el comparador 3D, mostrando heading fusionado, heading neuronal, heading giroscópico, peso neuronal y dropout. En paralelo, mantener una línea separada para mejorar el compass neuronal puro sin usar este gate operacional como evidencia biológica.

## Integración 3D completada

La categoría `Gate híbrido v5` quedó integrada en la aplicación. Permite seleccionar las comparaciones contra v4, heading giroscópico y navegación convencional, y recorrer los 24 casos de cada una. Muestra por separado heading fusionado, neuronal y giroscópico, junto con peso neuronal y desacuerdo angular.

El modo exhaustivo realizó 153 comprobaciones visuales y funcionales; 74 correspondieron al gate v5. Reconstruyó el steering de los 72 pares v5 y obtuvo un error máximo respecto del comando guardado de `2,845×10⁻¹⁵ rad/s`, compatible con redondeo numérico. La exportación PNG/CSV/JSON también pasó el smoke test.
