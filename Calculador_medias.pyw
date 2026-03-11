import pdfplumber
import pandas as pd
import re
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext
import os
import threading
from datetime import datetime

# --- LÓGICA DE EXTRACCIÓN ---
CONVERSION = {'SB': 9.5, 'NT': 8.5, 'BI': 6.5, 'SU': 5.5, 'IN': 4.0, 'NP': 0.0}
# Generación limpia de años según tu preferencia
ANIOS_VALIDOS = [f"{anio}/{anio+1}" for anio in range(2024, 2035)]

def limpiar_nombre(nombre):
    nombre = re.sub(r'\s+Nº.*$', '', nombre)
    nombre = re.sub(r'\s+identificacion.*$', '', nombre)
    nombre = re.sub(r'\s*\(\d+\)\s*$', '', nombre)
    return nombre.strip()

def encontrar_nombre(lineas):
    for i, linea in enumerate(lineas[:20]):
        if 'Apellidos y nombre:' in linea:
            return limpiar_nombre(linea.split('Apellidos y nombre:')[-1])
    for i, linea in enumerate(lineas[:15]):
        if 'CERTIFICADO ACADÉMICO OFICIAL DEL ALUMNO:' in linea:
            return limpiar_nombre(linea.split('DEL ALUMNO:')[-1])
        if 'CERTIFICADO ACADÉMICO OFICIAL DE LA ALUMNA:' in linea:
            return limpiar_nombre(linea.split('DE LA ALUMNA:')[-1])
    return None

def procesar_pdf(ruta_pdf, log_func):
    alumnos = {}
    with pdfplumber.open(ruta_pdf) as pdf:
        for num_pagina, pagina in enumerate(pdf.pages, 1):
            texto = pagina.extract_text()
            if not texto: continue
            lineas = texto.split('\n')
            nombre = encontrar_nombre(lineas)
            if not nombre: continue
            if nombre not in alumnos:
                alumnos[nombre] = {'ACT': [], 'AC': [], 'AS': []}
                log_func(f"  📍 Página {num_pagina}: {nombre}")
            for linea in lineas:
                for anio in ANIOS_VALIDOS:
                    if anio in linea:
                        for ambito in ['ACT', 'AC', 'AS']:
                            if ambito in linea:
                                for nota_raw, valor in CONVERSION.items():
                                    if nota_raw in linea:
                                        alumnos[nombre][ambito].append(valor)
                                        break
                                break
                        break
    return alumnos

# --- INTERFAZ GRÁFICA ---

class AppCalculadora:
    def __init__(self, root):
        self.root = root
        self.root.title("Calculadora ESPAD")
        # 1. Definimos el tamaño que queremos
        ancho = 800
        alto = 750
        
        # 2. Calculamos la posición (Esto es lo que va dentro de init)
        pos_x = (self.root.winfo_screenwidth() // 2) - (ancho // 2)
        
        # 3. Aplicamos la magia: Ancho x Alto + Derecha + Arriba (20)
        self.root.geometry(f"{ancho}x{alto}+{pos_x}+20")
        
        tk.Label(root, text="Calculadora de Expedientes ESPAD", font=("Arial", 14, "bold")).pack(pady=10)

        frame_dest = tk.LabelFrame(root, text=" Carpeta de Destino ", padx=10, pady=10)
        frame_dest.pack(pady=5, padx=20, fill="x")
        
        self.entry_dest = tk.Entry(frame_dest, width=65)
        self.entry_dest.pack(side="left", padx=(0, 10), pady=5, expand=True, fill="x")
        self.entry_dest.insert(0, os.getcwd()) 
        tk.Button(frame_dest, text="Cambiar", command=self.seleccionar_destino).pack(side="right")

        self.btn_seleccionar = tk.Button(root, text="SELECCIONAR PDFs Y CALCULAR", command=self.iniciar_proceso, 
                                         bg="#1976D2", fg="white", font=("Arial", 11, "bold"), padx=20, pady=12)
        self.btn_seleccionar.pack(pady=10)

        self.console = scrolledtext.ScrolledText(root, state='disabled', height=25, width=95, bg="#1e1e1e", fg="#00FF00", font=("Consolas", 10))
        self.console.pack(pady=5, padx=20)

    def seleccionar_destino(self):
        directorio = filedialog.askdirectory()
        if directorio:
            self.entry_dest.delete(0, tk.END)
            self.entry_dest.insert(0, directorio)

    def log(self, mensaje):
        self.console.config(state='normal')
        self.console.insert(tk.END, mensaje + "\n")
        self.console.see(tk.END)
        self.console.config(state='disabled')
        self.root.update_idletasks()

    def iniciar_proceso(self):
        dest_folder = self.entry_dest.get()
        if not os.path.isdir(dest_folder):
            messagebox.showerror("Error", "La carpeta de destino no es válida.")
            return
        threading.Thread(target=self.ejecutar_logica, args=(dest_folder,), daemon=True).start()

    def ejecutar_logica(self, dest_folder):
        self.btn_seleccionar.config(state='disabled')
        archivos = filedialog.askopenfilenames(title="Selecciona PDFs", filetypes=[("Archivos PDF", "*.pdf")])
        
        if not archivos:
            self.btn_seleccionar.config(state='normal')
            return

        alumnos_total = {}
        self.log("="*70 + "\n📄 PROCESANDO EXPEDIENTES...\n" + "="*70)

        for ruta_pdf in archivos:
            nombre_pdf = os.path.basename(ruta_pdf)
            self.log(f"\n📁 Archivo: {nombre_pdf}")
            try:
                nuevos = procesar_pdf(ruta_pdf, self.log)
                for nombre, datos in nuevos.items():
                    if nombre not in alumnos_total:
                        alumnos_total[nombre] = {'ACT': [], 'AC': [], 'AS': []}
                    alumnos_total[nombre]['ACT'].extend(datos['ACT'])
                    alumnos_total[nombre]['AC'].extend(datos['AC'])
                    alumnos_total[nombre]['AS'].extend(datos['AS'])
            except Exception as e:
                self.log(f"  ❌ Error: {e}")

        if not alumnos_total:
            self.log("\n❌ No se encontraron datos.")
            self.btn_seleccionar.config(state='normal')
            return

        resultados = []
        for nombre, datos in alumnos_total.items():
            self.log(f"\n👤 Alumno/a: {nombre}")
            m_act = sum(datos['ACT'])/len(datos['ACT']) if datos['ACT'] else None
            m_ac = sum(datos['AC'])/len(datos['AC']) if datos['AC'] else None
            m_as = sum(datos['AS'])/len(datos['AS']) if datos['AS'] else None
            
            if m_act: self.log(f"  ACT: {datos['ACT']} -> Media: {m_act:.2f}")
            if m_ac:  self.log(f"  AC:  {datos['AC']} -> Media: {m_ac:.2f}")
            if m_as:  self.log(f"  AS:  {datos['AS']} -> Media: {m_as:.2f}")
            
            validas = [m for m in [m_act, m_ac, m_as] if m]
            m_global = sum(validas) / len(validas) if validas else None
            if m_global: self.log(f"  ▶ MEDIA GLOBAL: {m_global:.2f}")

            resultados.append({
                'Nombre': nombre,
                'Media ACT': round(m_act, 2) if m_act else "N/A",
                'Media AC': round(m_ac, 2) if m_ac else "N/A",
                'Media AS': round(m_as, 2) if m_as else "N/A",
                'Media Global': round(m_global, 2) if m_global else "N/A"
            })

        ahora = datetime.now().strftime("%Y%m%d_%H%M%S")
        nombre_archivo = f"Medias_ESPAD_{ahora}.xlsx"
        ruta_final = os.path.join(dest_folder, nombre_archivo)

        try:
            pd.DataFrame(resultados).to_excel(ruta_final, index=False)
            self.log("\n" + "="*70 + f"\n✅ EXCEL GENERADO: {nombre_archivo}\n" + "="*70)
            messagebox.showinfo("Éxito", f"Guardado en:\n{nombre_archivo}")
        except Exception as e:
            self.log(f"❌ Error al guardar: {e}")
        
        self.btn_seleccionar.config(state='normal')

if __name__ == "__main__":
    root = tk.Tk()
    app = AppCalculadora(root)
    root.mainloop()