"""
Resumidor de Documentos con IA 
========================================
Requisitos:
    pip install google-generativeai pypdf pdfplumber python-docx requests beautifulsoup4
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import threading
import os
import sys
import subprocess
import json
from pathlib import Path
from datetime import datetime

# ─────────────────────────────────────────────────────────────────────────────
#  API KEY — se lee de config.ini (mismo directorio que este script)
#  Obtén tu clave gratis en: https://console.groq.com → API Keys
#
#  Crea un archivo config.ini con este contenido:
#  [groq]
#  api_key = gsk_tu_clave_aqui
# ─────────────────────────────────────────────────────────────────────────────
import configparser as _cp, pathlib as _pl

def _leer_api_key() -> str:
    cfg_path = _pl.Path(__file__).parent / "config.ini"
    if cfg_path.exists():
        cfg = _cp.ConfigParser()
        cfg.read(cfg_path, encoding="utf-8")
        return cfg.get("groq", "api_key", fallback="").strip()
    return ""

API_KEY_FIJA = _leer_api_key()

# Modelos Groq a intentar en orden
MODELOS_GROQ = [
    "llama-3.3-70b-versatile",   # el más capaz
    "llama-3.1-8b-instant",      # más rápido, por si hay límite de RPM
    "gemma2-9b-it",              # alternativa
]

# ── Extracción de texto ───────────────────────────────────────────────────────

def extraer_texto_pdf(ruta: str) -> str:
    try:
        import pdfplumber
        texto = []
        with pdfplumber.open(ruta) as pdf:
            for pagina in pdf.pages:
                t = pagina.extract_text()
                if t:
                    texto.append(t)
        return "\n".join(texto)
    except ImportError:
        from pypdf import PdfReader
        reader = PdfReader(ruta)
        return "\n".join(p.extract_text() or "" for p in reader.pages)


def extraer_texto_docx(ruta: str) -> str:
    from docx import Document
    doc = Document(ruta)
    return "\n".join(p.text for p in doc.paragraphs if p.text.strip())


def extraer_texto_web(url: str) -> str:
    import requests
    from bs4 import BeautifulSoup
    headers = {"User-Agent": "Mozilla/5.0 (compatible; ResumidorBot/1.0)"}
    resp = requests.get(url, headers=headers, timeout=20)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")
    for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
        tag.decompose()
    return soup.get_text(separator="\n", strip=True)


def obtener_texto(fuente: str) -> str:
    fuente = fuente.strip()
    if fuente.startswith("http://") or fuente.startswith("https://"):
        return extraer_texto_web(fuente)
    ext = Path(fuente).suffix.lower()
    if ext == ".pdf":
        return extraer_texto_pdf(fuente)
    if ext in (".docx", ".doc"):
        return extraer_texto_docx(fuente)
    raise ValueError(f"Formato no soportado: '{ext}'. Usa PDF, DOCX o URL.")


# ── Groq (con fallback automático de modelo) ─────────────────────────────────

def resumir_con_gemini(texto: str, api_key: str, tipo: str, idioma: str, secciones_examen: dict = None,
                       log_fn=None) -> str:
    from groq import Groq
    client = Groq(api_key=api_key)

    instrucciones = {
        "Resumen":      f"Genera un resumen conciso y claro del siguiente texto en {idioma}. "
                        "Destaca las ideas principales en 3-5 párrafos:",
        "Esquema":      f"Genera un esquema estructurado con jerarquía de puntos (usa ►, •, -) "
                        f"del siguiente texto en {idioma}. Incluye título, secciones y puntos clave:",
        "Puntos clave": f"Extrae los puntos clave más importantes del siguiente texto en {idioma}. "
                        "Presenta cada punto con una viñeta (•) y una frase concisa:",
        "Cuestionario": f"Genera un cuestionario de 10 preguntas con 4 opciones de respuesta (A, B, C, D) "
                        f"basado en el siguiente texto en {idioma}. "
                        "Formato: Pregunta numerada, luego las 4 opciones en líneas separadas, "
                        "y al final de cada pregunta indica entre paréntesis cuál es la respuesta correcta. "
                        "Las preguntas deben cubrir los conceptos más importantes del texto:",
        "Examen":       "__EXAMEN_DINAMICO__",
    }
    # Construir prompt dinámico para examen según secciones seleccionadas
    if tipo == "Examen" and secciones_examen:
        secs = []
        n = 1
        clave_secs = []
        if secciones_examen.get("verdadero_falso"):
            secs.append(f"{n}) VERDADERO/FALSO (5 afirmaciones, sin indicar la respuesta correcta en el enunciado)")
            clave_secs.append(f"Sección {n} — Verdadero/Falso"); n += 1
        if secciones_examen.get("opcion_multiple"):
            secs.append(f"{n}) OPCIÓN MÚLTIPLE (5 preguntas con opciones A, B, C, D, sin marcar la correcta en el enunciado)")
            clave_secs.append(f"Sección {n} — Opción múltiple"); n += 1
        if secciones_examen.get("comprension_lectora"):
            secs.append(
                f"{n}) COMPRENSIÓN LECTORA:\n"
                f"   - Escribe un texto expositivo o informativo original, adaptado al nivel, "
                f"de un mínimo de 175 palabras y un máximo de 250. "
                f"Preséntalo bajo el epígrafe 'TEXTO:'\n"
                f"   - A continuación, 5 preguntas de comprensión sobre ese texto "
                f"bajo el epígrafe 'PREGUNTAS:'"
            )
            n += 1
        if secciones_examen.get("comprension_literaria"):
            secs.append(
                f"{n}) COMPRENSIÓN LECTORA (TEXTO LITERARIO):\n"
                f"   - Escribe un fragmento literario original (narrativo o poético), "
                f"adaptado al nivel y relacionado temáticamente con el documento, "
                f"de un mínimo de 150 palabras y un máximo de 220. Preséntalo bajo el epígrafe 'TEXTO:'\n"
                f"   - A continuación, 3 preguntas de comprensión lectora y análisis literario "
                f"bajo el epígrafe 'PREGUNTAS:'"
            )
            clave_secs.append(f"Sección {n} — Comprensión literaria"); n += 1
        if secciones_examen.get("expresion_escrita"):
            secs.append(
                f"{n}) EXPRESIÓN ESCRITA:\n"
                f"   - Propón 1 tarea de redacción concreta y motivadora (carta, descripción, "
                f"narración breve, descripción, exposición, argumentación...) relacionada con el tema del documento. "
                f"Indica el tipo de texto, la extensión aproximada (entre 80 y 150 palabras) "
                f"y una pauta o guía de ayuda con 3-4 puntos"
            )
            n += 1
        if secciones_examen.get("comprension_oral"):
            secs.append(f"{n}) COMPRENSIÓN ORAL (descripción de 1-2 actividades de escucha relacionadas con el tema)")
            n += 1
        if secciones_examen.get("preguntas_cortas"):
            secs.append(f"{n}) PREGUNTAS CORTAS (3 preguntas de respuesta breve)")
            n += 1
        if secciones_examen.get("desarrollo"):
            secs.append(f"{n}) DESARROLLO (1 pregunta de respuesta elaborada)")
            n += 1
        clave_txt = (
            f"Al final del examen añade una sección separada titulada "
            f"'CLAVE DE RESPUESTAS' con todas las respuestas correctas agrupadas "
            f"por sección: {', '.join(clave_secs)}. "
            f"No incluyas las respuestas correctas dentro del cuerpo del examen."
            if clave_secs else ""
        )
        secs_txt = "\n".join(secs)
        instrucciones["Examen"] = (
            f"Genera un examen formal en {idioma} con las siguientes secciones:\n"
            f"{secs_txt}\n"
            f"Basado en el siguiente texto. {clave_txt}"
        )

    prompt = instrucciones.get(tipo, instrucciones["Resumen"])

    import time

    def llamar_groq(modelo, mensajes, log_fn=None, etiqueta=""):
        """Llama a la API con reintentos automáticos si hay límite de RPM."""
        ultimo_error = None
        for intento in range(3):
            try:
                r = client.chat.completions.create(
                    model=modelo,
                    messages=mensajes,
                    max_tokens=2048,
                    temperature=0.3,
                )
                return r.choices[0].message.content
            except Exception as e:
                ultimo_error = e
                msg = str(e).lower()
                if any(k in msg for k in ["rate_limit", "429", "too many"]):
                    espera = 15 * (intento + 1)
                    if log_fn:
                        log_fn(f"  ⚠ {etiqueta}Límite RPM. Esperando {espera}s…")
                    time.sleep(espera)
                    continue
                raise
        raise Exception(f"Error tras 3 intentos: {ultimo_error}")

    def elegir_modelo(log_fn=None):
        for m in MODELOS_GROQ:
            if log_fn:
                log_fn(f"  Usando modelo: {m}")
            return m
        return MODELOS_GROQ[0]

    CHUNK_SIZE = 30_000   # ~10.000 tokens por fragmento
    modelo = elegir_modelo(log_fn)

    # ── Documento corto: procesado directo ───────────────────────────────────
    if len(texto) <= CHUNK_SIZE:
        if log_fn:
            log_fn("  Documento corto — procesando directamente…")
        mensajes = [
            {"role": "system", "content": "Eres un asistente experto en análisis y síntesis de documentos."},
            {"role": "user",   "content": f"{prompt}\n\n---\n\n{texto}"}
        ]
        return llamar_groq(modelo, mensajes, log_fn)

    # ── Documento largo: resumen por fragmentos ───────────────────────────────
    # Divide el texto en trozos con un pequeño solapamiento para no perder contexto
    SOLAPAMIENTO = 500
    fragmentos = []
    inicio = 0
    while inicio < len(texto):
        fin = min(inicio + CHUNK_SIZE, len(texto))
        fragmentos.append(texto[inicio:fin])
        inicio = fin - SOLAPAMIENTO if fin < len(texto) else fin

    total_frags = len(fragmentos)
    if log_fn:
        log_fn(f"  Documento largo — {total_frags} fragmentos a procesar…")

    resumenes_parciales = []
    for i, frag in enumerate(fragmentos, 1):
        if log_fn:
            log_fn(f"  Fragmento {i}/{total_frags}…")
        mensajes = [
            {"role": "system", "content": "Eres un asistente experto en análisis y síntesis de documentos."},
            {"role": "user",   "content":
                f"Este es el fragmento {i} de {total_frags} de un documento más largo.\n"
                f"Resume los puntos clave de ESTE fragmento en español, de forma concisa:\n\n---\n\n{frag}"}
        ]
        r = llamar_groq(modelo, mensajes, log_fn, etiqueta=f"Frag {i}/{total_frags} — ")
        resumenes_parciales.append(f"[Fragmento {i}/{total_frags}]\n{r}")
        # Pausa entre fragmentos para no saturar el límite de RPM
        if i < total_frags:
            if log_fn:
                log_fn(f"  Pausa entre fragmentos…")
            time.sleep(8)

    # ── Síntesis final de todos los resúmenes parciales ───────────────────────
    if log_fn:
        log_fn(f"  Generando síntesis final…")

    texto_parciales = "\n\n".join(resumenes_parciales)
    sintesis_prompt = {
        "Resumen":      f"A partir de los siguientes resúmenes parciales de un documento, "
                        f"genera un RESUMEN FINAL coherente y bien estructurado en {idioma}, "
                        f"integrando toda la información sin repeticiones:",
        "Esquema":      f"A partir de los siguientes resúmenes parciales de un documento, "
                        f"genera un ESQUEMA FINAL completo y estructurado en {idioma} "
                        f"(usa ►, •, -) con todas las secciones y puntos clave:",
        "Puntos clave": f"A partir de los siguientes resúmenes parciales de un documento, "
                        f"extrae y consolida los PUNTOS CLAVE más importantes en {idioma} "
                        f"(una viñeta • por punto, sin repeticiones):",
        "Cuestionario": f"A partir de los siguientes resúmenes parciales de un documento, "
                        f"genera un CUESTIONARIO FINAL de 10 preguntas con 4 opciones (A, B, C, D) en {idioma}. "
                        f"Cubre los conceptos más importantes. Indica la respuesta correcta al final de cada pregunta:",
        "Examen":       instrucciones.get("Examen", "Genera un examen formal."),
    }
    mensajes_finales = [
        {"role": "system", "content": "Eres un asistente experto en síntesis de documentos largos."},
        {"role": "user",   "content": f"{sintesis_prompt.get(tipo, sintesis_prompt['Resumen'])}\n\n---\n\n{texto_parciales}"}
    ]
    return llamar_groq(modelo, mensajes_finales, log_fn, etiqueta="Síntesis — ")


# ── Colores — Tema claro ──────────────────────────────────────────────────────

BG       = "#f4f4f8"
PANEL    = "#e8e8f0"
ENTRADA  = "#ffffff"
ACENTO   = "#5b4fcf"
ACENTO2  = "#2976d4"
TEXTO    = "#1a1a2e"
SUBTEXTO = "#666688"
EXITO    = "#1a7a3c"
ERROR    = "#c0392b"
BORDE    = "#ccccdd"

F_MONO   = ("Consolas", 10)
F_NORM   = ("Segoe UI", 10)
F_TITULO = ("Segoe UI", 13, "bold")
F_LABEL  = ("Segoe UI", 9)
F_BOLD   = ("Segoe UI", 9, "bold")

CONFIG_FILE = Path.home() / ".resumidor_config.json"


# ── Aplicación ────────────────────────────────────────────────────────────────

class ResumidorApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Resúmenes y Exámenes con IA · Groq")
        self.configure(bg=BG)
        self.resizable(True, True)
        self._cargar_config()
        self._construir_ui()
        self._centrar_ventana(920, 700)
        self.protocol("WM_DELETE_WINDOW", self._al_cerrar)

    # ── Config ────────────────────────────────────────────────────────────────

    def _cargar_config(self):
        self.cfg = {}
        if CONFIG_FILE.exists():
            try:
                self.cfg = json.loads(CONFIG_FILE.read_text())
            except Exception:
                pass

    def _guardar_config(self):
        self.cfg["carpeta_sal"] = self.var_carpeta.get().strip()
        self.cfg["tipo"]        = self.var_tipo.get()
        self.cfg["idioma"]      = self.var_idioma.get()
        try:
            CONFIG_FILE.write_text(json.dumps(self.cfg, indent=2))
        except Exception:
            pass

    def _al_cerrar(self):
        self._guardar_config()
        self.destroy()

    def _centrar_ventana(self, w: int, h: int):
        self.update_idletasks()
        x = (self.winfo_screenwidth() - w) // 2
        self.geometry(f"{w}x{h}+{x}+5")
        self.minsize(700, 520)

    # ── UI ────────────────────────────────────────────────────────────────────

    def _construir_ui(self):
        self._estilo_combo()

        # Cabecera
        cab = tk.Frame(self, bg=ACENTO, pady=10)
        cab.pack(fill="x")
        tk.Label(cab, text="✦ Resúmenes · Cuestionarios · Exámenes con IA",
                 font=F_TITULO, bg=ACENTO, fg="white").pack(side="left", padx=18)
        tk.Label(cab, text="Powered by Groq · Llama 3.3 (gratuito)",
                 font=F_LABEL, bg=ACENTO, fg="#ccc8ff").pack(side="right", padx=18)

        # Cuerpo: PanedWindow horizontal
        paned = tk.PanedWindow(self, orient="horizontal", bg=BG,
                               sashwidth=5, sashrelief="flat", sashpad=2)
        paned.pack(fill="both", expand=True, padx=10, pady=8)

        # ── Columna izquierda (con scroll) ───────────────────────────────────
        izq_outer = tk.Frame(paned, bg=BG)
        paned.add(izq_outer, minsize=250, width=300)

        canvas_izq = tk.Canvas(izq_outer, bg=BG, highlightthickness=0)
        sb_izq = ttk.Scrollbar(izq_outer, orient="vertical",
                               command=canvas_izq.yview)
        canvas_izq.configure(yscrollcommand=sb_izq.set)
        sb_izq.pack(side="right", fill="y")
        canvas_izq.pack(side="left", fill="both", expand=True)

        izq = tk.Frame(canvas_izq, bg=BG, padx=10)
        izq_window = canvas_izq.create_window((0, 0), window=izq, anchor="nw")

        def _on_izq_configure(e):
            canvas_izq.configure(scrollregion=canvas_izq.bbox("all"))
        def _on_canvas_resize(e):
            canvas_izq.itemconfig(izq_window, width=e.width)
        izq.bind("<Configure>", _on_izq_configure)
        canvas_izq.bind("<Configure>", _on_canvas_resize)

        # Scroll con rueda del ratón
        def _scroll_izq(e):
            canvas_izq.yview_scroll(int(-1*(e.delta/120)), "units")
        canvas_izq.bind_all("<MouseWheel>", _scroll_izq)

        # Tipo de salida
        self._lbl(izq, "📝  Tipo de documento a generar")
        self.var_tipo = tk.StringVar(value=self.cfg.get("tipo", "Resumen"))
        for op in ("Resumen", "Esquema", "Puntos clave", "Cuestionario", "Examen"):
            tk.Radiobutton(izq, text=op, variable=self.var_tipo, value=op,
                           font=F_NORM, bg=BG, fg=TEXTO,
                           activebackground=BG, activeforeground=ACENTO,
                           selectcolor=PANEL, relief="flat",
                           command=self._toggle_secciones).pack(anchor="w", pady=1)

        # Panel secciones examen (visible solo cuando se elige Examen)
        self.frame_secciones = tk.Frame(izq, bg=PANEL, padx=8, pady=6,
                                        relief="solid", bd=1)
        self._lbl_sec = tk.Label(self.frame_secciones, text="Secciones del examen:",
                                 font=F_BOLD, bg=PANEL, fg=SUBTEXTO)
        self._lbl_sec.pack(anchor="w", pady=(0, 4))

        self.sec_vars = {
            "verdadero_falso":         tk.BooleanVar(value=True),
            "opcion_multiple":         tk.BooleanVar(value=True),
            "comprension_lectora":     tk.BooleanVar(value=False),
            "comprension_literaria":   tk.BooleanVar(value=False),
            "expresion_escrita":       tk.BooleanVar(value=False),
            "comprension_oral":        tk.BooleanVar(value=False),
            "preguntas_cortas":        tk.BooleanVar(value=True),
            "desarrollo":              tk.BooleanVar(value=True),
        }
        sec_labels = {
            "verdadero_falso":         "Verdadero / Falso",
            "opcion_multiple":         "Opción múltiple",
            "comprension_lectora":     "Comprensión lectora (texto expositivo)",
            "comprension_literaria":   "Comprensión lectora (texto literario)",
            "expresion_escrita":       "Expresión escrita (redacción)",
            "comprension_oral":        "Comprensión oral",
            "preguntas_cortas":        "Preguntas cortas",
            "desarrollo":              "Desarrollo / Redacción",
        }
        for key, label in sec_labels.items():
            tk.Checkbutton(self.frame_secciones, text=label,
                           variable=self.sec_vars[key],
                           font=F_LABEL, bg=PANEL, fg=TEXTO,
                           activebackground=PANEL, activeforeground=ACENTO,
                           selectcolor=ENTRADA, relief="flat").pack(anchor="w", pady=1)

        # Idioma
        self._lbl(izq, "🌐  Idioma de salida")
        self.var_idioma = tk.StringVar(value=self.cfg.get("idioma", "Español"))
        idiomas = ["Español", "English", "Français", "Deutsch",
                   "Italiano", "Português", "中文", "日本語"]
        ttk.Combobox(izq, textvariable=self.var_idioma,
                     values=idiomas, state="readonly",
                     font=F_NORM).pack(fill="x", pady=(0, 10))

        # Carpeta de destino
        self._lbl(izq, "📁  Carpeta de destino")
        self.var_carpeta = tk.StringVar(
            value=self.cfg.get("carpeta_sal", str(Path.home() / "Resumenes")))
        fr_carp = tk.Frame(izq, bg=BG)
        fr_carp.pack(fill="x", pady=(0, 4))
        tk.Entry(fr_carp, textvariable=self.var_carpeta, font=F_NORM,
                 bg=ENTRADA, fg=TEXTO, relief="solid", bd=1).pack(
                     side="left", fill="x", expand=True)
        tk.Button(fr_carp, text="…", font=F_NORM, bg=ACENTO, fg="white",
                  relief="flat", cursor="hand2",
                  command=self._elegir_carpeta).pack(side="left", padx=(3, 0))

        tk.Button(izq, text="📂  Abrir carpeta de destino",
                  font=F_LABEL, bg=PANEL, fg=ACENTO2,
                  relief="flat", cursor="hand2", pady=6,
                  command=self._abrir_carpeta).pack(fill="x", pady=(4, 10))

        # Info modelos
        tk.Frame(izq, bg=BORDE, height=1).pack(fill="x", pady=8)
        tk.Label(izq, text="ℹ️  Modelos Groq (fallback automático):",
                 font=F_BOLD, bg=BG, fg=SUBTEXTO).pack(anchor="w")
        for m in MODELOS_GROQ:
            tk.Label(izq, text=f"  · {m}", font=F_LABEL,
                     bg=BG, fg=SUBTEXTO).pack(anchor="w")
        tk.Label(izq,
                 text="Si hay límite de cuota cambia\nal siguiente automáticamente.",
                 font=F_LABEL, bg=BG, fg=SUBTEXTO,
                 justify="left").pack(anchor="w", pady=(4, 0))

        # ── Columna derecha ───────────────────────────────────────────────────
        der = tk.Frame(paned, bg=BG, padx=8)
        paned.add(der, minsize=400)

        # Fuentes
        self._lbl(der, "📄  Documentos / URLs  (uno por línea)")
        fr_txt = tk.Frame(der, bg=BORDE, bd=1, relief="solid")
        fr_txt.pack(fill="both", expand=False, pady=(0, 6))
        self.txt_fuentes = tk.Text(fr_txt, height=7, font=F_MONO,
                                   bg=ENTRADA, fg=TEXTO,
                                   insertbackground=TEXTO, relief="flat",
                                   bd=6, wrap="none",
                                   selectbackground=ACENTO,
                                   selectforeground="white")
        sb_f = ttk.Scrollbar(fr_txt, orient="vertical",
                             command=self.txt_fuentes.yview)
        self.txt_fuentes.configure(yscrollcommand=sb_f.set)
        self.txt_fuentes.pack(side="left", fill="both", expand=True)
        sb_f.pack(side="right", fill="y")

        # Menú contextual botón derecho
        self.menu_ctx = tk.Menu(self, tearoff=0, bg=ENTRADA, fg=TEXTO,
                                activebackground=ACENTO, activeforeground="white",
                                relief="flat", bd=1)
        self.menu_ctx.add_command(label="📋  Pegar",
                                  command=self._pegar, accelerator="Ctrl+V")
        self.menu_ctx.add_command(label="✂️  Cortar",
                                  command=self._cortar, accelerator="Ctrl+X")
        self.menu_ctx.add_command(label="📄  Copiar",
                                  command=self._copiar, accelerator="Ctrl+C")
        self.menu_ctx.add_separator()
        self.menu_ctx.add_command(label="✖  Limpiar todo",
                                  command=lambda: self.txt_fuentes.delete("1.0", "end"))
        self.txt_fuentes.bind("<Button-3>", self._mostrar_menu_ctx)

        # Botones
        fr_bts = tk.Frame(der, bg=BG)
        fr_bts.pack(fill="x", pady=(0, 6))
        tk.Button(fr_bts, text="＋ Agregar archivos", font=F_NORM,
                  bg=PANEL, fg=TEXTO, relief="flat", cursor="hand2",
                  padx=10, pady=5,
                  command=self._agregar_archivos).pack(side="left")
        tk.Button(fr_bts, text="✖ Limpiar", font=F_NORM,
                  bg=PANEL, fg=SUBTEXTO, relief="flat", cursor="hand2",
                  padx=10, pady=5,
                  command=lambda: self.txt_fuentes.delete("1.0", "end")
                  ).pack(side="left", padx=6)
        self.btn_procesar = tk.Button(
            fr_bts, text="▶  PROCESAR",
            font=("Segoe UI", 10, "bold"), bg=ACENTO, fg="white",
            relief="flat", cursor="hand2", padx=16, pady=5,
            command=self._iniciar_procesamiento)
        self.btn_procesar.pack(side="right")

        # Resultados
        self._lbl(der, "📋  Resultados")
        fr_res = tk.Frame(der, bg=BORDE, bd=1, relief="solid")
        fr_res.pack(fill="both", expand=True)
        self.txt_resultado = scrolledtext.ScrolledText(
            fr_res, font=F_MONO, bg=ENTRADA, fg=TEXTO,
            insertbackground=TEXTO, relief="flat", bd=6,
            wrap="word", selectbackground=ACENTO,
            selectforeground="white", state="disabled")
        self.txt_resultado.pack(fill="both", expand=True)

        # Barra de estado
        barra = tk.Frame(self, bg=PANEL)
        barra.pack(fill="x", side="bottom")
        self.var_estado = tk.StringVar(value="Listo.")
        tk.Label(barra, textvariable=self.var_estado,
                 font=F_LABEL, bg=PANEL, fg=SUBTEXTO,
                 anchor="w").pack(side="left", padx=12, pady=5)
        self.progreso = ttk.Progressbar(barra, mode="indeterminate", length=120)
        self.progreso.pack(side="right", padx=12, pady=5)

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _lbl(self, padre, texto: str):
        tk.Label(padre, text=texto, font=F_BOLD,
                 bg=BG, fg=SUBTEXTO).pack(anchor="w", pady=(8, 2))

    def _estilo_combo(self):
        s = ttk.Style()
        s.theme_use("clam")
        s.configure("TCombobox",
                    fieldbackground=ENTRADA, background=ENTRADA,
                    foreground=TEXTO, arrowcolor=ACENTO,
                    bordercolor=BORDE, lightcolor=ENTRADA,
                    darkcolor=ENTRADA, selectbackground=ACENTO,
                    selectforeground="white")
        s.configure("TScrollbar", background=PANEL,
                    troughcolor=BG, arrowcolor=SUBTEXTO)

    def _toggle_secciones(self):
        if self.var_tipo.get() == "Examen":
            self.frame_secciones.pack(fill="x", pady=(0, 8))
        else:
            self.frame_secciones.pack_forget()

    def _elegir_carpeta(self):
        d = filedialog.askdirectory(title="Selecciona carpeta de destino")
        if d:
            self.var_carpeta.set(d)

    def _abrir_carpeta(self):
        carpeta = self.var_carpeta.get().strip()
        if not carpeta:
            return
        Path(carpeta).mkdir(parents=True, exist_ok=True)
        if sys.platform == "win32":
            os.startfile(carpeta)
        elif sys.platform == "darwin":
            subprocess.Popen(["open", carpeta])
        else:
            subprocess.Popen(["xdg-open", carpeta])

    def _agregar_archivos(self):
        archivos = filedialog.askopenfilenames(
            title="Selecciona documentos",
            filetypes=[("Documentos", "*.pdf *.docx *.doc"),
                       ("PDF", "*.pdf"), ("Word", "*.docx *.doc"),
                       ("Todos", "*.*")])
        for ruta in archivos:
            self.txt_fuentes.insert("end", ruta + "\n")

    def _mostrar_menu_ctx(self, event):
        try:
            self.menu_ctx.tk_popup(event.x_root, event.y_root)
        finally:
            self.menu_ctx.grab_release()

    def _pegar(self):
        try:
            texto = self.clipboard_get()
            self.txt_fuentes.insert(tk.INSERT, texto)
        except tk.TclError:
            pass

    def _cortar(self):
        try:
            self.txt_fuentes.event_generate("<<Cut>>")
        except tk.TclError:
            pass

    def _copiar(self):
        try:
            self.txt_fuentes.event_generate("<<Copy>>")
        except tk.TclError:
            pass

    # ── Procesamiento ─────────────────────────────────────────────────────────

    def _iniciar_procesamiento(self):
        if not API_KEY_FIJA:
            messagebox.showerror(
                "API Key no encontrada",
                "No se encontró la clave de Groq.\n\n"
                "Crea un archivo config.ini en la misma carpeta que este script "
                "con el siguiente contenido:\n\n"
                "[groq]\n"
                "api_key = gsk_tu_clave_aqui")
            return
        fuentes = [f.strip() for f in
                   self.txt_fuentes.get("1.0", "end").splitlines() if f.strip()]
        if not fuentes:
            messagebox.showwarning("Sin fuentes",
                                   "Agrega al menos un documento o URL.")
            return
        self.btn_procesar.config(state="disabled", bg="#9990d8")
        self.progreso.start(12)
        self._limpiar_resultado()
        self._set_estado("Procesando…")
        self._guardar_config()
        secciones = {k: v.get() for k, v in self.sec_vars.items()}
        threading.Thread(
            target=self._procesar_hilo,
            args=(fuentes, API_KEY_FIJA, self.var_tipo.get(),
                  self.var_idioma.get(), secciones),
            daemon=True).start()

    def _procesar_hilo(self, fuentes, api_key, tipo, idioma, secciones):
        carpeta_sal = Path(self.var_carpeta.get().strip())
        carpeta_sal.mkdir(parents=True, exist_ok=True)
        total = len(fuentes)

        for i, fuente in enumerate(fuentes, 1):
            nombre = (Path(fuente).stem
                      if not fuente.startswith("http") else f"web_{i}")
            self._set_estado(f"[{i}/{total}]  Leyendo: {nombre}…")
            try:
                texto = obtener_texto(fuente)
                if not texto.strip():
                    raise ValueError("No se pudo extraer texto del documento.")
                self._set_estado(
                    f"[{i}/{total}]  Generando {tipo.lower()}: {nombre}…")

                def log(msg, _i=i, _t=total):
                    self._set_estado(f"[{_i}/{_t}]  {msg}")

                resultado = resumir_con_gemini(texto, api_key, tipo, idioma, secciones, log)

                ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                tipo_slug = tipo.lower().replace(" ", "_")
                ruta_sal = carpeta_sal / f"{nombre}_{tipo_slug}_{ts}.txt"
                ruta_sal.write_text(resultado, encoding="utf-8")

                bloque = (f"{'═'*58}\n"
                          f"  {tipo.upper()}: {nombre}\n"
                          f"{'─'*58}\n"
                          f"{resultado}\n"
                          f"  ✔ Guardado: {ruta_sal}\n")
                self._agregar_resultado(bloque, "ok")

            except Exception as e:
                bloque = (f"{'═'*58}\n"
                          f"  ✘ ERROR en: {nombre}\n"
                          f"{'─'*58}\n"
                          f"  {e}\n")
                self._agregar_resultado(bloque, "err")

        self._set_estado(
            f"✔ Listo. {total} documento(s) procesados → {carpeta_sal}")
        self.after(0, self._fin_procesamiento)

    def _fin_procesamiento(self):
        self.progreso.stop()
        self.btn_procesar.config(state="normal", bg=ACENTO)

    # ── Thread-safe ───────────────────────────────────────────────────────────

    def _set_estado(self, msg: str):
        self.after(0, lambda: self.var_estado.set(msg))

    def _limpiar_resultado(self):
        def _f():
            self.txt_resultado.config(state="normal")
            self.txt_resultado.delete("1.0", "end")
            self.txt_resultado.config(state="disabled")
        self.after(0, _f)

    def _agregar_resultado(self, texto: str, tipo: str = "ok"):
        color = EXITO if tipo == "ok" else ERROR
        def _f():
            self.txt_resultado.config(state="normal")
            self.txt_resultado.tag_configure(tipo, foreground=color)
            self.txt_resultado.insert("end", texto + "\n", tipo)
            self.txt_resultado.see("end")
            self.txt_resultado.config(state="disabled")
        self.after(0, _f)


# ── Punto de entrada ──────────────────────────────────────────────────────────

if __name__ == "__main__":
    app = ResumidorApp()
    app.mainloop()
