# Sistema de Evacuación Táctica (UCS)

Planificación de rutas de evacuación de menor riesgo acumulado en una planta
industrial modelada como cuadrícula estática, usando Búsqueda de Costo Uniforme (UCS).
Incluye una línea de comandos y una interfaz gráfica de escritorio.

**Integrantes:** Heber Alexander Escobar Nuricumbo, Edy Jordan González Abarca  
**Materia:** Fundamentos De Inteligencia Artificial  
**Institución:** Universidad Politécnica de Chiapas

## Modelo

| Valor de celda | Significado |
|---|---|
| 0 | Bloqueada (fuego, pared, humo letal) |
| 1 | Libre y limpia |
| 2-99 | Libre con concentración creciente de tóxico |

Costo de moverse a una celda = valor de la celda destino. Movimientos N, S, E, O.
Ambiente determinista, estático, observable y conocido. UCS no usa heurística.

## Requisitos

- **Núcleo y línea de comandos:** solo la biblioteca estándar de Python 3.10 o superior.
- **Gráfico e interfaz gráfica:** `tkinter`, `matplotlib` y `numpy`.

```
sudo apt install python3-tk            # Debian, Ubuntu, Kali
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
```

## Uso

### Línea de comandos

```
python -m evacuador generar data/mi_escenario.csv --filas 15 --cols 25 --seed 7
python -m evacuador resolver data/mi_escenario.csv
python -m evacuador resolver data/mi_escenario.csv --animar --pausa 0.03
python -m evacuador resolver data/mi_escenario.csv --grafico
python -m evacuador experimentos --csv resultados.csv --guardar-escenarios data/
```

### Interfaz gráfica

```
python -m evacuador gui
```

Permite abrir un escenario CSV, diseñarlo con el editor interactivo (paredes,
humo, inicio y salida), calcular la ruta y ver el mapa de riesgo con las métricas.

### Formato CSV

```
# start=0,0 goal=11,19
1,1,0,1,...
```

Con varias salidas: `goal=11,19;0,19`.

### Pruebas

```
python -m unittest discover -s tests -v
```

## Arquitectura

Arquitectura **modular por capas**, con una regla central: **las dependencias
apuntan siempre hacia el núcleo del dominio, nunca al revés.** Hay dos capas de
presentación (terminal e interfaz gráfica) que usan el mismo núcleo.

```
        ┌────────────────────┐          ┌───────────────────────────────┐
        │  cli.py            │          │  gui/  app · editor ·         │   Presentación
        │  (terminal)        │          │  resultado · tema  (tkinter)  │
        └─────────┬──────────┘          └───────────────┬───────────────┘
                  │                                     │
                  └──────────────────┬──────────────────┘
                                     │ usan
        ┌────────────────────┬───────┴────────────┬─────────────────┐
        ▼                    ▼                    ▼                 ▼
 ┌─────────────┐     ┌──────────────┐     ┌─────────────────┐  ┌─────────┐
 │ io_csv.py   │     │ generador.py │     │visualizacion.py │  │ ucs.py  │  Servicios
 │ (archivos)  │     │ edicion.py   │     │ (ASCII, mapa)   │  │ (búsq.) │  y algoritmo
 └──────┬──────┘     └──────┬───────┘     └────────┬────────┘  └────┬────┘
        │                   └──────────────────────┼────────────────┘
        └──────────────────────────────────────────┤
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
| `edicion.py` | Lógica del editor: herramientas de pintura, inicio/salida únicos, validación | Importar `tkinter` |
| `visualizacion.py` | ASCII, animación y `dibujar_mapa` (el único lugar donde se dibuja el mapa) | Modificar datos ni calcular rutas |
| `experimentos.py` | Correr UCS en varios escenarios y armar la tabla | Imprimir ni escribir archivos |
| `cli.py` | Leer argumentos y conectar las piezas | Contener lógica de negocio |
| `gui/tema.py` | Paleta, tipografía y estilos de la interfaz | Importar otras vistas |
| `gui/dialogos.py` | Diálogo «Guardar como CSV» compartido por el editor y la vista de resultado | Importar otras vistas |
| `gui/app.py` | Ventana principal, menús y navegación entre vistas (única que conoce a las demás vistas) | Contener lógica de negocio |
| `gui/editor.py` | Dibuja el editor y le pasa los clics a `edicion.py` | Decidir qué hace cada herramienta |
| `gui/resultado.py` | Métricas y marco del mapa (el dibujo lo hace `visualizacion.py`) | Calcular rutas ni dibujar por su cuenta |

### Principios de diseño

- **Una responsabilidad por módulo.** Si un archivo hace dos cosas, se divide.
- **Dominio puro.** `modelos.py` y `ucs.py` no hacen entrada/salida. Se prueban sin archivos ni pantalla.
- **Entrada/salida en los bordes.** Solo las capas de presentación, `io_csv.py` y `visualizacion.py` tocan el exterior.
- **Datos inmutables.** `Escenario` y `Resultado` no se modifican después de crearse.
- **Validar antes de calcular.** La transitabilidad (celda ≠ 0) se comprueba antes de usar el costo.
- **Constantes en un solo lugar.** Cambiar el modelo de costos implica editar solo `config.py`.
- **La interfaz no toca el algoritmo.** Terminal e interfaz gráfica usan el mismo `Escenario`, el mismo `buscar_ucs` y el mismo `Resultado`.

### Dónde va cada cosa nueva

| Quiero agregar... | Va en... |
|---|---|
| Un nuevo parámetro o constante del modelo | `config.py` |
| Un nuevo dato del escenario o del resultado | `modelos.py` |
| Una nueva métrica de la búsqueda | `ucs.py` (y el campo en `Resultado`) |
| Una nueva forma de generar mapas | `generador.py` |
| Otro formato de archivo | `io_csv.py` (o un módulo `io_*.py` nuevo) |
| Una nueva herramienta de pintura o regla del editor | `edicion.py` (y su botón en `gui/editor.py`) |
| Un nuevo tipo de gráfico o tabla | `visualizacion.py` |
| Un nuevo comando de terminal | `cli.py`, que solo llama a los módulos anteriores |
| Un color o estilo de la interfaz | `gui/tema.py` |
| Una nueva pantalla o control de la interfaz | `gui/app.py`, `gui/editor.py` o `gui/resultado.py` |

### Reglas para evitar código espagueti

1. Las importaciones solo van **hacia abajo** en el diagrama. `ucs.py` nunca importa `cli.py`, `gui/` ni `visualizacion.py`.
2. **Sin importaciones circulares** entre módulos del mismo nivel. Si dos módulos necesitan lo mismo (por ejemplo la paleta de colores: `gui/tema.py`), va en un tercer módulo del que ambos dependan.
3. Prohibido `print` e `input` fuera de `cli.py` y `visualizacion.py`.
4. Funciones cortas, con una sola tarea y con tipos (`type hints`).
5. Todo comportamiento nuevo trae su prueba en `tests/`.
6. Sin números mágicos: si un valor tiene significado, va a `config.py`.
7. Lo mismo no se dibuja ni se calcula en dos sitios: una función compartida.
8. Nada de estado global. Las vistas reciben lo que necesitan por argumentos.

Las reglas 1, 2 y 3 y el aislamiento de `tkinter` las verifica `tests/test_arquitectura.py`: si alguien las rompe, las pruebas fallan.

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
- [x] Guardar y cargar escenarios en CSV (editor, vista de resultado y menú Archivo › Guardar escenario como CSV…, Ctrl+S)
- [x] Visualización en terminal: ASCII, rastro de casillas exploradas y animación
- [x] Visualización gráfica (`--grafico`) con matplotlib
- [x] Pruebas unitarias del núcleo, los experimentos, la lógica del editor, el dibujo del mapa y la arquitectura (39)
- [x] Interfaz gráfica: inicio, editor de escenarios y vista de resultados
- [x] Estructura modular y README
- [x] Nombre unificado: **Sistema de Evacuación Táctica**
- [x] Interfaz gráfica fusionada en `develop` y verificada a mano en Linux (escenarios, editor, guardado, errores y menús)
- [x] Script de experimentos (`python -m evacuador experimentos`) y 5 escenarios en `data/`
- [x] Criterio de humo alineado: `UMBRAL_HUMO = 2` en `config.py`
- [x] Refactor de la interfaz: subpaquete `gui/`, `tema.py` (sin importaciones circulares), `edicion.py` (lógica del editor sin `tkinter`), `dibujar_mapa` compartido, sin estado global y comando `python -m evacuador gui`

### Pendiente: necesario para la entrega
- [ ] Informe: PEAS, modelo, algoritmo, experimentos, análisis, limitaciones, conclusiones
- [ ] Preparar la demo y las diapositivas (usar `--animar` y la interfaz)
- [ ] Pull Request final de `develop` a `main`

### Limitaciones conocidas (para el informe)
- El ambiente es **estático**: el humo no se propaga durante la evacuación.
- El costo es **lineal** respecto a la concentración de tóxico; es una decisión de modelado.
- El generador coloca inicio y salida en esquinas opuestas.
- Las vistas de la interfaz gráfica se verificaron a mano; solo su lógica (`edicion.py`) tiene pruebas automáticas.

### Fuera de alcance
Ambiente dinámico, replanificación, otros algoritmos (A\*, BFS, genéticos) y
múltiples agentes. Pueden mencionarse como trabajo futuro.
