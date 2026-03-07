import os
import ast
import sys
import importlib.util
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import subprocess

# --- 1. LIMPIEZA DE LOGS VIEJOS ---
ruta_log = os.path.join(os.path.dirname(os.path.abspath(__file__)), "error_log.txt")

if os.path.exists(ruta_log):
    try:
        os.remove(ruta_log)
    except:
        pass 

# --- 2. CONFIGURACIÓN DEL LOG (Solo si es .pyw) ---
if sys.executable.endswith("pythonw.exe"):
    try:
        sys.stderr = open(ruta_log, "w", encoding="utf-8")
    except:
        pass

# --- 3. VARIABLES DE ENTORNO ---
CARPETA_ACTUAL = os.path.dirname(os.path.abspath(__file__))
base_datos = {}

# --- 4. FUNCIONES DE ANÁLISIS ---

def verificar_estado_libreria(nombre_modulo):
    if nombre_modulo in sys.builtin_module_names:
        return None, "Estándar"
    try:
        spec = importlib.util.find_spec(nombre_modulo)
        if spec is None:
            return False, "No instalado"
        if spec.origin is None:
            return None, "Estándar"
        ruta = spec.origin.lower()
        if 'site-packages' in ruta or 'dist-packages' in ruta:
            return True, "Instalado"
        return None, "Estándar"
    except Exception:
        return False, "Error al verificar"

def analizar_archivo(ruta_archivo):
    try:
        with open(ruta_archivo, "r", encoding="utf-8") as f:
            arbol = ast.parse(f.read())
        resultado = []
        importados = set()
        for nodo in ast.walk(arbol):
            mod = None
            if isinstance(nodo, ast.Import):
                for n in nodo.names: mod = n.name.split('.')[0]
            elif isinstance(nodo, ast.ImportFrom):
                if nodo.module: mod = nodo.module.split('.')[0]
            if mod: importados.add(mod)
        for m in sorted(importados):
            es_pip, estado = verificar_estado_libreria(m)
            if es_pip is not None:
                resultado.append({"nombre": m, "instalado": es_pip})
        return resultado
    except:
        return []

def cargar_datos():
    """Escanea la carpeta y llena la base de datos"""
    base_datos.clear()
    for elemento in sorted(os.listdir(CARPETA_ACTUAL)):
        if elemento.endswith((".py", ".pyw")) and elemento != os.path.basename(__file__):
            info_pips = analizar_archivo(os.path.join(CARPETA_ACTUAL, elemento))
            if info_pips:
                base_datos[elemento] = info_pips

# --- 5. FUNCIONES DE BOTONES (ACCIONES) ---

def instalar_ahora():
    """Lanza la instalación en consola pequeña."""
    faltantes = set()
    for pips in base_datos.values():
        for p in pips:
            if not p['instalado']:
                faltantes.add(p['nombre'])
    
    if not faltantes:
        messagebox.showinfo("Limpio", "¡No hay nada que instalar!")
        return

    if not messagebox.askyesno("Confirmar", f"¿Instalar estas librerías?\n\n{', '.join(faltantes)}"):
        return

    python_exe = sys.executable.lower().replace("pythonw.exe", "python.exe")
    args_pip = [python_exe, "-m", "pip", "install"] + list(faltantes)
    
    comando_final = (
        f'title Instalador && mode con: cols=80 lines=20 && '
        f'echo Ejecutando instalacion... && '
    )
    
    try:
        subprocess.Popen(
            ["cmd", "/K", comando_final] + args_pip + ["&& exit"],
            creationflags=subprocess.CREATE_NEW_CONSOLE
        )
    except Exception as e:
        messagebox.showerror("Error", f"No se pudo ejecutar: {e}")

def limpiar_huerfanas():
    """Ventana de selección con barra de desplazamiento (Scrollbar)."""
    try:
        # 1. Análisis (Igual que antes)
        resultado = subprocess.check_output([sys.executable, "-m", "pip", "freeze"])
        instaladas = {line.split('==')[0].lower() for line in resultado.decode().splitlines()}
        
        mapeo_nombres = {
            'pil': 'pillow', 'docx': 'python-docx', 'win32com': 'pywin32',
            'pythoncom': 'pywin32', 'fitz': 'pymupdf', 'yt_dlp': 'yt-dlp',
            'speech_recognition': 'speechrecognition', 'deep_translator': 'deep-translator',
            'edge_tts': 'edge-tts', 'tkinterdnd2': 'tkinterdnd2', 'qrcode': 'qrcode',
            'pyinstaller': 'pyinstaller'
        }
        
        usadas = set()
        for pips in base_datos.values():
            for p in pips:
                usadas.add(mapeo_nombres.get(p['nombre'].lower(), p['nombre'].lower()))
        
        protegidas = {'pip', 'setuptools', 'wheel', 'tkinter', 'pypiwin32', 'altgraph', 'pefile', 'pywin32-ctypes'}
        sobran = sorted(list(instaladas - usadas - protegidas))
        
        if not sobran:
            messagebox.showinfo("Limpieza", "¡Entorno perfecto! No sobra nada.")
            return

        # --- 2. VENTANA EMERGENTE ---
        ventana_sel = tk.Toplevel(root)
        ventana_sel.title("Limpiar Librerías")
        ventana_sel.geometry("450x600")
        ventana_sel.configure(bg="#0f172a") # Fondo oscuro como el principal
        ventana_sel.grab_set()

        tk.Label(ventana_sel, text="SELECCIONA QUÉ DESINSTALAR", 
                 fg="#38bdf8", bg="#0f172a", font=("Segoe UI", 11, "bold")).pack(pady=15)

        # --- CONTENEDOR CON SCROLL ---
        container = tk.Frame(ventana_sel, bg="#0f172a")
        container.pack(fill="both", expand=True, padx=20)

        canvas = tk.Canvas(container, bg="#0f172a", highlightthickness=0)
        scrollbar = ttk.Scrollbar(container, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg="#0f172a")

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        # Diccionario para los Checks
        vars_seleccion = {}
        for lib in sobran:
            var = tk.BooleanVar()
            chk = tk.Checkbutton(scrollable_frame, text=lib, variable=var, 
                                 bg="#0f172a", fg="#94a3b8", selectcolor="#1e293b",
                                 activebackground="#1e293b", activeforeground="#38bdf8",
                                 font=("Consolas", 10), bd=0, padx=10, pady=2)
            chk.pack(anchor="w")
            vars_seleccion[lib] = var

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Función de borrado
        def ejecutar_borrado():
            a_borrar = [lib for lib, var in vars_seleccion.items() if var.get()]
            if not a_borrar:
                messagebox.showwarning("Vacío", "No has marcado ninguna librería.")
                return
            
            if messagebox.askyesno("Confirmar", f"¿Desinstalar {len(a_borrar)} librerías seleccionadas?"):
                python_exe = sys.executable.lower().replace("pythonw.exe", "python.exe")
                # Comando masivo
                comando_del = " && ".join([f'"{python_exe}" -m pip uninstall -y {lib}' for lib in a_borrar])
                
                comando_final = (
                    f'title Desinstalando... && mode con: cols=80 lines=20 && '
                    f'echo Eliminando seleccion... && {comando_del} && '
                    f'echo. && echo PROCESO COMPLETADO. && pause > nul'
                )
                
                subprocess.Popen(['cmd', '/C', comando_final], creationflags=subprocess.CREATE_NEW_CONSOLE)
                ventana_sel.destroy()

        # Botón de acción al pie
        btn_confirmar = tk.Button(ventana_sel, text="🚀 ELIMINAR SELECCIONADAS", command=ejecutar_borrado,
                                 bg="#ef4444", fg="white", font=("Segoe UI", 10, "bold"), 
                                 bd=0, pady=10, cursor="hand2")
        btn_confirmar.pack(fill="x", padx=20, pady=20)

    except Exception as e:
        messagebox.showerror("Error", f"Fallo al cargar lista: {e}")

# --- 6. INTERFAZ GRÁFICA (GUI) ---

root = tk.Tk()
root.title("Gestor de Dependencias PRO")
root.geometry("850x700")
root.configure(bg="#0f172a")

header = tk.Frame(root, bg="#1e293b", pady=20)
header.pack(fill="x")

tk.Label(header, text="📦 ESTADO DE DEPENDENCIAS EXTERNAS", 
         font=("Segoe UI", 14, "bold"), fg="#38bdf8", bg="#1e293b").pack()

busqueda_var = tk.StringVar()
entrada = tk.Entry(header, textvariable=busqueda_var, font=("Consolas", 12), 
                  bg="#0f172a", fg="white", width=50, bd=0)
entrada.pack(pady=10)
entrada.insert(0, "Filtrar por librería o script...")

frame_botones = tk.Frame(header, bg="#1e293b")
frame_botones.pack(pady=5)

# Botón 1: Instalar
btn_instalar = tk.Button(frame_botones, text="🚀 INSTALAR", command=instalar_ahora,
                        bg="#3b82f6", fg="white", font=("Segoe UI", 9, "bold"), bd=0, padx=15, pady=8)
btn_instalar.pack(side="left", padx=5)

# Botón 2: Refrescar
def accion_refrescar():
    cargar_datos()
    filtrar()

btn_refrescar = tk.Button(frame_botones, text="🔄 REFRESCAR", command=accion_refrescar,
                         bg="#64748b", fg="white", font=("Segoe UI", 9, "bold"), bd=0, padx=15, pady=8)
btn_refrescar.pack(side="left", padx=5)

# Botón 3: Limpiar (El nuevo)
btn_limpiar = tk.Button(frame_botones, text="🧹 LIMPIAR NO USADAS", command=limpiar_huerfanas,
                        bg="#ef4444", fg="white", font=("Segoe UI", 9, "bold"), bd=0, padx=15, pady=8)
btn_limpiar.pack(side="left", padx=5)

caja = scrolledtext.ScrolledText(root, bg="#0f172a", fg="#94a3b8", font=("Consolas", 11), borderwidth=0, padx=20)
caja.pack(fill="both", expand=True, pady=10)

def filtrar(*args):
    caja.config(state="normal")
    caja.delete("1.0", "end")
    termino = busqueda_var.get().lower()
    if termino == "filtrar por librería o script...": termino = ""

    for archivo, pips in base_datos.items():
        if not termino or termino in archivo.lower() or any(termino in p['nombre'].lower() for p in pips):
            caja.insert("end", f"📄 {archivo}\n", "archivo_titulo")
            for p in pips:
                tag = "ok" if p['instalado'] else "missing"
                txt = "[INSTALADO]" if p['instalado'] else "[⚠️ NO INSTALADO]"
                caja.insert("end", f"   • {p['nombre']:20}", "pip_nombre")
                caja.insert("end", f" {txt}\n", tag)
            caja.insert("end", "\n")
    caja.config(state="disabled")

# Estilos de texto
caja.tag_config("archivo_titulo", foreground="#f8fafc", font=("Consolas", 11, "bold"))
caja.tag_config("pip_nombre", foreground="#94a3b8")
caja.tag_config("ok", foreground="#4ade80")
caja.tag_config("missing", foreground="#f87171", font=("Consolas", 11, "bold"))

busqueda_var.trace_add("write", filtrar)
entrada.bind("<FocusIn>", lambda e: entrada.delete(0, 'end'))

cargar_datos()
filtrar()
root.mainloop()