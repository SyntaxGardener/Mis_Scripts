import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import os
import subprocess
import sys
from pathlib import Path
from datetime import datetime

# ── Paleta de colores ────────────────────────────────────────────────
BG         = "#F5F5F0"
PANEL      = "#FFFFFF"
ACCENT     = "#4A90D9"
ACCENT_HOV = "#357ABD"
TEXT       = "#2C2C2C"
SUBTEXT    = "#7A7A7A"
BORDER     = "#DCDCDC"
SUCCESS    = "#4CAF50"
ERROR      = "#E53935"
WARN       = "#FF8F00"
PROG_BG    = "#E8E8E8"
FONT_MAIN  = ("Segoe UI", 10)
FONT_BOLD  = ("Segoe UI", 10, "bold")
FONT_TITLE = ("Segoe UI", 13, "bold")
FONT_SMALL = ("Segoe UI", 8)

# ── Comprobación / instalación de dependencias ───────────────────────
REQUIRED = {"openai-whisper": "whisper"}

# Añadir la carpeta del script al PATH para que Whisper encuentre ffmpeg.exe local
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
os.environ["PATH"] = _SCRIPT_DIR + os.pathsep + os.environ.get("PATH", "")

# Velocidad estimada de cada modelo (segundos de audio por segundo de CPU).
# Se usa solo para la barra de progreso estimada; no afecta la transcripción.
_MODEL_SPEED = {
    "tiny":   10.0,
    "base":    6.0,
    "small":   3.0,
    "medium":  1.2,
}

def ensure_packages():
    missing = []
    for pkg, mod in REQUIRED.items():
        try:
            __import__(mod)
        except ImportError:
            missing.append(pkg)
    return missing

# ── Aplicación principal ─────────────────────────────────────────────
class TranscriptorApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Transcriptor de Audio — Whisper")
        self.configure(bg=BG)
        self.resizable(False, False)

        # Estado
        self.audio_path    = tk.StringVar()
        self.output_dir    = tk.StringVar(value=str(Path.home() / "Documentos"))
        self.open_folder   = tk.BooleanVar(value=True)
        self.model_choice  = tk.StringVar(value="small")
        self.status_msg    = tk.StringVar(value="Listo")
        self.progress_var  = tk.DoubleVar(value=0)
        self._running      = False
        self._timer_active = False   # controla el tick del cronómetro

        self._build_ui()
        self._center_window(540, 490)

    # ── Layout ──────────────────────────────────────────────────────
    def _build_ui(self):
        outer = tk.Frame(self, bg=BG, padx=18, pady=5)
        outer.pack(fill="both", expand=True)

        tk.Label(outer, text="🎙  Transcriptor de Audio",
                 font=FONT_TITLE, bg=BG, fg=TEXT).pack(anchor="w", pady=(0, 12))

        # ── Archivo de audio ──
        self._section(outer, "Archivo de audio")
        row_audio = tk.Frame(outer, bg=BG)
        row_audio.pack(fill="x", pady=(2, 8))
        self.lbl_audio = tk.Entry(row_audio, textvariable=self.audio_path,
                                  font=FONT_MAIN, fg=SUBTEXT, bg=PANEL,
                                  relief="flat", bd=0,
                                  highlightthickness=1, highlightbackground=BORDER,
                                  highlightcolor=ACCENT, state="readonly")
        self.lbl_audio.pack(side="left", fill="x", expand=True, ipady=6, padx=(0, 6))
        self._btn(row_audio, "Seleccionar…", self._pick_audio).pack(side="left")

        # ── Carpeta de destino ──
        self._section(outer, "Carpeta de destino")
        row_out = tk.Frame(outer, bg=BG)
        row_out.pack(fill="x", pady=(2, 4))
        tk.Entry(row_out, textvariable=self.output_dir,
                 font=FONT_MAIN, fg=TEXT, bg=PANEL,
                 relief="flat", bd=0,
                 highlightthickness=1, highlightbackground=BORDER,
                 highlightcolor=ACCENT).pack(side="left", fill="x", expand=True,
                                              ipady=6, padx=(0, 6))
        self._btn(row_out, "Cambiar…", self._pick_folder).pack(side="left")

        ck = tk.Checkbutton(outer, text="Abrir la carpeta al finalizar",
                            variable=self.open_folder,
                            font=FONT_MAIN, bg=BG, fg=TEXT,
                            activebackground=BG, selectcolor=PANEL,
                            relief="flat", cursor="hand2")
        ck.pack(anchor="w", pady=(2, 10))

        # ── Modelo ──
        self._section(outer, "Modelo Whisper")
        model_frame = tk.Frame(outer, bg=BG)
        model_frame.pack(fill="x", pady=(2, 10))
        models = [
            ("tiny",   "Tiny  — más rápido, menos preciso"),
            ("base",   "Base  — equilibrado"),
            ("small",  "Small — recomendado ★"),
            ("medium", "Medium — más preciso, más lento"),
        ]
        for i, (val, label) in enumerate(models):
            rb = tk.Radiobutton(model_frame, text=label, variable=self.model_choice,
                                value=val, font=FONT_MAIN, bg=BG, fg=TEXT,
                                activebackground=BG, selectcolor=PANEL,
                                relief="flat", cursor="hand2")
            rb.grid(row=i // 2, column=i % 2, sticky="w", padx=(0, 20), pady=1)

        # ── Barra de progreso ──
        self.progress = ttk.Progressbar(outer, variable=self.progress_var,
                                        maximum=100, mode="determinate",
                                        length=504)
        style = ttk.Style()
        style.theme_use("default")
        style.configure("TProgressbar", troughcolor=PROG_BG,
                        background=ACCENT, thickness=8)
        self.progress.pack(fill="x", pady=(0, 4))

        # ── Estado ──
        self.lbl_status = tk.Label(outer, textvariable=self.status_msg,
                                   font=FONT_MAIN, bg=BG, fg=SUBTEXT,
                                   anchor="w")
        self.lbl_status.pack(fill="x", pady=(0, 10))

        # ── Botón principal ──
        self.btn_run = self._btn(outer, "▶  Transcribir", self._start,
                                 big=True, accent=True)
        self.btn_run.pack(fill="x", ipady=8)

        tk.Label(outer, text="Procesado 100 % local · sin conexión a internet",
                 font=FONT_SMALL, bg=BG, fg=SUBTEXT).pack(pady=(8, 4))

    # ── Helpers UI ──────────────────────────────────────────────────
    def _section(self, parent, text):
        f = tk.Frame(parent, bg=BG)
        f.pack(fill="x", pady=(4, 0))
        tk.Label(f, text=text, font=FONT_BOLD, bg=BG, fg=TEXT).pack(side="left")
        tk.Frame(f, bg=BORDER, height=1).pack(side="left", fill="x",
                                               expand=True, padx=(8, 0), pady=6)

    def _btn(self, parent, text, cmd, big=False, accent=False):
        bg  = ACCENT     if accent else PANEL
        fg  = "#FFFFFF"  if accent else TEXT
        hov = ACCENT_HOV if accent else "#EFEFEF"
        fnt = ("Segoe UI", 11, "bold") if big else FONT_MAIN
        b = tk.Label(parent, text=text, font=fnt,
                     bg=bg, fg=fg, cursor="hand2",
                     padx=14, pady=4,
                     relief="flat", bd=0,
                     highlightthickness=1,
                     highlightbackground=ACCENT if accent else BORDER)
        b.bind("<Button-1>", lambda e: cmd())
        b.bind("<Enter>",    lambda e: b.configure(bg=hov))
        b.bind("<Leave>",    lambda e: b.configure(bg=bg))
        return b

    def _center_window(self, w, h):
        self.update_idletasks()
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        x  = (sw - w) // 2
        self.geometry(f"{w}x{h}+{x}+5")

    # ── Acciones ────────────────────────────────────────────────────
    def _pick_audio(self):
        path = filedialog.askopenfilename(
            title="Seleccionar archivo de audio",
            filetypes=[
                ("Archivos de audio", "*.mp3 *.m4a *.wav *.ogg *.flac *.aac *.wma"),
                ("Todos los archivos", "*.*"),
            ]
        )
        if path:
            self.audio_path.set(path)
            self._set_status("Archivo seleccionado.", SUBTEXT)

    def _pick_folder(self):
        folder = filedialog.askdirectory(title="Seleccionar carpeta de destino")
        if folder:
            self.output_dir.set(folder)

    def _set_status(self, msg, color=SUBTEXT):
        self.status_msg.set(msg)
        self.lbl_status.configure(fg=color)

    # ── Progreso ─────────────────────────────────────────────────────
    def _update_progress(self, pct):
        self.progress_var.set(pct)

    def _start_timer(self, start_time, total_secs, speed_ratio):
        """Tick cada segundo: actualiza el cronómetro y la barra de progreso estimada."""
        import time
        if not self._timer_active:
            return
        elapsed = time.time() - start_time
        elapsed_int = int(elapsed)
        em, es = divmod(elapsed_int, 60)

        # Duración del audio en formato legible
        am, a_s = divmod(int(total_secs), 60)

        # Estimación de progreso basada en velocidad típica del modelo
        expected_secs = total_secs / speed_ratio
        pct = min(elapsed / expected_secs * 95, 95)   # tope en 95% hasta terminar
        self._update_progress(pct)

        self._set_status(
            f"Transcribiendo…  ⏱ {em}m {es:02d}s transcurridos  "
            f"(audio: {am}m {a_s:02d}s)",
            ACCENT
        )
        self.after(1000, lambda: self._start_timer(start_time, total_secs, speed_ratio))

    # ── Transcripción ────────────────────────────────────────────────
    def _start(self):
        if self._running:
            return

        audio = self.audio_path.get().strip()
        if not audio or not os.path.isfile(audio):
            messagebox.showwarning("Sin archivo",
                                   "Por favor selecciona un archivo de audio primero.")
            return
        out_dir = self.output_dir.get().strip()
        if not out_dir:
            messagebox.showwarning("Sin carpeta",
                                   "Por favor elige una carpeta de destino.")
            return
        os.makedirs(out_dir, exist_ok=True)

        missing = ensure_packages()
        if missing:
            if messagebox.askyesno("Instalar dependencias",
                                   f"Faltan paquetes: {', '.join(missing)}\n"
                                   "¿Instalarlos ahora?"):
                self._install_and_run(missing, audio, out_dir)
            return

        self._run_transcription(audio, out_dir)

    def _install_and_run(self, pkgs, audio, out_dir):
        self._set_status("Instalando dependencias…", WARN)
        self.progress.configure(mode="indeterminate")
        self.progress.start(12)

        def worker():
            try:
                for pkg in pkgs:
                    subprocess.check_call(
                        [sys.executable, "-m", "pip", "install", pkg],
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
                    )
                self.after(0, lambda: self._run_transcription(audio, out_dir))
            except Exception as e:
                self.after(0, lambda: self._on_error(str(e)))
        threading.Thread(target=worker, daemon=True).start()

    def _run_transcription(self, audio, out_dir):
        import time

        self._running      = True
        self._timer_active = False
        self.btn_run.configure(fg="#AAAAAA", cursor="arrow")
        self.progress_var.set(0)
        self._set_status("Cargando modelo Whisper…", ACCENT)

        model_name  = self.model_choice.get()
        speed_ratio = _MODEL_SPEED.get(model_name, 3.0)

        def worker():
            try:
                import io
                if sys.stdout is None:
                    sys.stdout = io.StringIO()
                if sys.stderr is None:
                    sys.stderr = io.StringIO()

                # Forzar CPU y limitar threads ANTES de que torch se inicialice,
                # para evitar que se quede bloqueado detectando GPU o configurando CUDA
                os.environ.setdefault("CUDA_VISIBLE_DEVICES", "")
                import torch
                torch.set_num_threads(4)
                torch.set_num_interop_threads(1)

                import whisper

                # Obtener duración del audio sin cargar todo el array en memoria
                self.after(0, lambda: self._set_status(
                    "Analizando audio…", ACCENT))
                try:
                    # ffprobe es lo más ligero para obtener la duración
                    probe = subprocess.run(
                        ["ffprobe", "-v", "error", "-show_entries",
                         "format=duration", "-of", "default=noprint_wrappers=1:nokey=1",
                         audio],
                        capture_output=True, text=True, timeout=30
                    )
                    total_secs = float(probe.stdout.strip())
                except Exception:
                    # Fallback: carga rápida solo para medir duración
                    _arr = whisper.load_audio(audio)
                    total_secs = len(_arr) / whisper.audio.SAMPLE_RATE
                    del _arr  # liberar memoria inmediatamente

                # Carpeta de modelos: primero junto al script (útil en USB),
                # si no existe se usa la caché estándar del usuario.
                _local_models = os.path.join(_SCRIPT_DIR, "whisper_models")
                _model_files = {
                    "tiny":   "tiny.pt",
                    "base":   "base.pt",
                    "small":  "small.pt",
                    "medium": "medium.pt",
                }
                _local_file  = os.path.join(_local_models, _model_files.get(model_name, ""))
                _cache_dir   = os.path.join(os.path.expanduser("~"), ".cache", "whisper")
                _cache_file  = os.path.join(_cache_dir, _model_files.get(model_name, ""))

                if os.path.isfile(_local_file):
                    _download_root = _local_models
                    self.after(0, lambda: self._set_status(
                        f"Cargando modelo '{model_name}' desde el USB…", ACCENT))
                elif os.path.isfile(_cache_file):
                    _download_root = _cache_dir
                    self.after(0, lambda: self._set_status(
                        f"Cargando modelo '{model_name}' desde disco…", ACCENT))
                else:
                    # No está en ningún sitio: descargarlo junto al script
                    os.makedirs(_local_models, exist_ok=True)
                    _download_root = _local_models
                    _sizes = {"tiny": "~75 MB", "base": "~145 MB",
                              "small": "~460 MB", "medium": "~1,5 GB"}
                    _sz = _sizes.get(model_name, "")
                    self.after(0, lambda sz=_sz: self._set_status(
                        f"Descargando modelo '{model_name}' ({sz}) — puede tardar varios minutos…", WARN))

                model = whisper.load_model(model_name, download_root=_download_root,
                                           device="cpu")

                self.after(0, lambda: self._set_status(
                    f"Modelo '{model_name}' listo. Iniciando transcripción…", ACCENT))

                # Arrancar cronómetro
                start_time = time.time()
                self._timer_active = True
                self.after(1000, lambda: self._start_timer(
                    start_time, total_secs, speed_ratio))

                # condition_on_previous_text=False evita que Whisper entre en bucle
                # cuando un segmento tiene silencio o ruido (problema habitual en audios largos).
                # no_speech_threshold y compression_ratio_threshold hacen que descarte
                # segmentos sin voz en lugar de quedarse intentando transcribirlos.
                result = model.transcribe(
                    audio,
                    language="es",
                    verbose=None,
                    fp16=False,
                    condition_on_previous_text=False,
                    no_speech_threshold=0.6,
                    compression_ratio_threshold=2.4,
                    temperature=0.0,
                )

                # Detener cronómetro
                self._timer_active = False

                # Extraer texto
                if isinstance(result, dict):
                    text = result.get("text") or ""
                else:
                    text = str(result) if result is not None else ""
                text = text.strip()

                # Guardar resultado
                stem    = Path(audio).stem
                ts      = datetime.now().strftime("%Y%m%d_%H%M%S")
                out_txt = os.path.join(out_dir, f"{stem}_{ts}.txt")
                out_txt = os.path.normpath(out_txt)
                with open(out_txt, "w", encoding="utf-8") as fh:
                    fh.write(text if text else "(sin texto detectado)")

                self.after(0, lambda: self._on_done(out_txt))

            except Exception:
                import traceback
                self._timer_active = False
                detail = traceback.format_exc()
                self.after(0, lambda d=detail: self._on_error(d))

        threading.Thread(target=worker, daemon=True).start()

    def _on_done(self, out_path):
        self._running      = False
        self._timer_active = False
        self.progress_var.set(100)
        self._set_status(f"✔  Guardado en: {out_path}", SUCCESS)
        self.btn_run.configure(fg="#FFFFFF", cursor="hand2")

        if self.open_folder.get():
            folder = os.path.dirname(out_path)
            if sys.platform == "win32":
                os.startfile(folder)
            elif sys.platform == "darwin":
                subprocess.Popen(["open", folder])
            else:
                subprocess.Popen(["xdg-open", folder])

    def _on_error(self, msg):
        self._running      = False
        self._timer_active = False
        self.progress_var.set(0)
        self._set_status(f"✖  Error: {msg[:80]}", ERROR)
        self.btn_run.configure(fg="#FFFFFF", cursor="hand2")
        messagebox.showerror("Error en la transcripción", msg)


if __name__ == "__main__":
    app = TranscriptorApp()
    app.mainloop()
