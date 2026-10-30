"""Interfaz gráfica del Sistema de Evacuación Táctica.

Este módulo implementa la ventana principal de escritorio (``tkinter``/``ttk``)
del Planificador de Evacuación Segura. Todo el trabajo ocurre en una sola
ventana que alterna entre tres vistas:

* Inicio: acceso a las acciones principales y referencia del modelo.
* Editor: diseño interactivo de escenarios (módulo ``editor``).
* Resultado: mapa de riesgo con la ruta calculada por Búsqueda de Costo
  Uniforme (UCS) y sus métricas (módulo ``resultado``).

Proyecto desarrollado para la asignatura Fundamentos de Inteligencia
Artificial, Universidad Politécnica de Chiapas.
"""

from __future__ import annotations

import os
import tkinter as tk
from tkinter import filedialog, messagebox
from tkinter import font as tkfont
from tkinter import ttk
from typing import Callable, Final, Optional

from .io_csv import cargar_csv
from .modelos import Escenario, Resultado
from .ucs import buscar_ucs as resolver
from .visualizacion import graficar


# ---------------------------------------------------------------------------
# Constantes de presentación
# ---------------------------------------------------------------------------

TITULO_APP: Final[str] = "Sistema de Evacuación Táctica"
SUBTITULO_APP: Final[str] = (
    "Planificación de rutas de evacuación seguras mediante "
    "Búsqueda de Costo Uniforme"
)
VERSION_APP: Final[str] = "1.0.0"
INSTITUCION: Final[str] = "Universidad Politécnica de Chiapas"
ASIGNATURA: Final[str] = "Fundamentos de Inteligencia Artificial"

COLORES: Final[dict[str, str]] = {
    "fondo": "#F3F5F8",
    "superficie": "#FFFFFF",
    "borde": "#D9DFE7",
    "primario": "#14304F",
    "primario_hover": "#0F2540",
    "primario_presionado": "#0A1B30",
    "acento": "#C8102E",
    "texto": "#1E2A38",
    "texto_secundario": "#5B6B7D",
    "texto_tenue": "#8593A3",
    "texto_invertido": "#FFFFFF",
    "texto_invertido_suave": "#B8C7D9",
    "secundario": "#EEF2F6",
    "secundario_hover": "#E1E7EE",
    "exito": "#2E7D32",
    "error": "#B3261E",
    "celda_bloqueada": "#2E3640",
    "celda_libre": "#FFFFFF",
    "riesgo_bajo": "#F6D365",
    "riesgo_alto": "#B3261E",
}

FUENTES_PREFERIDAS: Final[tuple[str, ...]] = (
    "Segoe UI", "SF Pro Text", "Helvetica Neue", "Inter",
    "Roboto", "Ubuntu", "DejaVu Sans", "Arial",
)

ANCHO_TEXTO: Final[int] = 440
"""Ancho máximo (en píxeles) de los párrafos dentro de los paneles."""

# Firma de la función que muestra un escenario resuelto: (escenario, resultado, nombre).
Presentador = Callable[[Escenario, Resultado, str], None]

# Firma de la función que recibe notificaciones del procesamiento:
# (estado, nombre_de_archivo). Los estados válidos son "procesando",
# "completado" y "error".
Notificador = Callable[[str, str], None]


# ---------------------------------------------------------------------------
# Acciones del sistema
# ---------------------------------------------------------------------------

def abrir_explorador_archivos(notificar: Optional[Notificador] = None,
                              mostrar: Optional[Presentador] = None) -> None:
    """Solicita un escenario CSV, calcula la ruta óptima y la visualiza.

    Args:
        notificar: Función opcional que recibe el estado del procesamiento
            (``"procesando"``, ``"completado"`` o ``"error"``) y el nombre
            del archivo seleccionado. Permite a la interfaz reflejar el
            progreso sin acoplar esta función a un widget concreto.
        mostrar: Función que presenta el resultado. Si se omite, se usa
            :func:`visualizacion.graficar` en una ventana independiente.
    """
    ruta_archivo = filedialog.askopenfilename(
        title="Seleccionar escenario CSV",
        filetypes=[("Archivos CSV", "*.csv"), ("Todos los archivos", "*.*")],
    )
    if not ruta_archivo:
        return

    nombre = os.path.basename(ruta_archivo)
    if notificar:
        notificar("procesando", nombre)

    try:
        esc = cargar_csv(ruta_archivo)
        res = resolver(esc)
    except Exception as e:
        if notificar:
            notificar("error", nombre)
        messagebox.showerror(
            "Error al procesar el escenario",
            f"No fue posible procesar el archivo «{nombre}».\n\n"
            f"Detalle técnico: {e}\n\n"
            "Verifique que el archivo cumpla con el formato descrito en "
            "Ayuda › Formato del escenario CSV.",
        )
        return

    if notificar:
        notificar("completado", nombre)
    if mostrar:
        mostrar(esc, res, nombre)
    else:
        graficar(esc, res)


def abrir_creador_escenarios() -> None:
    """Muestra la vista del editor de escenarios en la ventana principal."""
    if _aplicacion is not None:
        _aplicacion.mostrar_editor()


_aplicacion: Optional["AplicacionEvacuacion"] = None
"""Instancia activa de la ventana principal (una por proceso)."""


# ---------------------------------------------------------------------------
# Utilidades gráficas
# ---------------------------------------------------------------------------

def _elegir_fuente() -> str:
    """Devuelve la primera familia tipográfica disponible en el sistema."""
    disponibles = set(tkfont.families())
    for familia in FUENTES_PREFERIDAS:
        if familia in disponibles:
            return familia
    return "TkDefaultFont"


def _hex_a_rgb(color: str) -> tuple[int, int, int]:
    """Convierte un color ``#RRGGBB`` en una tupla ``(r, g, b)``."""
    return int(color[1:3], 16), int(color[3:5], 16), int(color[5:7], 16)


def _muestra_color(padre: tk.Misc, color: str, ancho: int = 28, alto: int = 18) -> tk.Canvas:
    """Crea un recuadro de color sólido para la leyenda."""
    lienzo = tk.Canvas(padre, width=ancho, height=alto, bg=COLORES["superficie"],
                       highlightthickness=0, bd=0)
    lienzo.create_rectangle(1, 1, ancho - 1, alto - 1, fill=color, outline=COLORES["borde"])
    return lienzo


def _muestra_degradado(padre: tk.Misc, ancho: int = 28, alto: int = 18) -> tk.Canvas:
    """Crea un recuadro con degradado de riesgo bajo a riesgo alto."""
    lienzo = tk.Canvas(padre, width=ancho, height=alto, bg=COLORES["superficie"],
                       highlightthickness=0, bd=0)
    inicio = _hex_a_rgb(COLORES["riesgo_bajo"])
    fin = _hex_a_rgb(COLORES["riesgo_alto"])
    for x in range(1, ancho - 1):
        t = (x - 1) / max(ancho - 3, 1)
        r, g, b = (round(a + (z - a) * t) for a, z in zip(inicio, fin))
        lienzo.create_line(x, 1, x, alto - 1, fill=f"#{r:02x}{g:02x}{b:02x}")
    lienzo.create_rectangle(1, 1, ancho - 1, alto - 1, outline=COLORES["borde"])
    return lienzo


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
        self.fuente = _elegir_fuente()

        self._estado = tk.StringVar(value="Listo")
        self._area: Optional[ttk.Frame] = None
        self._vista_inicio: Optional[ttk.Frame] = None
        self._editor: Optional[ttk.Frame] = None
        self._vista_resultado: Optional[ttk.Frame] = None
        self._detalles_encabezado: list[ttk.Label] = []

        global _aplicacion
        _aplicacion = self

        self._configurar_ventana()
        self._configurar_estilos()
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

    def _configurar_estilos(self) -> None:
        """Registra los estilos ``ttk`` de la aplicación."""
        c, f = COLORES, self.fuente
        estilo = ttk.Style(self.raiz)
        if "clam" in estilo.theme_names():
            estilo.theme_use("clam")

        estilo.configure("App.TFrame", background=c["fondo"])
        estilo.configure("Header.TFrame", background=c["primario"])
        estilo.configure("Card.TFrame", background=c["superficie"])
        estilo.configure("Status.TFrame", background=c["superficie"])

        estilo.configure("Eyebrow.TLabel", background=c["primario"],
                         foreground=c["texto_invertido_suave"], font=(f, 9, "bold"))
        estilo.configure("HeaderTitle.TLabel", background=c["primario"],
                         foreground=c["texto_invertido"], font=(f, 22, "bold"))
        estilo.configure("HeaderSubtitle.TLabel", background=c["primario"],
                         foreground=c["texto_invertido_suave"], font=(f, 11))
        estilo.configure("Version.TLabel", background=c["primario"],
                         foreground=c["texto_invertido_suave"], font=(f, 9))

        estilo.configure("CardEyebrow.TLabel", background=c["superficie"],
                         foreground=c["acento"], font=(f, 9, "bold"))
        estilo.configure("SectionTitle.TLabel", background=c["superficie"],
                         foreground=c["primario"], font=(f, 16, "bold"))
        estilo.configure("Subsection.TLabel", background=c["superficie"],
                         foreground=c["primario"], font=(f, 10, "bold"))
        estilo.configure("Body.TLabel", background=c["superficie"],
                         foreground=c["texto_secundario"], font=(f, 10))
        estilo.configure("Term.TLabel", background=c["superficie"],
                         foreground=c["texto"], font=(f, 10, "bold"))
        estilo.configure("Hint.TLabel", background=c["superficie"],
                         foreground=c["texto_tenue"], font=(f, 9))
        estilo.configure("Status.TLabel", background=c["superficie"],
                         foreground=c["texto_secundario"], font=(f, 9))

        for nombre, color in (("Exito", c["exito"]), ("Error", c["error"])):
            estilo.configure(f"{nombre}.Result.TLabel", background=c["superficie"],
                             foreground=color, font=(f, 11, "bold"))

        estilo.configure("Tool.TRadiobutton", background=c["superficie"],
                         foreground=c["texto"], font=(f, 10))
        estilo.map("Tool.TRadiobutton", background=[("active", c["superficie"])])

        estilo.configure("Primary.TButton", font=(f, 11, "bold"), padding=(20, 12),
                         background=c["primario"], foreground=c["texto_invertido"],
                         borderwidth=0, focusthickness=0, relief="flat")
        estilo.map("Primary.TButton",
                   background=[("pressed", c["primario_presionado"]),
                               ("active", c["primario_hover"])],
                   foreground=[("disabled", c["texto_invertido_suave"])])

        estilo.configure("Secondary.TButton", font=(f, 11), padding=(20, 11),
                         background=c["secundario"], foreground=c["primario"],
                         bordercolor=c["borde"], borderwidth=1, focusthickness=0,
                         relief="flat")
        estilo.map("Secondary.TButton",
                   background=[("pressed", c["borde"]),
                               ("active", c["secundario_hover"])])

    def _registrar_atajos(self) -> None:
        """Asocia los atajos de teclado a las acciones principales."""
        self.raiz.bind_all("<Control-o>", lambda _e: self.abrir_escenario())
        self.raiz.bind_all("<Control-n>", lambda _e: self.mostrar_editor())
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
        archivo.add_command(label="Pantalla de inicio", command=self.mostrar_inicio)
        archivo.add_separator()
        archivo.add_command(label="Salir", accelerator="Ctrl+Q", command=self.salir)
        barra.add_cascade(label="Archivo", menu=archivo)

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

        # Vista de inicio: paneles de operación y referencia centrados.
        self._vista_inicio = ttk.Frame(self._area, style="App.TFrame", padding=(56, 40))
        self._vista_inicio.columnconfigure(0, weight=1)
        self._vista_inicio.rowconfigure(0, weight=1)
        contenido = ttk.Frame(self._vista_inicio, style="App.TFrame")
        contenido.grid(row=0, column=0, sticky="n")
        contenido.columnconfigure(0, weight=1, uniform="paneles", minsize=460)
        contenido.columnconfigure(1, weight=1, uniform="paneles", minsize=460)
        contenido.rowconfigure(0, weight=1)

        self._crear_panel_operacion(contenido)
        self._crear_panel_referencia(contenido)

    @staticmethod
    def _crear_tarjeta(padre: tk.Misc, columna: int, padx: tuple[int, int]) -> ttk.Frame:
        """Crea un panel blanco con borde fino y devuelve su contenedor interno."""
        marco = tk.Frame(padre, bg=COLORES["borde"], bd=0)
        marco.grid(row=0, column=columna, sticky="nsew", padx=padx)
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

    def _crear_panel_referencia(self, padre: tk.Misc) -> None:
        """Panel derecho: codificación de celdas y parámetros del modelo."""
        tarjeta = self._crear_tarjeta(padre, columna=1, padx=(12, 0))
        tarjeta.columnconfigure(1, weight=1)

        ttk.Label(tarjeta, text="REFERENCIA",
                  style="CardEyebrow.TLabel").grid(row=0, column=0, columnspan=2, sticky="w")
        ttk.Label(tarjeta, text="Codificación del escenario",
                  style="SectionTitle.TLabel").grid(row=1, column=0, columnspan=2,
                                                    sticky="w", pady=(4, 16))

        leyenda = (
            (_muestra_color(tarjeta, COLORES["celda_bloqueada"]), "0",
             "Celda bloqueada (pared o fuego letal)"),
            (_muestra_color(tarjeta, COLORES["celda_libre"]), "1",
             "Celda libre y sin contaminación"),
            (_muestra_degradado(tarjeta), "2 – 99",
             "Humo o tóxico; el valor es el costo de transición"),
        )
        for i, (muestra, valor, descripcion) in enumerate(leyenda, start=2):
            muestra.grid(row=i, column=0, sticky="w", pady=5)
            fila = ttk.Frame(tarjeta, style="Card.TFrame")
            fila.grid(row=i, column=1, sticky="w", padx=(12, 0))
            ttk.Label(fila, text=valor, style="Term.TLabel", width=7).pack(side="left")
            ttk.Label(fila, text=descripcion, style="Body.TLabel").pack(side="left")

        ttk.Separator(tarjeta, orient="horizontal").grid(row=5, column=0, columnspan=2,
                                                         sticky="ew", pady=18)

        ttk.Label(tarjeta, text="Parámetros del modelo",
                  style="Subsection.TLabel").grid(row=6, column=0, columnspan=2,
                                                  sticky="w", pady=(0, 8))
        parametros = (
            ("Algoritmo", "Búsqueda de Costo Uniforme (UCS)"),
            ("Tipo", "Búsqueda no informada, óptima y completa"),
            ("Movimientos", "Norte, Sur, Este y Oeste"),
            ("Criterio", "Minimizar el riesgo acumulado g(n)"),
            ("Entorno", "Determinista, estático, discreto y observable"),
        )
        for i, (termino, valor) in enumerate(parametros, start=7):
            ttk.Label(tarjeta, text=termino, style="Term.TLabel").grid(
                row=i, column=0, sticky="w", pady=2)
            ttk.Label(tarjeta, text=valor, style="Body.TLabel").grid(
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
        for otra in (self._vista_inicio, self._editor, self._vista_resultado):
            if otra is not None and otra is not vista:
                otra.grid_remove()
        vista.grid(row=0, column=0, sticky="nsew")
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
        if self._editor is None:
            try:
                # Importación diferida: editor.py reutiliza la paleta de este módulo.
                from .editor import EditorEscenarios
                self._editor = EditorEscenarios(
                    self._area, estado=self._estado,
                    al_calcular=lambda esc, res: self.mostrar_resultado(
                        esc, res, "Escenario diseñado en el editor", desde_editor=True),
                    al_volver=self.mostrar_inicio)
                self._editor.configure(padding=24)
            except Exception as e:
                self._editor = None
                messagebox.showerror(
                    "No fue posible abrir el editor",
                    "Ocurrió un error al iniciar el editor de escenarios.\n\n"
                    f"Detalle técnico: {type(e).__name__}: {e}\n\n"
                    "Verifique que editor.py se encuentre en la carpeta evacuador/, "
                    "junto a app.py.",
                )
                return
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
        try:
            from .resultado import VistaResultado
        except Exception as e:
            messagebox.showerror("No fue posible mostrar el resultado",
                                 f"Detalle técnico: {type(e).__name__}: {e}\n\n"
                                 "Verifique que resultado.py se encuentre en la "
                                 "carpeta evacuador/, junto a app.py.")
            return
        if self._vista_resultado is not None:
            self._vista_resultado.destroy()
        if desde_editor:
            al_editar, texto_editar = self.mostrar_editor, "Volver al editor"
        else:
            al_editar = lambda: self.mostrar_editor(escenario)  # noqa: E731
            texto_editar = "Editar este escenario"
        self._vista_resultado = VistaResultado(
            self._area, escenario, resultado, nombre,
            al_volver=self.mostrar_inicio, al_editar=al_editar, texto_editar=texto_editar)
        self._vista_resultado.configure(padding=24)
        self._mostrar_vista(self._vista_resultado, compacto=True)

    # -- Acciones de la interfaz -------------------------------------------

    def abrir_escenario(self) -> None:
        """Carga un escenario CSV, lo resuelve y muestra la vista de resultado."""
        abrir_explorador_archivos(notificar=self._registrar_progreso,
                                  mostrar=self.mostrar_resultado)

    def _registrar_progreso(self, estado: str, nombre_archivo: str) -> None:
        """Actualiza la barra de estado según el avance del procesamiento.

        Args:
            estado: ``"procesando"``, ``"completado"`` o ``"error"``.
            nombre_archivo: Nombre del archivo CSV en proceso.
        """
        if estado == "procesando":
            self._estado.set(f"Procesando escenario «{nombre_archivo}»…")
            self.raiz.config(cursor="watch")
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

    def mostrar_acerca_de(self) -> None:
        """Muestra la información general del sistema."""
        messagebox.showinfo(
            f"Acerca de {TITULO_APP}",
            f"{TITULO_APP}\nVersión {VERSION_APP}\n\n"
            "Sistema inteligente que calcula la ruta de escape más segura dentro "
            "de una instalación industrial durante un incendio, priorizando "
            "rodear zonas con humo tóxico o fuego.\n\n"
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
