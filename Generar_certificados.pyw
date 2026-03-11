# -*- coding: utf-8 -*-
import os, re, unicodedata
import pandas as pd
from docx import Document
from datetime import datetime
from dateutil import parser
import tkinter as tk
from tkinter import filedialog, messagebox
import threading

# --- CONFIGURACIÓN DE NEGRIFAS ---
MESES = {1:"enero",2:"febrero",3:"marzo",4:"abril",5:"mayo",6:"junio",
         7:"julio",8:"agosto",9:"septiembre",10:"octubre",11:"noviembre",12:"diciembre"}

NEG_CAMPOS = ["nombre", "dni", "media"]
NEG_FRASES = ["Educación Secundaria Obligatoria"]

# --- LÓGICA DE PROCESAMIENTO  ---
def normalizar(t):
    if not isinstance(t,str): t=str(t)
    t=t.strip().lower()
    return ''.join(c for c in unicodedata.normalize('NFD',t) if unicodedata.category(c)!='Mn')

def fecha_castellano(v):
    try:
        if isinstance(v,(int,float)): f = datetime(1899,12,30) + pd.to_timedelta(v,"D")
        else: f = parser.parse(str(v), dayfirst=True)
        return f"{f.day} de {MESES[f.month]} de {f.year}"
    except: return str(v)

def aplicar_genero_y_marcadores(texto, sexo, reemplazos):
    s = str(sexo).strip().upper()
    es_m = "M" in s
    cambios = {
        r"D\./Dña\.": "D." if es_m else "Dña.",
        r"nacido/a": "nacido" if es_m else "nacida",
        r"del/de la": "del" if es_m else "de la",
        r"interesado/a": "interesado" if es_m else "interesada",
        r"alumno/a": "alumno" if es_m else "alumna",
        r"el/la": "el" if es_m else "la"
    }
    for original, sustituto in cambios.items():
        texto = re.sub(original, sustituto, texto, flags=re.IGNORECASE)
    for frase in NEG_FRASES:
        texto = texto.replace(frase, f"<b>{frase}</b>")
    for m, v in reemplazos.items():
        if normalizar(m) in NEG_CAMPOS:
            texto = texto.replace(f"[{m}]", f"<b>{v}</b>")
        else:
            texto = texto.replace(f"[{m}]", str(v))
    return texto

def reconstruir_parrafo(parrafo, texto_con_tags):
    if not parrafo.runs: return
    run_base = parrafo.runs[0]
    f_name, f_size, bold_base = run_base.font.name, run_base.font.size, run_base.bold
    for r in parrafo.runs: r.text = ""
    partes = re.split(r"(<b>.*?</b>)", texto_con_tags)
    for parte in partes:
        if parte.startswith("<b>") and parte.endswith("</b>"):
            run = parrafo.add_run(parte[3:-4])
            run.bold = True
        else:
            if not parte: continue
            run = parrafo.add_run(parte)
            run.bold = bold_base
        if f_name:
            run.font.name, run.font.size = f_name, f_size

def procesar_todo(doc, reemplazos, sexo):
    for p in doc.paragraphs:
        txt_mod = aplicar_genero_y_marcadores(p.text, sexo, reemplazos)
        reconstruir_parrafo(p, txt_mod)
    for tabla in doc.tables:
        for fila in tabla.rows:
            for celda in fila.cells:
                for p in celda.paragraphs:
                    txt_mod = aplicar_genero_y_marcadores(p.text, sexo, reemplazos)
                    reconstruir_parrafo(p, txt_mod)

# --- INTERFAZ GRÁFICA ---
class AppCertificadosCentrado:
    def __init__(self, root):
        self.root = root
        self.root.title("Generador de Títulos")
        # 1. Definimos el tamaño que queremos
        ancho = 520
        alto = 400
        
        # 2. Calculamos la posición (Esto es lo que va dentro de init)
        pos_x = (self.root.winfo_screenwidth() // 2) - (ancho // 2)
        
        # 3. Aplicamos la magia: Ancho x Alto + Derecha + Arriba (20)
        self.root.geometry(f"{ancho}x{alto}+{pos_x}+20")
        self.root.resizable(False, False)
        
        self.plantilla = ""
        self.excel = ""

        # Título centrado
        tk.Label(root, text="🎓 Generador de Certificados de Título", 
                 font=("Segoe UI", 14, "bold")).pack(pady=(30, 20))

        # Contenedor central para alineación
        container = tk.Frame(root)
        container.pack(expand=True)

        # Botón 1 y su tick
        f1 = tk.Frame(container)
        f1.pack(pady=5)
        self.btn_p = tk.Button(f1, text="1. Seleccionar Plantilla Word", command=self.sel_p, width=30)
        self.btn_p.pack(side="left")
        self.tick_p = tk.Label(f1, text="", fg="#28a745", font=("Arial", 10, "bold"), width=20, anchor="w")
        self.tick_p.pack(side="left", padx=5)

        # Botón 2 y su tick
        f2 = tk.Frame(container)
        f2.pack(pady=5)
        self.btn_e = tk.Button(f2, text="2. Seleccionar Datos Excel", command=self.sel_e, width=30)
        self.btn_e.pack(side="left")
        self.tick_e = tk.Label(f2, text="", fg="#28a745", font=("Arial", 10, "bold"), width=20, anchor="w")
        self.tick_e.pack(side="left", padx=5)

        # Botón Generar 
        self.btn_go = tk.Button(root, text="GENERAR DOCUMENTACIÓN", command=self.hilo, 
                                bg="#88ffff", fg="white", font=("Segoe UI", 11, "bold"), 
                                width=35, height=2, state="disabled", relief="flat")
        self.btn_go.pack(pady=(30, 10))

        self.lbl_status = tk.Label(root, text="Faltan archivos por seleccionar", fg="#6c757d")
        self.lbl_status.pack(pady=(0, 20))

    def verificar(self):
        if self.plantilla and self.excel:
            self.btn_go.config(state="normal", bg="#28a745", cursor="hand2")
            self.lbl_status.config(text="¡Todo listo para generar!", fg="#28a745")

    def sel_p(self):
        self.plantilla = filedialog.askopenfilename(filetypes=[("Word", "*.docx")])
        if self.plantilla:
            nombre = os.path.basename(self.plantilla)
            self.tick_p.config(text=f"✔️ {nombre[:15]}...")
            self.verificar()

    def sel_e(self):
        self.excel = filedialog.askopenfilename(filetypes=[("Excel", "*.xlsx")])
        if self.excel:
            nombre = os.path.basename(self.excel)
            self.tick_e.config(text=f"✔️ {nombre[:15]}...")
            self.verificar()

    def hilo(self):
        dest = filedialog.askdirectory(title="Seleccionar carpeta de guardado")
        if dest:
            self.btn_go.config(state="disabled", text="Procesando...", bg="#6c757d")
            threading.Thread(target=self.run, args=(dest,), daemon=True).start()

    def run(self, folder):
        try:
            df = pd.read_excel(self.excel)
            df.columns = [str(c).strip() for c in df.columns]
            cols_norm = {normalizar(c):c for c in df.columns}
            
            doc_temp = Document(self.plantilla)
            full_text = "".join([p.text for p in doc_temp.paragraphs])
            marcadores = set(re.findall(r"\[([^\]]+)\]", full_text))

            for idx, fila in df.iterrows():
                doc = Document(self.plantilla)
                sexo = fila.get("sexo", "F")
                reemplazos = {}
                for m in marcadores:
                    col = cols_norm.get(normalizar(m), "")
                    val = fila.get(col, "") if col else ""
                    if "fecha" in normalizar(m): val = fecha_castellano(val)
                    elif "media" in normalizar(m):
                        try: val = f"{float(val):.2f}"
                        except: val = str(val)
                    reemplazos[m] = "" if pd.isna(val) else str(val)

                procesar_todo(doc, reemplazos, sexo)
                nom = "".join(c for c in str(fila.get("nombre", f"Cert_{idx}")) if c not in r'\/:*?"<>|')
                doc.save(os.path.join(folder, f"Certificado_{nom}.docx"))

            messagebox.showinfo("Hecho", f"Se han generado {len(df)} certificados con éxito.")
            os.startfile(folder)
        except Exception as e:
            messagebox.showerror("Error", f"Ocurrió un error: {e}")
        
        self.btn_go.config(state="normal", text="GENERAR DOCUMENTACIÓN", bg="#28a745")

if __name__ == "__main__":
    root = tk.Tk()
    AppCertificadosCentrado(root)
    root.mainloop()