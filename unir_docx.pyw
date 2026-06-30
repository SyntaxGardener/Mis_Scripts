#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Unir DOCX
---------
Aplicacion con interfaz grafica para unir varios documentos Word (.docx)
en uno solo, conservando el formato de cada documento original.

Dependencias necesarias (instalar una sola vez):
    pip install python-docx docxcompose

Como usarlo:
    1. Pulsa "Anadir documentos..." y selecciona los .docx que quieras unir.
    2. Ordena la lista con "Subir" / "Bajar" si hace falta (se unen en ese orden).
    3. Opcionalmente marca "Salto de pagina entre documentos".
    4. Pulsa "Unir y guardar...", elige nombre y carpeta de destino.
    5. Si quieres, marca "Abrir carpeta al terminar".
"""

import os
import sys
import subprocess
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

try:
    from docxcompose.composer import Composer
    from docx import Document
except ImportError:
    Document = None
    Composer = None


class UnirDocxApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Unir documentos Word")
        self.root.resizable(False, False)

        self.files = []  # lista de rutas .docx en orden de union

        self._build_ui()
        self._center_top5()

    # ------------------------------------------------------------------ UI
    def _build_ui(self):
        pad = {"padx": 10, "pady": 6}

        main = ttk.Frame(self.root, padding=12)
        main.grid(row=0, column=0, sticky="nsew")

        title = ttk.Label(main, text="Unir documentos Word (.docx)",
                           font=("Segoe UI", 12, "bold"))
        title.grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 10))

        # Lista de archivos
        list_frame = ttk.Frame(main)
        list_frame.grid(row=1, column=0, columnspan=3, sticky="nsew")

        self.listbox = tk.Listbox(list_frame, width=58, height=10,
                                   selectmode=tk.EXTENDED, activestyle="dotbox")
        self.listbox.grid(row=0, column=0, sticky="nsew")

        scrollbar = ttk.Scrollbar(list_frame, orient="vertical",
                                   command=self.listbox.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.listbox.configure(yscrollcommand=scrollbar.set)

        # Botones de gestion de la lista
        btns_frame = ttk.Frame(main)
        btns_frame.grid(row=2, column=0, columnspan=3, sticky="ew", pady=(8, 4))

        ttk.Button(btns_frame, text="Anadir documentos...",
                   command=self.add_files).pack(side="left")
        ttk.Button(btns_frame, text="Quitar seleccionados",
                   command=self.remove_selected).pack(side="left", padx=6)
        ttk.Button(btns_frame, text="Subir",
                   command=lambda: self.move_selected(-1)).pack(side="left")
        ttk.Button(btns_frame, text="Bajar",
                   command=lambda: self.move_selected(1)).pack(side="left", padx=6)
        ttk.Button(btns_frame, text="Vaciar lista",
                   command=self.clear_list).pack(side="left")

        # Opciones
        opts_frame = ttk.Frame(main)
        opts_frame.grid(row=3, column=0, columnspan=3, sticky="w", pady=(6, 4))

        self.page_break_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(opts_frame, text="Salto de pagina entre documentos",
                         variable=self.page_break_var).pack(side="left")

        self.open_folder_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(opts_frame, text="Abrir carpeta al terminar",
                         variable=self.open_folder_var).pack(side="left", padx=12)

        # Boton principal
        action_frame = ttk.Frame(main)
        action_frame.grid(row=4, column=0, columnspan=3, sticky="ew", pady=(10, 0))

        self.unir_btn = ttk.Button(action_frame, text="Unir y guardar...",
                                    command=self.unir_y_guardar)
        self.unir_btn.pack(fill="x")

        # Barra de estado
        self.status_var = tk.StringVar(value="Anade dos o mas documentos para empezar.")
        status = ttk.Label(main, textvariable=self.status_var,
                            foreground="#555555")
        status.grid(row=5, column=0, columnspan=3, sticky="w", pady=(8, 0))

    def _center_top5(self):
        self.root.update_idletasks()
        width = self.root.winfo_reqwidth()
        height = self.root.winfo_reqheight()
        screen_width = self.root.winfo_screenwidth()
        x = (screen_width - width) // 2
        y = 5  # a 5 pixeles del borde superior de la pantalla
        self.root.geometry(f"{width}x{height}+{x}+{y}")

    # ------------------------------------------------------------- acciones
    def add_files(self):
        paths = filedialog.askopenfilenames(
            title="Selecciona documentos Word",
            filetypes=[("Documentos Word", "*.docx")]
        )
        if not paths:
            return
        for p in paths:
            if p not in self.files:
                self.files.append(p)
                self.listbox.insert(tk.END, os.path.basename(p))
        self._update_status()

    def remove_selected(self):
        seleccion = list(self.listbox.curselection())
        if not seleccion:
            return
        for idx in reversed(seleccion):
            self.listbox.delete(idx)
            del self.files[idx]
        self._update_status()

    def move_selected(self, direction):
        seleccion = list(self.listbox.curselection())
        if not seleccion:
            return
        indices = seleccion if direction < 0 else list(reversed(seleccion))
        for idx in indices:
            new_idx = idx + direction
            if 0 <= new_idx < len(self.files):
                self.files[idx], self.files[new_idx] = self.files[new_idx], self.files[idx]
                texto = self.listbox.get(idx)
                self.listbox.delete(idx)
                self.listbox.insert(new_idx, texto)
                self.listbox.selection_set(new_idx)

    def clear_list(self):
        self.files.clear()
        self.listbox.delete(0, tk.END)
        self._update_status()

    def _update_status(self):
        n = len(self.files)
        if n == 0:
            self.status_var.set("Anade dos o mas documentos para empezar.")
        elif n == 1:
            self.status_var.set("Anade al menos un documento mas.")
        else:
            self.status_var.set(f"{n} documentos listos para unir.")

    def unir_y_guardar(self):
        if Document is None or Composer is None:
            messagebox.showerror(
                "Faltan dependencias",
                "Este script necesita las librerias 'python-docx' y 'docxcompose'.\n\n"
                "Instalalas abriendo una terminal y ejecutando:\n"
                "pip install python-docx docxcompose"
            )
            return

        if len(self.files) < 2:
            messagebox.showwarning("Faltan documentos",
                                    "Anade al menos dos documentos para unir.")
            return

        destino = filedialog.asksaveasfilename(
            title="Guardar documento unido como...",
            defaultextension=".docx",
            filetypes=[("Documento Word", "*.docx")],
            initialfile="documento_unido.docx"
        )
        if not destino:
            return

        try:
            self.unir_btn.config(state="disabled")
            self.status_var.set("Uniendo documentos, espera un momento...")
            self.root.update_idletasks()

            master = Document(self.files[0])
            composer = Composer(master)

            for ruta in self.files[1:]:
                if self.page_break_var.get():
                    master.add_page_break()
                doc_siguiente = Document(ruta)
                composer.append(doc_siguiente)

            composer.save(destino)

        except Exception as exc:
            messagebox.showerror("Error al unir documentos", str(exc))
            self.status_var.set("Ha ocurrido un error. Revisa los documentos e intentalo de nuevo.")
            self.unir_btn.config(state="normal")
            return

        self.unir_btn.config(state="normal")
        self.status_var.set(f"Documento guardado correctamente en:\n{destino}")
        messagebox.showinfo("Listo", f"Documento unido guardado en:\n{destino}")

        if self.open_folder_var.get():
            self._abrir_carpeta(os.path.dirname(destino))

    @staticmethod
    def _abrir_carpeta(carpeta):
        try:
            if sys.platform.startswith("win"):
                os.startfile(carpeta)
            elif sys.platform == "darwin":
                subprocess.run(["open", carpeta])
            else:
                subprocess.run(["xdg-open", carpeta])
        except Exception:
            pass


def main():
    root = tk.Tk()
    try:
        style = ttk.Style()
        if "vista" in style.theme_names():
            style.theme_use("vista")
        elif "clam" in style.theme_names():
            style.theme_use("clam")
    except Exception:
        pass

    app = UnirDocxApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
