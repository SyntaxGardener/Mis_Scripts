"""
╔══════════════════════════════════════════════════════╗
║        MEZCLADOR DE CUÑA PUBLICITARIA                ║
║        Herramienta para alumnos de locución          ║
╚══════════════════════════════════════════════════════╝

Dependencias:
    pip install pydub pygame

Externo (necesario para MP3):
    - ffmpeg: https://ffmpeg.org/download.html
      (añadir al PATH del sistema)
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import os
import sys
import tempfile
import shutil

# ── Comprobación de dependencias ──────────────────────────────────────────────
try:
    from pydub import AudioSegment
    from pydub.effects import normalize
except ImportError:
    import subprocess, sys
    messagebox_fallback = tk.Tk()
    messagebox_fallback.withdraw()
    tk.messagebox.showerror(
        "Dependencia faltante",
        "Instala pydub:\n\n  pip install pydub\n\nY ffmpeg desde https://ffmpeg.org"
    )
    sys.exit(1)

try:
    import pygame
    pygame.mixer.init()
    PYGAME_OK = True
except ImportError:
    PYGAME_OK = False


# ── Paleta de colores (estética "estudio de radio") ───────────────────────────
C = {
    "bg":        "#0f1923",   # Fondo principal
    "panel":     "#162230",   # Paneles
    "card":      "#1e2f3f",   # Tarjetas
    "border":    "#2a4055",   # Bordes
    "accent":    "#e8a020",   # Naranja dorado (VU meter vibes)
    "accent2":   "#1a9fd4",   # Azul cyan
    "success":   "#2ecc71",
    "warning":   "#f39c12",
    "error":     "#e74c3c",
    "text":      "#d4e6f1",
    "text_dim":  "#6b8fa8",
    "text_dark": "#3a5a72",
    "slider_bg": "#0a1520",
    "slider_trough": "#2a4055",
}

FONT_TITLE  = ("Consolas", 15, "bold")
FONT_LABEL  = ("Consolas", 9)
FONT_SMALL  = ("Consolas", 8)
FONT_VALUE  = ("Consolas", 11, "bold")
FONT_BUTTON = ("Consolas", 9, "bold")
FONT_MONO   = ("Consolas", 8)


# ── Utilidades de audio ───────────────────────────────────────────────────────

def db_from_percent(percent: float) -> float:
    """Convierte porcentaje de volumen (0-100) a ganancia en dB."""
    if percent <= 0:
        return -120.0
    if percent >= 100:
        return 0.0
    import math
    return 20 * math.log10(percent / 100)


def loop_music_to_duration(music: AudioSegment, duration_ms: int) -> AudioSegment:
    """Repite la música hasta alcanzar la duración necesaria, con crossfade suave."""
    if len(music) == 0:
        return AudioSegment.silent(duration=duration_ms)
    loops = (duration_ms // len(music)) + 2
    looped = music * loops
    return looped[:duration_ms]


def mix_audio(
    voice_path: str,
    music_path: str,
    silence_before: float,
    silence_after: float,
    vol_speech_pct: float,
    vol_silence_pct: float,
    fadein_ms: int,
    fadeout_ms: int,
    transition_ms: int,
    output_path: str,
    progress_cb=None,
) -> None:
    """
    Mezcla la locución con la música de fondo siguiendo la estructura:

        [silencio_intro] + [locución] + [silencio_outro]
         música al 100%    música baja  música al 100%
         fade in ──────►              ◄────── fade out
    """

    def prog(msg, val=None):
        if progress_cb:
            progress_cb(msg, val)

    prog("Cargando locución…", 5)
    voice = AudioSegment.from_file(voice_path)

    prog("Cargando música…", 15)
    music_raw = AudioSegment.from_file(music_path)

    # Duraciones en ms
    sil_before_ms  = int(silence_before * 1000)
    sil_after_ms   = int(silence_after  * 1000)
    voice_ms       = len(voice)
    total_ms       = sil_before_ms + voice_ms + sil_after_ms
    trans_ms       = min(transition_ms, sil_before_ms // 2, sil_after_ms // 2, 1000)

    prog("Bucleando música…", 25)
    music_full = loop_music_to_duration(music_raw, total_ms)

    # ── Sección INTRO: música a volumen alto ──────────────────────────────────
    prog("Aplicando fade in…", 35)
    intro = music_full[:sil_before_ms]
    intro_db = db_from_percent(vol_silence_pct)
    intro = intro.apply_gain(intro_db)
    if fadein_ms > 0 and len(intro) > 0:
        intro = intro.fade_in(min(fadein_ms, len(intro)))

    # ── Sección LOCUCIÓN: música a volumen bajo ───────────────────────────────
    prog("Mezclando locución…", 50)
    speech_music = music_full[sil_before_ms: sil_before_ms + voice_ms]
    speech_db = db_from_percent(vol_speech_pct)
    speech_music = speech_music.apply_gain(speech_db)

    # Transición suave intro → locución
    if trans_ms > 0 and len(intro) >= trans_ms and len(speech_music) >= trans_ms:
        intro        = intro.fade_out(trans_ms)
        speech_music = speech_music.fade_in(trans_ms)

    # ── Sección OUTRO: música a volumen alto ──────────────────────────────────
    prog("Aplicando fade out…", 65)
    outro = music_full[sil_before_ms + voice_ms:]
    outro = outro.apply_gain(intro_db)

    # Transición suave locución → outro
    if trans_ms > 0 and len(speech_music) >= trans_ms and len(outro) >= trans_ms:
        speech_music = speech_music.fade_out(trans_ms)
        outro        = outro.fade_in(trans_ms)

    if fadeout_ms > 0 and len(outro) > 0:
        outro = outro.fade_out(min(fadeout_ms, len(outro)))

    # ── Ensamblar pista de música completa ────────────────────────────────────
    prog("Ensamblando pistas…", 75)
    music_track = intro + speech_music + outro
    if len(music_track) < total_ms:
        music_track += AudioSegment.silent(duration=total_ms - len(music_track))
    music_track = music_track[:total_ms]

    # ── Base de silencio + superponer música + superponer voz ─────────────────
    base = AudioSegment.silent(duration=total_ms)
    base = base.overlay(music_track)
    base = base.overlay(voice, position=sil_before_ms)

    prog("Exportando archivo…", 90)
    fmt = os.path.splitext(output_path)[1].lstrip(".").lower()
    if fmt not in ("mp3", "wav", "ogg", "aac", "flac"):
        fmt = "mp3"
    base.export(output_path, format=fmt)
    prog("¡Listo!", 100)


# ── Widgets personalizados ─────────────────────────────────────────────────────

class LabeledScale(tk.Frame):
    """Slider con etiqueta, valor numérico y unidad."""

    def __init__(self, parent, label, from_, to, default,
                 unit="", resolution=1, fmt="{:.0f}", **kw):
        super().__init__(parent, bg=C["card"], **kw)
        self.fmt = fmt
        self.unit = unit

        tk.Label(self, text=label, bg=C["card"], fg=C["text_dim"],
                 font=FONT_SMALL, anchor="w").pack(side="top", fill="x", padx=4, pady=(4, 0))

        row = tk.Frame(self, bg=C["card"])
        row.pack(fill="x", padx=4, pady=(0, 4))

        self.var = tk.DoubleVar(value=default)
        self.val_lbl = tk.Label(row, text=self._fmt(default),
                                bg=C["card"], fg=C["accent"],
                                font=FONT_VALUE, width=7, anchor="e")
        self.val_lbl.pack(side="right", padx=(4, 0))

        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Dark.Horizontal.TScale",
                        background=C["card"],
                        troughcolor=C["slider_trough"],
                        sliderlength=16,
                        sliderrelief="flat")

        self.scale = ttk.Scale(row, from_=from_, to=to,
                               orient="horizontal", variable=self.var,
                               style="Dark.Horizontal.TScale",
                               command=self._on_change)
        self.scale.pack(side="left", fill="x", expand=True)

    def _fmt(self, val):
        return self.fmt.format(val) + " " + self.unit

    def _on_change(self, v):
        self.val_lbl.config(text=self._fmt(float(v)))

    def get(self):
        return self.var.get()


class FileSlot(tk.Frame):
    """Zona para arrastrar / seleccionar un archivo de audio."""

    def __init__(self, parent, label, icon, **kw):
        super().__init__(parent, bg=C["card"], highlightbackground=C["border"],
                         highlightthickness=1, **kw)
        self._path = None
        self.label = label

        # Cabecera
        header = tk.Frame(self, bg=C["border"], height=24)
        header.pack(fill="x")
        header.pack_propagate(False)
        tk.Label(header, text=f"  {icon}  {label}", bg=C["border"],
                 fg=C["text"], font=FONT_LABEL, anchor="w").pack(side="left", fill="y")

        # Cuerpo
        body = tk.Frame(self, bg=C["card"])
        body.pack(fill="x", padx=8, pady=6)

        self.path_var = tk.StringVar(value="(sin archivo)")
        self.path_lbl = tk.Label(body, textvariable=self.path_var,
                                 bg=C["card"], fg=C["text_dim"],
                                 font=FONT_MONO, anchor="w",
                                 wraplength=320, justify="left")
        self.path_lbl.pack(side="left", fill="x", expand=True)

        self.btn = tk.Button(body, text="Seleccionar…", command=self._browse,
                             bg=C["accent2"], fg=C["bg"], font=FONT_BUTTON,
                             relief="flat", padx=8, cursor="hand2",
                             activebackground=C["accent"], activeforeground=C["bg"])
        self.btn.pack(side="right", padx=(8, 0))

        # Indicador de estado
        self.status = tk.Label(self, text="", bg=C["card"],
                               fg=C["success"], font=FONT_SMALL)
        self.status.pack(anchor="w", padx=8, pady=(0, 4))

    def _browse(self):
        path = filedialog.askopenfilename(
            title=f"Seleccionar {self.label}",
            filetypes=[
                ("Audio", "*.mp3 *.wav *.ogg *.flac *.aac *.m4a *.wma"),
                ("Todos", "*.*"),
            ]
        )
        if path:
            self.set_path(path)

    def set_path(self, path):
        self._path = path
        name = os.path.basename(path)
        self.path_var.set(name)
        self.path_lbl.config(fg=C["text"])
        self.status.config(text=f"✔  {path}", fg=C["success"])

    def get_path(self):
        return self._path


# ── Ventana principal ─────────────────────────────────────────────────────────

class App(tk.Tk):

    def __init__(self):
        super().__init__()
        self.title("🎙 Mezclador para Cuña Publicitaria")
        self.configure(bg=C["bg"])
        self.resizable(False, False)
        self._tmp_preview = None
        self._build_ui()
        self._center()

    def _center(self):
        self.update_idletasks()
        w, h = self.winfo_reqwidth(), self.winfo_reqheight()
        sw = self.winfo_screenwidth()
        pos_x = (sw - w) // 2
        pos_y = 10
        self.geometry(f"{w}x{h}+{pos_x}+{pos_y}")

    # ── Construcción de la UI ─────────────────────────────────────────────────

    def _build_ui(self):
        # ── Título ────────────────────────────────────────────────────────────
        title_bar = tk.Frame(self, bg=C["accent"], height=48)
        title_bar.pack(fill="x")
        title_bar.pack_propagate(False)
        tk.Label(title_bar,
                 text="  🎙  MEZCLADOR PARA CUÑA PUBLICITARIA",
                 bg=C["accent"], fg=C["bg"],
                 font=FONT_TITLE).pack(side="left", fill="y", padx=8)
        tk.Label(title_bar,
                 text="Herramienta para audios ",
                 bg=C["accent"], fg=C["bg"],
                 font=FONT_SMALL).pack(side="right", fill="y")

        # ── Cuerpo principal ──────────────────────────────────────────────────
        main = tk.Frame(self, bg=C["bg"])
        main.pack(fill="both", expand=True, padx=14, pady=10)

        left  = tk.Frame(main, bg=C["bg"])
        left.pack(side="left", fill="both", expand=True, padx=(0, 6))
        right = tk.Frame(main, bg=C["bg"])
        right.pack(side="right", fill="both", expand=True, padx=(6, 0))

        # ── Columna izquierda: archivos + estructura ──────────────────────────
        self._section(left, "📁  ARCHIVOS DE AUDIO")

        self.slot_voice = FileSlot(left, "Locución (tu voz)", "🎤")
        self.slot_voice.pack(fill="x", pady=(0, 8))

        self.slot_music = FileSlot(left, "Música de fondo", "🎵")
        self.slot_music.pack(fill="x", pady=(0, 12))

        self._section(left, "⏱  ESTRUCTURA DE LA CUÑA")

        grid_struct = tk.Frame(left, bg=C["bg"])
        grid_struct.pack(fill="x")

        self.sil_before = LabeledScale(
            grid_struct, "Silencio al inicio (intro musical)", 0, 15, 3,
            unit="seg", fmt="{:.1f}")
        self.sil_before.pack(fill="x", pady=2)

        self.sil_after = LabeledScale(
            grid_struct, "Silencio al final (outro musical)", 0, 15, 3,
            unit="seg", fmt="{:.1f}")
        self.sil_after.pack(fill="x", pady=2)

        # ── Columna derecha: volumen + fades + botones ────────────────────────
        self._section(right, "🔊  VOLUMEN DE LA MÚSICA")

        self.vol_silence = LabeledScale(
            right, "Vol. música en intro / outro (silencio)", 0, 100, 85,
            unit="%", fmt="{:.0f}")
        self.vol_silence.pack(fill="x", pady=2)

        self.vol_speech = LabeledScale(
            right, "Vol. música durante la locución", 0, 100, 20,
            unit="%", fmt="{:.0f}")
        self.vol_speech.pack(fill="x", pady=2)

        self.transition = LabeledScale(
            right, "Duración del fundido entre secciones", 200, 3000, 800,
            unit="ms", fmt="{:.0f}")
        self.transition.pack(fill="x", pady=2)

        self._section(right, "🌅  FADE IN / FADE OUT")

        self.fadein = LabeledScale(
            right, "Duración del fade in (inicio)", 0, 5000, 1500,
            unit="ms", fmt="{:.0f}")
        self.fadein.pack(fill="x", pady=2)

        self.fadeout = LabeledScale(
            right, "Duración del fade out (final)", 0, 5000, 2000,
            unit="ms", fmt="{:.0f}")
        self.fadeout.pack(fill="x", pady=2)

        # ── Diagrama visual de la estructura ─────────────────────────────────
        self._build_diagram(right)

        # ── Barra de progreso ─────────────────────────────────────────────────
        prog_frame = tk.Frame(self, bg=C["bg"])
        prog_frame.pack(fill="x", padx=14, pady=(4, 0))

        self.prog_lbl = tk.Label(prog_frame, text="Listo para mezclar",
                                 bg=C["bg"], fg=C["text_dim"], font=FONT_SMALL,
                                 anchor="w")
        self.prog_lbl.pack(side="top", fill="x")

        style = ttk.Style()
        style.configure("Green.Horizontal.TProgressbar",
                        troughcolor=C["slider_trough"],
                        background=C["success"],
                        thickness=6)
        self.progressbar = ttk.Progressbar(prog_frame,
                                           style="Green.Horizontal.TProgressbar",
                                           mode="determinate", maximum=100)
        self.progressbar.pack(fill="x", pady=(2, 6))

        # ── Botones de acción ─────────────────────────────────────────────────
        btn_row = tk.Frame(self, bg=C["bg"])
        btn_row.pack(fill="x", padx=14, pady=(0, 12))

        btn_cfg = dict(font=FONT_BUTTON, relief="flat", padx=16, pady=8,
                       cursor="hand2")

        self.btn_preview = tk.Button(
            btn_row, text="▶  PREESCUCHAR",
            bg=C["accent2"], fg=C["bg"],
            activebackground="#0e7daa", activeforeground=C["bg"],
            command=self._preview, **btn_cfg)
        self.btn_preview.pack(side="left", fill="x", expand=True, padx=(0, 6))

        self.btn_stop = tk.Button(
            btn_row, text="⏹  DETENER",
            bg=C["card"], fg=C["text"],
            activebackground=C["border"], activeforeground=C["text"],
            command=self._stop, **btn_cfg)
        self.btn_stop.pack(side="left", padx=(0, 6))

        self.btn_export = tk.Button(
            btn_row, text="💾  EXPORTAR MEZCLA",
            bg=C["accent"], fg=C["bg"],
            activebackground="#c08010", activeforeground=C["bg"],
            command=self._export, **btn_cfg)
        self.btn_export.pack(side="right", fill="x", expand=True, padx=(6, 0))

        # ── Pie de página ─────────────────────────────────────────────────────
        footer = tk.Frame(self, bg=C["border"], height=1)
        footer.pack(fill="x")
        tk.Label(self,
                 text="  pydub + pygame  |  requiere ffmpeg en el PATH  |"
                      "  Formatos soportados: MP3, WAV, OGG, FLAC",
                 bg=C["bg"], fg=C["text_dark"], font=FONT_SMALL, anchor="w"
                 ).pack(fill="x", padx=10, pady=(3, 6))

    def _section(self, parent, title):
        frm = tk.Frame(parent, bg=C["bg"])
        frm.pack(fill="x", pady=(8, 4))
        tk.Label(frm, text=title, bg=C["bg"], fg=C["accent"],
                 font=FONT_LABEL).pack(side="left")
        tk.Frame(frm, bg=C["border"], height=1).pack(side="left",
                                                      fill="x", expand=True,
                                                      padx=(6, 0), pady=7)

    def _build_diagram(self, parent):
        """Diagrama simple de la estructura de la cuña."""
        self._section(parent, "📊  ESTRUCTURA RESULTANTE")
        canvas = tk.Canvas(parent, bg=C["card"], height=54,
                           highlightbackground=C["border"], highlightthickness=1)
        canvas.pack(fill="x", pady=(0, 6))
        canvas.bind("<Configure>", self._draw_diagram)
        self._diagram_canvas = canvas

    def _draw_diagram(self, event=None):
        c = self._diagram_canvas
        c.delete("all")
        W = c.winfo_width() or 400
        H = 54
        pad = 10
        w = W - 2 * pad

        # Secciones proporcionales
        total = max(
            self.sil_before.get() + 10 + self.sil_after.get(), 1)
        p_intro  = self.sil_before.get() / total
        p_voice  = 10 / total
        p_outro  = self.sil_after.get() / total

        x0 = pad
        blocks = [
            (p_intro, C["accent"],  "INTRO\n♫ alto"),
            (p_voice, C["accent2"], "LOCUCIÓN\n♫ bajo"),
            (p_outro, C["accent"],  "OUTRO\n♫ alto"),
        ]
        y_top, y_bot = 4, H - 4
        for ratio, color, label in blocks:
            bw = w * ratio
            c.create_rectangle(x0, y_top, x0 + bw, y_bot,
                                fill=color, outline=C["bg"], width=1)
            # Texto centrado si hay espacio
            if bw > 30:
                cx = x0 + bw / 2
                cy = (y_top + y_bot) / 2
                c.create_text(cx, cy, text=label, fill=C["bg"],
                              font=("Consolas", 7, "bold"), justify="center")
            x0 += bw

    # ── Lógica de mezcla ──────────────────────────────────────────────────────

    def _validate(self):
        if not self.slot_voice.get_path():
            messagebox.showwarning("Falta archivo", "Selecciona la grabación de tu locución.")
            return False
        if not self.slot_music.get_path():
            messagebox.showwarning("Falta archivo", "Selecciona la música de fondo.")
            return False
        return True

    def _get_params(self):
        return dict(
            voice_path    = self.slot_voice.get_path(),
            music_path    = self.slot_music.get_path(),
            silence_before= self.sil_before.get(),
            silence_after = self.sil_after.get(),
            vol_speech_pct= self.vol_speech.get(),
            vol_silence_pct= self.vol_silence.get(),
            fadein_ms     = int(self.fadein.get()),
            fadeout_ms    = int(self.fadeout.get()),
            transition_ms = int(self.transition.get()),
        )

    def _set_progress(self, msg, val=None):
        self.prog_lbl.config(text=msg)
        if val is not None:
            self.progressbar["value"] = val
        self.update_idletasks()

    def _preview(self):
        if not self._validate():
            return
        if not PYGAME_OK:
            messagebox.showwarning(
                "pygame no disponible",
                "Instala pygame para preescuchar:\n\n  pip install pygame"
            )
            return
        self.btn_preview.config(state="disabled")
        self.btn_export.config(state="disabled")
        tmp = tempfile.mktemp(suffix=".wav")
        self._tmp_preview = tmp

        def run():
            try:
                mix_audio(**self._get_params(),
                          output_path=tmp,
                          progress_cb=self._set_progress)
                pygame.mixer.music.load(tmp)
                pygame.mixer.music.play()
                self._set_progress("▶ Reproduciendo preescucha…", 100)
            except Exception as e:
                messagebox.showerror("Error al mezclar", str(e))
                self._set_progress("Error — revisa los archivos y ffmpeg")
            finally:
                self.btn_preview.config(state="normal")
                self.btn_export.config(state="normal")

        threading.Thread(target=run, daemon=True).start()

    def _stop(self):
        if PYGAME_OK:
            pygame.mixer.music.stop()
        self._set_progress("Reproducción detenida")

    def _export(self):
        if not self._validate():
            return

        out = filedialog.asksaveasfilename(
            title="Guardar cuña mezclada",
            defaultextension=".mp3",
            filetypes=[
                ("MP3", "*.mp3"),
                ("WAV", "*.wav"),
                ("OGG", "*.ogg"),
                ("FLAC", "*.flac"),
            ]
        )
        if not out:
            return

        self.btn_preview.config(state="disabled")
        self.btn_export.config(state="disabled")

        def run():
            try:
                mix_audio(**self._get_params(),
                          output_path=out,
                          progress_cb=self._set_progress)
                self.after(0, lambda: messagebox.showinfo(
                    "¡Exportado!",
                    f"Cuña guardada en:\n{out}\n\n"
                    "¡Ya puedes entregarla o reproducirla!"
                ))
            except Exception as e:
                self.after(0, lambda: messagebox.showerror(
                    "Error al exportar", str(e)))
                self._set_progress("Error — revisa los archivos y ffmpeg")
            finally:
                self.btn_preview.config(state="normal")
                self.btn_export.config(state="normal")

        threading.Thread(target=run, daemon=True).start()


# ── Punto de entrada ──────────────────────────────────────────────────────────
if __name__ == "__main__":
    app = App()
    # Actualizar diagrama cuando cambian los sliders
    for slider in ("sil_before", "sil_after"):
        def _refresh(_v, s=slider):
            app._draw_diagram()
        getattr(app, slider).var.trace_add("write", _refresh)
    app.mainloop()
