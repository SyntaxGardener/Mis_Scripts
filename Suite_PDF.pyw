# -*- coding: utf-8 -*-
import os
import fitz  # PyMuPDF
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from PIL import Image, ImageTk
import win32com.client
import pythoncom
from pdf2docx import Converter
from pypdf import PdfReader, PdfWriter
import re
import tempfile
import subprocess
import glob
from io import BytesIO


def _buscar_ghostscript():
    """Devuelve la ruta al ejecutable de Ghostscript o None si no se encuentra."""
    base = os.path.dirname(os.path.abspath(__file__))
    local = os.path.join(base, "gs", "bin", "gswin64c.exe")
    if os.path.exists(local):
        return local
    patrones = [
        r"C:\Program Files\gs\gs*\bin\gswin64c.exe",
        r"C:\Program Files (x86)\gs\gs*\bin\gswin32c.exe",
        r"C:\gs\gs*\bin\gswin64c.exe",
    ]
    for p in patrones:
        encontrados = glob.glob(p)
        if encontrados:
            return sorted(encontrados)[-1]
    import shutil
    for nombre in ("gswin64c", "gswin32c", "gs"):
        ruta = shutil.which(nombre)
        if ruta:
            return ruta
    return None


class SuiteDocumental:
    def __init__(self, root):
        self.root = root
        self.nombre_suite = "Suite PDF"
        self.root.title(self.nombre_suite)

        ancho_ventana = 775
        alto_ventana = 780
        ancho_pantalla = self.root.winfo_screenwidth()
        pos_x = (ancho_pantalla // 2) - (ancho_ventana // 2)
        self.root.geometry(f"{ancho_ventana}x{alto_ventana}+{pos_x}+0")

        try:
            self.icono = tk.PhotoImage(file="pdf-icono.png")
            self.root.iconphoto(False, self.icono)
        except:
            pass

        self.root.configure(bg="#f0f0fa")
        self.archivos_cargados = []
        self.ruta_pdf_unico = ""
        self.pag_selec = set()
        self.rot_map   = {}

        # ── Estilos — uno por fila para poder "apagar" el resalte ─────────────
        style = ttk.Style()
        style.theme_use("default")

        COLOR_SEL_BG  = "#dddcf7"
        COLOR_SEL_FG  = "#2d2580"
        COLOR_IDLE_BG = "#f0f0fa"
        COLOR_IDLE_FG = "#555"

        def _cfg_nb(name):
            style.configure(f"{name}.TNotebook",
                            background="#f0f0fa", borderwidth=0,
                            relief="flat", tabmargins=[4, 4, 0, 0])
            style.configure(f"{name}.TNotebook.Tab",
                            background="#f0f0fa", foreground="#555",
                            padding=[14, 7], font=("Arial", 9),
                            borderwidth=1, relief="flat",
                            focuscolor="#dddcf7")

        _cfg_nb("NB1")
        _cfg_nb("NB2")

        def _activar_nb1():
            style.map("NB1.TNotebook.Tab",
                      background=[("selected", COLOR_SEL_BG), ("active", "#e8e8f5")],
                      foreground=[("selected", COLOR_SEL_FG), ("active", "#4a3fb5")],
                      font=[("selected", ("Arial", 9, "bold"))])
            style.map("NB2.TNotebook.Tab",
                      background=[("selected", COLOR_IDLE_BG), ("active", "#e8e8f5")],
                      foreground=[("selected", COLOR_IDLE_FG), ("active", "#4a3fb5")],
                      font=[("selected", ("Arial", 9))])

        def _activar_nb2():
            style.map("NB1.TNotebook.Tab",
                      background=[("selected", COLOR_IDLE_BG), ("active", "#e8e8f5")],
                      foreground=[("selected", COLOR_IDLE_FG), ("active", "#4a3fb5")],
                      font=[("selected", ("Arial", 9))])
            style.map("NB2.TNotebook.Tab",
                      background=[("selected", COLOR_SEL_BG), ("active", "#e8e8f5")],
                      foreground=[("selected", COLOR_SEL_FG), ("active", "#4a3fb5")],
                      font=[("selected", ("Arial", 9, "bold"))])

        TABS = [
            ("📷 Img→PDF",      self.mostrar_img_to_pdf),
            ("🖼️ PDF→Img",      self.mostrar_p_to_img),
            ("📄 Word→PDF",     self.mostrar_w_to_p),
            ("📝 PDF→Word",     self.mostrar_p_to_w),
            ("✂️ Extractor",    self.mostrar_extractor),
            ("🔗 Unificador",   self.mostrar_unificador),
            ("🗜️ Compresor",    self.mostrar_compresor),
            ("🔍 Texto",        self.mostrar_ocr),
            ("🔐 Poner clave",  self.mostrar_proteccion),
            ("🔓 Quitar clave", self.mostrar_desproteccion),
            ("🔢 Marcas",       self.mostrar_marcas),
        ]
        mitad = (len(TABS) + 1) // 2

        self.main_frame = tk.Frame(root, bg="#fafafa", padx=30, pady=20)

        self._nb1 = ttk.Notebook(root, style="NB1.TNotebook", height=0)
        self._nb2 = ttk.Notebook(root, style="NB2.TNotebook", height=0)

        self._refs = []
        for texto, _ in TABS[:mitad]:
            f = tk.Frame(self._nb1, height=0)
            self._nb1.add(f, text=f"  {texto}  ")
            self._refs.append(f)
        for texto, _ in TABS[mitad:]:
            f = tk.Frame(self._nb2, height=0)
            self._nb2.add(f, text=f"  {texto}  ")
            self._refs.append(f)

        self._nb1.pack(fill="x")
        self._nb2.pack(fill="x")
        tk.Frame(root, bg="#cccaf0", height=1).pack(fill="x")
        self.main_frame.pack(fill="both", expand=True)

        self._bloquear = False

        def _cargar(global_idx):
            for w in self.main_frame.winfo_children():
                w.destroy()
            self.archivos_cargados = []
            self.ruta_pdf_unico    = ""
            TABS[global_idx][1]()

        def _on_nb1(event):
            if self._bloquear:
                return
            _activar_nb1()
            _cargar(self._nb1.index(self._nb1.select()))

        def _on_nb2(event):
            if self._bloquear:
                return
            _activar_nb2()
            _cargar(mitad + self._nb2.index(self._nb2.select()))

        self._nb1.bind("<<NotebookTabChanged>>", _on_nb1)
        self._nb2.bind("<<NotebookTabChanged>>", _on_nb2)

        # También capturar clic directo (por si la pestaña ya estaba seleccionada)
        def _clic_nb1(event):
            tab = self._nb1.identify(event.x, event.y)
            if tab == "label":
                idx = self._nb1.index(f"@{event.x},{event.y}")
                _activar_nb1()
                self._bloquear = True
                self._nb1.select(idx)
                self._nb2.select(0)
                self._bloquear = False
                _cargar(idx)

        def _clic_nb2(event):
            tab = self._nb2.identify(event.x, event.y)
            if tab == "label":
                idx = self._nb2.index(f"@{event.x},{event.y}")
                _activar_nb2()
                self._bloquear = True
                self._nb2.select(idx)
                self._nb1.select(0)
                self._bloquear = False
                _cargar(mitad + idx)

        self._nb1.bind("<Button-1>", _clic_nb1)
        self._nb2.bind("<Button-1>", _clic_nb2)

        # Arranque: nb1 activo, nb2 sin resalte
        _activar_nb1()
        self._bloquear = True
        self._nb1.select(0)
        self._nb2.select(0)
        self._bloquear = False
        _cargar(0)

    # ══════════════════════════════════════════════════════════════════════════
    #  HELPERS REUTILIZABLES
    # ══════════════════════════════════════════════════════════════════════════

    def limpiar_pantalla(self, titulo):
        for w in self.main_frame.winfo_children():
            w.destroy()
        self.archivos_cargados = []
        self.ruta_pdf_unico    = ""
        tk.Label(self.main_frame, text=titulo, font=("Arial", 16, "bold"),
                 bg="#fafafa", fg="#2d2580").pack(side="top", anchor="w", pady=(0, 15))

    def _checkbox_abrir(self, parent):
        """Devuelve un BooleanVar con el checkbox 'Abrir carpeta al finalizar'."""
        var = tk.BooleanVar(value=True)
        tk.Checkbutton(parent, text="📂  Abrir carpeta de destino al finalizar",
                       variable=var, bg="#fafafa", font=("Arial", 9)).pack(anchor="w", pady=3)
        return var

    def _abrir_carpeta(self, ruta_archivo_o_carpeta, var):
        """Abre en el explorador la carpeta si la opción está activa."""
        if var.get():
            if os.path.isdir(ruta_archivo_o_carpeta):
                carpeta = ruta_archivo_o_carpeta
            else:
                carpeta = os.path.dirname(ruta_archivo_o_carpeta)
            os.startfile(carpeta)

    def _lista_con_controles(self, parent, altura=9):
        """
        Crea un Listbox con scrollbar y botones ▲ ▼ ❌ al lado.
        Devuelve el Listbox.
        """
        frame = tk.Frame(parent, bg="#fafafa")
        frame.pack(fill="both", expand=True, pady=5)

        lista = tk.Listbox(frame, height=altura, font=("Arial", 10),
                           selectbackground="#3498db")
        lista.pack(side="left", fill="both", expand=True)

        sb = tk.Scrollbar(frame, orient="vertical", command=lista.yview)
        sb.pack(side="left", fill="y")
        lista.config(yscrollcommand=sb.set)

        btn_f = tk.Frame(frame, bg="#fafafa")
        btn_f.pack(side="left", padx=5)
        tk.Button(btn_f, text="▲", width=3,
                  command=lambda: self._subir(lista)).pack(pady=2)
        tk.Button(btn_f, text="▼", width=3,
                  command=lambda: self._bajar(lista)).pack(pady=2)
        tk.Button(btn_f, text="❌", width=3, fg="red",
                  command=lambda: self._eliminar(lista)).pack(pady=10)
        return lista

    def _subir(self, lista):
        sel = lista.curselection()
        if not sel or sel[0] == 0:
            return
        i = sel[0]
        self.archivos_cargados[i], self.archivos_cargados[i - 1] = (
            self.archivos_cargados[i - 1], self.archivos_cargados[i])
        self._refresh(lista)
        lista.selection_set(i - 1)

    def _bajar(self, lista):
        sel = lista.curselection()
        if not sel or sel[0] == len(self.archivos_cargados) - 1:
            return
        i = sel[0]
        self.archivos_cargados[i], self.archivos_cargados[i + 1] = (
            self.archivos_cargados[i + 1], self.archivos_cargados[i])
        self._refresh(lista)
        lista.selection_set(i + 1)

    def _eliminar(self, lista):
        sel = lista.curselection()
        if not sel:
            return
        self.archivos_cargados.pop(sel[0])
        self._refresh(lista)

    def _refresh(self, lista):
        lista.delete(0, tk.END)
        for f in self.archivos_cargados:
            lista.insert(tk.END, os.path.basename(f))

    def _add_files(self, tipos, lista):
        fs = filedialog.askopenfilenames(filetypes=tipos)
        if fs:
            for f in fs:
                if f not in self.archivos_cargados:
                    self.archivos_cargados.append(f)
            self._refresh(lista)

    def sel_pdf_simple(self):
        f = filedialog.askopenfilename(filetypes=[("PDF", "*.pdf")])
        if f:
            self.ruta_pdf_unico = f
            self.lbl_info.config(text=os.path.basename(f), fg="#2d2580")

    # ══════════════════════════════════════════════════════════════════════════
    #  INICIO
    # ══════════════════════════════════════════════════════════════════════════

    # ══════════════════════════════════════════════════════════════════════════
    #  📷  IMÁGENES A PDF  — miniaturas, reordenar, eliminar, nombre sugerido
    # ══════════════════════════════════════════════════════════════════════════

    def mostrar_img_to_pdf(self):
        self.limpiar_pantalla("📷 Imágenes a PDF")

        f_btns = tk.Frame(self.main_frame, bg="#fafafa")
        f_btns.pack(fill="x")
        tk.Button(f_btns, text="➕ Añadir imágenes",
                  command=lambda: self._add_img(lista),
                  bg="#2980b9", fg="white").pack(side="left", expand=True, fill="x", padx=2)
        tk.Button(f_btns, text="🗑️ Vaciar lista",
                  command=lambda: [self.archivos_cargados.clear(), self._refresh(lista)],
                  bg="#888780", fg="white").pack(side="left", expand=True, fill="x", padx=2)

        # Panel: lista + previsualización
        panel = tk.Frame(self.main_frame, bg="#fafafa")
        panel.pack(fill="both", expand=True, pady=5)

        # Izquierda: lista con controles
        f_izq = tk.Frame(panel, bg="#fafafa")
        f_izq.pack(side="left", fill="both", expand=True)
        tk.Label(f_izq, text="Imágenes (en orden):", bg="#fafafa",
                 font=("Arial", 9)).pack(anchor="w")

        lista_cont = tk.Frame(f_izq, bg="#fafafa")
        lista_cont.pack(fill="both", expand=True)
        lista = tk.Listbox(lista_cont, height=10, font=("Arial", 10),
                           selectbackground="#3498db", exportselection=False)
        lista.pack(side="left", fill="both", expand=True)
        sb = tk.Scrollbar(lista_cont, command=lista.yview)
        sb.pack(side="left", fill="y")
        lista.config(yscrollcommand=sb.set)
        lista.bind("<<ListboxSelect>>",
                   lambda e: self._preview_img(lista, lbl_prev))

        btn_f = tk.Frame(f_izq, bg="#fafafa")
        btn_f.pack(fill="x", pady=3)
        tk.Button(btn_f, text="▲ Subir",
                  command=lambda: self._subir(lista)).pack(side="left", padx=2)
        tk.Button(btn_f, text="▼ Bajar",
                  command=lambda: self._bajar(lista)).pack(side="left", padx=2)
        tk.Button(btn_f, text="❌ Eliminar", fg="red",
                  command=lambda: self._eliminar(lista)).pack(side="left", padx=2)

        # Derecha: previsualización
        f_der = tk.Frame(panel, bg="#f0f0fa", width=195,
                         relief="sunken", bd=1)
        f_der.pack(side="right", fill="y", padx=(10, 0))
        f_der.pack_propagate(False)
        tk.Label(f_der, text="Vista previa", bg="#f0f0fa",
                 font=("Arial", 9, "bold")).pack(pady=5)
        lbl_prev = tk.Label(f_der, bg="#f0f0fa",
                            text="Selecciona\nuna imagen", fg="gray")
        lbl_prev.pack(expand=True)

        self.var_img_abrir = self._checkbox_abrir(self.main_frame)

        tk.Button(self.main_frame, text="📄 GENERAR PDF",
                  bg="#1a5276", fg="white", font=("Arial", 11, "bold"), height=2,
                  command=lambda: self.run_img_to_pdf()).pack(fill="x", pady=5)

    def _add_img(self, lista):
        fs = filedialog.askopenfilenames(
            title="Selecciona imágenes",
            filetypes=[("Imágenes", "*.jpg *.jpeg *.png *.bmp *.tiff *.webp")])
        if fs:
            for f in fs:
                if f not in self.archivos_cargados:
                    self.archivos_cargados.append(f)
            self._refresh(lista)

    def _preview_img(self, lista, lbl):
        sel = lista.curselection()
        if not sel or sel[0] >= len(self.archivos_cargados):
            return
        try:
            img = Image.open(self.archivos_cargados[sel[0]])
            img.thumbnail((178, 215))
            photo = ImageTk.PhotoImage(img)
            lbl.config(image=photo, text="")
            lbl.image = photo
        except:
            pass

    def run_img_to_pdf(self):
        if not self.archivos_cargados:
            messagebox.showwarning("Aviso", "Añade al menos una imagen.")
            return
        nombre_sug = os.path.splitext(os.path.basename(self.archivos_cargados[0]))[0]
        out = filedialog.asksaveasfilename(
            title="Guardar PDF como…",
            defaultextension=".pdf",
            filetypes=[("PDF", "*.pdf")],
            initialfile=f"{nombre_sug}.pdf")
        if not out:
            return
        try:
            imgs = [Image.open(p).convert("RGB") for p in self.archivos_cargados]
            imgs[0].save(out, save_all=True, append_images=imgs[1:])
            messagebox.showinfo("Éxito", f"PDF creado con {len(imgs)} imagen(es).")
            self._abrir_carpeta(out, self.var_img_abrir)
        except Exception as e:
            messagebox.showerror("Error", str(e))

    # ══════════════════════════════════════════════════════════════════════════
    #  🖼️  PDF A IMÁGENES
    # ══════════════════════════════════════════════════════════════════════════

    def mostrar_p_to_img(self):
        self.limpiar_pantalla("🖼️ PDF a Imágenes")
        tk.Button(self.main_frame, text="➕ Seleccionar PDF",
                  command=lambda: self._add_files([("PDF", "*.pdf")], lista),
                  bg="#2980b9", fg="white").pack(fill="x")
        lista = tk.Listbox(self.main_frame, height=12)
        lista.pack(fill="x", pady=10)
        tk.Button(self.main_frame, text="CONVERTIR A IMÁGENES",
                  bg="#2980b9", fg="white", font=("Arial", 11, "bold"),
                  command=self.run_p2img).pack(fill="x")

    def run_p2img(self):
        if not self.archivos_cargados:
            return
        dest = filedialog.askdirectory()
        if dest:
            doc = fitz.open(self.archivos_cargados[0])
            for i, pag in enumerate(doc):
                pag.get_pixmap().save(os.path.join(dest, f"pag_{i+1}.png"))
            doc.close()
            os.startfile(dest)

    # ══════════════════════════════════════════════════════════════════════════
    #  📄  WORD A PDF  — reordenar, un PDF c/u o uno único, abrir carpeta
    # ══════════════════════════════════════════════════════════════════════════

    def mostrar_w_to_p(self):
        self.limpiar_pantalla("📄 Word a PDF")
        tk.Button(self.main_frame, text="➕ Añadir archivos Word (.docx)",
                  command=lambda: self._add_files([("Word", "*.docx")], lista),
                  bg="#2980b9", fg="white").pack(fill="x")

        lista = self._lista_con_controles(self.main_frame)

        sep = tk.Frame(self.main_frame, bg="#e8e8f5", height=2)
        sep.pack(fill="x", pady=8)
        tk.Label(self.main_frame, text="Resultado:", bg="#fafafa",
                 font=("Arial", 10, "bold")).pack(anchor="w")
        self.var_w2p_modo = tk.IntVar(value=1)
        tk.Radiobutton(self.main_frame, text="Un PDF por cada archivo Word (nombre original)",
                       variable=self.var_w2p_modo, value=1, bg="#fafafa").pack(anchor="w")
        tk.Radiobutton(self.main_frame, text="Un único PDF con todos los documentos juntos",
                       variable=self.var_w2p_modo, value=2, bg="#fafafa").pack(anchor="w")

        self.var_w2p_abrir = self._checkbox_abrir(self.main_frame)

        self.prog_w2p = ttk.Progressbar(self.main_frame, mode="determinate")
        self.prog_w2p.pack(fill="x", pady=(4, 0))

        tk.Button(self.main_frame, text="CONVERTIR A PDF",
                  bg="#1a5276", fg="white", font=("Arial", 11, "bold"), height=2,
                  command=self.run_w2p).pack(fill="x", pady=10)

    def run_w2p(self):
        if not self.archivos_cargados:
            messagebox.showwarning("Aviso", "Añade al menos un archivo Word.")
            return
        dest = filedialog.askdirectory(title="Selecciona carpeta de destino")
        if not dest:
            return
        try:
            pythoncom.CoInitialize()
            word = win32com.client.DispatchEx("Word.Application")

            if self.var_w2p_modo.get() == 1:
                # Un PDF por archivo
                self.prog_w2p["maximum"] = len(self.archivos_cargados)
                self.prog_w2p["value"]   = 0
                for i, r in enumerate(self.archivos_cargados):
                    out_path = os.path.join(
                        dest, os.path.splitext(os.path.basename(r))[0] + ".pdf")
                    doc = word.Documents.Open(os.path.abspath(r), ReadOnly=1)
                    doc.ExportAsFixedFormat(out_path, 17)
                    doc.Close(0)
                    self.prog_w2p["value"] = i + 1
                    self.main_frame.update_idletasks()
                word.Quit()
                messagebox.showinfo("Éxito", f"Convertidos {len(self.archivos_cargados)} archivo(s).")
                self._abrir_carpeta(dest, self.var_w2p_abrir)

            else:
                # Un único PDF
                temps = []
                self.prog_w2p["maximum"] = len(self.archivos_cargados) + 1
                self.prog_w2p["value"]   = 0
                for i, r in enumerate(self.archivos_cargados):
                    tmp = tempfile.mktemp(suffix=".pdf")
                    doc = word.Documents.Open(os.path.abspath(r), ReadOnly=1)
                    doc.ExportAsFixedFormat(tmp, 17)
                    doc.Close(0)
                    temps.append(tmp)
                    self.prog_w2p["value"] = i + 1
                    self.main_frame.update_idletasks()
                word.Quit()

                out_path = os.path.join(dest, "documentos_unidos.pdf")
                writer = PdfWriter()
                for t in temps:
                    writer.append(t)
                with open(out_path, "wb") as f:
                    writer.write(f)
                for t in temps:
                    try:
                        os.remove(t)
                    except:
                        pass
                self.prog_w2p["value"] = self.prog_w2p["maximum"]
                self.main_frame.update_idletasks()
                messagebox.showinfo("Éxito", "PDF unificado guardado.")
                self._abrir_carpeta(dest, self.var_w2p_abrir)

        except Exception as e:
            messagebox.showerror("Error", str(e))

    # ══════════════════════════════════════════════════════════════════════════
    #  📝  PDF A WORD  — abrir carpeta
    # ══════════════════════════════════════════════════════════════════════════

    def mostrar_p_to_w(self):
        self.limpiar_pantalla("📝 PDF a Word")
        tk.Button(self.main_frame, text="➕ Seleccionar PDF(s)",
                  command=lambda: self._add_files([("PDF", "*.pdf")], lista),
                  bg="#2980b9", fg="white").pack(fill="x")
        lista = tk.Listbox(self.main_frame, height=6)
        lista.pack(fill="x", pady=10)
        self.var_p2w_abrir = self._checkbox_abrir(self.main_frame)
        self.prog_p2w = ttk.Progressbar(self.main_frame, mode="determinate")
        self.prog_p2w.pack(fill="x", pady=(4, 0))
        tk.Button(self.main_frame, text="CONVERTIR A WORD",
                  bg="#2980b9", fg="white", font=("Arial", 11, "bold"), height=2,
                  command=self.run_p2w).pack(fill="x", pady=10)

    def run_p2w(self):
        if not self.archivos_cargados:
            messagebox.showwarning("Aviso", "Añade al menos un PDF.")
            return
        dest = filedialog.askdirectory()
        if dest:
            self.prog_p2w["maximum"] = len(self.archivos_cargados)
            self.prog_p2w["value"]   = 0
            for i, r in enumerate(self.archivos_cargados):
                cv = Converter(r)
                cv.convert(os.path.join(
                    dest, os.path.splitext(os.path.basename(r))[0] + ".docx"))
                cv.close()
                self.prog_p2w["value"] = i + 1
                self.main_frame.update_idletasks()
            messagebox.showinfo("Éxito", "Conversión completada.")
            self._abrir_carpeta(dest, self.var_p2w_abrir)

    # ══════════════════════════════════════════════════════════════════════════
    #  ✂️  EXTRACTOR — visor con grupos, rotación, modos, nombres, progreso
    # ══════════════════════════════════════════════════════════════════════════

    def mostrar_extractor(self):
        self.pag_selec = set()
        self.rot_map   = {}
        self.limpiar_pantalla("✂️ Extractor de Páginas")

        f_sel = tk.Frame(self.main_frame, bg="#fafafa")
        f_sel.pack(fill="x")
        tk.Button(f_sel, text="📂 Seleccionar PDF",
                  command=self._sel_pdf_extractor,
                  bg="#2980b9", fg="white").pack(side="left", fill="x", expand=True)
        tk.Button(f_sel, text="👁️ Visor / Seleccionar páginas",
                  command=lambda: self._abrir_visor_paginas("select"),
                  bg="#1a5276", fg="white").pack(side="left", padx=(4, 0))

        self.lbl_info = tk.Label(self.main_frame, text="Ningún archivo",
                                 bg="#fafafa", fg="gray")
        self.lbl_info.pack()
        self.lbl_pags_ext = tk.Label(self.main_frame, text="", bg="#fafafa",
                                     font=("Arial", 9), fg="#2E86C1")
        self.lbl_pags_ext.pack()

        tk.Label(self.main_frame,
                 text="Páginas a extraer (ej: 1, 3, 5-10) — o selecciónalas en el visor:",
                 bg="#fafafa", font=("Arial", 10, "bold")).pack(anchor="w", pady=(10, 0))
        self.ent_r = tk.Entry(self.main_frame, font=("Arial", 11))
        self.ent_r.pack(fill="x", pady=5)

        tk.Frame(self.main_frame, bg="#e8e8f5", height=2).pack(fill="x", pady=6)

        # ── Modo de extracción ───────────────────────────────────────────────
        tk.Label(self.main_frame, text="Modo de extracción:",
                 bg="#fafafa", font=("Arial", 10, "bold")).pack(anchor="w")
        self.var_ext_modo = tk.IntVar(value=1)
        tk.Radiobutton(self.main_frame, text="📄  Todas juntas en un único PDF",
                       variable=self.var_ext_modo, value=1, bg="#fafafa",
                       command=self._toggle_ext_opts).pack(anchor="w")
        tk.Radiobutton(self.main_frame, text="📑  Cada página en un PDF independiente",
                       variable=self.var_ext_modo, value=2, bg="#fafafa",
                       command=self._toggle_ext_opts).pack(anchor="w")
        tk.Radiobutton(self.main_frame, text="📚  Agrupadas por rangos (un PDF por grupo)",
                       variable=self.var_ext_modo, value=3, bg="#fafafa",
                       command=self._toggle_ext_opts).pack(anchor="w")

        # ── Nombre de los archivos (solo visible en modo 3) ──────────────────
        self.frame_nombres = tk.Frame(self.main_frame, bg="#fafafa")
        self.frame_nombres.pack(anchor="w", fill="x", pady=(6, 0))

        tk.Label(self.frame_nombres, text="Nombre de los archivos resultantes:",
                 bg="#fafafa", font=("Arial", 9, "bold"), fg="#555").pack(anchor="w")

        self.var_ext_nombre = tk.IntVar(value=1)

        tk.Radiobutton(self.frame_nombres,
                       text="Nombre original + número  (doc-1.pdf, doc-2.pdf…)",
                       variable=self.var_ext_nombre, value=1, bg="#fafafa",
                       font=("Arial", 9),
                       command=self._toggle_nombre_ext).pack(anchor="w", padx=10)

        f_op2 = tk.Frame(self.frame_nombres, bg="#fafafa")
        f_op2.pack(anchor="w", padx=10, fill="x")
        tk.Radiobutton(f_op2,
                       text="Detectar texto en la 1ª pág. del grupo — campo:",
                       variable=self.var_ext_nombre, value=2, bg="#fafafa",
                       font=("Arial", 9),
                       command=self._toggle_nombre_ext).pack(side="left")
        self.ent_ext_campo = tk.Entry(f_op2, font=("Arial", 9), width=20)
        self.ent_ext_campo.insert(0, "Apellidos y nombre")
        self.ent_ext_campo.pack(side="left", padx=(4, 0))

        f_op3 = tk.Frame(self.frame_nombres, bg="#fafafa")
        f_op3.pack(anchor="w", padx=10, fill="x")
        tk.Radiobutton(f_op3, text="Prefijo personalizado + número:",
                       variable=self.var_ext_nombre, value=3, bg="#fafafa",
                       font=("Arial", 9),
                       command=self._toggle_nombre_ext).pack(side="left")
        self.ent_ext_prefijo = tk.Entry(f_op3, font=("Arial", 9), width=20)
        self.ent_ext_prefijo.pack(side="left", padx=(4, 0))

        self._toggle_ext_opts()   # estado inicial

        self.var_ext_abrir = self._checkbox_abrir(self.main_frame)

        self.prog_ext = ttk.Progressbar(self.main_frame, mode="determinate")
        self.prog_ext.pack(fill="x", pady=(6, 0))

        tk.Button(self.main_frame, text="✂️ EXTRAER PÁGINAS",
                  bg="#1a5276", fg="white", font=("Arial", 11, "bold"), height=2,
                  command=self.run_ext).pack(fill="x", pady=8)

    def _toggle_ext_opts(self):
        """Muestra el panel de nombres solo en modo 3 (agrupadas)."""
        if self.var_ext_modo.get() == 3:
            self.frame_nombres.pack(anchor="w", fill="x", pady=(6, 0))
        else:
            self.frame_nombres.pack_forget()
        self._toggle_nombre_ext()

    def _toggle_nombre_ext(self):
        """Activa/desactiva los campos de texto según opción de nombre."""
        try:
            v = self.var_ext_nombre.get()
            self.ent_ext_campo.config(state="normal" if v == 2 else "disabled")
            self.ent_ext_prefijo.config(state="normal" if v == 3 else "disabled")
        except Exception:
            pass

    def _sel_pdf_extractor(self):
        f = filedialog.askopenfilename(filetypes=[("PDF", "*.pdf")])
        if f:
            self.ruta_pdf_unico = f
            self.lbl_info.config(text=os.path.basename(f), fg="#2d2580")
            self.lbl_pags_ext.config(
                text=f"Total: {len(PdfReader(f).pages)} páginas")
            self.pag_selec = set()
            self.rot_map   = {}

    @staticmethod
    def _indices_to_str(indices):
        """[0,1,2,4] (base 0) → '1-3, 5' (base 1). Respeta el orden original."""
        if not indices:
            return ""
        ns = [i + 1 for i in indices]   # base 1, conserva orden
        # Compactar consecutivos manteniendo dirección
        parts, start, prev = [], ns[0], ns[0]
        for n in ns[1:]:
            if n == prev + 1:
                prev = n
            else:
                parts.append(str(start) if start == prev else f"{start}-{prev}")
                start = prev = n
        parts.append(str(start) if start == prev else f"{start}-{prev}")
        return "-".join(str(p) for p in parts) if len(parts) == 1 else ", ".join(parts)

    def _abrir_visor_paginas(self, modo="select"):
        """
        Toplevel con miniaturas de todas las páginas del PDF.
        modo='select' : selección individual + grupos + rotar → rellena ent_r
        modo='preview': clic para ampliar (separador)
        """
        if not self.ruta_pdf_unico:
            messagebox.showwarning("Aviso", "Selecciona primero un PDF.")
            return

        THUMB_W, THUMB_H = 88, 124
        CELL_W,  CELL_H  = 108, 158
        COLS = 6
        # Paleta de colores para grupos (fondo, borde, texto)
        PALETA = [
            ("#d5e8fd", "#2980b9", "#1a5276"),   # azul
            ("#d5f5e3", "#27ae60", "#1e8449"),   # verde
            ("#fdebd0", "#e67e22", "#a04000"),   # naranja
            ("#f9ebea", "#e74c3c", "#922b21"),   # rojo
            ("#e8daef", "#8e44ad", "#6c3483"),   # morado
            ("#d6eaf8", "#1abc9c", "#148f77"),   # turquesa
        ]

        doc = fitz.open(self.ruta_pdf_unico)
        n   = len(doc)

        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        tw = min(940, sw - 80)
        th = min(sh - 60, 760)

        top = tk.Toplevel(self.root)
        top.title(
            f"{'Seleccionar páginas' if modo == 'select' else 'Vista previa'} — "
            f"{os.path.basename(self.ruta_pdf_unico)}  ({n} pág.)")
        top.geometry(f"{tw}x{th}+{(sw - tw) // 2}+{(sh - th) // 2}")
        top.configure(bg="#fafafa")
        top.grab_set()

        # grupos: lista de listas de índices (base 0) en orden de creación
        grupos    = []          # [ [0,1], [2,3], … ]
        seleccion = set()       # páginas marcadas en este momento (pendientes de grupo)

        # ── Barra superior ───────────────────────────────────────────────────
        bar = tk.Frame(top, bg="#1a5276", pady=5)
        bar.pack(fill="x")

        lbl_sel = None   # label contador

        if modo == "select":
            tk.Button(bar, text="✅ Todas",    command=lambda: _sel_all(),
                      bg="#2980b9", fg="white", font=("Arial", 9),
                      cursor="hand2").pack(side="left", padx=3)
            tk.Button(bar, text="⬜ Ninguna",  command=lambda: _desel_all(),
                      bg="#888780", fg="white", font=("Arial", 9),
                      cursor="hand2").pack(side="left", padx=3)
            tk.Button(bar, text="↺ 90° izq.", command=lambda: _rotar(-90),
                      bg="#1a5276", fg="white", font=("Arial", 9),
                      cursor="hand2").pack(side="left", padx=3)
            tk.Button(bar, text="↻ 90° der.", command=lambda: _rotar(90),
                      bg="#1a5276", fg="white", font=("Arial", 9),
                      cursor="hand2").pack(side="left", padx=3)
            lbl_sel = tk.Label(bar, text="0 sel.", bg="#1a5276",
                               fg="#e8e8f5", font=("Arial", 9))
            lbl_sel.pack(side="left", padx=6)
            tk.Button(bar, text="✔ ACEPTAR",  command=lambda: _aceptar(),
                      bg="#1a5276", fg="white", font=("Arial", 10, "bold"),
                      cursor="hand2").pack(side="right", padx=8)
        else:
            tk.Label(bar, text="Vista previa — clic en una página para ampliarla",
                     bg="#1a5276", fg="#e8e8f5", font=("Arial", 9)
                     ).pack(side="left", padx=8)
            tk.Button(bar, text="✖ Cerrar", command=lambda: _cerrar(),
                      bg="#888780", fg="white", font=("Arial", 9),
                      cursor="hand2").pack(side="right", padx=8)

        # ── Panel de grupos (solo modo select) ───────────────────────────────
        if modo == "select":
            gbar = tk.Frame(top, bg="#e8e8f5", pady=4, padx=6)
            gbar.pack(fill="x")

            tk.Button(gbar, text="➕ Añadir grupo con selección actual",
                      command=lambda: _add_grupo(),
                      bg="#1a5276", fg="white", font=("Arial", 9, "bold"),
                      cursor="hand2").pack(side="left", padx=(0, 6))
            tk.Button(gbar, text="🗑 Quitar último grupo",
                      command=lambda: _del_ultimo_grupo(),
                      bg="#888780", fg="white", font=("Arial", 9),
                      cursor="hand2").pack(side="left", padx=3)
            tk.Button(gbar, text="🗑🗑 Borrar todos los grupos",
                      command=lambda: _clear_grupos(),
                      bg="#1a5276", fg="white", font=("Arial", 9),
                      cursor="hand2").pack(side="left", padx=3)

            lbl_grupos = tk.Label(gbar, text="Sin grupos", bg="#e8e8f5",
                                  fg="#555", font=("Arial", 9), wraplength=480,
                                  justify="left")
            lbl_grupos.pack(side="left", padx=10)
        else:
            lbl_grupos = None

        # ── Canvas scrollable ────────────────────────────────────────────────
        fc = tk.Frame(top, bg="#f0f0fa")
        fc.pack(fill="both", expand=True, padx=4, pady=4)

        canvas = tk.Canvas(fc, bg="#f0f0fa", highlightthickness=0)
        vsb = tk.Scrollbar(fc, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)

        inner = tk.Frame(canvas, bg="#f0f0fa")
        canvas.create_window((0, 0), window=inner, anchor="nw")

        thumb_refs = []

        def _grupo_de(idx):
            """Devuelve (num_grupo, paleta) si idx está en algún grupo, sino None."""
            for gi, g in enumerate(grupos):
                if idx in g:
                    return gi, PALETA[gi % len(PALETA)]
            return None, None

        def _render_all():
            nonlocal thumb_refs
            thumb_refs = []
            for w in inner.winfo_children():
                w.destroy()

            for idx in range(n):
                page = doc[idx]
                zoom = min(THUMB_W / page.rect.width,
                           THUMB_H / page.rect.height)
                pix  = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), alpha=False)
                img  = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)

                rot = self.rot_map.get(idx, 0) if modo == "select" else 0
                if rot:
                    img = img.rotate(-rot, expand=True)
                    img.thumbnail((THUMB_W, THUMB_H), Image.LANCZOS)

                photo = ImageTk.PhotoImage(img)
                thumb_refs.append(photo)

                gi, pal = _grupo_de(idx)
                en_selec = idx in seleccion

                if gi is not None:
                    bg_c, brd_c, fg_c = "white", "#bdc3c7", pal[2]
                elif en_selec:
                    bg_c, brd_c, fg_c = "#fffacd", "#f39c12", "#7d6608"
                else:
                    bg_c, brd_c, fg_c = "white", "#bdc3c7", "#666"

                row, col = divmod(idx, COLS)
                cell = tk.Frame(inner, bg=bg_c, bd=2, relief="solid",
                                highlightthickness=2,
                                highlightbackground=brd_c,
                                width=CELL_W, height=CELL_H)
                cell.grid(row=row, column=col, padx=3, pady=3)
                cell.grid_propagate(False)

                lbl_img = tk.Label(cell, image=photo, bg=bg_c,
                                   cursor="hand2" if modo == "select" else "arrow")
                lbl_img.pack(pady=(4, 1))

                if gi is not None:
                    txt = f"G{gi+1} · Pág. {idx+1}"
                elif en_selec:
                    txt = f"✓ Pág. {idx+1}"
                else:
                    txt = f"Pág. {idx+1}"
                if rot:
                    txt += f" [{rot}°]"
                tk.Label(cell, text=txt, bg=bg_c, font=("Arial", 8),
                         fg=fg_c).pack()

                if modo == "select":
                    for w in (lbl_img, cell):
                        w.bind("<Button-1>", lambda e, i=idx: _toggle(i))
                else:
                    for w in (lbl_img, cell):
                        w.bind("<Button-1>", lambda e, i=idx: _ampliar(i))

            inner.update_idletasks()
            canvas.configure(scrollregion=canvas.bbox("all"))

        # ── Acciones ─────────────────────────────────────────────────────────

        def _update_lbl():
            if lbl_sel:
                ns = len(seleccion)
                lbl_sel.config(
                    text=f"{ns} sel.")

        def _update_grupos_lbl():
            if lbl_grupos is None:
                return
            if not grupos:
                lbl_grupos.config(text="Sin grupos")
                return
            partes = []
            for gi, g in enumerate(grupos):
                indices_ord = sorted(g)
                rng = self._indices_to_str(indices_ord)
                pal = PALETA[gi % len(PALETA)]
                partes.append(f"G{gi+1}: {rng}")
            lbl_grupos.config(text="  |  ".join(partes))

        def _toggle(idx):
            # No permitir seleccionar páginas ya asignadas a un grupo
            if _grupo_de(idx)[0] is not None:
                return
            if idx in seleccion:
                seleccion.discard(idx)
            else:
                seleccion.add(idx)
            _render_all()
            _update_lbl()

        def _sel_all():
            # Solo las que aún no tienen grupo
            ya_en_grupo = {i for g in grupos for i in g}
            seleccion.clear()
            seleccion.update(set(range(n)) - ya_en_grupo)
            _render_all()
            _update_lbl()

        def _desel_all():
            seleccion.clear()
            _render_all()
            _update_lbl()

        def _rotar(grados):
            for idx in seleccion:
                self.rot_map[idx] = (self.rot_map.get(idx, 0) + grados) % 360
            _render_all()

        def _add_grupo():
            if not seleccion:
                messagebox.showwarning("Aviso",
                    "Selecciona al menos una página antes de añadir un grupo.",
                    parent=top)
                return
            grupos.append(sorted(seleccion))
            seleccion.clear()
            _render_all()
            _update_lbl()
            _update_grupos_lbl()

        def _del_ultimo_grupo():
            if grupos:
                grupos.pop()
                _render_all()
                _update_grupos_lbl()

        def _clear_grupos():
            grupos.clear()
            seleccion.clear()
            _render_all()
            _update_lbl()
            _update_grupos_lbl()

        def _ampliar(idx):
            amp = tk.Toplevel(top)
            amp.title(f"Pág. {idx+1}")
            page  = doc[idx]
            max_w = int(sw * 0.75)
            max_h = int(sh * 0.85)
            zoom  = min(2.0,
                        max_w / page.rect.width,
                        max_h / page.rect.height)
            pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), alpha=False)
            img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
            rot = self.rot_map.get(idx, 0)
            if rot:
                img = img.rotate(-rot, expand=True)
            ph = ImageTk.PhotoImage(img)
            win_w = min(img.width + 20,  max_w)
            win_h = min(img.height + 40, max_h)
            amp.geometry(f"{win_w}x{win_h}")
            c2   = tk.Canvas(amp, bg="#555")
            sb_v = tk.Scrollbar(amp, orient="vertical",   command=c2.yview)
            sb_h = tk.Scrollbar(amp, orient="horizontal", command=c2.xview)
            c2.configure(yscrollcommand=sb_v.set, xscrollcommand=sb_h.set)
            sb_v.pack(side="right",  fill="y")
            sb_h.pack(side="bottom", fill="x")
            c2.pack(fill="both", expand=True)
            c2.create_image(0, 0, anchor="nw", image=ph)
            c2.configure(scrollregion=c2.bbox("all"))
            c2.image = ph

        def _aceptar():
            if modo == "select":
                # Construir el string final a partir de grupos + selección suelta
                partes = []
                for g in grupos:
                    partes.append(self._indices_to_str(sorted(g)))
                if seleccion:          # páginas seleccionadas pero sin grupo asignado
                    partes.append(self._indices_to_str(sorted(seleccion)))
                resultado = ", ".join(partes)
                try:
                    self.ent_r.delete(0, tk.END)
                    self.ent_r.insert(0, resultado)
                except Exception:
                    pass
                # Guardar en pag_selec para compatibilidad con rotación
                self.pag_selec = {i for g in grupos for i in g} | seleccion
            doc.close()
            top.destroy()

        def _cerrar():
            doc.close()
            top.destroy()

        canvas.bind("<MouseWheel>",
                    lambda e: canvas.yview_scroll(-1 * (e.delta // 120), "units"))
        inner.bind("<Configure>",
                   lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        top.protocol("WM_DELETE_WINDOW", _cerrar)

        _render_all()

    def run_ext(self):
        if not self.ruta_pdf_unico:
            messagebox.showwarning("Aviso", "Selecciona un PDF.")
            return
        if not self.ent_r.get().strip():
            messagebox.showwarning("Aviso", "Indica las páginas a extraer.")
            return

        nombre_base = os.path.splitext(os.path.basename(self.ruta_pdf_unico))[0]
        modo = self.var_ext_modo.get()

        def _get_page(reader, idx):
            """Devuelve la página con rotación aplicada si procede."""
            page = reader.pages[idx]
            rot  = self.rot_map.get(idx, 0)
            if rot:
                page.rotate(rot)
            return page

        try:
            reader = PdfReader(self.ruta_pdf_unico)
            rangos = []
            for p in self.ent_r.get().replace(" ", "").split(","):
                if "-" in p:
                    a, b = map(int, p.split("-"))
                    rangos.append(list(range(a - 1, b)))
                else:
                    rangos.append([int(p) - 1])

            todas = [n for rango in rangos for n in rango]

            if modo == 1:
                # ── Todas juntas ─────────────────────────────────────────────
                out = filedialog.asksaveasfilename(
                    title="Guardar PDF como…",
                    defaultextension=".pdf",
                    filetypes=[("PDF", "*.pdf")],
                    initialfile=f"páginas extraídas de {nombre_base}.pdf")
                if not out:
                    return
                self.prog_ext["maximum"] = len(todas)
                self.prog_ext["value"]   = 0
                writer = PdfWriter()
                for i, n in enumerate(todas):
                    writer.add_page(_get_page(reader, n))
                    self.prog_ext["value"] = i + 1
                    self.main_frame.update_idletasks()
                with open(out, "wb") as f:
                    writer.write(f)
                messagebox.showinfo("Éxito", "Páginas extraídas en un único PDF.")
                self._abrir_carpeta(out, self.var_ext_abrir)

            elif modo == 2:
                # ── Cada página independiente ────────────────────────────────
                dest = filedialog.askdirectory(title="Carpeta de destino")
                if not dest:
                    return
                self.prog_ext["maximum"] = len(todas)
                self.prog_ext["value"]   = 0
                for i, n in enumerate(todas):
                    w = PdfWriter()
                    w.add_page(_get_page(reader, n))
                    with open(
                        os.path.join(dest, f"{nombre_base}_pag{n+1}.pdf"), "wb"
                    ) as f:
                        w.write(f)
                    self.prog_ext["value"] = i + 1
                    self.main_frame.update_idletasks()
                messagebox.showinfo("Éxito",
                                    f"Generados {len(todas)} PDFs individuales.")
                self._abrir_carpeta(dest, self.var_ext_abrir)

            elif modo == 3:
                # ── Agrupadas por rangos ─────────────────────────────────────
                dest = filedialog.askdirectory(title="Carpeta de destino")
                if not dest:
                    return
                self.prog_ext["maximum"] = len(rangos)
                self.prog_ext["value"]   = 0
                modo_nombre = self.var_ext_nombre.get()
                for i, rango in enumerate(rangos):
                    w = PdfWriter()
                    for n in rango:
                        w.add_page(_get_page(reader, n))

                    if modo_nombre == 2:
                        campo = self.ent_ext_campo.get().strip()
                        texto = reader.pages[rango[0]].extract_text() or ""
                        patron = re.escape(campo) + r"[:\s]*([^\n\r]{1,80})"
                        match  = re.search(patron, texto, re.IGNORECASE)
                        name   = (match.group(1).strip().replace(",", "")
                                  if match else f"{nombre_base}-{i+1}")
                    elif modo_nombre == 3:
                        prefijo = self.ent_ext_prefijo.get().strip() or nombre_base
                        name    = f"{prefijo}-{i+1}"
                    else:
                        name = f"{nombre_base}-{i+1}"

                    name = re.sub(r'[\\/*?:"<>|]', "", name).strip() or f"{nombre_base}-{i+1}"
                    with open(
                        os.path.join(dest, f"{name}.pdf"), "wb"
                    ) as f:
                        w.write(f)
                    self.prog_ext["value"] = i + 1
                    self.main_frame.update_idletasks()
                messagebox.showinfo("Éxito",
                                    f"Generados {len(rangos)} grupo(s) de PDFs.")
                self._abrir_carpeta(dest, self.var_ext_abrir)

        except Exception as e:
            messagebox.showerror("Error", str(e))

    # ══════════════════════════════════════════════════════════════════════════
    #  🔗  UNIFICADOR PDF — reordenar, eliminar, nombre sugerido, abrir carpeta
    # ══════════════════════════════════════════════════════════════════════════

    def mostrar_unificador(self):
        self.limpiar_pantalla("🔗 Unificador de PDFs")
        tk.Button(self.main_frame, text="➕ Añadir PDFs",
                  command=lambda: self._add_files([("PDF", "*.pdf")], lista),
                  bg="#1a5276", fg="white").pack(fill="x")

        lista = self._lista_con_controles(self.main_frame)

        self.var_uni_abrir = self._checkbox_abrir(self.main_frame)

        tk.Button(self.main_frame, text="🔗 FUSIONAR PDFs",
                  bg="#1a5276", fg="white", font=("Arial", 11, "bold"), height=2,
                  command=self.run_uni).pack(fill="x", pady=10)

    def run_uni(self):
        if not self.archivos_cargados:
            messagebox.showwarning("Aviso", "Añade al menos un PDF.")
            return
        out = filedialog.asksaveasfilename(
            title="Guardar PDF unificado como…",
            defaultextension=".pdf",
            filetypes=[("PDF", "*.pdf")],
            initialfile="PDF_Unificado.pdf")
        if out:
            try:
                w = PdfWriter()
                for p in self.archivos_cargados:
                    w.append(p)
                with open(out, "wb") as f:
                    w.write(f)
                messagebox.showinfo("Éxito", "PDFs unificados correctamente.")
                self._abrir_carpeta(out, self.var_uni_abrir)
            except Exception as e:
                messagebox.showerror("Error", str(e))

    # ══════════════════════════════════════════════════════════════════════════
    #  🗜️  COMPRESOR — Ghostscript (real) + fallback PyMuPDF
    # ══════════════════════════════════════════════════════════════════════════

    def mostrar_compresor(self):
        self.limpiar_pantalla("🗜️ Compresor de PDF")

        # Estado de Ghostscript
        gs = _buscar_ghostscript()
        if gs:
            estado_txt = f"✅  Ghostscript encontrado"
            estado_color = "#27ae60"
        else:
            estado_txt = "⚠️  Ghostscript no encontrado — se usará modo alternativo (menor eficiencia)"
            estado_color = "#e67e22"
        tk.Label(self.main_frame, text=estado_txt, bg="#fafafa",
                 fg=estado_color, font=("Arial", 9, "bold"),
                 wraplength=650, justify="left").pack(anchor="w", pady=(0, 4))

        tk.Button(self.main_frame, text="📂 Seleccionar PDF",
                  command=self.sel_pdf_simple, bg="#2980b9", fg="white").pack(fill="x")
        self.lbl_info = tk.Label(self.main_frame, text="Ningún archivo",
                                 bg="#fafafa", fg="gray")
        self.lbl_info.pack(pady=4)

        tk.Frame(self.main_frame, bg="#e8e8f5", height=2).pack(fill="x", pady=6)

        # ── Nivel de compresión ──────────────────────────────────────────────
        tk.Label(self.main_frame, text="Nivel de compresión:",
                 bg="#fafafa", font=("Arial", 10, "bold")).pack(anchor="w")

        self.var_nivel_gs = tk.StringVar(value="ebook")
        niveles_gs = [
            ("screen",   "🔴  Máxima compresión  — reducción 70-90 %, baja calidad visual"),
            ("ebook",    "🟡  Equilibrado        — reducción 40-70 %  ✔ recomendado"),
            ("printer",  "🟢  Alta calidad       — reducción 10-40 %, buena nitidez"),
            ("prepress", "⚪  Preprensa          — mínima compresión, máxima calidad"),
        ]
        for val, txt in niveles_gs:
            tk.Radiobutton(self.main_frame, text=txt,
                           variable=self.var_nivel_gs, value=val,
                           bg="#fafafa", font=("Arial", 9)).pack(anchor="w")

        tk.Frame(self.main_frame, bg="#e8e8f5", height=2).pack(fill="x", pady=6)

        tk.Label(self.main_frame,
                 text="ℹ️  Ghostscript procesa TODO el contenido del PDF (texto, fuentes e imágenes)\n"
                      "    y garantiza una reducción significativa en cualquier tipo de documento.",
                 bg="#fafafa", fg="#666", font=("Arial", 8),
                 justify="left").pack(anchor="w")

        self.var_comp_abrir = self._checkbox_abrir(self.main_frame)

        tk.Button(self.main_frame, text="🗜️ COMPRIMIR PDF",
                  bg="#2980b9", fg="white", font=("Arial", 11, "bold"), height=2,
                  command=self.run_compresor).pack(fill="x", pady=8)

    def run_compresor(self):
        if not self.ruta_pdf_unico:
            messagebox.showwarning("Aviso", "Selecciona un PDF.")
            return
        nombre_base = os.path.splitext(os.path.basename(self.ruta_pdf_unico))[0]
        out = filedialog.asksaveasfilename(
            title="Guardar PDF comprimido como…",
            defaultextension=".pdf",
            filetypes=[("PDF", "*.pdf")],
            initialfile=f"{nombre_base}_comprimido.pdf")
        if not out:
            return

        orig_kb = os.path.getsize(self.ruta_pdf_unico) / 1024
        gs = _buscar_ghostscript()

        try:
            if gs:
                # ── GHOSTSCRIPT (mejor compresión real) ──────────────────────
                calidad = self.var_nivel_gs.get()
                cmd = [
                    gs,
                    "-sDEVICE=pdfwrite",
                    "-dCompatibilityLevel=1.4",
                    f"-dPDFSETTINGS=/{calidad}",
                    "-dNOPAUSE", "-dQUIET", "-dBATCH",
                    f"-sOutputFile={out}",
                    self.ruta_pdf_unico,
                ]
                subprocess.run(cmd, check=True,
                               creationflags=subprocess.CREATE_NO_WINDOW)
                metodo = "Ghostscript"

            else:
                # ── FALLBACK PyMuPDF — limpieza + streams ────────────────────
                doc = fitz.open(self.ruta_pdf_unico)
                doc.save(out, garbage=4, deflate=True,
                         deflate_images=True, deflate_fonts=True, clean=True)
                doc.close()
                metodo = "PyMuPDF (instala Ghostscript para mejor resultado)"

            nuevo_kb = os.path.getsize(out) / 1024
            reduccion = (orig_kb - nuevo_kb) / orig_kb * 100 if orig_kb > 0 else 0
            messagebox.showinfo(
                "Compresión completada",
                f"Original :  {orig_kb:,.1f} KB\n"
                f"Nuevo    :  {nuevo_kb:,.1f} KB\n"
                f"Reducción:  {reduccion:.1f} %\n\n"
                f"Motor: {metodo}")
            self._abrir_carpeta(out, self.var_comp_abrir)
        except Exception as e:
            messagebox.showerror("Error", str(e))

    # ══════════════════════════════════════════════════════════════════════════
    #  🔍  EXTRAER TEXTO — botón "Seleccionar todo"
    # ══════════════════════════════════════════════════════════════════════════

    def mostrar_ocr(self):
        self.limpiar_pantalla("🔍 Extraer Texto")
        tk.Button(self.main_frame, text="➕ Seleccionar PDF",
                  command=lambda: self._add_files([("PDF", "*.pdf")], lista),
                  bg="#2980b9", fg="white").pack(fill="x")
        lista = tk.Listbox(self.main_frame, height=3)
        lista.pack(fill="x", pady=5)

        f_acc = tk.Frame(self.main_frame, bg="#fafafa")
        f_acc.pack(fill="x", pady=4)
        tk.Button(f_acc, text="🔍 EXTRAER TEXTO",
                  command=self.run_ocr, bg="#2980b9", fg="white",
                  font=("Arial", 10, "bold")).pack(side="left")
        tk.Button(f_acc, text="📋 Seleccionar todo",
                  command=self._sel_todo, bg="#888780",
                  fg="white").pack(side="left", padx=5)
        tk.Button(f_acc, text="💾 Guardar como .txt",
                  command=self._guardar_txt, bg="#888780",
                  fg="white").pack(side="right")

        self.txt_res = tk.Text(self.main_frame, height=16,
                               bg="#f8f9fa", font=("Consolas", 10))
        self.txt_res.pack(fill="both", expand=True, pady=5)
        sb = tk.Scrollbar(self.txt_res, command=self.txt_res.yview)
        self.txt_res.config(yscrollcommand=sb.set)

    def run_ocr(self):
        if not self.archivos_cargados:
            return
        doc = fitz.open(self.archivos_cargados[0])
        texto = "".join(pag.get_text() + "\n" for pag in doc)
        self.txt_res.delete("1.0", tk.END)
        self.txt_res.insert(tk.END, texto)
        doc.close()

    def _sel_todo(self):
        self.txt_res.tag_add("sel", "1.0", "end")
        self.txt_res.focus()

    def _guardar_txt(self):
        contenido = self.txt_res.get("1.0", tk.END).strip()
        if not contenido:
            messagebox.showwarning("Aviso", "No hay texto para guardar.")
            return
        out = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Texto", "*.txt")],
            initialfile="texto_extraido.txt")
        if out:
            with open(out, "w", encoding="utf-8") as f:
                f.write(contenido)
            messagebox.showinfo("Éxito", "Texto guardado.")

    # ══════════════════════════════════════════════════════════════════════════
    #  🔐  PONER CLAVE — nombre sugerido "original_protegido", abrir carpeta
    # ══════════════════════════════════════════════════════════════════════════

    def mostrar_proteccion(self):
        self.limpiar_pantalla("🔐 Proteger PDF con Contraseña")
        tk.Button(self.main_frame, text="📂 Seleccionar PDF",
                  command=self.sel_pdf_simple, bg="#2980b9", fg="white").pack(fill="x")
        self.lbl_info = tk.Label(self.main_frame, text="Ningún archivo",
                                 bg="#fafafa", fg="gray")
        self.lbl_info.pack(pady=5)
        tk.Label(self.main_frame, text="Nueva contraseña:",
                 bg="#fafafa", font=("Arial", 10, "bold")).pack(pady=(15, 0), anchor="w")
        self.ent_pass = tk.Entry(self.main_frame, font=("Arial", 12), show="*")
        self.ent_pass.pack(fill="x", pady=5)
        self.var_prot_abrir = self._checkbox_abrir(self.main_frame)
        tk.Button(self.main_frame, text="🔐 ENCRIPTAR Y GUARDAR",
                  bg="#1a5276", fg="white", font=("Arial", 11, "bold"), height=2,
                  command=self.run_proteccion).pack(fill="x", pady=20)

    def run_proteccion(self):
        password = self.ent_pass.get()
        if not self.ruta_pdf_unico or not password:
            messagebox.showwarning("Aviso", "Selecciona un PDF y escribe una contraseña.")
            return
        nombre_base = os.path.splitext(os.path.basename(self.ruta_pdf_unico))[0]
        out = filedialog.asksaveasfilename(
            title="Guardar PDF protegido como…",
            defaultextension=".pdf",
            filetypes=[("PDF", "*.pdf")],
            initialfile=f"{nombre_base}_protegido.pdf")
        if out:
            try:
                reader = PdfReader(self.ruta_pdf_unico)
                writer = PdfWriter()
                for page in reader.pages:
                    writer.add_page(page)
                writer.encrypt(password)
                with open(out, "wb") as f:
                    writer.write(f)
                messagebox.showinfo("Éxito", "Contraseña aplicada correctamente.")
                self.ent_pass.delete(0, tk.END)
                self._abrir_carpeta(out, self.var_prot_abrir)
            except Exception as e:
                messagebox.showerror("Error", str(e))

    # ══════════════════════════════════════════════════════════════════════════
    #  🔓  QUITAR CLAVE — nombre sugerido "original_desprotegido", abrir carpeta
    # ══════════════════════════════════════════════════════════════════════════

    def mostrar_desproteccion(self):
        self.limpiar_pantalla("🔓 Desproteger PDF (Quitar Contraseña)")
        tk.Label(self.main_frame,
                 text="Se generará una copia sin contraseña del archivo original.",
                 bg="#fafafa", fg="#666").pack(anchor="w")
        tk.Button(self.main_frame, text="📂 Seleccionar PDF protegido",
                  command=self.sel_pdf_simple, bg="#2980b9", fg="white").pack(fill="x", pady=10)
        self.lbl_info = tk.Label(self.main_frame, text="Ningún archivo",
                                 bg="#fafafa", fg="gray")
        self.lbl_info.pack(pady=5)
        tk.Label(self.main_frame, text="Contraseña actual:",
                 bg="#fafafa", font=("Arial", 10, "bold")).pack(pady=(15, 0), anchor="w")
        self.ent_pass = tk.Entry(self.main_frame, font=("Arial", 12), show="*")
        self.ent_pass.pack(fill="x", pady=5)
        self.var_desprot_abrir = self._checkbox_abrir(self.main_frame)
        tk.Button(self.main_frame, text="🔓 QUITAR PROTECCIÓN Y GUARDAR",
                  bg="#2980b9", fg="white", font=("Arial", 11, "bold"), height=2,
                  command=self.run_desproteccion).pack(fill="x", pady=20)

    def run_desproteccion(self):
        password = self.ent_pass.get()
        if not self.ruta_pdf_unico or not password:
            messagebox.showwarning("Aviso", "Selecciona el PDF e introduce su contraseña.")
            return
        nombre_base = os.path.splitext(os.path.basename(self.ruta_pdf_unico))[0]
        out = filedialog.asksaveasfilename(
            title="Guardar copia sin contraseña como…",
            defaultextension=".pdf",
            filetypes=[("PDF", "*.pdf")],
            initialfile=f"{nombre_base}_desprotegido.pdf")
        if out:
            try:
                reader = PdfReader(self.ruta_pdf_unico)
                if reader.is_encrypted:
                    result = reader.decrypt(password)
                    if result == 0:
                        messagebox.showerror("Error", "Contraseña incorrecta.")
                        return
                writer = PdfWriter()
                for page in reader.pages:
                    writer.add_page(page)
                with open(out, "wb") as f:
                    writer.write(f)
                messagebox.showinfo("Éxito", "Copia sin contraseña generada.")
                self.ent_pass.delete(0, tk.END)
                self._abrir_carpeta(out, self.var_desprot_abrir)
            except Exception:
                messagebox.showerror("Error",
                    "Contraseña incorrecta o el archivo no está encriptado.")

    # ══════════════════════════════════════════════════════════════════════════
    #  🔢  NÚMEROS Y MARCAS
    # ══════════════════════════════════════════════════════════════════════════

    def mostrar_marcas(self):
        self.limpiar_pantalla("🔢 Numeración y Marcas de Agua")
        tk.Button(self.main_frame, text="📂 Seleccionar PDF",
                  command=self.sel_pdf_simple, bg="#2980b9", fg="white").pack(fill="x")
        self.lbl_info = tk.Label(self.main_frame, text="Ningún archivo",
                                 bg="#fafafa", fg="gray")
        self.lbl_info.pack(pady=5)
        tk.Label(self.main_frame, text="Texto a insertar:",
                 bg="#fafafa", font=("Arial", 10, "bold")).pack(pady=(10, 0))
        self.ent_marca = tk.Entry(self.main_frame, font=("Arial", 11))
        self.ent_marca.pack(fill="x", pady=5)
        self.var_num = tk.BooleanVar(value=True)
        tk.Checkbutton(self.main_frame, text="Añadir nº de página",
                       variable=self.var_num, bg="#fafafa").pack(anchor="w")
        tk.Button(self.main_frame, text="APLICAR Y GUARDAR",
                  bg="#1a5276", fg="white", font=("Arial", 11, "bold"),
                  command=self.run_marcas).pack(fill="x", pady=20)

    def run_marcas(self):
        if not self.ruta_pdf_unico:
            return
        out = filedialog.asksaveasfilename(defaultextension=".pdf",
                                           initialfile="marcado.pdf")
        if out:
            try:
                doc = fitz.open(self.ruta_pdf_unico)
                for i, page in enumerate(doc):
                    msg = self.ent_marca.get()
                    if self.var_num.get():
                        msg += f" | Pág. {i+1} de {len(doc)}"
                    page.insert_text((50, page.rect.height - 30), msg,
                                     fontsize=10, color=(0.7, 0.7, 0.7))
                doc.save(out)
                doc.close()
                messagebox.showinfo("Éxito", "Marcas añadidas.")
            except Exception as e:
                messagebox.showerror("Error", str(e))


# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    root = tk.Tk()
    app = SuiteDocumental(root)
    root.mainloop()
