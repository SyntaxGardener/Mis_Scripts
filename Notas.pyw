import pandas as pd
from openpyxl import load_workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
import re
import tkinter as tk
from tkinter import filedialog, messagebox
import pdfplumber
import os
import threading

class ProcesadorNotasESPAD:
    def __init__(self):
        # ---  CONFIGURACIÓN ORIGINAL ---
        self.mapeo_materias = {
            '1.2': {'LED': 'LEN', 'AUL': 'LIT', 'USLE': 'ING-1', 'ASLE': 'ING-2'},
            '2.1': {'ENL': 'LEN', 'PAL': 'LIT', 'LELE': 'ING-1', 'SOLE': 'ING-2'},
            '2.2': {'CPL': 'LEN', 'LIM': 'LIT', 'ECLE': 'ING-1', 'INLE': 'ING-2'}
        }
        
        self.config_notas = {
            'LEN': [('Examen', 6), ('Auto', 0.5), ('Oral', 0.5), ('Escrita', 1), ('Invest', 2)],
            'LIT': [('Examen', 6), ('Auto', 1), ('Escrita', 1.5), ('Lectura', 1.5)],
            'ING-1': [('Examen', 6), ('Auto', 0.5), ('Oral', 1.5), ('Ejerc', 2)],
            'ING-2': [('Examen', 6), ('Auto', 0.5), ('Oral', 1.5), ('Ejerc', 2)]
        }
        self.niveles = ['1.2', '2.1', '2.2']

    def extraer(self, ruta):
        alumnos = {n: [] for n in self.niveles}
        registro_bloqueos = {} 
        with pdfplumber.open(ruta) as pdf:
            for page in pdf.pages:
                texto = page.extract_text() or ""
                nivel_actual = next((n for n in self.niveles if f"Nivel {n}" in texto), None)
                if not nivel_actual: continue
                tablas = page.extract_tables()
                for tabla in tablas:
                    if not tabla or "Alumnado" not in str(tabla[0]): continue
                    encabezado = [str(c).strip().upper() for c in tabla[0]]
                    for fila in tabla[1:]:
                        if not fila or not fila[0] or "TOTAL:" in str(fila[0]).upper(): continue
                        nombre_raw = str(fila[0]).strip()
                        limpio = re.sub(r'ESPAD Mixt|ESP\.-SA|MATR|APRO|EXEN|\d{5,}', '', nombre_raw, flags=re.I).strip().strip('-').strip()
                        if ',' in limpio:
                            ape, nom = [part.strip() for part in limpio.split(',', 1)]
                            ape = ape.upper()
                            alumnos[nivel_actual].append((ape, nom))
                            mats_a_bloquear = []
                            for i, celda in enumerate(fila):
                                valor = str(celda).strip().upper() if celda else ""
                                if valor in ["APRO", "EXEN", ""]:
                                    cod_pdf = encabezado[i]
                                    if cod_pdf in self.mapeo_materias[nivel_actual]:
                                        mats_a_bloquear.append(self.mapeo_materias[nivel_actual][cod_pdf])
                            registro_bloqueos[(nivel_actual, ape, nom)] = mats_a_bloquear
        return alumnos, registro_bloqueos

    def generar_excel(self, datos, bloqueos, ruta):
        with pd.ExcelWriter(ruta, engine='openpyxl') as writer:
            for n in self.niveles:
                hoja = f'Nivel_{n}'.replace('.', '_')
                cols = ['Apellidos', 'Nombre']
                for asig in ['LEN', 'LIT', 'ING-1', 'ING-2']:
                    for c_nom, peso in self.config_notas[asig]: 
                        cols.append(f"{asig}_{c_nom} ({peso})")
                    cols.append(f"{asig}_TOT")
                df = pd.DataFrame(sorted(list(set(datos[n]))), columns=['Apellidos', 'Nombre'])
                for c in cols[2:]: df[c] = ""
                df.to_excel(writer, sheet_name=hoja, index=False)
        self.estilizar(ruta, bloqueos)

    def estilizar(self, ruta, bloqueos):
        wb = load_workbook(ruta)
        gris_bloqueo = PatternFill(start_color="D9D9D9", end_color="D9D9D9", fill_type="solid")
        azul_h = PatternFill(start_color="2F5597", end_color="2F5597", fill_type="solid")
        azul_f = PatternFill(start_color="E7EBF5", end_color="E7EBF5", fill_type="solid")
        f_blanca = Font(color="FFFFFF", bold=True)
        borde = Border(left=Side(style='thin'), right=Side(style='thin'), top=Side(style='thin'), bottom=Side(style='thin'))
        for ws in wb.worksheets:
            nivel_hoja = ws.title.replace('Nivel_', '').replace('_', '.')
            for cell in ws[1]:
                cell.fill, cell.font, cell.alignment = azul_h, f_blanca, Alignment(horizontal='center', vertical='center')
            for r_idx in range(2, ws.max_row + 1):
                ape, nom = str(ws.cell(row=r_idx, column=1).value), str(ws.cell(row=r_idx, column=2).value)
                mats_gris = bloqueos.get((nivel_hoja, ape, nom), [])
                for c_idx in range(3, ws.max_column + 1):
                    cell = ws.cell(row=r_idx, column=c_idx)
                    cell.border = borde
                    header = str(ws.cell(row=1, column=c_idx).value)
                    asig_actual = header.split('_')[0]
                    if asig_actual in mats_gris:
                        cell.fill = gris_bloqueo
                    else:
                        if header.endswith("_TOT"):
                            cell.fill = azul_f
                            prefix = header.split('_')[0]
                            start_c = next(i for i in range(3, c_idx) if str(ws.cell(row=1, column=i).value).startswith(prefix))
                            c1, c2 = ws.cell(row=r_idx, column=start_c).column_letter, ws.cell(row=r_idx, column=c_idx-1).column_letter
                            cell.value = f"=SUM({c1}{r_idx}:{c2}{r_idx})"
                    cell.alignment = Alignment(horizontal='center')
            for col in ws.columns:
                ws.column_dimensions[col[0].column_letter].width = 25 if col[0].column <= 2 else 15
        wb.save(ruta)

# --- INTERFAZ  ---
class AppRegistroGuiada:
    def __init__(self, root):
        self.root = root
        self.root.title("Generador Registro Notas Comunicación ESPAD")
        self.root.geometry("550x280")
        
        # Título principal
        tk.Label(root, text="GENERADOR DE REGISTRO DE NOTAS", font=("Arial", 12, "bold"), fg="#1A237E").pack(pady=15)

        # Sección Carpeta Destino
        frame_carpeta = tk.LabelFrame(root, text=" 1. Carpeta donde se guardará el Excel ", padx=10, pady=10, font=("Arial", 9, "bold"))
        frame_carpeta.pack(pady=10, padx=20, fill="x")
        
        self.entry_dest = tk.Entry(frame_carpeta, font=("Arial", 9))
        self.entry_dest.pack(side="left", padx=5, expand=True, fill="x")
        self.entry_dest.insert(0, os.getcwd())
        
        btn_browse = tk.Button(frame_carpeta, text="Seleccionar Carpeta", command=self.seleccionar_destino, font=("Arial", 9))
        btn_browse.pack(side="right")

        # Sección Selección PDF y Ejecución
        frame_accion = tk.Frame(root)
        frame_accion.pack(pady=20)
        
        tk.Label(frame_accion, text="2. ", font=("Arial", 10, "bold")).pack(side="left")
        self.btn = tk.Button(frame_accion, text="SELECCIONAR PDF Y GENERAR REGISTRO", 
                             command=self.iniciar, bg="#283593", fg="white", 
                             font=("Arial", 10, "bold"), padx=20, pady=10)
        self.btn.pack(side="left")

    def seleccionar_destino(self):
        d = filedialog.askdirectory()
        if d:
            self.entry_dest.delete(0, tk.END)
            self.entry_dest.insert(0, d)

    def iniciar(self):
        archivo = filedialog.askopenfilename(title="Selecciona el PDF de la plataforma", filetypes=[("PDF", "*.pdf")])
        if not archivo: return
        self.btn.config(state='disabled', text="Procesando datos...")
        threading.Thread(target=self.ejecutar, args=(archivo,), daemon=True).start()

    def ejecutar(self, archivo):
        try:
            p = ProcesadorNotasESPAD()
            datos, bloqueos = p.extraer(archivo)
            ruta_excel = os.path.join(self.entry_dest.get(), "Registro_Notas_ESPAD.xlsx")
            p.generar_excel(datos, bloqueos, ruta_excel)
            messagebox.showinfo("Proceso Exitoso", f"El registro se ha creado correctamente en:\n{ruta_excel}")
        except Exception as e:
            messagebox.showerror("Error", f"Se produjo un error durante el proceso:\n{str(e)}")
        finally:
            self.btn.config(state='normal', text="SELECCIONAR PDF Y GENERAR REGISTRO")

if __name__ == "__main__":
    root = tk.Tk()
    AppRegistroGuiada(root)
    root.mainloop()