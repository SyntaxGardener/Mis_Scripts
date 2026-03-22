import os
import ast
import sys
import importlib
import importlib.util
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import subprocess

# --- 1. DETECCIÓN DE RUTAS ---
CARPETA_SCRIPTS = os.path.dirname(os.path.abspath(__file__))
RAIZ_PORTABLE   = os.path.dirname(CARPETA_SCRIPTS)

# Diccionario de traducción: 'nombre_en_codigo_lowercase': 'nombre_en_pip'
MAPEO = {
    'pil':                      'Pillow',
    'fitz':                     'pymupdf',
    'docx':                     'python-docx',
    'bs4':                      'beautifulsoup4',
    'pyperclip':                'pyperclip',
    'docx2txt':                 'docx2txt',
    'cv2':                      'opencv-python',
    'yaml':                     'pyyaml',
    'speech_recognition':       'SpeechRecognition',
    'edge_tts':                 'edge-tts',
    'crypto':                   'pycryptodome',
    'cryptodome':               'pycryptodome',
    'image':                    'Pillow',
    'mysqldb':                  'mysqlclient',
    'opengl':                   'PyOpenGL',
    'openssl':                  'pyOpenSSL',
    'pil.imageqt':              'Pillow',
    'xlib':                     'python-xlib',
    '_cffi_backend':            'cffi',
    'allauth':                  'django-allauth',
    'apt':                      'python-apt',
    'attr':                     'attrs',
    'cairo':                    'pycairo',
    'corsheaders':              'django-cors-headers',
    'crispy_forms':             'django-crispy-forms',
    'dateutil':                 'python-dateutil',
    'debug_toolbar':            'django-debug-toolbar',
    'django_filters':           'django-filter',
    'dns':                      'dnspython',
    'dotenv':                   'python-dotenv',
    'email_validator':          'email-validator',
    'engineio':                 'python-engineio',
    'flask_login':              'Flask-Login',
    'flask_migrate':            'Flask-Migrate',
    'flask_restful':            'Flask-RESTful',
    'flask_wtf':                'Flask-WTF',
    'gi':                       'PyGObject',
    'google.cloud':             'google-cloud',
    'googleapiclient':          'google-api-python-client',
    'import_export':            'django-import-export',
    'jwt':                      'PyJWT',
    'kafka':                    'kafka-python',
    'matplotlib.pyplot':        'matplotlib',
    'mpl_toolkits':             'matplotlib',
    'multipart':                'python-multipart',
    'nacl':                     'pynacl',
    'pkg_resources':            'setuptools',
    'pptx':                     'python-pptx',
    'psycopg2':                 'psycopg2-binary',
    'rest_framework':           'djangorestframework',
    'serial':                   'pyserial',
    'skimage':                  'scikit-image',
    'sklearn':                  'scikit-learn',
    'slugify':                  'python-slugify',
    'socketio':                 'python-socketio',
    'storages':                 'django-storages',
    'tkinter':                  'tk',
    'websocket':                'websocket-client',
    'win32api':                 'pywin32',
    'win32com':                 'pywin32',
    'zmq':                      'pyzmq',
}

LIBRERIAS_ESTANDAR = {
    'os', 'sys', 'math', 'json', 'tkinter', 'ast', 'subprocess', 'tempfile',
    're', 'time', 'datetime', 'logging', 'email', 'collections', 'itertools',
    'asyncio', 'threading', 'ctypes', 'unicodedata', 'warnings', 'importlib',
    'io', 'pathlib', 'shutil', 'glob', 'struct', 'hashlib', 'hmac', 'base64',
    'urllib', 'http', 'socket', 'ssl', 'xml', 'html', 'csv', 'sqlite3',
    'configparser', 'argparse', 'copy', 'functools', 'operator', 'string',
    'textwrap', 'enum', 'dataclasses', 'abc', 'typing', 'types', 'gc',
    'inspect', 'traceback', 'queue', 'multiprocessing', 'concurrent', 'signal',
    'platform', 'stat', 'fnmatch', 'zipfile', 'tarfile', 'gzip', 'bz2', 'lzma',
    'pickle', 'shelve', 'pprint', 'decimal', 'fractions', 'random', 'statistics',
    'uuid', 'calendar', 'locale', 'gettext', 'codecs', 'binascii', 'array',
    'weakref', 'contextlib', 'atexit', 'builtins', 'site', 'token', 'tokenize',
}

base_datos = {}

# --- 2. MOTOR DE BÚSQUEDA ---

def analizar_y_generar():
    base_datos.clear()
    importlib.invalidate_caches()

    try:
        archivos = [f for f in os.listdir(CARPETA_SCRIPTS) if f.lower().endswith(('.py', '.pyw'))]
    except Exception as e:
        messagebox.showerror("Error", f"No se pudo leer la carpeta: {e}")
        return

    mi_nombre = os.path.basename(__file__)

    for arc in archivos:
        if arc == mi_nombre:
            continue
        ruta_completa = os.path.join(CARPETA_SCRIPTS, arc)

        try:
            with open(ruta_completa, "r", encoding="utf-8", errors="ignore") as f:
                tree = ast.parse(f.read())

            importados = set()
            for nodo in ast.walk(tree):
                mod = None
                if isinstance(nodo, ast.Import):
                    for n in nodo.names:
                        mod = n.name.split('.')[0]
                elif isinstance(nodo, ast.ImportFrom) and nodo.module:
                    mod = nodo.module.split('.')[0]

                if mod and mod.lower() not in LIBRERIAS_ESTANDAR:
                    importados.add(mod)

            if importados:
                res = []
                for m in sorted(importados):
                    try:
                        spec = importlib.util.find_spec(m) or importlib.util.find_spec(m.lower())
                        instalado = spec is not None
                    except Exception:
                        instalado = False
                    res.append({"nombre": m, "instalado": instalado})
                base_datos[arc] = res
        except Exception:
            pass

# --- 3. ACCIONES ---

def instalar():
    faltantes = {
        MAPEO.get(l['nombre'].lower(), l['nombre'])
        for lista in base_datos.values()
        for l in lista
        if not l['instalado']
    }

    if not faltantes:
        messagebox.showinfo("Todo OK", "Todas las librerías están instaladas. ✅")
        return

    py_exe  = sys.executable.lower().replace("pythonw.exe", "python.exe")
    libs    = " ".join(sorted(faltantes))
    cmd_pip = f'"{py_exe}" -m pip install {libs}'

    try:
        subprocess.Popen(
            f'start "Instalador" cmd /k "{cmd_pip} & pause"',
            shell=True, creationflags=0x08000000
        )
    except Exception as e:
        messagebox.showerror("Error", f"No se pudo iniciar: {e}")


def get_git_info(target, git_exe):
    """Recoge info del estado del repo: tamaño, objetos sueltos, rama."""
    info = {}
    try:
        # Tamaño total de la carpeta .git
        git_dir = os.path.join(target, ".git")
        total = sum(
            os.path.getsize(os.path.join(dp, f))
            for dp, _, files in os.walk(git_dir)
            for f in files
        )
        info['tamaño'] = f"{total / 1024 / 1024:.1f} MB"
    except Exception:
        info['tamaño'] = "desconocido"

    try:
        r = subprocess.run(
            f'{git_exe} -C "{target}" count-objects -v',
            shell=True, capture_output=True, text=True
        )
        for line in r.stdout.splitlines():
            if line.startswith("count:"):
                info['objetos_sueltos'] = line.split(":")[1].strip()
            if line.startswith("size:"):
                info['tamaño_sueltos'] = f"{int(line.split(':')[1].strip())} KB"
    except Exception:
        info['objetos_sueltos'] = "?"

    try:
        r = subprocess.run(
            f'{git_exe} -C "{target}" rev-parse --abbrev-ref HEAD',
            shell=True, capture_output=True, text=True
        )
        info['rama'] = r.stdout.strip() or "?"
    except Exception:
        info['rama'] = "?"

    return info


def limpiar_pycache(carpeta):
    """Elimina __pycache__ y archivos .pyc recursivamente."""
    eliminados_dirs  = 0
    eliminados_files = 0
    bytes_liberados  = 0

    for dp, dirs, files in os.walk(carpeta):
        # Eliminar archivos .pyc
        for f in files:
            if f.endswith('.pyc'):
                ruta = os.path.join(dp, f)
                try:
                    bytes_liberados += os.path.getsize(ruta)
                    os.remove(ruta)
                    eliminados_files += 1
                except Exception:
                    pass
        # Marcar __pycache__ para eliminar
        for d in dirs[:]:
            if d == '__pycache__':
                ruta = os.path.join(dp, d)
                try:
                    for root2, _, files2 in os.walk(ruta):
                        for f2 in files2:
                            bytes_liberados += os.path.getsize(os.path.join(root2, f2))
                    import shutil
                    shutil.rmtree(ruta)
                    eliminados_dirs += 1
                    dirs.remove(d)
                except Exception:
                    pass

    return eliminados_dirs, eliminados_files, bytes_liberados


def reparar_git():
    target   = CARPETA_SCRIPTS if os.path.exists(os.path.join(CARPETA_SCRIPTS, ".git")) else RAIZ_PORTABLE
    git_path = os.path.join(RAIZ_PORTABLE, "PortableGit", "bin", "git.exe")
    git_exe  = f'"{git_path}"' if os.path.exists(git_path) else "git"

    # --- Ventana de mantenimiento ---
    win = tk.Toplevel(root)
    win.title("🛠️ Mantenimiento del Repositorio")
    win.geometry("600x480")
    win.configure(bg="#0f172a")
    win.grab_set()

    tk.Label(win, text="🛠️  MANTENIMIENTO DEL REPOSITORIO",
             bg="#0f172a", fg="white", font=("Consolas", 11, "bold")).pack(pady=(15, 5))
    tk.Label(win, text=target, bg="#0f172a", fg="#64748b", font=("Consolas", 9)).pack()

    txt = scrolledtext.ScrolledText(win, bg="#1e293b", fg="#94a3b8",
                                     font=("Consolas", 9), borderwidth=0, height=18)
    txt.pack(fill="both", expand=True, padx=15, pady=10)
    txt.tag_config("ok",      foreground="#4ade80")
    txt.tag_config("warn",    foreground="#fbbf24")
    txt.tag_config("err",     foreground="#f87171")
    txt.tag_config("title",   foreground="white", font=("Consolas", 9, "bold"))
    txt.tag_config("info",    foreground="#94a3b8")

    def log(msg, tag="info"):
        txt.config(state="normal")
        txt.insert("end", msg + "\n", tag)
        txt.see("end")
        txt.config(state="disabled")
        win.update()

    # Mostrar estado actual del repo
    log("── Estado actual del repositorio ──────────────────", "title")
    info = get_git_info(target, git_exe)
    log(f"  Rama activa       : {info.get('rama', '?')}")
    log(f"  Tamaño carpeta .git: {info.get('tamaño', '?')}")
    log(f"  Objetos sueltos   : {info.get('objetos_sueltos', '?')} ({info.get('tamaño_sueltos', '?')})")

    frame_btns = tk.Frame(win, bg="#0f172a")
    frame_btns.pack(pady=8)

    def hacer_gc():
        btn_gc.config(state="disabled")
        btn_pyc.config(state="disabled")
        log("\n── Limpieza Git (gc --aggressive) ─────────────────", "title")
        log("  Ejecutando... (puede tardar)", "warn")
        win.update()
        try:
            git_cmd = git_exe if git_exe == "git" else git_exe
            r = subprocess.run(
                f'{git_cmd} -C "{target}" gc --prune=now --aggressive',
                shell=True, capture_output=True, text=True
            )
            if r.returncode == 0:
                log("  Git gc completado correctamente.", "ok")
                # Mostrar estado después
                info2 = get_git_info(target, git_exe)
                log(f"  Tamaño .git ahora  : {info2.get('tamaño', '?')}", "ok")
                log(f"  Objetos sueltos    : {info2.get('objetos_sueltos', '?')}", "ok")
            else:
                log(f"  Error: {r.stderr.strip()}", "err")
        except Exception as e:
            log(f"  Excepción: {e}", "err")
        btn_gc.config(state="normal")
        btn_pyc.config(state="normal")

    def hacer_pyc():
        btn_gc.config(state="disabled")
        btn_pyc.config(state="disabled")
        log("\n── Limpieza __pycache__ y .pyc ────────────────────", "title")
        log(f"  Escaneando: {RAIZ_PORTABLE}", "info")
        win.update()
        dirs, files, nb = limpiar_pycache(RAIZ_PORTABLE)
        kb = nb / 1024
        if dirs + files == 0:
            log("  No se encontró nada que limpiar.", "warn")
        else:
            log(f"  {dirs} carpetas __pycache__ eliminadas", "ok")
            log(f"  {files} archivos .pyc eliminados", "ok")
            log(f"  Espacio liberado: {kb:.1f} KB", "ok")
        btn_gc.config(state="normal")
        btn_pyc.config(state="normal")

    btn_gc = tk.Button(frame_btns, text="🧹 Limpiar Git (gc)",
                       command=hacer_gc, bg="#f59e0b", fg="black",
                       font=("Arial", 9, "bold"), width=22)
    btn_gc.pack(side="left", padx=8)

    btn_pyc = tk.Button(frame_btns, text="🗑️ Limpiar __pycache__",
                        command=hacer_pyc, bg="#6366f1", fg="white",
                        font=("Arial", 9, "bold"), width=22)
    btn_pyc.pack(side="left", padx=8)

    tk.Button(frame_btns, text="Cerrar", command=win.destroy,
              bg="#334155", fg="white", width=10).pack(side="left", padx=8)


# --- 4. GUI PRINCIPAL ---
root = tk.Tk()
root.title("ANALIZADOR DE IMPORTS PORTABLE")
root.geometry(f"800x600+{(root.winfo_screenwidth()//2)-400}+20")
root.configure(bg="#0f172a")

frame_top = tk.Frame(root, bg="#1e293b", pady=10)
frame_top.pack(fill="x")

tk.Button(frame_top, text="🚀 INSTALAR FALTANTES",
          command=lambda: [instalar(), analizar_y_generar(), dibujar()],
          bg="#10b981", fg="white", font=("Arial", 9, "bold")).pack(side="left", padx=10)

tk.Button(frame_top, text="🔄 REFRESCAR",
          command=lambda: [analizar_y_generar(), dibujar()],
          bg="#3b82f6", fg="white").pack(side="left", padx=5)

tk.Button(frame_top, text="🛠️ REPAIR REPOSITORY",
          command=reparar_git,
          bg="#f59e0b", fg="black", font=("Arial", 9, "bold")).pack(side="right", padx=10)

frame_status = tk.Frame(root, bg="#1e293b", pady=4)
frame_status.pack(fill="x")
lbl_status = tk.Label(frame_status, text="", bg="#1e293b", fg="#94a3b8", font=("Consolas", 9))
lbl_status.pack(side="left", padx=15)

caja = scrolledtext.ScrolledText(root, bg="#0f172a", fg="#94a3b8",
                                  font=("Consolas", 10), borderwidth=0)
caja.pack(fill="both", expand=True, padx=20, pady=(5, 20))

def dibujar():
    caja.config(state="normal")
    caja.delete("1.0", "end")
    caja.insert("end", f"📍 Carpeta: {CARPETA_SCRIPTS}\n\n", "info")

    if not base_datos:
        caja.insert("end", "⚠️  No se encontraron archivos .py en esta carpeta.\n", "err")
        lbl_status.config(text="")
    else:
        total_scripts   = len(base_datos)
        total_libs      = sum(len(v) for v in base_datos.values())
        total_faltantes = sum(1 for v in base_datos.values() for l in v if not l['instalado'])
        total_ok        = total_libs - total_faltantes

        for arc, libs in base_datos.items():
            n_ok    = sum(1 for l in libs if l['instalado'])
            n_falta = len(libs) - n_ok
            resumen = f"  ({n_ok} OK" + (f", {n_falta} FALTAN" if n_falta else "") + ")"
            caja.insert("end", f"📄 {arc}{resumen}\n", "h")
            for l in libs:
                etiqueta = "[OK]    " if l['instalado'] else "[FALTA] "
                pip_name = MAPEO.get(l['nombre'].lower(), l['nombre'])
                pip_info = f"  → pip: {pip_name}" if pip_name.lower() != l['nombre'].lower() else ""
                caja.insert("end", f"  {etiqueta} {l['nombre']}{pip_info}\n",
                            "ok" if l['instalado'] else "err")
            caja.insert("end", "\n")

        estado = (f"📊  {total_scripts} scripts  |  "
                  f"✅ {total_ok} instaladas  |  "
                  f"❌ {total_faltantes} faltantes")
        lbl_status.config(text=estado, fg="#f87171" if total_faltantes else "#4ade80")

    caja.config(state="disabled")

caja.tag_config("h",    foreground="white",   font=("Consolas", 10, "bold"))
caja.tag_config("ok",   foreground="#4ade80")
caja.tag_config("err",  foreground="#f87171")
caja.tag_config("info", foreground="#64748b")

analizar_y_generar()
dibujar()
root.mainloop()
