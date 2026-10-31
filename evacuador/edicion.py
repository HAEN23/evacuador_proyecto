"""Lógica de edición de escenarios, independiente de la interfaz gráfica.

``DisenoEscenario`` guarda el diseño en curso (cuadrícula, inicio y salidas) y
aplica las herramientas de pintura. No importa ``tkinter``: el editor gráfico
solo lo dibuja y le pasa los clics, y las pruebas lo ejercitan directamente.
"""
from __future__ import annotations

from enum import Enum
from typing import Optional

from .config import (BLOQUEADA, COLUMNAS_POR_DEFECTO, COSTO_MAX, COSTO_MIN,
                     DIMENSION_MAX, DIMENSION_MIN, FILAS_POR_DEFECTO,
                     NIVEL_HUMO_DEFECTO)
from .modelos import Escenario, Posicion


class Herramienta(str, Enum):
    """Acciones de pintura disponibles en el editor."""
    BLOQUEADA = "bloqueada"
    LIBRE = "libre"
    HUMO = "humo"
    INICIO = "inicio"
    SALIDA = "salida"
    BORRAR = "borrar"


class DisenoInvalido(ValueError):
    """El diseño no se puede convertir en escenario.

    Attributes:
        titulo: Título sugerido para mostrar el problema al usuario.
    """

    def __init__(self, titulo: str, mensaje: str) -> None:
        super().__init__(mensaje)
        self.titulo = titulo


def limitar_dimension(valor: int) -> int:
    """Ajusta un número de filas o columnas al rango permitido."""
    return min(max(int(valor), DIMENSION_MIN), DIMENSION_MAX)


class DisenoEscenario:
    """Escenario en edición: cuadrícula, inicio, salidas y celdas marcadas.

    Las celdas "marcadas como libres" solo cambian el color en el editor
    (para distinguirlas de las que nunca se tocaron); su valor sigue siendo 1.
    """

    def __init__(self, filas: int = FILAS_POR_DEFECTO,
                 columnas: int = COLUMNAS_POR_DEFECTO) -> None:
        self.grid: list[list[int]] = []
        self.inicio: Optional[Posicion] = None
        self.salidas: list[Posicion] = []
        self.libres_marcadas: set[Posicion] = set()
        self.nueva(filas, columnas)

    # -- Consulta ------------------------------------------------------------

    @property
    def filas(self) -> int:
        return len(self.grid)

    @property
    def columnas(self) -> int:
        return len(self.grid[0]) if self.grid else 0

    def dentro(self, pos: Posicion) -> bool:
        return 0 <= pos[0] < self.filas and 0 <= pos[1] < self.columnas

    def valor(self, pos: Posicion) -> int:
        return self.grid[pos[0]][pos[1]]

    # -- Cambios de estructura -----------------------------------------------

    def nueva(self, filas: int, columnas: int) -> None:
        """Crea una cuadrícula libre; inicio en la esquina superior izquierda y
        salida en la inferior derecha."""
        filas, columnas = limitar_dimension(filas), limitar_dimension(columnas)
        self.grid = [[COSTO_MIN] * columnas for _ in range(filas)]
        self.libres_marcadas = set()
        self.inicio = (0, 0)
        self.salidas = [(filas - 1, columnas - 1)]

    def restaurar(self) -> None:
        """Devuelve todas las celdas a libres; conserva inicio y salidas."""
        self.grid = [[COSTO_MIN] * self.columnas for _ in range(self.filas)]
        self.libres_marcadas = set()

    def cargar(self, esc: Escenario) -> None:
        """Reemplaza el diseño por un escenario existente."""
        self.grid = [list(fila) for fila in esc.grid]
        self.libres_marcadas = set()
        self.inicio = esc.inicio
        self.salidas = list(esc.metas)

    # -- Pintura -------------------------------------------------------------

    def aplicar(self, herramienta: Herramienta | str, pos: Posicion,
                nivel_humo: int = NIVEL_HUMO_DEFECTO) -> None:
        """Aplica una herramienta sobre una celda. Ignora posiciones fuera del mapa."""
        if not self.dentro(pos):
            return
        herramienta = Herramienta(herramienta)
        if herramienta is Herramienta.LIBRE:
            self.libres_marcadas.add(pos)
        elif herramienta not in (Herramienta.INICIO, Herramienta.SALIDA):
            self.libres_marcadas.discard(pos)

        if herramienta is Herramienta.INICIO:
            self._colocar_inicio(pos)
        elif herramienta is Herramienta.SALIDA:
            self._colocar_salida(pos)
        elif herramienta is Herramienta.BORRAR:
            self._poner(pos, COSTO_MIN)
            self._quitar_marcas(pos)
        else:
            valor = {Herramienta.BLOQUEADA: BLOQUEADA,
                     Herramienta.LIBRE: COSTO_MIN}.get(herramienta, nivel_humo)
            self._poner(pos, min(max(int(valor), BLOQUEADA), COSTO_MAX))
            if valor == BLOQUEADA:  # una pared no admite inicio ni salida
                self._quitar_marcas(pos)

    def _poner(self, pos: Posicion, valor: int) -> None:
        self.grid[pos[0]][pos[1]] = valor

    def _quitar_marcas(self, pos: Posicion) -> None:
        if pos == self.inicio:
            self.inicio = None
        if pos in self.salidas:
            self.salidas = []

    def _colocar_inicio(self, pos: Posicion) -> None:
        """Inicio y salida son únicos: colocarlos de nuevo los traslada."""
        self.inicio = pos
        if pos in self.salidas:
            self.salidas = []
        self._despejar(pos)

    def _colocar_salida(self, pos: Posicion) -> None:
        self.salidas = [pos]
        if pos == self.inicio:
            self.inicio = None
        self._despejar(pos)

    def _despejar(self, pos: Posicion) -> None:
        if self.valor(pos) == BLOQUEADA:
            self._poner(pos, COSTO_MIN)

    # -- Conversión ----------------------------------------------------------

    def a_escenario(self) -> Escenario:
        """Valida el diseño y lo convierte en un :class:`Escenario`.

        Raises:
            DisenoInvalido: si falta el inicio o la salida, o alguno está bloqueado.
        """
        if self.inicio is None:
            raise DisenoInvalido("Escenario incompleto",
                                 "Coloque el punto de inicio del agente.")
        if not self.salidas:
            raise DisenoInvalido("Escenario incompleto",
                                 "Coloque la salida de emergencia.")
        for pos in (self.inicio, *self.salidas):
            if self.valor(pos) == BLOQUEADA:
                raise DisenoInvalido(
                    "Escenario inválido",
                    f"La celda {pos} es de inicio o salida y no puede estar bloqueada.")
        try:
            return Escenario.desde_listas(self.grid, self.inicio, self.salidas)
        except ValueError as exc:
            raise DisenoInvalido("Escenario inválido", str(exc)) from exc

