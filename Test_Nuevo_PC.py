# -*- coding: utf-8 -*-
import os
import sys
import warnings
import io
import importlib
import subprocess
import logging

# --- CONFIGURACIÓN DE SILENCIO ---
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", message=".*pkg_resources is deprecated.*")
warnings.filterwarnings("ignore", message=".*Couldn't find ffmpeg.*")  # Silencia aviso de pydub

# Silenciar el log de pikepdf que sale en consola al importar
logging.getLogger('pikepdf').setLevel(logging.ERROR)

def setup_console():
    if sys.platform == 'win32':
        os.system('color') 
        os.system('chcp 65001 > nul')
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

VERDE = '\033[92m'
ROJO = '\033[91m'
AZUL = '\033[94m'
AMARILLO = '\033[93m'
RESET = '\033[0m'
BOLD = '\033[1m'

def check_and_update():
    setup_console()
    
    print(f"{AZUL}{BOLD}{'='*75}{RESET}")
    print(f"{AZUL}{BOLD}    GESTOR DE DEPENDENCIAS")
    print(f"{AZUL}{BOLD}{'='*75}{RESET}\n")
    
    # FORMATO: ("Import", "PIP Name", "Descripción", "Es Crítica (True/False)")
    librerias = [
        ("edge_tts", "edge-tts", "Voz Microsoft", True),

        ("speech_recognition", "SpeechRecognition", "Reconocimiento Voz", False),
        ("pyaudio", "pyaudio", "Acceso Micrófono", False),
        ("pyttsx3", "pyttsx3", "Voz Offline", False),
        ("deep_translator", "deep-translator", "Traductor Google", True),
        ("pandas", "pandas", "Análisis Datos", True),
        ("numpy", "numpy", "Operaciones Matem.", True),
        ("openpyxl", "openpyxl", "Excel", False),
        ("xlsxwriter", "xlsxwriter", "Formatos Excel", False),
        ("fitz", "pymupdf", "Motor PDF (Imágenes)", True),
        ("pypdf", "pypdf", "Unir/Extraer PDF", True),
        ("pdf2docx", "pdf2docx", "PDF a Word", True),
        ("docx2pdf", "docx2pdf", "Word a PDF", True),
        ("tkinterdnd2", "tkinterdnd2", "Arrastrar archivos", False),
        ("docx", "python-docx", "Editor Word", False),
        ("docx2txt", "docx2txt", "Extraer texto", False),
        ("pdfplumber", "pdfplumber", "Extracción PDF", False),
        ("PyPDF2", "PyPDF2", "Lector PDF", False),
        ("pyperclip", "pyperclip", "Portapapeles", False),
        ("PIL", "pillow", "Procesado Imágenes", True),
        ("qrcode", "qrcode[pil]", "Códigos QR", False),
        ("matplotlib", "matplotlib", "Gráficos", False),
        ("yt_dlp", "yt-dlp", "Descarga YouTube", True),
        ("moviepy", "moviepy", "Videos", True),
        ("win32com", "pywin32", "Automatización Win", False),
        ("pythoncom", "pywin32", "Componentes COM", False),
        ("PyInstaller", "pyinstaller", "Creador de .EXE", False),
        ("pydub", "pydub", "Manipulación de Audio", False),
        ("docxtpl", "docxtpl", "Plantillas Word (Jinja2)", False),
        ("bs4", "beautifulsoup4", "Web Scraping", True),
        ("google.genai", "google-genai", "Gemini API", False),
        ("anthropic", "anthropic", "Claude API", False),
        ("groq", "groq", "Groq API", False),
        ("pikepdf", "pikepdf", "Edición y Cifrado PDF", False),
        ("pygame", "pygame", "Reproducción Audio", False)        
    ]
    
    faltantes = []
    instaladas = []

    # 1. CHEQUEO INICIAL (Alineación mejorada con padding <22 y <30)
    for lib, pip_name, desc, critica in librerias:
        print(f"[*] {pip_name:<22} ({desc:<30})", end=" ", flush=True)
        try:
            importlib.import_module(lib)
            print(f"-> {VERDE}[ OK ]{RESET}")
            instaladas.append((pip_name, critica))
        except ImportError:
            print(f"-> {ROJO}[ NO ENCONTRADA ]{RESET}")
            faltantes.append(pip_name)

    # 2. INSTALACIÓN DE FALTANTES
    if faltantes:
        print(f"\n{AMARILLO}{BOLD}Atención: Faltan {len(faltantes)} librerías.{RESET}")
        if input("¿Instalar ahora? (s/n): ").lower() == 's':
            for paquete in faltantes:
                print(f"\nInstalando {paquete}...")
                subprocess.check_call([sys.executable, "-m", "pip", "install", paquete])
            print(f"\n{VERDE}Instalación completada.{RESET}")
            return 

    # 3. ACTUALIZACIÓN (UPGRADE)
    print(f"\n{AZUL}{'='*75}{RESET}")
    opcion_upd = input("¿Deseas buscar actualizaciones para las librerías críticas? (s/n): ").lower()
    
    if opcion_upd == 's':
        print(f"\n{AMARILLO}Buscando actualizaciones (esto puede tardar un poco)...{RESET}")
        for pip_name, critica in instaladas:
            if critica:
                print(f"[*] Verificando {pip_name:<22}...", end=" ", flush=True)
                try:
                    subprocess.check_call([sys.executable, "-m", "pip", "install", "--upgrade", pip_name, "--no-warn-script-location"], 
                                         stdout=subprocess.DEVNULL)
                    print(f"{VERDE}[ ACTUALIZADA ]{RESET}")
                except:
                    print(f"{ROJO}[ ERROR ]{RESET}")
        print(f"\n{VERDE}¡Todo el sistema está al día!{RESET}")
    else:
        print(f"\n{AZUL}Omitiendo actualizaciones.{RESET}")

if __name__ == "__main__":
    try:
        check_and_update()
    except Exception as e:
        print(f"\n{ROJO}ERROR:{RESET} {e}")
    
    input(f"\n{BOLD}Presiona Enter para finalizar...{RESET}")
