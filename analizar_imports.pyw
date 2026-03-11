import os
import ast
import sys
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import subprocess

# --- 1. CONFIGURACIÓN ---
CARPETA_ACTUAL = os.path.dirname(os.path.abspath(__file__))

MAPEO = {
    'pil': 'Pillow', 'fitz': 'pymupdf', 'docx': 'python-docx',
    'bs4': 'beautifulsoup4', 'pyperclip': 'pyperclip', 'docx2txt': 'docx2txt'
}

LIBRERIAS_ESTANDAR = [
    'os', 'sys', 'math', 'json', 'tkinter', 'ast', 'subprocess', 'tempfile',
    're', 'time', 'datetime', 'logging', 'email', 'collections', 'itertools',
    'asyncio', 'threading', 'ctypes', 'unicodedata', 'warnings', 'importlib', 'io'
]

# --- 2. MOTOR ---
def verificar_libreria(nombre):
    nombre = nombre.lower()
    if nombre in LIBRERIAS_ESTANDAR: return None
    try:
        __import__(nombre)
        return True
    except: return False

def analizar_y_generar():
    base_datos.clear()
    todos_pips = set()
    archivos = [f for f in os.listdir(CARPETA_ACTUAL) if f.endswith(('.py', '.pyw'))]
    for arc in archivos:
        if arc == os.path.basename(__file__): continue
        try:
            with open(os.path.join(CARPETA_ACTUAL, arc), "r", encoding="utf-8") as f:
                tree = ast.parse(f.read())
            importados = {n.name.split('.')[0] for n in ast.walk(tree) if isinstance(n, ast.Import)}
            for n in ast.walk(tree):
                if isinstance(n, ast.ImportFrom) and n.module: importados.add(n.module.split('.')[0])
            
            res = []
            for m in sorted(importados):
                est = verificar_libreria(m)
                if est is not None:
                    res.append({"nombre": m, "instalado": est})
                    todos_pips.add(MAPEO.get(m.lower(), m))
            if res: base_datos[arc] = res
        except: pass
    
    with open(os.path.join(CARPETA_ACTUAL, "requirements.txt"), "w") as f:
        f.write("\n".join(sorted(todos_pips)))

# --- 3. ACCIONES ---
def instalar():
    faltantes = {MAPEO.get(l['nombre'].lower(), l['nombre']) for lista in base_datos.values() for l in lista if not l['instalado']}
    
    if not faltantes:
        if not messagebox.askyesno("Todo OK", "No faltan librerías. ¿Deseas forzar reinstalación de pyperclip?"):
            return
        faltantes.add("pyperclip")

    py_exe = sys.executable.replace("pythonw.exe", "python.exe")
    cmd = f'"{py_exe}" -m pip install --upgrade {" ".join(faltantes)} & pause'
    subprocess.Popen(f'start "Instalador USB" cmd /k {cmd}', shell=True)

def reparar_git():
    """Lógica para reparar errores comunes de Git en el repositorio"""
    if not os.path.exists(os.path.join(CARPETA_ACTUAL, ".git")):
        messagebox.showerror("Error", "No se detectó un repositorio Git en esta carpeta.")
        return
    
    # Comandos de reparación: limpieza de índice y chequeo de objetos
    comando = 'git gc --prune=now --aggressive & git fsck & pause'
    subprocess.Popen(f'start "Repair Git" cmd /k {comando}', shell=True)

# --- 4. GUI ---
base_datos = {}
root = tk.Tk()
root.title("Analizador de Imports")
root.geometry(f"800x600+{(root.winfo_screenwidth()//2)-400}+50")
root.configure(bg="#0f172a")

frame_top = tk.Frame(root, bg="#1e293b", pady=10)
frame_top.pack(fill="x")

tk.Button(frame_top, text="🚀 INSTALAR", command=instalar, bg="#10b981", fg="white", font=("Arial", 9, "bold")).pack(side="left", padx=10)
tk.Button(frame_top, text="🔄 REFRESCAR", command=lambda: [analizar_y_generar(), dibujar()], bg="#3b82f6", fg="white").pack(side="left", padx=5)
tk.Button(frame_top, text="🛠️ REPAIR REPOSITORY", command=reparar_git, bg="#f59e0b", fg="black", font=("Arial", 9, "bold")).pack(side="right", padx=10)

caja = scrolledtext.ScrolledText(root, bg="#0f172a", fg="#94a3b8", font=("Consolas", 10))
caja.pack(fill="both", expand=True, padx=20, pady=20)

def dibujar():
    caja.config(state="normal"); caja.delete("1.0", "end")
    for arc, libs in base_datos.items():
        caja.insert("end", f"📄 {arc}\n", "h")
        for l in libs:
            caja.insert("end", f"  {'[OK]' if l['instalado'] else '[FALTA]'} {l['nombre']}\n", "ok" if l['instalado'] else "err")
    caja.config(state="disabled")

caja.tag_config("h", foreground="white", font=("Consolas", 10, "bold"))
caja.tag_config("ok", foreground="#4ade80")
caja.tag_config("err", foreground="#f87171")

analizar_y_generar(); dibujar()
root.mainloop()