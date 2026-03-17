import os, sys, ctypes, ctypes.wintypes, winreg, json, threading, subprocess, shutil
import urllib.request, urllib.parse
import tkinter as tk
from tkinter import ttk, messagebox

# SHQUERYRBINFO struct para medir la papelera
class SHQUERYRBINFO(ctypes.Structure):
    _fields_ = [("cbSize", ctypes.c_ulong),
                ("i64Size", ctypes.c_longlong),
                ("i64NumItems", ctypes.c_longlong)]


# ── Elevación UAC ─────────────────────────────────────────────
def es_admin():
    try: return ctypes.windll.shell32.IsUserAnAdmin()
    except: return False

def pedir_elevacion():
    if not es_admin():
        script = os.path.abspath(__file__)
        # Usar pythonw.exe para no abrir consola negra
        ejecutable = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
        if not os.path.exists(ejecutable):
            ejecutable = sys.executable
        ret = ctypes.windll.shell32.ShellExecuteW(None, "runas", ejecutable, f'"{script}"', None, 1)
        if ret <= 32:
            # UAC rechazado o bloqueado — avisar al usuario
            import tkinter as _tk
            from tkinter import messagebox as _mb
            _r = _tk.Tk(); _r.withdraw()
            _mb.showerror("Sin permisos de administrador",
                "No se pudieron obtener permisos de administrador.\n\n"
                "Ejecuta el script con clic derecho → 'Ejecutar como administrador'.")
            _r.destroy()
        sys.exit()

# ── Registro ──────────────────────────────────────────────────
CLAVES = [
    (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
    (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"),
    (winreg.HKEY_CURRENT_USER,  r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
]
PALABRAS_RIESGO = {"microsoft","windows","visual c++","net framework",".net",
                   "directx","redistributable","driver","intel","amd",
                   "nvidia","realtek","update","runtime"}

def val(clave, nombre):
    try: return winreg.QueryValueEx(clave, nombre)[0]
    except: return ""

import re as _re

# Ejecutables del sistema que siempre existen y no indican instalación real
_SISTEMA = {"msiexec.exe", "rundll32.exe", "regsvr32.exe", "cmd.exe",
            "powershell.exe", "wscript.exe", "cscript.exe"}

def extraer_exe(cadena):
    """Devuelve la ruta del .exe principal, o '' si apunta a un ejecutable del sistema."""
    if not cadena:
        return ""
    cadena = os.path.expandvars(cadena.strip())
    if cadena.startswith('"'):
        partes = cadena.split('"')
        cadena = partes[1] if len(partes) >= 2 else cadena.strip('"')
    # Extraer hasta el .exe
    m = _re.match(r"(?i)(.*?\.exe)", cadena)
    ruta = m.group(1).strip() if m else cadena.strip()
    # Si apunta a un exe del sistema, no sirve como referencia
    if os.path.basename(ruta).lower() in _SISTEMA:
        return ""
    return ruta

def carpeta_instalacion(inst, uni, icono):
    """Devuelve la mejor ruta para comprobar si el programa sigue instalado."""
    # 1. InstallLocation: es directamente la carpeta
    if inst:
        ruta = os.path.normpath(os.path.expandvars(inst.strip().strip('"')))
        if ruta and ruta != ".":
            return "carpeta", ruta
    # 2. UninstallString: extraer el exe y usar su carpeta
    exe = extraer_exe(uni)
    if exe:
        return "exe", os.path.normpath(exe)
    # 3. DisplayIcon: igual
    exe = extraer_exe(icono)
    if exe:
        return "exe", os.path.normpath(exe)
    return None, None

def esta_instalado(inst, uni, icono):
    tipo, ruta = carpeta_instalacion(inst, uni, icono)
    if tipo is None:
        return True   # Sin referencia fiable → no mostrar
    if tipo == "carpeta":
        return os.path.exists(ruta)
    if tipo == "exe":
        # Solo marcar como huérfano si el .exe concreto no existe
        return os.path.exists(ruta)
    return True

def es_riesgosa(nombre):
    n = nombre.lower()
    return any(p in n for p in PALABRAS_RIESGO)

def buscar_huerfanas():
    resultado = []
    for hive, subclave in CLAVES:
        try: raiz = winreg.OpenKey(hive, subclave, 0, winreg.KEY_READ)
        except: continue
        n = winreg.QueryInfoKey(raiz)[0]
        for i in range(n):
            try:
                ns = winreg.EnumKey(raiz, i)
                sub = winreg.OpenKey(raiz, ns, 0, winreg.KEY_READ)
                app  = val(sub, "DisplayName")
                inst = val(sub, "InstallLocation")
                ver  = val(sub, "DisplayVersion")
                uni  = val(sub, "UninstallString")
                winreg.CloseKey(sub)
                if not app: continue
                # Leer DisplayIcon
                icono = ""
                try:
                    sub2 = winreg.OpenKey(raiz, ns, 0, winreg.KEY_READ)
                    icono = val(sub2, "DisplayIcon")
                    winreg.CloseKey(sub2)
                except: pass
                if not esta_instalado(inst, uni, icono):
                    _, ruta_mostrar = carpeta_instalacion(inst, uni, icono)
                    resultado.append({"hive":hive,"subclave":subclave,"nombre_sub":ns,
                                      "app":app,"ver":ver,"ruta":ruta_mostrar or "—","uni":uni,
                                      "desc":"Buscando…","riesgo":es_riesgosa(app)})
            except: continue
        winreg.CloseKey(raiz)
    return resultado

def borrar_entrada(e):
    try:
        r = winreg.OpenKey(e["hive"],e["subclave"],0,winreg.KEY_ALL_ACCESS)
        winreg.DeleteKey(r,e["nombre_sub"])
        winreg.CloseKey(r)
        return True
    except: return False

def describir_app(nombre):
    try:
        q   = urllib.parse.quote(nombre)
        url = f"https://api.duckduckgo.com/?q={q}&format=json&no_html=1&skip_disambig=1"
        req = urllib.request.Request(url, headers={"User-Agent":"Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=8) as r:
            data = json.loads(r.read())
        txt = data.get("AbstractText","").strip()
        if txt:
            return ". ".join(txt.split(". ")[:2]).rstrip(".")+("." if not txt.endswith(".") else "")
        rel = data.get("RelatedTopics",[])
        if rel and isinstance(rel[0],dict):
            t = rel[0].get("Text","").strip()
            if t: return t[:160]+("…" if len(t)>160 else "")
        return "Sin descripción disponible."
    except: return "Sin descripción disponible."

# ── cleanmgr ──────────────────────────────────────────────────
SAGESET_ID = 77
HANDLERS_DESEADOS = ["Update Cleanup","Windows Update Cleanup","Previous Installations",
                     "Temporary Files","Recycle Bin","Temporary Internet Files",
                     "Thumbnail Cache","System error memory dump files",
                     "System error minidump files"]

def configurar_cleanmgr():
    base = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\VolumeCaches"
    flag = f"StateFlags{SAGESET_ID:04d}"
    try:
        raiz = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, base, 0, winreg.KEY_READ)
        n = winreg.QueryInfoKey(raiz)[0]
        for i in range(n):
            try:
                nombre = winreg.EnumKey(raiz, i)
                activar = any(h.lower() in nombre.lower() for h in HANDLERS_DESEADOS)
                sub = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                                     f"{base}\\{nombre}", 0, winreg.KEY_SET_VALUE)
                winreg.SetValueEx(sub, flag, 0, winreg.REG_DWORD, 2 if activar else 0)
                winreg.CloseKey(sub)
            except: continue
        winreg.CloseKey(raiz)
        return True, ""
    except Exception as e:
        return False, str(e)


# ── Medición pre/post limpieza ────────────────────────────────
CATEGORIAS_MEDICION = {
    "Actualizaciones de Windows": [
        r"%WINDIR%\SoftwareDistribution\Download",
        r"%WINDIR%\SoftwareDistribution\DeliveryOptimization",
    ],
    "Archivos temporales": [
        r"%TEMP%",
        r"%WINDIR%\Temp",
        r"%LOCALAPPDATA%\Temp",
    ],
    "Archivos de Internet": [
        r"%LOCALAPPDATA%\Microsoft\Windows\INetCache",
        r"%LOCALAPPDATA%\Microsoft\Windows\WebCache",
    ],
    "Miniaturas (thumbnails)": [
        r"%LOCALAPPDATA%\Microsoft\Windows\Explorer",
    ],
    "Volcados de memoria": [
        r"%WINDIR%\Minidump",
        r"%LOCALAPPDATA%\CrashDumps",
        r"%WINDIR%\LiveKernelReports",
    ],
}

def _rutas_cache_chromium(nombre, patron):
    rutas = []
    base = os.path.expandvars(patron)
    for perfil in _perfiles_chromium(base):
        for sub in CHROMIUM_SUBCARPETAS:
            rutas.append(os.path.join(perfil, sub))
    return rutas

def tamanio_carpeta(ruta):
    ruta = os.path.expandvars(ruta)
    if not os.path.exists(ruta):
        return 0
    total = 0
    try:
        for dp, _, files in os.walk(ruta):
            for f in files:
                try: total += os.path.getsize(os.path.join(dp, f))
                except: pass
    except: pass
    return total

def medir_categorias():
    resultado = {}
    for cat, rutas in CATEGORIAS_MEDICION.items():
        resultado[cat] = sum(tamanio_carpeta(r) for r in rutas)
    # Navegadores
    for nombre, patron in NAVEGADORES_CHROMIUM.items():
        resultado[f"Caché {nombre}"] = sum(
            tamanio_carpeta(r) for r in _rutas_cache_chromium(nombre, patron))
    resultado["Caché Firefox"] = sum(tamanio_carpeta(r) for r in _perfiles_firefox())
    # Papelera: usar tamaño reportado por Windows
    try:
        info = SHQUERYRBINFO()
        info.cbSize = ctypes.sizeof(info)
        ctypes.windll.shell32.SHQueryRecycleBinW(None, ctypes.byref(info))
        resultado["Papelera de reciclaje"] = info.i64Size
    except:
        resultado["Papelera de reciclaje"] = 0
    return resultado

CARPETAS_TEMP = [
    r"%TEMP%",
    r"%WINDIR%\Temp",
    r"%LOCALAPPDATA%\Temp",
]

# ── Caché de navegadores ──────────────────────────────────────
# Subcarpetas de caché seguras para borrar en navegadores Chromium
CHROMIUM_SUBCARPETAS = [
    "Cache", "Cache Storage", "Code Cache", "GPUCache",
    "Media Cache", "Service Worker\\CacheStorage",
    "Service Worker\\ScriptCache",
]

NAVEGADORES_CHROMIUM = {
    "Chrome":  r"%LOCALAPPDATA%\Google\Chrome\User Data",
    "Edge":    r"%LOCALAPPDATA%\Microsoft\Edge\User Data",
    "Brave":   r"%LOCALAPPDATA%\BraveSoftware\Brave-Browser\User Data",
}

def _perfiles_chromium(base):
    """Devuelve todas las carpetas de perfil dentro de User Data."""
    perfiles = []
    if not os.path.isdir(base):
        return perfiles
    for nombre in os.listdir(base):
        ruta = os.path.join(base, nombre)
        if nombre == "Default" or (nombre.startswith("Profile ") and os.path.isdir(ruta)):
            perfiles.append(ruta)
    return perfiles

def _perfiles_firefox():
    """Devuelve las carpetas de caché de todos los perfiles de Firefox.
    Firefox guarda la caché en %LOCALAPPDATA%, no en %APPDATA%."""
    rutas = []
    # Ruta principal de caché (Firefox moderno)
    base_cache = os.path.expandvars(r"%LOCALAPPDATA%\Mozilla\Firefox\Profiles")
    # Ruta de perfiles (para startupCache y perfiles antiguos)
    base_perfil = os.path.expandvars(r"%APPDATA%\Mozilla\Firefox\Profiles")

    # Caché en LOCALAPPDATA
    if os.path.isdir(base_cache):
        for perfil in os.listdir(base_cache):
            ruta = os.path.join(base_cache, perfil)
            if os.path.isdir(ruta):
                for sub in ["cache2", "startupCache"]:
                    rutas.append(os.path.join(ruta, sub))

    # startupCache y cache2 en APPDATA (instalaciones antiguas o portátiles)
    if os.path.isdir(base_perfil):
        for perfil in os.listdir(base_perfil):
            ruta = os.path.join(base_perfil, perfil)
            if os.path.isdir(ruta):
                for sub in ["cache2", "startupCache"]:
                    candidate = os.path.join(ruta, sub)
                    if candidate not in rutas:
                        rutas.append(candidate)

    return rutas

def _borrar_carpeta_contenido(ruta):
    """Borra el contenido de una carpeta (no la carpeta en sí). Devuelve (liberado, errores)."""
    liberado = 0
    errores = []
    if not os.path.isdir(ruta):
        return 0, []
    for nombre in os.listdir(ruta):
        elem = os.path.join(ruta, nombre)
        try:
            tam = tamanio_carpeta(elem) if os.path.isdir(elem) else os.path.getsize(elem)
            if os.path.isdir(elem):
                shutil.rmtree(elem, ignore_errors=False)
            else:
                os.remove(elem)
            liberado += tam
        except Exception as e:
            errores.append(str(e))
    return liberado, errores

def borrar_cache_navegadores():
    """Borra la caché de Chrome, Edge, Brave y Firefox.
    Devuelve dict {navegador: (bytes_liberados, num_errores)}."""
    resultado = {}

    # Chromium (Chrome, Edge, Brave)
    for nombre, patron in NAVEGADORES_CHROMIUM.items():
        base = os.path.expandvars(patron)
        lib_total, err_total = 0, 0
        for perfil in _perfiles_chromium(base):
            for sub in CHROMIUM_SUBCARPETAS:
                ruta = os.path.join(perfil, sub)
                lib, errs = _borrar_carpeta_contenido(ruta)
                lib_total += lib
                err_total += len(errs)
        resultado[nombre] = (lib_total, err_total)

    # Firefox
    lib_ff, err_ff = 0, 0
    for ruta_cache in _perfiles_firefox():
        lib, errs = _borrar_carpeta_contenido(ruta_cache)
        lib_ff += lib
        err_ff += len(errs)
    resultado["Firefox"] = (lib_ff, err_ff)

    return resultado

def borrar_temporales():
    """Borra directamente el contenido de las carpetas de archivos temporales.
    Devuelve (bytes_liberados, errores)."""
    liberados = 0
    errores = []
    for patron in CARPETAS_TEMP:
        ruta = os.path.expandvars(patron)
        if not os.path.exists(ruta):
            continue
        for nombre in os.listdir(ruta):
            elemento = os.path.join(ruta, nombre)
            try:
                tam = tamanio_carpeta(elemento) if os.path.isdir(elemento) else os.path.getsize(elemento)
                if os.path.isdir(elemento):
                    shutil.rmtree(elemento, ignore_errors=False)
                else:
                    os.remove(elemento)
                liberados += tam
            except Exception as e:
                errores.append(f"{elemento}: {e}")
    return liberados, errores

def formatear(b):
    for u in ["B","KB","MB","GB"]:
        if b < 1024: return f"{b:.1f} {u}"
        b /= 1024
    return f"{b:.1f} TB"

# ── Colores y fuentes ─────────────────────────────────────────
BG      = "#12131a"
CARD    = "#1c1e2e"
BORDE   = "#2a2d42"
ACENTO  = "#e94560"
AZUL    = "#1a4a7a"
FG      = "#dde1f0"
DIM     = "#6b7289"
AVISO   = "#f0a500"
VERDE   = "#2ecc71"
FH      = ("Consolas", 11, "bold")
FB      = ("Consolas", 10)
FS      = ("Consolas",  9)


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Limpiador de Archivos temporales y Registro")
        self.configure(bg=BG)
        w, h = 860, 600
        x = (self.winfo_screenwidth() - w) // 2
        self.geometry(f"{w}x{h}+{x}+20")
        self.minsize(700, 500)
        self.entradas  = []
        self.filas     = []          # lista de dicts con widgets por entrada
        self._build()
        self.after(200, lambda: threading.Thread(target=self._escanear, daemon=True).start())

    # ─── Construcción UI ───────────────────────────────────────
    def _build(self):
        # Cabecera
        hdr = tk.Frame(self, bg=AZUL, pady=10)
        hdr.pack(fill="x")
        tk.Label(hdr, text="  🗂  LIMPIEZA DE WINDOWS", font=("Consolas",14,"bold"),
                 bg=AZUL, fg=FG).pack(side="left")
        tk.Button(hdr, text="✖  Cerrar", font=FB, bg=ACENTO, fg=FG,
                  activebackground="#b03040", relief="flat", padx=10,
                  command=self.destroy).pack(side="right", padx=10)

        # Pestañas
        style = ttk.Style()
        style.theme_use("default")
        style.configure("TNotebook",        background=BG,   borderwidth=0)
        style.configure("TNotebook.Tab",    background=BORDE, foreground=FG,
                        font=("Consolas",10,"bold"), padding=[16,6])
        style.map("TNotebook.Tab",          background=[("selected", ACENTO)])

        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True, padx=6, pady=6)

        # ─ Pestaña registro ────────────────────────────────────
        self.tab_reg = tk.Frame(nb, bg=BG)
        nb.add(self.tab_reg, text="  🗂  Registro  ")
        self._build_registro(self.tab_reg)

        # ─ Pestaña disco ───────────────────────────────────────
        tab_disco = tk.Frame(nb, bg=BG)
        nb.add(tab_disco, text="  🧹  Limpieza de disco  ")
        self._build_disco(tab_disco)

        # ─ Pestaña navegadores ─────────────────────────────────
        tab_nav = tk.Frame(nb, bg=BG)
        nb.add(tab_nav, text="  🌐  Navegadores  ")
        self._build_navegadores(tab_nav)

    # ─── Pestaña Registro ──────────────────────────────────────
    def _build_registro(self, parent):
        # Aviso naranja
        av = tk.Frame(parent, bg="#2a1800", pady=5)
        av.pack(fill="x")
        tk.Label(av, text="⚠  Las entradas en naranja pueden ser componentes del sistema. "
                 "Revísalas antes de borrar.",
                 font=FS, bg="#2a1800", fg=AVISO, wraplength=820).pack(padx=12)

        # Barra de estado
        self.bar = tk.Frame(parent, bg=AZUL, pady=4)
        self.bar.pack(fill="x")
        self.lbl_estado  = tk.Label(self.bar, text="Escaneando el registro…",
                                    font=FS, bg=AZUL, fg=DIM)
        self.lbl_estado.pack(side="left", padx=10)
        self.lbl_resumen = tk.Label(self.bar, text="", font=FB, bg=AZUL, fg=FG)
        self.lbl_resumen.pack(side="right", padx=10)

        # Canvas scrollable
        wrap = tk.Frame(parent, bg=BG)
        wrap.pack(fill="both", expand=True)

        self.cv = tk.Canvas(wrap, bg=BG, highlightthickness=0)
        sb = ttk.Scrollbar(wrap, orient="vertical", command=self.cv.yview)
        self.cv.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self.cv.pack(side="left", fill="both", expand=True)

        self.inner = tk.Frame(self.cv, bg=BG)
        self._win  = self.cv.create_window((0,0), window=self.inner, anchor="nw")

        self.inner.bind("<Configure>",
                        lambda e: self.cv.configure(scrollregion=self.cv.bbox("all")))
        self.cv.bind("<Configure>",
                     lambda e: self.cv.itemconfig(self._win, width=e.width))
        self.cv.bind_all("<MouseWheel>",
                         lambda e: self.cv.yview_scroll(int(-1*(e.delta/120)),"units"))

    def _escanear(self):
        datos = buscar_huerfanas()
        self.entradas = datos
        self.after(0, lambda: self._poblar(datos))

    def _poblar(self, datos):
        if not datos:
            tk.Label(self.inner, text="✅  No se encontraron entradas huérfanas.",
                     font=FH, bg=BG, fg=VERDE, pady=40).pack()
            self.lbl_estado.config(text="Registro limpio ✅")
            return

        self.lbl_estado.config(text=f"{len(datos)} entradas encontradas")
        self.filas.clear()

        for idx, e in enumerate(datos):
            self._crear_fila(idx, e)

        self._refrescar_resumen()
        # Buscar descripciones en segundo plano
        threading.Thread(target=self._fetch_descs, daemon=True).start()

    def _crear_fila(self, idx, e):
        color_borde = AVISO if e["riesgo"] else ACENTO
        card = tk.Frame(self.inner, bg=CARD, pady=8, padx=12,
                        highlightbackground=color_borde, highlightthickness=1)
        card.pack(fill="x", padx=6, pady=3)
        card.columnconfigure(1, weight=1)

        # Número
        tk.Label(card, text=f"#{idx+1}", font=FS, bg=CARD, fg=ACENTO,
                 width=3, anchor="nw").grid(row=0, column=0, rowspan=4, sticky="n", padx=(0,8))

        # Nombre
        color_nombre = AVISO if e["riesgo"] else FG
        nombre_frame = tk.Frame(card, bg=CARD)
        nombre_frame.grid(row=0, column=1, sticky="ew")
        tk.Label(nombre_frame, text=e["app"], font=FH, bg=CARD,
                 fg=color_nombre, anchor="w").pack(side="left")
        if e["riesgo"]:
            tk.Label(nombre_frame, text=" ⚠ SISTEMA", font=FS,
                     bg=CARD, fg=AVISO).pack(side="left", padx=4)

        # Versión
        f1 = tk.Frame(card, bg=CARD); f1.grid(row=1, column=1, sticky="ew", pady=1)
        tk.Label(f1, text="Versión        ", font=FS, bg=CARD, fg=DIM).pack(side="left")
        tk.Label(f1, text=e["ver"] or "—", font=FS, bg=CARD, fg=FG).pack(side="left")

        # Ruta
        f2 = tk.Frame(card, bg=CARD); f2.grid(row=2, column=1, sticky="ew", pady=1)
        tk.Label(f2, text="Ruta           ", font=FS, bg=CARD, fg=DIM).pack(side="left")
        tk.Label(f2, text=e["ruta"] or "—", font=FS, bg=CARD, fg=FG,
                 wraplength=580, justify="left").pack(side="left")

        # Descripción
        f3 = tk.Frame(card, bg=CARD); f3.grid(row=3, column=1, sticky="ew", pady=1)
        lbl_d = tk.Label(f3, text="ℹ  Para qué sirve: Buscando…",
                         font=FS, bg=CARD, fg=DIM, wraplength=620, justify="left")
        lbl_d.pack(side="left")

        # Botones + estado
        f4 = tk.Frame(card, bg=CARD); f4.grid(row=4, column=1, sticky="ew", pady=(6,0))
        estado_var = tk.StringVar(value="pendiente")
        lbl_est = tk.Label(f4, text="", font=FS, bg=CARD, fg=DIM)
        lbl_est.pack(side="right", padx=4)

        def si(en=e, sv=estado_var, le=lbl_est, ca=card, b_si=None, b_no=None):
            if sv.get() != "pendiente": return
            if messagebox.askyesno("Confirmar borrado",
               f"¿Borrar la entrada de registro de:\n\n{en['app']}?\n\n"
               "La carpeta ya no existe, pero asegúrate de que el programa no está instalado."):
                if borrar_entrada(en):
                    sv.set("borrada"); le.config(text="✅ Borrada", fg=VERDE)
                    ca.configure(highlightbackground=VERDE)
                else:
                    le.config(text="❌ Error", fg=ACENTO)
            self._refrescar_resumen()

        def no(sv=estado_var, le=lbl_est, ca=card):
            if sv.get() != "pendiente": return
            sv.set("omitida"); le.config(text="⏭  Omitida", fg=DIM)
            ca.configure(highlightbackground=BORDE)
            self._refrescar_resumen()

        tk.Button(f4, text="✔  Borrar", font=FB, bg=ACENTO, fg=FG,
                  activebackground="#b03040", relief="flat", padx=10, pady=2,
                  command=si).pack(side="left", padx=(0,6))
        tk.Button(f4, text="✖  Omitir", font=FB, bg=AZUL, fg=FG,
                  activebackground="#0d3060", relief="flat", padx=10, pady=2,
                  command=no).pack(side="left")

        self.filas.append({"lbl_desc": lbl_d, "estado": estado_var})

    def _fetch_descs(self):
        for i, e in enumerate(self.entradas):
            desc = describir_app(e["app"])
            self.after(0, lambda d=desc, idx=i: self._set_desc(idx, d))

    def _set_desc(self, idx, desc):
        if idx < len(self.filas):
            self.filas[idx]["lbl_desc"].config(
                text=f"ℹ  Para qué sirve: {desc}", fg=DIM)

    def _refrescar_resumen(self):
        b = sum(1 for f in self.filas if f["estado"].get()=="borrada")
        o = sum(1 for f in self.filas if f["estado"].get()=="omitida")
        p = len(self.filas) - b - o
        self.lbl_resumen.config(
            text=f"✅ Borradas: {b}   ⏭ Omitidas: {o}   ⏳ Pendientes: {p}")

    # ─── Pestaña Disco ─────────────────────────────────────────
    def _build_disco(self, parent):
        tk.Label(parent,
            text="Equivalente a Win+R → cleanmgr → Limpiar archivos del sistema",
            font=FB, bg=BG, fg=DIM).pack(pady=(24,4))

        lista = tk.Frame(parent, bg=CARD, padx=20, pady=14,
                         highlightbackground=BORDE, highlightthickness=1)
        lista.pack(padx=80, pady=6)
        tk.Label(lista, text="Se limpiarán:", font=("Consolas",10,"bold"),
                 bg=CARD, fg=ACENTO).pack(anchor="w", pady=(0,6))
        for item in [
            "✔  Limpieza de actualizaciones de Windows",
            "✔  Instalaciones anteriores de Windows",
            "✔  Archivos temporales del sistema",
            "✔  Archivos de Internet temporales",
            "✔  Papelera de reciclaje",
            "✔  Miniaturas (thumbnails)",
            "✔  Volcados de memoria de errores del sistema",
        ]:
            tk.Label(lista, text=item, font=FS, bg=CARD, fg=FG,
                     anchor="w").pack(fill="x", pady=2)

        tk.Label(parent,
            text="⚠  Se abrirá la ventana de Limpieza de disco de Windows. "
                 "Espera a que se cierre sola.",
            font=FS, bg=BG, fg=AVISO, wraplength=680).pack(pady=(10,4))

        self.btn_disco = tk.Button(parent, text="🧹  EJECUTAR LIMPIEZA DE DISCO",
            font=("Consolas",12,"bold"), bg=ACENTO, fg=FG,
            activebackground="#b03040", relief="flat", padx=20, pady=10,
            command=self._run_disco)
        self.btn_disco.pack(pady=14)

        self.lbl_disco = tk.Label(parent, text="", font=FB, bg=BG, fg=DIM)
        self.lbl_disco.pack()

    def _run_disco(self):
        self.btn_disco.config(state="disabled", text="⏳  Configurando…")
        self.lbl_disco.config(text="Configurando opciones en el registro…", fg=DIM)

        def _tarea():
            ok, err = configurar_cleanmgr()
            if not ok:
                self.after(0, lambda: self.lbl_disco.config(text=f"Error: {err}", fg=ACENTO))
                self.after(0, lambda: self.btn_disco.config(
                    state="normal", text="🧹  EJECUTAR LIMPIEZA DE DISCO"))
                return

            # Medir ANTES
            antes = medir_categorias()

            # ── PASO 1: Borrar %TEMP% directamente ──────────────
            self.after(0, lambda: self.lbl_disco.config(
                text="Borrando archivos temporales del usuario…", fg=AVISO))
            lib_directo, errores_temp = borrar_temporales()
            msg_temp = f"  ({formatear(lib_directo)} borrados directamente"
            if errores_temp:
                msg_temp += f", {len(errores_temp)} archivos en uso omitidos"
            msg_temp += ")"

            # ── PASO 2: cleanmgr para el resto ──────────────────
            self.after(0, lambda: self.lbl_disco.config(
                text="Limpieza del sistema en curso… espera a que se cierre la ventana.", fg=AVISO))
            try:
                subprocess.run(["cleanmgr", f"/sagerun:{SAGESET_ID}"])
            except Exception as e:
                self.after(0, lambda: self.lbl_disco.config(
                    text=f"Error al lanzar cleanmgr: {e}", fg=ACENTO))
                self.after(0, lambda: self.btn_disco.config(
                    state="normal", text="🧹  EJECUTAR LIMPIEZA DE DISCO"))
                return

            # Medir DESPUÉS
            despues = medir_categorias()
            self.after(0, lambda: self.btn_disco.config(
                state="normal", text="🧹  EJECUTAR LIMPIEZA DE DISCO"))
            self.after(0, lambda: self.lbl_disco.config(
                text=f"✅  Limpieza completada.{msg_temp}", fg=VERDE))
            self.after(0, lambda: self._mostrar_informe(antes, despues))

        threading.Thread(target=_tarea, daemon=True).start()

    def _mostrar_informe(self, antes, despues):
        win = tk.Toplevel(self)
        win.title("Informe de limpieza")
        win.configure(bg=BG)
        win.geometry("520x420")
        win.resizable(False, False)
        win.grab_set()

        tk.Label(win, text="📋  INFORME DE LIMPIEZA DE DISCO",
                 font=("Consolas",12,"bold"), bg=AZUL, fg=FG,
                 pady=10).pack(fill="x")

        frame = tk.Frame(win, bg=BG)
        frame.pack(fill="both", expand=True, padx=20, pady=12)

        # Cabecera tabla
        for col, txt, w in [(0,"Categoría",30),(1,"Antes",10),(2,"Liberado",10)]:
            tk.Label(frame, text=txt, font=("Consolas",9,"bold"),
                     bg=BORDE, fg=ACENTO, width=w, anchor="w",
                     padx=6, pady=4).grid(row=0, column=col, sticky="ew", padx=1, pady=1)

        total_liberado = 0
        for i, cat in enumerate(antes, 1):
            a = antes[cat]
            d = despues.get(cat, 0)
            lib = max(0, a - d)
            total_liberado += lib
            color_lib = VERDE if lib > 0 else DIM
            bg_fila = CARD if i % 2 == 0 else BG
            tk.Label(frame, text=cat, font=FS, bg=bg_fila, fg=FG,
                     width=30, anchor="w", padx=6, pady=3).grid(row=i, column=0, sticky="ew", padx=1)
            tk.Label(frame, text=formatear(a), font=FS, bg=bg_fila, fg=DIM,
                     width=10, anchor="e", padx=6).grid(row=i, column=1, sticky="ew", padx=1)
            tk.Label(frame, text=formatear(lib), font=FS, bg=bg_fila, fg=color_lib,
                     width=10, anchor="e", padx=6).grid(row=i, column=2, sticky="ew", padx=1)

        # Total
        sep = tk.Frame(win, bg=ACENTO, height=1)
        sep.pack(fill="x", padx=20)
        tk.Label(win, text=f"💾  Total liberado:  {formatear(total_liberado)}",
                 font=("Consolas",11,"bold"), bg=BG, fg=VERDE,
                 pady=8).pack()

        tk.Button(win, text="✖  Cerrar informe", font=FB, bg=ACENTO, fg=FG,
                  activebackground="#b03040", relief="flat", padx=14, pady=6,
                  command=win.destroy).pack(pady=(0,14))


    # ─── Pestaña Navegadores ───────────────────────────────────
    def _build_navegadores(self, parent):
        tk.Label(parent,
            text="Borra la caché de Chrome, Edge, Brave y Firefox",
            font=FB, bg=BG, fg=DIM).pack(pady=(20, 4))

        av = tk.Frame(parent, bg="#2a1800", pady=6)
        av.pack(fill="x", padx=60, pady=(0, 10))
        tk.Label(av,
            text="\u26a0  Cierra los navegadores antes de limpiar. "
                 "Los archivos en uso se omitirán automáticamente.",
            font=FS, bg="#2a1800", fg=AVISO, wraplength=680).pack(padx=12)

        self._nav_frame = tk.Frame(parent, bg=BG)
        self._nav_frame.pack(padx=80, pady=4)

        self._nav_labels = {}
        ICONOS = {"Chrome": "\U0001f7e1", "Edge": "\U0001f535", "Brave": "\U0001f981", "Firefox": "\U0001f98a"}

        for nombre in list(NAVEGADORES_CHROMIUM.keys()) + ["Firefox"]:
            fila = tk.Frame(self._nav_frame, bg=CARD, pady=8, padx=14,
                            highlightbackground=BORDE, highlightthickness=1)
            fila.pack(fill="x", pady=3)
            fila.columnconfigure(1, weight=1)
            tk.Label(fila, text=f"{ICONOS.get(nombre,'\U0001f310')}  {nombre}",
                     font=FB, bg=CARD, fg=FG, width=14, anchor="w").grid(row=0, column=0, padx=(0,10))
            lbl_tam = tk.Label(fila, text="Calculando…", font=FS, bg=CARD, fg=DIM, anchor="w")
            lbl_tam.grid(row=0, column=1, sticky="w")
            lbl_res = tk.Label(fila, text="", font=FS, bg=CARD, fg=DIM, anchor="e")
            lbl_res.grid(row=0, column=2, sticky="e", padx=(10,0))
            self._nav_labels[nombre] = (lbl_tam, lbl_res)

        self.btn_nav = tk.Button(parent,
            text="\U0001f310  LIMPIAR CAché DE NAVEGADORES",
            font=("Consolas",12,"bold"), bg=ACENTO, fg=FG,
            activebackground="#b03040", relief="flat", padx=20, pady=10,
            command=self._run_navegadores)
        self.btn_nav.pack(pady=16)

        self.lbl_nav_total = tk.Label(parent, text="", font=FB, bg=BG, fg=DIM)
        self.lbl_nav_total.pack()

        threading.Thread(target=self._escanear_nav, daemon=True).start()

    def _escanear_nav(self):
        tareas = {}
        for nombre, patron in NAVEGADORES_CHROMIUM.items():
            base = os.path.expandvars(patron)
            rutas = []
            for perfil in _perfiles_chromium(base):
                for sub in CHROMIUM_SUBCARPETAS:
                    rutas.append(os.path.join(perfil, sub))
            tareas[nombre] = rutas
        tareas["Firefox"] = _perfiles_firefox()
        for nombre, rutas in tareas.items():
            total = sum(tamanio_carpeta(r) for r in rutas)
            lbl_tam, _ = self._nav_labels[nombre]
            texto = formatear(total) if total > 0 else "No instalado / vacc\u00edo"
            color = FG if total > 0 else DIM
            self.after(0, lambda t=texto, c=color, l=lbl_tam: l.config(text=t, fg=c))

    def _run_navegadores(self):
        self.btn_nav.config(state="disabled", text="\u23f3  Limpiando\u2026")
        self.lbl_nav_total.config(text="Borrando cach\u00e9\u2026", fg=AVISO)
        for lbl_tam, lbl_res in self._nav_labels.values():
            lbl_res.config(text="")

        def _tarea():
            resultado = borrar_cache_navegadores()
            total = 0
            for nombre, (liberado, errores) in resultado.items():
                total += liberado
                lbl_tam, lbl_res = self._nav_labels[nombre]
                if liberado > 0:
                    txt_res = f"\u2705 {formatear(liberado)} liberados"
                    col_res = VERDE
                    txt_tam = "0 B"
                elif errores > 0:
                    txt_res = f"\u26a0 {errores} archivos en uso"
                    col_res = AVISO
                    txt_tam = "\u2014"
                else:
                    txt_res = "\u2014  Sin cach\u00e9"
                    col_res = DIM
                    txt_tam = "0 B"
                self.after(0, lambda t=txt_tam, l=lbl_tam: l.config(text=t, fg=DIM))
                self.after(0, lambda t=txt_res, c=col_res, l=lbl_res: l.config(text=t, fg=c))
            self.after(0, lambda: self.btn_nav.config(
                state="normal", text="\U0001f310  LIMPIAR CAché DE NAVEGADORES"))
            self.after(0, lambda: self.lbl_nav_total.config(
                text=f"\u2705  Total liberado: {formatear(total)}", fg=VERDE))

        threading.Thread(target=_tarea, daemon=True).start()


# ── Arranque ──────────────────────────────────────────────────
if __name__ == "__main__":
    pedir_elevacion()
    App().mainloop()
