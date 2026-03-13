# -*- coding: utf-8 -*-
import os
import fitz  # PyMuPDF
import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image
import win32com.client
import pythoncom
from pdf2docx import Converter
from pypdf import PdfReader, PdfWriter
import re
import subprocess
from io import BytesIO

class SuiteDocumental:
    def __init__(self, root):
        self.root = root
        self.nombre_suite = "Suite PDF"
        self.root.title(self.nombre_suite)

        # Dimensiones de la ventana
        ancho_ventana = 980
        alto_ventana = 780
        ancho_pantalla = self.root.winfo_screenwidth()
        pos_x = (ancho_pantalla // 2) - (ancho_ventana // 2)
        pos_y = 0 
        self.root.geometry(f"{ancho_ventana}x{alto_ventana}+{pos_x}+{pos_y}")

        try:
            self.icono = tk.PhotoImage(file='pdf-icono.png')
            self.root.iconphoto(False, self.icono)
        except: pass

        self.root.configure(bg="#f0f2f5")
        self.archivos_cargados = []
        self.ruta_pdf_unico = ""
        self.naming_option = tk.IntVar(value=2)

        # --- Sidebar ---
        self.sidebar = tk.Frame(root, bg="#2c3e50", width=220)
        self.sidebar.pack(side="left", fill="y")
        
        tk.Label(self.sidebar, text=self.nombre_suite, fg="#1abc9c", bg="#2c3e50", 
                 font=("Arial", 11, "bold"), pady=20, wraplength=180).pack()

        self.crear_menu_btn("📷 Imágenes a PDF", self.mostrar_img_to_pdf)
        self.crear_menu_btn("🖼️ PDF a Imágenes", self.mostrar_p_to_img)
        self.crear_menu_btn("📄 Word a PDF", self.mostrar_w_to_p)
        self.crear_menu_btn("📝 PDF a Word", self.mostrar_p_to_w)
        self.crear_menu_btn("✂️ Extractor PDF", self.mostrar_extractor)
        self.crear_menu_btn("📂 Separador PDF", self.mostrar_separador)
        self.crear_menu_btn("🔗 Unificador PDF", self.mostrar_unificador)
        self.crear_menu_btn("🗜️ Compresor PDF", self.mostrar_compresor)
        self.crear_menu_btn("🔍 Extraer Texto (OCR)", self.mostrar_ocr)
        self.crear_menu_btn("🔐 Poner Clave", self.mostrar_proteccion)
        self.crear_menu_btn("🔓 Quitar Clave", self.mostrar_desproteccion) 
        self.crear_menu_btn("🔢 Números / Marcas", self.mostrar_marcas)

        self.main_frame = tk.Frame(root, bg="white", padx=30, pady=20)
        self.main_frame.pack(side="right", expand=True, fill="both")
        self.mostrar_inicio()

    def crear_menu_btn(self, texto, comando):
        btn = tk.Button(self.sidebar, text=texto, command=comando, bg="#34495e", 
                        fg="white", bd=0, font=("Arial", 10), pady=9, 
                        cursor="hand2", activebackground="#1abc9c")
        btn.pack(fill="x", padx=10, pady=2)

    def limpiar_pantalla(self, titulo):
        for widget in self.main_frame.winfo_children(): widget.destroy()
        self.archivos_cargados = []
        self.ruta_pdf_unico = ""
        tk.Label(self.main_frame, text=titulo, font=("Arial", 16, "bold"), bg="white", fg="#2c3e50").pack(side="top", anchor="w", pady=(0, 20))

    # --- NUEVA FUNCIÓN: QUITAR CLAVE ---
    def mostrar_desproteccion(self):
        self.limpiar_pantalla("🔓 Desproteger PDF (Quitar Contraseña)")
        tk.Label(self.main_frame, text="Esta función creará una copia del PDF sin contraseña.", bg="white", fg="#666").pack(anchor="w")
        
        tk.Button(self.main_frame, text="📂 Seleccionar PDF Protegido", command=self.sel_pdf_simple, bg="#3498db", fg="white").pack(fill="x", pady=10)
        self.lbl_info = tk.Label(self.main_frame, text="Ningún archivo", bg="white", fg="gray"); self.lbl_info.pack(pady=5)
        
        tk.Label(self.main_frame, text="Introduce la contraseña actual:", bg="white", font=("Arial", 10, "bold")).pack(pady=(15, 0))
        self.ent_pass = tk.Entry(self.main_frame, font=("Arial", 12), show="*")
        self.ent_pass.pack(fill="x", pady=5)
        
        tk.Button(self.main_frame, text="QUITAR PROTECCIÓN Y GUARDAR", bg="#27ae60", fg="white", font=("Arial", 11, "bold"), command=self.run_desproteccion).pack(fill="x", pady=20)

    def run_desproteccion(self):
        password = self.ent_pass.get()
        if not self.ruta_pdf_unico or not password:
            messagebox.showwarning("Error", "Selecciona el PDF e introduce su contraseña."); return
        
        out = filedialog.asksaveasfilename(defaultextension=".pdf", initialfile="desprotegido.pdf")
        if out:
            try:
                reader = PdfReader(self.ruta_pdf_unico)
                if reader.is_encrypted:
                    reader.decrypt(password)
                
                writer = PdfWriter()
                for page in reader.pages:
                    writer.add_page(page)
                
                with open(out, "wb") as f:
                    writer.write(f)
                
                messagebox.showinfo("Éxito", "Se ha generado una copia sin contraseña.")
                self.ent_pass.delete(0, tk.END)
            except Exception:
                messagebox.showerror("Error", "La contraseña es incorrecta o el archivo no está encriptado.")

    # --- FUNCIÓN: PONER CLAVE ---
    def mostrar_proteccion(self):
        self.limpiar_pantalla("🔐 Proteger PDF con Contraseña")
        tk.Button(self.main_frame, text="📂 Seleccionar PDF", command=self.sel_pdf_simple, bg="#3498db", fg="white").pack(fill="x")
        self.lbl_info = tk.Label(self.main_frame, text="Ningún archivo", bg="white", fg="gray"); self.lbl_info.pack(pady=5)
        tk.Label(self.main_frame, text="Escribe la contraseña deseada:", bg="white", font=("Arial", 10, "bold")).pack(pady=(15, 0))
        self.ent_pass = tk.Entry(self.main_frame, font=("Arial", 12), show="*")
        self.ent_pass.pack(fill="x", pady=5)
        tk.Button(self.main_frame, text="ENCRIPTAR Y GUARDAR", bg="#c0392b", fg="white", font=("Arial", 11, "bold"), command=self.run_proteccion).pack(fill="x", pady=20)

    def run_proteccion(self):
        password = self.ent_pass.get()
        if not self.ruta_pdf_unico or not password: return
        out = filedialog.asksaveasfilename(defaultextension=".pdf", initialfile="protegido.pdf")
        if out:
            try:
                reader = PdfReader(self.ruta_pdf_unico); writer = PdfWriter()
                for page in reader.pages: writer.add_page(page)
                writer.encrypt(password)
                with open(out, "wb") as f: writer.write(f)
                messagebox.showinfo("Éxito", "Contraseña aplicada."); self.ent_pass.delete(0, tk.END)
            except Exception as e: messagebox.showerror("Error", str(e))

    # --- FUNCIÓN: SEPARADOR PDF ---
    def mostrar_separador(self):
        self.limpiar_pantalla("📂 Separador de PDF")
        tk.Button(self.main_frame, text="📂 Seleccionar PDF Origen", command=self.sel_pdf_separador, bg="#3498db", fg="white").pack(fill="x", pady=5)
        self.lbl_ext_sep = tk.Label(self.main_frame, text="Ningún archivo", bg="white", fg="gray"); self.lbl_ext_sep.pack()
        self.lbl_pag_sep = tk.Label(self.main_frame, text="", bg="white", font=("Arial", 9, "bold"), fg="#2E86C1"); self.lbl_pag_sep.pack()
        tk.Label(self.main_frame, text="Indica los cortes (ej: 1-2, 3, 4-6):", bg="white", font=("Arial", 10, "bold")).pack(pady=(10, 0))
        self.ent_cortes = tk.Entry(self.main_frame, font=("Consolas", 11)); self.ent_cortes.pack(fill="x", pady=5)
        tk.Radiobutton(self.main_frame, text="Nombre original + nº", variable=self.naming_option, value=2, bg="white").pack(anchor="w")
        tk.Radiobutton(self.main_frame, text="Detectar 'Apellidos y nombre'", variable=self.naming_option, value=1, bg="white").pack(anchor="w")
        self.chk_abrir = tk.BooleanVar(value=True)
        tk.Checkbutton(self.main_frame, text="Abrir carpeta al finalizar", variable=self.chk_abrir, bg="white").pack(anchor="w")
        tk.Button(self.main_frame, text="EJECUTAR DIVISIÓN", bg="#28B463", fg="white", font=("Arial", 11, "bold"), command=self.run_separador).pack(fill="x", pady=15)

    def sel_pdf_separador(self):
        f = filedialog.askopenfilename(filetypes=[("PDF", "*.pdf")])
        if f:
            self.ruta_pdf_unico = f
            self.lbl_ext_sep.config(text=os.path.basename(f), fg="black")
            self.lbl_pag_sep.config(text=f"Total: {len(PdfReader(f).pages)} páginas")

    def run_separador(self):
        if not self.ruta_pdf_unico or not self.ent_cortes.get(): return
        dest = filedialog.askdirectory()
        if not dest: return
        try:
            reader = PdfReader(self.ruta_pdf_unico); base_name = os.path.splitext(os.path.basename(self.ruta_pdf_unico))[0]
            cortes = self.ent_cortes.get().replace(" ", "").split(",")
            for i, c in enumerate(cortes):
                writer = PdfWriter()
                if "-" in c:
                    ini, fin = map(int, c.split("-")); pags = list(range(ini-1, fin))
                else: pags = [int(c)-1]
                for p in pags: writer.add_page(reader.pages[p])
                name = ""
                if self.naming_option.get() == 1:
                    match = re.search(r"Apellidos y nombre:\s*([^\n\r]+)", reader.pages[pags[0]].extract_text())
                    name = match.group(1).strip().replace(',', '') if match else f"{base_name}_{i+1}"
                else: name = f"{base_name}-{i+1}"
                name = re.sub(r'[\\/*?:"<>|]', "", name)
                with open(os.path.join(dest, f"{name}.pdf"), "wb") as f_out: writer.write(f_out)
            messagebox.showinfo("Éxito", "Hecho."); self.ent_cortes.delete(0, tk.END)
            if self.chk_abrir.get(): os.startfile(dest)
        except Exception as e: messagebox.showerror("Error", str(e))

    # --- FUNCIÓN: NÚMEROS Y MARCAS ---
    def mostrar_marcas(self):
        self.limpiar_pantalla("🔢 Numeración y Marcas de Agua")
        tk.Button(self.main_frame, text="📂 Seleccionar PDF", command=self.sel_pdf_simple, bg="#3498db", fg="white").pack(fill="x")
        self.lbl_info = tk.Label(self.main_frame, text="Ningún archivo", bg="white", fg="gray"); self.lbl_info.pack(pady=5)
        tk.Label(self.main_frame, text="Texto a insertar:", bg="white", font=("Arial", 10, "bold")).pack(pady=(10, 0))
        self.ent_marca = tk.Entry(self.main_frame, font=("Arial", 11)); self.ent_marca.pack(fill="x", pady=5)
        self.var_num = tk.BooleanVar(value=True)
        tk.Checkbutton(self.main_frame, text="Añadir nº de página", variable=self.var_num, bg="white").pack(anchor="w")
        tk.Button(self.main_frame, text="APLICAR Y GUARDAR", bg="#8e44ad", fg="white", font=("Arial", 11, "bold"), command=self.run_marcas).pack(fill="x", pady=20)

    def run_marcas(self):
        if not self.ruta_pdf_unico: return
        out = filedialog.asksaveasfilename(defaultextension=".pdf", initialfile="marcado.pdf")
        if out:
            try:
                doc = fitz.open(self.ruta_pdf_unico)
                for i, page in enumerate(doc):
                    msg = self.ent_marca.get()
                    if self.var_num.get(): msg += f" | Pág. {i+1} de {len(doc)}"
                    page.insert_text((50, page.rect.height - 30), msg, fontsize=10, color=(0.7, 0.7, 0.7))
                doc.save(out); doc.close(); messagebox.showinfo("Éxito", "Marcas añadidas.")
            except Exception as e: messagebox.showerror("Error", str(e))

    # --- MÉTODOS DE SOPORTE Y RESTO DE HERRAMIENTAS ---
    def sel_pdf_simple(self):
        f = filedialog.askopenfilename(filetypes=[("PDF", "*.pdf")])
        if f:
            self.ruta_pdf_unico = f
            self.lbl_info.config(text=os.path.basename(f), fg="black")

    def mostrar_inicio(self):
        self.limpiar_pantalla("Bienvenid@")
        tk.Label(self.main_frame, text="Selecciona una herramienta para comenzar.", font=("Arial", 11), bg="white", fg="gray").pack(side="top", anchor="w")
        tk.Label(self.main_frame, text="RaquelCM", font=("Arial", 10), bg="white", fg="blue").pack(side="bottom", anchor="e")
    def mostrar_img_to_pdf(self):
        self.limpiar_pantalla("📷 Imágenes a PDF")
        f_btns = tk.Frame(self.main_frame, bg="white"); f_btns.pack(fill="x")
        tk.Button(f_btns, text="➕ Fotos", command=lambda: self.add_img_files(lista), bg="#3498db", fg="white").pack(side="left", expand=True, fill="x", padx=2)
        tk.Button(f_btns, text="🗑️ Vaciar", command=lambda: self.limpiar_lista_gen(lista), bg="#95a5a6", fg="white").pack(side="left", expand=True, fill="x", padx=2)
        lista = tk.Listbox(self.main_frame, height=12); lista.pack(fill="both", expand=True, pady=10)
        tk.Button(self.main_frame, text="GENERAR PDF", bg="#e74c3c", fg="white", font=("Arial", 11, "bold"), height=2, command=self.run_img_to_pdf).pack(fill="x")

    def run_img_to_pdf(self):
        if not self.archivos_cargados: return
        out = filedialog.asksaveasfilename(defaultextension=".pdf")
        if out:
            imgs = [Image.open(p).convert('RGB') for p in self.archivos_cargados]
            imgs[0].save(out, save_all=True, append_images=imgs[1:])
            messagebox.showinfo("Éxito", "PDF creado.")

    def mostrar_unificador(self):
        self.limpiar_pantalla("🔗 Unificador de PDFs")
        tk.Button(self.main_frame, text="➕ Añadir PDFs", command=lambda: self.sel_doc([("PDF", "*.pdf")], lista)).pack(fill="x")
        lista = tk.Listbox(self.main_frame, height=10); lista.pack(fill="both", expand=True, pady=10)
        tk.Button(self.main_frame, text="FUSIONAR", bg="#8e44ad", fg="white", font=("Arial", 11, "bold"), command=self.run_uni).pack(fill="x")

    def run_uni(self):
        if not self.archivos_cargados: return
        out = filedialog.asksaveasfilename(defaultextension=".pdf")
        if out:
            w = PdfWriter()
            for p in self.archivos_cargados: w.append(p)
            with open(out, "wb") as f: w.write(f)
            messagebox.showinfo("Éxito", "Unificados.")

    def mostrar_compresor(self):
        self.limpiar_pantalla("🗜️ Compresor de PDF")
        tk.Button(self.main_frame, text="➕ Seleccionar PDF", command=lambda: self.sel_doc([("PDF", "*.pdf")], lista)).pack(fill="x")
        lista = tk.Listbox(self.main_frame, height=8); lista.pack(fill="x", pady=10)
        tk.Button(self.main_frame, text="COMPRIMIR", bg="#2980b9", fg="white", font=("Arial", 11, "bold"), command=self.run_compresor).pack(fill="x")

    def run_compresor(self):
        if not self.archivos_cargados: return
        out = filedialog.asksaveasfilename(defaultextension=".pdf")
        if out:
            doc = fitz.open(self.archivos_cargados[0])
            doc.save(out, garbage=4, deflate=True); doc.close()
            messagebox.showinfo("Éxito", "Comprimido.")

    def mostrar_extractor(self):
        self.limpiar_pantalla("✂️ Extractor de Páginas")
        tk.Button(self.main_frame, text="📂 Seleccionar PDF", command=self.sel_pdf_simple, bg="#3498db", fg="white").pack(fill="x")
        self.lbl_info = tk.Label(self.main_frame, text="Ningún archivo", bg="white", fg="gray"); self.lbl_info.pack()
        tk.Label(self.main_frame, text="Rango (ej: 1, 3, 5-10):", bg="white").pack()
        self.ent_r = tk.Entry(self.main_frame, font=("Arial", 11)); self.ent_r.pack(fill="x", pady=5)
        tk.Button(self.main_frame, text="EXTRAER", bg="#e67e22", fg="white", command=self.run_ext).pack(fill="x")

    def run_ext(self):
        if not self.ruta_pdf_unico: return
        out = filedialog.asksaveasfilename(defaultextension=".pdf")
        if out:
            reader = PdfReader(self.ruta_pdf_unico); writer = PdfWriter()
            partes = self.ent_r.get().replace(" ", "").split(",")
            for p in partes:
                if "-" in p:
                    i, f = map(int, p.split("-"))
                    for n in range(i, f+1): writer.add_page(reader.pages[n-1])
                else: writer.add_page(reader.pages[int(p)-1])
            with open(out, "wb") as f: writer.write(f)
            messagebox.showinfo("Éxito", "Extraído.")

    def mostrar_ocr(self):
        self.limpiar_pantalla("🔍 Extraer Texto (OCR)")
        tk.Button(self.main_frame, text="➕ Seleccionar PDF", command=lambda: self.sel_doc([("PDF", "*.pdf")], lista)).pack(fill="x")
        lista = tk.Listbox(self.main_frame, height=4); lista.pack(fill="x", pady=10)
        self.txt_res = tk.Text(self.main_frame, height=12, bg="#f8f9fa"); self.txt_res.pack(fill="both", expand=True)
        tk.Button(self.main_frame, text="🔍 EXTRAER", command=self.run_ocr, bg="#16a085", fg="white").pack(fill="x", pady=5)

    def run_ocr(self):
        if not self.archivos_cargados: return
        doc = fitz.open(self.archivos_cargados[0]); texto = ""
        for pag in doc: texto += pag.get_text() + "\n"
        self.txt_res.delete("1.0", tk.END); self.txt_res.insert(tk.END, texto); doc.close()

    def sel_doc(self, tipos, l_ui):
        fs = filedialog.askopenfilenames(filetypes=tipos)
        if fs: self.archivos_cargados.extend(list(fs)); self.actualizar_lista_visual(l_ui)

    def add_img_files(self, l_ui):
        fs = filedialog.askopenfilenames(filetypes=[("Imágenes", "*.jpg *.png")])
        if fs: self.archivos_cargados.extend(list(fs)); self.actualizar_lista_visual(l_ui)

    def actualizar_lista_visual(self, l_ui):
        l_ui.delete(0, tk.END)
        for f in self.archivos_cargados: l_ui.insert(tk.END, os.path.basename(f))

    def limpiar_lista_gen(self, l_ui):
        self.archivos_cargados = []; l_ui.delete(0, tk.END)

    def mostrar_p_to_img(self):
        self.limpiar_pantalla("🖼️ PDF a Imágenes")
        tk.Button(self.main_frame, text="➕ PDF", command=lambda: self.sel_doc([("PDF", "*.pdf")], lista)).pack(fill="x")
        lista = tk.Listbox(self.main_frame, height=4); lista.pack(fill="x", pady=10)
        tk.Button(self.main_frame, text="CONVERTIR", bg="#27ae60", fg="white", command=self.run_p2img).pack(fill="x")

    def run_p2img(self):
        if not self.archivos_cargados: return
        dest = filedialog.askdirectory()
        if dest:
            doc = fitz.open(self.archivos_cargados[0])
            for i, pag in enumerate(doc): pag.get_pixmap().save(os.path.join(dest, f"pag_{i+1}.png"))
            doc.close(); os.startfile(dest)

    def mostrar_w_to_p(self):
        self.limpiar_pantalla("📄 Word a PDF")
        tk.Button(self.main_frame, text="➕ Word", command=lambda: self.sel_doc([("Word", "*.docx")], lista)).pack(fill="x")
        lista = tk.Listbox(self.main_frame, height=4); lista.pack(fill="x", pady=10)
        tk.Button(self.main_frame, text="CONVERTIR", bg="#c0392b", fg="white", command=self.run_w2p).pack(fill="x")

    def run_w2p(self):
        if not self.archivos_cargados: return
        dest = filedialog.askdirectory()
        if dest:
            pythoncom.CoInitialize(); word = win32com.client.DispatchEx("Word.Application")
            for r in self.archivos_cargados:
                doc = word.Documents.Open(os.path.abspath(r), ReadOnly=1)
                doc.ExportAsFixedFormat(os.path.join(dest, os.path.splitext(os.path.basename(r))[0] + ".pdf"), 17)
                doc.Close(0)
            word.Quit(); messagebox.showinfo("Éxito", "Hecho.")

    def mostrar_p_to_w(self):
        self.limpiar_pantalla("📝 PDF a Word")
        tk.Button(self.main_frame, text="➕ PDF", command=lambda: self.sel_doc([("PDF", "*.pdf")], lista)).pack(fill="x")
        lista = tk.Listbox(self.main_frame, height=4); lista.pack(fill="x", pady=10)
        tk.Button(self.main_frame, text="CONVERTIR", bg="#2980b9", fg="white", command=self.run_p2w).pack(fill="x")

    def run_p2w(self):
        if not self.archivos_cargados: return
        dest = filedialog.askdirectory()
        if dest:
            for r in self.archivos_cargados:
                cv = Converter(r); cv.convert(os.path.join(dest, os.path.splitext(os.path.basename(r))[0] + ".docx")); cv.close()
            messagebox.showinfo("Éxito", "Hecho.")

if __name__ == "__main__":
    root = tk.Tk()
    app = SuiteDocumental(root)
    root.mainloop()