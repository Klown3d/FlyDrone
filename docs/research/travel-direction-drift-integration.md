# Integración PFN/hΔB para compensar deriva

## Qué se integró

El modelo PFNd/PFNv→hΔB recibe el heading observado y el ángulo egocéntrico de la velocidad. Su fase decodificada representa la dirección allocéntrica estimada de desplazamiento. Una capa de ingeniería conserva la magnitud de velocidad medida y convierte la componente lateral respecto de la meta en aceleración correctiva.

La dirección proviene del circuito connectómico. La magnitud medida, la ganancia proporcional `2,0 s⁻¹` y el controlador de actitud son componentes de ingeniería; no se presentan como fisiología de la mosca.

## Diagnóstico 6DoF de desarrollo

Se ejecutaron 18 episodios emparejados, con tres bearings y dos escenarios:

- viento moderado de 0,5 N;
- viento fuerte de 0,8 N con ruido de velocidad de 0,05 m/s.

Cada caso se evaluó en tres condiciones:

1. compensación hΔB sin amortiguación lateral convencional;
2. sin ninguna compensación de deriva;
3. compensación convencional que accede directamente a la velocidad lateral.

| Condición | Llegadas | Desvío máximo mediano | Desvío medio mediano | Llegada mediana | Eficiencia mediana |
|---|---:|---:|---:|---:|---:|
| Convencional | 6/6 | 1,030 m | 0,368 m | 13,649 s | 0,716 |
| hΔB | 6/6 | 1,251 m | 0,388 m | 13,729 s | 0,660 |
| Sin compensación | 0/6 | 3,766 m | 1,433 m | — | — |

hΔB redujo el desvío máximo mediano un **66,8%** frente a no compensar y recuperó las seis llegadas. El controlador convencional conservó una ventaja de 0,221 m en desvío máximo, 0,080 s en llegada y 0,056 en eficiencia mediana.

## Interpretación

Este resultado demuestra en desarrollo que la salida del circuito puede cerrar el bucle de control y corregir deriva física simulada. No demuestra superioridad sobre un controlador convencional: el control convencional fue ligeramente mejor y recibe la velocidad lateral de forma directa.

La ablación sin compensación es funcional, pero todavía no aísla toda la conectividad PFN/hΔB. Los nulos de fase se evaluaron previamente en aislamiento; falta repetirlos dentro del dron.

## Próximo paso

El gate prospectivo posterior ejecutó 120 vuelos y aprobó 6/6 criterios. hΔB logró 30/30 llegadas, frente a 0/30 sin compensación y 0/30 con fases barajadas. Redujo 75,0% el desvío frente a ausencia y 92,5% frente al nulo. El convencional obtuvo 30/30 y un desvío máximo mediano de 1,217 m frente a 1,309 m para hΔB. No hubo saturación de motores.

El escritor original falló después de guardar los 120 episodios por serialización de un valor lógico. Las métricas se recuperaron sin repetir vuelos desde el CSV congelado, con hashes registrados previamente en `PREREGISTRO.md`.

La aplicación ya carga las 79 morfologías PFN/hΔB nuevas, colorea su actividad firmada y dibuja movimiento real, dirección hΔB y corrección. Un botón alterna hΔB frente a amortiguación convencional. El smoke test carga 286 esqueletos completos y completa un vuelo 6DoF con ráfaga.

## Artefactos

- Interfaz: `src/flydrone/neural/travel_direction_drift.py`.
- Configuración: `configs/travel_direction_drift.yaml`.
- Banco: `src/flydrone/simulation/benchmark_travel_direction_drift.py`.
- Casos: `configs/quadrotor_travel_direction_development.yaml`.
- Resultado: `results/simulation/quadrotor_travel_direction_development/report.json`.
- Resultado prospectivo: `results/simulation/quadrotor_travel_direction_prospective/report.json`.
