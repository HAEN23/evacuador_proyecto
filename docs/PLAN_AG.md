# Plan del Proyecto 2: EvacuAG

Sistema evolutivo de ubicación de salidas de emergencia para evacuaciones de menor riesgo.
Materia: Fundamentos de Inteligencia Artificial, UP Chiapas. Equipo: Edy Jordan González Abarca (243842) y Heber Alexander Escobar Nuricumbo (243691).

La propuesta enviada al profesor es la referencia de lo que se debe construir. Este archivo es el plan de trabajo. Si algo cambia en la propuesta, se actualiza aquí.

## 1. Objetivo

Dado un escenario (cuadrícula con muros, celdas libres y humo) y un catálogo de ocupantes, encontrar con un algoritmo genético las posiciones de `k` salidas que:

- O1: maximicen la cobertura (ocupantes con ruta), `O1 = N_ruta / N`.
- O2: minimicen el riesgo promedio, `O2 = riesgo_promedio / R_ref`.
- O3: minimicen el riesgo del peor ocupante, `O3 = riesgo_max / R_ref`.
- O4: minimicen el desbalance de ocupantes por salida, `O4 = sigma(ocupantes por salida) / (N_ruta / k)`.

```
Aptitud = O1 × 1/(1+O2) × 1/(1+O3) × 1/(1+O4)
```

Reglas de la aptitud:
- O2, O3, O4 se calculan solo con ocupantes que tienen ruta.
- Si nadie tiene ruta: O1 = 0, O2 = O3 = O4 = 0, aptitud = 0.
- `R_ref` = riesgo promedio con k salidas al azar (30 configuraciones, semilla fija), una sola vez por escenario.

## 2. Diseño base

- Individuo: lista de `2k` reales `[x1, y1, ..., xk, yk]`, cada gen en [0,1].
- Decodificación: `fila = round(y·(F−1))`, `col = round(x·(C−1))`.
- Reparación: si la celda no es válida (`valor == 1`) o queda a menos de `d_min` (distancia Manhattan) de otra salida, se mueve a la celda válida más cercana que cumpla. Si no existe, aptitud 0.
- Evaluación: para cada ocupante, UCS hacia cada salida y se toma el menor riesgo (el riesgo de una ruta es la suma de los valores de las celdas a las que entra). Se reutiliza `buscar_ucs`; el núcleo no se modifica.
- Operadores: torneo de 3, cruza aritmética `h = α·p1 + (1−α)·p2`, mutación gaussiana por gen recortada a [0,1], 2 élites.
- Parámetros iniciales: ver sección 3.

> Antes de codificar, revisar la firma real de `Escenario` en `modelos.py` (inicio y meta). Si solo admite una meta, se construye un `Escenario` por cada par ocupante-salida con `desde_listas`.

## 3. Contrato entre módulos

Esta es la interfaz que une el trabajo de los dos. No se cambia sin avisar al otro.

```python
# evacuador/genetico.py
@dataclass(frozen=True)
class ParametrosAG:
    tam_poblacion: int = 20
    p_cruza: float = 0.80
    p_mut_ind: float = 0.30
    p_mut_gen: float = 0.25
    sigma: float = 0.10
    torneo: int = 3
    elitismo: int = 2
    generaciones: int = 100
    k: int = 3
    d_min: int = 3
    semilla: int | None = None

@dataclass(frozen=True)
class Configuracion:
    salidas: tuple[tuple[int, int], ...]   # (fila, col) por salida
    o1: float
    o2: float
    o3: float
    o4: float
    aptitud: float
    riesgo_promedio: float
    riesgo_max: float
    ocupantes_por_salida: tuple[int, ...]

@dataclass(frozen=True)
class Generacion:
    numero: int
    mejor: Configuracion
    aptitud_mejor: float
    aptitud_promedio: float
    aptitud_peor: float

@dataclass(frozen=True)
class ResultadoAG:
    top3: tuple[Configuracion, ...]        # tres distintas, de mayor a menor aptitud
    historial: tuple[Generacion, ...]      # una por generación
    evaluaciones: int

def optimizar(escenario, ocupantes, params: ParametrosAG) -> ResultadoAG: ...
```

`ocupantes` es una lista de celdas `(fila, col)`.

## 4. Reparto de trabajo

Cada quien trabaja en su rama (`edy-ag`, `heber-ag`) y toca solo sus archivos.

| # | Tarea | Responsable | Archivos | Estado |
|---|-------|-------------|----------|--------|
| 1 | Decodificación de cromosoma a celdas y reparación | Edy | `evacuador/genetico.py`, `tests/test_genetico.py` | Pendiente |
| 2 | Evaluación de un individuo (O1–O4 con `buscar_ucs`) | Edy | `evacuador/genetico.py` | Pendiente |
| 3 | `R_ref` por escenario | Edy | `evacuador/genetico.py` | Pendiente |
| 4 | Aptitud producto y casos borde (sin ruta, sin ocupantes) | Edy | `evacuador/genetico.py` | Pendiente |
| 5 | Operadores y bucle generacional, `optimizar()` | Edy | `evacuador/genetico.py` | Pendiente |
| 6 | Top 3 distintas e historial por generación | Edy | `evacuador/genetico.py` | Pendiente |
| 7 | Formato y lectura de `ocupantes.csv` | Heber | `evacuador/io_ocupantes.py`, `data/ocupantes_*.csv`, `tests/test_io_ocupantes.py` | Pendiente |
| 8 | Subcomando `optimizar` del CLI | Heber | `evacuador/cli.py` | Pendiente |
| 9 | Línea base: salidas al azar y búsqueda exhaustiva en mapas pequeños | Heber | `evacuador/experimentos_ag.py`, `tests/test_experimentos_ag.py` | Pendiente |
| 10 | Gráfica de aptitud (mejor, promedio, peor) y tabla del mejor por generación | Heber | `evacuador/visualizacion_ag.py` | Pendiente |
| 11 | Mapa con las tres mejores configuraciones y tabla comparativa | Heber | `evacuador/visualizacion_ag.py` | Pendiente |
| 12 | Exportar resultados a CSV | Heber | `evacuador/io_ocupantes.py` o `experimentos_ag.py` | Pendiente |
| 13 | Experimentos y ajuste de parámetros en mapas A–E | Ambos | `evacuador/experimentos_ag.py` | Pendiente |
| 14 | Informe final | Ambos | `docs/` | Pendiente |

Mientras el núcleo no esté listo, Heber trabaja contra una función provisional que devuelva un `ResultadoAG` con datos de prueba.

Archivos compartidos (`cli.py`, `tests/test_arquitectura.py`): los toca una sola persona y se avisa. Agregar `genetico.py` a `test_arquitectura.py` (el núcleo no importa tkinter) lo hace Edy.

## 5. Flujo de git

- `main`: proyecto 1 entregado (etiqueta `v1.0-ucs`). No se toca hasta que el proyecto 2 esté completo.
- `develop`: integración del proyecto 2.
- `edy-ag` y `heber-ag`: ramas de trabajo de cada quien, salidas de `develop`.

Reglas:
1. Nadie hace push directo a `main` ni a `develop`; se entra por Pull Request.
2. El PR lo revisa la otra persona.
3. Antes de abrir un PR: `python3 -m unittest discover -s tests` debe pasar.
4. Cada pocos días se trae `develop` a la rama propia:
   ```
   git switch develop && git pull
   git switch edy-ag
   git merge develop
   ```
5. No usar `git add .`; agregar archivos por nombre.
6. Se pasa a `develop` cada pieza terminada, sin esperar a tener todo.
7. Mensajes de commit claros: `feat:`, `test:`, `fix:`, `docs:`.

## 6. Criterios de terminado

- `python3 -m unittest discover -s tests` pasa, con pruebas del núcleo AG.
- `genetico.py` no importa tkinter (verificado por `test_arquitectura.py`).
- Mismo escenario y misma semilla producen el mismo resultado.
- El sistema entrega las salidas de la propuesta: gráfica de evolución de la aptitud, tabla del mejor individuo por generación, tres mejores configuraciones sobre el mapa, tabla comparativa y comparación contra salidas al azar y contra búsqueda exhaustiva.
- En mapas pequeños, el AG alcanza una aptitud cercana a la exhaustiva y supera a las salidas al azar.
- Los parámetros usados en los experimentos quedan documentados.

## 7. Registro de decisiones

Anotar aquí cualquier cambio respecto a la propuesta (fecha, qué y por qué).

- 2026-11-23: plan creado.
