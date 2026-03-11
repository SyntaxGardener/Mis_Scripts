import os
import ast
import sys
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import subprocess

# --- 1. CONFIGURACIÓN ---
CARPETA_ACTUAL = os.path.dirname(os.path.abspath(__file__))

# Traductor para PIP (Lo que usas en el código -> Lo que pides en PIP)
MAPEO = {
    'pil': 'Pillow', 'fitz': 'pymupdf', 'docx': 'python-docx',
    'bs4': 'beautifulsoup4', 'pyperclip': 'pyperclip', 
    'sklearn': 'scikit-learn', 'yaml': 'pyyaml', 'cv2': 'opencv-python'
}

LIBRERIAS_ESTANDAR = [
    'os', 'sys', 'math', 'json', 'tkinter', 'ast', 'subprocess', 'tempfile',
    're', 'time', 'datetime', 'logging', 'email', 'collections', 'itertools',
    'asyncio', 'threading', 'ctypes', 'unicodedata', 'warnings', 'importlib', 'io'
]

# --- 2. MOTOR DE VERIFICACIÓN ---

def verificar_libreria(nombre):
    nombre = nombre.lower()
    if nombre in LIBRERIAS_ESTANDAR: return None
    
    # Caso especial PIL
    if nombre == 'pil':
        try:
            import PIL
            return True
        except ImportError: return False

    try:
        __import__(nombre)
        return True
    except ImportError: return False

# --- 3. ANÁLISIS Y REQUIREMENTS ---

base_datos = {}

def analizar_y_generar_requirements():
    base_datos.clear()
    todos_los_pips = set()
    archivos = [f for f in os.listdir(CARPETA_ACTUAL) if f.endswith(('.py', '.pyw'))]
    yo = os.path.basename(__file__)
    
    for arc in archivos:
        if arc == yo: continue
        try:
            with open(os.path.join(CARPETA_ACTUAL, arc), "r", encoding="utf-8") as f:
                tree = ast.parse(f.read())
            
            importados = set()
            for nodo in ast.walk(tree):
                mod = None
                if isinstance(nodo, ast.Import):
                    for n in nodo.names: mod = n.name.split('.')[0]
                elif isinstance(nodo, ast.ImportFrom):
                    if nodo.module: mod = nodo.module.split('.')[0]
                
                if mod and mod.lower() not in LIBRERIAS_ESTANDAR:
                    importados.add(mod)
            
            res = []
            for m in sorted(importados):
                estado = verificar_libreria(m)
                res.append({"nombre": m, "instalado": estado})
                # Añadir al set global de requirements usando el nombre de PIP
                todos_los_pips.add(MAPEO.get(m.lower(), m))
            
            if res: base_datos[arc] = res
        except: pass

    # Crear/Actualizar el archivo requirements.txt
    if todos_los_pips:
        with open(os.path.join(CARPETA_ACTUAL, "requirements.txt"), "w", encoding="utf-8") as req:
            req.write("\n".join(sorted(todos_los_pips)))

# --- 4. ACCIÓN DE INSTALACIÓN ---

def ejecutar_instalacion():
    faltantes = set()
    for lista in base_datos.values():
        for lib in lista:
            if not lib['instalado']:
                faltantes.add(MAPEO.get(lib['nombre'].lower(), lib['nombre']))
    
    # Opción de reparar pyperclip siempre a mano
    if messagebox.askyesno("Reparar", "¿Deseas forzar la instalación/reparación de pyperclip y faltantes?"):
        faltantes.add("pyperclip")
    elif not faltantes:
        return

    python_exe = sys.executable.replace("pythonw.exe", "python.exe")
    libs_str = " ".join(faltantes)
    comando = f'"{python_exe}" -m pip install --upgrade --force-reinstall {libs_str} & pause'
    
    try:
        subprocess.Popen(f'start "Instalador USB" cmd /k {comando}', shell=True)
    except Exception as e:
        messagebox.showerror("Error", str(e))

# --- 5. GUI CON POSICIONAMIENTO ---
root = tk.Tk()
root.title("Analizar imports para detectar librerías faltantes")

# Configuración de ventana (Centrada y a 50px del borde superior)
ancho_v = 800
alto_v = 600
ancho_pantalla = root.winfo_screenwidth()
# x = (ancho_pantalla // 2) - (ancho_v // 2) | y = 50
root.geometry(f"{ancho_v}x{alto_v}+{(ancho_pantalla // 2) - (ancho_v // 2)}+50")
root.configure(bg="#0f172a")

# Header y Botones
frame_top = tk.Frame(root, bg="#1e293b", pady=15)
frame_top.pack(fill="x")

tk.Button(frame_top, text="🚀 INSTALAR / REPARAR", command=ejecutar_instalacion, 
          bg="#10b981", fg="white", font=("Arial", 10, "bold"), padx=20).pack(side="left", padx=20)
tk.Button(frame_top, text="🔄 REFRESCAR Y REQS", command=lambda: [analizar_y_generar_requirements(), dibujar()], 
          bg="#3b82f6", fg="white", padx=20).pack(side="left")

caja = scrolledtext.ScrolledText(root, bg="#0f172a", fg="#94a3b8", font=("Consolas", 10), borderwidth=0)
caja.pack(fill="both", expand=True, padx=20, pady=20)

def dibujar():
    caja.config(state="normal")
    caja.delete("1.0", "end")
    caja.insert("end", "✅ El archivo 'requirements.txt' ha sido actualizado.\n\n", "info")
    for arc, libs in base_datos.items():
        caja.insert("end", f"📄 {arc}\n", "archivo")
        for l in libs:
            color = "ok" if l['instalado'] else "error"
            txt = "[OK]" if l['instalado'] else "[FALTA]"
            caja.insert("end", f"  {txt} {l['nombre']}\n", color)
        caja.insert("end", "\n")
    caja.config(state="disabled")

caja.tag_config("archivo", foreground="white", font=("Consolas", 10, "bold"))
caja.tag_config("ok", foreground="#4ade80")
caja.tag_config("error", foreground="#f87171", font=("Consolas", 10, "bold"))
caja.tag_config("info", foreground="#38bdf8", font=("Consolas", 9, "italic"))

analizar_y_generar_requirements()
dibujar()
root.mainloop()