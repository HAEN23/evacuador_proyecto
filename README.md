# Sistema de Evacuación Segura (UCS)

Planificación de rutas de evacuación de menor riesgo acumulado en una planta
industrial modelada como cuadrícula estática, usando Búsqueda de Costo Uniforme.

## Modelo
| Valor de celda | Significado |
|---|---|
| 0 | Bloqueada (fuego, pared, humo letal) |
| 1 | Libre y limpia |
| 2-99 | Libre con concentración creciente de tóxico |

Costo de moverse a una celda = valor de la celda destino. Movimientos N, S, E, O.
Ambiente determinista, estático, observable y conocido. UCS no usa heurística.

## Uso
```
python -m evacuador generar data/mi_escenario.csv --filas 15 --cols 25 --seed 7
python -m evacuador resolver data/mi_escenario.csv
python -m evacuador resolver data/mi_escenario.csv --animar --pausa 0.03
python -m evacuador resolver data/mi_escenario.csv --grafico   # requiere matplotlib
```

## Formato CSV
```
# start=0,0 goal=11,19
1,1,0,1,...
```

## Pruebas
```
python -m unittest discover -s tests -v
```

## Estructura
- `config.py`: constantes del modelo
- `modelos.py`: `Escenario` y `Resultado` (inmutables)
- `ucs.py`: algoritmo
- `generador.py`: escenarios reproducibles con semilla
- `io_csv.py`: guardar y cargar escenarios
- `visualizacion.py`: ASCII, animación y gráfico
- `cli.py`: interfaz de línea de comandos
