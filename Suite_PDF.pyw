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
from io import BytesIO

class SuiteDocumental:
    def __init__(self, root):
        self.root = root
        self.nombre_suite = "Suite PDF"
        self.root.title(self.nombre_suite)

        # --- CÁLCULO DE CENTRADO DINÁMICO ---
        ancho_ventana = 950
        alto_ventana = 750

        # Obtener el ancho y alto de TU pantalla real
        ancho_pantalla = self.root.winfo_screenwidth()
        alto_pantalla = self.root.winfo_screenheight()

        # Calcular X para que esté centrado (Ancho total - Ancho ventana) / 2
        pos_x = (ancho_pantalla // 2) - (ancho_ventana // 2)
        
        # Mantener Y en 0 para que esté pegada arriba como querías
        pos_y = 0 

        # Aplicar la geometría: "950x750+X+0"
        self.root.geometry(f"{ancho_ventana}x{alto_ventana}+{pos_x}+{pos_y}")

        # --- AÑADIR ICONO PNG ---
        try:
            # Reemplaza 'icono.png' por el nombre real de tu archivo
            self.icono = tk.PhotoImage(file='pdf-icono.png')
            self.root.iconphoto(False, self.icono)
        except Exception:
            # Si la imagen no existe, el programa seguirá abriéndose sin error
            pass
        # ------------------------
        self.root.configure(bg="#f0f2f5")
    
        self.archivos_cargados = []
        self.destino_seleccionado = ""
        self.ruta_pdf_unico = ""

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
        self.crear_menu_btn("🔗 Unificador PDF", self.mostrar_unificador)
        self.crear_menu_btn("🗜️ Compresor PDF", self.mostrar_compresor)
        self.crear_menu_btn("🔍 Extraer Texto (OCR)", self.mostrar_ocr)

        self.main_frame = tk.Frame(root, bg="white", padx=30, pady=20)
        self.main_frame.pack(side="right", expand=True, fill="both")
        
        self.mostrar_inicio()

    def crear_menu_btn(self, texto, comando):
        btn = tk.Button(self.sidebar, text=texto, command=comando, bg="#34495e", 
                        fg="white", bd=0, font=("Arial", 10), pady=12, 
                        cursor="hand2", activebackground="#1abc9c")
        btn.pack(fill="x", padx=10, pady=2)

    def limpiar_pantalla(self, titulo):
        for widget in self.main_frame.winfo_children():
            widget.destroy()
        self.archivos_cargados = []
        self.destino_seleccionado = ""
        # Cambiamos pack(anchor="w") por uno con un pequeño margen superior pero fijo arriba
        tk.Label(self.main_frame, text=titulo, font=("Arial", 16, "bold"), 
                 bg="white", fg="#2c3e50").pack(side="top", anchor="w", pady=(0, 20))

    def actualizar_lista_visual(self, lista_ui):
        lista_ui.delete(0, tk.END)
        for i, f in enumerate(self.archivos_cargados, 1):
            lista_ui.insert(tk.END, f"{i}. {os.path.basename(f)}")

    # --- HERRAMIENTA: IMÁGENES A PDF ---
    def mostrar_img_to_pdf(self):
        self.limpiar_pantalla("📷 Imágenes a PDF")
        f_btns = tk.Frame(self.main_frame, bg="white")
        f_btns.pack(fill="x")
        tk.Button(f_btns, text="➕ Fotos", command=lambda: self.add_img_files(lista), bg="#3498db", fg="white").pack(side="left", expand=True, fill="x", padx=2)
        tk.Button(f_btns, text="📁 Carpeta", command=lambda: self.add_img_folder(lista), bg="#2980b9", fg="white").pack(side="left", expand=True, fill="x", padx=2)
        tk.Button(f_btns, text="❌ Quitar", command=lambda: self.quitar_elemento_sel(lista), bg="#e67e22", fg="white").pack(side="left", expand=True, fill="x", padx=2)
        tk.Button(f_btns, text="🗑️ Vaciar", command=lambda: self.limpiar_lista_gen(lista), bg="#95a5a6", fg="white").pack(side="left", expand=True, fill="x", padx=2)
        
        f_mid = tk.Frame(self.main_frame, bg="white")
        f_mid.pack(fill="both", expand=True, pady=10)
        lista = tk.Listbox(f_mid, height=12, font=("Arial", 10), selectmode=tk.SINGLE)
        lista.pack(side="left", fill="both", expand=True)
        
        f_arrows = tk.Frame(f_mid, bg="white")
        f_arrows.pack(side="right", padx=10)
        tk.Button(f_arrows, text="▲", command=lambda: self.mover_elemento(lista, -1), width=4).pack(pady=5)
        tk.Button(f_arrows, text="▼", command=lambda: self.mover_elemento(lista, 1), width=4).pack(pady=5)
        
        tk.Button(self.main_frame, text="GENERAR ÁLBUM PDF", bg="#e74c3c", fg="white", font=("Arial", 11, "bold"), height=2, command=self.run_img_to_pdf).pack(fill="x", pady=10)

    def run_img_to_pdf(self):
        if not self.archivos_cargados: return
        base = os.path.splitext(os.path.basename(self.archivos_cargados[0]))[0]
        out = filedialog.asksaveasfilename(defaultextension=".pdf", initialfile=f"Album_{base}.pdf")
        if out:
            try:
                imgs = [Image.open(p).convert('RGB') for p in self.archivos_cargados]
                imgs[0].save(out, save_all=True, append_images=imgs[1:])
                if messagebox.askyesno("Éxito", "¿Abrir carpeta?"): os.startfile(os.path.dirname(out))
            except Exception as e: messagebox.showerror("Error", str(e))

    # --- HERRAMIENTA: UNIFICADOR ---
    def mostrar_unificador(self):
        self.limpiar_pantalla("🔗 Unificador de PDFs")
        f_top = tk.Frame(self.main_frame, bg="white")
        f_top.pack(fill="x")
        tk.Button(f_top, text="➕ Añadir PDFs", command=lambda: self.sel_doc([("PDF", "*.pdf")], lista)).pack(side="left", expand=True, fill="x", padx=2)
        tk.Button(f_top, text="🗑️ Vaciar", command=lambda: self.limpiar_lista_gen(lista), bg="#95a5a6", fg="white").pack(side="left", expand=True, fill="x", padx=2)
        
        f_l = tk.Frame(self.main_frame, bg="white")
        f_l.pack(fill="both", expand=True, pady=10)
        lista = tk.Listbox(f_l, height=10, font=("Arial", 10))
        lista.pack(side="left", fill="both", expand=True)
        
        f_b = tk.Frame(f_l, bg="white")
        f_b.pack(side="right", padx=5)
        tk.Button(f_b, text="▲", command=lambda: self.mover_elemento(lista, -1), width=3).pack(pady=2)
        tk.Button(f_b, text="▼", command=lambda: self.mover_elemento(lista, 1), width=3).pack(pady=2)
        
        tk.Button(self.main_frame, text="FUSIONAR ARCHIVOS", bg="#8e44ad", fg="white", font=("Arial", 11, "bold"), height=2, command=self.run_uni).pack(fill="x", pady=10)

    def run_uni(self):
        if not self.archivos_cargados: return
        base = os.path.splitext(os.path.basename(self.archivos_cargados[0]))[0]
        out = filedialog.asksaveasfilename(defaultextension=".pdf", initialfile=f"{base}_unificado.pdf")
        if out:
            try:
                w = PdfWriter()
                for p in self.archivos_cargados: w.append(p)
                with open(out, "wb") as f: w.write(f)
                if messagebox.askyesno("Éxito", "¿Abrir carpeta?"): os.startfile(os.path.dirname(out))
            except Exception as e: messagebox.showerror("Error", str(e))

    # --- HERRAMIENTA: COMPRESOR ---
    def mostrar_compresor(self):
        self.limpiar_pantalla("🗜️ Compresor de PDF")
        tk.Button(self.main_frame, text="➕ Seleccionar PDF", command=lambda: self.sel_doc([("PDF", "*.pdf")], lista)).pack(fill="x")
        lista = tk.Listbox(self.main_frame, height=8); lista.pack(fill="x", pady=10)
        tk.Button(self.main_frame, text="COMPRIMIR Y GUARDAR", bg="#2980b9", fg="white", font=("Arial", 11, "bold"), command=self.run_compresor).pack(fill="x", pady=10)

    def run_compresor(self):
        if not self.archivos_cargados: return
        ruta_orig = self.archivos_cargados[0]
        
        win_calidad = tk.Toplevel(self.root)
        win_calidad.title("Nivel de Compresión")
        win_calidad.geometry("300x200")
        win_calidad.grab_set()

        def aplicar(modo):
            win_calidad.destroy()
            out = filedialog.asksaveasfilename(defaultextension=".pdf", initialfile=f"comprimido_{os.path.basename(ruta_orig)}")
            if not out: return
            try:
                doc = fitz.open(ruta_orig)
                if modo != "alta":
                    calidad = 50 if modo == "media" else 20
                    for page in doc:
                        for img in page.get_images():
                            xref = img[0]
                            base = doc.extract_image(xref)
                            img_pil = Image.open(BytesIO(base["image"]))
                            if modo == "baja": img_pil.thumbnail((1000, 1000))
                            new_bytes = BytesIO()
                            img_pil.save(new_bytes, format="JPEG", quality=calidad, optimize=True)
                            page.replace_image(xref, stream=new_bytes.getvalue())
                
                doc.save(out, garbage=4, deflate=True)
                doc.close()
                if messagebox.askyesno("Éxito", "¿Abrir carpeta?"): os.startfile(os.path.dirname(out))
            except Exception as e: messagebox.showerror("Error", str(e))

        tk.Button(win_calidad, text="ALTA (Estándar)", command=lambda: aplicar("alta"), bg="#ecf0f1", width=25).pack(pady=5)
        tk.Button(win_calidad, text="MEDIA (Recomendado)", command=lambda: aplicar("media"), bg="#d4e6f1", width=25).pack(pady=5)
        tk.Button(win_calidad, text="BAJA (Mínimo peso)", command=lambda: aplicar("baja"), bg="#a9cce3", width=25).pack(pady=5)

    # --- HERRAMIENTA: EXTRACTOR ---
    def mostrar_extractor(self):
        self.limpiar_pantalla("✂️ Extractor de Páginas")
        tk.Button(self.main_frame, text="📂 Seleccionar PDF Origen", command=self.sel_pdf_un, bg="#3498db", fg="white").pack(fill="x", pady=5)
        self.lbl_ext = tk.Label(self.main_frame, text="Ningún archivo", bg="white", fg="gray"); self.lbl_ext.pack()
        self.lbl_paginas = tk.Label(self.main_frame, text="", bg="white", font=("Arial", 10, "bold")); self.lbl_paginas.pack()
        
        tk.Label(self.main_frame, text="Ejemplo: 1, 3, 5-10", bg="white", fg="blue").pack(pady=5)
        self.ent_r = tk.Entry(self.main_frame, font=("Arial", 11)); self.ent_r.pack(fill="x", pady=5)
        tk.Button(self.main_frame, text="EXTRAER", bg="#e67e22", fg="white", font=("Arial", 11, "bold"), command=self.run_ext).pack(fill="x", pady=10)

    def sel_pdf_un(self):
        f = filedialog.askopenfilename(filetypes=[("PDF", "*.pdf")])
        if f:
            self.ruta_pdf_unico = f
            self.lbl_ext.config(text=os.path.basename(f))
            self.lbl_paginas.config(text=f"Total: {len(PdfReader(f).pages)} páginas")

    def run_ext(self):
        if not self.ruta_pdf_unico: return
        out = filedialog.asksaveasfilename(defaultextension=".pdf", initialfile="extraido.pdf")
        if out:
            try:
                reader = PdfReader(self.ruta_pdf_unico); writer = PdfWriter()
                partes = self.ent_r.get().replace(" ", "").split(",")
                for p in partes:
                    if "-" in p:
                        i, f = map(int, p.split("-"))
                        for n in range(i, f+1): writer.add_page(reader.pages[n-1])
                    else: writer.add_page(reader.pages[int(p)-1])
                with open(out, "wb") as f: writer.write(f)
                if messagebox.askyesno("Éxito", "¿Abrir carpeta?"): os.startfile(os.path.dirname(out))
            except Exception as e: messagebox.showerror("Error", "Revisa el rango")

    # --- HERRAMIENTAS DE TEXTO ---
    def mostrar_ocr(self):
        self.limpiar_pantalla("🔍 Extraer Texto (OCR)")
        tk.Button(self.main_frame, text="➕ Seleccionar PDF", command=lambda: self.sel_doc([("PDF", "*.pdf")], lista)).pack(fill="x")
        lista = tk.Listbox(self.main_frame, height=4); lista.pack(fill="x", pady=10)
        self.txt_res = tk.Text(self.main_frame, height=12, bg="#f8f9fa"); self.txt_res.pack(fill="both", expand=True)
        f_b = tk.Frame(self.main_frame, bg="white"); f_b.pack(fill="x", pady=5)
        tk.Button(f_b, text="🔍 EXTRAER", command=self.run_ocr, bg="#16a085", fg="white").pack(side="left", expand=True, fill="x")
        tk.Button(f_b, text="💾 GUARDAR .TXT", command=self.guardar_texto_txt, bg="#34495e", fg="white").pack(side="left", expand=True, fill="x")

    def run_ocr(self):
        if not self.archivos_cargados: return
        try:
            doc = fitz.open(self.archivos_cargados[0]); texto = ""
            for pag in doc: texto += pag.get_text() + "\n" + "-"*20 + "\n"
            self.txt_res.delete("1.0", tk.END); self.txt_res.insert(tk.END, texto); doc.close()
        except Exception as e: messagebox.showerror("Error", str(e))

    def guardar_texto_txt(self):
        cont = self.txt_res.get("1.0", tk.END).strip()
        if not cont: return
        out = filedialog.asksaveasfilename(defaultextension=".txt", initialfile="texto.txt")
        if out:
            with open(out, "w", encoding="utf-8") as f: f.write(cont)
            if messagebox.askyesno("Éxito", "¿Abrir carpeta?"): os.startfile(os.path.dirname(out))

    # --- FUNCIONES COMUNES DE SOPORTE ---
    def sel_doc(self, tipos, l_ui):
        fs = filedialog.askopenfilenames(filetypes=tipos)
        if fs:
            self.archivos_cargados.extend(list(fs))
            self.actualizar_lista_visual(l_ui)

    def add_img_files(self, l_ui):
        fs = filedialog.askopenfilenames(filetypes=[("Imágenes", "*.jpg *.jpeg *.png *.bmp")])
        if fs:
            self.archivos_cargados.extend(list(fs))
            self.actualizar_lista_visual(l_ui)

    def add_img_folder(self, l_ui):
        folder = filedialog.askdirectory()
        if folder:
            exts = {'.jpg', '.jpeg', '.png', '.bmp'}
            for f in sorted(os.listdir(folder)):
                if os.path.splitext(f)[1].lower() in exts:
                    self.archivos_cargados.append(os.path.join(folder, f))
            self.actualizar_lista_visual(l_ui)

    def quitar_elemento_sel(self, l_ui):
        sel = l_ui.curselection()
        if sel:
            idx = sel[0]
            del self.archivos_cargados[idx]
            l_ui.delete(idx)

    def mover_elemento(self, l_ui, d):
        sel = l_ui.curselection()
        if not sel: return
        i = sel[0]; ni = i + d
        if 0 <= ni < len(self.archivos_cargados):
            self.archivos_cargados[i], self.archivos_cargados[ni] = self.archivos_cargados[ni], self.archivos_cargados[i]
            self.actualizar_lista_visual(l_ui); l_ui.selection_set(ni)

    def limpiar_lista_gen(self, l_ui):
        self.archivos_cargados = []
        l_ui.delete(0, tk.END)

    def mostrar_inicio(self):
        self.limpiar_pantalla("Bienvenido")
        # Quitamos el expand=True para que se pegue arriba
        tk.Label(self.main_frame, text="Selecciona una herramienta en el menú de la izquierda para comenzar.", 
                 font=("Arial", 11), bg="white", fg="gray").pack(side="top", anchor="w")

    # --- OTROS MÉTODOS (Word/Imágenes) ---
    def sel_dest(self, lbl):
        self.destino_seleccionado = filedialog.askdirectory()
        if self.destino_seleccionado: lbl.config(text=f"📂 {os.path.basename(self.destino_seleccionado)}", fg="blue")

    def mostrar_p_to_img(self):
        self.limpiar_pantalla("🖼️ PDF a Imágenes")
        tk.Button(self.main_frame, text="➕ Seleccionar PDF", command=lambda: self.sel_doc([("PDF", "*.pdf")], lista)).pack(fill="x")
        lista = tk.Listbox(self.main_frame, height=4); lista.pack(fill="x", pady=10)
        lbl = tk.Label(self.main_frame, text="Sin destino", fg="red", bg="white"); lbl.pack()
        tk.Button(self.main_frame, text="📁 Carpeta Salida", command=lambda: self.sel_dest(lbl)).pack(fill="x")
        tk.Button(self.main_frame, text="CONVERTIR", bg="#27ae60", fg="white", command=self.run_p2img).pack(fill="x", pady=10)

    def run_p2img(self):
        if not self.archivos_cargados or not self.destino_seleccionado: return
        doc = fitz.open(self.archivos_cargados[0])
        for i, pag in enumerate(doc): pag.get_pixmap().save(os.path.join(self.destino_seleccionado, f"pag_{i+1}.png"))
        doc.close(); os.startfile(self.destino_seleccionado)

    def mostrar_w_to_p(self):
        self.limpiar_pantalla("📄 Word a PDF")
        tk.Button(self.main_frame, text="➕ Word", command=lambda: self.sel_doc([("Word", "*.docx")], lista)).pack(fill="x")
        lista = tk.Listbox(self.main_frame, height=4); lista.pack(fill="x", pady=10)
        lbl = tk.Label(self.main_frame, text="Sin destino", fg="red", bg="white"); lbl.pack()
        tk.Button(self.main_frame, text="📁 Carpeta Salida", command=lambda: self.sel_dest(lbl)).pack(fill="x")
        tk.Button(self.main_frame, text="CONVERTIR", bg="#c0392b", fg="white", command=self.run_w2p).pack(fill="x", pady=10)

    def run_w2p(self):
        if not self.archivos_cargados or not self.destino_seleccionado: return
        pythoncom.CoInitialize()
        word = win32com.client.DispatchEx("Word.Application")
        for r in self.archivos_cargados:
            doc = word.Documents.Open(os.path.abspath(r), ReadOnly=1)
            doc.ExportAsFixedFormat(os.path.join(self.destino_seleccionado, os.path.splitext(os.path.basename(r))[0] + ".pdf"), 17)
            doc.Close(0)
        word.Quit(); messagebox.showinfo("Éxito", "Hecho.")

    def mostrar_p_to_w(self):
        self.limpiar_pantalla("📝 PDF a Word")
        tk.Button(self.main_frame, text="➕ PDF", command=lambda: self.sel_doc([("PDF", "*.pdf")], lista)).pack(fill="x")
        lista = tk.Listbox(self.main_frame, height=4); lista.pack(fill="x", pady=10)
        lbl = tk.Label(self.main_frame, text="Sin destino", fg="red", bg="white"); lbl.pack()
        tk.Button(self.main_frame, text="📁 Carpeta Salida", command=lambda: self.sel_dest(lbl)).pack(fill="x")
        tk.Button(self.main_frame, text="CONVERTIR", bg="#2980b9", fg="white", command=self.run_p2w).pack(fill="x", pady=10)

    def run_p2w(self):
        if not self.archivos_cargados or not self.destino_seleccionado: return
        for r in self.archivos_cargados:
            cv = Converter(r); cv.convert(os.path.join(self.destino_seleccionado, os.path.splitext(os.path.basename(r))[0] + ".docx")); cv.close()
        messagebox.showinfo("Éxito", "Hecho.")

if __name__ == "__main__":
    root = tk.Tk()
    app = SuiteDocumental(root)
    root.mainloop()