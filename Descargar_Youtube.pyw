# -*- coding: utf-8 -*-
import tkinter as tk
from tkinter import messagebox, filedialog
import yt_dlp
import os
import sys

# ==========================================================
# 1. CONFIGURACIÓN DE RUTAS INTELIGENTES (USB / PC)
# ==========================================================
def obtener_ruta_ffmpeg():
    ruta_actual = os.path.dirname(os.path.abspath(__file__))
    padre = os.path.abspath(os.path.join(ruta_actual, ".."))
    
    # 1. BUSCAR EN USB (Cualquier versión de WinPython)
    # Listamos las carpetas en TRABAJO_PORTABLE para ver cuál tienes
    try:
        for carpeta in os.listdir(padre):
            if carpeta.startswith("WPy64-"):
                usb_path = os.path.join(padre, carpeta, "python")
                if os.path.exists(os.path.join(usb_path, "ffmpeg.exe")):
                    return usb_path
    except:
        pass

    # 2. BUSCAR EN PC (Carpeta Herramientas al lado de Mis_Scripts)
    pc_path = os.path.normpath(os.path.join(ruta_actual, "..", "Herramientas"))
    if os.path.exists(os.path.join(pc_path, "ffmpeg.exe")):
        return pc_path

    return None

# Guardamos la ruta encontrada para usarla luego
RUTA_FFMPEG_FINAL = obtener_ruta_ffmpeg()

# ==========================================================
# 2. LÓGICA DE DESCARGA
# ==========================================================
def descargar():
    url = entry_url.get()
    folder = entry_folder.get()
    opcion = var_opcion.get()
    
    if not url or not folder:
        messagebox.showwarning("Error", "Introduce la URL y selecciona carpeta.")
        return

    ydl_opts = {
        'outtmpl': f'{folder}/%(title)s.%(ext)s',
        'noplaylist': True,
        # AQUÍ USAMOS LA RUTA INTELIGENTE
        'ffmpeg_location': RUTA_FFMPEG_FINAL, 
    }

    if opcion == "mp3":
        ydl_opts.update({
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
        })
    else:
        res = "720" if opcion == "720p" else "1080"
        ydl_opts['format'] = f'bestvideo[height<={res}][ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best'

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        messagebox.showinfo("Éxito", "¡Archivo guardado!")
    except Exception as e:
        messagebox.showerror("Error", f"Fallo: {e}")

# ==========================================================
# 3. INTERFAZ GRÁFICA (IGUAL QUE ANTES)
# ==========================================================
def mostrar_menu(event):
    menu_contextual.post(event.x_root, event.y_root)

def pegar_texto():
    try:
        texto = root.clipboard_get()
        entry_url.insert(tk.INSERT, texto)
    except: pass

def seleccionar_carpeta():
    dir_seleccionado = filedialog.askdirectory()
    if dir_seleccionado:
        entry_folder.delete(0, tk.END)
        entry_folder.insert(0, dir_seleccionado)

root = tk.Tk()
root.title("Descargador YouTube Portable")
root.geometry(f"500x450+{(root.winfo_screenwidth()//2)-250}+50")

menu_contextual = tk.Menu(root, tearoff=0)
menu_contextual.add_command(label="Pegar enlace", command=pegar_texto)

tk.Label(root, text="Enlace de YouTube:", font=("Arial", 10, "bold")).pack(pady=10)
entry_url = tk.Entry(root, width=55)
entry_url.pack(pady=5)
entry_url.bind("<Button-3>", mostrar_menu)

tk.Label(root, text="Carpeta donde guardar:", font=("Arial", 10, "bold")).pack(pady=10)
frame_folder = tk.Frame(root)
frame_folder.pack()
entry_folder = tk.Entry(frame_folder, width=35)
entry_folder.pack(side=tk.LEFT, padx=5)
tk.Button(frame_folder, text="Explorar...", command=seleccionar_carpeta).pack(side=tk.LEFT)

tk.Label(root, text="Formato de salida:", font=("Arial", 10, "bold")).pack(pady=15)
var_opcion = tk.StringVar(value="720p")
tk.Radiobutton(root, text="Vídeo MP4 (720p)", variable=var_opcion, value="720p").pack()
tk.Radiobutton(root, text="Vídeo MP4 (1080p)", variable=var_opcion, value="1080p").pack()
tk.Radiobutton(root, text="Audio MP3", variable=var_opcion, value="mp3").pack()

tk.Button(root, text="COMENZAR DESCARGA", bg="#2e7d32", fg="white", font=("Arial", 11, "bold"), 
          command=descargar, height=2, width=25).pack(pady=30)

root.mainloop()