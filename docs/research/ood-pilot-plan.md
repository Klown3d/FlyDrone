# Piloto de generalización fuera del régimen previo

Se fija esta matriz antes de ejecutar el piloto. No se reajustarán parámetros
con sus resultados. Se usa v4 y el baseline convencional con sus configuraciones
existentes, observaciones y semillas pareadas.

Cambios respecto de los gates previos: meta a 6 m en lugar de 4 m, viento
transversal invertido, pérdidas simultáneas de hasta 9 s, demora hasta 0,24 s
y perturbación tardía durante una navegación de 45 s. Dos geometrías por
escenario, tres escenarios, dos controladores: 12 vuelos.

Se informarán llegadas por escenario, desvío, colisiones, saturación y tiempo.
Este es un piloto diagnóstico pequeño y no un nuevo gate confirmatorio.
Los 12 vuelos se conservan con sus trazas completas, incluidos todos los fallos.
Una evaluación OOD mayor requerirá generador sellado y protocolo separado.
