# -*- coding: utf-8 -*-
# Descargador Portable — YouTube + RTVE + EducaMadrid + Eduboom + TikTok
# Requiere: pip install yt-dlp requests beautifulsoup4 selenium webdriver-manager
# ─────────────────────────────────────────────────────────────────────────────

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import threading
import os
import sys
import re
from urllib.parse import urljoin

# ── Paleta ────────────────────────────────────────────────────────────────────
BG        = "#f0f2f5"
BG2       = "#dde1e8"
BG3       = "#ffffff"
FG        = "#1c2030"
FG2       = "#555e72"
ACCENT    = "#2e7d32"          # verde YouTube
ACCENT2   = "#1565c0"          # azul RTVE
ACCENT3   = "#6a1b9a"          # morado EducaMadrid
ACCENT4   = "#e65100"          # naranja Eduboom
ACCENT5   = "#000000"          # negro TikTok
BTN_FG    = "#ffffff"
SEP_CLR   = "#b0b8c8"
# ──────────────────────────────────────────────────────────────────────────────

WIN_W = 540
WIN_H = 620

# =============================================================================
# Localizar ffmpeg
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
# Aplicación principal
# =============================================================================
class DescargadorApp:

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Descargador Portable — YouTube, RTVE, EducaMadrid, Eduboom & TikTok")
        self.root.configure(bg=BG)
        self.root.resizable(True, False)
        self._busy = False

        # Variables
        self.yt_url = tk.StringVar()
        self.yt_folder = tk.StringVar()
        self.yt_format = tk.StringVar(value="720p")
        self.yt_open_folder = tk.BooleanVar(value=False)

        self.rtve_url = tk.StringVar()
        self.rtve_folder = tk.StringVar()
        self.rtve_format = tk.StringVar(value="mejor")
        self.rtve_open_folder = tk.BooleanVar(value=False)

        self.educa_url = tk.StringVar()
        self.educa_folder = tk.StringVar()
        self.educa_open_folder = tk.BooleanVar(value=False)

        self.eduboom_url = tk.StringVar()
        self.eduboom_folder = tk.StringVar()
        self.eduboom_open_folder = tk.BooleanVar(value=False)

        self.tiktok_url = tk.StringVar()
        self.tiktok_folder = tk.StringVar()
        self.tiktok_format = tk.StringVar(value="video")
        self.tiktok_open_folder = tk.BooleanVar(value=False)

        self._build_ui()
        self._place_window()

    def _place_window(self):
        self.root.update_idletasks()
        sw = self.root.winfo_screenwidth()
        self.root.geometry(f"{WIN_W}x{WIN_H}+{(sw - WIN_W) // 2}+80")

    def _build_ui(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Horizontal.TProgressbar", troughcolor=BG2, background=ACCENT, thickness=8)
        style.configure("App.TNotebook", background=BG, tabmargins=[2, 4, 0, 0])
        style.configure("App.TNotebook.Tab", background=BG2, foreground=FG, font=("Segoe UI", 9, "bold"), padding=[12, 5])
        style.map("App.TNotebook.Tab", background=[("selected", ACCENT)], foreground=[("selected", BTN_FG)])

        root_frame = tk.Frame(self.root, bg=BG)
        root_frame.pack(fill=tk.BOTH, expand=True)

        # Cabecera
        hdr = tk.Frame(root_frame, bg=ACCENT, pady=7, padx=14)
        hdr.pack(fill=tk.X)
        tk.Label(hdr, text="⬇  Descargador Portable", font=("Segoe UI", 12, "bold"), bg=ACCENT, fg=BTN_FG).pack(side=tk.LEFT)
        tk.Label(hdr, text="yt-dlp + ffmpeg", font=("Segoe UI", 8), bg=ACCENT, fg="#a5d6a7").pack(side=tk.RIGHT)

        # Log + progreso
        bottom = tk.Frame(root_frame, bg=BG, padx=10, pady=4)
        bottom.pack(fill=tk.X, side=tk.BOTTOM)

        self.status_var = tk.StringVar(value="Listo.")
        tk.Label(bottom, textvariable=self.status_var, bg=BG, fg=FG2, font=("Segoe UI", 8, "italic"), anchor=tk.W).pack(fill=tk.X)

        self.pbar = ttk.Progressbar(bottom, mode="indeterminate", style="Horizontal.TProgressbar")
        self.pbar.pack(fill=tk.X, pady=(2, 6))

        # Notebook
        nb = ttk.Notebook(root_frame, style="App.TNotebook")
        nb.pack(fill=tk.BOTH, expand=True, padx=10, pady=(6, 0))

        t_yt = tk.Frame(nb, bg=BG, padx=16, pady=12)
        t_rtve = tk.Frame(nb, bg=BG, padx=16, pady=12)
        t_educa = tk.Frame(nb, bg=BG, padx=16, pady=12)
        t_eduboom = tk.Frame(nb, bg=BG, padx=16, pady=12)
        t_tiktok = tk.Frame(nb, bg=BG, padx=16, pady=12)
        
        nb.add(t_yt, text="  ▶  YouTube  ")
        nb.add(t_rtve, text="  📺  RTVE  ")
        nb.add(t_educa, text="  🎓  EducaMadrid  ")
        nb.add(t_eduboom, text="  📚  Eduboom  ")
        nb.add(t_tiktok, text="  🎵  TikTok  ")

        ACCENT_MAP = {0: ACCENT, 1: ACCENT2, 2: ACCENT3, 3: ACCENT4, 4: ACCENT5}
        def _on_tab_change(event):
            idx = nb.index(nb.select())
            color = ACCENT_MAP.get(idx, ACCENT)
            style.map("App.TNotebook.Tab", background=[("selected", color)], foreground=[("selected", BTN_FG)])
        nb.bind("<<NotebookTabChanged>>", _on_tab_change)

        self._build_yt_tab(t_yt)
        self._build_rtve_tab(t_rtve)
        self._build_educa_tab(t_educa)
        self._build_eduboom_tab(t_eduboom)
        self._build_tiktok_tab(t_tiktok)

    def _lbl(self, parent, text):
        tk.Label(parent, text=text, bg=BG, fg=FG2, font=("Segoe UI", 9)).pack(anchor=tk.W, pady=(8, 1))

    def _entry_row(self, parent, var, btn_text, btn_cmd):
        f = tk.Frame(parent, bg=BG)
        f.pack(fill=tk.X)
        e = tk.Entry(f, textvariable=var, bg=BG3, fg=FG, relief=tk.FLAT, font=("Segoe UI", 9), highlightthickness=1, highlightbackground=BG2)
        e.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=4, padx=(0, 6))
        tk.Button(f, text=btn_text, command=btn_cmd, bg=BG2, fg=FG, font=("Segoe UI", 8, "bold"), relief=tk.FLAT, cursor="hand2", activebackground=BG2, padx=8, pady=3).pack(side=tk.RIGHT)
        return e

    def _url_entry_row(self, parent, var, accent_color):
        f = tk.Frame(parent, bg=BG)
        f.pack(fill=tk.X)
        e = tk.Entry(f, textvariable=var, bg=BG3, fg=FG, relief=tk.FLAT, font=("Segoe UI", 9), highlightthickness=1, highlightbackground=BG2, highlightcolor=accent_color)
        e.pack(fill=tk.X, ipady=4)
        menu = tk.Menu(self.root, tearoff=0)
        menu.add_command(label="✂  Pegar", command=lambda: (var.set(""), e.insert(0, self.root.clipboard_get())))
        menu.add_command(label="🗑  Limpiar", command=lambda: var.set(""))
        e.bind("<Button-3>", lambda ev: menu.post(ev.x_root, ev.y_root))
        return e

    def _big_btn(self, parent, text, cmd, color):
        tk.Button(parent, text=text, command=cmd, bg=color, fg=BTN_FG, font=("Segoe UI", 10, "bold"), relief=tk.FLAT, cursor="hand2", activebackground=color, activeforeground=BTN_FG, pady=7).pack(fill=tk.X, pady=(14, 4))

    def _build_yt_tab(self, parent):
        self._lbl(parent, "Enlace de YouTube:")
        self._url_entry_row(parent, self.yt_url, ACCENT)
        self._lbl(parent, "Carpeta de destino:")
        self._entry_row(parent, self.yt_folder, "Explorar…", lambda: self._browse_folder(self.yt_folder))
        fmt_f = tk.Frame(parent, bg=BG)
        fmt_f.pack(fill=tk.X, pady=(10, 2))
        tk.Label(fmt_f, text="Formato:", bg=BG, fg=FG2, font=("Segoe UI", 9)).pack(side=tk.LEFT)
        for lbl, val in [("MP4 720p", "720p"), ("MP4 1080p", "1080p"), ("MP3", "mp3")]:
            tk.Radiobutton(fmt_f, text=lbl, variable=self.yt_format, value=val, bg=BG, fg=FG, selectcolor=BG2, activebackground=BG, font=("Segoe UI", 9)).pack(side=tk.LEFT, padx=8)
        tk.Checkbutton(parent, text="Abrir carpeta al terminar", variable=self.yt_open_folder, bg=BG, fg=FG2, selectcolor=BG2, activebackground=BG, font=("Segoe UI", 9)).pack(anchor=tk.W, pady=(4, 0))
        self._big_btn(parent, "⬇  Descargar de YouTube", self._yt_start, ACCENT)

    def _build_rtve_tab(self, parent):
        tk.Label(parent, text="Pega la URL de cualquier vídeo de RTVE", bg=BG, fg=FG2, font=("Segoe UI", 8), justify=tk.LEFT).pack(anchor=tk.W, pady=(0, 4))
        self._lbl(parent, "URL de RTVE:")
        self._url_entry_row(parent, self.rtve_url, ACCENT2)
        self._lbl(parent, "Carpeta de destino:")
        self._entry_row(parent, self.rtve_folder, "Explorar…", lambda: self._browse_folder(self.rtve_folder))
        fmt_f = tk.Frame(parent, bg=BG)
        fmt_f.pack(fill=tk.X, pady=(10, 2))
        tk.Label(fmt_f, text="Calidad:", bg=BG, fg=FG2, font=("Segoe UI", 9)).pack(side=tk.LEFT)
        for lbl, val in [("Mejor", "mejor"), ("720p", "720p"), ("480p", "480p")]:
            tk.Radiobutton(fmt_f, text=lbl, variable=self.rtve_format, value=val, bg=BG, fg=FG, selectcolor=BG2, activebackground=BG, font=("Segoe UI", 9)).pack(side=tk.LEFT, padx=6)
        tk.Checkbutton(parent, text="Abrir carpeta al terminar", variable=self.rtve_open_folder, bg=BG, fg=FG2, selectcolor=BG2, activebackground=BG, font=("Segoe UI", 9)).pack(anchor=tk.W, pady=(4, 0))
        self._big_btn(parent, "⬇  Descargar de RTVE", self._rtve_start, ACCENT2)

    def _build_educa_tab(self, parent):
        tk.Label(parent, text="Pega la URL de EducaMadrid Mediateca", bg=BG, fg=FG2, font=("Segoe UI", 8), justify=tk.LEFT).pack(anchor=tk.W, pady=(0, 4))
        self._lbl(parent, "URL de EducaMadrid:")
        self._url_entry_row(parent, self.educa_url, ACCENT3)
        self._lbl(parent, "Carpeta de destino:")
        self._entry_row(parent, self.educa_folder, "Explorar…", lambda: self._browse_folder(self.educa_folder))
        tk.Checkbutton(parent, text="Abrir carpeta al terminar", variable=self.educa_open_folder, bg=BG, fg=FG2, selectcolor=BG2, activebackground=BG, font=("Segoe UI", 9)).pack(anchor=tk.W, pady=(4, 0))
        self._big_btn(parent, "⬇  Descargar de EducaMadrid", self._educa_start, ACCENT3)

    def _build_eduboom_tab(self, parent):
        tk.Label(parent, text="Pega la URL de Eduboom\n(eduboom.es/video/ID/titulo)", bg=BG, fg=FG2, font=("Segoe UI", 8), justify=tk.LEFT).pack(anchor=tk.W, pady=(0, 4))
        self._lbl(parent, "URL de Eduboom:")
        self._url_entry_row(parent, self.eduboom_url, ACCENT4)
        self._lbl(parent, "Carpeta de destino:")
        self._entry_row(parent, self.eduboom_folder, "Explorar…", lambda: self._browse_folder(self.eduboom_folder))
        tk.Checkbutton(parent, text="Abrir carpeta al terminar", variable=self.eduboom_open_folder, bg=BG, fg=FG2, selectcolor=BG2, activebackground=BG, font=("Segoe UI", 9)).pack(anchor=tk.W, pady=(4, 0))
        self._big_btn(parent, "⬇  Descargar de Eduboom", self._eduboom_start, ACCENT4)

    def _build_tiktok_tab(self, parent):
        tk.Label(parent, text="Pega la URL de un vídeo de TikTok\n(tiktok.com/@usuario/video/ID)", bg=BG, fg=FG2, font=("Segoe UI", 8), justify=tk.LEFT).pack(anchor=tk.W, pady=(0, 4))
        self._lbl(parent, "URL de TikTok:")
        self._url_entry_row(parent, self.tiktok_url, ACCENT5)
        self._lbl(parent, "Carpeta de destino:")
        self._entry_row(parent, self.tiktok_folder, "Explorar…", lambda: self._browse_folder(self.tiktok_folder))
        fmt_f = tk.Frame(parent, bg=BG)
        fmt_f.pack(fill=tk.X, pady=(10, 2))
        tk.Label(fmt_f, text="Formato:", bg=BG, fg=FG2, font=("Segoe UI", 9)).pack(side=tk.LEFT)
        for lbl, val in [("Vídeo (sin marca de agua)", "video"), ("Solo audio (MP3)", "mp3")]:
            tk.Radiobutton(fmt_f, text=lbl, variable=self.tiktok_format, value=val, bg=BG, fg=FG, selectcolor=BG2, activebackground=BG, font=("Segoe UI", 9)).pack(side=tk.LEFT, padx=6)
        tk.Checkbutton(parent, text="Abrir carpeta al terminar", variable=self.tiktok_open_folder, bg=BG, fg=FG2, selectcolor=BG2, activebackground=BG, font=("Segoe UI", 9)).pack(anchor=tk.W, pady=(4, 0))
        self._big_btn(parent, "⬇  Descargar de TikTok", self._tiktok_start, ACCENT5)

    def _browse_folder(self, var):
        d = filedialog.askdirectory(title="Carpeta de destino")
        if d:
            var.set(d)

    def _status(self, msg):
        self.status_var.set(msg)
        self.root.update_idletasks()

    def _progress_hook(self, d):
        if d.get("status") == "downloading":
            total = d.get("total_bytes") or d.get("total_bytes_estimate", 0)
            downloaded = d.get("downloaded_bytes", 0)
            speed = d.get("speed") or 0
            eta = d.get("eta") or 0
            if total:
                pct = int(downloaded / total * 100)
                self.pbar.stop()
                self.pbar.configure(mode="determinate", maximum=100, value=pct)
                self._status(f"Descargando… {pct}% ({speed/1024:.0f} KB/s ETA {eta}s)")
            self.root.update_idletasks()
        elif d.get("status") == "finished":
            self._status("Procesando…")
            self.pbar.configure(mode="indeterminate")
            self.pbar.start(10)

    def _run_download(self, ydl_opts, url, folder, open_folder):
        self.pbar.start(10)
        try:
            import yt_dlp
        except ImportError:
            messagebox.showerror("Error", "yt-dlp no está instalado.\nEjecuta: pip install yt-dlp")
            self.pbar.stop()
            self._busy = False
            return
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
            self._status("✅ Descarga completada")
            messagebox.showinfo("Éxito", "¡Archivo guardado correctamente!")
            if open_folder and os.path.exists(folder):
                if sys.platform == "win32":
                    os.startfile(folder)
                elif sys.platform == "darwin":
                    import subprocess
                    subprocess.Popen(["open", folder])
                else:
                    import subprocess
                    subprocess.Popen(["xdg-open", folder])
        except Exception as exc:
            self._status("❌ Error en la descarga")
            messagebox.showerror("Error", str(exc))
        finally:
            self.pbar.stop()
            self.pbar.configure(mode="indeterminate", value=0)
            self._busy = False

    # ── YouTube ───────────────────────────────────────────────────────────────
    def _yt_start(self):
        if self._busy:
            return
        url = self.yt_url.get().strip()
        folder = self.yt_folder.get().strip()
        if not url or not folder:
            messagebox.showwarning("Atención", "Introduce la URL y selecciona una carpeta.")
            return
        folder = os.path.normpath(folder)
        fmt = self.yt_format.get()
        ydl_opts = {'outtmpl': os.path.join(folder, '%(title)s.%(ext)s'), 'noplaylist': True, 'ffmpeg_location': RUTA_FFMPEG, 'progress_hooks': [self._progress_hook]}
        if fmt == "mp3":
            ydl_opts.update({'format': 'bestaudio/best', 'postprocessors': [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': '192'}]})
        else:
            res = "720" if fmt == "720p" else "1080"
            ydl_opts['format'] = f'bestvideo[height<={res}][ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best'
        self._busy = True
        self._status(f"Iniciando descarga YouTube ({fmt})…")
        threading.Thread(target=self._run_download, args=(ydl_opts, url, folder, self.yt_open_folder.get()), daemon=True).start()

    # ── RTVE ──────────────────────────────────────────────────────────────────
    # El extractor rtve.es:alacarta de yt-dlp está roto. En su lugar usamos
    # el endpoint M3U8 directo de ZTNR (documentado en Streamlink).

    def _rtve_resolver(self, url_pagina, calidad):
        """Devuelve (titulo, url_m3u8) usando el endpoint ZTNR directo de RTVE."""
        import requests

        m = re.search(r'/(\d{6,})', url_pagina)
        if not m:
            raise ValueError(
                "No se encontró el ID del vídeo en la URL.\n"
                "Ejemplo: https://www.rtve.es/play/videos/nombre/titulo/17018915/")
        video_id = m.group(1)

        UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
              "AppleWebKit/537.36 (KHTML, like Gecko) "
              "Chrome/122.0.0.0 Safari/537.36")
        hdrs = {"User-Agent": UA}

        # Obtener título desde la API de metadatos (opcional)
        titulo = f"rtve_{video_id}"
        try:
            r = requests.get(f"https://api2.rtve.es/api/videos/{video_id}.json",
                             headers={**hdrs, "Accept": "application/json"}, timeout=15)
            items = r.json().get("page", {}).get("items", [])
            if items:
                t = (items[0].get("longTitle") or items[0].get("title", "")).strip()
                titulo = re.sub(r'[\\/*?:"<>|]', "", t).strip()[:80] or titulo
        except Exception:
            pass

        # URL M3U8 directa — yt-dlp seleccionará la calidad de la playlist HLS
        url_m3u8 = f"https://ztnr.rtve.es/ztnr/{video_id}.m3u8"
        try:
            chk = requests.get(url_m3u8, headers=hdrs, timeout=15)
            if chk.status_code == 404:
                raise ValueError(
                    f"Vídeo {video_id} no disponible (404).\n"
                    "Puede haber expirado o tener restricción geográfica.")
            chk.raise_for_status()
        except ValueError:
            raise
        except Exception as e:
            raise ConnectionError(f"No se pudo verificar el vídeo:\n{e}")

        return titulo, url_m3u8

    def _rtve_descargar(self, url_pagina, folder, cal, open_folder):
        import yt_dlp
        self.pbar.start(10)
        try:
            self._status("Obteniendo URL de RTVE…")
            titulo, url_video = self._rtve_resolver(url_pagina, cal)
            self._status(f"Descargando: {titulo}")
        except Exception as exc:
            self._status("❌ Error RTVE")
            messagebox.showerror("Error RTVE", str(exc))
            self.pbar.stop(); self._busy = False; return

        # Selección de calidad: yt-dlp elige de la playlist HLS
        if cal == "mejor":
            fmt = "bestvideo+bestaudio/best"
        elif cal == "720p":
            fmt = "bestvideo[height<=720]+bestaudio/best[height<=720]/best"
        else:
            fmt = "bestvideo[height<=480]+bestaudio/best[height<=480]/best"

        ydl_opts = {
            "outtmpl":             os.path.join(folder, f"{titulo}.%(ext)s"),
            "ffmpeg_location":     RUTA_FFMPEG,
            "progress_hooks":      [self._progress_hook],
            "merge_output_format": "mp4",
            "format":              fmt,
            "quiet":               False,
        }
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url_video])
            self._status("✅ Descarga completada")
            messagebox.showinfo("Éxito", f"Archivo guardado en:\n{folder}")
            if open_folder and os.path.exists(folder):
                if sys.platform == "win32":   os.startfile(folder)
                elif sys.platform == "darwin": import subprocess; subprocess.Popen(["open", folder])
                else:                          import subprocess; subprocess.Popen(["xdg-open", folder])
        except Exception as exc:
            self._status("❌ Error en la descarga")
            messagebox.showerror("Error", str(exc))
        finally:
            self.pbar.stop()
            self.pbar.configure(mode="indeterminate", value=0)
            self._busy = False

    def _rtve_start(self):
        if self._busy:
            return
        url = self.rtve_url.get().strip()
        folder = self.rtve_folder.get().strip()
        if not url or not folder:
            messagebox.showwarning("Atención", "Introduce la URL y selecciona una carpeta.")
            return
        folder = os.path.normpath(folder)
        cal = self.rtve_format.get()
        self._busy = True
        self._status(f"Iniciando descarga RTVE ({cal})…")
        threading.Thread(
            target=self._rtve_descargar,
            args=(url, folder, cal, self.rtve_open_folder.get()),
            daemon=True).start()

    # ── EducaMadrid ───────────────────────────────────────────────────────────
    def _educa_extraer_id(self, url):
        m = re.search(r"/video/([a-z0-9]+)", url)
        return m.group(1) if m else None

    def _educa_descargar(self, url_pagina, folder, open_folder):
        self.pbar.start(10)
        try:
            import requests
            from bs4 import BeautifulSoup
        except ImportError:
            messagebox.showerror("Error", "Falta requests o beautifulsoup4\npip install requests beautifulsoup4")
            self.pbar.stop()
            self._busy = False
            return
        video_id = self._educa_extraer_id(url_pagina)
        if not video_id:
            messagebox.showerror("Error", "No se pudo extraer el ID del vídeo")
            self.pbar.stop()
            self._busy = False
            return
        self._status("Analizando página...")
        try:
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
            resp = requests.get(url_pagina, headers=headers, timeout=15)
            soup = BeautifulSoup(resp.text, "html.parser")
            titulo = soup.find("h1")
            titulo = titulo.get_text(strip=True) if titulo else "video"
            titulo = re.sub(r'[\\/*?:"<>|]', "", titulo).strip().replace(" ", "_")[:80]
            url_video = None
            for tag in soup.find_all(["video", "source"]):
                src = tag.get("src") or tag.get("data-src")
                if src and ".mp4" in src:
                    url_video = urljoin(url_pagina, src)
                    break
            if not url_video:
                for script in soup.find_all("script"):
                    encontrados = re.findall(r'https?://[^\s\'"]+\.mp4[^\s\'"]*', script.get_text())
                    if encontrados:
                        url_video = encontrados[0]
                        break
            if not url_video:
                url_video = f"https://mediateca.educa.madrid.org/streaming.php?id={video_id}&ext=.mp4"
            ruta = os.path.join(folder, f"{titulo}.mp4")
            self._status("Descargando...")
            self.pbar.configure(mode="determinate", maximum=100, value=0)
            r = requests.get(url_video, stream=True, timeout=30)
            total = int(r.headers.get('content-length', 0))
            with open(ruta, 'wb') as f:
                for i, chunk in enumerate(r.iter_content(chunk_size=65536)):
                    if chunk:
                        f.write(chunk)
                        if total:
                            pct = int((i * 65536) / total * 100)
                            self.pbar.configure(value=min(pct, 100))
            if os.path.exists(ruta) and os.path.getsize(ruta) > 10000:
                self._status("✅ Descarga completada")
                messagebox.showinfo("Éxito", f"Vídeo guardado: {titulo}.mp4")
                if open_folder:
                    os.startfile(folder) if sys.platform == "win32" else None
            else:
                raise Exception("Archivo vacío")
        except Exception as e:
            self._status("❌ Error")
            messagebox.showerror("Error", str(e))
        finally:
            self.pbar.stop()
            self._busy = False

    def _educa_start(self):
        if self._busy:
            return
        url = self.educa_url.get().strip()
        folder = self.educa_folder.get().strip()
        if not url or not folder:
            messagebox.showwarning("Atención", "Introduce la URL y selecciona una carpeta.")
            return
        folder = os.path.normpath(folder)
        self._busy = True
        threading.Thread(target=self._educa_descargar, args=(url, folder, self.educa_open_folder.get()), daemon=True).start()

    # ── Eduboom ───────────────────────────────────────────────────────────────
    def _eduboom_extraer_id(self, url):
        m = re.search(r"/video/(\d+)", url)
        return m.group(1) if m else None

    def _eduboom_descargar(self, url_pagina, folder, open_folder):
        self.pbar.start(10)
        try:
            from selenium import webdriver
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            from webdriver_manager.chrome import ChromeDriverManager
            from selenium.webdriver.chrome.options import Options
            from selenium.webdriver.chrome.service import Service
            import yt_dlp
            import tempfile, time, html as html_mod
        except ImportError:
            messagebox.showerror("Error",
                "Faltan dependencias. Ejecuta:\n"
                "pip install selenium webdriver-manager yt-dlp")
            self.pbar.stop()
            self._busy = False
            return

        video_id = self._eduboom_extraer_id(url_pagina)
        if not video_id:
            messagebox.showerror("Error",
                "No se pudo extraer el ID del vídeo.\n"
                "Formato esperado: eduboom.es/video/ID/titulo")
            self.pbar.stop()
            self._busy = False
            return

        UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
              "AppleWebKit/537.36 (KHTML, like Gecko) "
              "Chrome/122.0.0.0 Safari/537.36")

        # ── Paso 1: Selenium — cargar la página y extraer URL + cookies ───────
        self._status("Abriendo navegador para analizar la página...")
        chrome_options = Options()
        chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument(f"--user-agent={UA}")
        # Perfil de usuario temporal para que Chrome acepte cookies normalmente
        tmp_profile = tempfile.mkdtemp(prefix="eduboom_chrome_")
        chrome_options.add_argument(f"--user-data-dir={tmp_profile}")

        service = Service(ChromeDriverManager().install())
        driver = None
        url_video = None
        titulo = f"eduboom_{video_id}"
        cookies_netscape = ""   # se rellenará con las cookies de Selenium

        try:
            driver = webdriver.Chrome(service=service, options=chrome_options)
            self._status("Cargando página de Eduboom...")
            driver.get(url_pagina)

            # Esperar a que el body esté presente y dar tiempo al JS
            WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            time.sleep(4)   # esperar renderizado del player JS

            page = html_mod.unescape(driver.page_source).replace('\\/', '/')

            # ── Buscar URL m3u8 ──────────────────────────────────────────────
            patron = r'https?://[^\s"\'<>]+\.m3u8[^\s"\'<>]*'
            matches = list(dict.fromkeys(re.findall(patron, page)))  # sin duplicados

            # También rastrear atributos data-* de cualquier elemento
            if not matches:
                for elem in driver.find_elements(By.CSS_SELECTOR,
                        "[data-params],[data-src],[data-video],[data-url],[data-file]"):
                    for attr in ("data-params","data-src","data-video","data-url","data-file"):
                        val = elem.get_attribute(attr) or ""
                        val = html_mod.unescape(val).replace('\\/', '/')
                        matches += re.findall(patron, val)

            # Limpiar y deduplicar
            matches = list(dict.fromkeys(m.rstrip('",\'\\') for m in matches))

            if not matches:
                raise Exception(
                    "No se encontró la URL del vídeo en la página.\n\n"
                    "Posibles causas:\n"
                    "• El vídeo requiere iniciar sesión en Eduboom\n"
                    "• La URL introducida no es correcta\n"
                    "• La estructura de la web ha cambiado")

            url_video = matches[0]

            # ── Obtener título ───────────────────────────────────────────────
            try:
                h1 = driver.find_element(By.TAG_NAME, "h1").text.strip()
                if h1:
                    titulo = h1
            except Exception:
                t = driver.title
                for suf in (" | Eduboom.es", " | Eduboom", "- Eduboom"):
                    t = t.replace(suf, "")
                if t.strip():
                    titulo = t.strip()
            titulo = re.sub(r'[\\/*?:"<>|]', "", titulo).strip()[:80] or f"eduboom_{video_id}"

            # ── Exportar cookies al formato Netscape para yt-dlp ─────────────
            lines = ["# Netscape HTTP Cookie File"]
            for c in driver.get_cookies():
                domain   = c.get("domain", "")
                flag     = "TRUE" if domain.startswith(".") else "FALSE"
                path     = c.get("path", "/")
                secure   = "TRUE" if c.get("secure") else "FALSE"
                expiry   = str(int(c.get("expiry", 0)))
                name     = c.get("name", "")
                value    = c.get("value", "")
                lines.append(f"{domain}\t{flag}\t{path}\t{secure}\t{expiry}\t{name}\t{value}")
            cookies_netscape = "\n".join(lines)

        except Exception as e:
            self._status("❌ Error")
            messagebox.showerror("Error en Eduboom", str(e))
            if driver:
                try: driver.quit()
                except Exception: pass
            self.pbar.stop()
            self._busy = False
            return
        finally:
            if driver:
                try: driver.quit()
                except Exception: pass
            driver = None

        # ── Paso 2: yt-dlp — descargar con cookies y cabeceras correctas ─────
        self._status("Descargando vídeo (HLS)...")
        self.pbar.configure(mode="determinate", maximum=100, value=0)

        # Guardar cookies en archivo temporal
        cookie_file = None
        try:
            import tempfile as tf
            fd, cookie_file = tf.mkstemp(suffix=".txt", prefix="eduboom_cookies_")
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                fh.write(cookies_netscape)

            ydl_opts = {
                'outtmpl': os.path.join(folder, f"{titulo}.%(ext)s"),
                'ffmpeg_location': RUTA_FFMPEG,
                'progress_hooks': [self._progress_hook],
                'merge_output_format': 'mp4',
                'cookiefile': cookie_file,
                'http_headers': {
                    'User-Agent': UA,
                    'Referer': 'https://www.eduboom.es/',
                    'Origin':  'https://www.eduboom.es',
                },
                'quiet': False,
            }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url_video])

        finally:
            if cookie_file and os.path.exists(cookie_file):
                try: os.remove(cookie_file)
                except Exception: pass
            # Limpiar perfil temporal de Chrome
            try:
                import shutil
                shutil.rmtree(tmp_profile, ignore_errors=True)
            except Exception:
                pass

        # ── Comprobar resultado ───────────────────────────────────────────────
        import glob
        patron_arch = os.path.join(folder, f"{titulo}.*")
        archivos = [f for f in glob.glob(patron_arch) if os.path.getsize(f) > 10000]
        if archivos:
            self._status("✅ Descarga completada")
            messagebox.showinfo("Éxito", f"Vídeo guardado:\n{archivos[0]}")
            if open_folder and sys.platform == "win32":
                os.startfile(folder)
        else:
            self._status("❌ Error")
            messagebox.showerror("Error", "El archivo descargado está vacío o no se encontró.")

        self.pbar.stop()
        self._busy = False

    def _eduboom_start(self):
        if self._busy:
            return
        url = self.eduboom_url.get().strip()
        folder = self.eduboom_folder.get().strip()
        if not url or not folder:
            messagebox.showwarning("Atención", "Introduce la URL y selecciona una carpeta.")
            return
        folder = os.path.normpath(folder)
        self._busy = True
        threading.Thread(target=self._eduboom_descargar, args=(url, folder, self.eduboom_open_folder.get()), daemon=True).start()

    # ── TikTok ────────────────────────────────────────────────────────────────
    # yt-dlp soporta TikTok de forma nativa (sin marca de agua cuando está disponible).

    def _tiktok_start(self):
        if self._busy:
            return
        url = self.tiktok_url.get().strip()
        folder = self.tiktok_folder.get().strip()
        if not url or not folder:
            messagebox.showwarning("Atención", "Introduce la URL y selecciona una carpeta.")
            return
        if "tiktok.com" not in url:
            messagebox.showwarning("Atención", "La URL introducida no parece ser de TikTok.")
            return
        folder = os.path.normpath(folder)
        fmt = self.tiktok_format.get()
        ydl_opts = {
            'outtmpl': os.path.join(folder, '%(uploader)s_%(id)s.%(ext)s'),
            'noplaylist': True,
            'ffmpeg_location': RUTA_FFMPEG,
            'progress_hooks': [self._progress_hook],
        }
        if fmt == "mp3":
            ydl_opts.update({
                'format': 'bestaudio/best',
                'postprocessors': [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': '192'}],
            })
        else:
            # yt-dlp prioriza automáticamente el vídeo "playAddr" sin marca de agua cuando existe
            ydl_opts['format'] = 'bestvideo+bestaudio/best'
            ydl_opts['merge_output_format'] = 'mp4'
        self._busy = True
        self._status(f"Iniciando descarga TikTok ({fmt})…")
        threading.Thread(target=self._run_download, args=(ydl_opts, url, folder, self.tiktok_open_folder.get()), daemon=True).start()

# ── Main ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    root = tk.Tk()
    root.minsize(WIN_W, WIN_H)
    app = DescargadorApp(root)
    root.mainloop()