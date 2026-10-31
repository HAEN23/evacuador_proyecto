"""Editor interactivo de escenarios del Sistema de Evacuación Táctica.

Ofrece una cuadrícula sobre la que el usuario pinta los distintos tipos de
celda (bloqueada, libre o con humo), coloca el punto de inicio del agente y
la salida de emergencia. El escenario resultante puede guardarse en CSV
(mediante :func:`io_csv.guardar_csv`) o resolverse directamente con UCS.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import filedialog, messagebox
from tkinter import ttk
from typing import Callable, Final, Optional

from ..config import (COLOR_INICIO, COLOR_SALIDA, COLUMNAS_POR_DEFECTO, COSTO_MAX,
                      DIMENSION_MAX, DIMENSION_MIN, FILAS_POR_DEFECTO,
                      NIVEL_HUMO_DEFECTO, UMBRAL_HUMO)
from ..edicion import DisenoEscenario, DisenoInvalido, Herramienta, limitar_dimension
from ..io_csv import cargar_csv, guardar_csv
from ..modelos import Escenario, Posicion, Resultado
from ..ucs import buscar_ucs
from .tema import COLORES, color_celda


TAMANO_CELDA_MAX: Final[int] = 36
TAMANO_CELDA_MIN: Final[int] = 4
ZOOM_MIN: Final[float] = 0.5
ZOOM_MAX: Final[float] = 6.0
ZOOM_PASO: Final[float] = 1.25

# Herramientas disponibles: (herramienta, etiqueta visible).
HERRAMIENTAS: Final[tuple[tuple[Herramienta, str], ...]] = (
    (Herramienta.BLOQUEADA, "Celda bloqueada (0)"),
    (Herramienta.LIBRE, "Celda libre (1)"),
    (Herramienta.HUMO, "Humo / tóxico (2 – 99)"),
    (Herramienta.INICIO, "Punto de inicio"),
    (Herramienta.SALIDA, "Salida de emergencia"),
    (Herramienta.BORRAR, "Borrar (restaurar celda)"),
)


class EditorEscenarios(ttk.Frame):
    """Vista para diseñar, guardar y resolver escenarios de evacuación.

    Se integra en el área de trabajo de la ventana principal.

    Args:
        padre: Contenedor de la vista.
        estado: Variable de la barra de estado de la ventana principal.
        al_calcular: Se invoca con el escenario y su resultado tras calcular la ruta.
        al_volver: Acción del botón "Volver al inicio".
    """

    def __init__(self, padre: tk.Misc, estado: tk.StringVar,
                 al_calcular: Callable[[Escenario, Resultado], None],
                 al_volver: Callable[[], None]) -> None:
        super().__init__(padre, style="App.TFrame")
        self._al_calcular = al_calcular
        self._al_volver = al_volver

        self._diseno = DisenoEscenario(FILAS_POR_DEFECTO, COLUMNAS_POR_DEFECTO)
        self._filas = tk.IntVar(value=FILAS_POR_DEFECTO)
        self._columnas = tk.IntVar(value=COLUMNAS_POR_DEFECTO)
        self._herramienta = tk.StringVar(value=Herramienta.BLOQUEADA.value)
        self._nivel_humo = tk.IntVar(value=NIVEL_HUMO_DEFECTO)
        self._estado = estado

        self._tamano_celda = TAMANO_CELDA_MAX
        self._margen_x = self._margen_y = 0
        self._zoom = 1.0
        self._texto_zoom = tk.StringVar(value="100 %")
        self._ultima_celda: Optional[Posicion] = None

        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)
        self._crear_panel_herramientas()
        self._crear_lienzo()
        self._dibujar()
        self._registrar_atajos()

    def _registrar_atajos(self) -> None:
        """Atajos de teclado, activos solo mientras el editor está visible."""
        ventana = self.winfo_toplevel()
        atajos = {
            "<Control-s>": self.guardar,
            "<F5>": self.calcular_ruta,
            "<Control-plus>": self.acercar,
            "<Control-equal>": self.acercar,
            "<Control-minus>": self.alejar,
            "<Control-0>": self.ajustar_zoom,
        }
        for secuencia, accion in atajos.items():
            ventana.bind(secuencia, lambda _e, a=accion: a() if self.winfo_ismapped() else None,
                         add="+")

    # -- Construcción de la interfaz ---------------------------------------

    def _crear_contenedor_desplazable(self) -> ttk.Frame:
        """Crea el marco del panel lateral con barra de desplazamiento vertical.

        Returns:
            El marco interior donde se colocan los controles del panel.
        """
        marco = tk.Frame(self, bg=COLORES["borde"])
        marco.grid(row=0, column=0, sticky="ns", padx=(0, 12))
        marco.rowconfigure(0, weight=1)

        lienzo = tk.Canvas(marco, bg=COLORES["superficie"], highlightthickness=0, bd=0)
        barra = ttk.Scrollbar(marco, orient="vertical", command=lienzo.yview,
                              style="Panel.Vertical.TScrollbar")
        lienzo.configure(yscrollcommand=barra.set)
        lienzo.grid(row=0, column=0, sticky="ns", padx=(1, 0), pady=1)
        barra.grid(row=0, column=1, sticky="ns", padx=(0, 1), pady=1)

        panel = ttk.Frame(lienzo, style="Card.TFrame", padding=(24, 20))
        panel.columnconfigure(0, weight=1)
        lienzo.create_window(0, 0, window=panel, anchor="nw")

        def ajustar(_evento: tk.Event) -> None:
            lienzo.configure(scrollregion=lienzo.bbox("all"),
                             width=panel.winfo_reqwidth())

        def desplazar(evento: tk.Event) -> None:
            if evento.num == 4:
                pasos = -1
            elif evento.num == 5:
                pasos = 1
            else:
                pasos = -1 if evento.delta > 0 else 1
            lienzo.yview_scroll(pasos, "units")

        def activar_rueda(_evento: tk.Event) -> None:
            for secuencia in ("<MouseWheel>", "<Button-4>", "<Button-5>"):
                self.bind_all(secuencia, desplazar)

        def desactivar_rueda(_evento: tk.Event) -> None:
            for secuencia in ("<MouseWheel>", "<Button-4>", "<Button-5>"):
                self.unbind_all(secuencia)

        panel.bind("<Configure>", ajustar)
        marco.bind("<Enter>", activar_rueda)
        marco.bind("<Leave>", desactivar_rueda)
        return panel

    def _crear_panel_herramientas(self) -> None:
        """Panel lateral con dimensiones, herramientas y acciones."""
        panel = self._crear_contenedor_desplazable()

        ttk.Label(panel, text="EDITOR", style="CardEyebrow.TLabel").grid(
            row=0, column=0, sticky="w")
        ttk.Label(panel, text="Diseñar escenario", style="SectionTitle.TLabel").grid(
            row=1, column=0, sticky="w", pady=(4, 14))

        # Dimensiones
        ttk.Label(panel, text="Dimensiones", style="Subsection.TLabel").grid(
            row=2, column=0, sticky="w", pady=(0, 6))
        dimensiones = ttk.Frame(panel, style="Card.TFrame")
        dimensiones.grid(row=3, column=0, sticky="ew")
        for col, (texto, variable) in enumerate((("Filas", self._filas),
                                                 ("Columnas", self._columnas))):
            ttk.Label(dimensiones, text=texto, style="Body.TLabel").grid(
                row=0, column=col * 2, sticky="w", padx=(0 if col == 0 else 12, 6))
            ttk.Spinbox(dimensiones, from_=DIMENSION_MIN, to=DIMENSION_MAX, width=4,
                        textvariable=variable).grid(row=0, column=col * 2 + 1)
        botones = ttk.Frame(panel, style="Card.TFrame")
        botones.grid(row=4, column=0, sticky="ew", pady=(10, 0))
        botones.columnconfigure(0, weight=1)
        ttk.Button(botones, text="Generar cuadrícula", style="Secondary.TButton",
                   cursor="hand2", command=self._confirmar_nueva_cuadricula).grid(
            row=0, column=0, sticky="ew")
        ttk.Button(botones, text="Restaurar cuadrícula", style="Secondary.TButton",
                   cursor="hand2", command=self.restaurar_cuadricula).grid(
            row=1, column=0, sticky="ew", pady=(8, 0))

        ttk.Separator(panel).grid(row=5, column=0, sticky="ew", pady=16)

        # Herramientas
        ttk.Label(panel, text="Herramienta", style="Subsection.TLabel").grid(
            row=6, column=0, sticky="w", pady=(0, 6))
        # Filas 7 a 12: una por herramienta.
        for i, (clave, etiqueta) in enumerate(HERRAMIENTAS, start=7):
            ttk.Radiobutton(panel, text=etiqueta, value=clave.value, variable=self._herramienta,
                            style="Tool.TRadiobutton").grid(row=i, column=0, sticky="w", pady=1)

        nivel = ttk.Frame(panel, style="Card.TFrame")
        nivel.grid(row=13, column=0, sticky="ew", pady=(8, 0))
        nivel.columnconfigure(1, weight=1)
        ttk.Label(nivel, text="Nivel de humo", style="Body.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(nivel, textvariable=self._nivel_humo, style="Term.TLabel", width=3,
                  anchor="e").grid(row=0, column=2, sticky="e")
        ttk.Scale(nivel, from_=UMBRAL_HUMO, to=COSTO_MAX, variable=self._nivel_humo,
                  command=lambda v: self._nivel_humo.set(round(float(v)))).grid(
            row=1, column=0, columnspan=3, sticky="ew", pady=(4, 0))

        ttk.Separator(panel).grid(row=14, column=0, sticky="ew", pady=16)

        # Acciones
        ttk.Button(panel, text="Calcular ruta (F5)", style="Primary.TButton", cursor="hand2",
                   command=self.calcular_ruta).grid(row=15, column=0, sticky="ew")
        ttk.Button(panel, text="Guardar CSV… (Ctrl+S)", style="Secondary.TButton",
                   cursor="hand2", command=self.guardar).grid(row=16, column=0, sticky="ew",
                                                              pady=(8, 0))
        ttk.Button(panel, text="Abrir CSV para editar…", style="Secondary.TButton",
                   cursor="hand2", command=self.abrir).grid(row=17, column=0, sticky="ew",
                                                            pady=(8, 0))
        ttk.Separator(panel).grid(row=18, column=0, sticky="ew", pady=16)
        ttk.Button(panel, text="Volver al inicio", style="Secondary.TButton",
                   cursor="hand2", command=self._al_volver).grid(row=19, column=0, sticky="ew")

    def _crear_lienzo(self) -> None:
        """Área de dibujo de la cuadrícula con controles de zoom y desplazamiento."""
        marco = tk.Frame(self, bg=COLORES["borde"])
        marco.grid(row=0, column=1, sticky="nsew", padx=(12, 0))
        interior = tk.Frame(marco, bg=COLORES["superficie"])
        interior.pack(fill="both", expand=True, padx=1, pady=1)
        interior.columnconfigure(0, weight=1)
        interior.rowconfigure(1, weight=1)

        # Barra de zoom
        barra_zoom = ttk.Frame(interior, style="Card.TFrame", padding=(16, 10, 16, 0))
        barra_zoom.grid(row=0, column=0, columnspan=2, sticky="ew")
        ttk.Label(barra_zoom, text="Zoom", style="Subsection.TLabel").pack(side="left")
        for signo, accion, ayuda in (("-", self.alejar, "Alejar (Ctrl + -)"),
                                     ("+", self.acercar, "Acercar (Ctrl + +)")):
            self._boton_lupa(barra_zoom, signo, accion, ayuda).pack(side="left", padx=(8, 0))
        ttk.Label(barra_zoom, textvariable=self._texto_zoom, style="Term.TLabel",
                  width=6, anchor="center").pack(side="left", padx=(8, 0))
        ttk.Button(barra_zoom, text="Ajustar a la ventana", style="Secondary.TButton",
                   cursor="hand2", padding=(10, 4),
                   command=self.ajustar_zoom).pack(side="left", padx=(8, 0))
        ttk.Label(barra_zoom, text="Ctrl + rueda del ratón para acercar o alejar",
                  style="Hint.TLabel").pack(side="right")

        self._lienzo = tk.Canvas(interior, bg=COLORES["superficie"], highlightthickness=0,
                                 cursor="crosshair")
        barra_v = ttk.Scrollbar(interior, orient="vertical", command=self._lienzo.yview,
                                style="Panel.Vertical.TScrollbar")
        barra_h = ttk.Scrollbar(interior, orient="horizontal", command=self._lienzo.xview,
                                style="Panel.Horizontal.TScrollbar")
        self._lienzo.configure(yscrollcommand=barra_v.set, xscrollcommand=barra_h.set)
        self._lienzo.grid(row=1, column=0, sticky="nsew")
        barra_v.grid(row=1, column=1, sticky="ns")
        barra_h.grid(row=2, column=0, sticky="ew")

        self._lienzo.bind("<Configure>", lambda _e: self._dibujar())
        self._lienzo.bind("<Button-1>", self._al_pintar)
        self._lienzo.bind("<B1-Motion>", self._al_pintar)
        self._lienzo.bind("<ButtonRelease-1>", lambda _e: setattr(self, "_ultima_celda", None))
        self._lienzo.bind("<Motion>", self._al_mover)
        self._lienzo.bind("<Enter>", lambda _e: self._activar_rueda_lienzo(True))
        self._lienzo.bind("<Leave>", lambda _e: self._activar_rueda_lienzo(False))

    def _boton_lupa(self, padre: tk.Misc, signo: str, accion, ayuda: str) -> tk.Canvas:
        """Dibuja un botón con icono de lupa y signo ``+`` o ``-``.

        Args:
            padre: Contenedor del botón.
            signo: ``"+"`` para acercar o ``"-"`` para alejar.
            accion: Función que se ejecuta al hacer clic.
            ayuda: Texto que se muestra en la barra de estado al pasar el puntero.
        """
        t = 32
        boton = tk.Canvas(padre, width=t, height=t, bg=COLORES["secundario"],
                          highlightthickness=1, highlightbackground=COLORES["borde"],
                          bd=0, cursor="hand2")
        color = COLORES["primario"]
        boton.create_oval(6, 6, 21, 21, outline=color, width=2)
        boton.create_line(19, 19, 26, 26, fill=color, width=3, capstyle="round")
        boton.create_line(10, 13.5, 17, 13.5, fill=color, width=2)
        if signo == "+":
            boton.create_line(13.5, 10, 13.5, 17, fill=color, width=2)

        boton.bind("<Button-1>", lambda _e: accion())
        boton.bind("<Enter>", lambda _e: (boton.configure(bg=COLORES["secundario_hover"]),
                                          self._estado.set(ayuda)))
        boton.bind("<Leave>", lambda _e: boton.configure(bg=COLORES["secundario"]))
        return boton

    def _activar_rueda_lienzo(self, activar: bool) -> None:
        """Asocia la rueda del ratón al lienzo mientras el puntero está encima."""
        secuencias = ("<MouseWheel>", "<Shift-MouseWheel>", "<Control-MouseWheel>",
                      "<Button-4>", "<Button-5>", "<Shift-Button-4>", "<Shift-Button-5>",
                      "<Control-Button-4>", "<Control-Button-5>")
        for secuencia in secuencias:
            if activar:
                self.bind_all(secuencia, self._al_girar_rueda)
            else:
                self.unbind_all(secuencia)

    def _al_girar_rueda(self, evento: tk.Event) -> None:
        """Rueda: desplaza. Mayús + rueda: desplaza en horizontal. Ctrl + rueda: zoom."""
        arriba = evento.num == 4 or getattr(evento, "delta", 0) > 0
        if evento.state & 0x0004:  # Ctrl
            if arriba:
                self.acercar()
            else:
                self.alejar()
        elif evento.state & 0x0001:  # Mayús
            self._lienzo.xview_scroll(-1 if arriba else 1, "units")
        else:
            self._lienzo.yview_scroll(-1 if arriba else 1, "units")

    # -- Modelo de la cuadrícula -------------------------------------------

    def _confirmar_nueva_cuadricula(self) -> None:
        if messagebox.askokcancel("Generar cuadrícula",
                                  "Se descartará el escenario actual. ¿Desea continuar?",
                                  parent=self.winfo_toplevel()):
            self._nueva_cuadricula()

    def restaurar_cuadricula(self) -> None:
        """Devuelve todas las celdas a libres, conservando el inicio y la salida."""
        if not messagebox.askokcancel(
                "Restaurar cuadrícula",
                "Se eliminarán todas las paredes, zonas de humo y celdas marcadas. "
                "El punto de inicio y la salida se conservan.\n\n¿Desea continuar?",
                parent=self.winfo_toplevel()):
            return
        self._diseno.restaurar()
        self._dibujar()
        self._estado.set("Cuadrícula restaurada.")

    def _nueva_cuadricula(self) -> None:
        """Crea una cuadrícula libre con las dimensiones indicadas."""
        try:
            filas = limitar_dimension(self._filas.get())
            columnas = limitar_dimension(self._columnas.get())
        except (tk.TclError, ValueError):
            messagebox.showerror("Dimensiones inválidas",
                                 "Las dimensiones deben ser números enteros.",
                                 parent=self.winfo_toplevel())
            return
        self._diseno.nueva(filas, columnas)
        self._filas.set(filas)
        self._columnas.set(columnas)
        self._dibujar()
        self._estado.set(f"Cuadrícula de {filas} × {columnas} generada.")

    def cargar_escenario(self, esc: Escenario) -> None:
        """Muestra en el editor un escenario existente."""
        self._diseno.cargar(esc)
        self._filas.set(esc.filas)
        self._columnas.set(esc.columnas)
        self._dibujar()

    def _construir_escenario(self) -> Optional[Escenario]:
        """Convierte el diseño en escenario; avisa al usuario si no es válido."""
        try:
            return self._diseno.a_escenario()
        except DisenoInvalido as exc:
            aviso = (messagebox.showwarning if exc.titulo == "Escenario incompleto"
                     else messagebox.showerror)
            aviso(exc.titulo, str(exc), parent=self.winfo_toplevel())
            return None

    # -- Dibujo e interacción ----------------------------------------------

    def _celda_en(self, x: int, y: int) -> Optional[Posicion]:
        """Convierte coordenadas de pantalla del lienzo en una celda (fila, columna)."""
        x, y = int(self._lienzo.canvasx(x)), int(self._lienzo.canvasy(y))
        pos = ((y - self._margen_y) // self._tamano_celda,
               (x - self._margen_x) // self._tamano_celda)
        return pos if self._diseno.dentro(pos) else None

    def _dibujar(self) -> None:
        """Redibuja la cuadrícula completa ajustándola al tamaño disponible."""
        lienzo = self._lienzo
        lienzo.delete("all")
        diseno = self._diseno
        filas, columnas = diseno.filas, diseno.columnas
        ancho, alto = max(lienzo.winfo_width(), 1), max(lienzo.winfo_height(), 1)
        ajuste = max(TAMANO_CELDA_MIN, min(TAMANO_CELDA_MAX, (ancho - 32) // columnas,
                                           (alto - 32) // filas))
        t = max(TAMANO_CELDA_MIN, round(ajuste * self._zoom))
        self._tamano_celda = t
        self._texto_zoom.set(f"{round(self._zoom * 100)} %")

        # Centrada si cabe; si no, con margen fijo y desplazable.
        self._margen_x = max(16, (ancho - t * columnas) // 2)
        self._margen_y = max(16, (alto - t * filas) // 2)
        lienzo.configure(scrollregion=(0, 0, t * columnas + 2 * self._margen_x,
                                       t * filas + 2 * self._margen_y))

        fuente = ("TkDefaultFont", max(7, t // 3), "bold")
        for f, fila in enumerate(diseno.grid):
            for c, valor in enumerate(fila):
                x0, y0 = self._margen_x + c * t, self._margen_y + f * t
                relleno = (COLORES["celda_libre_marcada"] if (f, c) in diseno.libres_marcadas
                           else color_celda(valor))
                lienzo.create_rectangle(x0, y0, x0 + t, y0 + t, fill=relleno,
                                        outline=COLORES["borde"])
                marca = None
                if (f, c) == diseno.inicio:
                    marca = ("I", COLOR_INICIO)
                elif (f, c) in diseno.salidas:
                    marca = ("S", COLOR_SALIDA)
                if marca:
                    m = max(2, t // 6)
                    lienzo.create_oval(x0 + m, y0 + m, x0 + t - m, y0 + t - m,
                                       fill=marca[1], outline="")
                    if t >= 14:
                        lienzo.create_text(x0 + t / 2, y0 + t / 2, text=marca[0],
                                           fill="#FFFFFF", font=fuente)

    def _al_pintar(self, evento: tk.Event) -> None:
        """Aplica la herramienta seleccionada sobre la celda bajo el puntero."""
        pos = self._celda_en(evento.x, evento.y)
        if pos is None or pos == self._ultima_celda:
            return
        self._ultima_celda = pos
        self._diseno.aplicar(self._herramienta.get(), pos, int(self._nivel_humo.get()))
        self._dibujar()

    def _al_mover(self, evento: tk.Event) -> None:
        pos = self._celda_en(evento.x, evento.y)
        if pos is not None:
            self._estado.set(f"Celda (fila {pos[0]}, columna {pos[1]})  ·  "
                             f"valor {self._diseno.valor(pos)}")

    # -- Acciones ----------------------------------------------------------

    def _aplicar_zoom(self, zoom: float) -> None:
        """Cambia el nivel de zoom conservando el centro de la vista."""
        zoom = min(ZOOM_MAX, max(ZOOM_MIN, zoom))
        if zoom == self._zoom:
            return
        x0, x1 = self._lienzo.xview()
        y0, y1 = self._lienzo.yview()
        self._zoom = zoom
        self._dibujar()
        ancho_v, alto_v = x1 - x0, y1 - y0
        nx0, nx1 = self._lienzo.xview()
        ny0, ny1 = self._lienzo.yview()
        self._lienzo.xview_moveto((x0 + ancho_v / 2) - (nx1 - nx0) / 2)
        self._lienzo.yview_moveto((y0 + alto_v / 2) - (ny1 - ny0) / 2)

    def acercar(self) -> None:
        """Aumenta el tamaño de las celdas (lupa +)."""
        self._aplicar_zoom(self._zoom * ZOOM_PASO)

    def alejar(self) -> None:
        """Reduce el tamaño de las celdas (lupa -)."""
        self._aplicar_zoom(self._zoom / ZOOM_PASO)

    def ajustar_zoom(self) -> None:
        """Ajusta la cuadrícula completa al tamaño de la ventana."""
        self._aplicar_zoom(1.0)
        self._lienzo.xview_moveto(0)
        self._lienzo.yview_moveto(0)

    def calcular_ruta(self) -> None:
        """Resuelve el escenario actual con UCS y muestra el resultado."""
        esc = self._construir_escenario()
        if esc is None:
            return
        try:
            res = buscar_ucs(esc)
        except Exception as e:
            messagebox.showerror("Error en la búsqueda", f"Detalle técnico: {e}", parent=self.winfo_toplevel())
            return
        if res.encontrada:
            self._estado.set(f"Ruta encontrada: costo {res.costo}, {res.pasos} pasos, "
                             f"{res.nodos_expandidos} nodos expandidos, "
                             f"{res.tiempo_ms:.2f} ms.")
        else:
            self._estado.set("No existe una ruta transitable hacia ninguna salida.")
        self._al_calcular(esc, res)

    def guardar(self) -> None:
        """Guarda el escenario actual como archivo CSV."""
        esc = self._construir_escenario()
        if esc is None:
            return
        ruta = filedialog.asksaveasfilename(
            parent=self.winfo_toplevel(), title="Guardar escenario", defaultextension=".csv",
            filetypes=[("Archivos CSV", "*.csv")], initialfile="escenario.csv")
        if not ruta:
            return
        try:
            guardar_csv(ruta, esc)
        except OSError as e:
            messagebox.showerror("Error al guardar", f"Detalle técnico: {e}", parent=self.winfo_toplevel())
            return
        self._estado.set(f"Escenario guardado en «{ruta}».")

    def abrir(self) -> None:
        """Carga un escenario CSV existente para editarlo."""
        ruta = filedialog.askopenfilename(
            parent=self.winfo_toplevel(), title="Abrir escenario",
            filetypes=[("Archivos CSV", "*.csv"), ("Todos los archivos", "*.*")])
        if not ruta:
            return
        try:
            self.cargar_escenario(cargar_csv(ruta))
        except Exception as e:
            messagebox.showerror("Error al abrir", f"Detalle técnico: {e}", parent=self.winfo_toplevel())
            return
        self._estado.set(f"Escenario «{ruta}» cargado para edición.")
