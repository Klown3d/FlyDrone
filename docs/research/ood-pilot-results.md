# Piloto OOD: resultados y límite identificado

Se ejecutaron los 12 vuelos previstos sin ajustar parámetros después de ver
resultados. Todos conservan la traza completa. Este piloto es diagnóstico.

| Controlador | Llegadas | Mediana de máximo desvío (m) | Mediana de error de heading durante corte (°) | Saturación |
|---|---:|---:|---:|---:|
| FlyWire v4 | 5/6 | 8.143 | 60.43 | 0 |
| Convencional | 6/6 | 2.236 | 2.64 | 0 |

Los dos controladores llegaron 2/2 bajo viento invertido y 2/2 con pérdida
tardía. Con heading y velocidad interrumpidos simultáneamente durante nueve
segundos, FlyWire llegó 1/2 y el convencional 2/2.

El vuelo fallido de FlyWire tuvo meta a 107°, orientación relativa inicial de
−137°, distancia terminal de 11.218 m y máximo desvío lateral de 24.478 m.
Su error mediano de heading durante el corte fue 88.30°. Se conserva el fallo
y no se lo trata como una llegada casi conseguida.

La brújula era un candidato claro para el siguiente diagnóstico, coherente con
sus limitaciones prospectivas anteriores. Un [diagnóstico posterior por
oráculos](ood-failure-oracle-diagnosis.md) reprodujo exactamente este caso:
heading verdadero rescató la llegada y velocidad verdadera por sí sola no.
Ese resultado localiza el fallo dominante de esta geometría en la vía de
heading o su uso posterior, pero sigue siendo una intervención de un solo caso.

Las seis geometrías son demasiado pocas para una conclusión fina: los
intervalos Wilson del 95% de éxito son aproximadamente 44--97% para 5/6 y
61--100% para 6/6. La comparación es descriptiva; no afirma una diferencia
estadística confirmatoria.

## Consecuencia para el alcance actual

La sensibilidad local ±20% fue favorable, pero no autoriza declarar robustez
global completada. El piloto detecta una degradación clara bajo pérdidas largas
y conserva la ventaja del convencional en precisión. La aplicación puede
mostrar este límite mientras se mantiene pendiente una evaluación OOD mayor.

## Ver los ensayos

Abrir `Start-FlyDrone-Gates3D.ps1`, seleccionar **Piloto OOD** y recorrer los
seis casos. El cuarto corresponde al fallo por pérdida larga. Se muestran las
trayectorias pareadas FlyWire/convencional y actividad neuronal sólo para FlyWire.

Datos: `results/simulation/quadrotor_integrated_v4_ood_pilot/`.
Preservación posterior: `archive/integrated_v4_ood_pilot/`.
Plan anterior a la corrida: `docs/research/ood-pilot-plan.md`.
