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

AUDIO_EXTS = {".mp3", ".m4a", ".wav", ".ogg", ".flac", ".aac", ".wma"}

REQUIRED = {"openai-whisper": "whisper"}

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
os.environ["PATH"] = _SCRIPT_DIR + os.pathsep + os.environ.get("PATH", "")

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

def find_audio_files(folder):
    files = []
    for p in sorted(Path(folder).iterdir()):
        if p.is_file() and p.suffix.lower() in AUDIO_EXTS:
            files.append(str(p))
    return files


class TranscriptorLoteApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Transcriptor en Lote — Whisper")
        self.configure(bg=BG)
        self.resizable(False, False)

        self.input_dir    = tk.StringVar()
        self.output_dir   = tk.StringVar(value=str(Path.home() / "Documentos"))
        self.open_folder  = tk.BooleanVar(value=True)
        self.model_choice = tk.StringVar(value="small")
        self.language     = tk.StringVar(value="en")
        self.output_mode  = tk.StringVar(value="individual")  # "individual" | "combined"
        self.status_msg   = tk.StringVar(value="Listo")
        self.progress_var = tk.DoubleVar(value=0)
        self._running     = False

        self._build_ui()
        self._center_window(560, 640)

    def _build_ui(self):
        outer = tk.Frame(self, bg=BG, padx=18, pady=5)
        outer.pack(fill="both", expand=True)

        tk.Label(outer, text="🎙  Transcriptor en Lote",
                 font=FONT_TITLE, bg=BG, fg=TEXT).pack(anchor="w", pady=(0, 12))

        # ── Carpeta de entrada ──
        self._section(outer, "Carpeta con los audios")
        row_in = tk.Frame(outer, bg=BG)
        row_in.pack(fill="x", pady=(2, 8))
        tk.Entry(row_in, textvariable=self.input_dir,
                 font=FONT_MAIN, fg=TEXT, bg=PANEL,
                 relief="flat", bd=0,
                 highlightthickness=1, highlightbackground=BORDER,
                 highlightcolor=ACCENT).pack(side="left", fill="x", expand=True,
                                              ipady=6, padx=(0, 6))
        self._btn(row_in, "Seleccionar…", self._pick_input).pack(side="left")

        # ── Carpeta de salida ──
        self._section(outer, "Carpeta de destino")
        row_out = tk.Frame(outer, bg=BG)
        row_out.pack(fill="x", pady=(2, 4))
        tk.Entry(row_out, textvariable=self.output_dir,
                 font=FONT_MAIN, fg=TEXT, bg=PANEL,
                 relief="flat", bd=0,
                 highlightthickness=1, highlightbackground=BORDER,
                 highlightcolor=ACCENT).pack(side="left", fill="x", expand=True,
                                              ipady=6, padx=(0, 6))
        self._btn(row_out, "Cambiar…", self._pick_output).pack(side="left")

        ck = tk.Checkbutton(outer, text="Abrir la carpeta al finalizar",
                            variable=self.open_folder,
                            font=FONT_MAIN, bg=BG, fg=TEXT,
                            activebackground=BG, selectcolor=PANEL,
                            relief="flat", cursor="hand2")
        ck.pack(anchor="w", pady=(2, 10))

        # ── Idioma ──
        self._section(outer, "Idioma de los audios")
        lang_frame = tk.Frame(outer, bg=BG)
        lang_frame.pack(fill="x", pady=(2, 10))
        langs = [
            ("en", "Inglés  🇬🇧"),
            ("es", "Español 🇪🇸"),
            ("fr", "Francés 🇫🇷"),
            ("de", "Alemán  🇩🇪"),
        ]
        for i, (val, label) in enumerate(langs):
            rb = tk.Radiobutton(lang_frame, text=label, variable=self.language,
                                value=val, font=FONT_MAIN, bg=BG, fg=TEXT,
                                activebackground=BG, selectcolor=PANEL,
                                relief="flat", cursor="hand2")
            rb.grid(row=i // 2, column=i % 2, sticky="w", padx=(0, 20), pady=1)

        # ── Modo de salida ──
        self._section(outer, "Modo de salida")
        mode_frame = tk.Frame(outer, bg=BG)
        mode_frame.pack(fill="x", pady=(2, 10))
        modes = [
            ("individual", "Un .txt por audio"),
            ("combined",   "Todo en un único .txt"),
        ]
        for i, (val, label) in enumerate(modes):
            rb = tk.Radiobutton(mode_frame, text=label, variable=self.output_mode,
                                value=val, font=FONT_MAIN, bg=BG, fg=TEXT,
                                activebackground=BG, selectcolor=PANEL,
                                relief="flat", cursor="hand2")
            rb.grid(row=0, column=i, sticky="w", padx=(0, 30), pady=1)

        # ── Modelo ──
        self._section(outer, "Modelo Whisper")
        model_frame = tk.Frame(outer, bg=BG)
        model_frame.pack(fill="x", pady=(2, 10))
        models = [
            ("tiny",   "Tiny   — más rápido, menos preciso"),
            ("base",   "Base   — equilibrado"),
            ("small",  "Small  — recomendado ★"),
            ("medium", "Medium — más preciso, más lento"),
        ]
        for i, (val, label) in enumerate(models):
            rb = tk.Radiobutton(model_frame, text=label, variable=self.model_choice,
                                value=val, font=FONT_MAIN, bg=BG, fg=TEXT,
                                activebackground=BG, selectcolor=PANEL,
                                relief="flat", cursor="hand2")
            rb.grid(row=i // 2, column=i % 2, sticky="w", padx=(0, 20), pady=1)

        # ── Progreso total ──
        self._section(outer, "Progreso")
        self.lbl_counter = tk.Label(outer, text="", font=FONT_SMALL, bg=BG, fg=SUBTEXT, anchor="w")
        self.lbl_counter.pack(fill="x", pady=(2, 2))

        self.progress = ttk.Progressbar(outer, variable=self.progress_var,
                                        maximum=100, mode="determinate", length=524)
        style = ttk.Style()
        style.theme_use("default")
        style.configure("TProgressbar", troughcolor=PROG_BG, background=ACCENT, thickness=8)
        self.progress.pack(fill="x", pady=(0, 4))

        self.lbl_status = tk.Label(outer, textvariable=self.status_msg,
                                   font=FONT_MAIN, bg=BG, fg=SUBTEXT, anchor="w")
        self.lbl_status.pack(fill="x", pady=(0, 8))

        # ── Botón principal ──
        self.btn_run = self._btn(outer, "▶  Transcribir todos los audios",
                                 self._start, big=True, accent=True)
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
        x  = (sw - w) // 2
        self.geometry(f"{w}x{h}+{x}+5")

    def _pick_input(self):
        folder = filedialog.askdirectory(title="Carpeta con los audios")
        if folder:
            self.input_dir.set(folder)
            files = find_audio_files(folder)
            self._set_status(f"{len(files)} archivo(s) de audio encontrados.", SUBTEXT)

    def _pick_output(self):
        folder = filedialog.askdirectory(title="Carpeta de destino")
        if folder:
            self.output_dir.set(folder)

    def _set_status(self, msg, color=SUBTEXT):
        self.status_msg.set(msg)
        self.lbl_status.configure(fg=color)

    # ── Inicio ──────────────────────────────────────────────────────
    def _start(self):
        if self._running:
            return

        in_dir = self.input_dir.get().strip()
        if not in_dir or not os.path.isdir(in_dir):
            messagebox.showwarning("Sin carpeta", "Por favor selecciona la carpeta con los audios.")
            return

        files = find_audio_files(in_dir)
        if not files:
            messagebox.showwarning("Sin archivos", "No se encontraron archivos de audio en esa carpeta.")
            return

        out_dir = self.output_dir.get().strip()
        if not out_dir:
            messagebox.showwarning("Sin destino", "Por favor elige una carpeta de destino.")
            return
        os.makedirs(out_dir, exist_ok=True)

        missing = ensure_packages()
        if missing:
            if messagebox.askyesno("Instalar dependencias",
                                   f"Faltan paquetes: {', '.join(missing)}\n¿Instalarlos ahora?"):
                self._install_and_run(missing, files, out_dir)
            return

        self._run_batch(files, out_dir)

    def _install_and_run(self, pkgs, files, out_dir):
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
                self.progress.stop()
                self.progress.configure(mode="determinate")
                self.after(0, lambda: self._run_batch(files, out_dir))
            except Exception as e:
                self.after(0, lambda: self._on_error(str(e)))
        threading.Thread(target=worker, daemon=True).start()

    def _run_batch(self, files, out_dir):
        self._running = True
        self.btn_run.configure(fg="#AAAAAA", cursor="arrow")
        self.progress_var.set(0)
        model_name  = self.model_choice.get()
        language    = self.language.get()
        output_mode = self.output_mode.get()
        total       = len(files)

        def worker():
            try:
                import io, torch, whisper

                if sys.stdout is None: sys.stdout = io.StringIO()
                if sys.stderr is None: sys.stderr = io.StringIO()

                os.environ.setdefault("CUDA_VISIBLE_DEVICES", "")
                torch.set_num_threads(4)
                torch.set_num_interop_threads(1)

                self.after(0, lambda: self._set_status("Cargando modelo Whisper…", ACCENT))

                _local_models = os.path.join(_SCRIPT_DIR, "whisper_models")
                _model_files  = {"tiny": "tiny.pt", "base": "base.pt",
                                 "small": "small.pt", "medium": "medium.pt"}
                _local_file   = os.path.join(_local_models, _model_files.get(model_name, ""))
                _cache_dir    = os.path.join(os.path.expanduser("~"), ".cache", "whisper")
                _cache_file   = os.path.join(_cache_dir, _model_files.get(model_name, ""))

                if os.path.isfile(_local_file):
                    _download_root = _local_models
                elif os.path.isfile(_cache_file):
                    _download_root = _cache_dir
                else:
                    os.makedirs(_local_models, exist_ok=True)
                    _download_root = _local_models
                    _sizes = {"tiny": "~75 MB", "base": "~145 MB",
                              "small": "~460 MB", "medium": "~1,5 GB"}
                    sz = _sizes.get(model_name, "")
                    self.after(0, lambda s=sz: self._set_status(
                        f"Descargando modelo '{model_name}' ({s})…", WARN))

                model = whisper.load_model(model_name, download_root=_download_root, device="cpu")

                TRANSCRIBE_OPTS = dict(
                    language=language,
                    verbose=None,
                    fp16=False,
                    condition_on_previous_text=False,
                    no_speech_threshold=0.6,
                    compression_ratio_threshold=2.4,
                    temperature=0.0,
                    max_initial_timestamp=1.0,
                    beam_size=1,
                    best_of=1,
                )

                errors        = []
                combined_parts = []  # solo usado en modo combinado

                for idx, audio in enumerate(files, 1):
                    name = Path(audio).name
                    self.after(0, lambda i=idx, n=total, nm=name: (
                        self._set_status(f"Transcribiendo {i}/{n}: {nm}", ACCENT),
                        self.lbl_counter.configure(
                            text=f"Archivo {i} de {n}  —  {nm}")
                    ))

                    try:
                        result = model.transcribe(audio, **TRANSCRIBE_OPTS)
                        text   = result.get("text", "").strip() if isinstance(result, dict) else str(result).strip()
                        if not text:
                            text = "(no speech detected)"

                        if output_mode == "individual":
                            stem    = Path(audio).stem
                            out_txt = os.path.join(out_dir, f"{stem}.txt")
                            with open(out_txt, "w", encoding="utf-8") as fh:
                                fh.write(text)
                        else:
                            # Acumular con cabecera de nombre de archivo
                            combined_parts.append(f"=== {Path(audio).name} ===\n{text}")

                    except Exception as e:
                        errors.append(f"{name}: {e}")

                    pct = idx / total * 100
                    self.after(0, lambda p=pct: self.progress_var.set(p))

                # Guardar archivo combinado si corresponde
                if output_mode == "combined" and combined_parts:
                    ts       = datetime.now().strftime("%Y%m%d_%H%M%S")
                    out_txt  = os.path.join(out_dir, f"transcripcion_completa_{ts}.txt")
                    with open(out_txt, "w", encoding="utf-8") as fh:
                        fh.write("\n\n".join(combined_parts))

                self.after(0, lambda: self._on_done(out_dir, total, errors))

            except Exception:
                import traceback
                self.after(0, lambda d=traceback.format_exc(): self._on_error(d))

        threading.Thread(target=worker, daemon=True).start()

    def _on_done(self, out_dir, total, errors):
        self._running = False
        self.btn_run.configure(fg="#FFFFFF", cursor="hand2")
        self.progress_var.set(100)

        if errors:
            msg = f"✔  {total - len(errors)}/{total} transcritos. Errores: {len(errors)}"
            self._set_status(msg, WARN)
            self.lbl_counter.configure(text="\n".join(errors[:5]))
        else:
            self._set_status(f"✔  {total} archivo(s) transcritos en: {out_dir}", SUCCESS)
            self.lbl_counter.configure(text="¡Todo completado sin errores!")

        if self.open_folder.get():
            if sys.platform == "win32":
                os.startfile(out_dir)
            elif sys.platform == "darwin":
                subprocess.Popen(["open", out_dir])
            else:
                subprocess.Popen(["xdg-open", out_dir])

    def _on_error(self, msg):
        self._running = False
        self.btn_run.configure(fg="#FFFFFF", cursor="hand2")
        self.progress_var.set(0)
        self._set_status(f"✖  Error: {msg[:80]}", ERROR)
        messagebox.showerror("Error", msg)


if __name__ == "__main__":
    app = TranscriptorLoteApp()
    app.mainloop()
