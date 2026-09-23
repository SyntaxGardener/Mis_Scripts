#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Fusionar Excel
--------------
Combina varios archivos .xls/.xlsx (cada uno con una sola hoja) en un
único libro nuevo, donde cada archivo original pasa a ser una hoja.

Requisitos (instalar una vez con pip):
    pip install pandas openpyxl xlrd

- pandas y openpyxl: lectura/escritura de .xlsx
- xlrd: necesario solo si vas a leer archivos .xls antiguos (formato binario)
"""

import os
import re
import sys
import subprocess
import tkinter as tk
from tkinter import filedialog, messagebox
import threading

try:
    import pandas as pd
except ImportError:
    pd = None


APP_TITLE = "Fusionar archivos Excel"
WIN_WIDTH = 520
WIN_HEIGHT = 400


def sanitize_sheet_name(name, used_names):
    """Excel: máx 31 caracteres, sin [ ] : * ? / \\ , y nombre único."""
    clean = re.sub(r'[\[\]:*?/\\]', '_', name)
    clean = clean.strip() or "Hoja"
    clean = clean[:31]

    base = clean
    counter = 1
    while clean in used_names:
        suffix = f"_{counter}"
        clean = (base[: 31 - len(suffix)]) + suffix
        counter += 1

    used_names.add(clean)
    return clean


def open_folder_in_explorer(path):
    try:
        if sys.platform.startswith("win"):
            os.startfile(path)  # type: ignore[attr-defined]
        elif sys.platform == "darwin":
            subprocess.Popen(["open", path])
        else:
            subprocess.Popen(["xdg-open", path])
    except Exception:
        pass  # No es crítico si falla; el archivo ya se creó igualmente.


class MergeApp:
    def __init__(self, root):
        self.root = root
        self.files = []

        root.title(APP_TITLE)
        root.resizable(False, False)
        self._center_window()

        root.configure(bg="#f4f5f7")

        container = tk.Frame(root, bg="#f4f5f7")
        container.pack(fill="both", expand=True, padx=20, pady=16)

        title_lbl = tk.Label(
            container,
            text=APP_TITLE,
            font=("Segoe UI", 14, "bold"),
            bg="#f4f5f7",
            fg="#1f2937",
        )
        title_lbl.pack(pady=(0, 4))

        subtitle_lbl = tk.Label(
            container,
            text="Cada archivo seleccionado se convertirá en una hoja del nuevo libro.",
            font=("Segoe UI", 9),
            bg="#f4f5f7",
            fg="#6b7280",
            wraplength=460,
            justify="center",
        )
        subtitle_lbl.pack(pady=(0, 12))

        # Lista de archivos
        list_frame = tk.Frame(container, bg="#f4f5f7")
        list_frame.pack(fill="both", expand=True)

        scrollbar = tk.Scrollbar(list_frame)
        scrollbar.pack(side="right", fill="y")

        self.listbox = tk.Listbox(
            list_frame,
            yscrollcommand=scrollbar.set,
            font=("Segoe UI", 9),
            selectmode=tk.EXTENDED,
            height=10,
            relief="solid",
            borderwidth=1,
        )
        self.listbox.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=self.listbox.yview)

        # Botones de gestión de archivos
        btn_row = tk.Frame(container, bg="#f4f5f7")
        btn_row.pack(fill="x", pady=(10, 6))

        self.add_btn = tk.Button(
            btn_row, text="Añadir archivos...", command=self.add_files,
            bg="#ffffff", relief="solid", borderwidth=1, padx=10, pady=4,
        )
        self.add_btn.pack(side="left")

        self.remove_btn = tk.Button(
            btn_row, text="Quitar seleccionado(s)", command=self.remove_selected,
            bg="#ffffff", relief="solid", borderwidth=1, padx=10, pady=4,
        )
        self.remove_btn.pack(side="left", padx=(8, 0))

        self.clear_btn = tk.Button(
            btn_row, text="Limpiar lista", command=self.clear_list,
            bg="#ffffff", relief="solid", borderwidth=1, padx=10, pady=4,
        )
        self.clear_btn.pack(side="left", padx=(8, 0))

        # Estado
        self.status_lbl = tk.Label(
            container, text="", font=("Segoe UI", 9), bg="#f4f5f7", fg="#6b7280"
        )
        self.status_lbl.pack(pady=(6, 6))

        # Botón principal
        self.merge_btn = tk.Button(
            container,
            text="Fusionar y guardar como...",
            command=self.start_merge,
            bg="#2563eb",
            fg="white",
            activebackground="#1d4ed8",
            activeforeground="white",
            font=("Segoe UI", 10, "bold"),
            relief="flat",
            padx=12,
            pady=8,
        )
        self.merge_btn.pack(fill="x", pady=(4, 0))

    def _center_window(self):
        self.root.update_idletasks()
        screen_w = self.root.winfo_screenwidth()
        x = (screen_w - WIN_WIDTH) // 2
        y = 5  # pegado a 5 px del borde superior
        self.root.geometry(f"{WIN_WIDTH}x{WIN_HEIGHT}+{x}+{y}")

    def add_files(self):
        paths = filedialog.askopenfilenames(
            title="Selecciona archivos Excel",
            filetypes=[("Archivos Excel", "*.xls *.xlsx"), ("Todos los archivos", "*.*")],
        )
        for p in paths:
            if p not in self.files:
                self.files.append(p)
                self.listbox.insert(tk.END, os.path.basename(p))
        self._update_status()

    def remove_selected(self):
        selected = list(self.listbox.curselection())
        for idx in reversed(selected):
            self.listbox.delete(idx)
            del self.files[idx]
        self._update_status()

    def clear_list(self):
        self.listbox.delete(0, tk.END)
        self.files.clear()
        self._update_status()

    def _update_status(self):
        n = len(self.files)
        self.status_lbl.config(text=f"{n} archivo(s) seleccionado(s)" if n else "")

    def start_merge(self):
        if pd is None:
            messagebox.showerror(
                APP_TITLE,
                "Faltan dependencias. Instala con:\n\npip install pandas openpyxl xlrd",
            )
            return

        if not self.files:
            messagebox.showwarning(APP_TITLE, "Añade al menos un archivo antes de fusionar.")
            return

        dest_path = filedialog.asksaveasfilename(
            title="Guardar libro fusionado como",
            defaultextension=".xlsx",
            filetypes=[("Libro de Excel", "*.xlsx")],
            initialfile="fusionado.xlsx",
        )
        if not dest_path:
            return

        self._set_ui_enabled(False)
        self.status_lbl.config(text="Fusionando archivos, por favor espera...")

        thread = threading.Thread(target=self._merge_worker, args=(dest_path,), daemon=True)
        thread.start()

    def _set_ui_enabled(self, enabled):
        state = tk.NORMAL if enabled else tk.DISABLED
        self.add_btn.config(state=state)
        self.remove_btn.config(state=state)
        self.clear_btn.config(state=state)
        self.merge_btn.config(state=state)

    def _merge_worker(self, dest_path):
        try:
            used_names = set()
            with pd.ExcelWriter(dest_path, engine="openpyxl") as writer:
                for path in self.files:
                    ext = os.path.splitext(path)[1].lower()
                    engine = "xlrd" if ext == ".xls" else "openpyxl"
                    df = pd.read_excel(path, engine=engine, sheet_name=0)

                    base_name = os.path.splitext(os.path.basename(path))[0]
                    sheet_name = sanitize_sheet_name(base_name, used_names)

                    df.to_excel(writer, sheet_name=sheet_name, index=False)

            self.root.after(0, self._on_merge_success, dest_path)
        except Exception as e:
            self.root.after(0, self._on_merge_error, str(e))

    def _on_merge_success(self, dest_path):
        self._set_ui_enabled(True)
        self.status_lbl.config(text="¡Fusión completada!")
        folder = os.path.dirname(os.path.abspath(dest_path))
        open_folder_in_explorer(folder)
        messagebox.showinfo(APP_TITLE, f"Archivo creado correctamente:\n{dest_path}")

    def _on_merge_error(self, error_msg):
        self._set_ui_enabled(True)
        self.status_lbl.config(text="")
        messagebox.showerror(APP_TITLE, f"Ocurrió un error al fusionar:\n\n{error_msg}")


def main():
    root = tk.Tk()
    app = MergeApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
