import os
import time
import datetime
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from docx import Document
import openpyxl
import pikepdf
import threading
import pywintypes, win32file, win32con

class CronosMetadatos:
    def __init__(self, root):
        self.root = root
        self.root.title("Editor de Metadatos")
        
        w, h = 550, 600
        px = (self.root.winfo_screenwidth() // 2) - (w // 2)
        self.root.geometry(f"{w}x{h}+{px}+5")
        
        self.target_path = tk.StringVar()
        self.nuevo_autor = tk.StringVar(value="Admin")
        self.nueva_org = tk.StringVar(value="Oficina")
        
        # Variables de tiempo
        now = datetime.datetime.now()
        self.dia = tk.StringVar(value=now.strftime("%d/%m/%Y"))
        self.hora = tk.StringVar(value=now.strftime("%H:%M"))
        
        self.create_widgets()

    def create_widgets(self):
        p = {'padx': 20, 'pady': 5}
        
        tk.Label(self.root, text="Modificador de Metadatos", font=("Arial", 12, "bold")).pack(pady=15)

        # SELECCIÓN
        tk.Label(self.root, text="1. Origen (Archivo o Carpeta):", font=("Arial", 9, "bold")).pack(anchor="w", **p)
        f_sel = tk.Frame(self.root); f_sel.pack(fill="x", **p)
        tk.Entry(f_sel, textvariable=self.target_path).pack(side="left", fill="x", expand=True)
        tk.Button(f_sel, text="Archivo", command=self.sel_file).pack(side="right", padx=2)
        tk.Button(f_sel, text="Carpeta", command=self.sel_dir).pack(side="right", padx=2)

        # FECHA Y HORA
        tk.Label(self.root, text="2. Configurar Fecha y Hora:", font=("Arial", 9, "bold")).pack(anchor="w", **p)
        f_time = tk.Frame(self.root); f_time.pack(fill="x", **p)
        tk.Label(f_time, text="Fecha (DD/MM/AAAA):").grid(row=0, column=0)
        tk.Entry(f_time, textvariable=self.dia, width=12).grid(row=0, column=1, padx=10)
        tk.Label(f_time, text="Hora (HH:MM):").grid(row=0, column=2)
        tk.Entry(f_time, textvariable=self.hora, width=8).grid(row=0, column=3, padx=10)

        # METADATOS INTERNOS
        tk.Label(self.root, text="3. Identidad del Documento:", font=("Arial", 9, "bold")).pack(anchor="w", **p)
        tk.Label(self.root, text="Autor / Creador:").pack(anchor="w", **p)
        tk.Entry(self.root, textvariable=self.nuevo_autor).pack(fill="x", **p)
        tk.Label(self.root, text="Organización / Programa:").pack(anchor="w", **p)
        tk.Entry(self.root, textvariable=self.nueva_org).pack(fill="x", **p)

        # BOTÓN PROCESAR
        self.btn = tk.Button(self.root, text="APLICAR CAMBIOS TOTALES", bg="#2980b9", fg="white", 
                            font=("Arial", 10, "bold"), height=2, command=self.run)
        self.btn.pack(pady=30, fill="x", padx=20)

    def sel_file(self): self.target_path.set(filedialog.askopenfilename())
    def sel_dir(self): self.target_path.set(filedialog.askdirectory())

    def cambiar_fechas_windows(self, filePath, new_time):
        """Cambia creación, modificación y acceso usando la API de Windows."""
        try:
            wtime = pywintypes.Time(new_time)
            handle = win32file.CreateFile(
                filePath, win32con.GENERIC_WRITE,
                win32con.FILE_SHARE_READ | win32con.FILE_SHARE_WRITE | win32con.FILE_SHARE_DELETE,
                None, win32con.OPEN_EXISTING,
                win32con.FILE_ATTRIBUTE_NORMAL, None
            )
            win32file.SetFileTime(handle, wtime, wtime, wtime)
            handle.close()
        except:
            # Fallback si falla pywin32
            t = time.mktime(new_time.timetuple())
            os.utime(filePath, (t, t))

    def limpiar_interno(self, file_path):
        ext = file_path.lower()
        try:
            if ext.endswith('.docx'):
                doc = Document(file_path)
                doc.core_properties.author = self.nuevo_autor.get()
                doc.core_properties.last_modified_by = self.nuevo_autor.get()
                doc.save(file_path)
            elif ext.endswith('.xlsx'):
                wb = openpyxl.load_workbook(file_path)
                wb.properties.creator = self.nuevo_autor.get()
                wb.properties.lastModifiedBy = self.nuevo_autor.get()
                wb.save(file_path)
            elif ext.endswith('.pdf'):
                with pikepdf.open(file_path, allow_overwriting_input=True) as pdf:
                    with pdf.open_metadata() as meta:
                        meta['dc:creator'] = [self.nuevo_autor.get()]
                    pdf.save(file_path)
        except: pass

    def process(self):
        try:
            target = self.target_path.get()
            # Parsear fecha y hora
            dt_str = f"{self.dia.get()} {self.hora.get()}"
            new_dt = datetime.datetime.strptime(dt_str, "%d/%m/%Y %H:%M")
            
            archivos = []
            if os.path.isfile(target): archivos.append(target)
            else:
                for root, _, files in os.walk(target):
                    for f in files: archivos.append(os.path.join(root, f))

            for f in archivos:
                self.limpiar_interno(f) # Primero metadatos internos
                self.cambiar_fechas_windows(f, new_dt) # Al final las fechas del sistema

            messagebox.showinfo("Éxito", f"Se han modificado {len(archivos)} archivos con la fecha {dt_str}")
            os.startfile(os.path.dirname(target) if os.path.isfile(target) else target)
        except Exception as e:
            messagebox.showerror("Error", f"Verifica el formato de fecha (DD/MM/AAAA) y hora.\n{e}")
        finally:
            self.btn.config(state="normal", text="APLICAR CAMBIOS TOTALES")

    def run(self):
        if not self.target_path.get(): return
        self.btn.config(state="disabled", text="Procesando...")
        threading.Thread(target=self.process, daemon=True).start()

if __name__ == "__main__":
    root = tk.Tk(); app = CronosMetadatos(root); root.mainloop()