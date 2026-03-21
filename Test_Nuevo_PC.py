# -*- coding: utf-8 -*-
import os
import sys
import warnings
import importlib
import subprocess
import logging
import json
import configparser

# --- CONFIGURACIÓN DE SILENCIO ---
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", message=".*pkg_resources is deprecated.*")
warnings.filterwarnings("ignore", message=".*Couldn't find ffmpeg.*")
logging.getLogger('pikepdf').setLevel(logging.ERROR)

VERDE   = '\033[92m'
ROJO    = '\033[91m'
AZUL    = '\033[94m'
AMARILLO= '\033[93m'
RESET   = '\033[0m'
BOLD    = '\033[1m'

SCRIPT_DIR   = os.path.dirname(os.path.abspath(__file__))
EXTRAS_FILE  = os.path.join(SCRIPT_DIR, "librerias_extra.json")
CONFIG_FILE  = os.path.join(SCRIPT_DIR, "config.ini")

LIBRERIAS_BASE = [
    ("edge_tts",          "edge-tts",          "Voz Microsoft",            True),
    ("speech_recognition","SpeechRecognition", "Reconocimiento Voz",       False),
    ("pyaudio",           "pyaudio",           "Acceso Micrófono",         False),
    ("pyttsx3",           "pyttsx3",           "Voz Offline",              False),
    ("deep_translator",   "deep-translator",   "Traductor Google",         True),
    ("pandas",            "pandas",            "Análisis Datos",           True),
    ("numpy",             "numpy",             "Operaciones Matem.",       True),
    ("openpyxl",          "openpyxl",          "Excel",                    False),
    ("xlsxwriter",        "xlsxwriter",        "Formatos Excel",           False),
    ("fitz",              "pymupdf",           "Motor PDF (Imágenes)",     True),
    ("pypdf",             "pypdf",             "Unir/Extraer PDF",         True),
    ("pdf2docx",          "pdf2docx",          "PDF a Word",               True),
    ("docx2pdf",          "docx2pdf",          "Word a PDF",               True),
    ("tkinterdnd2",       "tkinterdnd2",       "Arrastrar archivos",       False),
    ("docx",              "python-docx",       "Editor Word",              False),
    ("docx2txt",          "docx2txt",          "Extraer texto",            False),
    ("pdfplumber",        "pdfplumber",        "Extracción PDF",           False),
    ("PyPDF2",            "PyPDF2",            "Lector PDF",               False),
    ("pyperclip",         "pyperclip",         "Portapapeles",             False),
    ("PIL",               "pillow",            "Procesado Imágenes",       True),
    ("qrcode",            "qrcode[pil]",       "Códigos QR",               False),
    ("matplotlib",        "matplotlib",        "Gráficos",                 False),
    ("yt_dlp",            "yt-dlp",            "Descarga YouTube",         True),
    ("moviepy",           "moviepy",           "Videos",                   True),
    ("win32com",          "pywin32",           "Automatización Win",       False),
    ("pythoncom",         "pywin32",           "Componentes COM",          False),
    ("PyInstaller",       "pyinstaller",       "Creador de .EXE",          False),
    ("pydub",             "pydub",             "Manipulación de Audio",    False),
    ("docxtpl",           "docxtpl",           "Plantillas Word (Jinja2)", False),
    ("bs4",               "beautifulsoup4",    "Web Scraping",             True),
    ("google.genai",      "google-genai",      "Gemini API",               False),
    ("anthropic",         "anthropic",         "Claude API",               False),
    ("groq",              "groq",              "Groq API",                 False),
    ("requests",          "requests",          "Peticiones HTTP",          True),
    ("pptx",              "python-pptx",       "Crear presentaciones",     False),
    ("pikepdf",           "pikepdf",           "Edición y Cifrado PDF",    False),
    ("pygame",            "pygame",            "Reproducción Audio",       False),
]

def setup_console():
    if sys.platform == 'win32':
        os.system('color')
        os.system('chcp 65001 > nul')

# ── API Key ──────────────────────────────────────────────────────────────────

def get_api_key():
    config = configparser.ConfigParser()
    config.read(CONFIG_FILE, encoding='utf-8')
    try:
        return config['anthropic']['api_key']
    except KeyError:
        print(f"{ROJO}No se encontró [anthropic] api_key en config.ini{RESET}")
        return None

# ── Consulta a Claude ────────────────────────────────────────────────────────

def consultar_claude(nombre_import):
    """Pregunta a Claude cuál es el nombre pip y una descripción corta."""
    api_key = get_api_key()
    if not api_key:
        return None, None

    try:
        import urllib.request
        import urllib.error

        prompt = (
            f"La librería de Python se importa como: import {nombre_import}\n"
            f"Responde ÚNICAMENTE con este formato JSON, sin explicaciones ni texto extra:\n"
            f'{{"pip": "nombre-en-pip", "desc": "descripción corta max 28 caracteres"}}'
        )

        datos = json.dumps({
            "model": "claude-haiku-4-5-20251001",
            "max_tokens": 100,
            "messages": [{"role": "user", "content": prompt}]
        }).encode("utf-8")

        req = urllib.request.Request(
            "https://api.anthropic.com/v1/messages",
            data=datos,
            headers={
                "Content-Type": "application/json",
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01"
            }
        )

        with urllib.request.urlopen(req, timeout=10) as resp:
            respuesta = json.loads(resp.read().decode("utf-8"))
            texto = respuesta["content"][0]["text"].strip()
            # Limpiar posibles bloques ```json
            texto = texto.replace("```json", "").replace("```", "").strip()
            datos_lib = json.loads(texto)
            return datos_lib.get("pip", ""), datos_lib.get("desc", "")

    except Exception as e:
        print(f"{ROJO}Error consultando Claude: {e}{RESET}")
        return None, None

# ── Gestión de extras ────────────────────────────────────────────────────────

def cargar_extras():
    if not os.path.exists(EXTRAS_FILE):
        return []
    try:
        with open(EXTRAS_FILE, "r", encoding="utf-8") as f:
            datos = json.load(f)
        return [tuple(item) for item in datos]
    except Exception:
        return []

def guardar_extras(extras):
    with open(EXTRAS_FILE, "w", encoding="utf-8") as f:
        json.dump([list(item) for item in extras], f, ensure_ascii=False, indent=2)

def gestionar_librerias(extras):
    while True:
        print(f"\n{AZUL}{BOLD}{'='*75}{RESET}")
        print(f"{AZUL}{BOLD}  GESTIÓN DE LIBRERÍAS EXTRA{RESET}")
        print(f"{AZUL}{'='*75}{RESET}")
        print(f"  {BOLD}1.{RESET} Añadir nueva librería")
        print(f"  {BOLD}2.{RESET} Ver librerías extra guardadas ({len(extras)})")
        print(f"  {BOLD}3.{RESET} Eliminar una librería extra")
        print(f"  {BOLD}0.{RESET} Salir de este menú")
        print(f"{AZUL}{'='*75}{RESET}")

        opcion = input("Elige una opción: ").strip()

        if opcion == '0':
            break

        elif opcion == '1':
            print(f"\n{AMARILLO}-- AÑADIR NUEVA LIBRERÍA --{RESET}")
            imp = input("Nombre de import (ej: sklearn): ").strip()
            if not imp:
                print(f"{ROJO}El nombre de import es obligatorio.{RESET}")
                continue

            # Comprobar duplicados
            todos = LIBRERIAS_BASE + extras
            if any(lib[0] == imp for lib in todos):
                print(f"{AMARILLO}Esa librería ya existe en la lista.{RESET}")
                continue

            print(f"{AMARILLO}Consultando a Claude...{RESET}", end=" ", flush=True)
            pip, desc = consultar_claude(imp)

            if pip:
                print(f"{VERDE}OK{RESET}")
                print(f"\n  Import : {BOLD}{imp}{RESET}")
                print(f"  Pip    : {BOLD}{pip}{RESET}")
                print(f"  Desc   : {BOLD}{desc}{RESET}")
            else:
                print(f"{ROJO}No se pudo obtener info automáticamente.{RESET}")
                pip  = input("Nombre pip (manual): ").strip()
                desc = input("Descripción (manual): ").strip()

            if not pip:
                print(f"{ROJO}Operación cancelada.{RESET}")
                continue

            crit = input("\n¿Es crítica? (s/n): ").strip().lower() == 's'
            extras.append((imp, pip, desc or pip, crit))
            guardar_extras(extras)
            print(f"\n{VERDE}'{pip}' añadida correctamente.{RESET}")
            print(f"{AMARILLO}Se verificará e instalará en la próxima ejecución.{RESET}")

        elif opcion == '2':
            if not extras:
                print(f"\n{AMARILLO}No hay librerías extra guardadas.{RESET}")
            else:
                print(f"\n{AZUL}{BOLD}Librerías extra ({len(extras)}):{RESET}")
                for i, (imp, pip, desc, crit) in enumerate(extras, 1):
                    critica_txt = f"{AMARILLO}[CRÍTICA]{RESET}" if crit else ""
                    print(f"  {BOLD}{i:>2}.{RESET} {pip:<22} ({desc:<28}) import: {imp} {critica_txt}")

        elif opcion == '3':
            if not extras:
                print(f"\n{AMARILLO}No hay librerías extra para eliminar.{RESET}")
                continue
            print(f"\n{AZUL}Librerías extra:{RESET}")
            for i, (imp, pip, desc, crit) in enumerate(extras, 1):
                print(f"  {BOLD}{i}.{RESET} {pip} ({desc})")
            try:
                idx = int(input("\nNúmero a eliminar (0 para cancelar): ").strip())
                if idx == 0:
                    continue
                if 1 <= idx <= len(extras):
                    eliminada = extras.pop(idx - 1)
                    guardar_extras(extras)
                    print(f"{VERDE}'{eliminada[1]}' eliminada de la lista.{RESET}")
                else:
                    print(f"{ROJO}Número fuera de rango.{RESET}")
            except ValueError:
                print(f"{ROJO}Entrada no válida.{RESET}")
        else:
            print(f"{ROJO}Opción no válida.{RESET}")

    return extras

# ── Funciones principales ────────────────────────────────────────────────────

def limpiar_corrupts():
    import site, shutil
    site_packages = site.getsitepackages()[0]
    corruptas = [d for d in os.listdir(site_packages) if d.startswith('~')]

    if not corruptas:
        print(f"{VERDE}No se encontraron instalaciones corruptas.{RESET}\n")
        return

    print(f"{AMARILLO}Se encontraron {len(corruptas)} carpetas corruptas:{RESET}")
    for d in corruptas:
        print(f"  {ROJO}x{RESET} {d}")

    if input("\n¿Eliminarlas ahora? (s/n): ").lower() != 's':
        print(f"{AZUL}Omitiendo limpieza.{RESET}\n")
        return

    eliminadas, errores = 0, 0
    for d in corruptas:
        ruta = os.path.join(site_packages, d)
        try:
            if os.path.isdir(ruta):
                shutil.rmtree(ruta)
            else:
                os.remove(ruta)
            print(f"  {VERDE}OK{RESET} Eliminada: {d}")
            eliminadas += 1
        except Exception as e:
            print(f"  {ROJO}ERROR{RESET} {d}: {e}")
            errores += 1

    print(f"\n{VERDE}Limpieza completada: {eliminadas} eliminadas", end="")
    print(f", {ROJO}{errores} con error{RESET}" if errores else f"{RESET}")
    print()

def generar_requirements(instaladas_info):
    print(f"\n{AZUL}{'='*75}{RESET}")
    if input("¿Generar requirements.txt con versiones instaladas? (s/n): ").lower() != 's':
        print(f"{AZUL}Omitiendo requirements.txt.{RESET}")
        return

    print(f"\n{AMARILLO}Generando requirements.txt...{RESET}")
    resultado = subprocess.run(
        [sys.executable, "-m", "pip", "list", "--format=freeze"],
        capture_output=True, text=True
    )
    versiones = {}
    for linea in resultado.stdout.splitlines():
        if "==" in linea:
            nombre = linea.split("==")[0].strip().lower()
            versiones[nombre] = linea.strip()

    lineas = []
    for pip_name, _ in instaladas_info:
        nombre_base = pip_name.split('[')[0]
        entrada = versiones.get(nombre_base.lower())
        lineas.append(entrada if entrada else nombre_base)

    ruta = os.path.join(SCRIPT_DIR, "requirements.txt")
    with open(ruta, "w", encoding="utf-8") as f:
        f.write("\n".join(lineas) + "\n")

    print(f"{VERDE}{BOLD}requirements.txt generado en:{RESET}")
    print(f"  {ruta}")

def check_and_update():
    setup_console()

    print(f"{AZUL}{BOLD}{'='*75}{RESET}")
    print(f"{AZUL}{BOLD}    GESTOR DE DEPENDENCIAS{RESET}")
    print(f"{AZUL}{BOLD}{'='*75}{RESET}\n")

    # 0. LIMPIEZA
    print(f"{AZUL}{BOLD}[ PASO 0 ] Buscando instalaciones corruptas (~carpetas)...{RESET}")
    limpiar_corrupts()

    # Combinar base + extras
    extras = cargar_extras()
    librerias = LIBRERIAS_BASE + extras

    # 1. CHEQUEO
    print(f"{AZUL}{BOLD}[ PASO 1 ] Verificando librerías instaladas...{RESET}\n")
    faltantes = []
    instaladas = []
    for lib, pip_name, desc, critica in librerias:
        print(f"[*] {pip_name:<22} ({desc:<30})", end=" ", flush=True)
        try:
            importlib.import_module(lib)
            print(f"-> {VERDE}[ OK ]{RESET}")
            instaladas.append((pip_name, critica))
        except ImportError:
            print(f"-> {ROJO}[ NO ENCONTRADA ]{RESET}")
            faltantes.append(pip_name)

    # 2. INSTALACIÓN
    if faltantes:
        print(f"\n{AMARILLO}{BOLD}Atención: Faltan {len(faltantes)} librerías.{RESET}")
        if input("¿Instalar ahora? (s/n): ").lower() == 's':
            for paquete in faltantes:
                print(f"\nInstalando {paquete}...")
                subprocess.check_call([sys.executable, "-m", "pip", "install", paquete])
                instaladas.append((paquete, False))
            print(f"\n{VERDE}Instalación completada.{RESET}")

    # 3. ACTUALIZACIÓN
    print(f"\n{AZUL}{'='*75}{RESET}")
    if input("¿Buscar actualizaciones para librerías críticas? (s/n): ").lower() == 's':
        print(f"\n{AMARILLO}Buscando actualizaciones (esto puede tardar un poco)...{RESET}")
        for pip_name, critica in instaladas:
            if critica:
                print(f"[*] Verificando {pip_name:<22}...", end=" ", flush=True)
                try:
                    subprocess.check_call(
                        [sys.executable, "-m", "pip", "install", "--upgrade",
                         pip_name, "--no-warn-script-location"],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL
                    )
                    print(f"{VERDE}[ ACTUALIZADA ]{RESET}")
                except Exception:
                    print(f"{ROJO}[ ERROR ]{RESET}")
        print(f"\n{VERDE}¡Todo el sistema está al día!{RESET}")
    else:
        print(f"\n{AZUL}Omitiendo actualizaciones.{RESET}")

    # 4. REQUIREMENTS
    generar_requirements(instaladas)

    # 5. GESTIÓN DE LIBRERÍAS EXTRA
    print(f"\n{AZUL}{'='*75}{RESET}")
    if input("¿Gestionar librerías extra? (s/n): ").lower() == 's':
        gestionar_librerias(extras)

if __name__ == "__main__":
    try:
        check_and_update()
    except KeyboardInterrupt:
        print(f"\n{AMARILLO}Operación cancelada por el usuario.{RESET}")
    except Exception as e:
        print(f"\n{ROJO}{BOLD}ERROR INESPERADO:{RESET} {e}")
        import traceback
        traceback.print_exc()

    input(f"\n{BOLD}Presiona Enter para finalizar...{RESET}")
