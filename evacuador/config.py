"""Constantes del dominio. Un único lugar para cambiar el modelo y los valores compartidos.

PARA LA DEFENSA: aquí vive el MODELO. Si el profesor pregunta "¿y si quiero otra
escala de humo?", se cambia en este archivo y nada más. Reglas del modelo:
    * 0      -> celda bloqueada (fuego, pared o humo letal): NO se puede pisar.
    * 1      -> celda limpia, costo mínimo.
    * 2..99  -> humo; mientras mayor el número, más tóxico y más caro pasar.
    * Costo de un movimiento = valor de la celda a la que se entra.
Este módulo NO importa nada del proyecto: todos los demás dependen de él.
"""

NOMBRE_SISTEMA = "Sistema de Evacuación Táctica"

# --- Modelo de costos -------------------------------------------------------
# 0 NO es "costo cero": es "infinito". Por eso se valida ANTES de sumar costos.
BLOQUEADA = 0        # fuego, pared o humo letal: intransitable
COSTO_MIN = 1        # celda libre y limpia
COSTO_MAX = 99       # humo denso, altamente tóxico
# Solo sirve para CONTAR cuántas celdas de humo atraviesa la ruta (métrica); no afecta la búsqueda.
UMBRAL_HUMO = 2      # desde este valor una celda cuenta como "con humo" (coincide con el modelo 2-99)

# Movimientos permitidos (fila, columna): Norte, Sur, Este, Oeste.
# Solo 4 direcciones (sin diagonales): cada paso cuesta lo que vale la celda destino.
MOVIMIENTOS = ((-1, 0), (1, 0), (0, 1), (0, -1))

# --- Editor de escenarios ---------------------------------------------------
FILAS_POR_DEFECTO = 12
COLUMNAS_POR_DEFECTO = 20
DIMENSION_MIN = 3
DIMENSION_MAX = 60
NIVEL_HUMO_DEFECTO = 50

# --- Colores del mapa (los usan la gráfica y la interfaz) --------------------
COLOR_BLOQUEADA = "#2E3640"
COLOR_INICIO = "#2E7D32"
COLOR_SALIDA = "#1565C0"
COLOR_RUTA = "#14304F"
COLOR_ALERTA = "#B3261E"
COLOR_EXPLORADA = "deepskyblue"
