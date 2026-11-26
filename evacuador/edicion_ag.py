"""Lógica del editor del AG: el escenario más los grupos de personas.

``DisenoAG`` extiende ``DisenoEscenario`` con un catálogo de grupos
(celda -> tamaño). No importa ``tkinter``: el editor gráfico solo lo dibuja y
le pasa los clics, y las pruebas lo ejercitan directamente.

El AG no usa el inicio ni las salidas del escenario (él decide dónde van las
salidas), pero el CSV los necesita en su cabecera. Si el diseño no los tiene,
se usan la primera y la última celda transitable.
"""
from __future__ import annotations

from .config import BLOQUEADA, NIVEL_HUMO_DEFECTO
from .edicion import DisenoEscenario, DisenoInvalido, Herramienta
from .genetico import Grupo
from .modelos import Escenario, Posicion

TAMANO_GRUPO_DEFECTO = 4
TAMANO_GRUPO_MAX = 99


class DisenoAG(DisenoEscenario):
    """Escenario en edición más los grupos de personas que se van a evacuar."""

    grupos: dict[Posicion, int]   # celda -> personas; `nueva` lo inicia vacío

    # -- Cambios de estructura -------------------------------------------------

    def nueva(self, filas: int, columnas: int) -> None:
        super().nueva(filas, columnas)
        self.grupos = {}

    def restaurar(self) -> None:
        """Devuelve todas las celdas a libres y quita los grupos."""
        super().restaurar()
        self.grupos = {}

    def cargar(self, esc: Escenario) -> None:
        """Carga un escenario y conserva los grupos que sigan siendo válidos."""
        super().cargar(esc)
        self.grupos = {p: t for p, t in self.grupos.items()
                       if self.dentro(p) and self.valor(p) != BLOQUEADA}

    # -- Pintura ---------------------------------------------------------------

    def aplicar(self, herramienta: Herramienta | str, pos: Posicion,
                nivel_humo: int = NIVEL_HUMO_DEFECTO,
                tamano: int = TAMANO_GRUPO_DEFECTO) -> None:
        """Como ``DisenoEscenario.aplicar`` más la herramienta GRUPO.

        GRUPO coloca (o cambia el tamaño de) un grupo; una pared o BORRAR lo quitan.
        """
        if not self.dentro(pos):
            return
        herramienta = Herramienta(herramienta)
        if herramienta is Herramienta.GRUPO:
            self.grupos[pos] = min(max(int(tamano), 1), TAMANO_GRUPO_MAX)
            self._despejar(pos)
            return
        super().aplicar(herramienta, pos, nivel_humo)
        if herramienta is Herramienta.BORRAR or self.valor(pos) == BLOQUEADA:
            self.grupos.pop(pos, None)

    def poner_grupos(self, grupos: list[Grupo]) -> None:
        """Reemplaza los grupos. Lanza ValueError si alguno cae fuera del mapa o en un muro."""
        nuevos: dict[Posicion, int] = {}
        for g in grupos:
            if not self.dentro(g.celda):
                raise ValueError(f"El grupo en {g.celda} queda fuera de la cuadrícula "
                                 f"de {self.filas} × {self.columnas}")
            if self.valor(g.celda) == BLOQUEADA:
                raise ValueError(f"El grupo en {g.celda} está sobre una celda bloqueada")
            nuevos[g.celda] = nuevos.get(g.celda, 0) + g.tamano
        self.grupos = nuevos

    # -- Conversión ------------------------------------------------------------

    def lista_grupos(self) -> list[Grupo]:
        """Grupos en orden fila-columna."""
        return [Grupo(p, t) for p, t in sorted(self.grupos.items())]

    @property
    def personas(self) -> int:
        return sum(self.grupos.values())

    def a_escenario(self) -> Escenario:
        """Convierte la cuadrícula en ``Escenario``.

        Si faltan el inicio o la salida (que el AG no usa), se completan con la
        primera y la última celda transitable para que el CSV sea válido.

        Raises:
            DisenoInvalido: si todas las celdas están bloqueadas.
        """
        transitables = [(f, c) for f in range(self.filas) for c in range(self.columnas)
                        if self.grid[f][c] != BLOQUEADA]
        if not transitables:
            raise DisenoInvalido("Escenario inválido", "Todas las celdas están bloqueadas.")
        inicio = self.inicio
        if inicio is None or self.valor(inicio) == BLOQUEADA:
            inicio = transitables[0]
        salidas = [s for s in self.salidas if self.valor(s) != BLOQUEADA] or [transitables[-1]]
        try:
            return Escenario.desde_listas(self.grid, inicio, salidas)
        except ValueError as exc:
            raise DisenoInvalido("Escenario inválido", str(exc)) from exc
