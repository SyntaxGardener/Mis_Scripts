import os
import subprocess
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import yt_dlp


class SerYTDLPDownloaderPro:

  def __init__(self, root):
    self.root = root
    self.root.title("Descargador Podcasts Cadena SER")
    self.root.geometry("540x360")
    self.root.resizable(False, False)

    # Posicionar centrado horizontalmente y a 5 píxeles del borde superior
    self.root.update_idletasks()
    screen_width = self.root.winfo_screenwidth()
    x_pos = (screen_width // 2) - (540 // 2)
    self.root.geometry(f"540x360+{x_pos}+5")

    # Configuración de estilo claro y limpio
    self.root.configure(bg="#F4F6F9")
    style = ttk.Style()
    style.theme_use("clam")

    style.configure(
        "TLabel", background="#F4F6F9", foreground="#2C3E50", font=("Segoe UI", 10)
    )
    style.configure(
        "TButton", font=("Segoe UI", 10, "bold"), padding=6, relief="flat"
    )
    style.configure(
        "Horizontal.TProgressbar", troughcolor="#E2E8F0", background="#3498DB"
    )

    # Carpeta por defecto (Carpeta Descargas del usuario)
    self.download_path = os.path.join(os.path.expanduser("~"), "Downloads")

    # Interfaz gráfica
    title_label = tk.Label(
        root,
        text="🎙️ Descargador Podcasts Cadena SER",
        font=("Segoe UI", 12, "bold"),
        bg="#F4F6F9",
        fg="#1A252F",
    )
    title_label.pack(pady=12)

    # Marco para la URL
    frame_url = tk.Frame(root, bg="#F4F6F9")
    frame_url.pack(fill="x", padx=25, pady=5)

    lbl_url = ttk.Label(frame_url, text="Pega la URL del episodio de la SER:")
    lbl_url.pack(anchor="w", pady=2)

    self.url_entry = ttk.Entry(frame_url, font=("Segoe UI", 10))
    self.url_entry.pack(fill="x", pady=5)
    self.url_entry.insert(0, "https://cadenaser.com/audio/1787467570403/")

    # Marco para elegir la carpeta de destino
    frame_dir = tk.Frame(root, bg="#F4F6F9")
    frame_dir.pack(fill="x", padx=25, pady=5)

    lbl_dir = ttk.Label(frame_dir, text="Carpeta de destino:")
    lbl_dir.pack(anchor="w", pady=2)

    dir_subframe = tk.Frame(frame_dir, bg="#F4F6F9")
    dir_subframe.pack(fill="x", pady=2)

    self.dir_entry = ttk.Entry(dir_subframe, font=("Segoe UI", 9))
    self.dir_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))
    self.dir_entry.insert(0, self.download_path)

    btn_browse = ttk.Button(
        dir_subframe, text="Examinar...", command=self.seleccionar_carpeta, width=10
    )
    btn_browse.pack(side="right")

    # Botón de descarga
    self.btn_download = ttk.Button(
        root, text="📥 Descargar Episodio", command=self.iniciar_hilo
    )
    self.btn_download.pack(pady=12)

    # Barra de estado y progreso
    self.status_label = ttk.Label(
        root, text="Listo para descargar", font=("Segoe UI", 9, "italic")
    )
    self.status_label.pack(pady=2)

    self.progress = ttk.Progressbar(
        root, orient="horizontal", length=490, mode="indeterminate"
    )
    self.progress.pack(pady=5)

  def seleccionar_carpeta(self):
    carpeta = filedialog.askdirectory(initialdir=self.download_path)
    if carpeta:
      self.download_path = carpeta
      self.dir_entry.delete(0, tk.END)
      self.dir_entry.insert(0, self.download_path)

  def iniciar_hilo(self):
    url = self.url_entry.get().strip()
    if not url:
      messagebox.showerror("Error", "Introduce una URL válida.")
      return

    self.btn_download.config(state="disabled")
    self.progress.start(10)

    threading.Thread(
        target=self.procesar_descarga, args=(url, self.download_path), daemon=True
    ).start()

  def procesar_descarga(self, url, destino):
    try:
      self.actualizar_estado("Procesando descarga...")

      output_template = os.path.join(destino, "%(title)s.%(ext)s")

      ydl_opts = {
          "format": "bestaudio/best",
          "outtmpl": output_template,
          "postprocessors": [{
              "key": "FFmpegExtractAudio",
              "preferredcodec": "mp3",
              "preferredquality": "192",
          }],
          "ignoreerrors": True,
      }

      with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])

      # Abrir la carpeta de destino automáticamente en Windows
      try:
        os.startfile(destino)
      except Exception:
        # En caso de ejecutarse en otro SO que no sea Windows
        pass

      self.root.after(
          0,
          lambda: self.exito_descarga(
              f"¡Descargado con éxito!\n\nGuardado en:\n{destino}"
          ),
      )

    except Exception as e:
      self.root.after(
          0, lambda: self.error_descarga(f"Ocurrió un error:\n{str(e)}")
      )

  def actualizar_estado(self, texto):
    self.root.after(0, lambda: self.status_label.config(text=texto))

  def exito_descarga(self, mensaje):
    self.progress.stop()
    self.btn_download.config(state="normal")
    self.status_label.config(text="Descarga completada")
    messagebox.showinfo("Completado", mensaje)

  def error_descarga(self, mensaje):
    self.progress.stop()
    self.btn_download.config(state="normal")
    self.status_label.config(text="Error en la descarga")
    messagebox.showerror("Error", mensaje)


if __name__ == "__main__":
  root = tk.Tk()
  app = SerYTDLPDownloaderPro(root)
  root.mainloop()