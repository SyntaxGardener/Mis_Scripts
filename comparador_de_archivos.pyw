import os
import tkinter as tk
from tkinter import filedialog, ttk
from datetime import datetime
import fitz  # PyMuPDF
import docx  # python-docx
import difflib

class ComparadorDefinitivo:
    def __init__(self, root):
        self.root = root
        self.root.title("Comparador de Archivos: Contenido y Formato")
        
        # --- Configuración de Geometría Inteligente ---
        alto_v = 780
        dist_sup = 5
        ancho_p = self.root.winfo_screenwidth()
        # Ajuste de ancho según monitor (95% si es pequeño, máximo 1400)
        ancho_v = int(ancho_p * 0.95) if ancho_p < 1450 else 1400
        pos_x = (ancho_p // 2) - (ancho_v // 2)
        
        self.root.geometry(f"{ancho_v}x{alto_v}+{pos_x}+{dist_sup}")
        self.root.configure(bg="#f4f4f4")

        self.ruta1, self.ruta2 = tk.StringVar(), tk.StringVar()
        self.cambios_texto = 0
        self.cambios_formato = 0
        
        self.crear_widgets()

    def crear_widgets(self):
        # --- SELECCIÓN ---
        f_sel = tk.Frame(self.root, bg="#f4f4f4", pady=10)
        f_sel.pack(fill="x", padx=20)
        for i, v in enumerate([self.ruta1, self.ruta2], 1):
            tk.Label(f_sel, text=f"Archivo {chr(64+i)}:", bg="#f4f4f4", font=("Arial", 9, "bold")).grid(row=i, column=0, sticky="w")
            tk.Entry(f_sel, textvariable=v, width=110).grid(row=i, column=1, padx=10, pady=2)
            tk.Button(f_sel, text="...", command=lambda var=v: self.sel_file(var)).grid(row=i, column=2)

        # --- BOTONES ---
        f_btns = tk.Frame(self.root, bg="#f4f4f4")
        f_btns.pack(pady=5)
        tk.Button(f_btns, text="🔍 COMPARAR", bg="#217346", fg="white", font=("Arial", 10, "bold"), command=self.comparar, width=15).pack(side="left", padx=5)
        tk.Button(f_btns, text="📄 GENERAR INFORME", bg="#0078d4", fg="white", font=("Arial", 10, "bold"), command=self.generar_reporte, width=18).pack(side="left", padx=5)
        tk.Button(f_btns, text="🧹 LIMPIAR", bg="#666", fg="white", command=self.limpiar, width=12).pack(side="left", padx=5)
        
        # --- PANEL DETALLES ---
        self.f_info = tk.Frame(self.root, bg="#ffffff", bd=1, relief="solid")
        self.f_info.pack(fill="x", padx=20, pady=5)
        self.lbl_info_a = tk.Label(self.f_info, text="Esperando archivo A...", justify="left", bg="white", font=("Consolas", 9), anchor="nw")
        self.lbl_info_a.pack(side="left", expand=True, fill="both", padx=10, pady=5)
        self.lbl_info_b = tk.Label(self.f_info, text="Esperando archivo B...", justify="left", bg="white", font=("Consolas", 9), anchor="nw")
        self.lbl_info_b.pack(side="left", expand=True, fill="both", padx=10, pady=5)

        # --- VISOR ---
        f_viz = tk.Frame(self.root)
        f_viz.pack(fill="both", expand=True, padx=20, pady=10)
        scroll = tk.Scrollbar(f_viz, command=self.sync_v)
        scroll.pack(side="right", fill="y")
        self.txt_a = tk.Text(f_viz, font=("Consolas", 10), wrap="none", yscrollcommand=scroll.set, bg="#fafafa")
        self.txt_b = tk.Text(f_viz, font=("Consolas", 10), wrap="none", yscrollcommand=scroll.set, bg="#fafafa")
        self.txt_a.pack(side="left", fill="both", expand=True)
        self.txt_b.pack(side="left", fill="both", expand=True)

        self.txt_a.tag_config("diff_text", background="#ffcccc")
        self.txt_b.tag_config("diff_text", background="#ffcccc")
        self.txt_a.tag_config("diff_format", background="#e6f3ff")
        self.txt_b.tag_config("diff_format", background="#e6f3ff")

    def sync_v(self, *args):
        self.txt_a.yview(*args); self.txt_b.yview(*args)

    def sel_file(self, v):
        f = filedialog.askopenfilename(); 
        if f: v.set(f)

    def limpiar(self):
        self.ruta1.set(""); self.ruta2.set("")
        self.txt_a.delete("1.0", tk.END); self.txt_b.delete("1.0", tk.END)
        self.lbl_info_a.config(text="Esperando archivo A...")
        self.lbl_info_b.config(text="Esperando archivo B...")
        self.cambios_texto = 0; self.cambios_formato = 0

    def extraer_datos(self, ruta):
        lineas = []
        try:
            if ruta.lower().endswith(".docx"):
                doc = docx.Document(ruta)
                for p in doc.paragraphs:
                    firma = "D"
                    if p.runs:
                        r = p.runs[0]
                        firma = f"F:{r.font.name}-S:{r.font.size}-B:{r.bold}"
                    if p.text.strip(): lineas.append({'t': p.text.strip(), 'f': firma})
            elif ruta.lower().endswith(".pdf"):
                d = fitz.open(ruta)
                for pag in d:
                    for b in pag.get_text("dict")["blocks"]:
                        if "lines" in b:
                            for l in b["lines"]:
                                for s in l["spans"]:
                                    lineas.append({'t': s['text'].strip(), 'f': f"{s['size']}-{s['font']}"})
            else:
                with open(ruta, 'r', encoding='utf-8', errors='ignore') as f:
                    for l in f: lineas.append({'t': l.strip(), 'f': 'txt'})
        except: pass
        return [l for l in lineas if l['t']]

    def comparar(self):
        r1, r2 = self.ruta1.get().strip('"'), self.ruta2.get().strip('"')
        if not r1 or not r2: return
        
        self.cambios_texto = 0; self.cambios_formato = 0
        self.lbl_info_a.config(text=self.obtener_detalles(r1))
        self.lbl_info_b.config(text=self.obtener_detalles(r2))
        self.txt_a.delete("1.0", tk.END); self.txt_b.delete("1.0", tk.END)
        
        d1, d2 = self.extraer_datos(r1), self.extraer_datos(r2)
        sm = difflib.SequenceMatcher(None, [x['t'] for x in d1], [x['t'] for x in d2])
        
        for op, i1, i2, j1, j2 in sm.get_opcodes():
            if op == 'equal':
                for k in range(i2 - i1):
                    tag = ""
                    if d1[i1+k]['f'] != d2[j1+k]['f']:
                        tag = "diff_format"; self.cambios_formato += 1
                    self.txt_a.insert(tk.END, d1[i1+k]['t'] + "\n", tag)
                    self.txt_b.insert(tk.END, d2[j1+k]['t'] + "\n", tag)
            else:
                for k in range(i1, i2): 
                    self.txt_a.insert(tk.END, d1[k]['t'] + "\n", "diff_text")
                    self.cambios_texto += 1
                for k in range(j1, j2): 
                    self.txt_b.insert(tk.END, d2[k]['t'] + "\n", "diff_text")
                    self.cambios_texto += 1

    def obtener_detalles(self, ruta):
        if not os.path.exists(ruta): return "No encontrado"
        s = os.stat(ruta)
        u = os.path.splitdrive(ruta)[0]
        return f"NOMBRE: {os.path.basename(ruta)}\nTAM.: {s.st_size:,} bytes\nFECHA: {datetime.fromtimestamp(s.st_mtime).strftime('%d/%m/%Y %H:%M')}\nUNIDAD: {u}"

    def generar_reporte(self):
        r1, r2 = self.ruta1.get(), self.ruta2.get()
        if not r1 or not r2: return
        
        nombre_rep = f"Reporte_{datetime.now().strftime('%H%M%S')}.txt"
        with open(nombre_rep, "w", encoding="utf-8") as f:
            f.write(f"REPORTE: {datetime.now()}\nA: {r1}\nB: {r2}\n")
            f.write("-" * 40 + "\n")
            f.write(f"CAMBIOS TEXTO: {self.cambios_texto}\n")
            f.write(f"CAMBIOS FORMATO: {self.cambios_formato}\n")
        
        # Solo abrimos el archivo para que el usuario lo vea, sin ventanitas extra.
        os.startfile(nombre_rep)

if __name__ == "__main__":
    root = tk.Tk(); app = ComparadorDefinitivo(root); root.mainloop()