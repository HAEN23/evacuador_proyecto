"""Interfaz gráfica del Sistema de Evacuación Táctica.

Este módulo implementa la ventana principal de escritorio (``tkinter``/``ttk``)
del Planificador de Evacuación Táctica. Todo el trabajo ocurre en una sola
ventana que alterna entre tres vistas:

* Inicio: acceso a las acciones principales y referencia del modelo.
* Editor: diseño interactivo de escenarios (módulo ``editor``).
* Resultado: mapa de riesgo con la ruta calculada por Búsqueda de Costo
  Uniforme (UCS) y sus métricas (módulo ``resultado``).
* Editor del AG: escenario más grupos de personas y parámetros del algoritmo
  genético (módulo ``editor_ag``).
* Resultado del AG: las tres mejores ubicaciones de salidas, la evolución de la
  aptitud, la curva de evacuación y las tablas (módulo ``resultado_ag``).

Proyecto desarrollado para la asignatura Fundamentos de Inteligencia
Artificial, Universidad Politécnica de Chiapas.
"""

from __future__ import annotations

import os
import tkinter as tk
from tkinter import filedialog, messagebox
from tkinter import ttk
from typing import Final, Optional

from ..config import NOMBRE_SISTEMA
from ..io_csv import cargar_csv
from ..genetico import Configuracion, Grupo, ParametrosAG, ResultadoAG
from ..modelos import Escenario, Resultado
from ..ucs import buscar_ucs
from .dialogos import guardar_escenario_como
from .editor import EditorEscenarios
from .editor_ag import EditorAG
from .resultado import VistaResultado
from .resultado_ag import VistaResultadoAG
from .tema import (ANCHO_TEXTO, COLORES, configurar_estilos, elegir_fuente,
                   muestra_color, muestra_degradado)

TITULO_APP: Final[str] = NOMBRE_SISTEMA
SUBTITULO_APP: Final[str] = (
    "Rutas de evacuación con Búsqueda de Costo Uniforme y ubicación de "
    "salidas de emergencia con algoritmos genéticos"
)
VERSION_APP: Final[str] = "2.0.0"
INSTITUCION: Final[str] = "Universidad Politécnica de Chiapas"
ASIGNATURA: Final[str] = "Fundamentos de Inteligencia Artificial"


# ---------------------------------------------------------------------------
# Ventana principal
# ---------------------------------------------------------------------------

class AplicacionEvacuacion:
    """Ventana principal del Sistema de Evacuación Táctica.

    Organiza la interfaz en cuatro regiones: barra de menú, encabezado
    institucional, área de trabajo y barra de estado. El área de trabajo
    alterna entre las vistas de inicio, editor y resultado sin abrir
    ventanas adicionales.

    Attributes:
        raiz: Ventana raíz de ``tkinter``.
        fuente: Familia tipográfica utilizada en toda la interfaz.
    """

    def __init__(self, raiz: tk.Tk) -> None:
        self.raiz = raiz
        self.fuente = elegir_fuente()

        self._estado = tk.StringVar(value="Listo")
        self._area: Optional[ttk.Frame] = None
        self._vista_inicio: Optional[ttk.Frame] = None
        self._editor: Optional[ttk.Frame] = None
        self._vista_resultado: Optional[ttk.Frame] = None
        self._editor_ag: Optional[EditorAG] = None
        self._vista_resultado_ag: Optional[VistaResultadoAG] = None
        self._detalles_encabezado: list[ttk.Label] = []

        self._configurar_ventana()
        configurar_estilos(self.raiz, self.fuente)
        self._crear_menu()
        self._crear_encabezado()
        self._crear_area_trabajo()
        self._crear_barra_estado()
        self._registrar_atajos()
        self.mostrar_inicio()

    # -- Configuración general ---------------------------------------------

    def _configurar_ventana(self) -> None:
        """Define título, dimensiones y estado inicial de la ventana."""
        self.raiz.title(f"{TITULO_APP} — v{VERSION_APP}")
        self.raiz.configure(bg=COLORES["fondo"])
        self.raiz.minsize(960, 660)
        self.raiz.geometry("1180x760")
        self.raiz.columnconfigure(0, weight=1)
        self.raiz.rowconfigure(1, weight=1)
        self.raiz.option_add("*tearOff", False)
        self._maximizar()

    def _maximizar(self) -> None:
        """Maximiza la ventana de forma compatible con Windows, Linux y macOS."""
        try:
            self.raiz.state("zoomed")
        except tk.TclError:
            try:
                self.raiz.attributes("-zoomed", True)
            except tk.TclError:
                pass

    def _registrar_atajos(self) -> None:
        """Asocia los atajos de teclado a las acciones principales."""
        self.raiz.bind_all("<Control-o>", lambda _e: self.abrir_escenario())
        self.raiz.bind_all("<Control-n>", lambda _e: self.mostrar_editor())
        self.raiz.bind_all("<Control-g>", lambda _e: self.mostrar_editor_ag())
        self.raiz.bind_all("<Control-O>", lambda _e: self.abrir_escenario_ag())
        self.raiz.bind_all("<Control-s>", lambda _e: self.guardar_escenario())
        self.raiz.bind_all("<Control-q>", lambda _e: self.salir())
        self.raiz.bind_all("<F1>", lambda _e: self.mostrar_formato_csv())
        self.raiz.protocol("WM_DELETE_WINDOW", self.salir)

    # -- Construcción de regiones ------------------------------------------

    def _crear_menu(self) -> None:
        """Construye la barra de menú (Archivo y Ayuda)."""
        barra = tk.Menu(self.raiz)

        archivo = tk.Menu(barra)
        archivo.add_command(label="Abrir escenario…", accelerator="Ctrl+O",
                            command=self.abrir_escenario)
        archivo.add_command(label="Nuevo escenario", accelerator="Ctrl+N",
                            command=self.mostrar_editor)
        archivo.add_command(label="Guardar escenario como CSV…", accelerator="Ctrl+S",
                            command=self.guardar_escenario)
        archivo.add_command(label="Pantalla de inicio", command=self.mostrar_inicio)
        archivo.add_separator()
        archivo.add_command(label="Salir", accelerator="Ctrl+Q", command=self.salir)
        barra.add_cascade(label="Archivo", menu=archivo)

        genetico = tk.Menu(barra)
        genetico.add_command(label="Abrir escenario existente (CSV)…",
                             accelerator="Ctrl+Mayús+O", command=self.abrir_escenario_ag)
        genetico.add_command(label="Crear nuevo escenario", accelerator="Ctrl+G",
                             command=self.mostrar_editor_ag)
        genetico.add_separator()
        genetico.add_command(label="Formato de los grupos CSV",
                             command=self.mostrar_formato_grupos)
        barra.add_cascade(label="Algoritmo genético", menu=genetico)

        ayuda = tk.Menu(barra)
        ayuda.add_command(label="Formato del escenario CSV", accelerator="F1",
                          command=self.mostrar_formato_csv)
        ayuda.add_separator()
        ayuda.add_command(label=f"Acerca de {TITULO_APP}", command=self.mostrar_acerca_de)
        barra.add_cascade(label="Ayuda", menu=ayuda)

        self.raiz.config(menu=barra)

    def _crear_encabezado(self) -> None:
        """Construye el encabezado institucional con franja de acento."""
        encabezado = ttk.Frame(self.raiz, style="Header.TFrame", padding=(56, 28, 56, 26))
        encabezado.grid(row=0, column=0, sticky="ew")
        encabezado.columnconfigure(0, weight=1)

        self._encabezado = encabezado
        antetitulo = ttk.Label(encabezado, text="GESTIÓN DE SEGURIDAD INDUSTRIAL",
                               style="Eyebrow.TLabel")
        antetitulo.grid(row=0, column=0, sticky="w")
        ttk.Label(encabezado, text=TITULO_APP,
                  style="HeaderTitle.TLabel").grid(row=1, column=0, sticky="w", pady=(6, 2))
        subtitulo = ttk.Label(encabezado, text=SUBTITULO_APP, style="HeaderSubtitle.TLabel")
        subtitulo.grid(row=2, column=0, sticky="w")
        # En el editor y el resultado el encabezado se compacta para ganar espacio.
        self._detalles_encabezado = [antetitulo, subtitulo]
        ttk.Label(encabezado, text=f"Versión {VERSION_APP}",
                  style="Version.TLabel").grid(row=0, column=1, sticky="ne")

        # Franja de acento que identifica el contexto de emergencia.
        tk.Frame(self.raiz, bg=COLORES["acento"], height=3).grid(row=0, column=0, sticky="sew")

    def _crear_area_trabajo(self) -> None:
        """Construye el área central donde se alternan las vistas."""
        self._area = ttk.Frame(self.raiz, style="App.TFrame")
        self._area.grid(row=1, column=0, sticky="nsew")
        self._area.columnconfigure(0, weight=1)
        self._area.rowconfigure(0, weight=1)

        # Vista de inicio: dos tarjetas de operación (UCS y AG) y la referencia debajo.
        # Va dentro de un Canvas para poder desplazarla en pantallas pequeñas.
        self._vista_inicio = ttk.Frame(self._area, style="App.TFrame")
        self._vista_inicio.columnconfigure(0, weight=1)
        self._vista_inicio.rowconfigure(0, weight=1)
        lienzo = tk.Canvas(self._vista_inicio, bg=COLORES["fondo"], highlightthickness=0, bd=0)
        barra = ttk.Scrollbar(self._vista_inicio, orient="vertical", command=lienzo.yview,
                              style="Panel.Vertical.TScrollbar")
        lienzo.configure(yscrollcommand=barra.set)
        lienzo.grid(row=0, column=0, sticky="nsew")
        barra.grid(row=0, column=1, sticky="ns")

        contenido = ttk.Frame(lienzo, style="App.TFrame", padding=(32, 28))
        contenido.columnconfigure(0, weight=1, uniform="paneles", minsize=440)
        contenido.columnconfigure(1, weight=1, uniform="paneles", minsize=440)
        ventana = lienzo.create_window(0, 0, window=contenido, anchor="n")

        def ajustar(_evento: tk.Event) -> None:
            # Centra el contenido y actualiza la zona desplazable al cambiar el tamaño.
            ancho = max(lienzo.winfo_width(), contenido.winfo_reqwidth())
            lienzo.coords(ventana, ancho / 2, 0)
            lienzo.configure(scrollregion=(0, 0, ancho, contenido.winfo_reqheight()))

        def desplazar(evento: tk.Event) -> None:
            if contenido.winfo_reqheight() <= lienzo.winfo_height():
                return
            arriba = evento.num == 4 or getattr(evento, "delta", 0) > 0
            lienzo.yview_scroll(-1 if arriba else 1, "units")

        lienzo.bind("<Configure>", ajustar)
        contenido.bind("<Configure>", ajustar)
        for secuencia in ("<MouseWheel>", "<Button-4>", "<Button-5>"):
            lienzo.bind(secuencia, desplazar)
            contenido.bind(secuencia, desplazar)

        self._crear_panel_operacion(contenido)
        self._crear_panel_ag(contenido)
        self._crear_panel_referencia(contenido)

    @staticmethod
    def _crear_tarjeta(padre: tk.Misc, columna: int, padx: tuple[int, int], fila: int = 0,
                       columnas: int = 1) -> ttk.Frame:
        """Crea un panel blanco con borde fino y devuelve su contenedor interno."""
        marco = tk.Frame(padre, bg=COLORES["borde"], bd=0)
        marco.grid(row=fila, column=columna, columnspan=columnas, sticky="nsew", padx=padx,
                   pady=(0 if fila == 0 else 24, 0))
        interior = ttk.Frame(marco, style="Card.TFrame", padding=(32, 28))
        interior.pack(fill="both", expand=True, padx=1, pady=1)
        interior.columnconfigure(0, weight=1)
        return interior

    def _crear_panel_operacion(self, padre: tk.Misc) -> None:
        """Panel izquierdo: acciones principales del sistema."""
        tarjeta = self._crear_tarjeta(padre, columna=0, padx=(0, 12))

        ttk.Label(tarjeta, text="OPERACIÓN",
                  style="CardEyebrow.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(tarjeta, text="Planificar una evacuación",
                  style="SectionTitle.TLabel").grid(row=1, column=0, sticky="w", pady=(4, 0))
        ttk.Label(
            tarjeta,
            text="Seleccione un escenario en formato CSV para calcular la ruta de "
                 "menor riesgo acumulado hacia la salida de emergencia y "
                 "visualizar el resultado.",
            style="Body.TLabel", wraplength=ANCHO_TEXTO, justify="left",
        ).grid(row=2, column=0, sticky="w", pady=(10, 24))

        ttk.Button(tarjeta, text="Abrir escenario existente (CSV)",
                   style="Primary.TButton", cursor="hand2",
                   command=self.abrir_escenario).grid(row=3, column=0, sticky="ew")
        ttk.Label(tarjeta, text="Atajo: Ctrl + O",
                  style="Hint.TLabel").grid(row=4, column=0, sticky="e", pady=(4, 12))

        ttk.Button(tarjeta, text="Crear nuevo escenario",
                   style="Secondary.TButton", cursor="hand2",
                   command=self.mostrar_editor).grid(row=5, column=0, sticky="ew")
        ttk.Label(tarjeta, text="Atajo: Ctrl + N",
                  style="Hint.TLabel").grid(row=6, column=0, sticky="e", pady=(4, 0))

    def _crear_panel_ag(self, padre: tk.Misc) -> None:
        """Panel derecho: las mismas acciones, para el algoritmo genético."""
        tarjeta = self._crear_tarjeta(padre, columna=1, padx=(12, 0))

        ttk.Label(tarjeta, text="ALGORITMO GENÉTICO",
                  style="CardEyebrow.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(tarjeta, text="Ubicar salidas de emergencia",
                  style="SectionTitle.TLabel").grid(row=1, column=0, sticky="w", pady=(4, 0))
        ttk.Label(
            tarjeta,
            text="Coloque grupos de personas sobre el escenario y el algoritmo genético "
                 "decide dónde poner k salidas para que salgan más personas, con menos "
                 "riesgo, en menos tiempo y sin aglomeraciones.",
            style="Body.TLabel", wraplength=ANCHO_TEXTO, justify="left",
        ).grid(row=2, column=0, sticky="w", pady=(10, 24))

        ttk.Button(tarjeta, text="Abrir escenario existente (CSV)",
                   style="Primary.TButton", cursor="hand2",
                   command=self.abrir_escenario_ag).grid(row=3, column=0, sticky="ew")
        ttk.Label(tarjeta, text="Atajo: Ctrl + Mayús + O",
                  style="Hint.TLabel").grid(row=4, column=0, sticky="e", pady=(4, 12))

        ttk.Button(tarjeta, text="Crear nuevo escenario",
                   style="Secondary.TButton", cursor="hand2",
                   command=self.mostrar_editor_ag).grid(row=5, column=0, sticky="ew")
        ttk.Label(tarjeta, text="Atajo: Ctrl + G",
                  style="Hint.TLabel").grid(row=6, column=0, sticky="e", pady=(4, 0))

    def _crear_panel_referencia(self, padre: tk.Misc) -> None:
        """Panel inferior: codificación de celdas (izquierda) y parámetros (derecha)."""
        tarjeta = self._crear_tarjeta(padre, columna=0, padx=(0, 0), fila=1, columnas=2)
        tarjeta.columnconfigure(0, weight=1, uniform="ref")
        tarjeta.columnconfigure(1, weight=1, uniform="ref")

        ttk.Label(tarjeta, text="REFERENCIA",
                  style="CardEyebrow.TLabel").grid(row=0, column=0, columnspan=2, sticky="w")

        codificacion = ttk.Frame(tarjeta, style="Card.TFrame")
        codificacion.grid(row=1, column=0, sticky="nw", padx=(0, 24))
        ttk.Label(codificacion, text="Codificación del escenario",
                  style="SectionTitle.TLabel").grid(row=0, column=0, columnspan=2,
                                                    sticky="w", pady=(4, 12))
        leyenda = (
            (muestra_color(codificacion, COLORES["celda_bloqueada"]), "0",
             "Celda bloqueada (pared o fuego letal)"),
            (muestra_color(codificacion, COLORES["celda_libre"]), "1",
             "Celda libre y sin contaminación"),
            (muestra_degradado(codificacion), "2 – 99",
             "Humo o tóxico; el valor es el costo de transición"),
        )
        for i, (muestra, valor, descripcion) in enumerate(leyenda, start=1):
            muestra.grid(row=i, column=0, sticky="w", pady=5)
            fila = ttk.Frame(codificacion, style="Card.TFrame")
            fila.grid(row=i, column=1, sticky="w", padx=(12, 0))
            ttk.Label(fila, text=valor, style="Term.TLabel", width=7).pack(side="left")
            ttk.Label(fila, text=descripcion, style="Body.TLabel").pack(side="left")

        modelo = ttk.Frame(tarjeta, style="Card.TFrame")
        modelo.grid(row=1, column=1, sticky="nw")
        ttk.Label(modelo, text="Parámetros del modelo",
                  style="SectionTitle.TLabel").grid(row=0, column=0, columnspan=2,
                                                    sticky="w", pady=(4, 12))
        parametros = (
            ("Ruta", "Búsqueda de Costo Uniforme (UCS), óptima y completa"),
            ("Movimientos", "Norte, Sur, Este y Oeste"),
            ("Criterio", "Minimizar el riesgo acumulado g(n)"),
            ("Salidas", "Algoritmo genético con k = 2, 3 o 4 salidas"),
            ("Aptitud", "O1 · 1/(1+O2) · 1/(1+O3) · 1/(1+O4)"),
        )
        for i, (termino, valor) in enumerate(parametros, start=1):
            ttk.Label(modelo, text=termino, style="Term.TLabel").grid(
                row=i, column=0, sticky="w", pady=2)
            ttk.Label(modelo, text=valor, style="Body.TLabel").grid(
                row=i, column=1, sticky="w", padx=(12, 0), pady=2)

    def _crear_barra_estado(self) -> None:
        """Construye la barra de estado inferior."""
        tk.Frame(self.raiz, bg=COLORES["borde"], height=1).grid(row=2, column=0, sticky="ew")
        barra = ttk.Frame(self.raiz, style="Status.TFrame", padding=(24, 8))
        barra.grid(row=3, column=0, sticky="ew")
        barra.columnconfigure(0, weight=1)

        ttk.Label(barra, textvariable=self._estado,
                  style="Status.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(barra, text=f"{INSTITUCION}  ·  {ASIGNATURA}",
                  style="Status.TLabel").grid(row=0, column=1, sticky="e")

    # -- Navegación entre vistas -------------------------------------------

    def _mostrar_vista(self, vista: ttk.Frame, compacto: bool) -> None:
        """Muestra una vista en el área de trabajo y oculta las demás."""
        # Las vistas comparten el mismo espacio; grid_remove las oculta sin destruirlas.
        for otra in (self._vista_inicio, self._editor, self._vista_resultado,
                     self._editor_ag, self._vista_resultado_ag):
            if otra is not None and otra is not vista:
                otra.grid_remove()
        vista.grid(row=0, column=0, sticky="nsew")
        # El encabezado compacto deja más espacio al editor y al mapa de resultados.
        for etiqueta in self._detalles_encabezado:
            if compacto:
                etiqueta.grid_remove()
            else:
                etiqueta.grid()
        self._encabezado.configure(padding=(56, 14) if compacto else (56, 28, 56, 26))

    def mostrar_inicio(self) -> None:
        """Muestra la pantalla de inicio."""
        self._mostrar_vista(self._vista_inicio, compacto=False)
        self._estado.set("Listo")

    def mostrar_editor(self, escenario: Optional[Escenario] = None) -> None:
        """Muestra el editor de escenarios, opcionalmente con un escenario cargado.

        Args:
            escenario: Escenario a editar. Si se omite, se conserva el diseño
                en curso del editor.
        """
        # El editor se instancia una sola vez para conservar el diseño al volver.
        if self._editor is None:
            self._editor = EditorEscenarios(
                self._area, estado=self._estado,
                al_calcular=lambda esc, res: self.mostrar_resultado(
                    esc, res, "Escenario diseñado en el editor", desde_editor=True),
                al_volver=self.mostrar_inicio)
            self._editor.configure(padding=24)
        if escenario is not None:
            self._editor.cargar_escenario(escenario)
        self._mostrar_vista(self._editor, compacto=True)
        self._estado.set("Editor de escenarios: seleccione una herramienta y pinte "
                         "sobre la cuadrícula.")

    def mostrar_resultado(self, escenario: Escenario, resultado: Resultado, nombre: str,
                          desde_editor: bool = False) -> None:
        """Muestra el mapa de riesgo y las métricas de un escenario resuelto.

        Args:
            escenario: Escenario resuelto.
            resultado: Resultado de la búsqueda UCS.
            nombre: Nombre que identifica al escenario en la vista.
            desde_editor: ``True`` si el cálculo se lanzó desde el editor; en
                ese caso el botón de edición regresa al diseño en curso.
        """
        # Cada cálculo reemplaza la vista anterior para actualizar mapa y gráfica.
        if self._vista_resultado is not None:
            self._vista_resultado.destroy()
        # Si se llega desde el editor, se vuelve al diseño; si no, se carga este mapa.
        if desde_editor:
            al_editar, texto_editar = self.mostrar_editor, "Volver al editor"
        else:
            al_editar = lambda: self.mostrar_editor(escenario)  # noqa: E731
            texto_editar = "Editar este escenario"
        self._vista_resultado = VistaResultado(
            self._area, escenario, resultado, nombre,
            al_volver=self.mostrar_inicio, al_editar=al_editar, texto_editar=texto_editar,
            al_guardar=lambda: self._guardar_resultado(escenario, nombre))
        self._vista_resultado.configure(padding=24)
        self._mostrar_vista(self._vista_resultado, compacto=True)

    def mostrar_editor_ag(self, escenario: Optional[Escenario] = None) -> None:
        """Muestra el editor del AG, opcionalmente con un escenario cargado."""
        if self._editor_ag is None:
            self._editor_ag = EditorAG(self._area, estado=self._estado,
                                       al_optimizar=self.mostrar_resultado_ag,
                                       al_volver=self.mostrar_inicio)
            self._editor_ag.configure(padding=24)
        if escenario is not None:
            self._editor_ag.cargar_escenario(escenario)
        self._mostrar_vista(self._editor_ag, compacto=True)
        self._estado.set("Algoritmo genético: pinte el escenario, coloque grupos de personas "
                         "y ejecute el algoritmo (F5).")

    def mostrar_resultado_ag(self, escenario: Escenario, grupos: list[Grupo],
                             params: ParametrosAG, resultado: ResultadoAG,
                             manual: Optional[Configuracion] = None) -> None:
        """Muestra las tres mejores ubicaciones de salidas, gráficas y tablas del AG.

        ``manual`` es la evaluación de las salidas colocadas en el editor, si las hay.
        """
        if self._vista_resultado_ag is not None:
            self._vista_resultado_ag.destroy()
        self._vista_resultado_ag = VistaResultadoAG(
            self._area, escenario, grupos, params, resultado,
            al_volver=self.mostrar_inicio, al_editar=self.mostrar_editor_ag,
            al_guardar=lambda: self._guardar_resultado(escenario, "escenario_ag.csv"),
            al_guardar_grupos=self._editor_ag.guardar_grupos, manual=manual)
        self._vista_resultado_ag.configure(padding=24)
        self._mostrar_vista(self._vista_resultado_ag, compacto=True)

    def abrir_escenario_ag(self) -> None:
        """Pide un CSV de escenario y lo abre en el editor del AG."""
        ruta = filedialog.askopenfilename(
            title="Seleccionar escenario CSV para el AG",
            filetypes=[("Archivos CSV", "*.csv"), ("Todos los archivos", "*.*")])
        if not ruta:
            return
        try:
            escenario = cargar_csv(ruta)
        except (ValueError, OSError) as exc:
            messagebox.showerror("Error al abrir el escenario",
                                 f"No fue posible abrir «{os.path.basename(ruta)}».\n\n"
                                 f"Detalle técnico: {exc}")
            return
        self.mostrar_editor_ag(escenario)
        self._estado.set(f"Escenario «{os.path.basename(ruta)}» cargado. Agregue grupos "
                         "(Abrir grupos CSV, Generar al azar o la herramienta Grupo).")

    # -- Acciones de la interfaz -------------------------------------------

    def guardar_escenario(self) -> None:
        """Guarda en CSV el escenario de la vista activa (editor o resultado)."""
        # winfo_ismapped identifica cuál de las vistas está visible.
        if self._editor is not None and self._editor.winfo_ismapped():
            self._editor.guardar()
        elif self._vista_resultado is not None and self._vista_resultado.winfo_ismapped():
            self._vista_resultado.guardar()
        elif self._editor_ag is not None and self._editor_ag.winfo_ismapped():
            self._editor_ag.guardar()
        elif (self._vista_resultado_ag is not None
              and self._vista_resultado_ag.winfo_ismapped()):
            self._vista_resultado_ag.guardar()
        else:
            messagebox.showinfo(
                "Guardar escenario",
                "Cree un escenario con «Nuevo escenario» o abra uno existente para "
                "poder guardarlo como CSV.", parent=self.raiz)

    def _guardar_resultado(self, escenario: Escenario, nombre: str) -> None:
        """Guarda como CSV el escenario mostrado en la vista de resultado."""
        sugerido = nombre if nombre.lower().endswith(".csv") else "escenario_nuevo.csv"
        ruta = guardar_escenario_como(self.raiz, escenario, sugerido)
        if ruta is not None:
            self._estado.set(f"Escenario guardado en «{ruta}».")

    def abrir_escenario(self) -> None:
        """Pide un CSV, calcula la ruta con UCS y muestra la vista de resultado."""
        ruta = filedialog.askopenfilename(
            title="Seleccionar escenario CSV",
            filetypes=[("Archivos CSV", "*.csv"), ("Todos los archivos", "*.*")])
        if not ruta:
            return
        nombre = os.path.basename(ruta)
        self._registrar_progreso("procesando", nombre)
        try:
            # Carga el escenario y resuelve UCS antes de mostrar la vista.
            escenario = cargar_csv(ruta)
            resultado = buscar_ucs(escenario)
        except (ValueError, OSError) as exc:
            # Los archivos inválidos o ilegibles se notifican sin cerrar la GUI.
            self._registrar_progreso("error", nombre)
            messagebox.showerror(
                "Error al procesar el escenario",
                f"No fue posible procesar el archivo «{nombre}».\n\n"
                f"Detalle técnico: {exc}\n\n"
                "Verifique que el archivo cumpla con el formato descrito en "
                "Ayuda › Formato del escenario CSV.")
            return
        self._registrar_progreso("completado", nombre)
        self.mostrar_resultado(escenario, resultado, nombre)

    def _registrar_progreso(self, estado: str, nombre_archivo: str) -> None:
        """Actualiza la barra de estado según el avance del procesamiento.

        Args:
            estado: ``"procesando"``, ``"completado"`` o ``"error"``.
            nombre_archivo: Nombre del archivo CSV en proceso.
        """
        if estado == "procesando":
            self._estado.set(f"Procesando escenario «{nombre_archivo}»…")
            self.raiz.config(cursor="watch")
            # Fuerza a tkinter a repintar el estado y el cursor antes del trabajo pesado.
            self.raiz.update_idletasks()
            return

        self.raiz.config(cursor="")
        if estado == "completado":
            self._estado.set(f"Escenario «{nombre_archivo}» procesado correctamente")
        else:
            self._estado.set(f"No fue posible procesar «{nombre_archivo}»")

    def mostrar_formato_csv(self) -> None:
        """Muestra la especificación del formato de escenario CSV."""
        messagebox.showinfo(
            "Formato del escenario CSV",
            "Cada escenario es una cuadrícula de valores enteros separados por comas.\n\n"
            "Primera línea (cabecera de metadatos):\n"
            "    # start=fila,columna goal=fila,columna\n"
            "    Indica la celda de inicio del agente y la salida de emergencia.\n"
            "    Si existen varias salidas, se separan con punto y coma:\n"
            "    goal=11,19;0,19\n\n"
            "Valores de celda:\n"
            "    0        Celda bloqueada (pared o fuego letal)\n"
            "    1        Celda libre y sin contaminación\n"
            "    2 – 99   Humo o tóxico; el valor es el costo de transición",
        )

    def mostrar_formato_grupos(self) -> None:
        """Muestra la especificación del formato de grupos CSV."""
        messagebox.showinfo(
            "Formato de los grupos CSV",
            "Una fila por grupo de personas, con encabezado:\n\n"
            "    fila,columna,tamano\n"
            "    3,5,4\n"
            "    10,2,1\n\n"
            "fila y columna empiezan en 0; tamano es el número de personas (1 o más).\n"
            "Un grupo no puede estar sobre una celda bloqueada.\n\n"
            "Ejemplos en la carpeta data/: grupos_a.csv … grupos_d.csv, para los "
            "escenarios a_sin_humo.csv … d_mapa_grande.csv.",
        )

    def mostrar_acerca_de(self) -> None:
        """Muestra la información general del sistema."""
        messagebox.showinfo(
            f"Acerca de {TITULO_APP}",
            f"{TITULO_APP}\nVersión {VERSION_APP}\n\n"
            "Sistema inteligente que calcula la ruta de escape más segura dentro "
            "de una instalación industrial durante un incendio, priorizando "
            "rodear zonas con humo tóxico o fuego.\n\n"
            "Versión 2: un algoritmo genético (EvacuAG) decide dónde colocar k salidas "
            "de emergencia para evacuar a varios grupos de personas con el menor "
            "riesgo, tiempo y aglomeración.\n\n"
            f"{ASIGNATURA}\n{INSTITUCION}",
        )

    def salir(self) -> None:
        """Solicita confirmación y cierra la aplicación."""
        if messagebox.askokcancel("Salir", "¿Desea cerrar el Sistema de Evacuación Táctica?",
                                  parent=self.raiz):
            self.raiz.destroy()

    def ejecutar(self) -> None:
        """Inicia el ciclo principal de eventos."""
        self.raiz.mainloop()


def iniciar_interfaz() -> None:
    """Construye y lanza la ventana principal del programa."""
    AplicacionEvacuacion(tk.Tk()).ejecutar()


if __name__ == "__main__":
    iniciar_interfaz()
