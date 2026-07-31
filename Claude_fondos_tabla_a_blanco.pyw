"""
Convertidor de fondos de tabla a blanco (para impresión en blanco y negro)
---------------------------------------------------------------------------
Convierte todos los fondos de color de las tablas y cajas de uno o varios
documentos .docx a blanco, y ajusta el texto blanco a negro para que las
cabeceras de las cajas (antes blancas sobre fondo de color) se sigan
leyendo bien.

Requiere: python-docx  (pip install python-docx)
Uso: haz doble clic en el archivo (no requiere consola).
"""

import os
import sys
import platform
import subprocess
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

try:
    from docx import Document
    from docx.oxml.ns import qn
except ImportError:
    Document = None


# ----------------------------------------------------------------------
# Lógica de conversión
# ----------------------------------------------------------------------

def _set_shading_white(shd_element):
    shd_element.set(qn('w:val'), 'clear')
    shd_element.set(qn('w:color'), 'auto')
    shd_element.set(qn('w:fill'), 'FFFFFF')


def convert_backgrounds_to_white(input_path, output_path):
    """
    Pone en blanco todos los fondos de color (tablas y párrafos) de un
    .docx y corrige el texto blanco a negro. Guarda el resultado en
    output_path. Devuelve el número de sombreados modificados.
    """
    doc = Document(input_path)
    count = 0

    body = doc.element.body

    # Fondos de color (tablas y párrafos con sombreado)
    for shd in body.iter(qn('w:shd')):
        fill = shd.get(qn('w:fill'))
        if fill and fill.upper() not in ('FFFFFF', 'AUTO'):
            _set_shading_white(shd)
            count += 1

    # Texto blanco -> negro, para que siga siendo legible sin el fondo
    for color in body.iter(qn('w:color')):
        val = color.get(qn('w:val'))
        if val and val.upper() == 'FFFFFF':
            color.set(qn('w:val'), '000000')

    doc.save(output_path)
    return count


# ----------------------------------------------------------------------
# Interfaz gráfica
# ----------------------------------------------------------------------

class App:
    BG = "#F4F6F7"
    PRIMARY = "#1F4E5F"
    ACCENT = "#2C5F6F"

    def __init__(self, root):
        self.root = root
        self.files = []
        self.output_dir = tk.StringVar()
        self.suffix = tk.StringVar(value="_BN")

        root.title("Fondos de tabla a blanco (para imprimir en B/N)")
        root.configure(bg=self.BG)
        root.resizable(False, False)

        self._build_ui()
        self._center_window()

    # -- construcción de la interfaz -----------------------------------
    def _build_ui(self):
        pad = {"padx": 16, "pady": 8}

        title = tk.Label(
            self.root, text="Fondos de tabla a blanco",
            font=("Segoe UI", 15, "bold"), fg=self.PRIMARY, bg=self.BG,
        )
        title.pack(pady=(18, 2))

        subtitle = tk.Label(
            self.root,
            text="Convierte los fondos de color de las tablas a blanco,\n"
                 "para que se impriman con nitidez en blanco y negro.",
            font=("Segoe UI", 9), fg="#555555", bg=self.BG, justify="center",
        )
        subtitle.pack(pady=(0, 12))

        # --- Selección de archivos ---
        files_frame = tk.LabelFrame(
            self.root, text=" Documentos .docx ", font=("Segoe UI", 9, "bold"),
            fg=self.PRIMARY, bg=self.BG, bd=1, relief="groove",
        )
        files_frame.pack(fill="x", **pad)

        list_container = tk.Frame(files_frame, bg=self.BG)
        list_container.pack(fill="both", padx=8, pady=8)

        scrollbar = tk.Scrollbar(list_container)
        scrollbar.pack(side="right", fill="y")

        self.listbox = tk.Listbox(
            list_container, width=62, height=7,
            yscrollcommand=scrollbar.set, font=("Segoe UI", 9),
            selectmode="extended", relief="solid", bd=1,
        )
        self.listbox.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=self.listbox.yview)

        btns_frame = tk.Frame(files_frame, bg=self.BG)
        btns_frame.pack(fill="x", padx=8, pady=(0, 8))

        self._make_button(btns_frame, "Añadir archivos...", self.add_files).pack(side="left")
        self._make_button(btns_frame, "Quitar seleccionados", self.remove_selected).pack(side="left", padx=6)
        self._make_button(btns_frame, "Vaciar lista", self.clear_files).pack(side="left")

        # --- Carpeta de destino ---
        out_frame = tk.LabelFrame(
            self.root, text=" Carpeta de destino ", font=("Segoe UI", 9, "bold"),
            fg=self.PRIMARY, bg=self.BG, bd=1, relief="groove",
        )
        out_frame.pack(fill="x", **pad)

        out_row = tk.Frame(out_frame, bg=self.BG)
        out_row.pack(fill="x", padx=8, pady=8)

        self.out_entry = tk.Entry(
            out_row, textvariable=self.output_dir, font=("Segoe UI", 9),
            relief="solid", bd=1,
        )
        self.out_entry.pack(side="left", fill="x", expand=True, ipady=3)
        self._make_button(out_row, "Elegir...", self.choose_output_dir).pack(side="left", padx=(6, 0))

        # --- Nombre de los archivos resultantes ---
        name_frame = tk.LabelFrame(
            self.root, text=" Nombre de los archivos resultantes ",
            font=("Segoe UI", 9, "bold"), fg=self.PRIMARY, bg=self.BG,
            bd=1, relief="groove",
        )
        name_frame.pack(fill="x", **pad)

        name_row = tk.Frame(name_frame, bg=self.BG)
        name_row.pack(fill="x", padx=8, pady=8)

        tk.Label(
            name_row, text="Se añadirá este sufijo al nombre original:",
            font=("Segoe UI", 9), bg=self.BG,
        ).pack(side="left")

        suffix_entry = tk.Entry(
            name_row, textvariable=self.suffix, font=("Segoe UI", 9),
            width=14, relief="solid", bd=1, justify="center",
        )
        suffix_entry.pack(side="left", padx=8, ipady=3)

        tk.Label(
            name_row, text="Ej.: Apuntes_BN.docx",
            font=("Segoe UI", 8, "italic"), fg="#777777", bg=self.BG,
        ).pack(side="left")

        # --- Botón de proceso y estado ---
        action_frame = tk.Frame(self.root, bg=self.BG)
        action_frame.pack(fill="x", **pad)

        self.process_btn = tk.Button(
            action_frame, text="Convertir documentos", command=self.start_processing,
            bg=self.PRIMARY, fg="white", activebackground=self.ACCENT,
            activeforeground="white", font=("Segoe UI", 10, "bold"),
            relief="flat", padx=14, pady=8, cursor="hand2",
        )
        self.process_btn.pack(fill="x")

        self.status_label = tk.Label(
            self.root, text="", font=("Segoe UI", 9), fg="#555555", bg=self.BG,
        )
        self.status_label.pack(pady=(4, 4))

        self.progress = ttk.Progressbar(self.root, mode="determinate", length=440)
        self.progress.pack(pady=(0, 16))

        if Document is None:
            messagebox.showerror(
                "Falta una librería",
                "Este programa necesita la librería 'python-docx'.\n\n"
                "Instálala abriendo una terminal y ejecutando:\n"
                "pip install python-docx",
            )

    def _make_button(self, parent, text, command):
        return tk.Button(
            parent, text=text, command=command,
            bg="#E8EEF0", fg=self.PRIMARY, activebackground="#D7E2E5",
            font=("Segoe UI", 9), relief="flat", padx=10, pady=4, cursor="hand2",
        )

    # -- centrado de la ventana -----------------------------------------
    def _center_window(self):
        self.root.update_idletasks()
        w = self.root.winfo_width()
        h = self.root.winfo_height()
        screen_w = self.root.winfo_screenwidth()
        x = (screen_w - w) // 2
        y = 5  # borde superior a 5 píxeles del borde de la pantalla
        self.root.geometry(f"{w}x{h}+{x}+{y}")

    # -- acciones de archivos --------------------------------------------
    def add_files(self):
        paths = filedialog.askopenfilenames(
            title="Selecciona los documentos .docx",
            filetypes=[("Documentos Word", "*.docx")],
        )
        for p in paths:
            if p not in self.files:
                self.files.append(p)
                self.listbox.insert("end", os.path.basename(p))

    def remove_selected(self):
        selected = list(self.listbox.curselection())
        for index in reversed(selected):
            self.listbox.delete(index)
            del self.files[index]

    def clear_files(self):
        self.listbox.delete(0, "end")
        self.files.clear()

    def choose_output_dir(self):
        folder = filedialog.askdirectory(title="Elige la carpeta de destino")
        if folder:
            self.output_dir.set(folder)

    # -- procesamiento -----------------------------------------------------
    def start_processing(self):
        if Document is None:
            messagebox.showerror(
                "Falta una librería",
                "Instala primero python-docx:\npip install python-docx",
            )
            return

        if not self.files:
            messagebox.showwarning("Sin archivos", "Añade al menos un documento .docx.")
            return

        out_dir = self.output_dir.get().strip()
        if not out_dir:
            messagebox.showwarning("Sin carpeta", "Elige una carpeta de destino.")
            return
        if not os.path.isdir(out_dir):
            try:
                os.makedirs(out_dir, exist_ok=True)
            except OSError:
                messagebox.showerror("Error", "No se ha podido crear la carpeta de destino.")
                return

        self.process_btn.config(state="disabled")
        self.progress["value"] = 0
        self.progress["maximum"] = len(self.files)
        self.status_label.config(text="Procesando...")

        thread = threading.Thread(target=self._process_files, args=(out_dir,), daemon=True)
        thread.start()

    def _process_files(self, out_dir):
        suffix = self.suffix.get().strip()
        errores = []
        procesados = 0

        for i, path in enumerate(self.files, start=1):
            base = os.path.splitext(os.path.basename(path))[0]
            out_name = f"{base}{suffix}.docx"
            out_path = os.path.join(out_dir, out_name)
            try:
                convert_backgrounds_to_white(path, out_path)
                procesados += 1
            except Exception as exc:
                errores.append(f"{os.path.basename(path)}: {exc}")

            self.root.after(0, self._update_progress, i, os.path.basename(path))

        self.root.after(0, self._finish_processing, procesados, errores, out_dir)

    def _update_progress(self, i, filename):
        self.progress["value"] = i
        self.status_label.config(text=f"Procesado: {filename}")

    def _finish_processing(self, procesados, errores, out_dir):
        self.process_btn.config(state="normal")

        if errores:
            self.status_label.config(text=f"Terminado con incidencias ({procesados} correctos).")
            messagebox.showwarning(
                "Terminado con incidencias",
                f"Se procesaron {procesados} documento(s) correctamente.\n\n"
                "No se pudieron convertir:\n" + "\n".join(errores),
            )
        else:
            self.status_label.config(text=f"Listo. {procesados} documento(s) convertidos.")
            messagebox.showinfo(
                "Conversión completada",
                f"Se han convertido {procesados} documento(s) correctamente.",
            )

        self._open_folder(out_dir)

    @staticmethod
    def _open_folder(path):
        try:
            system = platform.system()
            if system == "Windows":
                os.startfile(path)  # noqa
            elif system == "Darwin":
                subprocess.Popen(["open", path])
            else:
                subprocess.Popen(["xdg-open", path])
        except Exception:
            pass


def main():
    root = tk.Tk()
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
