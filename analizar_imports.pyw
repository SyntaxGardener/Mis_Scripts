import os
import ast
import sys
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import subprocess

# --- 1. DETECCIÓN DE RUTAS (ESTRUCTURA TRABAJO_PORTABLE) ---
# Forzamos que busque en la carpeta real del archivo
CARPETA_SCRIPTS = os.path.dirname(os.path.abspath(__file__))
# Subimos un nivel para llegar a la raíz donde está PortableGit
RAIZ_PORTABLE = os.path.dirname(CARPETA_SCRIPTS)

MAPEO = {
    'pil': 'Pillow', 'fitz': 'pymupdf', 'docx': 'python-docx',
    'bs4': 'beautifulsoup4', 'pyperclip': 'pyperclip', 'docx2txt': 'docx2txt',
    'cv2': 'opencv-python', 'yaml': 'pyyaml'
}

LIBRERIAS_ESTANDAR = [
    'os', 'sys', 'math', 'json', 'tkinter', 'ast', 'subprocess', 'tempfile',
    're', 'time', 'datetime', 'logging', 'email', 'collections', 'itertools',
    'asyncio', 'threading', 'ctypes', 'unicodedata', 'warnings', 'importlib', 'io'
]

# --- 2. MOTOR DE BÚSQUEDA ---
base_datos = {}

def analizar_y_generar():
    base_datos.clear()
    todos_pips = set()
    
    try:
        # Listamos solo archivos .py o .pyw en Mis_Scripts
        archivos = [f for f in os.listdir(CARPETA_SCRIPTS) if f.lower().endswith(('.py', '.pyw'))]
    except Exception as e:
        messagebox.showerror("Error", f"No se pudo leer la carpeta: {e}")
        return

    mi_nombre = os.path.basename(__file__)
    
    for arc in archivos:
        if arc == mi_nombre: continue
        ruta_completa = os.path.join(CARPETA_SCRIPTS, arc)
        
        try:
            with open(ruta_completa, "r", encoding="utf-8", errors="ignore") as f:
                tree = ast.parse(f.read())
            
            importados = set()
            for nodo in ast.walk(tree):
                mod = None
                if isinstance(nodo, ast.Import):
                    for n in nodo.names: mod = n.name.split('.')[0]
                elif isinstance(nodo, ast.ImportFrom) and nodo.module:
                    mod = nodo.module.split('.')[0]
                
                if mod and mod.lower() not in LIBRERIAS_ESTANDAR:
                    importados.add(mod)
            
            if importados:
                res = []
                for m in sorted(importados):
                    # Chequeo de PIL y otros (insensible a mayúsculas)
                    try:
                        __import__(m.lower())
                        est = True
                    except:
                        try:
                            __import__(m)
                            est = True
                        except:
                            est = False
                    
                    res.append({"nombre": m, "instalado": est})
                    todos_pips.add(MAPEO.get(m.lower(), m))
                base_datos[arc] = res
        except: pass

    # Generar requirements.txt
    try:
        with open(os.path.join(CARPETA_SCRIPTS, "requirements.txt"), "w", encoding="utf-8") as f:
            f.write("\n".join(sorted(todos_pips)))
    except: pass

# --- 3. ACCIONES ---
def instalar():
    faltantes = {MAPEO.get(l['nombre'].lower(), l['nombre']) for lista in base_datos.values() for l in lista if not l['instalado']}
    
    if not faltantes:
        if not messagebox.askyesno("Todo OK", "No faltan librerías. ¿Forzar reparación de pyperclip?"):
            return
        faltantes.add("pyperclip")

    py_exe = sys.executable.replace("pythonw.exe", "python.exe")
    cmd = f'"{py_exe}" -m pip install --upgrade {" ".join(faltantes)} & pause'
    subprocess.Popen(f'start "Instalador USB" cmd /k {cmd}', shell=True)

def reparar_git():
    # Comprobar si hay repo en Mis_Scripts o en la Raíz
    target = CARPETA_SCRIPTS if os.path.exists(os.path.join(CARPETA_SCRIPTS, ".git")) else RAIZ_PORTABLE
    
    if not os.path.exists(os.path.join(target, ".git")):
        messagebox.showwarning("Git", "No se encontró la carpeta .git para reparar.")
        return

    # Ruta al Git Portable (según tu captura TRABAJO_PORTABLE/PortableGit)
    git_path = os.path.join(RAIZ_PORTABLE, "PortableGit", "bin", "git.exe")
    git_exe = f'"{git_path}"' if os.path.exists(git_path) else "git"

    comando = f'cd /d "{target}" && {git_exe} gc --prune=now --aggressive && {git_exe} fsck && pause'
    subprocess.Popen(f'start "Repair Git" cmd /k {comando}', shell=True)

# --- 4. GUI ---
root = tk.Tk()
root.title("ANALIZADOR DE IMPORTS")
# --- Configuración de dimensiones ---
ancho_ventana = 800
alto_ventana = 600
distancia_superior = 20
        
# Obtener dimensiones y calcular centro
ancho_pantalla = root.winfo_screenwidth()
posicion_x = (ancho_pantalla // 2) - (ancho_ventana // 2)
        
# Aplicar geometría corregida
root.geometry(f"{ancho_ventana}x{alto_ventana}+{posicion_x}+{distancia_superior}")
root.configure(bg="#0f172a")

frame_top = tk.Frame(root, bg="#1e293b", pady=10)
frame_top.pack(fill="x")

tk.Button(frame_top, text="🚀 INSTALAR", command=lambda: [instalar(), analizar_y_generar(), dibujar()], bg="#10b981", fg="white", font=("Arial", 9, "bold")).pack(side="left", padx=10)
tk.Button(frame_top, text="🔄 REFRESCAR", command=lambda: [analizar_y_generar(), dibujar()], bg="#3b82f6", fg="white").pack(side="left", padx=5)
tk.Button(frame_top, text="🛠️ REPAIR REPOSITORY", command=reparar_git, bg="#f59e0b", fg="black", font=("Arial", 9, "bold")).pack(side="right", padx=10)

caja = scrolledtext.ScrolledText(root, bg="#0f172a", fg="#94a3b8", font=("Consolas", 10), borderwidth=0)
caja.pack(fill="both", expand=True, padx=20, pady=20)

def dibujar():
    caja.config(state="normal")
    caja.delete("1.0", "end")
    caja.insert("end", f"📍 Carpeta: {CARPETA_SCRIPTS}\n\n", "info")
    
    if not base_datos:
        caja.insert("end", "⚠️ No se ven archivos .py aquí. Asegúrate de que el script esté dentro de la carpeta Mis_Scripts.", "err")
    else:
        for arc, libs in base_datos.items():
            caja.insert("end", f"📄 {arc}\n", "h")
            for l in libs:
                caja.insert("end", f"  {'[OK]' if l['instalado'] else '[FALTA]'} {l['nombre']}\n", "ok" if l['instalado'] else "err")
    caja.config(state="disabled")

caja.tag_config("h", foreground="white", font=("Consolas", 10, "bold"))
caja.tag_config("ok", foreground="#4ade80")
caja.tag_config("err", foreground="#f87171")
caja.tag_config("info", foreground="#64748b")

analizar_y_generar()
dibujar()
root.mainloop()