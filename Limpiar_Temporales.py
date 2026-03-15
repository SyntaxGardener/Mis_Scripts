import os, shutil, tempfile, ctypes, sys, traceback

# ─────────────────────────────────────────────────────────────
#  UTILIDADES
# ─────────────────────────────────────────────────────────────

def es_administrador():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def pedir_elevacion():
    if not es_administrador():
        ctypes.windll.shell32.ShellExecuteW(
            None, "runas", sys.executable, __file__, None, 1
        )
        sys.exit()

def formatear_bytes(b):
    for u in ["B", "KB", "MB", "GB"]:
        if b < 1024:
            return f"{b:.1f} {u}"
        b /= 1024
    return f"{b:.1f} TB"

def tamanio_elemento(ruta):
    try:
        if os.path.isfile(ruta):
            return os.path.getsize(ruta)
        return sum(
            os.path.getsize(os.path.join(dp, f))
            for dp, _, files in os.walk(ruta)
            for f in files
        )
    except:
        return 0

def eliminar(ruta):
    if os.path.isfile(ruta) or os.path.islink(ruta):
        os.remove(ruta)
    elif os.path.isdir(ruta):
        shutil.rmtree(ruta)

def limpiar_carpeta(carpeta):
    elim = err = espacio = 0
    if not os.path.exists(carpeta):
        return elim, err, espacio
    try:
        contenido = os.listdir(carpeta)
    except PermissionError:
        print(f"    [!] Sin permisos: {carpeta}")
        return elim, err, espacio
    for nombre in contenido:
        ruta = os.path.join(carpeta, nombre)
        try:
            espacio += tamanio_elemento(ruta)
            eliminar(ruta)
            elim += 1
        except:
            err += 1
    return elim, err, espacio

def imprimir_subtotal(e, err, esp):
    print(f"    >> Subtotal: {e} eliminados | {err} errores | {formatear_bytes(esp)} liberados")

# ─────────────────────────────────────────────────────────────
#  MÓDULOS DE LIMPIEZA
# ─────────────────────────────────────────────────────────────

def limpiar_temporales():
    print("\n📁 ARCHIVOS TEMPORALES DEL SISTEMA")
    carpetas = [
        tempfile.gettempdir(),
        os.path.expandvars(r"%WINDIR%\Temp"),
        os.path.expandvars(r"%LOCALAPPDATA%\Temp"),
    ]
    total_e = total_err = total_esp = 0
    for carpeta in carpetas:
        print(f"   → {carpeta}")
        e, err, esp = limpiar_carpeta(carpeta)
        total_e += e; total_err += err; total_esp += esp
    imprimir_subtotal(total_e, total_err, total_esp)
    return total_e, total_err, total_esp

def vaciar_papelera():
    print("\n🗑️  PAPELERA DE RECICLAJE")
    total_e = 0
    total_esp = 0
    
    # Buscamos en todas las unidades disponibles
    unidades = [f"{d}:\\" for d in "ABCDEFGHIJKLMNOPQRSTUVWXYZ" if os.path.exists(f"{d}:\\")]
    
    for unidad in unidades:
        ruta_papelera = os.path.join(unidad, "$Recycle.Bin")
        if os.path.exists(ruta_papelera):
            for raiz, dirs, archivos in os.walk(ruta_papelera):
                for f in archivos:
                    # FILTROS PARA CONTEO REALISTA:
                    # 1. Ignoramos archivos de metadatos ($I...) que Windows crea por cada borrado
                    # 2. Ignoramos archivos de sistema (desktop.ini)
                    if f.startswith("$I") or f.lower() == "desktop.ini":
                        continue
                    
                    # Solo contamos archivos que empiecen por $R (el contenido real) 
                    # o cualquier otro archivo que no sea de control.
                    total_e += 1
                    try:
                        total_esp += os.path.getsize(os.path.join(raiz, f))
                    except:
                        pass

    try:
        # Ejecutamos el vaciado
        result = ctypes.windll.shell32.SHEmptyRecycleBinW(None, None, 0x0007)
        if result == 0 or result == -2147418113:
            if total_e > 0:
                print(f"   → Vaciada correctamente")
                imprimir_subtotal(total_e, 0, total_esp)
            else:
                print("   → La papelera ya estaba vacía.")
            return total_e, 0, total_esp
        else:
            return 0, 1, 0
    except Exception:
        return 0, 1, 0

def limpiar_logs_y_tmp():
    print("\n📄 ARCHIVOS .LOG / .TMP / .BAK DEL SISTEMA")
    extensiones = {".tmp", ".log", ".bak", ".old", ".chk", ".gid", ".dmp"}
    carpetas = [
        os.path.expandvars(r"%WINDIR%\Logs"),
        os.path.expandvars(r"%WINDIR%\Minidump"),
        os.path.expandvars(r"%LOCALAPPDATA%\CrashDumps"),
        os.path.expandvars(r"%APPDATA%\Microsoft\Windows\Recent"),
    ]
    total_e = total_err = total_esp = 0
    for carpeta in carpetas:
        if not os.path.exists(carpeta): continue
        print(f"   → Buscando en {carpeta}...")
        for dp, _, files in os.walk(carpeta):
            for f in files:
                if os.path.splitext(f)[1].lower() in extensiones:
                    ruta = os.path.join(dp, f)
                    try:
                        total_esp += tamanio_elemento(ruta)
                        os.remove(ruta)
                        total_e += 1
                    except:
                        total_err += 1
    imprimir_subtotal(total_e, total_err, total_esp)
    return total_e, total_err, total_esp

def limpiar_cache_navegadores():
    print("\n🌐 CACHÉ DE NAVEGADORES")
    total_e = total_err = total_esp = 0
    chromium = {
        "Chrome": os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\User Data"),
        "Edge":   os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\Edge\User Data"),
    }
    for nombre, base in chromium.items():
        if not os.path.exists(base): continue
        perfiles = ["Default"] + [p for p in os.listdir(base) if p.startswith("Profile")]
        for perfil in perfiles:
            for sub in ["Cache", os.path.join("Cache", "Cache_Data"), "Code Cache", "GPUCache"]:
                ruta = os.path.join(base, perfil, sub)
                if os.path.exists(ruta):
                    e, err, esp = limpiar_carpeta(ruta)
                    total_e += e; total_err += err; total_esp += esp
    
    # Firefox
    firefox_base = None
    for candidato in [os.path.expandvars(r"%APPDATA%\Mozilla\Firefox\Profiles"), os.path.expandvars(r"%LOCALAPPDATA%\Mozilla\Firefox\Profiles")]:
        if os.path.exists(candidato):
            firefox_base = candidato
            break
    if firefox_base:
        for perfil in os.listdir(firefox_base):
            for sub in ["cache2", "startupCache", "thumbnails"]:
                ruta = os.path.join(firefox_base, perfil, sub)
                if os.path.exists(ruta):
                    e, err, esp = limpiar_carpeta(ruta)
                    total_e += e; total_err += err; total_esp += esp
    
    imprimir_subtotal(total_e, total_err, total_esp)
    return total_e, total_err, total_esp

def limpiar_windows_update():
    print("\n🔄 CACHÉ DE WINDOWS UPDATE")
    os.system("net stop wuauserv >nul 2>&1")
    os.system("net stop bits >nul 2>&1")
    carpetas = [
        os.path.expandvars(r"%WINDIR%\SoftwareDistribution\Download"),
        os.path.expandvars(r"%WINDIR%\SoftwareDistribution\DeliveryOptimization"),
    ]
    total_e = total_err = total_esp = 0
    for carpeta in carpetas:
        if os.path.exists(carpeta):
            e, err, esp = limpiar_carpeta(carpeta)
            total_e += e; total_err += err; total_esp += esp
    os.system("net start wuauserv >nul 2>&1")
    os.system("net start bits >nul 2>&1")
    imprimir_subtotal(total_e, total_err, total_esp)
    return total_e, total_err, total_esp

# ─────────────────────────────────────────────────────────────
#  MAIN
# ─────────────────────────────────────────────────────────────

def main():
    pedir_elevacion()
    print("=" * 60)
    print("         LIMPIEZA PROFUNDA DE WINDOWS INICIADA")
    print("=" * 60)

    modulos = [
        ("Temporales", limpiar_temporales),
        ("Papelera", vaciar_papelera),
        ("Logs/Extra", limpiar_logs_y_tmp),
        ("Navegadores", limpiar_cache_navegadores),
        ("Windows Update", limpiar_windows_update)
    ]

    grand_e = grand_err = grand_esp = 0
    for nombre, func in modulos:
        e, err, esp = func()
        grand_e += e; grand_err += err; grand_esp += esp

    print("\n" + "=" * 60)
    print("  RESUMEN FINAL")
    print("=" * 60)
    print(f"  ✅ Total elementos eliminados : {grand_e}")
    print(f"  ❌ Total errores (en uso)     : {grand_err}")
    print(f"  💾 Total espacio liberado     : {formatear_bytes(grand_esp)}")
    print("=" * 60)
    input("\nPulsa ENTER para cerrar...")

if __name__ == "__main__":
    try:
        main()
    except Exception:
        log = os.path.join(os.path.expanduser("~"), "Desktop", "limpieza_error.txt")
        with open(log, "w") as f:
            traceback.print_exc(file=f)
        input(f"\nERROR inesperado. Revisa {log} y pulsa ENTER...")