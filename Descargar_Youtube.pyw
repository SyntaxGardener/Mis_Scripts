import tkinter as tk
from tkinter import messagebox, filedialog
import yt_dlp
import os

def descargar():
    url = entry_url.get()
    folder = entry_folder.get()
    opcion = var_opcion.get()
    
    if not url or not folder:
        messagebox.showwarning("Error", "Por favor, introduce la URL y selecciona una carpeta.")
        return

    # Configuración para forzar MP4 y elegir resolución/audio
    ydl_opts = {
        'outtmpl': f'{folder}/%(title)s.%(ext)s',
        'noplaylist': True,
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
        # Forzamos extensión mp4 buscando la mejor combinación de video mp4 + audio m4a
        res = "720" if opcion == "720p" else "1080"
        ydl_opts['format'] = f'bestvideo[height<={res}][ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best'

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        messagebox.showinfo("Éxito", "¡Archivo guardado correctamente!")
    except Exception as e:
        messagebox.showerror("Error", f"Algo salió mal: {e}")

# --- Funciones para el Menú del Botón Derecho ---
def mostrar_menu(event):
    menu_contextual.post(event.x_root, event.y_root)

def pegar_texto():
    try:
        texto = root.clipboard_get()
        entry_url.insert(tk.INSERT, texto)
    except:
        pass

def seleccionar_carpeta():
    dir_seleccionado = filedialog.askdirectory()
    if dir_seleccionado:
        entry_folder.delete(0, tk.END)
        entry_folder.insert(0, dir_seleccionado)

# --- Configuración de la Ventana ---
root = tk.Tk()
root.title("Descargador Educativo v2.0")
root.geometry("500x400")

# Menú contextual (Botón derecho)
menu_contextual = tk.Menu(root, tearoff=0)
menu_contextual.add_command(label="Pequeño tip: Ctrl+V también funciona")
menu_contextual.add_separator()
menu_contextual.add_command(label="Pegar enlace", command=pegar_texto)

# Interfaz
tk.Label(root, text="Enlace de YouTube:", font=("Arial", 10, "bold")).pack(pady=10)
entry_url = tk.Entry(root, width=55)
entry_url.pack(pady=5)

# Vinculamos el botón derecho al cuadro de texto
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