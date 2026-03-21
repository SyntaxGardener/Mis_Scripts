"""
presentaciones.pyw
Interfaz gráfica para convertir resúmenes Word en presentaciones PPTX vistosas.
Requiere: python-docx, requests, python-pptx, pillow
"""

import configparser
import json
import os
import re
import sys
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

try:
    from docx import Document
    import requests
    from generar_pptx import generar_presentacion
except ImportError as e:
    root = tk.Tk(); root.withdraw()
    messagebox.showerror("Falta una dependencia",
        f"Instala las dependencias con:\n\n"
        f"python -m pip install python-docx requests python-pptx pillow\n\nError: {e}")
    sys.exit(1)

# ─────────────────────────────────────────────────────────────────────
# DATOS
# ─────────────────────────────────────────────────────────────────────

def cargar_api_key() -> str:
    config_path = os.path.join(BASE_DIR, "config.ini")
    if os.path.exists(config_path):
        cfg = configparser.ConfigParser()
        cfg.read(config_path, encoding="utf-8")
        key = cfg.get("claude", "api_key", fallback="").strip()
        if key:
            return key
    return os.environ.get("ANTHROPIC_API_KEY", "")

MODELOS = {
    "haiku":  "claude-haiku-4-5-20251001",
    "sonnet": "claude-sonnet-4-20250514",
}

PALETAS = {
    # ── Fondo oscuro ──────────────────────────────────────────────────
    "oceano":    {"primary":"065A82","secondary":"1C7293","accent":"02C39A","dark":"021B33","texto":"021B33","fondo_claro":False},
    "coral":     {"primary":"F96167","secondary":"F9E795","accent":"2F3C7E","dark":"1a1a4a","texto":"1a1a4a","fondo_claro":False},
    "bosque":    {"primary":"2C5F2D","secondary":"97BC62","accent":"F5F5F5","dark":"1a3a1b","texto":"1a3a1b","fondo_claro":False},
    "terracota": {"primary":"B85042","secondary":"E7E8D1","accent":"A7BEAE","dark":"5c2015","texto":"2d1208","fondo_claro":False},
    "teal":      {"primary":"028090","secondary":"00A896","accent":"05668D","dark":"012a30","texto":"012a30","fondo_claro":False},
    "nocturno":  {"primary":"1E2761","secondary":"CADCFC","accent":"7DE8E8","dark":"0d1230","texto":"CADCFC","fondo_claro":False},
    "cereza":    {"primary":"990011","secondary":"FCF6F5","accent":"2F3C7E","dark":"4a0008","texto":"4a0008","fondo_claro":False},
    "sage":      {"primary":"84B59F","secondary":"69A297","accent":"50808E","dark":"1a3530","texto":"1a3530","fondo_claro":False},
    # ── Fondo claro ───────────────────────────────────────────────────
    "lavanda":   {"primary":"6C63FF","secondary":"A5B4FC","accent":"4F46E5","dark":"F5F3FF","texto":"1E1B4B","fondo_claro":True},
    "melocoton": {"primary":"E07B54","secondary":"FDE8D8","accent":"C25E3A","dark":"FFF8F5","texto":"3D1A0A","fondo_claro":True},
    "cielo":     {"primary":"0284C7","secondary":"BAE6FD","accent":"0369A1","dark":"F0F9FF","texto":"0C2A3F","fondo_claro":True},
    "menta":     {"primary":"059669","secondary":"A7F3D0","accent":"047857","dark":"F0FDF4","texto":"052E16","fondo_claro":True},
}

PALETA_NOMBRES = {
    "oceano":    "🌊 Océano",
    "coral":     "🪸 Coral",
    "bosque":    "🌿 Bosque",
    "terracota": "🏺 Terracota",
    "teal":      "💎 Teal",
    "nocturno":  "🌙 Nocturno",
    "cereza":    "🍒 Cereza",
    "sage":      "🌱 Sage",
    "lavanda":   "💜 Lavanda  ☀",
    "melocoton": "🍑 Melocotón  ☀",
    "cielo":     "🩵 Cielo  ☀",
    "menta":     "🫧 Menta  ☀",
}

PALETA_DESC = {
    "oceano":    "Azul marino profundo",
    "coral":     "Coral + dorado vibrante",
    "bosque":    "Verde bosque natural",
    "terracota": "Terracota cálido",
    "teal":      "Verde azulado moderno",
    "nocturno":  "Azul noche + hielo",
    "cereza":    "Rojo cereza elegante",
    "sage":      "Verde salvia suave",
    "lavanda":   "Fondo blanco + violeta",
    "melocoton": "Fondo blanco + naranja",
    "cielo":     "Fondo blanco + azul cielo",
    "menta":     "Fondo blanco + verde menta",
}

# ─────────────────────────────────────────────────────────────────────
# LÓGICA IA
# ─────────────────────────────────────────────────────────────────────

def leer_docx(ruta: str) -> str:
    doc = Document(ruta)
    lineas = []
    for para in doc.paragraphs:
        texto = para.text.strip()
        if not texto:
            continue
        estilo = para.style.name.lower()
        if "heading 1" in estilo or "titulo 1" in estilo:
            lineas.append(f"\n## {texto}\n")
        elif "heading 2" in estilo or "titulo 2" in estilo:
            lineas.append(f"\n### {texto}\n")
        else:
            lineas.append(texto)
    return "\n".join(lineas)

PROMPT_SISTEMA = (
    "Eres un experto en diseño instruccional y presentaciones educativas. "
    "Tu tarea es estructurar un resumen de tema en diapositivas para una tutoría presencial "
    "de enseñanza a distancia (1 hora semanal). "
    "Responde ÚNICAMENTE con un objeto JSON válido, sin texto adicional ni bloques markdown."
)

PROMPT_USUARIO = """
Convierte el siguiente resumen en {n_slides} diapositivas educativas.

REGLAS ESTRICTAS:
1. La primera diapositiva es siempre la portada (tipo "portada").
2. La última diapositiva es siempre un resumen/cierre (tipo "resumen").
3. Cada diapositiva de contenido debe tener entre 3 y 5 puntos clave, concisos.
4. Genera notas del presentador (2-4 frases) para cada diapositiva.
5. Elige el icono más adecuado de react-icons/fa para cada diapositiva de contenido.
   Usa nombres EXACTOS como: FaBook, FaLightbulb, FaChartBar, FaStar, FaUsers, FaCog,
   FaFlask, FaGlobe, FaHeart, FaLock, FaSearch, FaCheckCircle, FaArrowRight, FaBrain,
   FaCalculator, FaAtom, FaDna, FaLeaf, FaCode, FaHistory, FaBalanceScale, FaMusic.
6. Varia los tipos de diapositiva: "contenido", "dos_columnas", "estadistica", "lista_iconos".

Responde SOLO con este JSON (sin ```json ni ningun otro texto):

{{
  "titulo_presentacion": "...",
  "asignatura": "...",
  "diapositivas": [
    {{"tipo": "portada", "titulo": "...", "subtitulo": "...", "notas": "..."}},
    {{"tipo": "contenido", "titulo": "...", "icono": "FaBook", "puntos": ["...", "..."], "notas": "..."}},
    {{"tipo": "dos_columnas", "titulo": "...",
      "columna_izq": {{"titulo": "...", "items": ["...", "..."]}},
      "columna_der": {{"titulo": "...", "items": ["...", "..."]}},
      "notas": "..."}},
    {{"tipo": "estadistica", "titulo": "...",
      "datos": [{{"valor": "...", "etiqueta": "..."}}, {{"valor": "...", "etiqueta": "..."}}],
      "notas": "..."}},
    {{"tipo": "lista_iconos", "titulo": "...",
      "items": [{{"icono": "FaStar", "titulo": "...", "descripcion": "..."}},
                {{"icono": "FaCog",  "titulo": "...", "descripcion": "..."}}],
      "notas": "..."}},
    {{"tipo": "resumen", "titulo": "Puntos clave", "puntos": ["...", "..."], "notas": "..."}}
  ]
}}

RESUMEN A TRANSFORMAR:
{contenido}
"""

def llamar_claude(contenido: str, n_slides: int, modelo: str) -> dict:
    api_key  = cargar_api_key()
    model_id = MODELOS.get(modelo, MODELOS["haiku"])
    prompt   = PROMPT_USUARIO.format(n_slides=n_slides, contenido=contenido)
    headers  = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    payload = {
        "model": model_id, "max_tokens": 4096,
        "system": PROMPT_SISTEMA,
        "messages": [{"role": "user", "content": prompt}],
    }
    resp = requests.post("https://api.anthropic.com/v1/messages",
                         headers=headers, json=payload, timeout=120)
    resp.raise_for_status()
    texto = resp.json()["content"][0]["text"].strip()
    texto = re.sub(r"^```json\s*", "", texto)
    texto = re.sub(r"^```\s*",     "", texto)
    texto = re.sub(r"\s*```$",     "", texto)
    return json.loads(texto)

# ─────────────────────────────────────────────────────────────────────
# INTERFAZ
# ─────────────────────────────────────────────────────────────────────

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Generador de Presentaciones")
        self.resizable(False, False)

        BG     = "#F0F4F8"
        AZUL   = "#065A82"
        BLANCO = "#FFFFFF"
        GRIS   = "#64748B"
        VERDE  = "#028090"

        self.configure(bg=BG)

        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("TLabel",        background=BG,    foreground="#1E293B", font=("Segoe UI", 10))
        style.configure("Header.TLabel", background=BG,    foreground=AZUL,      font=("Segoe UI", 13, "bold"))
        style.configure("Sub.TLabel",    background=BG,    foreground=GRIS,      font=("Segoe UI", 9))
        style.configure("TFrame",        background=BG)
        style.configure("Card.TFrame",   background=BLANCO, relief="flat")
        style.configure("TCombobox",     font=("Segoe UI", 10))
        style.configure("TSpinbox",      font=("Segoe UI", 10))
        style.configure("TCheckbutton",  background=BG,    font=("Segoe UI", 10))
        style.configure("Go.TButton",
            background=AZUL, foreground=BLANCO,
            font=("Segoe UI", 11, "bold"), padding=(20, 8), relief="flat")
        style.map("Go.TButton",
            background=[("active", VERDE), ("disabled", "#94A3B8")],
            foreground=[("disabled", "#CBD5E1")])

        outer = ttk.Frame(self, padding=20)
        outer.pack(fill="both", expand=True)

        # Cabecera
        ttk.Label(outer, text="Generador de Presentaciones", style="Header.TLabel").pack(anchor="w")
        ttk.Label(outer, text="Convierte tu resumen Word en una presentación vistosa con IA",
                  style="Sub.TLabel").pack(anchor="w", pady=(0, 14))

        # ── Tarjeta principal ─────────────────────────────────────
        card = ttk.Frame(outer, style="Card.TFrame", padding=16)
        card.pack(fill="x")
        card.columnconfigure(0, weight=1)

        # Archivo
        ttk.Label(card, text="Archivo Word (.docx)", background=BLANCO,
                  font=("Segoe UI", 10, "bold")).grid(row=0, column=0, sticky="w", pady=(0, 4))

        fila_arch = ttk.Frame(card, style="Card.TFrame")
        fila_arch.grid(row=1, column=0, sticky="ew", pady=(0, 14))

        self.var_archivo = tk.StringVar()
        tk.Entry(fila_arch, textvariable=self.var_archivo, width=44,
                 font=("Segoe UI", 10), relief="solid", bd=1,
                 bg=BLANCO, fg="#334155", state="readonly",
                 readonlybackground="#F8FAFC").pack(side="left", fill="x", expand=True)
        tk.Button(fila_arch, text="  Examinar…  ",
                  font=("Segoe UI", 10), bg=AZUL, fg=BLANCO,
                  relief="flat", cursor="hand2",
                  activebackground=VERDE, activeforeground=BLANCO,
                  bd=0, padx=8, pady=4,
                  command=self.elegir_archivo).pack(side="left", padx=(8, 0))

        ttk.Separator(card, orient="horizontal").grid(row=2, column=0, sticky="ew", pady=(0, 14))

        # ── Fila paleta + preview ──────────────────────────────────
        fila_pal = ttk.Frame(card, style="Card.TFrame")
        fila_pal.grid(row=3, column=0, sticky="ew", pady=(0, 12))

        ttk.Label(fila_pal, text="Paleta de colores", background=BLANCO,
                  font=("Segoe UI", 10, "bold")).grid(row=0, column=0, sticky="w")

        self._combo_paleta = ttk.Combobox(
            fila_pal, values=list(PALETA_NOMBRES.values()),
            state="readonly", width=17, font=("Segoe UI", 10))
        self._combo_paleta.set(PALETA_NOMBRES["oceano"])
        self._combo_paleta.grid(row=0, column=1, sticky="w", padx=(8, 16))
        self._combo_paleta.bind("<<ComboboxSelected>>", self._actualizar_preview)

        # Canvas previsualización: 3 bloques de color + descripción
        self._canvas_prev = tk.Canvas(fila_pal, width=180, height=26,
                                      bg=BLANCO, bd=0, highlightthickness=0)
        self._canvas_prev.grid(row=0, column=2, sticky="w", padx=(0, 12))

        self._lbl_desc = ttk.Label(fila_pal, text="", background=BLANCO,
                                   foreground=GRIS, font=("Segoe UI", 9, "italic"))
        self._lbl_desc.grid(row=0, column=3, sticky="w")

        self._actualizar_preview()   # pintar estado inicial

        # ── Nº diapositivas ────────────────────────────────────────
        fila_slides = ttk.Frame(card, style="Card.TFrame")
        fila_slides.grid(row=4, column=0, sticky="w", pady=(0, 12))
        ttk.Label(fila_slides, text="Nº de diapositivas", background=BLANCO,
                  font=("Segoe UI", 10, "bold")).pack(side="left")
        self.var_slides = tk.IntVar(value=8)
        ttk.Spinbox(fila_slides, from_=4, to=20,
                    textvariable=self.var_slides,
                    width=5, font=("Segoe UI", 10)).pack(side="left", padx=(8, 0))

        # ── Modelo ─────────────────────────────────────────────────
        fila_mod = ttk.Frame(card, style="Card.TFrame")
        fila_mod.grid(row=5, column=0, sticky="w", pady=(0, 4))
        ttk.Label(fila_mod, text="Modelo IA", background=BLANCO,
                  font=("Segoe UI", 10, "bold")).pack(side="left")
        self.var_modelo = tk.StringVar(value="haiku")
        tk.Radiobutton(fila_mod, text="Haiku  (rápido)",
                       variable=self.var_modelo, value="haiku",
                       bg=BLANCO, font=("Segoe UI", 10),
                       activebackground=BLANCO).pack(side="left", padx=(10, 0))
        tk.Radiobutton(fila_mod, text="Sonnet  (más potente)",
                       variable=self.var_modelo, value="sonnet",
                       bg=BLANCO, font=("Segoe UI", 10),
                       activebackground=BLANCO).pack(side="left", padx=(14, 0))

        # ── Abrir carpeta ──────────────────────────────────────────
        ttk.Separator(card, orient="horizontal").grid(row=6, column=0, sticky="ew", pady=(10, 10))
        self.var_abrir = tk.BooleanVar(value=True)
        ttk.Checkbutton(card, text="Abrir carpeta de destino al terminar",
                        variable=self.var_abrir).grid(row=7, column=0, sticky="w")

        # ── Progreso y botón ───────────────────────────────────────
        self.var_estado = tk.StringVar(value="")
        ttk.Label(outer, textvariable=self.var_estado,
                  style="Sub.TLabel").pack(anchor="w", pady=(14, 0))
        self.progress = ttk.Progressbar(outer, mode="indeterminate", length=400)
        self.progress.pack(fill="x", pady=(4, 14))
        self.btn_generar = ttk.Button(outer, text="✨  Generar presentación",
                                      style="Go.TButton", command=self.iniciar_generacion)
        self.btn_generar.pack(pady=(0, 4))

        # ── Posicionar: centrada, 5px del borde superior ───────────
        self.update_idletasks()
        w = self.winfo_reqwidth()
        h = self.winfo_reqheight()
        x = (self.winfo_screenwidth() - w) // 2
        self.geometry(f"{w}x{h}+{x}+5")

    # ── Preview de paleta ─────────────────────────────────────────────

    def _paleta_clave(self) -> str:
        nombre = self._combo_paleta.get()
        for clave, nom in PALETA_NOMBRES.items():
            if nom == nombre:
                return clave
        return "oceano"

    def _actualizar_preview(self, event=None):
        clave = self._paleta_clave()
        pal   = PALETAS[clave]
        cv    = self._canvas_prev
        cv.delete("all")

        colores = [
            ("#" + pal["dark"],      "Fondo"),
            ("#" + pal["primary"],   "Principal"),
            ("#" + pal["secondary"], "Secundario"),
        ]
        bw = 58   # ancho de cada bloque
        bh = 26   # alto

        for i, (color, etiqueta) in enumerate(colores):
            x0 = i * bw
            # Bloque de color
            cv.create_rectangle(x0, 0, x0 + bw, bh, fill=color, outline="")
            # Texto encima en blanco o negro según luminosidad
            r = int(color[1:3], 16)
            g = int(color[3:5], 16)
            b = int(color[5:7], 16)
            lum = 0.299*r + 0.587*g + 0.114*b
            txt_color = "#FFFFFF" if lum < 140 else "#333333"
            cv.create_text(x0 + bw//2, bh//2, text=etiqueta,
                           fill=txt_color, font=("Segoe UI", 7))

        self._lbl_desc.config(text=PALETA_DESC.get(clave, ""))

    # ── Acciones ──────────────────────────────────────────────────────

    def elegir_archivo(self):
        ruta = filedialog.askopenfilename(
            title="Selecciona el resumen Word",
            filetypes=[("Documentos Word", "*.docx"), ("Todos los archivos", "*.*")])
        if ruta:
            self.var_archivo.set(ruta)

    def iniciar_generacion(self):
        archivo = self.var_archivo.get().strip()
        if not archivo:
            messagebox.showwarning("Archivo no seleccionado",
                                   "Por favor selecciona un archivo .docx primero.")
            return
        if not os.path.exists(archivo):
            messagebox.showerror("Archivo no encontrado", f"No se encuentra:\n{archivo}")
            return
        if not cargar_api_key():
            messagebox.showerror("API key no encontrada",
                "No se encontró la API key.\n\n"
                "Comprueba que config.ini tiene:\n[claude]\napi_key = sk-ant-...")
            return
        self.btn_generar.config(state="disabled")
        self.progress.start(12)
        threading.Thread(target=self._generar, daemon=True).start()

    def _generar(self):
        archivo  = self.var_archivo.get().strip()
        paleta   = self._paleta_clave()
        n_slides = self.var_slides.get()
        modelo   = self.var_modelo.get()
        salida   = os.path.splitext(archivo)[0] + ".pptx"
        try:
            self._estado("📖  Leyendo documento...")
            contenido = leer_docx(archivo)
            self._estado(f"🤖  Consultando Claude {modelo.capitalize()}...")
            estructura = llamar_claude(contenido, n_slides, modelo)
            self._estado("🎨  Generando diapositivas...")
            generar_presentacion(estructura, PALETAS[paleta], salida)
            self._estado(f"✅  Listo: {os.path.basename(salida)}")
            self.after(0, lambda: self._fin_ok(salida))
        except requests.exceptions.HTTPError as e:
            self.after(0, lambda: self._fin_error(
                f"Error en la API de Claude:\n{e}\n\nComprueba tu API key."))
        except Exception as e:
            self.after(0, lambda: self._fin_error(str(e)))

    def _estado(self, texto):
        self.after(0, lambda: self.var_estado.set(texto))

    def _fin_ok(self, salida):
        self.progress.stop()
        self.progress["value"] = 0
        self.btn_generar.config(state="normal")
        messagebox.showinfo("¡Presentación generada!",
            f"Archivo guardado en:\n{salida}\n\n"
            f"Ábrelo en Word y exporta a PDF con Archivo → Exportar.")
        if self.var_abrir.get():
            os.startfile(os.path.dirname(salida))
        self.var_estado.set("")

    def _fin_error(self, mensaje):
        self.progress.stop()
        self.progress["value"] = 0
        self.btn_generar.config(state="normal")
        self.var_estado.set("❌  Error")
        messagebox.showerror("Error al generar", mensaje)
        self.var_estado.set("")


if __name__ == "__main__":
    app = App()
    app.mainloop()
