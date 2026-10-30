"""Constantes del dominio. Un único lugar para cambiar el modelo de costos."""

BLOQUEADA = 0        # fuego, pared o humo letal: intransitable
COSTO_MIN = 1        # celda libre y limpia
COSTO_MAX = 99       # humo denso, altamente tóxico
UMBRAL_HUMO = 2      # desde este valor una celda cuenta como "con humo" (coincide con el modelo 2-99)

# Movimientos permitidos (fila, columna): Norte, Sur, Este, Oeste
MOVIMIENTOS = ((-1, 0), (1, 0), (0, 1), (0, -1))
