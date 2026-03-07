import os
import shutil
import threading
from pathlib import Path
from datetime import datetime
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

class SincronizadorUltra:
    def __init__(self, root):
        self.root = root
        self.root.title("Sincronizador")
        
        # --- Configuración de Geometría (Centrado Superior) ---
        ancho = 1050
        alto = 850
        pos_x = (self.root.winfo_screenwidth() // 2) - (ancho // 2)
        pos_y = 0 # Pegado arriba
        self.root.geometry(f"{ancho}x{alto}+{pos_x}+{pos_y}")
        
        self.ruta_a = tk.StringVar()
        self.ruta_b = tk.StringVar()
        self.filtro_var = tk.StringVar()
        self.items_analizados = [] # Base de datos completa del análisis

        # --- Interfaz de Rutas ---
        f_rutas = tk.LabelFrame(root, text=" Configuración de Carpetas ", padx=10, pady=10)
        f_rutas.pack(pady=10, padx=15, fill="x")

        tk.Label(f_rutas, text="Carpeta A:").grid(row=0, column=0, sticky="e")
        tk.Entry(f_rutas, textvariable=self.ruta_a, width=80).grid(row=0, column=1, padx=5)
        tk.Button(f_rutas, text="Buscar", command=lambda: self.seleccionar(self.ruta_a)).grid(row=0, column=2)

        tk.Label(f_rutas, text="Carpeta B:").grid(row=1, column=0, sticky="e", pady=5)
        tk.Entry(f_rutas, textvariable=self.ruta_b, width=80).grid(row=1, column=1, padx=5)
        tk.Button(f_rutas, text="Buscar", command=lambda: self.seleccionar(self.ruta_b)).grid(row=1, column=2)

        # --- Panel de Control (Filtros y Acciones) ---
        f_control = tk.Frame(root, padx=15)
        f_control.pack(fill="x", pady=5)

        self.btn_ana = tk.Button(f_control, text="🔍 ANALIZAR", command=self.iniciar_analisis, bg="#28a745", fg="white", font=('Arial', 9, 'bold'))
        self.btn_ana.pack(side=tk.LEFT, padx=5)

        tk.Label(f_control, text=" |  Filtrar por nombre/extensión:").pack(side=tk.LEFT, padx=5)
        self.entry_filtro = tk.Entry(f_control, textvariable=self.filtro_var, width=25)
        self.entry_filtro.pack(side=tk.LEFT, padx=5)
        self.filtro_var.trace_add("write", lambda *args: self.refrescar_tabla())

        self.btn_all = tk.Button(f_control, text="☑ Seleccionar Todos", command=self.seleccionar_todos, state="disabled")
        self.btn_all.pack(side=tk.LEFT, padx=10)
        
        self.btn_none = tk.Button(f_control, text="☐ Desmarcar", command=self.desmarcar_todos, state="disabled")
        self.btn_none.pack(side=tk.LEFT)

        # --- Tabla de Archivos ---
        columnas = ("accion", "archivo", "detalles")
        self.tree = ttk.Treeview(root, columns=columnas, show="headings", selectmode="extended")
        self.tree.heading("accion", text="Acción Sugerida")
        self.tree.heading("archivo", text="Ruta Relativa del Archivo")
        self.tree.heading("detalles", text="Estado / Fecha")
        self.tree.column("accion", width=150)
        self.tree.column("archivo", width=400)
        self.tree.column("detalles", width=400)
        
        vsb = ttk.Scrollbar(root, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.pack(pady=10, padx=15, fill=tk.BOTH, expand=True)
        vsb.pack(side=tk.RIGHT, fill=tk.Y, in_=self.tree)

        # --- Sincronización y Progreso ---
        f_footer = tk.Frame(root, pady=10)
        f_footer.pack(fill="x")
        
        self.btn_sync = tk.Button(f_footer, text="🚀 SINCRONIZAR SELECCIONADOS", command=self.iniciar_sincronizacion, 
                                 bg="#007bff", fg="white", state="disabled", font=('Arial', 10, 'bold'), height=2)
        self.btn_sync.pack(pady=5)

        self.progress = ttk.Progressbar(f_footer, orient="horizontal", length=800, mode="determinate")
        self.progress.pack(pady=5)
        self.lbl_status = tk.Label(f_footer, text="Esperando carpetas...", fg="gray")
        self.lbl_status.pack()

    def seleccionar(self, var):
        r = filedialog.askdirectory()
        if r: var.set(r)

    def formatear_fecha(self, timestamp):
        return datetime.fromtimestamp(timestamp).strftime('%d/%m/%y %H:%M')

    def iniciar_analisis(self):
        if not self.ruta_a.get() or not self.ruta_b.get():
            messagebox.showwarning("Error", "Debes configurar ambas rutas.")
            return
        self.btn_ana.config(state="disabled")
        self.lbl_status.config(text="Escaneando archivos...")
        threading.Thread(target=self.hilo_analizar, daemon=True).start()

    def hilo_analizar(self):
        self.items_analizados = []
        pa, pb = Path(self.ruta_a.get()), Path(self.ruta_b.get())
        
        def scan(p):
            return {f.relative_to(p): f for f in p.rglob('*') if f.is_file() and not any(part.startswith('.') for part in f.parts)}

        items_a = scan(pa); items_b = scan(pb)
        todos = sorted(set(items_a.keys()) | set(items_b.keys()))

        for rel in todos:
            info = None
            if rel in items_a and rel in items_b:
                ma, mb = items_a[rel].stat().st_mtime, items_b[rel].stat().st_mtime
                if abs(ma - mb) > 2:
                    if ma > mb:
                        info = ("B <- A (Actualizar)", str(rel), f"Origen más nuevo ({self.formatear_fecha(ma)})", items_a[rel], pb/rel)
                    else:
                        info = ("A <- B (Actualizar)", str(rel), f"Destino más nuevo ({self.formatear_fecha(mb)})", items_b[rel], pa/rel)
            elif rel in items_a:
                info = ("Copiar a B", str(rel), "Archivo nuevo en A", items_a[rel], pb/rel)
            else:
                info = ("Copiar a A", str(rel), "Archivo nuevo en B", items_b[rel], pa/rel)
            
            if info: self.items_analizados.append(info)

        self.root.after(0, self.finalizar_analisis)

    def finalizar_analisis(self):
        self.btn_ana.config(state="normal")
        self.btn_all.config(state="normal")
        self.btn_none.config(state="normal")
        self.refrescar_tabla()
        self.lbl_status.config(text=f"Análisis terminado. {len(self.items_analizados)} cambios detectados.")

    def refrescar_tabla(self):
        """Limpia y vuelve a llenar la tabla aplicando el filtro de búsqueda."""
        self.tree.delete(*self.tree.get_children())
        filtro = self.filtro_var.get().lower()
        
        for idx, item in enumerate(self.items_analizados):
            # item[1] es el nombre del archivo
            if filtro in item[1].lower():
                self.tree.insert("", tk.END, iid=idx, values=(item[0], item[1], item[2]))
        
        self.btn_sync.config(state="normal" if self.items_analizados else "disabled")

    def seleccionar_todos(self):
        self.tree.selection_set(self.tree.get_children())

    def desmarcar_todos(self):
        self.tree.selection_remove(self.tree.selection())

    def iniciar_sincronizacion(self):
        seleccionados = self.tree.selection()
        if not seleccionados:
            messagebox.showwarning("Atención", "Selecciona al menos un archivo de la lista.")
            return

        if not messagebox.askyesno("Confirmar", f"¿Sincronizar {len(seleccionados)} archivos?"):
            return

        self.btn_sync.config(state="disabled")
        lista_trabajo = [self.items_analizados[int(idx)] for idx in seleccionados]
        
        self.progress['maximum'] = len(lista_trabajo)
        threading.Thread(target=self.hilo_sincronizar, args=(lista_trabajo,), daemon=True).start()

    def hilo_sincronizar(self, lista):
        exitos = 0
        for i, (_, nombre, _, orig, dest) in enumerate(lista):
            try:
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(orig, dest)
                exitos += 1
                self.root.after(0, lambda v=i+1: self.actualizar_progreso(v, len(lista)))
            except: pass
        
        self.root.after(0, lambda: self.finalizar_sincronizacion(exitos))

    def actualizar_progreso(self, valor, total):
        self.progress['value'] = valor
        self.lbl_status.config(text=f"Sincronizando... {valor}/{total}")

    def finalizar_sincronizacion(self, exitos):
        messagebox.showinfo("Éxito", f"Se han sincronizado {exitos} archivos correctamente.")
        self.iniciar_analisis()

if __name__ == "__main__":
    root = tk.Tk()
    app = SincronizadorUltra(root)
    root.mainloop()