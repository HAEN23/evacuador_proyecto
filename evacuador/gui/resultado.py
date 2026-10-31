"""Vista de resultados del Sistema de Evacuación Táctica.

Muestra, dentro de la ventana principal, el mapa de riesgo del escenario con
la ruta calculada por UCS y las métricas de la búsqueda. La gráfica se
integra en ``tkinter`` mediante el backend ``TkAgg`` de ``matplotlib``.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import font as tkfont
from tkinter import messagebox, ttk
from typing import Callable, Optional

from ..modelos import Escenario, Resultado
from ..visualizacion import dibujar_mapa, nueva_figura
from .tema import COLORES


class VistaResultado(ttk.Frame):
    """Panel de métricas y mapa de riesgo con la ruta de evacuación.

    Args:
        padre: Contenedor de la vista.
        escenario: Escenario resuelto.
        resultado: Resultado devuelto por la búsqueda UCS.
        nombre: Nombre del escenario (archivo o "Escenario del editor").
        al_volver: Acción del botón "Volver al inicio".
        al_editar: Acción del botón de edición.
        texto_editar: Texto del botón de edición.
    """

    def __init__(self, padre: tk.Misc, escenario: Escenario, resultado: Resultado,
                 nombre: str, al_volver: Callable[[], None],
                 al_editar: Callable[[], None], texto_editar: str) -> None:
        super().__init__(padre, style="App.TFrame")
        self._escenario = escenario
        self._resultado = resultado
        self._lienzo_mpl: Optional[object] = None

        self.columnconfigure(1, weight=1)
        self.rowconfigure(1, weight=1)
        if not resultado.encontrada:
            self._crear_alerta_critica()
            self.after_idle(self._notificar_situacion_critica)
        self._crear_panel_metricas(nombre, al_volver, al_editar, texto_editar)
        self._crear_grafica()

    # -- Situación crítica -------------------------------------------------

    def _crear_alerta_critica(self) -> None:
        """Banda de alerta visible cuando no existe ruta hacia ninguna salida."""
        familia = tkfont.Font(font=ttk.Style(self).lookup("Body.TLabel", "font")).actual("family")
        alerta = tk.Frame(self, bg=COLORES["error"])
        alerta.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 16))
        tk.Label(alerta, text="⚠  SITUACIÓN CRÍTICA: NO EXISTE RUTA DE EVACUACIÓN",
                 bg=COLORES["error"], fg=COLORES["texto_invertido"],
                 font=(familia, 13, "bold"), anchor="w").pack(
            fill="x", padx=20, pady=(12, 2))
        tk.Label(alerta,
                 text="El agente está aislado: todas las salidas están bloqueadas por "
                      "paredes o fuego letal. Se requiere rescate externo o despejar un "
                      "acceso antes de intentar la evacuación.",
                 bg=COLORES["error"], fg="#FBE3E1", font=(familia, 10),
                 anchor="w", justify="left", wraplength=1100).pack(
            fill="x", padx=20, pady=(0, 12))

    def _notificar_situacion_critica(self) -> None:
        """Muestra el aviso de situación crítica una vez que la vista es visible."""
        exp = self._resultado.nodos_expandidos
        messagebox.showerror(
            "Situación crítica",
            "No existe ninguna ruta transitable desde el punto de inicio hasta una "
            "salida de emergencia.\n\n"
            f"La búsqueda UCS exploró {exp} celda(s) alcanzable(s) sin encontrar salida.\n\n"
            "Recomendación: solicitar rescate externo o despejar un acceso en el "
            "escenario y volver a calcular.",
            parent=self.winfo_toplevel())

    # -- Construcción ------------------------------------------------------

    def _crear_panel_metricas(self, nombre: str, al_volver: Callable[[], None],
                              al_editar: Callable[[], None], texto_editar: str) -> None:
        """Panel lateral con el resumen de la búsqueda y la navegación."""
        marco = tk.Frame(self, bg=COLORES["borde"])
        marco.grid(row=1, column=0, sticky="ns", padx=(0, 12))
        panel = ttk.Frame(marco, style="Card.TFrame", padding=(24, 20))
        panel.pack(fill="both", expand=True, padx=1, pady=1)
        panel.columnconfigure(1, weight=1)

        res, esc = self._resultado, self._escenario
        ttk.Label(panel, text="RESULTADO", style="CardEyebrow.TLabel").grid(
            row=0, column=0, columnspan=2, sticky="w")
        ttk.Label(panel, text="Ruta de evacuación", style="SectionTitle.TLabel").grid(
            row=1, column=0, columnspan=2, sticky="w", pady=(4, 2))
        ttk.Label(panel, text=nombre, style="Body.TLabel", wraplength=260).grid(
            row=2, column=0, columnspan=2, sticky="w", pady=(0, 14))

        estilo_estado = "Exito.Result.TLabel" if res.encontrada else "Error.Result.TLabel"
        texto_estado = "Ruta encontrada" if res.encontrada else "Situación crítica: sin ruta"
        ttk.Label(panel, text=texto_estado, style=estilo_estado).grid(
            row=3, column=0, columnspan=2, sticky="w", pady=(0, 10))

        metricas = (
            ("Costo acumulado", str(res.costo) if res.encontrada else "—"),
            ("Pasos", str(res.pasos) if res.encontrada else "—"),
            ("Nodos expandidos", str(res.nodos_expandidos)),
            ("Celdas con humo", str(res.celdas_humo)),
            ("Tiempo de búsqueda", f"{res.tiempo_ms:.2f} ms"),
            ("Dimensiones", f"{esc.filas} × {esc.columnas}"),
            ("Inicio", f"({esc.inicio[0]}, {esc.inicio[1]})"),
            ("Salida", ", ".join(f"({r}, {c})" for r, c in esc.metas)),
        )
        for i, (termino, valor) in enumerate(metricas, start=4):
            ttk.Label(panel, text=termino, style="Term.TLabel").grid(
                row=i, column=0, sticky="w", pady=3)
            ttk.Label(panel, text=valor, style="Body.TLabel").grid(
                row=i, column=1, sticky="e", padx=(16, 0), pady=3)

        ttk.Separator(panel).grid(row=20, column=0, columnspan=2, sticky="ew", pady=16)
        ttk.Button(panel, text=texto_editar, style="Primary.TButton", cursor="hand2",
                   command=al_editar).grid(row=21, column=0, columnspan=2, sticky="ew")
        ttk.Button(panel, text="Volver al inicio", style="Secondary.TButton",
                   cursor="hand2", command=al_volver).grid(
            row=22, column=0, columnspan=2, sticky="ew", pady=(8, 0))

    def _crear_grafica(self) -> None:
        """Integra el mapa de riesgo de ``matplotlib`` en la vista."""
        marco = tk.Frame(self, bg=COLORES["borde"])
        marco.grid(row=1, column=1, sticky="nsew", padx=(12, 0))
        interior = tk.Frame(marco, bg=COLORES["superficie"])
        interior.pack(fill="both", expand=True, padx=1, pady=1)

        try:
            from matplotlib.backends.backend_tkagg import (FigureCanvasTkAgg,
                                                           NavigationToolbar2Tk)
        except ImportError:
            ttk.Label(interior, text="Para visualizar la gráfica instale matplotlib y numpy:\n"
                                     "pip install matplotlib numpy",
                      style="Body.TLabel", justify="center").pack(expand=True)
            return

        figura = nueva_figura(COLORES["superficie"])
        dibujar_mapa(figura, figura.add_subplot(111), self._escenario, self._resultado)

        lienzo = FigureCanvasTkAgg(figura, master=interior)
        barra = NavigationToolbar2Tk(lienzo, interior, pack_toolbar=False)
        barra.configure(background=COLORES["superficie"])
        for hijo in barra.winfo_children():
            try:
                hijo.configure(background=COLORES["superficie"])
            except tk.TclError:
                pass
        barra.update()
        barra.pack(side="top", fill="x", padx=12, pady=(8, 0))
        lienzo.get_tk_widget().pack(side="top", fill="both", expand=True, padx=12, pady=12)
        lienzo.draw()
        self._lienzo_mpl = lienzo
