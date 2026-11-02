# Preregistro congelado: atribución PFN→hDeltaB v1

**Estado:** protocolo preparado para congelación criptográfica antes de la primera ejecución. Una vez creado `configs/quadrotor_connectome_confirmatory.lock.json`, cualquier cambio en código, configuración, entorno o datos bloquea la corrida.

## Pregunta e hipótesis

La pregunta primaria es si el controlador PFN→hDeltaB intacto alcanza navegación funcional con observaciones no privilegiadas. Si lo hace, se evaluará si su desempeño depende de la correspondencia de conexiones reconstruida de FlyWire.

La hipótesis confirmatoria no afirma superioridad de rendimiento frente a un controlador convencional ni frente al cálculo vectorial directo. Predice que el circuito intacto será funcional y superará a una familia predefinida de redes nulas con estadísticas anatómicas conservadas.

## Protocolo

La configuración canónica es `configs/quadrotor_connectome_confirmatory.yaml`. Contiene cuatro escenarios, cinco bearings y cinco orientaciones iniciales, para un total de 100 vuelos por condición. Ningún bearing, orientación o semilla se utilizó en los dos experimentos de desarrollo de controles nulos.

Se ejecutarán ocho condiciones:

1. PFN→hDeltaB FlyWire intacto.
2. Cinco reconexiones nulas con semillas 130021, 130027, 130043, 130051 y 130069.
3. Sustituto vectorial directo con la misma estimación de velocidad y regla de corrección.
4. Navegación convencional.

Total congelado: 800 vuelos.

Cada nulo conserva las 61 PFN, las 18 hDeltaB, grados binarios de entrada y salida, y el conjunto de pesos de entrada de cada hDeltaB por separado dentro de PFNd izquierda, PFNd derecha, PFNv izquierda y PFNv derecha. Cada matriz recibe una única calibración angular global equivalente a la del circuito intacto. No se conserva la suma ponderada de salida de cada PFN.

PFL2 y la capa de confianza graduada permanecen apagadas. El estabilizador de actitud, altura y motores es convencional en todas las condiciones. La fuerza específica 3D, posición observada, ruido, sesgo, retardo y pérdidas se comparten de forma pareada.

## Secuencia jerárquica

Los criterios se evalúan en este orden. Cuando falla uno, los posteriores se informan solamente como descriptivos.

1. **Función primaria:** al menos 90 llegadas terminales válidas entre los 100 vuelos intactos.
2. **Atribución al connectoma:** la tasa intacta debe superar la mediana de las cinco tasas nulas en al menos 20 puntos porcentuales y ser mayor o igual al percentil 95 interpolado de esas cinco tasas.
3. **Comparabilidad directa:** el déficit de éxitos respecto del sustituto directo no puede superar 10 puntos porcentuales.
4. **Seguridad:** cero colisiones en el intacto y saturación máxima de motores menor o igual a 0,01.

La llegada exige permanecer dentro del radio de meta, por debajo del límite de velocidad y a altura válida durante dos segundos. La métrica secundaria es el aumento pareado del error direccional mediano de cada nulo respecto del intacto, con intervalo bootstrap del 95%. Tiempo, eficiencia, desvío lateral, recuperación y resultados por escenario son exploratorios.

## Reglas de integridad

- El validador exige exactamente 100 casos por condición, cinco nulos y semillas nuevas.
- El lock incluye todos los módulos Python de FlyDrone, configuraciones YAML, archivos procesados de los circuitos utilizados, transferencia de brújula, preregistro, `pyproject.toml` y versiones del entorno.
- La carpeta de resultados debe estar vacía antes de ejecutar.
- El protocolo rechaza sobrescritura o reanudación silenciosa.
- Se conservarán vuelos fallidos, resultados negativos y todas las condiciones.
- Cualquier repetición posterior será un experimento distinto y recibirá otro identificador.

## Interpretación prevista

Si el gate completo pasa, se podrá afirmar que el modelo intacto produce navegación funcional y que, bajo este protocolo, su desempeño depende de una organización de contactos consistente con FlyWire. Si falla la atribución, el connectoma seguirá aportando trazabilidad e interpretabilidad, pero no habrá evidencia confirmatoria de que su cableado específico mejore la tarea. Si falla la comparabilidad, el circuito podrá ser funcional y anatómicamente dependiente sin ser competitivo con el cálculo directo.
