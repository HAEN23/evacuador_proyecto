"""Editor del algoritmo genético (EvacuAG).

Reutiliza la cuadrícula, el zoom y la pintura del editor de escenarios y añade:

* la herramienta «Grupo de personas» (cada grupo tiene un tamaño);
* abrir, guardar y generar al azar el catálogo de grupos (CSV ``fila,columna,tamano``);
* salidas de emergencia colocadas a mano o generadas al azar (k y distancia
  mínima de los parámetros); al ejecutar se comparan con las que elige el AG;
* los parámetros del AG y el botón que lo ejecuta.
"""

from __future__ import annotations

import os
import random
import tkinter as tk
from tkinter import filedialog, messagebox
from tkinter import ttk
from typing import Callable, Final, Optional

from ..config import (COLOR_INICIO, COLOR_SALIDA, COSTO_MAX, DIMENSION_MAX, DIMENSION_MIN, UMBRAL_HUMO)
from ..edicion import Herramienta
from ..edicion_ag import TAMANO_GRUPO_DEFECTO, TAMANO_GRUPO_MAX, DisenoAG
from ..genetico import (K_PERMITIDOS, Configuracion, Grupo, ParametrosAG, ResultadoAG,
                        crear_problema, evaluar, optimizar)
from ..io_grupos import cargar_grupos, generar_grupos, guardar_grupos
from ..modelos import Escenario, Posicion
from .dialogos import TIPOS_CSV
from .editor import EditorEscenarios

HERRAMIENTAS_AG: Final[tuple[tuple[Herramienta, str], ...]] = (
    (Herramienta.BLOQUEADA, "Celda bloqueada (0)"),
    (Herramienta.LIBRE, "Celda libre (1)"),
    (Herramienta.HUMO, "Humo / tóxico (2 – 99)"),
    (Herramienta.GRUPO, "Grupo de personas"),
    (Herramienta.SALIDA, "Salida de emergencia"),
    (Herramienta.BORRAR, "Borrar (restaurar celda)"),
)

# Firma del aviso que recibe la ventana principal cuando termina el AG. El último
# argumento es la evaluación de las salidas del editor (None si no se colocaron).
AlOptimizar = Callable[[Escenario, list[Grupo], ParametrosAG, ResultadoAG,
                        Optional[Configuracion]], None]


class EditorAG(EditorEscenarios):
    """Vista para diseñar el escenario y los grupos y ejecutar el AG.

    Args:
        padre: Contenedor de la vista.
        estado: Variable de la barra de estado de la ventana principal.
        al_optimizar: Se invoca con escenario, grupos, parámetros y resultado del AG.
        al_volver: Acción del botón "Volver al inicio".
    """

    def __init__(self, padre: tk.Misc, estado: tk.StringVar, al_optimizar: AlOptimizar,
                 al_volver: Callable[[], None]) -> None:
        # Las variables del panel se crean antes porque la clase base construye el panel.
        self._tamano_grupo = tk.IntVar(value=TAMANO_GRUPO_DEFECTO)
        self._n_azar = tk.IntVar(value=12)
        self._conteo = tk.StringVar()
        defecto = ParametrosAG()
        self._k = tk.StringVar(value=str(defecto.k))
        self._d_min = tk.StringVar(value=str(defecto.d_min))
        self._poblacion = tk.StringVar(value=str(defecto.tam_poblacion))
        self._generaciones = tk.StringVar(value=str(defecto.generaciones))
        self._p_evac = tk.StringVar(value=str(defecto.p_evac))
        self._ventana = tk.StringVar(value=str(defecto.ventana))
        self._semilla = tk.StringVar(value="7")
        self._ruta_grupos: Optional[str] = None
        super().__init__(padre, estado, al_calcular=al_optimizar, al_volver=al_volver)
        self._herramienta.set(Herramienta.GRUPO.value)

    # -- Modelo ------------------------------------------------------------

    def _crear_diseno(self) -> DisenoAG:
        return DisenoAG()

    def _marca(self, pos: Posicion) -> Optional[tuple[str, str]]:
        """Grupo: círculo verde con sus personas. Salida: círculo azul con «S»."""
        tamano = self._diseno.grupos.get(pos)
        if pos in self._diseno.salidas:
            return (str(tamano) if tamano else "S", COLOR_SALIDA)
        return (str(tamano), COLOR_INICIO) if tamano else None

    def _aplicar(self, pos: Posicion) -> None:
        try:
            tamano = int(self._tamano_grupo.get())
        except (tk.TclError, ValueError):
            tamano = TAMANO_GRUPO_DEFECTO
        self._diseno.aplicar(self._herramienta.get(), pos, int(self._nivel_humo.get()), tamano)

    def _dibujar(self) -> None:
        super()._dibujar()
        n, personas = len(self._diseno.grupos), self._diseno.personas
        salidas = len(self._diseno.salidas)
        self._conteo.set(f"{n} grupo{'s' if n != 1 else ''} · {personas} persona"
                         f"{'s' if personas != 1 else ''} · {salidas} salida"
                         f"{'s' if salidas != 1 else ''}")

    def cargar_escenario(self, esc: Escenario) -> None:
        super().cargar_escenario(esc)
        self._dibujar()

    # -- Panel lateral -----------------------------------------------------

    def _crear_panel_herramientas(self) -> None:
        """Panel lateral: dimensiones, herramientas, grupos, parámetros y acciones."""
        panel = self._crear_contenedor_desplazable()
        fila = iter(range(100))  # filas consecutivas de la rejilla del panel

        def poner(widget: tk.Widget, **kw) -> None:
            widget.grid(row=next(fila), column=0, sticky=kw.pop("sticky", "ew"), **kw)

        def boton(texto: str, accion, primario: bool = False, **kw) -> None:
            poner(ttk.Button(panel, text=texto, cursor="hand2", command=accion,
                             style="Primary.TButton" if primario else "Secondary.TButton"),
                  **kw)

        poner(ttk.Label(panel, text="ALGORITMO GENÉTICO", style="CardEyebrow.TLabel"),
              sticky="w")
        poner(ttk.Label(panel, text="Escenario y grupos", style="SectionTitle.TLabel"),
              sticky="w", pady=(4, 4))
        poner(ttk.Label(panel, text="Las salidas que coloque aquí se comparan con las que "
                                    "elige el algoritmo genético al ejecutarlo (F5).",
                        style="Hint.TLabel", wraplength=300, justify="left"),
              sticky="w", pady=(0, 14))

        # Dimensiones
        poner(ttk.Label(panel, text="Dimensiones", style="Subsection.TLabel"),
              sticky="w", pady=(0, 6))
        dimensiones = ttk.Frame(panel, style="Card.TFrame")
        for col, (texto, variable) in enumerate((("Filas", self._filas),
                                                 ("Columnas", self._columnas))):
            ttk.Label(dimensiones, text=texto, style="Body.TLabel").grid(
                row=0, column=col * 2, sticky="w", padx=(0 if col == 0 else 12, 6))
            ttk.Spinbox(dimensiones, from_=DIMENSION_MIN, to=DIMENSION_MAX, width=4,
                        textvariable=variable).grid(row=0, column=col * 2 + 1)
        poner(dimensiones)
        boton("Generar cuadrícula", self._confirmar_nueva_cuadricula, pady=(10, 0))
        boton("Restaurar cuadrícula", self.restaurar_cuadricula, pady=(8, 0))
        poner(ttk.Separator(panel), pady=16)

        # Herramientas
        poner(ttk.Label(panel, text="Herramienta", style="Subsection.TLabel"),
              sticky="w", pady=(0, 6))
        for clave, etiqueta in HERRAMIENTAS_AG:
            poner(ttk.Radiobutton(panel, text=etiqueta, value=clave.value,
                                  variable=self._herramienta, style="Tool.TRadiobutton"),
                  sticky="w", pady=1)
        nivel = ttk.Frame(panel, style="Card.TFrame")
        nivel.columnconfigure(1, weight=1)
        ttk.Label(nivel, text="Nivel de humo", style="Body.TLabel").grid(row=0, column=0,
                                                                        sticky="w")
        ttk.Label(nivel, textvariable=self._nivel_humo, style="Term.TLabel", width=3,
                  anchor="e").grid(row=0, column=2, sticky="e")
        ttk.Scale(nivel, from_=UMBRAL_HUMO, to=COSTO_MAX, variable=self._nivel_humo,
                  command=lambda v: self._nivel_humo.set(round(float(v)))).grid(
            row=1, column=0, columnspan=3, sticky="ew", pady=(4, 0))
        poner(nivel, pady=(8, 0))
        tamano = ttk.Frame(panel, style="Card.TFrame")
        ttk.Label(tamano, text="Personas por grupo", style="Body.TLabel").pack(side="left")
        ttk.Spinbox(tamano, from_=1, to=TAMANO_GRUPO_MAX, width=4,
                    textvariable=self._tamano_grupo).pack(side="right")
        poner(tamano, pady=(8, 0))
        poner(ttk.Separator(panel), pady=16)

        # Grupos
        poner(ttk.Label(panel, text="Grupos de personas", style="Subsection.TLabel"),
              sticky="w", pady=(0, 2))
        poner(ttk.Label(panel, textvariable=self._conteo, style="Body.TLabel"),
              sticky="w", pady=(0, 8))
        azar = ttk.Frame(panel, style="Card.TFrame")
        azar.columnconfigure(0, weight=1)
        ttk.Button(azar, text="Generar al azar", style="Secondary.TButton", cursor="hand2",
                   command=self.generar_grupos_azar).grid(row=0, column=0, sticky="ew")
        ttk.Spinbox(azar, from_=1, to=200, width=4, textvariable=self._n_azar).grid(
            row=0, column=1, padx=(8, 0))
        poner(azar)
        boton("Abrir grupos CSV…", self.abrir_grupos, pady=(8, 0))
        boton("Guardar grupos como CSV…", self.guardar_grupos, pady=(8, 0))
        boton("Quitar todos los grupos", self.quitar_grupos, pady=(8, 0))
        poner(ttk.Separator(panel), pady=16)

        # Salidas
        poner(ttk.Label(panel, text="Salidas de emergencia", style="Subsection.TLabel"),
              sticky="w", pady=(0, 2))
        poner(ttk.Label(panel, text="Herramienta «Salida de emergencia», o al azar: el "
                                    "botón también sortea k y la distancia mínima y los "
                                    "pone en los parámetros. Solo en celdas libres.",
                        style="Hint.TLabel", wraplength=300, justify="left"),
              sticky="w", pady=(0, 8))
        boton("Generar salidas al azar", self.generar_salidas_azar)
        boton("Quitar todas las salidas", self.quitar_salidas, pady=(8, 0))
        poner(ttk.Separator(panel), pady=16)

        # Parámetros del AG
        poner(ttk.Label(panel, text="Parámetros del algoritmo", style="Subsection.TLabel"),
              sticky="w", pady=(0, 6))
        parametros = ttk.Frame(panel, style="Card.TFrame")
        parametros.columnconfigure(0, weight=1)
        campos = (
            ("Salidas (k)", self._k, list(map(str, K_PERMITIDOS))),
            ("Distancia mínima entre salidas", self._d_min, None),
            ("Tamaño de la población", self._poblacion, None),
            ("Generaciones", self._generaciones, None),
            ("Fracción evacuada para T_p", self._p_evac, None),
            ("Ventana de aglomeración (s)", self._ventana, None),
            ("Semilla (vacía = al azar)", self._semilla, None),
        )
        for i, (texto, variable, opciones) in enumerate(campos):
            ttk.Label(parametros, text=texto, style="Body.TLabel").grid(
                row=i, column=0, sticky="w", pady=2)
            if opciones:
                campo = ttk.Combobox(parametros, values=opciones, textvariable=variable,
                                     width=6, state="readonly")
            else:
                campo = ttk.Entry(parametros, textvariable=variable, width=8)
            campo.grid(row=i, column=1, sticky="e", padx=(12, 0), pady=2)
        poner(parametros)
        poner(ttk.Separator(panel), pady=16)

        # Acciones
        boton("Ejecutar algoritmo genético (F5)", self.calcular_ruta, primario=True)
        boton("Guardar escenario como CSV… (Ctrl+S)", self.guardar, pady=(8, 0))
        boton("Abrir escenario CSV…", self.abrir, pady=(8, 0))
        poner(ttk.Separator(panel), pady=16)
        boton("Volver al inicio", self._al_volver)

    # -- Grupos ------------------------------------------------------------

    def _semilla_o_none(self) -> Optional[int]:
        texto = self._semilla.get().strip()
        if not texto:
            return None
        try:
            return int(texto)
        except ValueError:
            raise ValueError("La semilla debe ser un número entero o quedar vacía") from None

    def generar_grupos_azar(self) -> None:
        """Coloca grupos al azar (tamaño 1 a 8) en celdas transitables."""
        try:
            esc = self._diseno.a_escenario()
            semilla = self._semilla_o_none()
            grupos = generar_grupos(esc, int(self._n_azar.get()), 8,
                                    semilla if semilla is not None else random.randrange(10**6))
        except (ValueError, tk.TclError) as exc:
            messagebox.showerror("No se pudieron generar los grupos", str(exc),
                                 parent=self.winfo_toplevel())
            return
        self._diseno.poner_grupos(grupos)
        self._dibujar()
        self._estado.set(f"{len(grupos)} grupos generados al azar.")

    def abrir_grupos(self) -> None:
        """Carga un CSV de grupos sobre el escenario actual."""
        ruta = filedialog.askopenfilename(parent=self.winfo_toplevel(),
                                          title="Abrir grupos CSV",
                                          filetypes=TIPOS_CSV + [("Todos los archivos", "*.*")])
        if not ruta:
            return
        try:
            self._diseno.poner_grupos(cargar_grupos(ruta))
        except (ValueError, OSError) as exc:
            messagebox.showerror("Error al abrir los grupos",
                                 f"No fue posible usar «{os.path.basename(ruta)}».\n\n"
                                 f"Detalle técnico: {exc}", parent=self.winfo_toplevel())
            return
        self._ruta_grupos = ruta
        self._dibujar()
        self._estado.set(f"Grupos cargados desde «{ruta}».")

    def guardar_grupos(self) -> None:
        """Guarda los grupos actuales como CSV (fila,columna,tamano)."""
        if not self._diseno.grupos:
            messagebox.showinfo("Guardar grupos", "Todavía no hay grupos en el escenario.",
                                parent=self.winfo_toplevel())
            return
        nombre = os.path.basename(self._ruta_grupos) if self._ruta_grupos else "grupos.csv"
        ruta = filedialog.asksaveasfilename(parent=self.winfo_toplevel(),
                                            title="Guardar grupos como CSV",
                                            defaultextension=".csv", filetypes=TIPOS_CSV,
                                            initialfile=nombre)
        if not ruta:
            return
        try:
            guardar_grupos(ruta, self._diseno.lista_grupos())
        except OSError as exc:
            messagebox.showerror("Error al guardar", f"Detalle técnico: {exc}",
                                 parent=self.winfo_toplevel())
            return
        self._ruta_grupos = ruta
        self._estado.set(f"Grupos guardados en «{ruta}».")

    def restaurar_cuadricula(self) -> None:
        """Deja todas las celdas libres y quita los grupos."""
        if not messagebox.askokcancel(
                "Restaurar cuadrícula",
                "Se eliminarán todas las paredes, zonas de humo y grupos de personas.\n\n"
                "¿Desea continuar?", parent=self.winfo_toplevel()):
            return
        self._diseno.restaurar()
        self._dibujar()
        self._estado.set("Cuadrícula restaurada: sin paredes, humo ni grupos.")

    def generar_salidas_azar(self) -> None:
        """Sortea k y la distancia mínima, los pone en el panel y coloca las salidas.

        Cada clic da un resultado distinto (no usa la semilla del panel, que es la
        del AG).
        """
        try:
            k, d_min = self._diseno.generar_salidas_aleatorias(random.randrange(10**9))
        except ValueError as exc:
            messagebox.showerror("No se pudieron generar las salidas", str(exc),
                                 parent=self.winfo_toplevel())
            return
        self._k.set(str(k))
        self._d_min.set(str(d_min))
        self._dibujar()
        self._estado.set(f"Al azar: k = {k}, distancia mínima = {d_min}. Salidas: "
                         + " ".join(f"({f}, {c})" for f, c in self._diseno.salidas))

    def quitar_salidas(self) -> None:
        self._diseno.salidas = []
        self._dibujar()
        self._estado.set("Se quitaron todas las salidas.")

    def quitar_grupos(self) -> None:
        self._diseno.grupos = {}
        self._dibujar()
        self._estado.set("Se quitaron todos los grupos.")

    # -- Ejecución del AG --------------------------------------------------

    def _leer_parametros(self) -> ParametrosAG:
        """Convierte los campos del panel en ``ParametrosAG`` (ValueError si no son válidos)."""
        def numero(variable: tk.StringVar, tipo, nombre: str):
            try:
                return tipo(variable.get().strip())
            except ValueError:
                raise ValueError(f"«{nombre}» debe ser un número") from None

        return ParametrosAG(
            k=numero(self._k, int, "Salidas (k)"),
            d_min=numero(self._d_min, int, "Distancia mínima"),
            tam_poblacion=numero(self._poblacion, int, "Tamaño de la población"),
            generaciones=numero(self._generaciones, int, "Generaciones"),
            p_evac=numero(self._p_evac, float, "Fracción evacuada"),
            ventana=numero(self._ventana, int, "Ventana de aglomeración"),
            semilla=self._semilla_o_none())

    def calcular_ruta(self) -> None:
        """Ejecuta el AG con el escenario, los grupos y los parámetros del panel."""
        esc = self._construir_escenario()
        if esc is None:
            return
        grupos = self._diseno.lista_grupos()
        if not grupos:
            messagebox.showwarning("Faltan grupos",
                                   "Coloque al menos un grupo de personas con la herramienta "
                                   "«Grupo de personas», ábralos de un CSV o genérelos al azar.",
                                   parent=self.winfo_toplevel())
            return
        ventana = self.winfo_toplevel()
        try:
            params = self._leer_parametros()
            self._estado.set(f"Ejecutando el algoritmo genético ({params.generaciones} "
                             "generaciones)…")
            ventana.config(cursor="watch")
            ventana.update_idletasks()
            resultado = optimizar(esc, grupos, params)
        except ValueError as exc:
            messagebox.showerror("No se pudo ejecutar el algoritmo", str(exc), parent=ventana)
            self._estado.set("El algoritmo genético no se ejecutó.")
            return
        finally:
            ventana.config(cursor="")
        self._estado.set(f"AG terminado: aptitud {resultado.mejor.aptitud:.4f} con "
                         f"{resultado.evaluaciones} evaluaciones.")
        self._al_calcular(esc, grupos, params, resultado, self._evaluar_salidas(esc, grupos,
                                                                              params))

    def _evaluar_salidas(self, esc: Escenario, grupos: list[Grupo],
                         params: ParametrosAG) -> Optional[Configuracion]:
        """Evalúa las salidas del editor con la misma aptitud que usa el AG."""
        if not self._diseno.salidas:
            return None
        return evaluar(crear_problema(esc, grupos, params), tuple(self._diseno.salidas))
