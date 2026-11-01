"""Diálogos de archivo compartidos por las vistas de la interfaz.

PARA LA DEFENSA: aquí está "Guardar como…" (Ctrl+S). Lo usan el editor y la vista de
resultado, así el guardado se escribe una sola vez y siempre produce el formato CSV
que ``io_csv.cargar_csv`` sabe volver a leer."""

from __future__ import annotations

import os
import tkinter as tk
from tkinter import filedialog, messagebox
from typing import Final, Optional

from ..io_csv import guardar_csv
from ..modelos import Escenario

TIPOS_CSV: Final[list[tuple[str, str]]] = [("Archivos CSV", "*.csv")]


def guardar_escenario_como(padre: tk.Misc, escenario: Escenario,
                           nombre_sugerido: str = "escenario_nuevo.csv") -> Optional[str]:
    """Pide una ruta con el diálogo «Guardar como» y escribe el escenario en CSV.

    El archivo usa el mismo formato que :func:`io_csv.cargar_csv`, por lo que
    puede volver a abrirse desde «Abrir escenario» o desde el editor.

    Returns:
        La ruta guardada, o ``None`` si el usuario canceló o hubo un error.
    """
    ventana = padre.winfo_toplevel()
    ruta = filedialog.asksaveasfilename(
        parent=ventana, title="Guardar escenario como CSV", defaultextension=".csv",
        filetypes=TIPOS_CSV, initialfile=nombre_sugerido)
    if not ruta:
        # El diálogo devuelve una ruta vacía cuando se cancela.
        return None
    if not ruta.lower().endswith(".csv"):
        ruta += ".csv"
    try:
        # Si la escritura falla, el diálogo informa el error y permite continuar en la GUI.
        guardar_csv(ruta, escenario)
    except OSError as exc:
        messagebox.showerror("Error al guardar",
                             f"No fue posible guardar «{os.path.basename(ruta)}».\n\n"
                             f"Detalle técnico: {exc}", parent=ventana)
        return None
    return ruta
