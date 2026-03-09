# -*- coding: utf-8 -*-
import os
import subprocess
import platform
import threading
import shutil
from pathlib import Path
from datetime import datetime
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

class SincronizadorUltra:
    def __init__(self, root):
        self.root = root
        self.root.title("Sincronizador de Carpetas")
        
        # Geometria
        ancho, alto = 1050, 850
        pos_x = (self.root.winfo_screenwidth() // 2) - (ancho // 2)
        self.root.geometry(f"{ancho}x{alto}+{pos_x}+0")
        
        # Variables
        self.ruta_a = tk.StringVar()
        self.ruta_b = tk.StringVar()
        self.filtro_var = tk.StringVar()
        self.items_analizados = [] 

        # --- Interfaz de Rutas ---
        f_rutas = tk.LabelFrame(root, text=" Seleccion de Directorios ", padx=10, pady=10)
        f_rutas.pack(pady=10, padx=15, fill="x")

        for i, (label, var) in enumerate([("Carpeta A:", self.ruta_a), ("Carpeta B:", self.ruta_b)]):
            tk.Label(f_rutas, text=label).grid(row=i, column=0, sticky="e", pady=2)
            tk.Entry(f_rutas, textvariable=var, width=80).grid(row=i, column=1, padx=5)
            tk.Button(f_rutas, text="Explorar", command=lambda v=var: self.seleccionar(v)).grid(row=i, column=2)

        # --- Panel de Control ---
        f_control = tk.Frame(root, padx=15)
        f_control.pack(fill="x", pady=5)

        self.btn_ana = tk.Button(f_control, text="ANALIZAR", command=self.iniciar_analisis, bg="#28a745", fg="white", font=('Arial', 9, 'bold'), padx=10)
        self.btn_ana.pack(side=tk.LEFT)

        tk.Label(f_control, text="   Filtrar:").pack(side=tk.LEFT)
        self.entry_filtro = tk.Entry(f_control, textvariable=self.filtro_var, width=30)
        self.entry_filtro.pack(side=tk.LEFT, padx=5)
        self.filtro_var.trace_add("write", lambda *args: self.refrescar_tabla())

        self.btn_invertir = tk.Button(f_control, text="Invertir Seleccion", command=self.invertir_seleccion)
        self.btn_invertir.pack(side=tk.RIGHT)

        # --- Tabla ---
        self.tree = ttk.Treeview(root, columns=("archivo", "detalles"), show="tree headings")
        self.tree.heading("#0", text="Estado / Accion")
        self.tree.heading("archivo", text="Ruta del Archivo")
        self.tree.heading("detalles", text="Comparativa de Fechas")
        self.tree.column("#0", width=280); self.tree.column("archivo", width=380)
        
        self.tree.tag_configure('nuevo', foreground='#2e7d32', font=('Arial', 9, 'bold'))
        self.tree.tag_configure('actualizar', foreground='#1565c0')
        self.tree.pack(pady=10, padx=15, fill=tk.BOTH, expand=True)

        # Menu contextual
        self.menu_contextual = tk.Menu(self.root, tearoff=0)
        self.menu_contextual.add_command(label="Abrir carpeta contenedora", command=self.abrir_carpeta_archivo)
        self.tree.bind("<Button-3>", self.mostrar_menu)
        self.tree.bind("<Button-2>", self.mostrar_menu)

        # --- Footer ---
        f_footer = tk.Frame(root, pady=10)
        f_footer.pack(fill="x")
        
        f_botones = tk.Frame(f_footer)
        f_botones.pack()

        self.btn_sync = tk.Button(f_botones, text="SINCRONIZAR", command=self.iniciar_sincronizacion, 
                                 bg="#007bff", fg="white", state="disabled", font=('Arial', 10, 'bold'), height=2, width=20)
        self.btn_sync.pack(side=tk.LEFT, padx=5)

        self.btn_del = tk.Button(f_botones, text="BORRAR", command=self.iniciar_borrado, 
                                bg="#dc3545", fg="white", state="disabled", font=('Arial', 10, 'bold'), height=2, width=20)
        self.btn_del.pack(side=tk.LEFT, padx=5)

        self.progress = ttk.Progressbar(f_footer, orient="horizontal", length=600, mode="determinate")
        self.progress.pack(pady=10)
        self.lbl_status = tk.Label(f_footer, text="Listo.", fg="#666")
        self.lbl_status.pack()

    def seleccionar(self, var):
        r = filedialog.askdirectory()
        if r: var.set(r)

    def mostrar_menu(self, event):
        item = self.tree.identify_row(event.y)
        if item:
            self.tree.selection_set(item)
            self.menu_contextual.post(event.x_root, event.y_root)

    def abrir_carpeta_archivo(self):
        seleccion = self.tree.selection()
        if not seleccion or not seleccion[0].isdigit(): return
        ruta_completa = self.items_analizados[int(seleccion[0])][4]
        carpeta = ruta_completa.parent
        if platform.system() == "Windows": os.startfile(carpeta)
        elif platform.system() == "Darwin": subprocess.Popen(["open", str(carpeta)])
        else: subprocess.Popen(["xdg-open", str(carpeta)])

    def invertir_seleccion(self):
        todos = [i for i in self.tree.get_children() if i.isdigit()]
        actuales = self.tree.selection()
        nuevos = [i for i in todos if i not in actuales]
        self.tree.selection_set(nuevos)

    def iniciar_analisis(self):
        if not self.ruta_a.get() or not self.ruta_b.get():
            messagebox.showwarning("Error", "Selecciona ambas carpetas.")
            return
        self.btn_ana.config(state="disabled")
        threading.Thread(target=self.hilo_analizar, daemon=True).start()

    def hilo_analizar(self):
        self.items_analizados = []
        pa, pb = Path(self.ruta_a.get()), Path(self.ruta_b.get())
        def scan(p):
            return {f.relative_to(p): f for f in p.rglob('*') if f.is_file() and not any(part.startswith('.') for part in f.parts)}
        try:
            items_a, items_b = scan(pa), scan(pb)
            todos = sorted(set(items_a.keys()) | set(items_b.keys()))
            for rel in todos:
                f_a, f_b = items_a.get(rel), items_b.get(rel)
                if f_a and f_b:
                    ma, mb = f_a.stat().st_mtime, f_b.stat().st_mtime
                    if abs(ma - mb) > 2:
                        if ma > mb: self.items_analizados.append((3, "Actualizar B", str(rel), f"A es mas nuevo", f_a, pb/rel, 'actualizar'))
                        else: self.items_analizados.append((4, "Actualizar A", str(rel), f"B es mas nuevo", f_b, pa/rel, 'actualizar'))
                elif f_a: self.items_analizados.append((1, "Solo en A", str(rel), "Copia a B", f_a, pb/rel, 'nuevo'))
                else: self.items_analizados.append((2, "Solo en B", str(rel), "Copia a A", f_b, pa/rel, 'nuevo'))
        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("Error", str(e)))
        self.root.after(0, self.finalizar_analisis)

    def fmt(self, ts): return datetime.fromtimestamp(ts).strftime('%d/%m/%y %H:%M')
    def finalizar_analisis(self):
        self.btn_ana.config(state="normal"); self.refrescar_tabla()

    def refrescar_tabla(self):
        self.tree.delete(*self.tree.get_children())
        filtro = self.filtro_var.get().lower()
        padres = {}
        for idx, (peso, cat, archivo, det, orig, dest, tag) in enumerate(self.items_analizados):
            if filtro in archivo.lower() or filtro in cat.lower():
                if cat not in padres: padres[cat] = self.tree.insert("", tk.END, text=cat, open=True)
                self.tree.insert(padres[cat], tk.END, iid=idx, text=" [ ]", values=(archivo, det), tags=(tag,))
        st = "normal" if self.items_analizados else "disabled"
        self.btn_sync.config(state=st); self.btn_del.config(state=st)

    def iniciar_sincronizacion(self):
        sel = [s for s in self.tree.selection() if s.isdigit()]
        if not sel: return
        if messagebox.askyesno("Confirmar", "Sincronizar seleccionados?"):
            lista = [self.items_analizados[int(idx)] for idx in sel]
            self.progress['maximum'] = len(lista)
            threading.Thread(target=self.hilo_sincronizar, args=(lista,), daemon=True).start()

    def hilo_sincronizar(self, lista):
        for i, (_, _, _, _, orig, dest, _) in enumerate(lista):
            try:
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(orig, dest)
                self.root.after(0, lambda v=i+1: self.actualizar_progreso(v, len(lista), "Copiando"))
            except: pass
        self.root.after(0, self.iniciar_analisis)

    def iniciar_borrado(self):
        sel = [s for s in self.tree.selection() if s.isdigit()]
        if not sel: return
        if messagebox.askyesno("PELIGRO", "Borrar archivos originales?"):
            lista = [self.items_analizados[int(idx)] for idx in sel]
            self.progress['maximum'] = len(lista)
            threading.Thread(target=self.hilo_borrar, args=(lista,), daemon=True).start()

    def hilo_borrar(self, lista):
        for i, (_, _, _, _, orig, _, _) in enumerate(lista):
            try:
                if orig.exists(): os.remove(orig)
                self.root.after(0, lambda v=i+1: self.actualizar_progreso(v, len(lista), "Borrando"))
            except: pass
        self.root.after(0, self.iniciar_analisis)

    def actualizar_progreso(self, v, t, texto):
        self.progress['value'] = v
        self.lbl_status.config(text=f"{texto}: {v}/{t}")

if __name__ == "__main__":
    root = tk.Tk()
    app = SincronizadorUltra(root)
    root.mainloop()