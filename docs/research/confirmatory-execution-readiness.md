# Preparación de ejecución: gate confirmatorio PFN→hDeltaB v1

## Estado

**Listo y congelado; todavía no ejecutado.**

- Protocolo: `flydrone_pfn_hdelta_confirmatory_v1`
- Configuración: `configs/quadrotor_connectome_confirmatory.yaml`
- Lock: `configs/quadrotor_connectome_confirmatory.lock.json`
- SHA-256 del lock: `df37bf86636ff4f1e92ee197dadf8e7fdb2b4902bb531bc9ea8acdd4eb705698`
- Casos: 100 por condición
- Condiciones: 8
- Total: 800 vuelos
- Pruebas antes de congelar: 139/139 aprobadas

## Comprobaciones terminadas

- Los cinco bearings, cinco headings, cuatro semillas de escenario y cinco semillas nulas no aparecen en los experimentos de desarrollo de conectividad.
- Cada nulo conserva tipo PFN, lado, grados binarios y conjuntos de pesos por hDeltaB.
- El análisis jerárquico está implementado y forma parte del lock.
- El entorno congelado incluye Python 3.13.14, NumPy 2.5.3, pandas 2.3.3, SciPy 1.18.1, PyArrow 25.0.1 y Panda3D 1.10.16.
- La carpeta de salida confirmatoria no contiene resultados previos.
- La verificación posterior del lock terminó sin diferencias.

## Recursos previstos

Con base en las corridas de desarrollo, se esperan aproximadamente 90–120 minutos de cálculo secuencial y unos 800 MB de trazas comprimidas. La ejecución debe hacerse en un período continuo, con el equipo conectado a corriente, sin suspensión automática y sin modificar el repositorio ni actualizar dependencias.

## Ejecución

Desde la raíz del proyecto:

```powershell
$env:PYTHONPATH=(Resolve-Path 'src').Path
.\.venv\Scripts\python.exe -m flydrone.simulation.confirmatory_protocol verify
.\.venv\Scripts\python.exe -m flydrone.simulation.confirmatory_protocol run
.\.venv\Scripts\python.exe -m flydrone.simulation.analyze_confirmatory_gate
```

El segundo comando es la ejecución única. Si se interrumpe después de crear resultados parciales, esos datos deben conservarse como corrida fallida; no se deben borrar para repetir silenciosamente la misma versión.

## Productos esperados

- `results/simulation/quadrotor_connectome_confirmatory_v1/episodes.csv`
- `results/simulation/quadrotor_connectome_confirmatory_v1/report.json`
- `results/simulation/quadrotor_connectome_confirmatory_v1/confirmatory_analysis.json`
- trazas completas de las condiciones neuronales y del sustituto directo;
- actualización de `data/manifest.json`.

No se interpretará ningún resultado parcial antes de terminar los 800 vuelos y ejecutar el análisis congelado.
