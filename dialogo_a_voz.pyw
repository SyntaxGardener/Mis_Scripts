#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Dialogo a Voz
=============
Convierte un dialogo escrito (formato "NOMBRE: texto") en un unico archivo
de audio, usando una voz neuronal distinta para cada interlocutor.

Requisitos (instalar una vez):
    pip install edge-tts pydub

Ademas necesita tener ffmpeg accesible (en el PATH del sistema, o bien
indicar la ruta a ffmpeg.exe portable desde el boton "ffmpeg..." de abajo).

Autor: herramienta generada para Raquel - C.E.P.A. Suroccidente
"""

import asyncio
import json
import os
import re
import sys
import tempfile
import threading
import traceback
from pathlib import Path

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog

try:
    import edge_tts
except ImportError:
    edge_tts = None

try:
    from pydub import AudioSegment
except ImportError:
    AudioSegment = None


# ----------------------------------------------------------------------
# Configuracion / constantes
# ----------------------------------------------------------------------

APP_DIR = Path(__file__).resolve().parent
CONFIG_PATH = APP_DIR / "dialogo_a_voz_config.json"

BG = "#f5f6f8"
BG_PANEL = "#ffffff"
ACCENT = "#2f6f4f"
ACCENT_DARK = "#204d37"
TEXT = "#2b2b2b"
MUTED = "#6b6b6b"
BORDER = "#d9dde1"

# Lista estatica de voces neuronales en espanol de Microsoft Edge TTS.
# Se puede ampliar/actualizar en caliente con el boton "Actualizar voces"
# (necesita conexion a internet).
VOCES_ES = [
    ("es-ES-AlvaroNeural",   "Espana - Alvaro (hombre)"),
    ("es-ES-ElviraNeural",   "Espana - Elvira (mujer)"),
    ("es-ES-AbrilNeural",    "Espana - Abril (mujer, joven)"),
    ("es-ES-ArnauNeural",    "Espana - Arnau (hombre)"),
    ("es-ES-DarioNeural",    "Espana - Dario (hombre)"),
    ("es-ES-EliasNeural",    "Espana - Elias (hombre)"),
    ("es-ES-EstrellaNeural", "Espana - Estrella (mujer)"),
    ("es-ES-IreneNeural",    "Espana - Irene (mujer)"),
    ("es-ES-LaiaNeural",     "Espana - Laia (mujer, joven)"),
    ("es-ES-LiaNeural",      "Espana - Lia (mujer)"),
    ("es-ES-NilNeural",      "Espana - Nil (hombre, joven)"),
    ("es-ES-SaulNeural",     "Espana - Saul (hombre, joven)"),
    ("es-ES-TeoNeural",      "Espana - Teo (hombre)"),
    ("es-ES-TrianaNeural",   "Espana - Triana (mujer, joven)"),
    ("es-ES-VeraNeural",     "Espana - Vera (mujer)"),
    ("es-ES-XimenaNeural",   "Espana - Ximena (mujer)"),
    ("es-MX-JorgeNeural",    "Mexico - Jorge (hombre)"),
    ("es-MX-DaliaNeural",    "Mexico - Dalia (mujer)"),
    ("es-AR-TomasNeural",    "Argentina - Tomas (hombre)"),
    ("es-AR-ElenaNeural",    "Argentina - Elena (mujer)"),
]

SPEAKER_LINE_RE = re.compile(
    r"^\s*([A-ZÁÉÍÓÚÑÜ][A-ZÁÉÍÓÚÑÜa-záéíóúñü0-9 .'\-]{0,40}?)\s*:\s*(.+)$"
)

# Linea que empieza por guion de dialogo (—, – o -) seguida de texto:
# formato tipico de dialogos de libro de texto sin nombres, con
# interlocutores que se alternan turno a turno.
GUION_LINE_RE = re.compile(r"^\s*[—–\-]\s*(\S.*)$")


# ----------------------------------------------------------------------
# Logica de parseo del dialogo
# ----------------------------------------------------------------------

def _parsear_por_nombres(texto):
    turnos = []
    hablante_actual = None

    for linea_bruta in texto.splitlines():
        linea = linea_bruta.strip()
        if not linea:
            continue

        m = SPEAKER_LINE_RE.match(linea)
        if m:
            hablante_actual = m.group(1).strip()
            resto = m.group(2).strip()
            if resto:
                turnos.append([hablante_actual, resto])
            continue

        # linea de continuacion (sin "NOMBRE:")
        if hablante_actual is None:
            hablante_actual = "NARRADOR"
            turnos.append([hablante_actual, linea])
        else:
            if turnos and turnos[-1][0] == hablante_actual:
                turnos[-1][1] += " " + linea
            else:
                turnos.append([hablante_actual, linea])

    return turnos


def _parsear_por_guiones(texto, n_interlocutores=2):
    """
    Dialogos tipo:
        — Buenos dias.
        — Buenos dias, ¿que desea?
        — Queria informacion sobre el curso...
    Cada linea que empieza por guion es un turno nuevo; los turnos se
    reparten ciclicamente entre "Interlocutor 1", "Interlocutor 2", etc.
    Una linea que NO empieza por guion se anade como continuacion del
    ultimo turno (por si una intervencion ocupa varias lineas).
    """
    n_interlocutores = max(1, int(n_interlocutores))
    turnos = []
    contador = 0

    for linea_bruta in texto.splitlines():
        linea = linea_bruta.strip()
        if not linea:
            continue

        m = GUION_LINE_RE.match(linea)
        if m:
            hablante = f"Interlocutor {(contador % n_interlocutores) + 1}"
            turnos.append([hablante, m.group(1).strip()])
            contador += 1
        else:
            if turnos:
                turnos[-1][1] += " " + linea

    return turnos


def _detectar_modo(texto):
    """Decide automaticamente si el dialogo usa 'NOMBRE:' o guion largo."""
    lineas = [l.strip() for l in texto.splitlines() if l.strip()]
    n_nombre = sum(1 for l in lineas if SPEAKER_LINE_RE.match(l))
    n_guion = sum(1 for l in lineas if GUION_LINE_RE.match(l))

    if n_guion >= 2 and n_guion >= n_nombre:
        return "guiones"
    return "nombres"


def parsear_dialogo(texto, modo="auto", n_interlocutores=2):
    """
    Convierte el texto pegado en una lista de tuplas (hablante, linea).

    modo:
      - "auto"     : detecta automaticamente el formato (recomendado).
      - "nombres"  : fuerza el formato "NOMBRE: texto".
      - "guiones"  : fuerza el formato de guion largo alternado (— texto).
    """
    if modo == "auto":
        modo = _detectar_modo(texto)

    if modo == "guiones":
        return _parsear_por_guiones(texto, n_interlocutores)
    return _parsear_por_nombres(texto)


def hablantes_unicos(turnos):
    vistos = []
    for hablante, _ in turnos:
        if hablante not in vistos:
            vistos.append(hablante)
    return vistos


# ----------------------------------------------------------------------
# Configuracion persistente (ruta de ffmpeg, ultima carpeta de salida...)
# ----------------------------------------------------------------------

def cargar_config():
    if CONFIG_PATH.exists():
        try:
            return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def guardar_config(cfg):
    try:
        CONFIG_PATH.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass


# ----------------------------------------------------------------------
# Generacion de audio
# ----------------------------------------------------------------------

async def _generar_turno_mp3(texto, voz, velocidad, salida_path):
    """Genera un mp3 para un turno de dialogo usando edge-tts."""
    rate_str = f"{velocidad:+d}%"
    communicate = edge_tts.Communicate(texto, voz, rate=rate_str)
    await communicate.save(str(salida_path))


def generar_audio_completo(turnos, voces_por_hablante, velocidades_por_hablante,
                            pausa_ms, ffmpeg_path, salida_final, progreso_cb, log_cb):
    """
    Genera todos los turnos y los concatena en un unico archivo.
    Se ejecuta en un hilo aparte (no en el hilo de la interfaz).
    progreso_cb(i, total) y log_cb(mensaje) se llaman para informar del avance.
    """
    if AudioSegment is not None and ffmpeg_path:
        AudioSegment.converter = ffmpeg_path
        AudioSegment.ffmpeg = ffmpeg_path
        ffprobe_path = str(Path(ffmpeg_path).with_name(
            "ffprobe.exe" if ffmpeg_path.lower().endswith(".exe") else "ffprobe"))
        if Path(ffprobe_path).exists():
            AudioSegment.ffprobe = ffprobe_path

    with tempfile.TemporaryDirectory(prefix="dialogo_a_voz_") as tmpdir:
        tmpdir = Path(tmpdir)
        segmentos = []
        total = len(turnos)

        for i, (hablante, texto) in enumerate(turnos, start=1):
            voz = voces_por_hablante.get(hablante)
            velocidad = velocidades_por_hablante.get(hablante, 0)
            if not voz:
                raise ValueError(f'No hay voz asignada para "{hablante}"')

            log_cb(f"Generando turno {i}/{total} ({hablante})...")
            turno_path = tmpdir / f"turno_{i:03d}.mp3"
            asyncio.run(_generar_turno_mp3(texto, voz, velocidad, turno_path))
            segmentos.append(turno_path)
            progreso_cb(i, total)

        log_cb("Uniendo todos los turnos en un solo archivo...")

        if AudioSegment is None:
            # Sin pydub: union simple por concatenacion binaria (sin pausas
            # perfectas, pero funcional como ultimo recurso).
            with open(salida_final, "wb") as out:
                for idx, seg_path in enumerate(segmentos):
                    with open(seg_path, "rb") as f:
                        out.write(f.read())
        else:
            silencio = AudioSegment.silent(duration=pausa_ms)
            audio_final = AudioSegment.empty()
            for idx, seg_path in enumerate(segmentos):
                audio_final += AudioSegment.from_file(seg_path, format="mp3")
                if idx < len(segmentos) - 1:
                    audio_final += silencio
            audio_final.export(salida_final, format="mp3", bitrate="128k")

        log_cb(f"Listo. Archivo generado: {salida_final}")


# ----------------------------------------------------------------------
# Interfaz grafica
# ----------------------------------------------------------------------

class DialogoAVozApp:

    DIALOGO_EJEMPLO = (
        "ENTREVISTADOR: Buenos dias, ¿podria decirnos como se llama y a que se dedica?\n"
        "MARIA: Buenos dias. Me llamo Maria y soy enfermera en el hospital del pueblo.\n"
        "ENTREVISTADOR: ¿Y desde cuando trabaja en ese hospital?\n"
        "MARIA: Pues llevo ya casi doce años. Empece nada mas terminar la carrera.\n"
    )

    def __init__(self, root):
        self.root = root
        self.root.title("Dialogo a Voz - generador de audios para comprension oral")
        self.root.configure(bg=BG)
        self.root.minsize(860, 620)
        self._centrar_ventana(980, 720)

        self.cfg = cargar_config()
        self.ffmpeg_path = self.cfg.get("ffmpeg_path") or self._detectar_ffmpeg()
        self.carpeta_salida = self.cfg.get("carpeta_salida") or str(Path.home() / "Desktop")

        self.turnos = []
        self.hablante_vars = {}   # nombre -> {"voz": StringVar, "velocidad": IntVar}
        self.generando = False

        self._construir_estilos()
        self._construir_interfaz()

        if edge_tts is None:
            self._log("ATENCION: no se encuentra el paquete 'edge-tts'. "
                       "Instalalo con:  pip install edge-tts pydub")

    # ------------------------------------------------------------------
    # ------------------------------------------------------------------
    def _centrar_ventana(self, ancho, alto):
        self.root.update_idletasks()
        pantalla_ancho = self.root.winfo_screenwidth()
        x = max(0, (pantalla_ancho - ancho) // 2)
        y = 5
        self.root.geometry(f"{ancho}x{alto}+{x}+{y}")

    def _detectar_ffmpeg(self):
        import shutil
        return shutil.which("ffmpeg") or ""

    def _construir_estilos(self):
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except Exception:
            pass

        style.configure("TFrame", background=BG)
        style.configure("Panel.TFrame", background=BG_PANEL)
        style.configure("TLabel", background=BG, foreground=TEXT, font=("Segoe UI", 10))
        style.configure("Panel.TLabel", background=BG_PANEL, foreground=TEXT, font=("Segoe UI", 10))
        style.configure("Muted.TLabel", background=BG_PANEL, foreground=MUTED, font=("Segoe UI", 9))
        style.configure("Titulo.TLabel", background=BG, foreground=ACCENT_DARK,
                         font=("Segoe UI Semibold", 15))
        style.configure("Subtitulo.TLabel", background=BG, foreground=MUTED, font=("Segoe UI", 10))

        style.configure("Accent.TButton", background=ACCENT, foreground="white",
                         font=("Segoe UI Semibold", 10), padding=8)
        style.map("Accent.TButton", background=[("active", ACCENT_DARK)])

        style.configure("TButton", padding=6, font=("Segoe UI", 9))
        style.configure("TCombobox", padding=3)
        style.configure("Horizontal.TProgressbar", background=ACCENT, troughcolor="#e6e8eb")

    def _construir_interfaz(self):
        contenedor = ttk.Frame(self.root, padding=16)
        contenedor.pack(fill="both", expand=True)

        # --- Cabecera -----------------------------------------------------
        cab = ttk.Frame(contenedor)
        cab.pack(fill="x", pady=(0, 12))
        ttk.Label(cab, text="Dialogo a Voz", style="Titulo.TLabel").pack(anchor="w")
        ttk.Label(cab, text="Pega un dialogo con formato \"NOMBRE: texto\" y genera un audio "
                             "con una voz distinta para cada personaje.",
                  style="Subtitulo.TLabel").pack(anchor="w")

        cuerpo = ttk.Frame(contenedor)
        cuerpo.pack(fill="both", expand=True)
        cuerpo.columnconfigure(0, weight=3)
        cuerpo.columnconfigure(1, weight=2)
        cuerpo.rowconfigure(0, weight=1)

        # --- Panel izquierdo: texto del dialogo ---------------------------
        panel_izq = tk.Frame(cuerpo, bg=BG_PANEL, highlightbackground=BORDER,
                              highlightthickness=1)
        panel_izq.grid(row=0, column=0, sticky="nsew", padx=(0, 10))

        ttk.Label(panel_izq, text="Texto del dialogo", style="Panel.TLabel",
                  font=("Segoe UI Semibold", 10)).pack(anchor="w", padx=12, pady=(10, 2))

        text_frame = tk.Frame(panel_izq, bg=BG_PANEL)
        text_frame.pack(fill="both", expand=True, padx=12, pady=(0, 8))

        self.txt_dialogo = tk.Text(text_frame, wrap="word", font=("Segoe UI", 10),
                                    bg="#fbfcfc", fg=TEXT, relief="flat",
                                    highlightbackground=BORDER, highlightthickness=1,
                                    padx=8, pady=8, undo=True)
        self.txt_dialogo.pack(side="left", fill="both", expand=True)
        scroll = ttk.Scrollbar(text_frame, command=self.txt_dialogo.yview)
        scroll.pack(side="right", fill="y")
        self.txt_dialogo.configure(yscrollcommand=scroll.set)
        self.txt_dialogo.insert("1.0", self.DIALOGO_EJEMPLO)

        formato_frame = tk.Frame(panel_izq, bg=BG_PANEL)
        formato_frame.pack(fill="x", padx=12, pady=(0, 6))
        ttk.Label(formato_frame, text="Formato:", style="Panel.TLabel").pack(side="left")

        self.var_modo = tk.StringVar(value="auto")
        ttk.Radiobutton(formato_frame, text="Automatico", value="auto",
                         variable=self.var_modo,
                         command=self._actualizar_estado_n_interlocutores).pack(side="left", padx=(8, 0))
        ttk.Radiobutton(formato_frame, text="Con nombres (NOMBRE:)", value="nombres",
                         variable=self.var_modo,
                         command=self._actualizar_estado_n_interlocutores).pack(side="left", padx=6)
        ttk.Radiobutton(formato_frame, text="Con guiones (— alternado)", value="guiones",
                         variable=self.var_modo,
                         command=self._actualizar_estado_n_interlocutores).pack(side="left", padx=6)

        formato_frame2 = tk.Frame(panel_izq, bg=BG_PANEL)
        formato_frame2.pack(fill="x", padx=12, pady=(0, 8))
        ttk.Label(formato_frame2, text="Nº interlocutores (solo formato guiones):",
                  style="Muted.TLabel").pack(side="left")
        self.var_n_interlocutores = tk.IntVar(value=2)
        self.spin_n_interlocutores = ttk.Spinbox(
            formato_frame2, from_=1, to=6, width=4, textvariable=self.var_n_interlocutores)
        self.spin_n_interlocutores.pack(side="left", padx=8)

        botones_texto = ttk.Frame(panel_izq, style="Panel.TFrame")
        botones_texto.pack(fill="x", padx=12, pady=(0, 12))
        ttk.Button(botones_texto, text="Cargar .txt...", command=self._cargar_txt).pack(side="left")
        ttk.Button(botones_texto, text="Borrar todo",
                   command=lambda: self.txt_dialogo.delete("1.0", "end")).pack(side="left", padx=6)
        ttk.Button(botones_texto, text="Detectar hablantes ▶",
                   style="Accent.TButton", command=self._detectar_hablantes).pack(side="right")

        # --- Panel derecho: hablantes y opciones ---------------------------
        panel_der = tk.Frame(cuerpo, bg=BG_PANEL, highlightbackground=BORDER,
                              highlightthickness=1)
        panel_der.grid(row=0, column=1, sticky="nsew")

        ttk.Label(panel_der, text="Hablantes detectados", style="Panel.TLabel",
                  font=("Segoe UI Semibold", 10)).pack(anchor="w", padx=12, pady=(10, 2))
        ttk.Label(panel_der, text="Asigna una voz (y velocidad opcional) a cada uno.",
                  style="Muted.TLabel").pack(anchor="w", padx=12, pady=(0, 8))

        hablantes_frame = tk.Frame(panel_der, bg=BG_PANEL)
        hablantes_frame.pack(fill="both", expand=True, padx=12)

        canvas = tk.Canvas(hablantes_frame, bg=BG_PANEL, highlightthickness=0)
        vscroll = ttk.Scrollbar(hablantes_frame, orient="vertical", command=canvas.yview)
        self.hablantes_inner = tk.Frame(canvas, bg=BG_PANEL)
        self.hablantes_inner.bind(
            "<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=self.hablantes_inner, anchor="nw")
        canvas.configure(yscrollcommand=vscroll.set)
        canvas.pack(side="left", fill="both", expand=True)
        vscroll.pack(side="right", fill="y")
        self.canvas_hablantes = canvas

        self.lbl_sin_hablantes = ttk.Label(
            self.hablantes_inner, text="(pulsa \"Detectar hablantes\" primero)",
            style="Muted.TLabel")
        self.lbl_sin_hablantes.pack(anchor="w", pady=10)

        # --- Opciones de generacion -----------------------------------
        opciones = tk.Frame(panel_der, bg=BG_PANEL)
        opciones.pack(fill="x", padx=12, pady=(6, 10))

        fila1 = tk.Frame(opciones, bg=BG_PANEL)
        fila1.pack(fill="x", pady=3)
        ttk.Label(fila1, text="Pausa entre turnos (ms):", style="Panel.TLabel").pack(side="left")
        self.var_pausa = tk.IntVar(value=450)
        ttk.Spinbox(fila1, from_=0, to=3000, increment=50, width=6,
                    textvariable=self.var_pausa).pack(side="left", padx=8)

        fila2 = tk.Frame(opciones, bg=BG_PANEL)
        fila2.pack(fill="x", pady=3)
        ttk.Label(fila2, text="Carpeta de salida:", style="Panel.TLabel").pack(side="left")
        self.lbl_carpeta = ttk.Label(fila2, text=self._acortar(self.carpeta_salida),
                                      style="Muted.TLabel")
        self.lbl_carpeta.pack(side="left", padx=8)
        ttk.Button(fila2, text="Elegir...", command=self._elegir_carpeta).pack(side="right")

        fila3 = tk.Frame(opciones, bg=BG_PANEL)
        fila3.pack(fill="x", pady=3)
        ttk.Label(fila3, text="Nombre del archivo:", style="Panel.TLabel").pack(side="left")
        self.var_nombre_archivo = tk.StringVar(value="dialogo_01.mp3")
        ttk.Entry(fila3, textvariable=self.var_nombre_archivo, width=22).pack(side="left", padx=8)

        fila4 = tk.Frame(opciones, bg=BG_PANEL)
        fila4.pack(fill="x", pady=3)
        ttk.Label(fila4, text=f"ffmpeg: {self._acortar(self.ffmpeg_path) or 'no detectado'}",
                  style="Muted.TLabel").pack(side="left")
        ttk.Button(fila4, text="ffmpeg...", command=self._elegir_ffmpeg).pack(side="right")

        # --- Barra de progreso y log ---------------------------------------
        pie = ttk.Frame(contenedor)
        pie.pack(fill="x", pady=(12, 0))

        self.progreso = ttk.Progressbar(pie, style="Horizontal.TProgressbar",
                                         mode="determinate")
        self.progreso.pack(fill="x", pady=(0, 6))

        fila_botones = ttk.Frame(pie)
        fila_botones.pack(fill="x")
        self.btn_generar = ttk.Button(fila_botones, text="🔊  Generar audio",
                                       style="Accent.TButton", command=self._generar)
        self.btn_generar.pack(side="left")
        self.btn_abrir = ttk.Button(fila_botones, text="Abrir carpeta de salida",
                                     command=self._abrir_carpeta, state="disabled")
        self.btn_abrir.pack(side="left", padx=8)

        self.lbl_estado = ttk.Label(pie, text="Listo.", style="Subtitulo.TLabel")
        self.lbl_estado.pack(anchor="w", pady=(6, 0))

        self.txt_log = tk.Text(pie, height=5, bg="#fbfcfc", fg=MUTED, relief="flat",
                                highlightbackground=BORDER, highlightthickness=1,
                                font=("Consolas", 9), state="disabled")
        self.txt_log.pack(fill="x", pady=(6, 0))

    # ------------------------------------------------------------------
    def _acortar(self, ruta, largo=46):
        if not ruta:
            return ""
        return ruta if len(ruta) <= largo else "..." + ruta[-(largo - 3):]

    def _log(self, mensaje):
        def hacer():
            self.txt_log.configure(state="normal")
            self.txt_log.insert("end", mensaje + "\n")
            self.txt_log.see("end")
            self.txt_log.configure(state="disabled")
        self.root.after(0, hacer)

    def _set_estado(self, mensaje):
        self.root.after(0, lambda: self.lbl_estado.configure(text=mensaje))

    # ------------------------------------------------------------------
    def _cargar_txt(self):
        ruta = filedialog.askopenfilename(
            title="Elegir archivo de texto con el dialogo",
            filetypes=[("Texto", "*.txt"), ("Todos los archivos", "*.*")])
        if not ruta:
            return
        try:
            contenido = Path(ruta).read_text(encoding="utf-8")
        except UnicodeDecodeError:
            contenido = Path(ruta).read_text(encoding="latin-1")
        self.txt_dialogo.delete("1.0", "end")
        self.txt_dialogo.insert("1.0", contenido)

    def _elegir_carpeta(self):
        ruta = filedialog.askdirectory(title="Elegir carpeta de salida",
                                        initialdir=self.carpeta_salida)
        if ruta:
            self.carpeta_salida = ruta
            self.lbl_carpeta.configure(text=self._acortar(ruta))
            self.cfg["carpeta_salida"] = ruta
            guardar_config(self.cfg)

    def _elegir_ffmpeg(self):
        ruta = filedialog.askopenfilename(
            title="Elegir ffmpeg.exe (o ejecutable ffmpeg)",
            filetypes=[("ffmpeg", "ffmpeg*"), ("Todos los archivos", "*.*")])
        if ruta:
            self.ffmpeg_path = ruta
            self.cfg["ffmpeg_path"] = ruta
            guardar_config(self.cfg)
            messagebox.showinfo("ffmpeg", f"Ruta guardada:\n{ruta}")

    def _abrir_carpeta(self):
        try:
            if sys.platform.startswith("win"):
                os.startfile(self.carpeta_salida)
            elif sys.platform == "darwin":
                os.system(f'open "{self.carpeta_salida}"')
            else:
                os.system(f'xdg-open "{self.carpeta_salida}"')
        except Exception as e:
            messagebox.showerror("Error", str(e))

    # ------------------------------------------------------------------
    def _actualizar_estado_n_interlocutores(self):
        estado = "normal" if self.var_modo.get() in ("guiones", "auto") else "disabled"
        self.spin_n_interlocutores.configure(state=estado)

    def _detectar_hablantes(self):
        texto = self.txt_dialogo.get("1.0", "end")
        modo = self.var_modo.get()
        n_interlocutores = int(self.var_n_interlocutores.get() or 2)
        self.turnos = parsear_dialogo(texto, modo=modo, n_interlocutores=n_interlocutores)

        if not self.turnos:
            messagebox.showwarning(
                "Sin turnos detectados",
                "No se ha reconocido ningun turno de dialogo.\n\n"
                "Formato esperado, una intervencion por linea:\n"
                "NOMBRE: texto de lo que dice...")
            return

        for widget in self.hablantes_inner.winfo_children():
            widget.destroy()
        self.hablante_vars = {}

        nombres = hablantes_unicos(self.turnos)
        voces_ciclo = [v[0] for v in VOCES_ES]

        for i, nombre in enumerate(nombres):
            fila = tk.Frame(self.hablantes_inner, bg=BG_PANEL)
            fila.pack(fill="x", pady=5)

            ttk.Label(fila, text=nombre, style="Panel.TLabel",
                      font=("Segoe UI Semibold", 9), width=16, anchor="w").pack(side="left")

            voz_var = tk.StringVar()
            etiquetas_voces = [f"{nombre_voz}  ({vid})" for vid, nombre_voz in VOCES_ES]
            combo = ttk.Combobox(fila, textvariable=voz_var, values=etiquetas_voces,
                                  width=26, state="readonly")
            voz_por_defecto = voces_ciclo[i % len(voces_ciclo)]
            idx_defecto = [v[0] for v in VOCES_ES].index(voz_por_defecto)
            combo.current(idx_defecto)
            combo.pack(side="left", padx=6)

            vel_var = tk.IntVar(value=0)
            ttk.Label(fila, text="vel.", style="Muted.TLabel").pack(side="left", padx=(10, 2))
            ttk.Spinbox(fila, from_=-30, to=30, increment=5, width=4,
                        textvariable=vel_var).pack(side="left")

            self.hablante_vars[nombre] = {"voz_var": voz_var, "vel_var": vel_var}

        n_turnos = len(self.turnos)
        n_hablantes = len(nombres)
        self._set_estado(f"Detectados {n_hablantes} hablantes y {n_turnos} turnos de dialogo.")

    def _voz_id_desde_etiqueta(self, etiqueta):
        # etiqueta tiene formato "Nombre bonito  (es-ES-XxxNeural)"
        m = re.search(r"\(([^)]+)\)\s*$", etiqueta)
        return m.group(1) if m else etiqueta

    # ------------------------------------------------------------------
    def _generar(self):
        if self.generando:
            return
        if edge_tts is None:
            messagebox.showerror(
                "Falta edge-tts",
                "No se encuentra el paquete 'edge-tts'.\n\n"
                "Instalalo abriendo una terminal y ejecutando:\n"
                "pip install edge-tts pydub")
            return
        if not self.turnos:
            self._detectar_hablantes()
            if not self.turnos:
                return
        if not self.hablante_vars:
            messagebox.showwarning("Faltan hablantes", "Pulsa antes \"Detectar hablantes\".")
            return

        nombre_archivo = self.var_nombre_archivo.get().strip() or "dialogo.mp3"
        if not nombre_archivo.lower().endswith(".mp3"):
            nombre_archivo += ".mp3"
        salida_final = str(Path(self.carpeta_salida) / nombre_archivo)

        voces_por_hablante = {}
        velocidades_por_hablante = {}
        for nombre, refs in self.hablante_vars.items():
            etiqueta = refs["voz_var"].get()
            voces_por_hablante[nombre] = self._voz_id_desde_etiqueta(etiqueta)
            velocidades_por_hablante[nombre] = int(refs["vel_var"].get())

        pausa_ms = int(self.var_pausa.get())

        self.generando = True
        self.btn_generar.configure(state="disabled")
        self.btn_abrir.configure(state="disabled")
        self.progreso.configure(maximum=len(self.turnos), value=0)
        self._log(f"--- Generando '{nombre_archivo}' ({len(self.turnos)} turnos) ---")

        def worker():
            try:
                def progreso_cb(i, total):
                    self.root.after(0, lambda: self.progreso.configure(value=i))
                    self._set_estado(f"Generando turno {i}/{total}...")

                generar_audio_completo(
                    self.turnos, voces_por_hablante, velocidades_por_hablante,
                    pausa_ms, self.ffmpeg_path, salida_final,
                    progreso_cb, self._log)

                self._set_estado(f"Completado: {nombre_archivo}")
                self.root.after(0, lambda: self.btn_abrir.configure(state="normal"))
                self.root.after(0, lambda: messagebox.showinfo(
                    "Audio generado", f"Se ha creado el archivo:\n{salida_final}"))
            except Exception as e:
                detalle = traceback.format_exc()
                self._log("ERROR: " + str(e))
                self._log(detalle)
                self.root.after(0, lambda: messagebox.showerror("Error al generar el audio", str(e)))
            finally:
                self.generando = False
                self.root.after(0, lambda: self.btn_generar.configure(state="normal"))

        threading.Thread(target=worker, daemon=True).start()


# ----------------------------------------------------------------------
def main():
    root = tk.Tk()
    app = DialogoAVozApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
