# -*- coding: utf-8 -*-
import tkinter as tk
from tkinter import messagebox, simpledialog
import subprocess
import os
import sys
import shutil
import threading
import webbrowser

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
GITHUB_URL = "https://github.com/SyntaxGardener/"

# --- FUNCIONES DE SOPORTE ---
def leer_favoritos():
    if os.path.exists(FAV_FILE):
        try:
            with open(FAV_FILE, "r", encoding="utf-8") as f:
                return [line.strip() for line in f.readlines()]
        except: 
            return []
    return []

def guardar_favoritos(favoritos):
    with open(FAV_FILE, "w", encoding="utf-8") as f:
        for fav in favoritos: 
            f.write(f"{fav}\n")

def obtener_info_sistema():
    v_python = f"Py {sys.version_info.major}.{sys.version_info.minor}"
    ruta_base = os.path.dirname(os.path.abspath(__file__))
    unidad = os.path.splitdrive(ruta_base)[0]
    try:
        total, usado, libre = shutil.disk_usage(unidad if unidad else "/")
        gb_libres = libre // (2**30)
        return f"{v_python}  |  {unidad if unidad else 'USB'} ({gb_libres} GB libres)"
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
        self.root.title("BIBLIOTECA DE HERRAMIENTAS - PORTABLE GIT SYNC")
        ancho = 800
        alto = 800
        pos_x = (self.root.winfo_screenwidth() // 2) - (ancho // 2)
        self.root.geometry(f"{ancho}x{alto}+{pos_x}+0")
        self.root.configure(bg="#121212")
        
        # --- RUTAS DINÁMICAS (Para que funcione en cualquier PC) ---
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        # Busca PortableGit un nivel arriba de donde esté este script
        self.ruta_git = os.path.normpath(os.path.join(self.base_dir, "..", "PortableGit", "bin", "git.exe"))
        self.ruta_config = os.path.normpath(os.path.join(self.base_dir, "..", "Config"))
        self.ruta_creds = os.path.join(self.ruta_config, ".git-credentials").replace("\\", "/")

        if not os.path.exists(self.ruta_config):
            os.makedirs(self.ruta_config)
        
        self.favoritos = leer_favoritos()
        self.estados_carpetas = {cat: False for cat in COLORES.keys()}

        # --- 1. HEADER ---
        header_frame = tk.Frame(self.root, bg="#121212")
        header_frame.pack(fill="x", padx=20, pady=10)
        
        title_container = tk.Frame(header_frame, bg="#121212")
        title_container.pack(side="left")

        tk.Label(title_container, text="MIS HERRAMIENTAS", fg="#ffffff", bg="#121212", 
                 font=("Segoe UI Semibold", 18)).pack(side="left", padx=(10, 5))

        self.github_btn = tk.Label(title_container, text="  SyntaxGardener", 
                                  fg="#8b949e", bg="#121212", 
                                  font=("Segoe UI Semibold", 9), cursor="hand2")
        self.github_btn.pack(side="left", padx=10, pady=(8, 0))
        self.github_btn.bind("<Button-1>", lambda e: webbrowser.open(GITHUB_URL))
        
        # Botones de Acción
        tk.Button(header_frame, text="🔄", font=("Segoe UI", 10, "bold"), bg="#333333", fg="white", 
                 relief="flat", command=self.actualizar_todo).pack(side="right", padx=5)
        
        self.btn_push = tk.Button(header_frame, text="☁️ SUBIR CAMBIOS", font=("Segoe UI", 8, "bold"), bg="#333333", fg="white", 
                                  relief="flat", state="disabled", command=self.realizar_push)
        self.btn_push.pack(side="right", padx=5)

        self.btn_pull = tk.Button(header_frame, text="📥 DESCARGAR", font=("Segoe UI", 8, "bold"), bg="#333333", fg="white", 
                                  relief="flat", command=self.realizar_pull)
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
        self.lbl_git = tk.Label(self.status_bar, text="Git: Buscando...", fg="#00ffff", bg="#1a1a1a", font=("Segoe UI", 8, "bold"))
        self.lbl_git.pack(side="left", padx=20)
        self.lbl_info = tk.Label(self.status_bar, fg="#888888", bg="#1a1a1a", font=("Segoe UI", 8))
        self.lbl_info.pack(side="right", padx=10)
        
        self.actualizar_barra_estado()

        # --- 4. CONTENEDOR CON SCROLL ---
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

    # --- MOTOR GIT PORTABLE ---
    def obtener_comando_git(self):
        return self.ruta_git if os.path.exists(self.ruta_git) else "git"

    def comprobar_git_status(self):
        try:
            cmd = self.obtener_comando_git()
            # 1. Configurar safe directory
            subprocess.run([cmd, "config", "--global", "safe.directory", "*"], creationflags=subprocess.CREATE_NO_WINDOW)
            
            # 2. TRAER INFO DEL SERVIDOR (FETCH) - Esto es lo que te faltaba
            # Usamos las credenciales guardadas en el USB
            subprocess.run([cmd, "config", "credential.helper", f"store --file {self.ruta_creds}"], cwd=self.base_dir, creationflags=subprocess.CREATE_NO_WINDOW)
            subprocess.run([cmd, "fetch"], cwd=self.base_dir, creationflags=subprocess.CREATE_NO_WINDOW)

            # 3. VER CAMBIOS LOCALES (lo que ya tenías)
            cambios_locales = subprocess.check_output([cmd, "status", "--porcelain"], cwd=self.base_dir, text=True, creationflags=subprocess.CREATE_NO_WINDOW).strip()
            
            # 4. VER SI ESTAMOS ATRASADOS (Cambios en el servidor)
            # Compara la rama local con la remota (suponiendo que es 'main')
            status_remoto = subprocess.check_output([cmd, "rev-list", "HEAD..origin/main", "--count"], cwd=self.base_dir, text=True, creationflags=subprocess.CREATE_NO_WINDOW).strip()
            atrasado = int(status_remoto) if status_remoto.isdigit() else 0

            # --- LÓGICA DE ETIQUETAS ---
            if cambios_locales:
                self.root.after(0, lambda: self.lbl_git.config(text="⚠️ CAMBIOS LOCALES PENDIENTES", fg="#ff8c00"))
                self.root.after(0, lambda: self.btn_push.config(bg="#ff8c00", fg="black", state="normal"))
            elif atrasado > 0:
                self.root.after(0, lambda: self.lbl_git.config(text=f"📥 {atrasado} CAMBIOS EN NUBE (DESCARGA)", fg="#00ffff"))
                self.root.after(0, lambda: self.btn_push.config(bg="#333333", fg="white", state="disabled"))
            else:
                self.root.after(0, lambda: self.lbl_git.config(text="✅ REPOSITORIO SINCRONIZADO", fg="#00ff00"))
                self.root.after(0, lambda: self.btn_push.config(bg="#333333", fg="white", state="disabled"))
            
        except Exception as e:
            print(f"Error Git: {e}")
            self.root.after(0, lambda: self.lbl_git.config(text="❌ ERROR AL SINCRONIZAR", fg="#ff4d4d"))

    def realizar_push(self):
        cmd = self.obtener_comando_git()
        mensaje = simpledialog.askstring("Git Push", "¿Qué cambios hiciste?", parent=self.root)
        if mensaje:
            try:
                # Usa las credenciales del USB exclusivamente
                subprocess.run([cmd, "config", "credential.helper", f"store --file {self.ruta_creds}"], cwd=self.base_dir, creationflags=subprocess.CREATE_NO_WINDOW)
                subprocess.run([cmd, "add", "."], cwd=self.base_dir, check=True, creationflags=subprocess.CREATE_NO_WINDOW)
                subprocess.run([cmd, "commit", "-m", mensaje], cwd=self.base_dir, check=True, creationflags=subprocess.CREATE_NO_WINDOW)
                res = subprocess.run([cmd, "push"], cwd=self.base_dir, capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW)
                
                if res.returncode == 0:
                    messagebox.showinfo("Éxito", "¡Subido a GitHub correctamente!")
                    self.actualizar_todo()
                else:
                    messagebox.showerror("Error", f"Fallo al subir:\n{res.stderr}")
            except Exception as e:
                messagebox.showerror("Error", str(e))

    def realizar_pull(self):
        cmd = self.obtener_comando_git()
        try:
            subprocess.run([cmd, "config", "credential.helper", f"store --file {self.ruta_creds}"], cwd=self.base_dir, creationflags=subprocess.CREATE_NO_WINDOW)
            res = subprocess.run([cmd, "pull"], cwd=self.base_dir, capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW)
            if res.returncode == 0:
                messagebox.showinfo("Éxito", "¡Archivos actualizados!")
                self.actualizar_todo()
            else:
                messagebox.showerror("Error", f"Fallo al descargar:\n{res.stderr}")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    # --- MÉTODOS DE INTERFAZ ---
    def actualizar_barra_estado(self):
        modo = "PORTABLE (USB)" if "C:" not in self.base_dir.upper() else "PC LOCAL"
        self.lbl_modo.config(text=f"📍 {modo}")
        self.lbl_info.config(text=obtener_info_sistema())

    def cargar_scripts(self):
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()
    
        termino = self.entry_busqueda.get().lower()
        if termino == "buscar...": 
            termino = ""
    
        # Lista de archivos a ignorar
        ignorar = ["lanzador.bat", "iniciar.vbs", "favoritos.txt"]
        script_actual = os.path.basename(__file__)
    
        try:
            # Obtener archivos válidos (excluyendo ignorados)
            archivos = [f for f in os.listdir(self.base_dir) 
                       if f.lower().endswith(('.py', '.bat', '.pyw')) 
                       and f not in ignorar 
                       and f != script_actual]
        
            # CLASIFICAR POR CATEGORÍAS
            cats = {cat: [] for cat in COLORES.keys()}
            for f in archivos:
                if termino and termino not in f.lower():
                    continue
                cats[self.clasificar(f)].append(f)
        
            # MOSTRAR EN LA INTERFAZ
            fila = 0
            self.scrollable_frame.grid_columnconfigure((0, 1), weight=1)
        
            for cat, lista in cats.items():
                if not lista:
                    continue
                
                # Determinar si la carpeta está abierta
                abierta = True if termino else self.estados_carpetas.get(cat, False)
            
                # Botón de categoría
                btn_carpeta = tk.Button(
                    self.scrollable_frame, 
                    text=f"  {'📂' if abierta else '📁'}  {cat}  [{len(lista)}]", 
                    font=("Segoe UI", 11, "bold"), 
                    bg="#1f1f1f", 
                    fg=COLORES[cat], 
                    relief="flat", 
                    anchor="w",
                    command=lambda c=cat: self.toggle_carpeta(c)
                )
                btn_carpeta.grid(row=fila, column=0, columnspan=2, sticky="ew", pady=(10, 2))
                fila += 1
            
                # Mostrar scripts si la carpeta está abierta
                if abierta:
                    for i, f in enumerate(sorted(lista)):
                        r, c = fila + (i // 2), i % 2
                        self.crear_boton(os.path.join(self.base_dir, f), r, c, COLORES[cat])
                    fila += (len(lista) + 1) // 2
                
        except Exception as e:
            print(f"Error al cargar scripts: {e}")
            # Mostrar mensaje de error en la interfaz
            error_label = tk.Label(
                self.scrollable_frame, 
                text=f"Error: {e}", 
                fg="#ff4d4d", 
                bg="#181818"
            )
            error_label.grid(row=0, column=0, pady=20)
            return

    def crear_boton(self, ruta, f, c, col):
        nombre = os.path.splitext(os.path.basename(ruta))[0].replace("_", " ").capitalize()
        btn = tk.Button(self.scrollable_frame, text=nombre, font=("Segoe UI", 10, "bold"), bg="#252525", fg=col,
                        relief="flat", height=2, command=lambda: ejecutar_herramienta(ruta, self.root))
        btn.grid(row=f, column=c, sticky="nsew", padx=5, pady=5)
        btn.bind("<Button-3>", lambda e, n=os.path.basename(ruta): self.toggle_favorito(n))

    def clasificar(self, nombre):
        n = nombre.lower()
        if nombre in self.favoritos: 
            return "FAVORITOS"
        if any(x in n for x in ["expulsar", "pc", "test", "usb", "imports", "limpieza", "borrar", "temp", "cerrar", "organizador"]): 
            return "SISTEMA"
        if "pdf" in n: 
            return "PDF"
        if any(x in n for x in ["examenes", "notas"]): 
            return "CLASES"
        if any(x in n for x in ["horario", "diligencia", "certificados", "calculador", "diplomas"]): 
            return "ADMINISTRACIÓN"
        if any(x in n for x in ["bingo", "crono", "traductor", "pasapalabra", "picker", "clase", "qr", "juego"]): 
            return "AULA"
        return "OTROS"

    def actualizar_todo(self):
        self.actualizar_barra_estado()
        self.cargar_scripts()
        threading.Thread(target=self.comprobar_git_status, daemon=True).start()

    def toggle_carpeta(self, cat):
        self.estados_carpetas[cat] = not self.estados_carpetas[cat]
        self.cargar_scripts()

    def filtrar_scripts(self, e): self.cargar_scripts()

    def toggle_favorito(self, n):
        if n in self.favoritos: self.favoritos.remove(n)
        else: self.favoritos.append(n)
        guardar_favoritos(self.favoritos)
        self.cargar_scripts()

    def _on_mousewheel(self, event):
        self.canvas.yview_scroll(int(-1*(event.delta/120)), "units")

if __name__ == "__main__":
    root = tk.Tk()
    app = MenuFinalPerfecto(root)
    root.mainloop()