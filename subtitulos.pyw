# SubtitleGen  — subtitulos.pyw
# Requiere: pip install openai-whisper   |   ffmpeg en el PATH del sistema o junto al .pyw
# ─────────────────────────────────────────────────────────────────────────────

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, colorchooser
import threading
import subprocess
import os
import sys

# Añadir la carpeta del propio script al PATH para que ffmpeg se encuentre
# aunque no esté instalado en el sistema (ej. entorno portable en USB)
_script_dir = os.path.dirname(os.path.abspath(__file__))
if _script_dir not in os.environ.get("PATH", "").split(os.pathsep):
    os.environ["PATH"] = _script_dir + os.pathsep + os.environ.get("PATH", "")

# ── Paleta ────────────────────────────────────────────────────────────────────
BG        = "#cfd3dc"   # gris azulado medio
BG2       = "#b8bdc9"   # sección más oscura
BG3       = "#dde1e8"   # frames internos / entries
FG        = "#1c2030"
FG2       = "#444c60"
ACCENT    = "#3a5a8c"
ACCENT_LT = "#5a80b8"
BTN_BG    = "#3a5a8c"
BTN_FG    = "#f0f4ff"
SEP_CLR   = "#9aa1b3"
LOG_BG    = "#1a1e2b"
LOG_FG    = "#7ec98a"
# ──────────────────────────────────────────────────────────────────────────────

LANGUAGES = {
    "Auto-detectar": None,
    "English":        "en",
    "Español":        "es",
    "Português":      "pt",
    "Deutsch":        "de",
    "Français":       "fr",
    "Italiano":       "it",
    "العربية":        "ar",
    "Українська":     "uk",
    "Русский":        "ru",
    "中文":            "zh",
    "日本語":          "ja",
    "한국어":          "ko",
    "Polski":         "pl",
    "Nederlands":     "nl",
    "Türkçe":         "tr",
    "हिन्दी":         "hi",
}

MODELS = ["tiny", "base", "small", "medium", "large", "large-v2", "large-v3"]
POSITIONS = {"Abajo": 2, "Centro": 5, "Arriba": 8}
WIN_W = 620


# ══════════════════════════════════════════════════════════════════════════════
class SubtitleGen:

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("SubtitleGen ~ Generación e Incrustación de Subtítulos")
        self.root.configure(bg=BG)
        self.root.resizable(True, False)

        # ── Variables ────────────────────────────────────────────────────────
        self.video_path    = tk.StringVar()
        self.srt_path      = tk.StringVar()
        self.output_folder = tk.StringVar()
        self.out_name      = tk.StringVar()
        self.language      = tk.StringVar(value="Auto-detectar")
        self.model         = tk.StringVar(value="small")
        self.font_size     = tk.IntVar(value=24)
        self.font_color    = tk.StringVar(value="#FFFFFF")
        self.position      = tk.StringVar(value="Abajo")
        self.open_folder        = tk.BooleanVar(value=True)
        self.max_seg_duration   = tk.DoubleVar(value=4.0)
        self._busy              = False

        self._build_ui()
        self.root.update_idletasks()
        self._place_window()

    # ── Layout ────────────────────────────────────────────────────────────────

    def _place_window(self):
        sw = self.root.winfo_screenwidth()
        self.root.geometry(f"{WIN_W}x{self.root.winfo_height()}+{(sw - WIN_W) // 2}+5")

    def _build_ui(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TCombobox",
                        fieldbackground=BG3, background=BG3,
                        foreground=FG, selectbackground=ACCENT,
                        selectforeground=BTN_FG)
        style.configure("Horizontal.TProgressbar",
                        troughcolor=BG2, background=ACCENT, thickness=6)
        style.configure("TSeparator", background=SEP_CLR)

        outer = tk.Frame(self.root, bg=BG, padx=14, pady=10)
        outer.pack(fill=tk.BOTH, expand=True)

        # Título
        hdr = tk.Frame(outer, bg=ACCENT, pady=7, padx=12)
        hdr.pack(fill=tk.X, pady=(0, 10))
        tk.Label(hdr, text="🎬  SubtitleGen",
                 font=("Segoe UI", 14, "bold"),
                 bg=ACCENT, fg=BTN_FG).pack(side=tk.LEFT)
        tk.Label(hdr, text="Whisper + FFmpeg",
                 font=("Segoe UI", 8),
                 bg=ACCENT, fg="#a8c4f0").pack(side=tk.RIGHT, padx=4)

        # ── Sección 1 : Vídeo de entrada ─────────────────────────────────────
        self._section(outer, "📂  Vídeo de entrada")
        self._file_row(outer, self.video_path, "Examinar…",
                       self._browse_video,
                       ftype=[("Vídeo", "*.mp4 *.mkv *.avi *.mov *.webm *.flv *.wmv *.ts"),
                               ("Todos", "*.*")])

        # ── Sección 2 : Generar .srt ─────────────────────────────────────────
        self._section(outer, "🗣️  Generar subtítulos (.srt) con Whisper")

        # Opciones Whisper
        row_w = tk.Frame(outer, bg=BG)
        row_w.pack(fill=tk.X, pady=3)
        self._lbl(row_w, "Idioma:", side=tk.LEFT)
        lang_cb = ttk.Combobox(row_w, textvariable=self.language,
                               values=list(LANGUAGES.keys()),
                               state="readonly", width=16)
        lang_cb.pack(side=tk.LEFT, padx=(2, 14))
        self._lbl(row_w, "Modelo:", side=tk.LEFT)
        ttk.Combobox(row_w, textvariable=self.model,
                     values=MODELS, state="readonly", width=10).pack(side=tk.LEFT, padx=2)

        # Duración máxima por segmento
        row_d = tk.Frame(outer, bg=BG)
        row_d.pack(fill=tk.X, pady=3)
        self._lbl(row_d, "Duración máx. segmento (s):", side=tk.LEFT)
        tk.Spinbox(row_d, from_=1.0, to=15.0, increment=0.25,
                   textvariable=self.max_seg_duration,
                   format="%.1f", width=5,
                   bg=BG3, fg=FG, relief=tk.FLAT,
                   font=("Segoe UI", 9),
                   buttonbackground=BG2).pack(side=tk.LEFT, padx=(3, 10))
        tk.Label(row_d, text="(2.5-4 canción / 4-5 diálogo / 5-6 documental)",
                 bg=BG, fg=FG2, font=("Segoe UI", 8)).pack(side=tk.LEFT)

        # Ruta del .srt
        srt_row = tk.Frame(outer, bg=BG)
        srt_row.pack(fill=tk.X, pady=3)
        self._lbl(srt_row, "Archivo .srt:", side=tk.LEFT)
        tk.Entry(srt_row, textvariable=self.srt_path,
                 bg=BG3, fg=FG, relief=tk.FLAT,
                 font=("Segoe UI", 9)).pack(side=tk.LEFT, fill=tk.X,
                                             expand=True, ipady=3, padx=(4, 4))
        self._btn(srt_row, "Elegir .srt",
                  self._browse_srt).pack(side=tk.RIGHT)

        self._big_btn(outer, "⚡  Generar .srt desde el vídeo",
                      self._start_generate)

        # ── Sección 3 : Incrustar ────────────────────────────────────────────
        self._section(outer, "🔥  Incrustar subtítulos en el vídeo")

        # Estilo de subtítulos
        sty = tk.Frame(outer, bg=BG2, padx=10, pady=8)
        sty.pack(fill=tk.X, pady=3)

        # Fila 1 : tamaño + posición
        r1 = tk.Frame(sty, bg=BG2)
        r1.pack(fill=tk.X, pady=2)
        self._lbl(r1, "Tamaño fuente:", side=tk.LEFT, parent_bg=BG2)
        tk.Spinbox(r1, from_=8, to=96, textvariable=self.font_size,
                   width=5, bg=BG3, fg=FG, relief=tk.FLAT,
                   font=("Segoe UI", 9), buttonbackground=BG2).pack(side=tk.LEFT, padx=(3, 16))
        self._lbl(r1, "Posición:", side=tk.LEFT, parent_bg=BG2)
        ttk.Combobox(r1, textvariable=self.position,
                     values=list(POSITIONS.keys()),
                     state="readonly", width=9).pack(side=tk.LEFT, padx=3)

        # Fila 2 : color
        r2 = tk.Frame(sty, bg=BG2)
        r2.pack(fill=tk.X, pady=(4, 0))
        self._lbl(r2, "Color texto:", side=tk.LEFT, parent_bg=BG2)
        self.color_swatch = tk.Label(r2, bg=self.font_color.get(),
                                     width=4, height=1,
                                     relief=tk.RIDGE, cursor="hand2",
                                     bd=1)
        self.color_swatch.pack(side=tk.LEFT, padx=(3, 4))
        self.color_swatch.bind("<Button-1>", self._pick_color)
        self._lbl(r2, "►", side=tk.LEFT, parent_bg=BG2)
        tk.Label(r2, textvariable=self.font_color,
                 bg=BG2, fg=ACCENT,
                 font=("Courier", 9, "bold")).pack(side=tk.LEFT, padx=3)
        tk.Label(r2, text="(clic en el cuadro para cambiar)",
                 bg=BG2, fg=FG2, font=("Segoe UI", 8)).pack(side=tk.LEFT, padx=6)

        # Carpeta de salida
        out_row = tk.Frame(outer, bg=BG)
        out_row.pack(fill=tk.X, pady=3)
        self._lbl(out_row, "Carpeta salida:", side=tk.LEFT)
        tk.Entry(out_row, textvariable=self.output_folder,
                 bg=BG3, fg=FG, relief=tk.FLAT,
                 font=("Segoe UI", 9)).pack(side=tk.LEFT, fill=tk.X,
                                             expand=True, ipady=3, padx=(4, 4))
        self._btn(out_row, "Elegir…", self._browse_output).pack(side=tk.RIGHT)

        # Nombre del fichero de salida
        nm_row = tk.Frame(outer, bg=BG)
        nm_row.pack(fill=tk.X, pady=3)
        self._lbl(nm_row, "Nombre vídeo:", side=tk.LEFT)
        tk.Entry(nm_row, textvariable=self.out_name,
                 bg=BG3, fg=FG, relief=tk.FLAT,
                 font=("Segoe UI", 9)).pack(side=tk.LEFT, fill=tk.X,
                                             expand=True, ipady=3, padx=(4, 0))

        # Opción abrir carpeta
        tk.Checkbutton(outer,
                       text="Abrir carpeta de salida al terminar",
                       variable=self.open_folder,
                       bg=BG, fg=FG2,
                       selectcolor=BG2,
                       activebackground=BG,
                       font=("Segoe UI", 9)).pack(anchor=tk.W, pady=(4, 0))

        self._big_btn(outer, "🎬  Incrustar subtítulos en el vídeo",
                      self._start_burn)

        # ── Log ──────────────────────────────────────────────────────────────
        self._section(outer, "📋  Log")

        log_wrap = tk.Frame(outer, bg=LOG_BG, bd=1, relief=tk.FLAT)
        log_wrap.pack(fill=tk.BOTH, expand=True, pady=(2, 4))

        self.log = tk.Text(log_wrap, height=7,
                           bg=LOG_BG, fg=LOG_FG,
                           font=("Consolas", 8),
                           relief=tk.FLAT, wrap=tk.WORD,
                           insertbackground=LOG_FG)
        sb = tk.Scrollbar(log_wrap, command=self.log.yview,
                          troughcolor=LOG_BG, bg=BG2)
        self.log.configure(yscrollcommand=sb.set)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        self.log.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

        # Barra de progreso + estado
        self.pbar = ttk.Progressbar(outer, mode="indeterminate",
                                    style="Horizontal.TProgressbar")
        self.pbar.pack(fill=tk.X, pady=(0, 2))

        self.status_var = tk.StringVar(value="Listo.")
        tk.Label(outer, textvariable=self.status_var,
                 bg=BG, fg=ACCENT,
                 font=("Segoe UI", 8, "italic"),
                 anchor=tk.W).pack(fill=tk.X)

        # Mensaje inicial
        self._log("SubtitleGen iniciado.")
        self._log("Dependencias necesarias:")
        self._log("  • Python: pip install openai-whisper")
        self._log("  • Sistema: ffmpeg  (https://ffmpeg.org/download.html)")

    # ── Helpers de construcción ───────────────────────────────────────────────

    def _section(self, parent, title):
        f = tk.Frame(parent, bg=BG)
        f.pack(fill=tk.X, pady=(9, 2))
        tk.Label(f, text=title, font=("Segoe UI", 9, "bold"),
                 bg=BG, fg=ACCENT).pack(side=tk.LEFT)
        tk.Frame(f, bg=SEP_CLR, height=1).pack(
            side=tk.LEFT, fill=tk.X, expand=True, padx=(8, 0), pady=6)

    def _lbl(self, parent, text, side=tk.LEFT, parent_bg=None):
        tk.Label(parent, text=text,
                 bg=parent_bg or BG, fg=FG2,
                 font=("Segoe UI", 9)).pack(side=side)

    def _btn(self, parent, text, cmd):
        return tk.Button(parent, text=text, command=cmd,
                         bg=BTN_BG, fg=BTN_FG,
                         font=("Segoe UI", 8, "bold"),
                         relief=tk.FLAT, cursor="hand2",
                         activebackground=ACCENT_LT,
                         activeforeground=BTN_FG,
                         padx=8, pady=3)

    def _big_btn(self, parent, text, cmd):
        tk.Button(parent, text=text, command=cmd,
                  bg=ACCENT, fg=BTN_FG,
                  font=("Segoe UI", 10, "bold"),
                  relief=tk.FLAT, cursor="hand2",
                  activebackground=ACCENT_LT,
                  activeforeground=BTN_FG,
                  pady=6).pack(fill=tk.X, pady=5)

    def _file_row(self, parent, var, btn_txt, cmd, ftype=None):
        f = tk.Frame(parent, bg=BG)
        f.pack(fill=tk.X, pady=3)
        tk.Entry(f, textvariable=var, bg=BG3, fg=FG,
                 relief=tk.FLAT, font=("Segoe UI", 9)).pack(
            side=tk.LEFT, fill=tk.X, expand=True, ipady=3, padx=(0, 4))
        self._btn(f, btn_txt, cmd).pack(side=tk.RIGHT)

    # ── Callbacks UI ─────────────────────────────────────────────────────────

    def _browse_video(self):
        p = filedialog.askopenfilename(
            title="Seleccionar vídeo",
            filetypes=[("Vídeo", "*.mp4 *.mkv *.avi *.mov *.webm *.flv *.wmv *.ts"),
                       ("Todos", "*.*")])
        if p:
            self.video_path.set(p)
            base = os.path.splitext(p)[0]
            if not self.srt_path.get():
                self.srt_path.set(base + ".srt")
            if not self.output_folder.get():
                self.output_folder.set(os.path.dirname(p))
            if not self.out_name.get():
                self.out_name.set(
                    os.path.splitext(os.path.basename(p))[0] + "_subtitled.mp4")

    def _browse_srt(self):
        p = filedialog.askopenfilename(
            title="Seleccionar archivo .srt",
            filetypes=[("SubRip", "*.srt"), ("Todos", "*.*")])
        if p:
            self.srt_path.set(p)

    def _browse_output(self):
        d = filedialog.askdirectory(title="Carpeta de salida")
        if d:
            self.output_folder.set(d)

    def _pick_color(self, _event=None):
        result = colorchooser.askcolor(
            color=self.font_color.get(), title="Color del texto")
        if result and result[1]:
            hex_c = result[1].upper()
            self.font_color.set(hex_c)
            self.color_swatch.configure(bg=hex_c)

    # ── Log / status ─────────────────────────────────────────────────────────

    def _log(self, msg: str):
        self.log.insert(tk.END, msg + "\n")
        self.log.see(tk.END)
        self.root.update_idletasks()

    def _status(self, msg: str):
        self.status_var.set(msg)
        self.root.update_idletasks()

    # ── Guardianes ───────────────────────────────────────────────────────────

    def _guard(self, checks: list) -> bool:
        """Valida condiciones; muestra aviso y retorna False si alguna falla."""
        for ok, msg in checks:
            if not ok:
                messagebox.showwarning("Atención", msg)
                return False
        return True

    # ── Generar .srt ─────────────────────────────────────────────────────────

    def _start_generate(self):
        if self._busy:
            return
        if not self._guard([
            (bool(self.video_path.get()), "Selecciona un vídeo primero."),
            (bool(self.srt_path.get()),   "Indica la ruta del archivo .srt."),
        ]):
            return
        self._busy = True
        threading.Thread(target=self._generate_thread, daemon=True).start()

    def _generate_thread(self):
        self.pbar.start(10)
        self._status("Cargando modelo Whisper…")
        try:
            import whisper
        except ImportError:
            self._log("❌  openai-whisper no instalado.")
            self._log("    Ejecuta:  pip install openai-whisper")
            messagebox.showerror("Error", "openai-whisper no está instalado.\n"
                                          "Ejecuta:  pip install openai-whisper")
            self.pbar.stop(); self._busy = False; return

        video     = self.video_path.get()
        srt_out   = self.srt_path.get()
        lang_code = LANGUAGES.get(self.language.get())
        model_id  = self.model.get()

        try:
            # En .pyw no hay consola → sys.stderr/stdout son None.
            # Whisper (especialmente medium/large) escribe en ellos aunque
            # verbose=False, lo que produce 'NoneType has no attribute write'.
            import io
            _real_stderr = sys.stderr
            _real_stdout = sys.stdout
            if sys.stderr is None:
                sys.stderr = io.StringIO()
            if sys.stdout is None:
                sys.stdout = io.StringIO()

            self._log(f"▶  Cargando modelo '{model_id}'…")
            model = whisper.load_model(model_id)
            self._log(f"▶  Transcribiendo: {os.path.basename(video)}")
            self._status("Transcribiendo vídeo… (puede tardar)")

            kwargs = {"verbose": False, "fp16": False, "word_timestamps": True}
            if lang_code:
                kwargs["language"] = lang_code

            result = model.transcribe(video, **kwargs)

            # Restaurar streams originales
            sys.stderr = _real_stderr
            sys.stdout = _real_stdout

            max_dur = self.max_seg_duration.get()
            segs = self._split_segments(result["segments"], max_dur)

            self._log(f"▶  Guardando .srt → {srt_out}")
            self._write_srt(segs, srt_out)
            self._log(f"✅  .srt generado con {len(segs)} segmentos.")
            self._status("✅  .srt generado correctamente")
            messagebox.showinfo("Éxito", f"Subtítulos generados:\n{srt_out}")

        except Exception as exc:
            # Restaurar streams por si el error ocurrió durante la transcripción
            try:
                sys.stderr = _real_stderr
                sys.stdout = _real_stdout
            except UnboundLocalError:
                pass
            self._log(f"❌  {exc}")
            self._status("❌  Error al generar .srt")
            messagebox.showerror("Error", str(exc))
        finally:
            self.pbar.stop()
            self._busy = False

    @staticmethod
    def _split_segments(segments, max_dur: float) -> list:
        """
        Divide los segmentos de Whisper usando timestamps por palabra.
        Respeta las pausas naturales del audio: solo corta entre palabras
        y preferiblemente donde hay una pausa mayor.
        """
        out = []
        for seg in segments:
            words = seg.get("words", [])
            if not words:
                # Sin timestamps de palabra → segmento tal cual
                out.append({"start": seg["start"], "end": seg["end"],
                             "text": seg["text"].strip()})
                continue

            chunk_words  = []
            chunk_start  = words[0]["start"]

            for i, w in enumerate(words):
                chunk_words.append(w["word"])
                chunk_end = w["end"]
                duration  = chunk_end - chunk_start

                # Calculamos el hueco hasta la siguiente palabra
                next_gap = (words[i + 1]["start"] - chunk_end if i + 1 < len(words) else 0.0)

                # --- NUEVA LÓGICA DE CORTE ---
                is_last = (i == len(words) - 1)
                
                # Condición 1: Se pasó del tiempo máximo (Corte forzado)
                # Condición 2: Hay una pausa decente (Corte natural)
                if (duration >= max_dur) or (next_gap >= 0.15):
                    out.append({
                        "start": chunk_start, 
                        "end": chunk_end,
                        "text": "".join(chunk_words).strip()
                    })
                    if not is_last:
                        chunk_start = words[i + 1]["start"]
                        chunk_words = []

            # Volcar resto del segmento
            if chunk_words:
                out.append({"start": chunk_start, "end": words[-1]["end"],
                            "text": "".join(chunk_words).strip()})
        return out

    @staticmethod
    def _write_srt(segments, path: str):
        def t(sec):
            h, rem = divmod(int(sec), 3600)
            m, s   = divmod(rem, 60)
            ms     = int((sec - int(sec)) * 1000)
            return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"
        with open(path, "w", encoding="utf-8") as f:
            for i, seg in enumerate(segments, 1):
                f.write(f"{i}\n{t(seg['start'])} --> {t(seg['end'])}\n"
                        f"{seg['text'].strip()}\n\n")

    # ── Incrustar subtítulos ──────────────────────────────────────────────────

    def _start_burn(self):
        if self._busy:
            return
        srt = self.srt_path.get()
        if not self._guard([
            (bool(self.video_path.get()),             "Selecciona un vídeo primero."),
            (bool(srt),                               "Indica la ruta del archivo .srt."),
            (os.path.isfile(srt),                     f"El archivo .srt no existe:\n{srt}"),
            (bool(self.output_folder.get()),          "Selecciona la carpeta de salida."),
            (bool(self.out_name.get()),               "Indica el nombre del vídeo de salida."),
        ]):
            return
        self._busy = True
        threading.Thread(target=self._burn_thread, daemon=True).start()

    @staticmethod
    def _hex_to_ass(hex_color: str) -> str:
        """#RRGGBB → &H00BBGGRR  (formato ASS/FFmpeg)"""
        h = hex_color.lstrip("#")
        r, g, b = h[0:2], h[2:4], h[4:6]
        return f"&H00{b}{g}{r}"

    @staticmethod
    def _escape_srt_path(path: str) -> str:
        """Escapa la ruta del .srt para el filtro subtitles de FFmpeg."""
        # En Windows: C:\ruta → C\:/ruta  (escapar la barra y los dos puntos)
        p = path.replace("\\", "/")
        # Escapar el ':' del drive de Windows
        if len(p) >= 2 and p[1] == ":":
            p = p[0] + "\\:" + p[2:]
        # Escapar posibles comillas simples
        p = p.replace("'", "\\'")
        return p

    def _burn_thread(self):
        self.pbar.start(10)
        self._status("Incrustando subtítulos con FFmpeg…")

        video   = self.video_path.get()
        srt     = self.srt_path.get()
        folder  = self.output_folder.get()
        out     = os.path.join(folder, self.out_name.get())

        font_size  = self.font_size.get()
        ass_color  = self._hex_to_ass(self.font_color.get())
        alignment  = POSITIONS.get(self.position.get(), 2)
        srt_esc    = self._escape_srt_path(srt)

        force_style = (
            f"FontSize={font_size},"
            f"PrimaryColour={ass_color},"
            f"Alignment={alignment},"
            f"BorderStyle=1,Outline=1,Shadow=0,"
            f"Bold=0,MarginV=20"
        )

        cmd = [
            "ffmpeg", "-y",
            "-i", video,
            "-vf", f"subtitles='{srt_esc}':force_style='{force_style}'",
            "-c:a", "copy",
            out,
        ]

        self._log("▶  Ejecutando FFmpeg…")
        self._log(f"   Salida → {out}")

        try:
            kwargs_popen = dict(
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                errors="replace",
            )
            if sys.platform == "win32":
                kwargs_popen["creationflags"] = subprocess.CREATE_NO_WINDOW

            proc = subprocess.Popen(cmd, **kwargs_popen)
            for line in proc.stdout:
                line = line.rstrip()
                if line:
                    self._log(line)
            proc.wait()

            if proc.returncode == 0:
                self._log(f"✅  Vídeo guardado: {out}")
                self._status("✅  Subtítulos incrustados correctamente")
                messagebox.showinfo("Éxito", f"Vídeo listo:\n{out}")
                if self.open_folder.get():
                    self._open_folder(folder)
            else:
                self._log(f"❌  FFmpeg terminó con código {proc.returncode}")
                self._status("❌  Error en FFmpeg")
                messagebox.showerror("Error",
                                     "FFmpeg terminó con error.\n"
                                     "Revisa el log para más detalles.")

        except FileNotFoundError:
            self._log("❌  'ffmpeg' no encontrado en el PATH del sistema.")
            self._log("    Descarga ffmpeg en:  https://ffmpeg.org/download.html")
            self._status("❌  ffmpeg no encontrado")
            messagebox.showerror("Error",
                                 "'ffmpeg' no está instalado o no está en el PATH.\n"
                                 "Descárgalo en: https://ffmpeg.org/download.html")
        except Exception as exc:
            self._log(f"❌  {exc}")
            self._status("❌  Error inesperado")
            messagebox.showerror("Error", str(exc))
        finally:
            self.pbar.stop()
            self._busy = False

    @staticmethod
    def _open_folder(folder: str):
        try:
            if sys.platform == "win32":
                os.startfile(folder)
            elif sys.platform == "darwin":
                subprocess.Popen(["open", folder])
            else:
                subprocess.Popen(["xdg-open", folder])
        except Exception:
            pass


# ── Main ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    root = tk.Tk()

    # Variables de dimensiones
    WIN_W = 620  # O el ancho que estés usando
    WIN_H = 780

    # Configuración de límites
    root.minsize(WIN_W, 400)
    root.maxsize(root.winfo_screenwidth(), WIN_H)

    app = SubtitleGen(root)

    # Actualizar para obtener medidas reales
    root.update_idletasks()
    sw = root.winfo_screenwidth()

    # LA CORRECCIÓN: Definir ancho, ALTO y posición en una sola línea
    # Formato: "ANCHO x ALTO + X + Y"
    root.geometry(f"{WIN_W}x{WIN_H}+{(sw - WIN_W) // 2}+5")

    root.mainloop()
