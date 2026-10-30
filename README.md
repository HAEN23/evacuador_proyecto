# Sistema de Evacuación Segura (UCS)

Planificación de rutas de evacuación de menor riesgo acumulado en una planta
industrial modelada como cuadrícula estática, usando Búsqueda de Costo Uniforme (UCS).

**Integrantes:** _(nombres)_  
**Materia:** Inteligencia Artificial

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

### Formato CSV

```
# start=0,0 goal=11,19
1,1,0,1,...
```

### Pruebas

```
python -m unittest discover -s tests -v
```

## Arquitectura

Arquitectura **modular por capas**, con una regla central: **las dependencias
apuntan siempre hacia el núcleo del dominio, nunca al revés.**

```
              ┌─────────────────────────────┐
  Entrada     │   cli.py  (interfaz)        │  Orquesta. No contiene lógica.
              └──────────────┬──────────────┘
                             │ usa
        ┌────────────────────┼─────────────────────┐
        ▼                    ▼                     ▼
 ┌─────────────┐     ┌──────────────┐     ┌─────────────────┐
 │ io_csv.py   │     │ generador.py │     │visualizacion.py │   Servicios
 │ (archivos)  │     │ (escenarios) │     │ (salida)        │   alrededor del
 └──────┬──────┘     └──────┬───────┘     └────────┬────────┘   núcleo
        │                   │ usa                  │
        │                   ▼                      │
        │            ┌─────────────┐               │
        │            │   ucs.py    │  Algoritmo    │
        │            │ (búsqueda)  │  puro         │
        │            └──────┬──────┘               │
        └───────────────────┼──────────────────────┘
                            ▼
                  ┌───────────────────┐
                  │   modelos.py      │  Escenario y Resultado
                  │   (dominio)       │  (inmutables, validados)
                  └─────────┬─────────┘
                            ▼
                  ┌───────────────────┐
                  │   config.py       │  Constantes del modelo
                  └───────────────────┘
```

| Módulo | Responsabilidad | No debe hacer |
|---|---|---|
| `config.py` | Constantes (0 = bloqueada, 1-99, umbral de humo, movimientos) | Tener lógica |
| `modelos.py` | `Escenario` y `Resultado`; validan sus datos al crearse | Leer archivos ni imprimir |
| `ucs.py` | El algoritmo y sus métricas | Imprimir, leer CSV, dibujar |
| `generador.py` | Crear escenarios reproducibles con semilla | Resolver ni dibujar |
| `io_csv.py` | Guardar y cargar escenarios | Conocer el algoritmo |
| `visualizacion.py` | ASCII, animación y gráfico | Modificar datos ni calcular rutas |
| `cli.py` | Leer argumentos y conectar las piezas | Contener lógica de negocio |

### Principios de diseño

- **Una responsabilidad por módulo.** Si un archivo hace dos cosas, se divide.
- **Dominio puro.** `modelos.py` y `ucs.py` no hacen entrada/salida. Se prueban sin archivos ni pantalla.
- **Entrada/salida en los bordes.** Solo `io_csv.py`, `visualizacion.py` y `cli.py` tocan el mundo exterior.
- **Datos inmutables.** `Escenario` y `Resultado` no se modifican después de crearse.
- **Validar antes de calcular.** La transitabilidad (celda ≠ 0) se comprueba antes de usar el costo.
- **Constantes en un solo lugar.** Cambiar el modelo de costos implica editar solo `config.py`.

### Dónde va cada cosa nueva

| Quiero agregar... | Va en... |
|---|---|
| Un nuevo parámetro o constante del modelo | `config.py` |
| Un nuevo dato del escenario o del resultado | `modelos.py` |
| Una nueva métrica de la búsqueda | `ucs.py` (y el campo en `Resultado`) |
| Una nueva forma de generar mapas | `generador.py` |
| Otro formato de archivo | `io_csv.py` (o un módulo `io_*.py` nuevo) |
| Un nuevo tipo de gráfico o tabla | `visualizacion.py` |
| Un nuevo comando | `cli.py`, que solo llama a los módulos anteriores |

### Reglas para evitar código espagueti

1. Las importaciones solo van **hacia abajo** en el diagrama. `ucs.py` nunca importa `cli.py` ni `visualizacion.py`.
2. Prohibido `print` e `input` fuera de `cli.py` y `visualizacion.py`.
3. Funciones cortas, con una sola tarea y con tipos (`type hints`).
4. Todo comportamiento nuevo trae su prueba en `tests/`.
5. Sin números mágicos: si un valor tiene significado, va a `config.py`.

## Flujo de trabajo con Git

```
main      → código estable y verificado (lo que se entrega)
develop   → integración del trabajo de ambos
edy / feature/...  → trabajo individual
```

1. Nadie hace push directo a `main` ni a `develop`.
2. Cada tarea se trabaja en su propia rama, creada desde `develop`.
3. Antes de abrir un Pull Request, correr las pruebas (deben dar `OK`).
4. El Pull Request va hacia `develop` y lo revisa el otro integrante.
5. Cuando `develop` esté probado y completo, se hace el Pull Request final hacia `main`.

Mensajes de commit claros: `Agrega script de experimentos`, no `cambios`.

## Estado del proyecto y tareas

### Hecho
- [x] Modelo de celdas y propuesta (PEAS, entorno, transiciones)
- [x] Algoritmo UCS con métricas (costo, pasos, celdas de humo, nodos, tiempo)
- [x] Generador de escenarios con semilla
- [x] Guardar y cargar escenarios en CSV
- [x] Visualización: ASCII, rastro de casillas exploradas y animación
- [x] Pruebas unitarias (10)
- [x] Estructura modular y README

### Pendiente
- [ ] Probar la visualización gráfica (`--grafico`) con matplotlib
- [ ] Script de experimentos: correr varios escenarios y generar la tabla de resultados
- [ ] Generar 3 o 4 escenarios de prueba en `data/` (sin humo, mucho humo, sin ruta)
- [ ] Informe: PEAS, modelo, algoritmo, experimentos, análisis, limitaciones, conclusiones
- [ ] Preparar la demo y las diapositivas (usar `--animar`)
- [ ] Completar nombres de integrantes en este README
- [ ] Pull Request final de `develop` a `main`

### Limitaciones conocidas (para el informe)
- El ambiente es **estático**: el humo no se propaga durante la evacuación.
- El costo es **lineal** respecto a la concentración de tóxico; es una decisión de modelado.
- El generador coloca inicio y salida en esquinas opuestas.

### Fuera de alcance
Ambiente dinámico, replanificación, otros algoritmos (A\*, BFS, genéticos) y
múltiples agentes. Pueden mencionarse como trabajo futuro.

## Requisitos

El núcleo usa solo la biblioteca estándar de Python. Para `--grafico`:

```
pip install -r requirements.txt
```
