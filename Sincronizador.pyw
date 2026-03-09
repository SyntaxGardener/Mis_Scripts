# -*- coding: utf-8 -*-
import os
import shutil
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import platform
import subprocess
from datetime import datetime

class SincronizadorConFechas:
    def __init__(self, root):
        self.root = root
        self.root.title("Sincronizador de Archivos")
        # Esto pone la ventana de 1000x700, centrada horizontalmente y pegada arriba (0)
        ancho = 1000
        alto = 700
        pos_x = (self.root.winfo_screenwidth() // 2) - (ancho // 2)
        self.root.geometry(f"{ancho}x{alto}+{pos_x}+0")
        
        self.ruta_a = tk.StringVar()
        self.ruta_b = tk.StringVar()
        self.lista_datos = [] 

        # --- Selección de carpetas ---
        f_top = tk.LabelFrame(root, text=" 1. Directorios de Trabajo ", padx=10, pady=10)
        f_top.pack(fill="x", padx=15, pady=10)

        for i, (txt, var) in enumerate([("Carpeta A:", self.ruta_a), ("Carpeta B:", self.ruta_b)]):
            tk.Label(f_top, text=txt).grid(row=i, column=0, sticky="e")
            tk.Entry(f_top, textvariable=var, width=90).grid(row=i, column=1, padx=5, pady=2)
            tk.Button(f_top, text="Buscar", command=lambda v=var: self.elegir(v)).grid(row=i, column=2)

        # --- Panel de Mandos ---
        f_ctrl = tk.Frame(root, padx=15)
        f_ctrl.pack(fill="x")

        self.btn_ana = tk.Button(f_ctrl, text="🔍 ANALIZAR DIFERENCIAS", command=self.analizar, bg="#28a745", fg="white", font=("Arial", 9, "bold"), padx=15)
        self.btn_ana.pack(side=tk.LEFT)

        tk.Button(f_ctrl, text="Seleccionar TODO", command=self.seleccionar_todo).pack(side=tk.RIGHT, padx=5)
        tk.Button(f_ctrl, text="Limpiar Selección", command=self.deseleccionar).pack(side=tk.RIGHT, padx=5)

        # --- Tabla con columna de Detalles/Fechas ---
        self.tree = ttk.Treeview(root, columns=("archivo", "info"), show="tree headings")
        self.tree.heading("#0", text="Categoría")
        self.tree.heading("archivo", text="Nombre del Archivo")
        self.tree.heading("info", text="Comparativa de Fechas (A vs B)")
        
        self.tree.column("#0", width=180)
        self.tree.column("archivo", width=420)
        self.tree.column("info", width=350)
        
        self.tree.tag_configure('nuevo', foreground='#2e7d32')
        self.tree.tag_configure('actualizar', foreground='#1565c0')
        self.tree.pack(pady=10, padx=15, fill=tk.BOTH, expand=True)
        
        self.tree.bind("<Double-1>", self.abrir_ubicacion)

        # --- Footer ---
        f_foot = tk.Frame(root, pady=15)
        f_foot.pack(fill="x")
        
        tk.Button(f_foot, text="SINCRONIZAR (COPIAR)", command=self.sincronizar, bg="#007bff", fg="white", width=25, height=2, font=("Arial", 10, "bold")).pack(side=tk.LEFT, padx=60)
        tk.Button(f_foot, text="BORRAR ORIGINALES", command=self.borrar, bg="#dc3545", fg="white", width=25, height=2, font=("Arial", 10, "bold")).pack(side=tk.RIGHT, padx=60)

    def elegir(self, var):
        d = filedialog.askdirectory()
        if d: var.set(os.path.normpath(d))

    def formar_fecha(self, ts):
        return datetime.fromtimestamp(ts).strftime('%d/%m/%y %H:%M')

    def seleccionar_todo(self):
        hijos = []
        for p in self.tree.get_children():
            hijos.extend(self.tree.get_children(p))
        self.tree.selection_set(tuple(hijos) + tuple(self.tree.get_children()))

    def deseleccionar(self):
        self.tree.selection_remove(self.tree.selection())

    def abrir_ubicacion(self, event):
        item = self.tree.identify_row(event.y)
        if item and item.isdigit():
            ruta_orig = self.lista_datos[int(item)][3]
            carpeta = os.path.dirname(ruta_orig)
            if platform.system() == "Windows": os.startfile(carpeta)
            else: subprocess.Popen(["open", carpeta])

    def analizar(self):
        da, db = self.ruta_a.get().strip(), self.ruta_b.get().strip()
        if not da or not db: return

        self.tree.delete(*self.tree.get_children())
        self.lista_datos = []
        
        try:
            pa, pb = Path(da), Path(db)
            dict_a = {f.relative_to(pa): f for f in pa.rglob('*') if f.is_file()}
            dict_b = {f.relative_to(pb): f for f in pb.rglob('*') if f.is_file()}
            
            todos = sorted(set(dict_a.keys()) | set(dict_b.keys()))
            padres = {}

            for rel in todos:
                fa, fb = dict_a.get(rel), dict_b.get(rel)
                res = None
                
                if fa and fb:
                    ma, mb = fa.stat().st_mtime, fb.stat().st_mtime
                    if abs(ma - mb) > 2:
                        txt_fecha = f"A: {self.formar_fecha(ma)} | B: {self.formar_fecha(mb)}"
                        if ma > mb: res = ("Actualizar en B", str(rel), f"Nuevo en A -> {txt_fecha}", fa, pb/rel, 'actualizar')
                        else: res = ("Actualizar en A", str(rel), f"Nuevo en B -> {txt_fecha}", fb, pa/rel, 'actualizar')
                elif fa:
                    res = ("Solo en A (Copiar a B)", str(rel), "No existe en destino B", fa, pb/rel, 'nuevo')
                else:
                    res = ("Solo en B (Copiar a A)", str(rel), "No existe en destino A", fb, pa/rel, 'nuevo')

                if res:
                    cat = res[0]
                    if cat not in padres:
                        padres[cat] = self.tree.insert("", tk.END, text=cat, open=True)
                    
                    idx = len(self.lista_datos)
                    self.lista_datos.append(res)
                    self.tree.insert(padres[cat], tk.END, iid=str(idx), text=" 📄 ", values=(res[1], res[2]), tags=(res[5],))

        except Exception as e:
            messagebox.showerror("Error", str(e))

    def sincronizar(self):
        sel = [s for s in self.tree.selection() if s.isdigit()]
        if not sel: return
        if messagebox.askyesno("Confirmar", f"¿Copiar {len(sel)} archivos?"):
            for iid in sel:
                _, _, _, orig, dest, _ = self.lista_datos[int(iid)]
                os.makedirs(dest.parent, exist_ok=True)
                shutil.copy2(orig, dest)
            messagebox.showinfo("Hecho", "Copiado correctamente.")
            self.analizar()

    def borrar(self):
        sel = [s for s in self.tree.selection() if s.isdigit()]
        if not sel: return
        if messagebox.askyesno("PELIGRO", f"¿BORRAR {len(sel)} archivos originales?"):
            for iid in sel:
                _, _, _, orig, _, _ = self.lista_datos[int(iid)]
                if os.path.exists(orig): os.remove(orig)
            messagebox.showinfo("Hecho", "Archivos borrados.")
            self.analizar()

if __name__ == "__main__":
    root = tk.Tk()
    app = SincronizadorConFechas(root)
    root.mainloop()