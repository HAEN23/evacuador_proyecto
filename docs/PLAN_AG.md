# Plan del Proyecto 2: EvacuAG

Sistema evolutivo de ubicación de salidas de emergencia para evacuaciones de menor riesgo.
Materia: Fundamentos de Inteligencia Artificial, UP Chiapas. Equipo: Edy Jordan González Abarca (243842) y Heber Alexander Escobar Nuricumbo (243691).

La propuesta enviada al profesor es la referencia de lo que se debe construir. Este archivo es el plan de trabajo. Si algo cambia en la propuesta, se actualiza aquí.

## 1. Objetivo

Dado un escenario (cuadrícula con muros, celdas libres y humo) y un catálogo de grupos de personas, encontrar con un algoritmo genético las posiciones de maniobra de `k` salidas que:

- O1: maximicen el porcentaje de personas que salen, `O1 = personas que salen / personas totales`.
- O2: minimicen el riesgo al cruzar zonas críticas, `O2 = riesgo promedio por persona / R_ref`.
- O3: minimicen el tiempo de evacuación, `O3 = T_p / T_ref`, con `T_p` los segundos hasta que sale el `p %` de las personas (p = 90 % por defecto).
- O4: minimicen la aglomeración en las salidas, `O4 = personas en la peor ventana de una salida / personas que salen`.

```
Aptitud = O1 × 1/(1+O2) × 1/(1+O3) × 1/(1+O4)
```

Reglas de la aptitud:
- O2, O3, O4 se calculan solo con los grupos que tienen ruta.
- Si ningún grupo tiene ruta: O1 = 0, O2 = O3 = O4 = 0, aptitud = 0.
- `R_ref` y `T_ref` son el riesgo promedio por persona y el tiempo `T_p` con k salidas al azar (30 configuraciones, semilla fija), una sola vez por escenario. Si valen 0 se usa 1.
- O4 queda en [0, 1].

Se reportan además `T50`, `T90`, `T100` y la curva de evacuación (porcentaje de personas evacuadas contra segundos).

## 2. Diseño base

- Individuo: lista de `2k` reales `[x1, y1, ..., xk, yk]`, cada gen en [0,1]. Es la posición de maniobra de cada salida.
- Decodificación: `fila = round(y·(F−1))`, `col = round(x·(C−1))` (redondeo clásico, 0.5 sube).
- Reparación: si la celda no es válida (`valor == 1`) o queda a menos de `d_min` (distancia Manhattan) de otra salida, se mueve a la celda válida más cercana que cumpla. Si no existe, aptitud 0.
- Grupos: cada grupo se mueve como una sola entidad y tiene un tamaño (personas).
- Evaluación: un UCS por grupo con todas las salidas como `metas`; el UCS devuelve la ruta de menor riesgo y su salida. Se reutiliza `buscar_ucs`; el núcleo no se modifica.
- Tiempo: cada casilla recorrida cuesta 1 segundo, por lo que el tiempo de un grupo es el número de pasos de su ruta. El costo de riesgo no cambia.
- Aglomeración: para cada salida se suman las personas que llegan dentro de una ventana de `w` segundos (5 por defecto, arrancando en cada llegada); cuenta la peor ventana de todas las salidas.
- Operadores: torneo de 3, cruza aritmética `h = α·p1 + (1−α)·p2`, mutación gaussiana por gen recortada a [0,1], 2 élites.
- Parámetros iniciales: ver sección 3.

Limitación conocida: la aglomeración es una aproximación estática (sin colas ni capacidad de puerta).

## 3. Contrato entre módulos

Esta es la interfaz que une el trabajo de los dos. No se cambia sin avisar al otro.

```python
# evacuador/genetico.py
@dataclass(frozen=True)
class Grupo:
    celda: tuple[int, int]
    tamano: int = 1

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
    p_evac: float = 0.90
    ventana: int = 5
    semilla: int | None = None

@dataclass(frozen=True)
class Configuracion:
    salidas: tuple[tuple[int, int], ...]   # (fila, col), ordenadas
    o1: float
    o2: float
    o3: float
    o4: float
    aptitud: float
    riesgo_promedio: float                 # por persona, sin normalizar
    riesgo_max: float                      # informativo
    personas_por_salida: tuple[int, ...]
    t50: int                               # segundos hasta que sale el 50 %
    t90: int
    t100: int
    aglomeracion_max: int                  # personas en la peor ventana
    curva_evacuacion: tuple[tuple[int, float], ...]   # (segundo, fracción acumulada del total)

@dataclass(frozen=True)
class Generacion:
    numero: int                            # la 0 es la población inicial
    mejor: Configuracion
    aptitud_mejor: float
    aptitud_promedio: float
    aptitud_peor: float

@dataclass(frozen=True)
class ResultadoAG:
    top3: tuple[Configuracion, ...]        # hasta 3 distintas, de mayor a menor aptitud
    historial: tuple[Generacion, ...]      # generaciones 0..n
    evaluaciones: int                      # configuraciones distintas evaluadas con UCS

def optimizar(escenario, grupos, params: ParametrosAG) -> ResultadoAG: ...
```

`grupos` es una lista de `Grupo`, de `(fila, col)` (tamaño 1) o de `(fila, col, tamaño)`.

## 4. Reparto de trabajo

Cada quien trabaja en su rama (`edy-ag`, `heber-ag`) y toca solo sus archivos.

| # | Tarea | Responsable | Archivos | Estado |
|---|-------|-------------|----------|--------|
| 1 | Decodificación de cromosoma a celdas y reparación | Edy | `evacuador/genetico.py`, `tests/test_genetico.py` | Hecho |
| 2 | Evaluación de un grupo de salidas (O1–O4, tiempos y aglomeración con `buscar_ucs`) | Edy | `evacuador/genetico.py` | Hecho |
| 3 | `R_ref` y `T_ref` por escenario | Edy | `evacuador/genetico.py` | Hecho |
| 4 | Aptitud producto y casos borde (sin ruta, sin grupos) | Edy | `evacuador/genetico.py` | Hecho |
| 5 | Operadores y bucle generacional, `optimizar()` | Edy | `evacuador/genetico.py` | Hecho |
| 6 | Top 3 distintas e historial por generación | Edy | `evacuador/genetico.py` | Hecho |
| 7 | Formato y lectura de `grupos.csv` (fila, columna, tamaño) | Heber | `evacuador/io_grupos.py`, `data/grupos_*.csv`, `tests/test_io_grupos.py` | Pendiente |
| 8 | Subcomando `optimizar` del CLI (opciones `--p-evac` y `--ventana`) | Heber | `evacuador/cli.py` | Pendiente |
| 9 | Línea base: salidas al azar y búsqueda exhaustiva en mapas pequeños | Heber | `evacuador/experimentos_ag.py`, `tests/test_experimentos_ag.py` | Pendiente |
| 10 | Gráfica de aptitud (mejor, promedio, peor) y tabla del mejor por generación | Heber | `evacuador/visualizacion_ag.py` | Pendiente |
| 11 | Mapa con las tres mejores configuraciones, tabla comparativa y curva de evacuación | Heber | `evacuador/visualizacion_ag.py` | Pendiente |
| 12 | Exportar resultados a CSV | Heber | `evacuador/io_grupos.py` o `experimentos_ag.py` | Pendiente |
| 13 | Experimentos y ajuste de parámetros en mapas A–E | Ambos | `evacuador/experimentos_ag.py` | Pendiente |
| 14 | Informe final | Ambos | `docs/` | Pendiente |

Archivos compartidos (`cli.py`, `tests/test_arquitectura.py`): los toca una sola persona y se avisa. Agregar `genetico.py` a `test_arquitectura.py` (el núcleo no importa tkinter) ya lo hizo Edy.

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
- El sistema entrega las salidas de la propuesta: gráfica de evolución de la aptitud, tabla del mejor individuo por generación, tres mejores configuraciones sobre el mapa, tabla comparativa (con T50/T90/T100 y aglomeración), curva de evacuación y comparación contra salidas al azar y contra búsqueda exhaustiva.
- En mapas pequeños, el AG alcanza una aptitud cercana a la exhaustiva y supera a las salidas al azar.
- Los parámetros usados en los experimentos quedan documentados.

## 7. Registro de decisiones

Anotar aquí cualquier cambio respecto a la propuesta (fecha, qué y por qué).

- 2026-11-23: plan creado.
- 2026-11-24: `Escenario` admite varias metas, así que se usa un solo UCS por grupo con todas las salidas como metas.
- 2026-11-24: el historial incluye la generación 0 (población inicial), por lo que tiene n+1 entradas.
- 2026-11-24: `evaluaciones` cuenta configuraciones distintas evaluadas con UCS (hay caché por configuración).
- 2026-11-25: tras comentarios del profesor (posición de maniobra, aglomeraciones, zonas críticas, tiempos de salida) y la entrevista con protección civil, el modelo pasa a grupos con tamaño, 1 casilla = 1 segundo, porcentaje de personas que salen (O1), tiempo T_p (O3, en vez del riesgo del peor ocupante) y aglomeración por ventana (O4, en vez del desbalance entre salidas). La fórmula de la aptitud no cambia. El profesor dio el visto bueno.
- 2026-11-25: T_p se calcula sobre las personas que sí llegan a una salida, para que siempre esté definido; las que no tienen ruta ya las castiga O1.
- 2026-11-25: pendiente en los experimentos (tarea 13): top 3 con separación mínima entre configuraciones y ajuste de sigma y élites por convergencia temprana.
- 2026-11-25: el desbalance entre salidas y el riesgo del peor grupo dejaron de ser objetivos; siguen como datos informativos (`personas_por_salida`, `riesgo_max`).
