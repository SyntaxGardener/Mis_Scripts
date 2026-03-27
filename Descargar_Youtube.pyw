# -*- coding: utf-8 -*-
import tkinter as tk
from tkinter import messagebox, filedialog
import yt_dlp
import os
import sys

# ==========================================================
# 1. CONFIGURACIÓN DE RUTAS INTELIGENTES
# ==========================================================
def obtener_ruta_ffmpeg():
    ruta_actual = os.path.dirname(os.path.abspath(__file__))
    
    # Prioridad 1: Carpeta actual (Mis_Scripts)
    if os.path.exists(os.path.join(ruta_actual, "ffmpeg.exe")):
        return ruta_actual

    # Prioridad 2: Buscar en carpeta superior (Estructura USB)
    padre = os.path.abspath(os.path.join(ruta_actual, ".."))
    try:
        for carpeta in os.listdir(padre):
            if carpeta.startswith("WPy64-"):
                usb_path = os.path.join(padre, carpeta, "python")
                if os.path.exists(os.path.join(usb_path, "ffmpeg.exe")):
                    return usb_path
    except:
        pass

    # Prioridad 3: Carpeta Herramientas
    pc_path = os.path.normpath(os.path.join(ruta_actual, "..", "Herramientas"))
    if os.path.exists(os.path.join(pc_path, "ffmpeg.exe")):
        return pc_path

    return None

RUTA_FFMPEG_FINAL = obtener_ruta_ffmpeg()

# ==========================================================
# 2. LÓGICA DE DESCARGA
# ==========================================================
def descargar():
    url = entry_url.get()
    folder = entry_folder.get()
    opcion = var_opcion.get()
    abrir_al_final = var_abrir_carpeta.get()
    
    if not url or not folder:
        messagebox.showwarning("Error", "Introduce la URL y selecciona carpeta.")
        return

    folder = os.path.normpath(folder)

    ydl_opts = {
        'outtmpl': os.path.join(folder, '%(title)s.%(ext)s'),
        'noplaylist': True,
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
        
        if abrir_al_final and os.path.exists(folder):
            os.startfile(folder)
            
        messagebox.showinfo("Éxito", "¡Archivo guardado!")
    except Exception as e:
        messagebox.showerror("Error", f"Fallo: {e}")

# ==========================================================
# 3. INTERFAZ GRÁFICA
# ==========================================================
def seleccionar_carpeta():
    dir_seleccionado = filedialog.askdirectory()
    if dir_seleccionado:
        entry_folder.delete(0, tk.END)
        entry_folder.insert(0, dir_seleccionado)

def pegar_texto():
    try:
        texto = root.clipboard_get()
        entry_url.insert(tk.INSERT, texto)
    except: pass

def mostrar_menu(event):
    menu_contextual.post(event.x_root, event.y_root)

root = tk.Tk()
root.title("Descargador YouTube Portable")
root.geometry("500x500")

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

tk.Label(root, text="Formato de salida:", font=("Arial", 10, "bold")).pack(pady=10)
var_opcion = tk.StringVar(value="720p")
tk.Radiobutton(root, text="Vídeo MP4 (720p)", variable=var_opcion, value="720p").pack()
tk.Radiobutton(root, text="Vídeo MP4 (1080p)", variable=var_opcion, value="1080p").pack()
tk.Radiobutton(root, text="Audio MP3", variable=var_opcion, value="mp3").pack()

var_abrir_carpeta = tk.BooleanVar(value=False)
tk.Checkbutton(root, text="Abrir carpeta al finalizar", variable=var_abrir_carpeta).pack(pady=10)

tk.Button(root, text="COMENZAR DESCARGA", bg="#2e7d32", fg="white", font=("Arial", 11, "bold"), 
          command=descargar, height=2, width=25).pack(pady=20)

root.mainloop()