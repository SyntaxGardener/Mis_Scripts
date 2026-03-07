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
        self.root.title("Sincronizador de Carpetas")
        
        # Geometría
        ancho, alto = 1050, 850
        pos_x = (self.root.winfo_screenwidth() // 2) - (ancho // 2)
        self.root.geometry(f"{ancho}x{alto}+{pos_x}+0")
        
        # Variables
        self.ruta_a = tk.StringVar()
        self.ruta_b = tk.StringVar()
        self.filtro_var = tk.StringVar()
        self.items_analizados = [] 

        # --- Interfaz de Rutas ---
        f_rutas = tk.LabelFrame(root, text=" 📂 Selección de Directorios ", padx=10, pady=10)
        f_rutas.pack(pady=10, padx=15, fill="x")

        for i, (label, var) in enumerate([("Carpeta A:", self.ruta_a), ("Carpeta B:", self.ruta_b)]):
            tk.Label(f_rutas, text=label).grid(row=i, column=0, sticky="e", pady=2)
            tk.Entry(f_rutas, textvariable=var, width=80).grid(row=i, column=1, padx=5)
            tk.Button(f_rutas, text="Explorar", command=lambda v=var: self.seleccionar(v)).grid(row=i, column=2)

        # --- Panel de Control con Buscador ---
        f_control = tk.Frame(root, padx=15)
        f_control.pack(fill="x", pady=5)

        self.btn_ana = tk.Button(f_control, text="🔍 INICIAR ANÁLISIS", command=self.iniciar_analisis, bg="#28a745", fg="white", font=('Arial', 9, 'bold'), padx=10)
        self.btn_ana.pack(side=tk.LEFT)

        # --- AQUÍ ESTÁ LA BARRA DE BÚSQUEDA ---
        tk.Label(f_control, text="   🔎 Filtrar resultados:", font=('Arial', 9, 'bold')).pack(side=tk.LEFT)
        self.entry_filtro = tk.Entry(f_control, textvariable=self.filtro_var, width=35, font=('Arial', 10))
        self.entry_filtro.pack(side=tk.LEFT, padx=5)
        self.entry_filtro.insert(0, "Escribe nombre o extensión...")
        self.entry_filtro.bind("<FocusIn>", lambda e: self.entry_filtro.delete(0, tk.END) if self.filtro_var.get() == "Escribe nombre o extensión..." else None)
        
        # Evento que dispara el filtro al escribir
        self.filtro_var.trace_add("write", lambda *args: self.refrescar_tabla())

        # --- Tabla de Archivos ---
        self.tree = ttk.Treeview(root, columns=("archivo", "detalles"), show="tree headings")
        self.tree.heading("#0", text="Estado / Acción")
        self.tree.heading("archivo", text="Ruta del Archivo")
        self.tree.heading("detalles", text="Comparativa de Fechas")
        self.tree.column("#0", width=280); self.tree.column("archivo", width=380)
        
        self.tree.tag_configure('nuevo', foreground='#2e7d32', font=('Arial', 9, 'bold'))
        self.tree.tag_configure('actualizar', foreground='#1565c0')
        
        self.tree.pack(pady=10, padx=15, fill=tk.BOTH, expand=True)

        # --- Footer y Progreso ---
        f_footer = tk.Frame(root, pady=10)
        f_footer.pack(fill="x")
        
        self.btn_sync = tk.Button(f_footer, text="🚀 SINCRONIZAR MARCADOS", command=self.iniciar_sincronizacion, 
                                 bg="#007bff", fg="white", state="disabled", font=('Arial', 10, 'bold'), height=2, width=30)
        self.btn_sync.pack()

        self.progress = ttk.Progressbar(f_footer, orient="horizontal", length=600, mode="determinate")
        self.progress.pack(pady=5)
        self.lbl_status = tk.Label(f_footer, text="Esperando selección de carpetas...", fg="#666")
        self.lbl_status.pack()

    def seleccionar(self, var):
        r = filedialog.askdirectory()
        if r: var.set(r)

    def iniciar_analisis(self):
        if not self.ruta_a.get() or not self.ruta_b.get():
            messagebox.showwarning("Error", "Selecciona ambas carpetas primero.")
            return
        self.btn_ana.config(state="disabled")
        self.lbl_status.config(text="Analizando archivos... por favor espera.")
        threading.Thread(target=self.hilo_analizar, daemon=True).start()

    def hilo_analizar(self):
        self.items_analizados = []
        pa, pb = Path(self.ruta_a.get()), Path(self.ruta_b.get())
        
        def scan(p):
            # Filtramos archivos ocultos o de sistema (los que empiezan por .)
            return {f.relative_to(p): f for f in p.rglob('*') if f.is_file() and not any(part.startswith('.') for part in f.parts)}

        try:
            items_a, items_b = scan(pa), scan(pb)
            todos = sorted(set(items_a.keys()) | set(items_b.keys()))

            for rel in todos:
                f_a, f_b = items_a.get(rel), items_b.get(rel)
                
                if f_a and f_b:
                    ma, mb = f_a.stat().st_mtime, f_b.stat().st_mtime
                    if abs(ma - mb) > 2: # Margen de 2 segundos para sistemas de archivos distintos
                        if ma > mb:
                            self.items_analizados.append((3, "🔄 Actualizar B (A es más nuevo)", str(rel), f"A: {self.fmt(ma)} > B: {self.fmt(mb)}", f_a, pb/rel, 'actualizar'))
                        else:
                            self.items_analizados.append((4, "🔄 Actualizar A (B es más nuevo)", str(rel), f"B: {self.fmt(mb)} > A: {self.fmt(ma)}", f_b, pa/rel, 'actualizar'))
                elif f_a:
                    self.items_analizados.append((1, "➕ Solo en A (Copiar a B)", str(rel), "Archivo nuevo", f_a, pb/rel, 'nuevo'))
                else:
                    self.items_analizados.append((2, "➕ Solo en B (Copiar a A)", str(rel), "Archivo nuevo", f_b, pa/rel, 'nuevo'))
            
            self.items_analizados.sort(key=lambda x: (x[0], x[2]))
        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("Error de lectura", str(e)))

        self.root.after(0, self.finalizar_analisis)

    def fmt(self, ts): return datetime.fromtimestamp(ts).strftime('%d/%m/%y %H:%M')

    def finalizar_analisis(self):
        self.btn_ana.config(state="normal")
        self.refrescar_tabla()
        self.lbl_status.config(text=f"Análisis completo: {len(self.items_analizados)} diferencias.")

    def refrescar_tabla(self):
        self.tree.delete(*self.tree.get_children())
        filtro = self.filtro_var.get().lower()
        if filtro == "escribe nombre o extensión...": filtro = ""
        
        padres = {}
        for idx, (peso, cat, archivo, det, orig, dest, tag) in enumerate(self.items_analizados):
            if filtro in archivo.lower() or filtro in cat.lower():
                if cat not in padres:
                    padres[cat] = self.tree.insert("", tk.END, text=cat, open=True)
                
                self.tree.insert(padres[cat], tk.END, iid=idx, text="  [ ]", values=(archivo, det), tags=(tag,))
        
        self.btn_sync.config(state="normal" if self.items_analizados else "disabled")

    def iniciar_sincronizacion(self):
        seleccionados = [s for s in self.tree.selection() if s.isdigit()]
        if not seleccionados:
            messagebox.showwarning("Aviso", "Haz clic en los archivos de la lista para seleccionarlos (puedes usar Ctrl o Shift).")
            return

        if messagebox.askyesno("Confirmar", f"¿Sincronizar estos {len(seleccionados)} archivos?"):
            self.btn_sync.config(state="disabled")
            lista = [self.items_analizados[int(idx)] for idx in seleccionados]
            self.progress['maximum'] = len(lista)
            threading.Thread(target=self.hilo_sincronizar, args=(lista,), daemon=True).start()

    def hilo_sincronizar(self, lista):
        exitos = 0
        for i, (_, _, _, _, orig, dest, _) in enumerate(lista):
            try:
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(orig, dest)
                exitos += 1
                self.root.after(0, lambda v=i+1: self.actualizar_progreso(v, len(lista)))
            except: pass
        self.root.after(0, lambda: self.finalizar_sincronizacion(exitos))

    def actualizar_progreso(self, v, t):
        self.progress['value'] = v
        self.lbl_status.config(text=f"Copiando... {v} de {t}")

    def finalizar_sincronizacion(self, e):
        messagebox.showinfo("Hecho", f"Se han sincronizado {e} archivos.")
        self.iniciar_analisis()

if __name__ == "__main__":
    root = tk.Tk()
    app = SincronizadorUltra(root)
    root.mainloop()