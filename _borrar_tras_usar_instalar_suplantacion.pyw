# -*- coding: utf-8 -*-
# Instala/actualiza yt-dlp con suplantación de navegador (curl_cffi)
# usando el MISMO Python que ejecuta este archivo.
import sys, os, subprocess, tkinter as tk
from tkinter import messagebox

py = sys.executable
if py.lower().endswith("pythonw.exe"):
    py = py[:-len("pythonw.exe")] + "python.exe"

root = tk.Tk()
root.withdraw()
messagebox.showinfo("Instalador",
    "Voy a instalar/actualizar yt-dlp con suplantación de navegador.\n\n"
    "Puede tardar un minuto. Pulsa Aceptar y espera al siguiente aviso.")

try:
    flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
    r = subprocess.run(
        [py, "-m", "pip", "install", "-U", "--pre", "yt-dlp[default,curl-cffi]"],
        capture_output=True, text=True, creationflags=flags)
    salida = (r.stdout + "\n" + r.stderr).strip()[-1500:]
    if r.returncode == 0:
        messagebox.showinfo("Listo ✅", "Instalación completada.\nYa puedes usar el descargador de TikTok.")
    else:
        messagebox.showerror("Error", f"No se pudo instalar:\n\n{salida}")
except Exception as e:
    messagebox.showerror("Error", str(e))
