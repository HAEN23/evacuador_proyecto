"""Vista de resultados del algoritmo genético (EvacuAG).

Panel lateral con la mejor configuración y sus objetivos, y pestañas con las
salidas que pide la propuesta:

* las tres mejores configuraciones dibujadas sobre el mapa de riesgo;
* la evolución de la aptitud (mejor, promedio y peor por generación);
* la curva de personas evacuadas contra tiempo;
* la tabla comparativa del top 3 y la tabla del mejor individuo por generación.

Las gráficas usan las funciones de ``visualizacion_ag`` (las mismas que guarda el
CLI) y se integran con el backend ``TkAgg`` de matplotlib.
"""

from __future__ import annotations

import csv
import io
import os
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Callable, Optional

from .. import experimentos_ag as exp_ag
from ..genetico import Configuracion, Grupo, ParametrosAG, ResultadoAG
from ..modelos import Escenario
from .tema import COLORES


class VistaResultadoAG(ttk.Frame):
    """Resultados del AG: métricas, gráficas, tablas y exportación.

    Args:
        padre: Contenedor de la vista.
        escenario: Escenario optimizado.
        grupos: Grupos de personas usados.
        params: Parámetros con los que se ejecutó el AG.
        resultado: Resultado de ``optimizar``.
        al_volver: Acción del botón "Volver al inicio".
        al_editar: Acción del botón "Volver al editor".
        al_guardar: Acción del botón «Guardar escenario como CSV…».
        al_guardar_grupos: Acción del botón «Guardar grupos como CSV…».
        manual: Evaluación de las salidas colocadas en el editor, para compararlas
            con las del AG. None si no se colocaron.
    """

    def __init__(self, padre: tk.Misc, escenario: Escenario, grupos: list[Grupo],
                 params: ParametrosAG, resultado: ResultadoAG, al_volver: Callable[[], None],
                 al_editar: Callable[[], None], al_guardar: Callable[[], None],
                 al_guardar_grupos: Callable[[], None],
                 manual: Optional[Configuracion] = None) -> None:
        super().__init__(padre, style="App.TFrame")
        self._escenario = escenario
        self._grupos = grupos
        self._params = params
        self._resultado = resultado
        self._manual = manual
        self._al_guardar = al_guardar
        self._lienzos: list[object] = []   # referencias a los lienzos de matplotlib

        self.columnconfigure(1, weight=1)
        self.rowconfigure(1, weight=1)
        if resultado.mejor.o1 == 0:
            self._crear_alerta()
        self._crear_panel(al_volver, al_editar, al_guardar, al_guardar_grupos)
        self._crear_pestanas()

    def guardar(self) -> None:
        """Atajo Ctrl+S: guarda el escenario."""
        self._al_guardar()

    # -- Construcción ------------------------------------------------------

    def _crear_alerta(self) -> None:
        alerta = tk.Frame(self, bg=COLORES["error"])
        alerta.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 16))
        tk.Label(alerta, text="⚠  NINGÚN GRUPO ALCANZA UNA SALIDA",
                 bg=COLORES["error"], fg=COLORES["texto_invertido"],
                 font=("TkDefaultFont", 13, "bold"), anchor="w").pack(fill="x", padx=20,
                                                                     pady=12)

    def _crear_panel(self, al_volver, al_editar, al_guardar, al_guardar_grupos) -> None:
        """Panel lateral con la mejor configuración y las acciones."""
        panel = self._panel_desplazable()
        panel.columnconfigure(1, weight=1)

        r, m, p = self._resultado, self._resultado.mejor, self._params
        ttk.Label(panel, text="RESULTADO DEL AG", style="CardEyebrow.TLabel").grid(
            row=0, column=0, columnspan=2, sticky="w")
        ttk.Label(panel, text="Mejor configuración", style="SectionTitle.TLabel").grid(
            row=1, column=0, columnspan=2, sticky="w", pady=(4, 2))
        ttk.Label(panel, text=" ".join(f"({f}, {c})" for f, c in m.salidas),
                  style="Exito.Result.TLabel" if m.o1 > 0 else "Error.Result.TLabel",
                  wraplength=280).grid(row=2, column=0, columnspan=2, sticky="w",
                                       pady=(0, 12))

        personas = sum(g.tamano for g in self._grupos)
        metricas = (
            ("Aptitud", f"{m.aptitud:.4f}"),
            ("Personas que salen (O1)", f"{100 * m.o1:.1f} % de {personas}"),
            ("Riesgo por persona", f"{m.riesgo_promedio:.2f}  (O2 = {m.o2:.3f})"),
            (f"T{round(100 * p.p_evac)} / T_ref (O3)", f"{m.o3:.3f}"),
            ("Aglomeración (O4)", f"{m.aglomeracion_max} personas  ({m.o4:.3f})"),
            ("T50 · T90 · T100", f"{m.t50} · {m.t90} · {m.t100} s"),
            ("Personas por salida", " · ".join(map(str, m.personas_por_salida))),
            ("Evaluaciones (UCS)", str(r.evaluaciones)),
            ("Generaciones", str(len(r.historial) - 1)),
            ("Grupos", str(len(self._grupos))),
            ("Parámetros", f"k = {p.k}, d_min = {p.d_min}, población {p.tam_poblacion}"),
            ("Semilla", "al azar" if p.semilla is None else str(p.semilla)),
        )
        for i, (termino, valor) in enumerate(metricas, start=3):
            ttk.Label(panel, text=termino, style="Term.TLabel").grid(
                row=i, column=0, sticky="w", pady=3)
            ttk.Label(panel, text=valor, style="Body.TLabel").grid(
                row=i, column=1, sticky="e", padx=(16, 0), pady=3)

        if self._manual is not None:
            c = self._manual
            ttk.Separator(panel).grid(row=20, column=0, columnspan=2, sticky="ew", pady=12)
            ttk.Label(panel, text="Sus salidas (editor)", style="Subsection.TLabel").grid(
                row=21, column=0, columnspan=2, sticky="w")
            ttk.Label(panel, text=" ".join(f"({f}, {col})" for f, col in c.salidas),
                      style="Body.TLabel", wraplength=280).grid(
                row=22, column=0, columnspan=2, sticky="w", pady=(2, 4))
            if m.aptitud > c.aptitud:
                veredicto = f"El AG es {100 * (m.aptitud / c.aptitud - 1):.0f} % mejor" \
                    if c.aptitud > 0 else "El AG es mejor"
            elif m.aptitud < c.aptitud:
                veredicto = "Sus salidas son mejores que las del AG"
            else:
                veredicto = "Empate con el AG"
            # El detalle de estas salidas está en la pestaña «Sus salidas vs. AG».
            for i, (termino, valor) in enumerate((
                    ("Aptitud", f"{c.aptitud:.4f}  ({veredicto})"),), start=23):
                ttk.Label(panel, text=termino, style="Term.TLabel").grid(
                    row=i, column=0, sticky="w", pady=2)
                ttk.Label(panel, text=valor, style="Body.TLabel", wraplength=230).grid(
                    row=i, column=1, sticky="e", padx=(16, 0), pady=2)

        ttk.Separator(panel).grid(row=30, column=0, columnspan=2, sticky="ew", pady=16)
        botones = (
            ("Exportar resultados (CSV y figuras)…", self.exportar, "Primary.TButton"),
            ("Volver al editor", al_editar, "Secondary.TButton"),
            ("Guardar escenario como CSV… (Ctrl+S)", al_guardar, "Secondary.TButton"),
            ("Guardar grupos como CSV…", al_guardar_grupos, "Secondary.TButton"),
            ("Volver al inicio", al_volver, "Secondary.TButton"),
        )
        for i, (texto, accion, estilo) in enumerate(botones, start=31):
            ttk.Button(panel, text=texto, style=estilo, cursor="hand2", command=accion).grid(
                row=i, column=0, columnspan=2, sticky="ew", pady=(0 if i == 31 else 8, 0))

    def _panel_desplazable(self) -> ttk.Frame:
        """Panel lateral con barra vertical, para que no se corte en pantallas bajas."""
        marco = tk.Frame(self, bg=COLORES["borde"])
        marco.grid(row=1, column=0, sticky="ns", padx=(0, 12))
        marco.rowconfigure(0, weight=1)
        lienzo = tk.Canvas(marco, bg=COLORES["superficie"], highlightthickness=0, bd=0)
        barra = ttk.Scrollbar(marco, orient="vertical", command=lienzo.yview,
                              style="Panel.Vertical.TScrollbar")
        lienzo.configure(yscrollcommand=barra.set)
        lienzo.grid(row=0, column=0, sticky="ns", padx=(1, 0), pady=1)
        barra.grid(row=0, column=1, sticky="ns", padx=(0, 1), pady=1)
        panel = ttk.Frame(lienzo, style="Card.TFrame", padding=(24, 20))
        lienzo.create_window(0, 0, window=panel, anchor="nw")
        panel.bind("<Configure>", lambda _e: lienzo.configure(
            scrollregion=lienzo.bbox("all"), width=panel.winfo_reqwidth()))

        def desplazar(evento: tk.Event) -> None:
            arriba = evento.num == 4 or getattr(evento, "delta", 0) > 0
            lienzo.yview_scroll(-1 if arriba else 1, "units")

        # La rueda solo mueve el panel mientras el puntero está encima.
        secuencias = ("<MouseWheel>", "<Button-4>", "<Button-5>")
        marco.bind("<Enter>", lambda _e: [self.bind_all(q, desplazar) for q in secuencias])
        marco.bind("<Leave>", lambda _e: [self.unbind_all(q) for q in secuencias])
        return panel

    def _crear_pestanas(self) -> None:
        """Pestañas con las gráficas y las tablas."""
        cuaderno = ttk.Notebook(self, style="AG.TNotebook")
        cuaderno.grid(row=1, column=1, sticky="nsew", padx=(12, 0))
        try:
            from matplotlib.figure import Figure
            from .. import visualizacion_ag as vis
        except ImportError:
            aviso = ttk.Frame(cuaderno, style="Card.TFrame")
            ttk.Label(aviso, text="Para ver las gráficas instale matplotlib y numpy:\n"
                                  "pip install -r requirements.txt",
                      style="Body.TLabel", justify="center").pack(expand=True)
            cuaderno.add(aviso, text="Gráficas")
        else:
            r = self._resultado
            graficas = (
                ("Top 3 en el mapa",
                 lambda f: vis.dibujar_top3(f, self._escenario, self._grupos, r)),
                ("Evolución",
                 lambda f: vis.dibujar_evolucion(f, f.add_subplot(111), r)),
                ("Curva de evacuación",
                 lambda f: vis.dibujar_curvas(f, f.add_subplot(111), r)),
            )
            if self._manual is not None:
                graficas += (("Sus salidas vs. AG", self._dibujar_comparacion),)
            for titulo, dibujar in graficas:
                figura = Figure(figsize=(9, 6), dpi=100, facecolor=COLORES["superficie"],
                                layout="constrained")
                dibujar(figura)
                cuaderno.add(self._incrustar(cuaderno, figura), text=titulo)

        cuaderno.add(self._tabla(cuaderno, exp_ag.top3_csv(self._resultado)),
                     text="Tabla top 3")
        cuaderno.add(self._tabla(cuaderno, exp_ag.historial_csv(self._resultado)),
                     text="Por generación")

    def _dibujar_comparacion(self, figura) -> None:
        """La mejor configuración del AG junto a las salidas colocadas en el editor."""
        from .. import visualizacion_ag as vis

        ag, manual = self._resultado.mejor, self._manual
        izquierda, derecha = figura.subplots(1, 2)
        vis.dibujar_configuracion(figura, izquierda, self._escenario, self._grupos, ag,
                                  titulo=f"AG  ·  aptitud {ag.aptitud:.4f}", barra=False)
        vis.dibujar_configuracion(figura, derecha, self._escenario, self._grupos, manual,
                                  titulo=f"Sus salidas  ·  aptitud {manual.aptitud:.4f}")

    def _incrustar(self, padre: tk.Misc, figura) -> tk.Frame:
        """Integra una figura de matplotlib con su barra de navegación."""
        from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk

        marco = tk.Frame(padre, bg=COLORES["superficie"])
        lienzo = FigureCanvasTkAgg(figura, master=marco)
        barra = NavigationToolbar2Tk(lienzo, marco, pack_toolbar=False)
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
        self._lienzos.append(lienzo)
        return marco

    @staticmethod
    def _tabla(padre: tk.Misc, texto_csv: str) -> ttk.Frame:
        """Muestra un CSV (encabezado + filas) en un ``Treeview`` desplazable."""
        filas = list(csv.reader(io.StringIO(texto_csv)))
        encabezado, datos = filas[0], filas[1:]
        marco = ttk.Frame(padre, style="Card.TFrame", padding=12)
        marco.columnconfigure(0, weight=1)
        marco.rowconfigure(0, weight=1)
        arbol = ttk.Treeview(marco, columns=encabezado, show="headings", style="AG.Treeview")
        for col in encabezado:
            ancho = max(90, 9 * len(col) + 16, *(8 * len(f[encabezado.index(col)]) for f in datos))
            arbol.heading(col, text=col)
            arbol.column(col, width=min(ancho, 260), anchor="center", stretch=False)
        for fila in datos:
            arbol.insert("", "end", values=fila)
        barra_v = ttk.Scrollbar(marco, orient="vertical", command=arbol.yview,
                                style="Panel.Vertical.TScrollbar")
        barra_h = ttk.Scrollbar(marco, orient="horizontal", command=arbol.xview,
                                style="Panel.Horizontal.TScrollbar")
        arbol.configure(yscrollcommand=barra_v.set, xscrollcommand=barra_h.set)
        arbol.grid(row=0, column=0, sticky="nsew")
        barra_v.grid(row=0, column=1, sticky="ns")
        barra_h.grid(row=1, column=0, sticky="ew")
        return marco

    # -- Exportación -------------------------------------------------------

    def exportar(self) -> None:
        """Guarda historial.csv, top3.csv y las tres figuras en una carpeta."""
        ventana = self.winfo_toplevel()
        carpeta = filedialog.askdirectory(parent=ventana,
                                          title="Carpeta donde guardar los resultados")
        if not carpeta:
            return
        destino = Path(carpeta)
        try:
            (destino / "historial.csv").write_text(
                exp_ag.historial_csv(self._resultado) + "\n", encoding="utf-8")
            (destino / "top3.csv").write_text(exp_ag.top3_csv(self._resultado) + "\n",
                                              encoding="utf-8")
            archivos = ["historial.csv", "top3.csv"]
            try:
                from .. import visualizacion_ag as vis
                archivos += [r.name for r in vis.guardar_figuras(
                    destino, self._escenario, self._grupos, self._resultado)]
            except RuntimeError:
                pass  # sin matplotlib solo se exportan los CSV
        except OSError as exc:
            messagebox.showerror("Error al exportar", f"Detalle técnico: {exc}", parent=ventana)
            return
        messagebox.showinfo("Resultados exportados",
                            f"Se guardaron en «{os.path.normpath(carpeta)}»:\n\n"
                            + "\n".join(archivos), parent=ventana)

