# -*- coding: utf-8 -*-
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import pandas as pd
import sys, os, re, unicodedata
from docx import Document
import threading

# --- FUNCIONES DE LÓGICA (Tus originales mejoradas) ---
def normalizar(t):
    if not isinstance(t, str): t = str(t)
    t = t.strip().lower()
    t = ''.join(c for c in unicodedata.normalize('NFD', t) if unicodedata.category(c) != 'Mn')
    return t

def limpiar_fecha_texto(texto):
    if not isinstance(texto, str): return texto
    meses = {
        "enero": "01", "febrero": "02", "marzo": "03", "abril": "04",
        "mayo": "05", "junio": "06", "julio": "07", "agosto": "08",
        "septiembre": "09", "octubre": "10", "noviembre": "11", "diciembre": "12"
    }
    texto_lc = texto.lower()
    match = re.search(r'(\d{1,2})\s+de\s+([a-zñáéíóú]+)\s+de\s+(\d{4})', texto_lc)
    if match:
        dia = match.group(1).zfill(2)
        mes_nombre = match.group(2)
        anio = match.group(3)
        if mes_nombre in meses:
            return f"{dia}/{meses[mes_nombre]}/{anio}"
    return texto

# --- INTERFAZ Y PROCESO ---
class AppDiligencias:
    def __init__(self, root):
        self.root = root
        self.root.title("Generador de Diligencias")
        # 1. Definimos el tamaño que queremos
        ancho = 450
        alto = 300
        
        # 2. Calculamos la posición (Esto es lo que va dentro de init)
        pos_x = (self.root.winfo_screenwidth() // 2) - (ancho // 2)
        
        # 3. Aplicamos la magia: Ancho x Alto + Derecha + Arriba (20)
        self.root.geometry(f"{ancho}x{alto}+{pos_x}+20")
        self.root.resizable(False, False)
        
        # Variables de ruta
        self.plantilla = ""
        self.excel = ""
        self.salida = ""

        # Diseño simple
        tk.Label(root, text="Generador de Diligencias para SAUCE", font=("Arial", 12, "bold")).pack(pady=10)
        
        self.btn_plantilla = tk.Button(root, text="1. Seleccionar Plantilla Word", command=self.sel_plantilla, width=35)
        self.btn_plantilla.pack(pady=5)
        
        self.btn_excel = tk.Button(root, text="2. Seleccionar Excel de Datos", command=self.sel_excel, width=35)
        self.btn_excel.pack(pady=5)
        
        self.btn_procesar = tk.Button(root, text="3. Generar y Guardar", command=self.iniciar_hilo, 
                                     bg="#4CAF50", fg="white", font=("Arial", 10, "bold"), width=30)
        self.btn_procesar.pack(pady=20)

        self.lbl_estado = tk.Label(root, text="Esperando archivos...", fg="gray")
        self.lbl_estado.pack()

    def sel_plantilla(self):
        self.plantilla = filedialog.askopenfilename(title="Seleccionar Plantilla", filetypes=[("Word", "*.docx")])
        if self.plantilla: self.lbl_estado.config(text="Plantilla cargada ✔️", fg="green")

    def sel_excel(self):
        self.excel = filedialog.askopenfilename(title="Seleccionar Excel", filetypes=[("Excel", "*.xlsx")])
        if self.excel: self.lbl_estado.config(text="Excel cargado ✔️", fg="green")

    def iniciar_hilo(self):
        if not self.plantilla or not self.excel:
            messagebox.showwarning("Faltan datos", "Por favor, selecciona ambos archivos primero.")
            return
        
        self.salida = filedialog.asksaveasfilename(title="Guardar resultado", 
                                                   defaultextension=".xlsx",
                                                   initialfile="Diligencias_Generadas.xlsx",
                                                   filetypes=[("Excel", "*.xlsx")])
        if self.salida:
            self.btn_procesar.config(state="disabled", text="Procesando...")
            threading.Thread(target=self.procesar_datos, daemon=True).start()

    def procesar_datos(self):
        try:
            # Lectura y preparación
            doc = Document(self.plantilla)
            texto_base = "\n".join([p.text for p in doc.paragraphs if p.text.strip() != ""])
            marcadores = re.findall(r"\[([^\]]+)\]", texto_base)

            df = pd.read_excel(self.excel)
            df.columns = [str(c).strip() for c in df.columns]
            df = df.astype(str)
            for col in df.columns:
                df[col] = df[col].apply(limpiar_fecha_texto)

            resultados = []
            for _, fila in df.iterrows():
                sexo_val = fila.get("sexo", "").upper()
                t_gen = texto_base.replace("D./Dña.", "Dña." if "F" in sexo_val else "D.")
                
                fila_dict = fila.to_dict()
                for m in marcadores:
                    col_real = next((c for c in df.columns if normalizar(c) == normalizar(m)), None)
                    valor = fila_dict.get(col_real, "") if col_real else ""
                    t_gen = t_gen.replace(f"[{m}]", valor)
                
                fila_dict['Diligencia_Generada'] = t_gen
                resultados.append(fila_dict)

            # Guardado profesional con XlsxWriter
            df_final = pd.DataFrame(resultados)
            quitar = ["lugar de nacimiento", "fecha de nacimiento", "nacimiento", "media", "dni", "nacionalidad", "sexo"]
            df_final.drop(columns=[c for c in df_final.columns if normalizar(c) in quitar], inplace=True, errors='ignore')

            writer = pd.ExcelWriter(self.salida, engine='xlsxwriter')
            df_final.to_excel(writer, index=False)
            workbook = writer.book
            worksheet = writer.sheets['Sheet1']
            fmt = workbook.add_format({'num_format': '@', 'text_wrap': True, 'valign': 'top'})

            for i, col in enumerate(df_final.columns):
                worksheet.set_column(i, i, 100 if "Diligencia" in col else 20, fmt)
            
            writer.close()
            
            messagebox.showinfo("¡Hecho!", f"Proceso completado.\nArchivo guardado en:\n{self.salida}")
            os.startfile(os.path.dirname(self.salida))
            
        except Exception as e:
            messagebox.showerror("Error", f"Algo falló: {str(e)}")
        
        self.btn_procesar.config(state="normal", text="3. Generar y Guardar")
        self.lbl_estado.config(text="Listo.")

if __name__ == "__main__":
    root = tk.Tk()
    app = AppDiligencias(root)
    root.mainloop()