"""Constantes del dominio. Un único lugar para cambiar el modelo y los valores compartidos."""

NOMBRE_SISTEMA = "Sistema de Evacuación Táctica"

# --- Modelo de costos -------------------------------------------------------
BLOQUEADA = 0        # fuego, pared o humo letal: intransitable
COSTO_MIN = 1        # celda libre y limpia
COSTO_MAX = 99       # humo denso, altamente tóxico
UMBRAL_HUMO = 2      # desde este valor una celda cuenta como "con humo" (coincide con el modelo 2-99)

# Movimientos permitidos (fila, columna): Norte, Sur, Este, Oeste
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
