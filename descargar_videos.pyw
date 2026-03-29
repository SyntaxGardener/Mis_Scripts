# -*- coding: utf-8 -*-
# Descargador portable — YouTube  +  RTVE Mediateca  +  EducaMadrid Mediateca
# Requiere: pip install yt-dlp  |  ffmpeg en el PATH o junto al .pyw
# ─────────────────────────────────────────────────────────────────────────────

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import threading
import os
import sys

# ── Paleta ────────────────────────────────────────────────────────────────────
BG        = "#f0f2f5"
BG2       = "#dde1e8"
BG3       = "#ffffff"
FG        = "#1c2030"
FG2       = "#555e72"
ACCENT    = "#2e7d32"          # verde YouTube
ACCENT2   = "#1565c0"          # azul RTVE
ACCENT3   = "#6a1b9a"          # morado EducaMadrid
ACCENT_LT = "#43a047"
BTN_FG    = "#ffffff"
SEP_CLR   = "#b0b8c8"
# ──────────────────────────────────────────────────────────────────────────────

WIN_W = 520
WIN_H = 570

# =============================================================================
# Localizar ffmpeg (misma lógica que el script original)
# =============================================================================
def _obtener_ruta_ffmpeg():
    ruta_actual = os.path.dirname(os.path.abspath(__file__))
    if os.path.exists(os.path.join(ruta_actual, "ffmpeg.exe")):
        return ruta_actual
    padre = os.path.abspath(os.path.join(ruta_actual, ".."))
    try:
        for carpeta in os.listdir(padre):
            if carpeta.startswith("WPy64-"):
                usb_path = os.path.join(padre, carpeta, "python")
                if os.path.exists(os.path.join(usb_path, "ffmpeg.exe")):
                    return usb_path
    except Exception:
        pass
    pc_path = os.path.normpath(os.path.join(ruta_actual, "..", "Herramientas"))
    if os.path.exists(os.path.join(pc_path, "ffmpeg.exe")):
        return pc_path
    return None

RUTA_FFMPEG = _obtener_ruta_ffmpeg()


# =============================================================================
# Logger para yt-dlp → Text widget
# =============================================================================
class _YtLogger:
    def __init__(self, log_fn):
        self._log = log_fn
    def debug(self, msg):
        if not msg.startswith("[debug]"):
            self._log(msg)
    def info(self, msg):
        self._log(msg)
    def warning(self, msg):
        self._log(f"⚠  {msg}")
    def error(self, msg):
        self._log(f"❌  {msg}")


# =============================================================================
# Aplicación principal
# =============================================================================
class DescargadorApp:

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Descargador Portable — YouTube, RTVE & EducaMadrid")
        self.root.configure(bg=BG)
        self.root.resizable(True, False)
        self._busy = False

        # Variables YouTube
        self.yt_url          = tk.StringVar()
        self.yt_folder       = tk.StringVar()
        self.yt_format       = tk.StringVar(value="720p")
        self.yt_open_folder  = tk.BooleanVar(value=False)

        # Variables RTVE Mediateca
        self.rtve_url        = tk.StringVar()
        self.rtve_folder     = tk.StringVar()
        self.rtve_format     = tk.StringVar(value="mejor")
        self.rtve_open_folder = tk.BooleanVar(value=False)

        # Variables EducaMadrid Mediateca
        self.educa_url         = tk.StringVar()
        self.educa_folder      = tk.StringVar()
        self.educa_format      = tk.StringVar(value="mejor")
        self.educa_open_folder = tk.BooleanVar(value=False)

        self._build_ui()
        self._place_window()

    # ── Posición centrada ─────────────────────────────────────────────────────
    def _place_window(self):
        self.root.update_idletasks()
        sw = self.root.winfo_screenwidth()
        self.root.geometry(f"{WIN_W}x{WIN_H}+{(sw - WIN_W) // 2}+80")

    # ── UI ────────────────────────────────────────────────────────────────────
    def _build_ui(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Horizontal.TProgressbar",
                        troughcolor=BG2, background=ACCENT, thickness=8)
        style.configure("App.TNotebook", background=BG, tabmargins=[2, 4, 0, 0])
        style.configure("App.TNotebook.Tab",
                        background=BG2, foreground=FG,
                        font=("Segoe UI", 9, "bold"), padding=[14, 5])
        style.map("App.TNotebook.Tab",
                  background=[("selected", ACCENT)],
                  foreground=[("selected", BTN_FG)])

        root_frame = tk.Frame(self.root, bg=BG)
        root_frame.pack(fill=tk.BOTH, expand=True)

        # Cabecera
        hdr = tk.Frame(root_frame, bg=ACCENT, pady=7, padx=14)
        hdr.pack(fill=tk.X)
        tk.Label(hdr, text="⬇  Descargador Portable",
                 font=("Segoe UI", 12, "bold"),
                 bg=ACCENT, fg=BTN_FG).pack(side=tk.LEFT)
        tk.Label(hdr, text="yt-dlp + ffmpeg",
                 font=("Segoe UI", 8),
                 bg=ACCENT, fg="#a5d6a7").pack(side=tk.RIGHT)

        # ── Log + progreso — debe empaquetarse ANTES que el notebook ──────────
        bottom = tk.Frame(root_frame, bg=BG, padx=10, pady=4)
        bottom.pack(fill=tk.X, side=tk.BOTTOM)

        self.status_var = tk.StringVar(value="Listo.")
        tk.Label(bottom, textvariable=self.status_var,
                 bg=BG, fg=FG2,
                 font=("Segoe UI", 8, "italic"),
                 anchor=tk.W).pack(fill=tk.X)

        self.pbar = ttk.Progressbar(bottom, mode="indeterminate",
                                    style="Horizontal.TProgressbar")
        self.pbar.pack(fill=tk.X, pady=(2, 6))

        # ── Notebook ──────────────────────────────────────────────────────────
        nb = ttk.Notebook(root_frame, style="App.TNotebook")
        nb.pack(fill=tk.BOTH, expand=True, padx=10, pady=(6, 0))

        t_yt    = tk.Frame(nb, bg=BG, padx=16, pady=12)
        t_rtve  = tk.Frame(nb, bg=BG, padx=16, pady=12)
        t_educa = tk.Frame(nb, bg=BG, padx=16, pady=12)
        nb.add(t_yt,    text="  ▶  YouTube  ")
        nb.add(t_rtve,  text="  📺  RTVE Mediateca  ")
        nb.add(t_educa, text="  🎓  EducaMadrid  ")

        # Cambiar color del tab activo según pestaña
        ACCENT_MAP = {0: ACCENT, 1: ACCENT2, 2: ACCENT3}
        def _on_tab_change(event):
            idx = nb.index(nb.select())
            color = ACCENT_MAP.get(idx, ACCENT)
            style.map("App.TNotebook.Tab",
                      background=[("selected", color)],
                      foreground=[("selected", BTN_FG)])
        nb.bind("<<NotebookTabChanged>>", _on_tab_change)

        self._build_yt_tab(t_yt)
        self._build_rtve_tab(t_rtve)
        self._build_educa_tab(t_educa)

    # ── Helpers UI ────────────────────────────────────────────────────────────
    def _lbl(self, parent, text):
        tk.Label(parent, text=text, bg=BG, fg=FG2,
                 font=("Segoe UI", 9)).pack(anchor=tk.W, pady=(8, 1))

    def _entry_row(self, parent, var, btn_text, btn_cmd):
        f = tk.Frame(parent, bg=BG)
        f.pack(fill=tk.X)
        e = tk.Entry(f, textvariable=var, bg=BG3, fg=FG,
                     relief=tk.FLAT, font=("Segoe UI", 9),
                     highlightthickness=1, highlightbackground=BG2,
                     highlightcolor=ACCENT)
        e.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=4, padx=(0, 6))
        tk.Button(f, text=btn_text, command=btn_cmd,
                  bg=BG2, fg=FG, font=("Segoe UI", 8, "bold"),
                  relief=tk.FLAT, cursor="hand2",
                  activebackground=BG2, padx=8, pady=3).pack(side=tk.RIGHT)
        return e

    def _url_entry_row(self, parent, var, accent_color):
        """Entry de URL con menú contextual pegar."""
        f = tk.Frame(parent, bg=BG)
        f.pack(fill=tk.X)
        e = tk.Entry(f, textvariable=var, bg=BG3, fg=FG,
                     relief=tk.FLAT, font=("Segoe UI", 9),
                     highlightthickness=1, highlightbackground=BG2,
                     highlightcolor=accent_color)
        e.pack(fill=tk.X, ipady=4)
        menu = tk.Menu(self.root, tearoff=0)
        menu.add_command(label="✂  Pegar",
                         command=lambda: (var.set(""),
                                         e.insert(0, self.root.clipboard_get())))
        menu.add_command(label="🗑  Limpiar", command=lambda: var.set(""))
        e.bind("<Button-3>", lambda ev: menu.post(ev.x_root, ev.y_root))
        return e

    def _big_btn(self, parent, text, cmd, color):
        tk.Button(parent, text=text, command=cmd,
                  bg=color, fg=BTN_FG,
                  font=("Segoe UI", 10, "bold"),
                  relief=tk.FLAT, cursor="hand2",
                  activebackground=color,
                  activeforeground=BTN_FG,
                  pady=7).pack(fill=tk.X, pady=(14, 4))

    # ── Pestaña YouTube ───────────────────────────────────────────────────────
    def _build_yt_tab(self, parent):
        self._lbl(parent, "Enlace de YouTube:")
        self._url_entry_row(parent, self.yt_url, ACCENT)

        self._lbl(parent, "Carpeta de destino:")
        self._entry_row(parent, self.yt_folder, "Explorar…",
                        lambda: self._browse_folder(self.yt_folder))

        fmt_f = tk.Frame(parent, bg=BG)
        fmt_f.pack(fill=tk.X, pady=(10, 2))
        tk.Label(fmt_f, text="Formato:", bg=BG, fg=FG2,
                 font=("Segoe UI", 9)).pack(side=tk.LEFT)
        for lbl, val in [("MP4 720p", "720p"), ("MP4 1080p", "1080p"), ("MP3", "mp3")]:
            tk.Radiobutton(fmt_f, text=lbl, variable=self.yt_format, value=val,
                           bg=BG, fg=FG, selectcolor=BG2,
                           activebackground=BG,
                           font=("Segoe UI", 9)).pack(side=tk.LEFT, padx=8)

        tk.Checkbutton(parent, text="Abrir carpeta al terminar",
                       variable=self.yt_open_folder,
                       bg=BG, fg=FG2, selectcolor=BG2, activebackground=BG,
                       font=("Segoe UI", 9)).pack(anchor=tk.W, pady=(4, 0))

        self._big_btn(parent, "⬇  Descargar de YouTube",
                      self._yt_start, ACCENT)

    # ── Pestaña RTVE Mediateca ────────────────────────────────────────────────
    def _build_rtve_tab(self, parent):
        tk.Label(parent,
                 text="Pega la URL de cualquier vídeo de RTVE Mediateca\n"
                      "(rtve.es/play/videos/…)",
                 bg=BG, fg=FG2, font=("Segoe UI", 8),
                 justify=tk.LEFT).pack(anchor=tk.W, pady=(0, 4))

        self._lbl(parent, "URL de RTVE Mediateca:")
        self._url_entry_row(parent, self.rtve_url, ACCENT2)

        self._lbl(parent, "Carpeta de destino:")
        self._entry_row(parent, self.rtve_folder, "Explorar…",
                        lambda: self._browse_folder(self.rtve_folder))

        fmt_f = tk.Frame(parent, bg=BG)
        fmt_f.pack(fill=tk.X, pady=(10, 2))
        tk.Label(fmt_f, text="Calidad:", bg=BG, fg=FG2,
                 font=("Segoe UI", 9)).pack(side=tk.LEFT)
        for lbl, val in [("Mejor disponible", "mejor"),
                         ("720p", "720p"),
                         ("480p", "480p")]:
            tk.Radiobutton(fmt_f, text=lbl, variable=self.rtve_format, value=val,
                           bg=BG, fg=FG, selectcolor=BG2,
                           activebackground=BG,
                           font=("Segoe UI", 9)).pack(side=tk.LEFT, padx=6)

        tk.Checkbutton(parent, text="Abrir carpeta al terminar",
                       variable=self.rtve_open_folder,
                       bg=BG, fg=FG2, selectcolor=BG2, activebackground=BG,
                       font=("Segoe UI", 9)).pack(anchor=tk.W, pady=(4, 0))

        self._big_btn(parent, "⬇  Descargar de RTVE Mediateca",
                      self._rtve_start, ACCENT2)

    # ── Pestaña EducaMadrid Mediateca ─────────────────────────────────────────
    def _build_educa_tab(self, parent):
        tk.Label(parent,
                 text="Pega la URL de cualquier vídeo de la Mediateca de EducaMadrid\n"
                      "(mediateca.educa.madrid.org/video/…)",
                 bg=BG, fg=FG2, font=("Segoe UI", 8),
                 justify=tk.LEFT).pack(anchor=tk.W, pady=(0, 4))

        self._lbl(parent, "URL de EducaMadrid Mediateca:")
        self._url_entry_row(parent, self.educa_url, ACCENT3)

        self._lbl(parent, "Carpeta de destino:")
        self._entry_row(parent, self.educa_folder, "Explorar…",
                        lambda: self._browse_folder(self.educa_folder))

        fmt_f = tk.Frame(parent, bg=BG)
        fmt_f.pack(fill=tk.X, pady=(10, 2))
        tk.Label(fmt_f, text="Calidad:", bg=BG, fg=FG2,
                 font=("Segoe UI", 9)).pack(side=tk.LEFT)
        for lbl, val in [("Mejor disponible", "mejor"),
                         ("720p", "720p"),
                         ("480p", "480p")]:
            tk.Radiobutton(fmt_f, text=lbl, variable=self.educa_format, value=val,
                           bg=BG, fg=FG, selectcolor=BG2,
                           activebackground=BG,
                           font=("Segoe UI", 9)).pack(side=tk.LEFT, padx=6)

        tk.Checkbutton(parent, text="Abrir carpeta al terminar",
                       variable=self.educa_open_folder,
                       bg=BG, fg=FG2, selectcolor=BG2, activebackground=BG,
                       font=("Segoe UI", 9)).pack(anchor=tk.W, pady=(4, 0))

        self._big_btn(parent, "⬇  Descargar de EducaMadrid",
                      self._educa_start, ACCENT3)

    # ── Carpeta común ─────────────────────────────────────────────────────────
    def _browse_folder(self, var: tk.StringVar):
        d = filedialog.askdirectory(title="Carpeta de destino")
        if d:
            var.set(d)

    # ── Helpers estado ────────────────────────────────────────────────────────
    def _status(self, msg: str):
        self.status_var.set(msg)
        self.root.update_idletasks()

    def _progress_hook(self, d):
        if d.get("status") == "downloading":
            total      = d.get("total_bytes") or d.get("total_bytes_estimate", 0)
            downloaded = d.get("downloaded_bytes", 0)
            speed      = d.get("speed") or 0
            eta        = d.get("eta") or 0
            if total:
                pct = int(downloaded / total * 100)
                self.pbar.stop()
                self.pbar.configure(mode="determinate", maximum=100, value=pct)
                self._status(
                    f"Descargando… {pct}%  "
                    f"({speed/1024:.0f} KB/s  ETA {eta}s)"
                )
            self.root.update_idletasks()
        elif d.get("status") == "finished":
            self._status("Procesando…")
            self.pbar.configure(mode="indeterminate")
            self.pbar.start(10)

    # ── Descarga genérica (hilo) ──────────────────────────────────────────────
    def _run_download(self, ydl_opts: dict, url: str, folder: str,
                      open_folder: bool):
        self.pbar.start(10)
        try:
            import yt_dlp
        except ImportError:
            messagebox.showerror(
                "Error",
                "yt-dlp no está instalado.\nEjecuta:  pip install yt-dlp")
            self.pbar.stop(); self._busy = False; return

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
            self._status("✅  Descarga completada")
            messagebox.showinfo("Éxito", "¡Archivo guardado correctamente!")
            if open_folder and os.path.exists(folder):
                if sys.platform == "win32":
                    os.startfile(folder)
                elif sys.platform == "darwin":
                    import subprocess; subprocess.Popen(["open", folder])
                else:
                    import subprocess; subprocess.Popen(["xdg-open", folder])
        except Exception as exc:
            self._status("❌  Error en la descarga")
            messagebox.showerror("Error", str(exc))
        finally:
            self.pbar.stop()
            self.pbar.configure(mode="indeterminate", value=0)
            self._busy = False

    # ── YouTube ───────────────────────────────────────────────────────────────
    def _yt_start(self):
        if self._busy:
            return
        url    = self.yt_url.get().strip()
        folder = self.yt_folder.get().strip()
        if not url or not folder:
            messagebox.showwarning("Atención",
                                   "Introduce la URL y selecciona una carpeta.")
            return
        folder = os.path.normpath(folder)
        fmt    = self.yt_format.get()

        ydl_opts = {
            'outtmpl':          os.path.join(folder, '%(title)s.%(ext)s'),
            'noplaylist':       True,
            'ffmpeg_location':  RUTA_FFMPEG,
            'progress_hooks':   [self._progress_hook],
        }
        if fmt == "mp3":
            ydl_opts.update({
                'format': 'bestaudio/best',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }],
            })
        else:
            res = "720" if fmt == "720p" else "1080"
            ydl_opts['format'] = (
                f'bestvideo[height<={res}][ext=mp4]'
                f'+bestaudio[ext=m4a]/best[ext=mp4]/best'
            )

        self._busy = True
        self._status(f"Iniciando descarga YouTube ({fmt})…")
        threading.Thread(
            target=self._run_download,
            args=(ydl_opts, url, folder, self.yt_open_folder.get()),
            daemon=True
        ).start()

    # ── RTVE Mediateca ────────────────────────────────────────────────────────
    def _rtve_start(self):
        if self._busy:
            return
        url    = self.rtve_url.get().strip()
        folder = self.rtve_folder.get().strip()
        if not url or not folder:
            messagebox.showwarning("Atención",
                                   "Introduce la URL y selecciona una carpeta.")
            return
        folder = os.path.normpath(folder)
        cal    = self.rtve_format.get()

        if cal == "mejor":
            fmt_str = "best"
        elif cal == "720p":
            fmt_str = "bestvideo[height<=720]+bestaudio/best[height<=720]/best"
        else:  # 480p
            fmt_str = "bestvideo[height<=480]+bestaudio/best[height<=480]/best"

        ydl_opts = {
            'outtmpl':         os.path.join(folder, '%(title)s.%(ext)s'),
            'format':          fmt_str,
            'ffmpeg_location': RUTA_FFMPEG,
            'progress_hooks':  [self._progress_hook],
            # RTVE usa HLS; merge en mp4
            'merge_output_format': 'mp4',
        }

        self._busy = True
        self._status(f"Iniciando descarga RTVE Mediateca ({cal})…")
        threading.Thread(
            target=self._run_download,
            args=(ydl_opts, url, folder, self.rtve_open_folder.get()),
            daemon=True
        ).start()

    # ── EducaMadrid Mediateca ─────────────────────────────────────────────────
    def _educa_start(self):
        if self._busy:
            return
        url    = self.educa_url.get().strip()
        folder = self.educa_folder.get().strip()
        if not url or not folder:
            messagebox.showwarning("Atención",
                                   "Introduce la URL y selecciona una carpeta.")
            return

        # Validación básica de URL de EducaMadrid
        if "educa.madrid.org" not in url and "educa2.madrid.org" not in url:
            if not messagebox.askyesno(
                    "URL inusual",
                    "La URL no parece ser de EducaMadrid.\n¿Continuar igualmente?"):
                return

        folder = os.path.normpath(folder)
        cal    = self.educa_format.get()

        if cal == "mejor":
            fmt_str = "best"
        elif cal == "720p":
            fmt_str = "bestvideo[height<=720]+bestaudio/best[height<=720]/best"
        else:  # 480p
            fmt_str = "bestvideo[height<=480]+bestaudio/best[height<=480]/best"

        ydl_opts = {
            'outtmpl':         os.path.join(folder, '%(title)s.%(ext)s'),
            'format':          fmt_str,
            'ffmpeg_location': RUTA_FFMPEG,
            'progress_hooks':  [self._progress_hook],
            'merge_output_format': 'mp4',
            # Cabeceras que imitan al navegador (Kaltura puede requerir Referer)
            'http_headers': {
                'Referer': 'https://mediateca.educa.madrid.org/',
                'User-Agent': (
                    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                    'AppleWebKit/537.36 (KHTML, like Gecko) '
                    'Chrome/124.0.0.0 Safari/537.36'
                ),
            },
        }

        self._busy = True
        self._status(f"Iniciando descarga EducaMadrid ({cal})…")
        threading.Thread(
            target=self._run_download,
            args=(ydl_opts, url, folder, self.educa_open_folder.get()),
            daemon=True
        ).start()


# ── Main ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    root = tk.Tk()
    root.minsize(WIN_W, WIN_H)
    app = DescargadorApp(root)
    root.mainloop()
