#!/usr/bin/env python3
"""Coleccion de juegos: Wordle · Spelling Bee · Ahorcado  (ES / EN)"""

import tkinter as tk
from tkinter import messagebox
import random, os, unicodedata

# ─── Colores ──────────────────────────────────────────────────────────────────
BG     = "#2c3e50"
BLUE   = "#3498db"
RED    = "#e74c3c"
GREEN  = "#27ae60"
YELLOW = "#f1c40f"
PURPLE = "#9b59b6"
ORANGE = "#e67e22"
GRAY   = "#7f8c8d"
WHITE  = "#ffffff"
DARK   = "#1a252f"

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# ─── Configuración por idioma ─────────────────────────────────────────────────
IDIOMAS = {
    "ES": {
        "nombre":      "Español",
        "bandera":     "🇪🇸",
        "ficheros":    ["diccionario.txt", "palabras.txt", "0_palabras_todas.txt"],
        "niveles_dic": [
            ("🟢", "Básico",       "rae_1000.txt"),
            ("🟡", "Intermedio",   "rae_5000.txt"),
            ("🔴", "Avanzado",     "0_palabras_todas.txt"),
        ],
        "teclado":     [
            list("QWERTYUIOP"),
            list("ASDFGHJKLÑ"),
            ["ENTER", *list("ZXCVBNM"), "DEL"],
        ],
        "letras_validas": "ABCDEFGHIJKLMNOPQRSTUVWXYZ",
        "wordle_defecto": [
            "CASCO","PERRO","GASTO","RATON","BOLSA","LUNAR","MONTE","PLAYA",
            "RADIO","FONDO","CLIMA","BELLO","CAMPO","DISCO","GLOBO","GRUTA",
            "HIELO","MAGIA","NOCHE","PADRE","QUESO","REINO","SALUD","TAREA",
            "VAPOR","ALETA","BRUMA","CANTO","DANZA","IDEAL","JARRO","LABIO",
            "MANDO","OVEJA","PATIO","RASPA","TANGO","VALOR","ZANJA","ABEJA",
            "BUZON","CAOBA","FLOTA","GANSO","HUECO","JUEGO","LIMON","MANGO",
            "NUEVO","OLIVO","RUEDA","SABOR","ASTRO","BARCO","CESTA","DUELO",
            "FERIA","GUSTO","HORNO","TALLO","VIAJE","ZURDO","ANCLA","BROTE",
            "CERDO","DULCE","GRAMO","LLANO","FALDA","LLAVE","PLAZA","TRIGO",
        ],
        "ahorcado_defecto": [
            "PYTHON","ORDENADOR","PROGRAMACION","TECLADO","MONITOR",
            "INTERNET","MUSICA","PELOTA","JARDIN","COCINA","VENTANA","PUERTA",
            "COLUMPIO","ESCUELA","BIBLIOTECA","OCEANO","DESIERTO","MARIPOSA",
            "ELEFANTE","JIRAFA","TORTUGA","DELFIN","CABALLERO","PRINCESA",
            "DRAGON","CASTILLO","AVENTURA","MISTERIO","CHOCOLATE","HELADO",
            "NARANJA","MANZANA","PLATANO","FRESA","INGENIERO","MATEMATICAS",
            "LITERATURA","GEOGRAFIA","DINOSAURIO","TELESCOPIO","MICROSCOPIO",
            "SUBMARINO","HELICOPTERO","PELICULA","TEATRO","PINTURA","ESQUELETO",
        ],
        "bee_defecto": [
            {
                "letras": ["A","S","O","R","P","H","C"],
                "central": "A",
                "palabras": {
                    "CARO","CASA","CAPA","COPA","ARCO","ROCA","SACO","ROPA",
                    "ORCA","RASO","CAPAS","ROCAS","ARCOS","COPAS","CAROS",
                    "PROSA","SACRO","PARCA","OCASO","COPAR",
                }
            },
            {
                "letras": ["E","R","A","N","T","I","M"],
                "central": "E",
                "palabras": {
                    "MARE","MIRA","MINA","ANIME","MENTA","MARTE","MITRE",
                    "MIREN","RAMEN","MIRAN","MARINE","MINERA","MENTE","TRAMO",
                }
            },
        ],
        "txt": {
            "titulo":       "Coleccion de Juegos",
            "elegir":       "Elige un juego",
            "dic_ok":       "Diccionario: {nombre}  |  {total:,} palabras  |  {cinco:,} de 5 letras",
            "dic_no":       "Sin diccionario externo — usando palabras de reserva\nColoca '{f}' junto al script para ampliar el vocabulario",
            "nivel_no":     "Fichero no encontrado — se usarán palabras de reserva",
            "wordle":       "W O R D L E",
            "bee":          "SPELLING BEE",
            "ahorcado":     "A H O R C A D O",
            "menu":         "<- Menu",
            "nueva":        "Nueva palabra",
            "nueva_p":      "Nuevo puzzle",
            "mezclar":      "Mezclar",
            "borrar":       "Borrar",
            "enviar":       "Enviar",
            "w_instruc":    "Adivina la palabra de 5 letras en 6 intentos.",
            "w_5letras":    "Escribe 5 letras",
            "w_correcto":   "Correcto!",
            "w_era":        "Era: {w}",
            "bee_instruc":  "Palabras de 4+ letras. La letra dorada ({c}) es obligatoria.",
            "bee_min4":     "Minimo 4 letras",
            "bee_central":  "Debe contener la '{c}'",
            "bee_nodispon": "Letra no disponible: '{c}'",
            "bee_yaencon":  "Ya la encontraste",
            "bee_noenc":    "Palabra no encontrada",
            "bee_puntos":   "Puntos: {p}/{m}",
            "bee_halladas": "Palabras encontradas:",
            "niveles":      ["Principiante","Novato","Bueno","Genial","Increible","Asombroso","GENIO"],
            "ah_incorrec":  "Letras incorrectas: -",
            "ah_incorrec2": "Letras incorrectas: {l}",
            "ah_gana_t":    "Ganaste!",
            "ah_gana_m":    "Correcto!\n\nLa palabra era:\n{w}",
            "ah_pierde_t":  "Perdiste",
            "ah_pierde_m":  "La palabra era:\n{w}",
            "ah_cargar":    "Cargar .txt",
            "ah_car_titulo":"Cargar lista de palabras",
            "ah_car_ok":    "{n} palabras cargadas desde\n«{f}»",
            "ah_car_pocas": "No se encontraron palabras válidas (mínimo 3 letras).",
            "ah_car_error": "Error al leer el fichero",
            "ah_tema":      "Lista: {f}",
        },
    },
    "EN": {
        "nombre":      "English",
        "bandera":     "🇬🇧",
        "ficheros":    ["words.txt", "words_alpha.txt", "english.txt", "popular.txt"],
        "niveles_dic": [
            ("🟢", "Basic",        "english1000.txt"),
            ("🟡", "Intermediate", "english5000.txt"),
            ("🔴", "Advanced",     "words_alpha.txt"),
        ],
        "teclado":     [
            list("QWERTYUIOP"),
            list("ASDFGHJKL"),
            ["ENTER", *list("ZXCVBNM"), "DEL"],
        ],
        "letras_validas": "ABCDEFGHIJKLMNOPQRSTUVWXYZ",
        "wordle_defecto": [
            "CRANE","SLATE","HOUSE","PLANT","BRAIN","CLOCK","STORM","FLAME",
            "GRIND","CHIME","BLAZE","FROST","GLOOM","PRIDE","THORN","SWIFT",
            "CRISP","DROWN","FLINT","GRAZE","HATCH","JOUST","KNELT","LYMPH",
            "MULCH","NYMPH","OXIDE","PLUMB","QUART","RIGID","SCALP","THYME",
            "USHER","VENOM","WALTZ","YEARN","ZESTY","ABHOR","BIRCH","CINCH",
            "DWARF","EXPEL","FLAIR","GLYPH","HOVER","INTER","JAZZY","KNACK",
            "LOFTY","MARSH","NOTCH","OPTIC","PERCH","QUELL","RETCH","SMIRK",
            "TRUCE","UNIFY","VOUCH","WRING","XYLEM","YACHT","ZILCH","AXIOM",
        ],
        "ahorcado_defecto": [
            "PYTHON","KEYBOARD","PROGRAMMING","MONITOR","INTERNET","ELEPHANT",
            "BUTTERFLY","TELESCOPE","ADVENTURE","CHOCOLATE","UNIVERSITY",
            "LIBRARY","SUBMARINE","HELICOPTER","GEOGRAPHY","MATHEMATICS",
            "DINOSAUR","MICROSCOPE","PHOTOGRAPHY","SCULPTURE","ARCHITECTURE",
            "REVOLUTION","IMAGINATION","EXTRAORDINARY","MYSTERIOUS","FANTASTIC",
            "WILDERNESS","ATMOSPHERE","CIVILIZATION","TOURNAMENT","PHILOSOPHY",
        ],
        "bee_defecto": [
            {
                "letras": ["A","R","T","I","N","G","E"],
                "central": "A",
                "palabras": {
                    "EARN","GRIN","GAIT","RAIN","RANT","RAGE","RING","REIN",
                    "GAIN","GATE","GRATE","TRAIN","GRAIN","TIGER","IRATE",
                    "TRIAGE","RATING","GAITER","TEARING","GRANITE","TANGERINE",
                }
            },
            {
                "letras": ["O","C","E","S","L","P","A"],
                "central": "O",
                "palabras": {
                    "COAL","COPE","COLA","POLE","PALE","OPAL","SLOPE","PLACE",
                    "CLOSE","SCOPE","SCALP","PETAL","SPACE","PLEAS","OCTAL",
                    "LOCALE","PLACES","PALACE","CAPOLES",
                }
            },
        ],
        "txt": {
            "titulo":       "Games Collection",
            "elegir":       "Choose a game",
            "dic_ok":       "Dictionary: {nombre}  |  {total:,} words  |  {cinco:,} of 5 letters",
            "dic_no":       "No external dictionary found — using built-in words\nPlace '{f}' next to the script to expand vocabulary",
            "nivel_no":     "File not found — built-in words will be used",
            "wordle":       "W O R D L E",
            "bee":          "SPELLING BEE",
            "ahorcado":     "H A N G M A N",
            "menu":         "<- Menu",
            "nueva":        "New word",
            "nueva_p":      "New puzzle",
            "mezclar":      "Shuffle",
            "borrar":       "Delete",
            "enviar":       "Enter",
            "w_instruc":    "Guess the 5-letter word in 6 attempts.",
            "w_5letras":    "Type 5 letters",
            "w_correcto":   "Correct!",
            "w_era":        "It was: {w}",
            "bee_instruc":  "Words of 4+ letters. The golden letter ({c}) is required.",
            "bee_min4":     "Minimum 4 letters",
            "bee_central":  "Must contain '{c}'",
            "bee_nodispon": "Letter not available: '{c}'",
            "bee_yaencon":  "Already found!",
            "bee_noenc":    "Word not found",
            "bee_puntos":   "Points: {p}/{m}",
            "bee_halladas": "Found words:",
            "niveles":      ["Beginner","Novice","Good","Great","Amazing","Awesome","GENIUS"],
            "ah_incorrec":  "Wrong letters: -",
            "ah_incorrec2": "Wrong letters: {l}",
            "ah_gana_t":    "You won!",
            "ah_gana_m":    "Correct!\n\nThe word was:\n{w}",
            "ah_pierde_t":  "Game over",
            "ah_pierde_m":  "The word was:\n{w}",
            "ah_cargar":    "Load .txt",
            "ah_car_titulo":"Load word list",
            "ah_car_ok":    "{n} words loaded from\n«{f}»",
            "ah_car_pocas": "No valid words found (minimum 3 letters).",
            "ah_car_error": "Error reading file",
            "ah_tema":      "List: {f}",
        },
    },
}


# ─── Utilidades ───────────────────────────────────────────────────────────────
def quitar_tildes(texto):
    res = []
    for c in unicodedata.normalize("NFD", texto):
        if unicodedata.category(c) == "Mn":
            continue
        res.append(c)
    return "".join(res)


def cargar_diccionario(idioma_key, fichero=None):
    """
    Carga un diccionario. Si se pasa 'fichero', intenta ese primero.
    Si no, recorre la lista de ficheros del idioma en orden.
    """
    cfg = IDIOMAS[idioma_key]
    candidatos = ([fichero] if fichero else []) + cfg["ficheros"]
    for nombre in candidatos:
        if not nombre:
            continue
        ruta = os.path.join(SCRIPT_DIR, nombre)
        if os.path.isfile(ruta):
            try:
                with open(ruta, encoding="utf-8", errors="ignore") as f:
                    raw = [l.strip() for l in f if l.strip()]
                validas = cfg["letras_validas"]
                palabras = []
                for p in raw:
                    p = quitar_tildes(p.upper())
                    if p.isalpha() and all(c in validas for c in p):
                        palabras.append(p)
                return ruta, palabras
            except Exception:
                continue
    return None, []


def generar_puzzles_bee(pool):
    candidatos = [p for p in pool if 4 <= len(p) <= 12]
    if len(candidatos) < 20:
        return None
    puzzles = []
    intentos = 0
    while len(puzzles) < 8 and intentos < 300:
        intentos += 1
        semilla = random.choice(candidatos)
        letras_base = list(dict.fromkeys(semilla))
        if len(letras_base) > 7:
            continue
        frecuentes = list("AEIOURLSTNMDPCBGFHVQYZJXKW")
        for c in frecuentes:
            if len(letras_base) >= 7:
                break
            if c not in letras_base:
                letras_base.append(c)
        letras7 = letras_base[:7]
        frz = frozenset(letras7)
        mejor_puzzle, mejor_count = None, 0
        for central in letras7:
            if central not in "AEIOU":
                continue
            validas = frozenset(p for p in candidatos if set(p) <= frz and central in p)
            n = len(validas)
            if 15 <= n <= 80 and n > mejor_count:
                mejor_count = n
                mejor_puzzle = {"letras": letras7, "central": central, "palabras": validas}
        if mejor_puzzle:
            puzzles.append(mejor_puzzle)
    return puzzles if puzzles else None


# ══════════════════════════════════════════════════════════════════════════════
#  APP PRINCIPAL
# ══════════════════════════════════════════════════════════════════════════════
class JuegosApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Games / Juegos")
        w, h = 680, 760
        x = (self.winfo_screenwidth() - w) // 2
        self.geometry(f"{w}x{h}+{x}+20")
        self.configure(bg=BG)
        self.resizable(False, False)

        self.idioma      = None   # "ES" o "EN"
        self.dic_ruta    = None
        self.dic_palabras= []

        self.main = tk.Frame(self, bg=BG)
        self.main.pack(fill="both", expand=True, padx=20, pady=20)

        self.elegir_idioma()

    def limpiar(self):
        for w in self.main.winfo_children():
            w.destroy()
        try:
            self.unbind("<Key>")
        except Exception:
            pass

    # ── Pantalla de selección de idioma + nivel ───────────────────────────────
    def elegir_idioma(self):
        self.limpiar()

        tk.Label(self.main, text="🎮",
                 font=("Helvetica", 44), bg=BG, fg=WHITE).pack(pady=(30, 4))
        tk.Label(self.main, text="Games · Juegos",
                 font=("Helvetica", 26, "bold"), bg=BG, fg=WHITE).pack(pady=(0, 30))

        # ── Sección idioma
        tk.Label(self.main, text="Choose a language / Elige un idioma",
                 font=("Helvetica", 12), bg=BG, fg="#bdc3c7").pack(pady=(0, 10))

        idioma_frame = tk.Frame(self.main, bg=BG)
        idioma_frame.pack()

        self._btn_idioma = {}
        for key, cfg in IDIOMAS.items():
            btn = tk.Button(
                idioma_frame,
                text=f"{cfg['bandera']}  {cfg['nombre']}",
                font=("Helvetica", 13, "bold"),
                bg="#4a5568", fg=WHITE,
                width=16, height=2,
                relief="flat", cursor="hand2",
                command=lambda k=key: self._seleccionar_idioma_ui(k))
            btn.pack(side="left", padx=8)
            self._btn_idioma[key] = btn

        # ── Separador
        tk.Frame(self.main, bg="#4a5568", height=1).pack(fill="x", pady=20)

        # ── Sección nivel
        tk.Label(self.main, text="Choose a level / Elige un nivel",
                 font=("Helvetica", 12), bg=BG, fg="#bdc3c7").pack(pady=(0, 10))

        self._nivel_frame = tk.Frame(self.main, bg=BG)
        self._nivel_frame.pack()

        # Aviso de disponibilidad de ficheros (se rellena al elegir idioma)
        self._lbl_nivel_info = tk.Label(self.main, text="",
                                        font=("Helvetica", 9, "italic"),
                                        bg=BG, fg="#bdc3c7",
                                        justify="center")
        self._lbl_nivel_info.pack(pady=(8, 0))

        # ── Botón Jugar (oculto hasta que se elija idioma Y nivel)
        self._btn_jugar_frame = tk.Frame(self.main, bg=BG)
        self._btn_jugar_frame.pack(pady=30)

        # Estado interno
        self._idioma_sel = None
        self._nivel_sel  = None   # (emoji, label, fichero)
        self._btn_nivel  = {}

        # Si venimos de una partida, preseleccionar lo que había
        if self.idioma:
            self._seleccionar_idioma_ui(self.idioma, presel_fichero=self.dic_ruta)

    def _seleccionar_idioma_ui(self, key, presel_fichero=None):
        """Resalta el idioma elegido y muestra los botones de nivel."""
        self._idioma_sel = key

        # Actualizar colores botones idioma
        for k, btn in self._btn_idioma.items():
            btn.config(bg=BLUE if k == key else "#4a5568")

        # Limpiar nivel frame
        for w in self._nivel_frame.winfo_children():
            w.destroy()
        self._btn_nivel = {}
        self._nivel_sel = None

        cfg = IDIOMAS[key]

        # Construir botones de nivel con indicador de disponibilidad
        disponibles = []
        for emoji, label, fichero in cfg["niveles_dic"]:
            existe = os.path.isfile(os.path.join(SCRIPT_DIR, fichero))
            disponibles.append((emoji, label, fichero, existe))

        info_lines = []
        for emoji, label, fichero, existe in disponibles:
            color_btn = "#4a5568"
            estado    = "normal"
            if not existe:
                color_btn = "#2d3748"
                estado    = "disabled"
                info_lines.append(f"{'✓' if existe else '✗'} {label}: {fichero}")
            else:
                info_lines.append(f"✓ {label}: {fichero}")

            btn = tk.Button(
                self._nivel_frame,
                text=f"{emoji}  {label}",
                font=("Helvetica", 13, "bold"),
                bg=color_btn, fg=WHITE if existe else GRAY,
                width=14, height=2,
                relief="flat",
                cursor="hand2" if existe else "arrow",
                state=estado,
                command=lambda e=emoji, l=label, f=fichero: self._seleccionar_nivel_ui(e, l, f))
            btn.pack(side="left", padx=8)
            self._btn_nivel[(emoji, label, fichero)] = btn

        self._lbl_nivel_info.config(text="   ".join(info_lines))

        # Si venimos con un fichero preseleccionado, marcar el nivel correspondiente
        if presel_fichero:
            nombre = os.path.basename(presel_fichero)
            for emoji, label, fichero, existe in disponibles:
                if fichero == nombre and existe:
                    self._seleccionar_nivel_ui(emoji, label, fichero)
                    break

        # Limpiar botón jugar
        for w in self._btn_jugar_frame.winfo_children():
            w.destroy()

    def _seleccionar_nivel_ui(self, emoji, label, fichero):
        """Resalta el nivel elegido y muestra el botón Jugar."""
        self._nivel_sel = (emoji, label, fichero)
        cfg_idioma = IDIOMAS[self._idioma_sel]

        for (e, l, f), btn in self._btn_nivel.items():
            existe = os.path.isfile(os.path.join(SCRIPT_DIR, f))
            if (e, l, f) == (emoji, label, fichero):
                # Color según nivel
                colores = {"🟢": GREEN, "🟡": YELLOW, "🔴": RED}
                btn.config(bg=colores.get(emoji, BLUE),
                           fg=BG if emoji == "🟡" else WHITE)
            elif existe:
                btn.config(bg="#4a5568", fg=WHITE)

        # Mostrar / actualizar botón Jugar
        for w in self._btn_jugar_frame.winfo_children():
            w.destroy()
        lbl_jugar = "▶  Play" if self._idioma_sel == "EN" else "▶  Jugar"
        tk.Button(self._btn_jugar_frame,
                  text=lbl_jugar,
                  font=("Helvetica", 15, "bold"),
                  bg=GREEN, fg=WHITE,
                  width=18, height=2,
                  relief="flat", cursor="hand2",
                  command=self._confirmar_seleccion).pack()

    def _confirmar_seleccion(self):
        if not self._idioma_sel or not self._nivel_sel:
            return
        emoji, label, fichero = self._nivel_sel
        self.idioma = self._idioma_sel
        self.dic_ruta, self.dic_palabras = cargar_diccionario(self.idioma, fichero)
        self.nivel_nombre = label
        self.mostrar_menu()

    # ── Menú principal ────────────────────────────────────────────────────────
    def mostrar_menu(self):
        self.limpiar()
        cfg = IDIOMAS[self.idioma]
        txt = cfg["txt"]

        # Botón cambiar idioma/nivel
        top = tk.Frame(self.main, bg=BG)
        top.pack(fill="x")
        lbl_cambiar = "🌐 Change language / level" if self.idioma == "EN" else "🌐 Cambiar idioma / nivel"
        tk.Button(top, text=lbl_cambiar,
                  bg="#4a5568", fg=WHITE, font=("Helvetica", 9, "bold"),
                  relief="flat", cursor="hand2",
                  command=self.elegir_idioma).pack(side="right")

        tk.Label(self.main, text=txt["titulo"],
                 font=("Helvetica", 24, "bold"), bg=BG, fg=WHITE).pack(pady=(16, 6))

        # Estado del diccionario + nivel activo
        nivel = getattr(self, "nivel_nombre", "")
        if self.dic_ruta:
            nombre  = os.path.basename(self.dic_ruta)
            n_cinco = len([p for p in self.dic_palabras if len(p) == 5])
            dic_texto = txt["dic_ok"].format(
                nombre=nombre, total=len(self.dic_palabras), cinco=n_cinco)
            if nivel:
                dic_texto = f"Nivel: {nivel}  ·  " + dic_texto
            dic_color = GREEN
        else:
            dic_texto = txt["dic_no"].format(f=cfg["ficheros"][0])
            if nivel:
                dic_texto = f"Nivel: {nivel}  ·  " + dic_texto
            dic_color = ORANGE
        tk.Label(self.main, text=dic_texto,
                 font=("Helvetica", 10), bg=BG, fg=dic_color,
                 justify="center").pack(pady=(0, 24))

        juegos = [
            (txt["wordle"],   BLUE,   self.abrir_wordle),
            (txt["bee"],      YELLOW, self.abrir_spelling_bee),
            (txt["ahorcado"], PURPLE, self.abrir_ahorcado),
        ]
        for texto, color, cmd in juegos:
            fg = BG if color == YELLOW else WHITE
            tk.Button(self.main, text=texto,
                      font=("Helvetica", 14, "bold"),
                      bg=color, fg=fg, width=26, height=2,
                      relief="flat", cursor="hand2",
                      command=cmd).pack(pady=12)

    def _palabras_wordle(self):
        if self.dic_palabras:
            cinco = [p for p in self.dic_palabras if len(p) == 5]
            if cinco:
                return cinco
        return IDIOMAS[self.idioma]["wordle_defecto"]

    def _palabras_ahorcado(self):
        if self.dic_palabras:
            rango = [p for p in self.dic_palabras if 5 <= len(p) <= 15]
            if rango:
                return rango
        return IDIOMAS[self.idioma]["ahorcado_defecto"]

    def _puzzles_bee(self):
        if self.dic_palabras:
            gen = generar_puzzles_bee(self.dic_palabras)
            if gen:
                return gen
        return IDIOMAS[self.idioma]["bee_defecto"]

    def abrir_wordle(self):
        self.limpiar()
        WordleGame(self.main, self.mostrar_menu,
                   self._palabras_wordle(), IDIOMAS[self.idioma])

    def abrir_spelling_bee(self):
        self.limpiar()
        SpellingBeeGame(self.main, self.mostrar_menu,
                        self._puzzles_bee(), IDIOMAS[self.idioma])

    def abrir_ahorcado(self):
        self.limpiar()
        AhorcadoGame(self.main, self.mostrar_menu,
                     self._palabras_ahorcado(), IDIOMAS[self.idioma])


# ══════════════════════════════════════════════════════════════════════════════
#  WORDLE
# ══════════════════════════════════════════════════════════════════════════════
class WordleGame:
    def __init__(self, parent, volver_cb, palabras, cfg):
        self.parent    = parent
        self.volver_cb = volver_cb
        self.palabras  = palabras
        self.cfg       = cfg
        self.txt       = cfg["txt"]
        self._nueva_partida()

    def _nueva_partida(self):
        self.secreta  = random.choice(self.palabras)
        self.intentos = 0
        self.max_int  = 6
        self.actual   = ""
        self._construir_ui()

    def _limpiar(self):
        for w in self.parent.winfo_children():
            w.destroy()

    def _construir_ui(self):
        self._limpiar()
        cab = tk.Frame(self.parent, bg=BG)
        cab.pack(fill="x", pady=(0, 8))
        tk.Button(cab, text=self.txt["menu"], bg=RED, fg=WHITE,
                  font=("Helvetica", 10, "bold"), relief="flat", cursor="hand2",
                  command=self._volver).pack(side="left")
        tk.Label(cab, text=self.txt["wordle"],
                 font=("Helvetica", 22, "bold"), bg=BG, fg=WHITE).pack(side="left", expand=True)

        tk.Label(self.parent, text=self.txt["w_instruc"],
                 font=("Helvetica", 10), bg=BG, fg="#bdc3c7").pack(pady=(0, 6))

        grid = tk.Frame(self.parent, bg=BG)
        grid.pack(pady=4)
        self.celdas = []
        for i in range(6):
            fila = []
            for j in range(5):
                lbl = tk.Label(grid, text="", width=3,
                               font=("Helvetica", 22, "bold"),
                               bg=WHITE, fg=BG, relief="solid", bd=2)
                lbl.grid(row=i, column=j, padx=3, pady=3, ipady=6)
                fila.append(lbl)
            self.celdas.append(fila)

        self.lbl_msg = tk.Label(self.parent, text="",
                                font=("Helvetica", 12, "bold"), bg=BG, fg=WHITE)
        self.lbl_msg.pack(pady=4)

        teclado = tk.Frame(self.parent, bg=BG)
        teclado.pack(pady=4)
        self.teclas = {}
        for fila in self.cfg["teclado"]:
            fr = tk.Frame(teclado, bg=BG)
            fr.pack(pady=2)
            for letra in fila:
                if letra == "ENTER":
                    bg, w, cmd = GREEN, 5, self._enviar
                elif letra == "DEL":
                    bg, w, cmd = RED,   4, self._borrar
                else:
                    bg, w = "#4a5568", 3
                    cmd = lambda l=letra: self._agregar(l)
                btn = tk.Button(fr, text=letra, width=w, height=1,
                                bg=bg, fg=WHITE, relief="flat",
                                font=("Helvetica", 10, "bold"),
                                cursor="hand2", command=cmd)
                btn.pack(side="left", padx=1)
                self.teclas[letra] = btn

        tk.Button(self.parent, text=self.txt["nueva"], bg=BLUE, fg=WHITE,
                  font=("Helvetica", 11, "bold"), relief="flat", cursor="hand2",
                  command=self._nueva_partida).pack(pady=10)

        self.parent.winfo_toplevel().bind("<Key>", self._key_fisico)

    def _volver(self):
        self.parent.winfo_toplevel().unbind("<Key>")
        self.volver_cb()

    def _key_fisico(self, event):
        k = quitar_tildes(event.keysym.upper())
        if k == "RETURN":
            self._enviar()
        elif k == "BACKSPACE":
            self._borrar()
        elif len(k) == 1 and k.isalpha():
            self._agregar(k)

    def _agregar(self, letra):
        if self.intentos >= self.max_int or len(self.actual) >= 5:
            return
        self.actual += letra
        self._refrescar_fila()

    def _borrar(self):
        if self.actual:
            self.actual = self.actual[:-1]
            self._refrescar_fila()

    def _refrescar_fila(self):
        for j in range(5):
            txt = self.actual[j] if j < len(self.actual) else ""
            self.celdas[self.intentos][j].config(text=txt, bg=WHITE, fg=BG)

    def _enviar(self):
        if self.intentos >= self.max_int:
            return
        if len(self.actual) != 5:
            self.lbl_msg.config(text=self.txt["w_5letras"], fg=ORANGE)
            return
        intento = self.actual.upper()
        secreta = self.secreta
        colores = [""] * 5
        conteo  = {}
        for c in secreta:
            conteo[c] = conteo.get(c, 0) + 1
        for j in range(5):
            if intento[j] == secreta[j]:
                colores[j] = GREEN
                conteo[intento[j]] -= 1
        for j in range(5):
            if colores[j]:
                continue
            if intento[j] in conteo and conteo[intento[j]] > 0:
                colores[j] = YELLOW
                conteo[intento[j]] -= 1
            else:
                colores[j] = GRAY
        for j in range(5):
            self.celdas[self.intentos][j].config(
                text=intento[j], bg=colores[j], fg=WHITE, relief="solid")
            btn = self.teclas.get(intento[j])
            if btn and btn.cget("bg") != GREEN:
                btn.config(bg=colores[j])
        if intento == secreta:
            self.lbl_msg.config(text=self.txt["w_correcto"], fg=GREEN)
            self.intentos = self.max_int
            self.parent.winfo_toplevel().unbind("<Key>")
            return
        self.intentos += 1
        self.actual = ""
        if self.intentos >= self.max_int:
            self.lbl_msg.config(text=self.txt["w_era"].format(w=secreta), fg=RED)
            self.parent.winfo_toplevel().unbind("<Key>")


# ══════════════════════════════════════════════════════════════════════════════
#  SPELLING BEE
# ══════════════════════════════════════════════════════════════════════════════
class SpellingBeeGame:
    def __init__(self, parent, volver_cb, puzzles, cfg):
        self.parent    = parent
        self.volver_cb = volver_cb
        self.puzzles   = puzzles
        self.cfg       = cfg
        self.txt       = cfg["txt"]
        self._nuevo_puzzle()

    def _limpiar(self):
        for w in self.parent.winfo_children():
            w.destroy()

    def _nuevo_puzzle(self):
        p = random.choice(self.puzzles)
        self.central           = p["central"]
        perifericas            = [l for l in p["letras"] if l != self.central]
        random.shuffle(perifericas)
        self.perifericas       = perifericas
        self.diccionario       = {w.upper() for w in p["palabras"]}
        self.palabra_actual    = ""
        self.palabras_halladas = set()
        self.puntos            = 0
        self.max_puntos        = sum(1 if len(w) == 4 else len(w) for w in self.diccionario)
        self._construir_ui()

    def _construir_ui(self):
        self._limpiar()
        cab = tk.Frame(self.parent, bg=BG)
        cab.pack(fill="x", pady=(0, 6))
        tk.Button(cab, text=self.txt["menu"], bg=RED, fg=WHITE,
                  font=("Helvetica", 10, "bold"), relief="flat", cursor="hand2",
                  command=self._volver).pack(side="left")
        tk.Label(cab, text=self.txt["bee"],
                 font=("Helvetica", 19, "bold"), bg=BG, fg=YELLOW).pack(side="left", expand=True)

        info = tk.Frame(self.parent, bg=BG)
        info.pack(fill="x", pady=4)
        self.lbl_puntos = tk.Label(info,
                                   text=self.txt["bee_puntos"].format(p=0, m=self.max_puntos),
                                   font=("Helvetica", 13, "bold"), bg=BG, fg=WHITE)
        self.lbl_puntos.pack(side="left", padx=20)
        self.lbl_nivel = tk.Label(info, text=self.txt["niveles"][0],
                                  font=("Helvetica", 13, "bold"), bg=BG, fg=YELLOW)
        self.lbl_nivel.pack(side="left")

        tk.Label(self.parent,
                 text=self.txt["bee_instruc"].format(c=self.central),
                 font=("Helvetica", 10), bg=BG, fg="#bdc3c7",
                 justify="center").pack(pady=(0, 8))

        self.btn_frame = tk.Frame(self.parent, bg=BG)
        self.btn_frame.pack(pady=6)
        self.btns_letra = {}
        self._empaquetar_botones(self.perifericas)

        self.lbl_entrada = tk.Label(self.parent, text="",
                                    font=("Helvetica", 24, "bold"),
                                    bg=WHITE, fg=BG,
                                    width=18, relief="solid", bd=2, anchor="center")
        self.lbl_entrada.pack(pady=8)

        ctrl = tk.Frame(self.parent, bg=BG)
        ctrl.pack(pady=4)
        for texto, color, cmd in [
            (self.txt["mezclar"], PURPLE,    self._mezclar),
            (self.txt["borrar"],  ORANGE,    self._borrar),
            (self.txt["enviar"],  GREEN,     self._enviar),
            (self.txt["nueva_p"],"#4a5568", self._nuevo_puzzle),
        ]:
            tk.Button(ctrl, text=texto, bg=color, fg=WHITE,
                      font=("Helvetica", 11, "bold"), relief="flat",
                      cursor="hand2", command=cmd).pack(side="left", padx=4)

        self.lbl_fb = tk.Label(self.parent, text="",
                               font=("Helvetica", 12, "bold"), bg=BG)
        self.lbl_fb.pack(pady=2)

        tk.Label(self.parent, text=self.txt["bee_halladas"],
                 font=("Helvetica", 11), bg=BG, fg=WHITE).pack()
        lista_f = tk.Frame(self.parent)
        lista_f.pack(fill="both", expand=True, padx=30, pady=4)
        sb = tk.Scrollbar(lista_f)
        sb.pack(side="right", fill="y")
        self.texto_lista = tk.Text(lista_f, height=7, width=44,
                                   font=("Helvetica", 11),
                                   yscrollcommand=sb.set,
                                   state="disabled",
                                   bg=DARK, fg=WHITE, relief="flat")
        self.texto_lista.pack(side="left", fill="both", expand=True)
        sb.config(command=self.texto_lista.yview)
        self.parent.winfo_toplevel().bind("<Key>", self._key_fisico)

    def _empaquetar_botones(self, orden_perifericas):
        for w in self.btn_frame.winfo_children():
            w.destroy()
        self.btns_letra = {}
        for letra in orden_perifericas:
            btn = tk.Button(self.btn_frame, text=letra,
                            font=("Helvetica", 20, "bold"),
                            width=3, height=1, bg=BLUE, fg=WHITE,
                            relief="flat", cursor="hand2",
                            command=lambda l=letra: self._agregar(l))
            btn.pack(side="left", padx=4)
            self.btns_letra[letra] = btn
        btn_c = tk.Button(self.btn_frame, text=self.central,
                          font=("Helvetica", 20, "bold"),
                          width=3, height=1, bg=YELLOW, fg=BG,
                          relief="groove", cursor="hand2",
                          command=lambda: self._agregar(self.central))
        btn_c.pack(side="left", padx=4)
        self.btns_letra[self.central] = btn_c

    def _volver(self):
        self.parent.winfo_toplevel().unbind("<Key>")
        self.volver_cb()

    def _key_fisico(self, event):
        k = quitar_tildes(event.keysym.upper())
        todas = set(self.perifericas) | {self.central}
        if k == "RETURN":
            self._enviar()
        elif k == "BACKSPACE":
            self._borrar()
        elif len(k) == 1 and k.isalpha() and k in todas:
            self._agregar(k)

    def _agregar(self, letra):
        self.palabra_actual += letra
        self.lbl_entrada.config(text=self.palabra_actual)

    def _borrar(self):
        self.palabra_actual = self.palabra_actual[:-1]
        self.lbl_entrada.config(text=self.palabra_actual)

    def _mezclar(self):
        random.shuffle(self.perifericas)
        self._empaquetar_botones(self.perifericas)

    def _enviar(self):
        p = self.palabra_actual.upper()
        self.palabra_actual = ""
        self.lbl_entrada.config(text="")
        txt = self.txt
        if len(p) < 4:
            self._feedback(txt["bee_min4"], ORANGE); return
        if self.central not in p:
            self._feedback(txt["bee_central"].format(c=self.central), RED); return
        todas = set(self.perifericas) | {self.central}
        for c in p:
            if c not in todas:
                self._feedback(txt["bee_nodispon"].format(c=c), RED); return
        if p in self.palabras_halladas:
            self._feedback(txt["bee_yaencon"], ORANGE); return
        if p in self.diccionario:
            pts = 1 if len(p) == 4 else len(p)
            self.palabras_halladas.add(p)
            self.puntos += pts
            self._actualizar_puntuacion()
            self._feedback(f"+{pts} pt{'s' if pts > 1 else ''}!", GREEN)
            self.texto_lista.config(state="normal")
            self.texto_lista.insert(tk.END, f"  {p}  ({pts} pt{'s' if pts > 1 else ''})\n")
            self.texto_lista.see(tk.END)
            self.texto_lista.config(state="disabled")
        else:
            self._feedback(txt["bee_noenc"], RED)

    def _feedback(self, msg, color):
        self.lbl_fb.config(text=msg, fg=color)
        self.parent.after(2000, lambda: self.lbl_fb.config(text=""))

    def _actualizar_puntuacion(self):
        self.lbl_puntos.config(
            text=self.txt["bee_puntos"].format(p=self.puntos, m=self.max_puntos))
        pct = self.puntos / max(self.max_puntos, 1) * 100
        umbrales = [10, 25, 40, 55, 70, 90, 101]
        nivel = self.txt["niveles"][next(i for i, u in enumerate(umbrales) if pct < u)]
        self.lbl_nivel.config(text=nivel)


# ══════════════════════════════════════════════════════════════════════════════
#  AHORCADO / HANGMAN
# ══════════════════════════════════════════════════════════════════════════════
class AhorcadoGame:
    MAX_ERRORES = 7

    def __init__(self, parent, volver_cb, palabras, cfg):
        self.parent    = parent
        self.volver_cb = volver_cb
        self.palabras  = palabras
        self.cfg       = cfg
        self.txt       = cfg["txt"]
        self._nueva_partida()

    def _limpiar(self):
        for w in self.parent.winfo_children():
            w.destroy()

    def _nueva_partida(self):
        self.palabra    = random.choice(self.palabras).upper()
        self.letras_ok  = set()
        self.letras_mal = set()
        self.errores    = 0
        self._construir_ui()

    def _construir_ui(self):
        self._limpiar()
        cab = tk.Frame(self.parent, bg=BG)
        cab.pack(fill="x", pady=(0, 4))
        tk.Button(cab, text=self.txt["menu"], bg=RED, fg=WHITE,
                  font=("Helvetica", 10, "bold"), relief="flat", cursor="hand2",
                  command=self._volver).pack(side="left")
        tk.Button(cab, text=self.txt["ah_cargar"], bg="#4a5568", fg=WHITE,
                  font=("Helvetica", 10, "bold"), relief="flat", cursor="hand2",
                  command=self._cargar_txt).pack(side="right")
        tk.Label(cab, text=self.txt["ahorcado"],
                 font=("Helvetica", 22, "bold"), bg=BG, fg=WHITE).pack(side="left", expand=True)

        # Etiqueta de tema activo (solo visible cuando hay lista cargada)
        tema = getattr(self, "tema_nombre", None)
        if tema:
            tk.Label(self.parent,
                     text=self.txt["ah_tema"].format(f=tema),
                     font=("Helvetica", 9, "italic"), bg=BG, fg=YELLOW).pack()

        self.canvas = tk.Canvas(self.parent, width=260, height=210,
                                bg=DARK, highlightthickness=0)
        self.canvas.pack(pady=4)
        self._dibujar_horca()

        self.lbl_palabra = tk.Label(self.parent,
                                    text=self._mostrar_palabra(),
                                    font=("Courier", 22, "bold"), bg=BG, fg=WHITE)
        self.lbl_palabra.pack(pady=6)

        self.lbl_falladas = tk.Label(self.parent,
                                     text=self.txt["ah_incorrec"],
                                     font=("Helvetica", 11), bg=BG, fg=RED)
        self.lbl_falladas.pack()

        teclado = tk.Frame(self.parent, bg=BG)
        teclado.pack(pady=8)
        self.btns_kbd = {}
        for fila in self.cfg["teclado"]:
            letras = [l for l in fila if l not in ("ENTER", "DEL")]
            fr = tk.Frame(teclado, bg=BG)
            fr.pack(pady=2)
            for letra in letras:
                btn = tk.Button(fr, text=letra, width=3, height=1,
                                font=("Helvetica", 11, "bold"),
                                bg="#4a5568", fg=WHITE, relief="flat",
                                cursor="hand2",
                                command=lambda l=letra: self._adivinar(l))
                btn.pack(side="left", padx=1)
                self.btns_kbd[letra] = btn

        tk.Button(self.parent, text=self.txt["nueva"], bg=BLUE, fg=WHITE,
                  font=("Helvetica", 11, "bold"), relief="flat", cursor="hand2",
                  command=self._nueva_partida).pack(pady=8)

        self.parent.winfo_toplevel().bind("<Key>", self._key_fisico)

    def _volver(self):
        self.parent.winfo_toplevel().unbind("<Key>")
        self.volver_cb()

    def _cargar_txt(self):
        from tkinter import filedialog
        ruta = filedialog.askopenfilename(
            title=self.txt["ah_car_titulo"],
            filetypes=[("Texto", "*.txt"), ("Todos", "*.*")])
        if not ruta:
            return
        try:
            with open(ruta, encoding="utf-8", errors="ignore") as f:
                raw = [l.strip() for l in f if l.strip()]
            validas_letras = self.cfg["letras_validas"]
            nuevas = []
            for p in raw:
                p = quitar_tildes(p.upper())
                if p.isalpha() and len(p) >= 3 and all(c in validas_letras for c in p):
                    nuevas.append(p)
            if not nuevas:
                messagebox.showwarning(
                    self.txt["ah_car_titulo"],
                    self.txt["ah_car_pocas"])
                return
            self.palabras    = nuevas
            self.tema_nombre = os.path.basename(ruta)
            messagebox.showinfo(
                self.txt["ah_car_titulo"],
                self.txt["ah_car_ok"].format(n=len(nuevas), f=self.tema_nombre))
            self._nueva_partida()
        except Exception as e:
            messagebox.showerror(self.txt["ah_car_error"], str(e))

    def _key_fisico(self, event):
        k = quitar_tildes(event.keysym.upper())
        if len(k) == 1 and k.isalpha() and k in self.btns_kbd:
            self._adivinar(k)

    def _mostrar_palabra(self):
        return "  ".join(l if l in self.letras_ok else "_" for l in self.palabra)

    def _adivinar(self, letra):
        if letra in self.letras_ok or letra in self.letras_mal:
            return
        btn = self.btns_kbd.get(letra)
        if letra in self.palabra:
            self.letras_ok.add(letra)
            self.lbl_palabra.config(text=self._mostrar_palabra())
            if btn:
                btn.config(bg=GREEN, state="disabled")
            if all(l in self.letras_ok for l in self.palabra):
                self._dibujar_ganador()
                messagebox.showinfo(
                    self.txt["ah_gana_t"],
                    self.txt["ah_gana_m"].format(w=self.palabra))
                self._deshabilitar_teclado()
        else:
            self.letras_mal.add(letra)
            self.errores += 1
            if btn:
                btn.config(bg=RED, state="disabled")
            self._dibujar_parte(self.errores)
            self.lbl_falladas.config(
                text=self.txt["ah_incorrec2"].format(l="  ".join(sorted(self.letras_mal))))
            if self.errores >= self.MAX_ERRORES:
                self.lbl_palabra.config(text="  ".join(self.palabra), fg=RED)
                messagebox.showinfo(
                    self.txt["ah_pierde_t"],
                    self.txt["ah_pierde_m"].format(w=self.palabra))
                self._deshabilitar_teclado()

    def _deshabilitar_teclado(self):
        self.parent.winfo_toplevel().unbind("<Key>")
        for btn in self.btns_kbd.values():
            btn.config(state="disabled")

    def _dibujar_horca(self):
        c = self.canvas
        c.delete("all")
        c.create_line( 20, 200, 180, 200, width=5, fill=WHITE)
        c.create_line( 70, 200,  70,  20, width=5, fill=WHITE)
        c.create_line( 70,  20, 170,  20, width=5, fill=WHITE)
        c.create_line(170,  20, 170,  50, width=3, fill=WHITE)

    def _dibujar_parte(self, n):
        c = self.canvas
        if n == 1:   c.create_oval(150, 50, 190, 90, width=3, outline=WHITE)
        elif n == 2: c.create_line(170, 90, 170, 145, width=3, fill=WHITE)
        elif n == 3: c.create_line(170, 103, 140, 130, width=3, fill=WHITE)
        elif n == 4: c.create_line(170, 103, 200, 130, width=3, fill=WHITE)
        elif n == 5: c.create_line(170, 145, 140, 182, width=3, fill=WHITE)
        elif n == 6: c.create_line(170, 145, 200, 182, width=3, fill=WHITE)
        elif n == 7:
            c.create_arc(157, 67, 183, 87, start=0, extent=-180,
                         style="arc", width=2, outline=RED)
            c.create_oval(159, 58, 165, 64, fill=RED, outline=RED)
            c.create_oval(175, 58, 181, 64, fill=RED, outline=RED)

    def _dibujar_ganador(self):
        c = self.canvas
        self._dibujar_horca()
        c.create_oval(150, 50, 190, 90, width=3, outline=GREEN)
        c.create_line(170, 90, 170, 145, width=3, fill=GREEN)
        c.create_line(170, 103, 140, 130, width=3, fill=GREEN)
        c.create_line(170, 103, 200, 130, width=3, fill=GREEN)
        c.create_line(170, 145, 140, 182, width=3, fill=GREEN)
        c.create_line(170, 145, 200, 182, width=3, fill=GREEN)
        c.create_arc(157, 67, 183, 87, start=0, extent=180,
                     style="arc", width=2, outline=GREEN)
        c.create_oval(159, 58, 165, 64, fill=GREEN, outline=GREEN)
        c.create_oval(175, 58, 181, 64, fill=GREEN, outline=GREEN)


if __name__ == "__main__":
    app = JuegosApp()
    app.mainloop()
