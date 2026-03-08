# -*- coding: utf-8 -*-
import tkinter as tk
from tkinter import messagebox, simpledialog
import subprocess
import os
import sys
import shutil
import threading

# --- CONFIGURACIÓN VISUAL ---
COLORES = {
    "FAVORITOS": "#ffffff",
    "SISTEMA": "#ff4d4d",
    "PDF": "#3498db",
    "ADMINISTRACIÓN": "#f1c40f",
    "CLASES": "#9b59b6",
    "AULA": "#2ecc71",
    "OTROS": "#e0e0e0"
}
FAV_FILE = "favoritos.txt"

# --- FUNCIONES DE SOPORTE ---
def leer_favoritos():
    if os.path.exists(FAV_FILE):
        try:
            with open(FAV_FILE, "r", encoding="utf-8") as f:
                return [line.strip() for line in f.readlines()]
        except: return []
    return []

def guardar_favoritos(favoritos):
    with open(FAV_FILE, "w", encoding="utf-8") as f:
        for fav in favoritos: f.write(f"{fav}\n")

def obtener_info_sistema():
    v_python = f"Py {sys.version_info.major}.{sys.version_info.minor}"
    ruta_base = os.path.dirname(os.path.abspath(__file__))
    unidad = os.path.splitdrive(ruta_base)[0]
    try:
        total, usado, libre = shutil.disk_usage(unidad if unidad else "/")
        gb_libres = libre // (2**30)
        return f"{v_python}  |  {unidad if unidad else 'C:'} ({gb_libres} GB libres)"
    except:
        return f"{v_python}"

def ejecutar_herramienta(ruta_archivo, ventana_principal):
    try:
        if not os.path.exists(ruta_archivo):
            messagebox.showerror("Error", f"El archivo NO existe en:\n{ruta_archivo}")
            return
        ruta_abs = os.path.abspath(ruta_archivo)
        exe_py = sys.executable.replace("pythonw.exe", "python.exe")
        if ruta_abs.lower().endswith(".py"):
            subprocess.Popen([exe_py, ruta_abs], creationflags=subprocess.CREATE_NEW_CONSOLE)
        elif ruta_abs.lower().endswith(".pyw"):
            subprocess.Popen([sys.executable, ruta_abs])
        else:
            os.startfile(ruta_abs)
    except Exception as e:
        messagebox.showerror("Error Crítico", f"Fallo al lanzar:\n{e}")

# --- CLASE PRINCIPAL ---
class MenuFinalPerfecto:
    def __init__(self, root):
        self.root = root
        self.root.title("BIBLIOTECA DE HERRAMIENTAS - GIT SYNC")
        self.root.geometry("820x850")
        self.root.configure(bg="#121212")
        
        self.favoritos = leer_favoritos()
        self.estados_carpetas = {cat: False for cat in COLORES.keys()}

        # --- 1. HEADER ---
        header_frame = tk.Frame(self.root, bg="#121212")
        header_frame.pack(fill="x", padx=20, pady=10)
        tk.Label(header_frame, text="MIS HERRAMIENTAS", fg="#ffffff", bg="#121212", font=("Segoe UI Semibold", 18)).pack(side="left", padx=10)
        
        # Botones de Git y Refrescar
        tk.Button(header_frame, text="🔄", font=("Segoe UI", 10, "bold"), bg="#333333", fg="white", 
                  relief="flat", command=self.actualizar_todo).pack(side="right", padx=5)
        
        self.btn_push = tk.Button(header_frame, text="☁️ SUBIR CAMBIOS", font=("Segoe UI", 8, "bold"), bg="#333333", fg="white", 
                                  relief="flat", state="disabled", command=self.realizar_push)
        self.btn_push.pack(side="right", padx=5)

        self.btn_pull = tk.Button(header_frame, text="📥 DESCARGAR NOVEDADES", font=("Segoe UI", 8, "bold"), bg="#333333", fg="white", 
                                  relief="flat", state="disabled", command=self.realizar_pull)
        self.btn_pull.pack(side="right", padx=5)

        # --- 2. BUSCADOR ---
        search_frame = tk.Frame(self.root, bg="#2d2d2d", padx=10, pady=5)
        search_frame.pack(fill="x", padx=50, pady=(5, 5))
        self.entry_busqueda = tk.Entry(search_frame, bg="#2d2d2d", fg="white", borderwidth=0, font=("Segoe UI", 11))
        self.entry_busqueda.pack(side="left", fill="x", expand=True)
        self.entry_busqueda.insert(0, "Buscar...")
        self.entry_busqueda.bind("<FocusIn>", lambda e: self.entry_busqueda.delete(0, "end") if self.entry_busqueda.get() == "Buscar..." else None)
        self.entry_busqueda.bind("<KeyRelease>", self.filtrar_scripts)

        # --- 3. BARRA DE INFORMACIÓN ---
        self.status_bar = tk.Frame(self.root, bg="#1a1a1a", height=30)
        self.status_bar.pack(fill="x", padx=50, pady=(5, 10))
        
        self.lbl_modo = tk.Label(self.status_bar, fg="#aaaaaa", bg="#1a1a1a", font=("Segoe UI", 8, "bold"))
        self.lbl_modo.pack(side="left", padx=10)
        
        self.lbl_git = tk.Label(self.status_bar, text="Git: Comprobando...", fg="#00ffff", bg="#1a1a1a", font=("Segoe UI", 8, "bold"))
        self.lbl_git.pack(side="left", padx=20)
        
        self.lbl_info = tk.Label(self.status_bar, fg="#888888", bg="#1a1a1a", font=("Segoe UI", 8))
        self.lbl_info.pack(side="right", padx=10)
        
        self.actualizar_barra_estado()

        # --- 4. CONTENEDOR ---
        self.container = tk.Frame(self.root, bg="#181818")
        self.container.pack(fill="both", expand=True, padx=20, pady=(0, 20))
        self.canvas = tk.Canvas(self.container, bg="#181818", highlightthickness=0)
        self.scrollbar = tk.Scrollbar(self.container, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = tk.Frame(self.canvas, bg="#181818")
        self.scrollable_frame.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas_frame = self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.bind('<Configure>', lambda e: self.canvas.itemconfig(self.canvas_frame, width=e.width))
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")
        self.root.bind_all("<MouseWheel>", self._on_mousewheel)
        
        self.cargar_scripts()
        threading.Thread(target=self.comprobar_git_status, daemon=True).start()

    # --- LÓGICA DE GIT ---
    def comprobar_git_status(self):
        try:
            subprocess.run(["git", "fetch"], capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)
            cambios_locales = subprocess.check_output(["git", "status", "--porcelain"], text=True, creationflags=subprocess.CREATE_NO_WINDOW).strip()
            
            # Comparación de commits (local vs remoto)
            res_comp = subprocess.check_output(["git", "rev-list", "--left-right", "--count", "main...origin/main"], text=True, creationflags=subprocess.CREATE_NO_WINDOW).strip()
            atras, adelante = res_comp.split('\t') # atras: commits locales no subidos, adelante: commits remotos no bajados

            if cambios_locales:
                self.lbl_git.config(text="⚠️ TIENES CAMBIOS SIN GUARDAR EN EL PC", fg="#ff8c00")
                self.btn_push.config(bg="#ff8c00", fg="black", state="normal")
                self.btn_pull.config(bg="#333333", fg="white", state="disabled")
            elif int(adelante) > 0:
                self.lbl_git.config(text=f"🚀 {adelante} NOVEDADES EN GITHUB", fg="#ffff00")
                self.btn_pull.config(bg="#3498db", fg="white", state="normal")
                self.btn_push.config(bg="#333333", fg="white", state="disabled")
            elif int(atras) > 0:
                self.lbl_git.config(text="⬆️ COMMITS PENDIENTES DE SUBIR", fg="#2ecc71")
                self.btn_push.config(bg="#2ecc71", fg="black", state="normal")
                self.btn_pull.config(bg="#333333", fg="white", state="disabled")
            else:
                self.lbl_git.config(text="✅ TODO SINCRONIZADO", fg="#00ff00")
                self.btn_push.config(bg="#333333", fg="white", state="disabled")
                self.btn_pull.config(bg="#333333", fg="white", state="disabled")
        except:
            self.lbl_git.config(text="❌ ERROR DE CONEXIÓN GIT", fg="#ff4d4d")

    def realizar_push(self):
        mensaje = simpledialog.askstring("Git Push", "Nombre del cambio (Commit message):", parent=self.root)
        if mensaje:
            try:
                subprocess.run(["git", "add", "."], check=True, creationflags=subprocess.CREATE_NO_WINDOW)
                subprocess.run(["git", "commit", "-m", mensaje], check=True, creationflags=subprocess.CREATE_NO_WINDOW)
                subprocess.run(["git", "push"], check=True, creationflags=subprocess.CREATE_NO_WINDOW)
                messagebox.showinfo("Éxito", "Cambios subidos correctamente.")
                self.actualizar_todo()
            except Exception as e: messagebox.showerror("Error", str(e))

    def realizar_pull(self):
        if messagebox.askyesno("Git Pull", "¿Descargar las novedades de GitHub?"):
            try:
                subprocess.run(["git", "pull"], check=True, creationflags=subprocess.CREATE_NO_WINDOW)
                messagebox.showinfo("Éxito", "Archivos actualizados.")
                self.actualizar_todo()
            except Exception as e: messagebox.showerror("Error", str(e))

    # --- MÉTODOS DE INTERFAZ ---
    def actualizar_barra_estado(self):
        modo = "PORTABLE (USB)" if "C:" not in os.path.abspath(__file__).upper() else "PC LOCAL"
        self.lbl_modo.config(text=f"📍 {modo}")
        self.lbl_info.config(text=obtener_info_sistema())

    def actualizar_todo(self):
        self.actualizar_barra_estado()
        self.cargar_scripts()
        self.lbl_git.config(text="Comprobando...", fg="#00ffff")
        threading.Thread(target=self.comprobar_git_status, daemon=True).start()

    def _on_mousewheel(self, event):
        self.canvas.yview_scroll(int(-1*(event.delta/120)), "units")

    def clasificar(self, nombre):
        n = nombre.lower()
        if nombre in self.favoritos: return "FAVORITOS"
        if any(x in n for x in ["expulsar", "pc", "test", "usb", "imports", "limpieza", "borrar", "temp", "organizador"]): return "SISTEMA"
        if "pdf" in n: return "PDF"
        if any(x in n for x in ["examenes", "notas"]): return "CLASES"
        if any(x in n for x in ["horario", "diligencia", "certificados", "calculador", "diplomas"]): return "ADMINISTRACIÓN"
        if any(x in n for x in ["bingo", "crono", "traductor", "pasapalabra", "picker", "clase", "qr", "juego"]): return "AULA"
        return "OTROS"

    def cargar_scripts(self):
        for widget in self.scrollable_frame.winfo_children(): widget.destroy()
        termino = self.entry_busqueda.get().lower()
        if termino == "buscar...": termino = ""
        ruta_base = os.path.dirname(os.path.abspath(__file__))
        ignorar = [os.path.basename(__file__), "lanzador.bat", "iniciar.vbs"]
        try:
            archivos = [f for f in os.listdir(ruta_base) if f.lower().endswith(('.py', '.bat', '.pyw')) and f not in ignorar]
        except: return
        mapeo = {os.path.splitext(f)[0]: f for f in archivos}
        cats = {cat: [] for cat in COLORES.keys()}
        for f in mapeo.values():
            if termino and termino not in f.lower(): continue
            cats[self.clasificar(f)].append(f)
        fila = 0
        self.scrollable_frame.grid_columnconfigure((0, 1), weight=1)
        for cat, lista in cats.items():
            if not lista: continue
            abierta = True if termino else self.estados_carpetas.get(cat, False)
            tk.Button(self.scrollable_frame, text=f"  {'📂' if abierta else '📁'}  {cat}  [{len(lista)}]", 
                      font=("Segoe UI", 11, "bold"), bg="#1f1f1f", fg=COLORES[cat], relief="flat", anchor="w",
                      command=lambda c=cat: self.toggle_carpeta(c)).grid(row=fila, column=0, columnspan=2, sticky="ew", pady=(10, 2))
            fila += 1
            if abierta:
                for i, f in enumerate(sorted(lista)):
                    r, c = fila + (i // 2), i % 2
                    self.crear_boton(os.path.join(ruta_base, f), r, c, COLORES[cat])
                fila += (len(lista) + 1) // 2
        tk.Frame(self.scrollable_frame, height=50, bg="#181818").grid(row=fila, column=0)

    def crear_boton(self, ruta, f, c, col):
        nombre = os.path.splitext(os.path.basename(ruta))[0].replace("_", " ").capitalize()
        btn = tk.Button(self.scrollable_frame, text=nombre, font=("Segoe UI", 10, "bold"), bg="#252525", fg=col,
                        relief="flat", height=2, command=lambda: ejecutar_herramienta(ruta, self.root))
        btn.grid(row=f, column=c, sticky="nsew", padx=5, pady=5)
        btn.bind("<Button-3>", lambda e, n=os.path.basename(ruta): self.toggle_favorito(n))

    def toggle_carpeta(self, cat):
        self.estados_carpetas[cat] = not self.estados_carpetas[cat]
        self.cargar_scripts()

    def filtrar_scripts(self, e): self.cargar_scripts()

    def toggle_favorito(self, n):
        if n in self.favoritos: self.favoritos.remove(n)
        else: self.favoritos.append(n)
        guardar_favoritos(self.favoritos)
        self.cargar_scripts()

if __name__ == "__main__":
    root = tk.Tk()
    app = MenuFinalPerfecto(root)
    root.mainloop()