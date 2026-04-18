
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import threading
import io
import os
import time
import urllib.request
import urllib.parse
from datetime import datetime

try:
    from PIL import Image, ImageTk
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

# ─────────────────────────────────────────────
#  PALETA CLARA AZUL/GRIS
# ─────────────────────────────────────────────
BG_MAIN      = "#F0F4F8"   # gris azulado muy claro
BG_SIDEBAR   = "#DDE6F0"   # azul grisáceo claro
BG_CARD      = "#FFFFFF"   # blanco limpio
BG_HEADER    = "#4A7DB5"   # azul medio para el header
ACCENT       = "#2563EB"   # azul vivo
ACCENT_HOVER = "#1D4ED8"
SUCCESS      = "#0891B2"   # cian oscuro
DANGER       = "#DC2626"
TEXT_DARK    = "#1E293B"   # casi negro
TEXT_MID     = "#475569"   # gris medio
TEXT_LIGHT   = "#94A3B8"   # gris claro
BORDER       = "#CBD5E1"   # borde gris azulado
BTN_BG       = "#FFFFFF"   # botón sin seleccionar (blanco, contrasta con sidebar)
BTN_ACTIVE   = "#C7DCF5"   # botón seleccionado
WARN_BG      = "#FEF3C7"
WARN_FG      = "#92400E"

SIDEBAR_W = 200

# ─────────────────────────────────────────────
#  DEFINICIÓN DE APIs
# ─────────────────────────────────────────────
APIS = {
    "Pollinations · flux": {
        "desc": "FLUX · uso general · buena calidad",
        "tag": "general",
        "icon": "🌸",
        "color": "#EC4899",
        "type": "pollinations",
        "poll_model": "flux",
        "group": "Pollinations",
        "sizes": ["256x256", "320x320", "512x512", "768x512", "1024x512", "1024x768", "1024x1024", "512x1024"],
        "default_size": "1024x1024",
        "needs_token": False,
        "supports_neg": False,
        "max_steps": 0,
    },
    "Pollinations · turbo": {
        "desc": "SDXL Turbo · generación rápida",
        "tag": "rápido",
        "icon": "⚡",
        "color": "#7C3AED",
        "type": "pollinations",
        "poll_model": "turbo",
        "group": "Pollinations",
        "sizes": ["256x256", "320x320", "512x512", "768x512", "1024x512", "1024x1024", "512x1024"],
        "default_size": "512x512",
        "needs_token": False,
        "supports_neg": False,
        "max_steps": 0,
    },
    "Pollinations · realistic": {
        "desc": "Realistic Vision · fotografía realista",
        "tag": "foto",
        "icon": "📸",
        "color": "#059669",
        "type": "pollinations",
        "poll_model": "realistic",
        "group": "Pollinations",
        "sizes": ["256x256", "320x320", "512x512", "768x512", "1024x512", "768x768", "1024x768"],
        "default_size": "768x512",
        "needs_token": False,
        "supports_neg": False,
        "max_steps": 0,
    },
    "Pollinations · gptimage": {
        "desc": "GPT-Image-1 · prompts complejos · alta calidad",
        "tag": "calidad",
        "icon": "🤖",
        "color": "#0EA5E9",
        "type": "pollinations",
        "poll_model": "gptimage",
        "group": "Pollinations",
        "sizes": ["256x256", "320x320", "512x512", "768x768", "1024x1024"],
        "default_size": "1024x1024",
        "needs_token": False,
        "supports_neg": False,
        "max_steps": 0,
    },
    "Pollinations · kontext": {
        "desc": "FLUX Kontext · editar imágenes existentes",
        "tag": "img2img",
        "icon": "🎞",
        "color": "#7C3AED",
        "type": "pollinations",
        "poll_model": "flux-pro",
        "group": "Pollinations",
        "sizes": ["256x256", "320x320", "512x512", "768x768", "1024x1024", "1024x768", "768x1024"],
        "default_size": "1024x1024",
        "needs_token": False,
        "supports_neg": False,
        "max_steps": 0,
    },
    "Pollinations · anime": {
        "desc": "Illustrious XL · estilo anime/manga",
        "tag": "anime",
        "icon": "🌸",
        "color": "#EC4899",
        "type": "pollinations",
        "poll_model": "anime",
        "group": "Pollinations",
        "sizes": ["256x256", "320x320", "512x512", "768x512", "1024x512", "768x768", "512x768"],
        "default_size": "768x768",
        "needs_token": False,
        "supports_neg": False,
        "max_steps": 0,
    },
    "Pollinations · seedream": {
        "desc": "Seedream · piel y texturas muy realistas",
        "tag": "hiperrealista",
        "icon": "🌿",
        "color": "#16A34A",
        "type": "pollinations",
        "poll_model": "seedream",
        "group": "Pollinations",
        "sizes": ["256x256", "320x320", "512x512", "768x768", "1024x1024", "1280x1280"],
        "default_size": "1024x1024",
        "needs_token": False,
        "supports_neg": False,
        "max_steps": 0,
    },
    "Pollinations · zimage": {
        "desc": "Zimage · modelo por defecto de Pollinations",
        "tag": "por defecto",
        "icon": "✦",
        "color": "#0891B2",
        "type": "pollinations",
        "poll_model": "zimage",
        "group": "Pollinations",
        "sizes": ["256x256", "320x320", "512x512", "768x768", "1024x1024"],
        "default_size": "1024x1024",
        "needs_token": False,
        "supports_neg": False,
        "max_steps": 0,
    },
    "Picsum (Demo)": {
        "desc": "Placeholder · sin IA · siempre disponible",
        "tag": "demo",
        "icon": "🎲",
        "color": "#64748B",
        "type": "picsum",
        "group": "Otros",
        "sizes": ["256x256", "320x320", "512x512", "768x512", "1024x768"],
        "default_size": "512x512",
        "needs_token": False,
        "supports_neg": False,
        "max_steps": 0,
    },
}

# ─────────────────────────────────────────────
#  FUNCIONES DE GENERACIÓN
# ─────────────────────────────────────────────

# Nota: HF Inference API dejó de soportar modelos de imagen en julio 2025.
# Los modelos de difusión ahora requieren proveedores de pago (fal-ai, replicate…).
# Se han sustituido por modelos de Pollinations igualmente gratuitos.


# Modelos de Pollinations en orden de rotación para evitar 429
_POLL_ROTATION = ["flux", "turbo", "realistic", "flux-pro", "anime", "gptimage", "seedream", "zimage"]
_poll_index = 0  # índice global de rotación

def _poll_single(prompt, w, h, seed, model):
    """Intenta una petición a Pollinations. Lanza HTTPError si falla."""
    enc = urllib.parse.quote(prompt)
    s   = str(seed) if seed >= 0 else str(int(time.time()))
    url = (f"https://image.pollinations.ai/prompt/{enc}"
           f"?width={w}&height={h}&seed={s}&model={model}&nologo=true&enhance=false")
    req = urllib.request.Request(url, headers={"User-Agent": "ImageGenPro/2.0"})
    with urllib.request.urlopen(req, timeout=120) as resp:
        return resp.read()


def _upload_image_temp(img_bytes):
    """Sube imagen a litterbox.catbox.moe y devuelve URL pública. Temporal 1h."""
    boundary = "----FormBoundary7MA4YWxkTrZu0gW"
    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="reqtype"\r\n\r\nfileupload\r\n'
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="time"\r\n\r\n1h\r\n'
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="fileToUpload"; filename="image.png"\r\n'
        f"Content-Type: image/png\r\n\r\n"
    ).encode() + img_bytes + f"\r\n--{boundary}--\r\n".encode()
    req = urllib.request.Request(
        "https://litterbox.catbox.moe/resources/internals/api.php",
        data=body,
        headers={
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "User-Agent": "ImageGenPro/2.0",
        }
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        url = resp.read().decode().strip()
    if not url.startswith("http"):
        raise RuntimeError(f"Error subiendo imagen: {url}")
    return url


def _poll_single_i2i(prompt, w, h, seed, image_url):
    """Petición kontext img2img con URL de imagen base."""
    enc = urllib.parse.quote(prompt)
    s   = str(seed) if seed >= 0 else str(int(time.time()))
    img_enc = urllib.parse.quote(image_url, safe="")
    url = (f"https://image.pollinations.ai/prompt/{enc}"
           f"?width={w}&height={h}&seed={s}&model=flux-pro"
           f"&image={img_enc}&nologo=true&enhance=false")
    req = urllib.request.Request(url, headers={"User-Agent": "ImageGenPro/2.0"})
    with urllib.request.urlopen(req, timeout=180) as resp:
        return resp.read()


def call_pollinations(prompt, w, h, seed, model="flux", img2img_bytes=None):
    """Llama a Pollinations. Si recibe 429 rota por los demás modelos automáticamente."""
    global _poll_index

    # Modo img2img kontext
    if model == "flux-pro" and img2img_bytes:
        image_url = _upload_image_temp(img2img_bytes)
        return _poll_single_i2i(prompt, w, h, seed, image_url)

    # Lista de modelos a intentar: el solicitado primero, luego el resto en rotación
    others = [m for m in _POLL_ROTATION if m != model]
    # Reordenar empezando por _poll_index para distribuir carga
    others = others[_poll_index % len(others):] + others[:_poll_index % len(others)]
    candidates = [model] + others

    last_err = None
    for i, m in enumerate(candidates):
        wait = 3 if i > 0 else 0   # pequeña pausa antes de cambiar de modelo
        if wait:
            time.sleep(wait)
        try:
            data = _poll_single(prompt, w, h, seed, m)
            _poll_index = (_poll_index + 1) % len(_POLL_ROTATION)
            return data
        except urllib.error.HTTPError as e:
            if e.code == 429:
                last_err = e
                continue   # prueba el siguiente modelo
            raise

    raise RuntimeError(
        "Todos los modelos de Pollinations devuelven 429 (demasiadas peticiones).\n"
        "Espera 1-2 minutos y vuelve a intentarlo."
    ) from last_err






def call_picsum(prompt, w, h):
    seed = abs(hash(prompt)) % 1000
    url  = f"https://picsum.photos/seed/{seed}/{w}/{h}"
    req  = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read()


def generate(api_name, prompt, size, tokens, negative, steps, seed, img2img_bytes=None):
    w, h = map(int, size.split("x"))
    info = APIS[api_name]
    t    = info["type"]

    if t == "pollinations":
        return call_pollinations(prompt, w, h, seed, info.get("poll_model", "flux"), img2img_bytes)
    elif t == "picsum":
        return call_picsum(prompt, w, h)
    raise RuntimeError(f"Tipo desconocido: {t}")


# ─────────────────────────────────────────────
#  APLICACIÓN
# ─────────────────────────────────────────────
class App(tk.Tk):

    def __init__(self):
        super().__init__()
        self.title("🎨 Image Generator")
        self.configure(bg=BG_MAIN)
        self.resizable(True, True)

        self.sel_api       = tk.StringVar(value=list(APIS)[0])
        self.sel_size      = tk.StringVar(value="512x512")
        self.steps_var     = tk.IntVar(value=20)
        self.seed_var      = tk.IntVar(value=-1)
        self.open_folder_var = tk.BooleanVar(value=False)
        self.generating    = False
        self.cur_img       = None
        self.cur_bytes     = None
        self.cur_prompt    = ""
        self.img2img_bytes = None   # imagen base para edición kontext
        self._history      = []
        self._api_btns     = {}

        self.update_idletasks()
        W, H = 1100, 760
        sw   = self.winfo_screenwidth()
        self.geometry(f"{W}x{H}+{(sw-W)//2}+5")
        self.minsize(880, 640)

        self._build()
        self._select(list(APIS)[0])

    # ── BUILD ─────────────────────────────────
    def _build(self):
        # Header
        hdr = tk.Frame(self, bg=BG_HEADER, height=50)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        tk.Label(hdr, text="🎨  Image Generator",
                 font=("Segoe UI", 14, "bold"),
                 bg=BG_HEADER, fg="white").pack(side="left", padx=16)
        tk.Label(hdr, text="Pollinations AI · Totalmente gratuito · Sin clave",
                 font=("Segoe UI", 9), bg=BG_HEADER, fg="#DBEAFE").pack(side="left", padx=4)
        pil_txt = "✅ Pillow OK" if PIL_AVAILABLE else "⚠️ pip install pillow"
        pil_col = "#A7F3D0" if PIL_AVAILABLE else "#FEE2E2"
        tk.Label(hdr, text=pil_txt, font=("Segoe UI", 9),
                 bg=BG_HEADER, fg=pil_col).pack(side="right", padx=14)

        body = tk.Frame(self, bg=BG_MAIN)
        body.pack(fill="both", expand=True)
        self._sidebar(body)
        self._main_panel(body)

    def _sidebar(self, parent):
        sb = tk.Frame(parent, bg=BG_SIDEBAR, width=SIDEBAR_W,
                      highlightbackground=BORDER, highlightthickness=1)
        sb.pack(side="left", fill="y")
        sb.pack_propagate(False)

        tk.Label(sb, text="  Selecciona modelo", font=("Segoe UI", 10, "bold"),
                 bg=BG_SIDEBAR, fg=TEXT_DARK, anchor="w").pack(
                 fill="x", padx=8, pady=(10, 4))

        # ── Zona superior: modelos (altura fija, scroll interno) ──
        models_frame = tk.Frame(sb, bg=BG_SIDEBAR)
        models_frame.pack(fill="x")          # NO expand — altura natural

        canvas_sb = tk.Canvas(models_frame, bg=BG_SIDEBAR, bd=0,
                              highlightthickness=0, height=380)
        scrollbar = ttk.Scrollbar(models_frame, orient="vertical",
                                  command=canvas_sb.yview)
        self._sb_inner = tk.Frame(canvas_sb, bg=BG_SIDEBAR)

        self._sb_inner.bind("<Configure>",
            lambda e: canvas_sb.configure(scrollregion=canvas_sb.bbox("all")))
        canvas_sb.create_window((0, 0), window=self._sb_inner, anchor="nw")
        canvas_sb.configure(yscrollcommand=scrollbar.set)

        def _on_wheel(e):
            canvas_sb.yview_scroll(int(-1*(e.delta/120)), "units")
        canvas_sb.bind_all("<MouseWheel>", _on_wheel)

        scrollbar.pack(side="right", fill="y")
        canvas_sb.pack(side="left", fill="x", expand=True)

        # Agrupar y construir modelos
        groups = {}
        for name, info in APIS.items():
            g = info.get("group", "Otros")
            groups.setdefault(g, []).append((name, info))

        self._group_expanded = {}
        for gname, members in groups.items():
            self._build_group(self._sb_inner, gname, members)

        # ── Zona inferior: seed + historial ──
        ttk.Separator(sb).pack(fill="x", padx=8, pady=5)

        self._lbl(sb, "🎲 Seed  (-1 = aleatorio)")
        tk.Entry(sb, textvariable=self.seed_var, font=("Segoe UI", 9),
                 bd=1, relief="solid", bg="#FFFFFF", fg=TEXT_DARK).pack(
                 fill="x", padx=8, pady=(2, 4))

        ttk.Separator(sb).pack(fill="x", padx=8, pady=5)

        self._lbl(sb, "📋 Historial")
        hf = tk.Frame(sb, bg=BG_SIDEBAR)
        hf.pack(fill="both", expand=True, padx=6, pady=4)
        self._hist = tk.Listbox(hf, font=("Segoe UI", 8), bd=0,
                                 bg="#FFFFFF", fg=TEXT_DARK,
                                 selectbackground=BTN_ACTIVE,
                                 relief="flat", activestyle="none")
        self._hist.pack(fill="both", expand=True)
        self._hist.bind("<<ListboxSelect>>", self._hist_select)

    def _build_group(self, parent, gname, members):
        """Construye un grupo colapsable con sus botones de modelo."""
        expanded = tk.BooleanVar(value=True)
        self._group_expanded[gname] = expanded

        # Cabecera del grupo
        hdr = tk.Frame(parent, bg=BG_SIDEBAR)
        hdr.pack(fill="x", padx=4, pady=(4, 0))

        arrow_lbl = tk.Label(hdr, text="▼", font=("Segoe UI", 8),
                             bg=BG_SIDEBAR, fg=TEXT_MID, width=2)
        arrow_lbl.pack(side="left")
        tk.Label(hdr, text=gname.upper(), font=("Segoe UI", 8, "bold"),
                 bg=BG_SIDEBAR, fg=TEXT_MID, anchor="w").pack(side="left")

        # Contenedor de botones
        body = tk.Frame(parent, bg=BG_SIDEBAR)
        body.pack(fill="x")

        for name, info in members:
            self._api_btn(body, name, info)

        def toggle(_event=None):
            if expanded.get():
                body.pack_forget()
                arrow_lbl.config(text="▶")
                expanded.set(False)
            else:
                body.pack(fill="x")
                arrow_lbl.config(text="▼")
                expanded.set(True)

        hdr.bind("<Button-1>", toggle)
        for w in hdr.winfo_children():
            w.bind("<Button-1>", toggle)
        hdr.config(cursor="hand2")

    def _lbl(self, parent, text):
        tk.Label(parent, text=f"  {text}", font=("Segoe UI", 8),
                 bg=BG_SIDEBAR, fg=TEXT_MID, anchor="w").pack(fill="x", padx=10)

    def _api_btn(self, parent, name, info):
        color = info["color"]
        tag   = info.get("tag", "")
        wrap  = tk.Frame(parent, bg=BG_SIDEBAR)
        wrap.pack(fill="x", padx=6, pady=1)

        inner = tk.Frame(wrap, bg=BTN_BG, highlightbackground=BORDER,
                         highlightthickness=1)
        inner.pack(fill="x")
        inner.columnconfigure(2, weight=1)

        bar = tk.Frame(inner, bg=color, width=4)
        bar.grid(row=0, column=0, rowspan=2, sticky="ns")

        icon = tk.Label(inner, text=info["icon"], font=("Segoe UI", 11),
                        bg=BTN_BG, fg=color, width=2, anchor="center")
        icon.grid(row=0, column=1, rowspan=2, padx=(4, 2), pady=4, sticky="ns")

        # Nombre corto (sin prefijo "Pollinations · ")
        short_name = name.replace("Pollinations · ", "")
        nl = tk.Label(inner, text=short_name, font=("Segoe UI", 9, "bold"),
                      bg=BTN_BG, fg=TEXT_DARK, anchor="w", justify="left")
        nl.grid(row=0, column=2, sticky="ew", padx=(2, 4), pady=(4, 0))

        tl = tk.Label(inner, text=tag, font=("Segoe UI", 7),
                      bg=BTN_BG, fg=color, anchor="w", justify="left")
        tl.grid(row=1, column=2, sticky="ew", padx=(2, 4), pady=(0, 4))

        all_w = [wrap, inner, bar, icon, nl, tl]
        for w in all_w:
            w.bind("<Button-1>", lambda e, n=name: self._select(n))
            w.bind("<Enter>",    lambda e, f=inner, b=bar, c=color:
                   (f.config(bg=BTN_ACTIVE, highlightbackground=c),
                    b.config(bg=c)))
            w.bind("<Leave>",    lambda e, n=name, f=inner, b=bar, c=color:
                   (f.config(bg=(BTN_ACTIVE if n == self.sel_api.get() else BTN_BG),
                             highlightbackground=(c if n == self.sel_api.get() else BORDER)),
                    b.config(bg=c)))

        self._api_btns[name] = {
            "inner": inner, "nl": nl, "dl": tl, "icon": icon,
            "bar": bar, "all": all_w, "color": color
        }

    def _select(self, name):
        self.sel_api.set(name)
        info = APIS[name]
        for n, d in self._api_btns.items():
            sel = n == name
            bg  = BTN_ACTIVE if sel else BTN_BG
            bd  = d["color"] if sel else BORDER
            d["inner"].config(bg=bg, highlightbackground=bd)
            d["bar"].config(bg=d["color"])   # la barra siempre mantiene su color
            for w in d["all"]:
                try:
                    if w is not d["bar"]:
                        w.config(bg=bg)
                except Exception: pass

        self._size_cb["values"] = info["sizes"]
        self.sel_size.set(info["default_size"])
        self._api_lbl.config(text=f"{info['icon']}  {name}", fg=info["color"])
        self._api_desc_lbl.config(text=info["desc"])

        # Mostrar panel img2img solo para kontext
        if info.get("poll_model") == "flux-pro":
            self._img2img_frame.pack(fill="x", padx=12, pady=(0, 6))
        else:
            self._img2img_frame.pack_forget()
            self._i2i_clear()

    def _main_panel(self, parent):
        main = tk.Frame(parent, bg=BG_MAIN)
        main.pack(side="left", fill="both", expand=True)

        # ── Card prompt ──
        card = tk.Frame(main, bg=BG_CARD, highlightbackground=BORDER,
                        highlightthickness=1)
        card.pack(fill="x", padx=14, pady=(14, 6))

        # API activa
        row = tk.Frame(card, bg=BG_CARD)
        row.pack(fill="x", padx=12, pady=(10, 4))
        tk.Label(row, text="API activa:", font=("Segoe UI", 9),
                 bg=BG_CARD, fg=TEXT_LIGHT).pack(side="left")
        self._api_lbl = tk.Label(row, text="", font=("Segoe UI", 10, "bold"),
                                  bg=BG_CARD, fg=ACCENT)
        self._api_lbl.pack(side="left", padx=6)
        self._api_desc_lbl = tk.Label(row, text="", font=("Segoe UI", 9),
                                       bg=BG_CARD, fg=TEXT_LIGHT)
        self._api_desc_lbl.pack(side="left")


        # Prompt
        tk.Label(card, text="✏️  Prompt  (en inglés da mejores resultados)",
                 font=("Segoe UI", 10, "bold"),
                 bg=BG_CARD, fg=TEXT_DARK, anchor="w").pack(
                 fill="x", padx=12, pady=(4, 2))
        self._prompt = tk.Text(card, height=3, font=("Segoe UI", 10),
                                bd=1, relief="solid", bg="#F8FAFC", fg=TEXT_DARK,
                                wrap="word", padx=8, pady=6,
                                insertbackground=ACCENT)
        self._prompt.pack(fill="x", padx=12, pady=(0, 4))
        self._prompt.insert("1.0",
            "a beautiful mountain landscape at golden hour, "
            "photorealistic, 8k, dramatic lighting, cinematic")

        # ── Panel img2img (solo visible con kontext) ──
        self._img2img_frame = tk.Frame(card, bg="#EEF4FF",
                                        highlightbackground="#BFCFEE",
                                        highlightthickness=1)
        # (se muestra/oculta en _select)

        i2i_title = tk.Frame(self._img2img_frame, bg="#EEF4FF")
        i2i_title.pack(fill="x", padx=8, pady=(6, 2))
        tk.Label(i2i_title, text="🖌  Edición img2img  (kontext)",
                 font=("Segoe UI", 9, "bold"), bg="#EEF4FF", fg=ACCENT).pack(side="left")
        tk.Label(i2i_title,
                 text="Carga una imagen base y escribe cómo quieres modificarla",
                 font=("Segoe UI", 8), bg="#EEF4FF", fg=TEXT_MID).pack(side="left", padx=8)

        i2i_body = tk.Frame(self._img2img_frame, bg="#EEF4FF")
        i2i_body.pack(fill="x", padx=8, pady=(0, 8))

        # Miniatura
        self._i2i_thumb = tk.Label(i2i_body, text="Sin imagen",
                                    font=("Segoe UI", 8), bg="#D8E4F8", fg=TEXT_MID,
                                    width=12, height=4, relief="solid", bd=1)
        self._i2i_thumb.pack(side="left", padx=(0, 8))

        i2i_btns = tk.Frame(i2i_body, bg="#EEF4FF")
        i2i_btns.pack(side="left", fill="y")

        tk.Button(i2i_btns, text="📂 Cargar imagen…",
                  font=("Segoe UI", 9), bg=BTN_BG, fg=TEXT_DARK, bd=0,
                  activebackground=BTN_ACTIVE, padx=8, pady=4, cursor="hand2",
                  command=self._i2i_load).pack(fill="x", pady=(0, 4))

        self._i2i_use_btn = tk.Button(i2i_btns, text="♻ Usar imagen generada",
                  font=("Segoe UI", 9), bg=BTN_BG, fg=TEXT_DARK, bd=0,
                  activebackground=BTN_ACTIVE, padx=8, pady=4, cursor="hand2",
                  state="disabled", command=self._i2i_use_current)
        self._i2i_use_btn.pack(fill="x", pady=(0, 4))

        tk.Button(i2i_btns, text="✖ Quitar imagen base",
                  font=("Segoe UI", 9), bg=BTN_BG, fg=DANGER, bd=0,
                  activebackground=BTN_ACTIVE, padx=8, pady=4, cursor="hand2",
                  command=self._i2i_clear).pack(fill="x")

        self._i2i_status = tk.Label(self._img2img_frame,
                                     text="  Sin imagen base — se generará desde cero",
                                     font=("Segoe UI", 8, "italic"),
                                     bg="#EEF4FF", fg=TEXT_MID, anchor="w")
        self._i2i_status.pack(fill="x", padx=8, pady=(0, 4))

        # Controles
        ctrl = tk.Frame(card, bg=BG_CARD)
        ctrl.pack(fill="x", padx=12, pady=(2, 10))

        tk.Label(ctrl, text="Tamaño:", font=("Segoe UI", 9),
                 bg=BG_CARD, fg=TEXT_MID).pack(side="left")
        self._size_cb = ttk.Combobox(ctrl, textvariable=self.sel_size,
                                      width=11, state="normal",
                                      font=("Segoe UI", 9))
        self._size_cb.pack(side="left", padx=(4, 4))
        tk.Label(ctrl, text="(o escribe p.ej. 100x400)", font=("Segoe UI", 8),
                 bg=BG_CARD, fg=TEXT_LIGHT).pack(side="left", padx=(0, 12))

        self._gen_btn = tk.Button(ctrl, text="  ✨  Generar  ",
                                   font=("Segoe UI", 11, "bold"),
                                   bg=ACCENT, fg="white", bd=0,
                                   activebackground=ACCENT_HOVER,
                                   activeforeground="white",
                                   padx=16, pady=7, cursor="hand2",
                                   command=self._generate)
        self._gen_btn.pack(side="left")

        self._save_btn = tk.Button(ctrl, text=" 💾 Guardar ",
                                    font=("Segoe UI", 10),
                                    bg=SUCCESS, fg="white", bd=0,
                                    activebackground="#15803D",
                                    activeforeground="white",
                                    padx=10, pady=7, state="disabled",
                                    cursor="hand2", command=self._save)
        self._save_btn.pack(side="left", padx=8)

        tk.Checkbutton(ctrl, text="Abrir carpeta al guardar",
                       variable=self.open_folder_var,
                       font=("Segoe UI", 9), bg=BG_CARD, fg=TEXT_MID,
                       activebackground=BG_CARD, selectcolor=BG_CARD,
                       cursor="hand2").pack(side="left", padx=(0, 12))

        tk.Button(ctrl, text=" 📋 Copiar prompt ",
                  font=("Segoe UI", 9), bg=BTN_BG, fg=ACCENT, bd=0,
                  activebackground=BTN_ACTIVE, padx=8, pady=7,
                  cursor="hand2", command=self._copy).pack(side="left")

        # Estado y progreso
        sf = tk.Frame(card, bg=BG_CARD)
        sf.pack(fill="x", padx=12, pady=(0, 8))
        self._prog = ttk.Progressbar(sf, mode="indeterminate", length=200)
        self._prog.pack(side="left")
        self._status = tk.StringVar(value="Listo. Selecciona API y escribe un prompt.")
        tk.Label(sf, textvariable=self._status, font=("Segoe UI", 9),
                 bg=BG_CARD, fg=TEXT_MID).pack(side="left", padx=10)

        # ── Canvas imagen ──
        cc = tk.Frame(main, bg=BG_CARD, highlightbackground=BORDER,
                      highlightthickness=1)
        cc.pack(fill="both", expand=True, padx=14, pady=(0, 14))
        self._canvas = tk.Canvas(cc, bg="#E2EAF4", bd=0, highlightthickness=0)
        self._canvas.pack(fill="both", expand=True, padx=4, pady=4)
        self._canvas.bind("<Configure>", self._canvas_resize)
        self._ph = self._canvas.create_text(0, 0, justify="center",
            anchor="center",
            text="Tu imagen aparecerá aquí\n\n"
                 "Prueba primero 🌸 Pollinations · flux\n"
                 "(funciona sin ninguna clave)",
            font=("Segoe UI", 13), fill=TEXT_MID)
        self._reposition_ph()

    # ── GENERACIÓN ───────────────────────────
    def _generate(self):
        if self.generating:
            return
        prompt = self._prompt.get("1.0", "end").strip()
        if not prompt:
            messagebox.showwarning("Prompt vacío", "Escribe un prompt antes de generar.")
            return

        # Validar tamaño (acepta cualquier NxM con valores entre 64 y 2048)
        import re
        size = self.sel_size.get().strip()
        m = re.fullmatch(r"(\d+)\s*[xX×]\s*(\d+)", size)
        if not m:
            messagebox.showwarning("Tamaño inválido",
                "Formato incorrecto. Usa el formato ancho×alto, p.ej.: 512x512 o 100x400")
            return
        w, h = int(m.group(1)), int(m.group(2))
        if not (64 <= w <= 2048 and 64 <= h <= 2048):
            messagebox.showwarning("Tamaño fuera de rango",
                "Ancho y alto deben estar entre 64 y 2048 píxeles.")
            return
        # Normalizar formato en el campo
        size = f"{w}x{h}"
        self.sel_size.set(size)

        self.generating = True
        self._gen_btn.config(state="disabled", text="  ⏳ Generando…  ")
        self._save_btn.config(state="disabled")
        self._prog.start(10)
        self._set_status("Enviando solicitud…")

        tokens = {
        }
        threading.Thread(
            target=self._thread,
            args=(self.sel_api.get(), prompt, self.sel_size.get(),
                  tokens, "",
                  self.steps_var.get(), self.seed_var.get(),
                  self.img2img_bytes),
            daemon=True
        ).start()

    def _thread(self, api, prompt, size, tokens, neg, steps, seed, img2img_bytes):
        try:
            if img2img_bytes:
                self._set_status("Subiendo imagen base a servidor temporal…")
            else:
                self._set_status(f"Llamando a {api}…")
            data = generate(api, prompt, size, tokens, neg, steps, seed, img2img_bytes)
            if img2img_bytes:
                self._set_status("Imagen subida · esperando resultado de kontext…")
            self.cur_bytes = data
            if PIL_AVAILABLE:
                self.cur_img = Image.open(io.BytesIO(data))
            self.after(0, self._success, prompt, api)
        except Exception as e:
            self.after(0, self._error, str(e))

    def _success(self, prompt, api):
        self.generating = False
        self.cur_prompt = prompt
        self._gen_btn.config(state="normal", text="  ✨  Generar  ")
        self._save_btn.config(state="normal")
        self._i2i_use_btn.config(state="normal")  # ya hay imagen generada
        self._prog.stop()
        info = APIS[api]
        self._set_status(f"✅ Imagen generada · {api}")
        if PIL_AVAILABLE and self.cur_img:
            self._show_img(self.cur_img)
            self._history.insert(0, (prompt[:60], api, self.cur_img.copy()))
            self._hist.insert(0, f"{info['icon']} {prompt[:30]}…")
            if len(self._history) > 20:
                self._history.pop()
                self._hist.delete(20)
        else:
            self._set_status("✅ Recibida · instala Pillow para previsualizar")

    def _error(self, err):
        self.generating = False
        self._gen_btn.config(state="normal", text="  ✨  Generar  ")
        self._prog.stop()
        self._set_status(f"❌ Error: {err[:80]}")
        messagebox.showerror("Error al generar", err)

    def _show_img(self, img):
        cw = max(self._canvas.winfo_width(),  10)
        ch = max(self._canvas.winfo_height(), 10)
        copy = img.copy()
        copy.thumbnail((cw - 8, ch - 8), Image.LANCZOS)
        self._tk_img = ImageTk.PhotoImage(copy)
        self._canvas.delete("all")
        self._canvas.create_image(cw // 2, ch // 2, image=self._tk_img, anchor="center")

    def _canvas_resize(self, _):
        if self.cur_img and PIL_AVAILABLE:
            self._show_img(self.cur_img)
        else:
            self._reposition_ph()

    def _reposition_ph(self):
        cw = max(self._canvas.winfo_width(),  400)
        ch = max(self._canvas.winfo_height(), 300)
        self._canvas.coords(self._ph, cw // 2, ch // 2)

    def _save(self):
        if not self.cur_bytes:
            return
        # Nombre sugerido: dos primeras palabras del prompt + timestamp
        import re
        words = re.findall(r"[A-Za-z0-9áéíóúüñÁÉÍÓÚÜÑ]+", self.cur_prompt)
        base  = "_".join(words[:2]).lower() if words else "imagen"
        now   = datetime.now().strftime("%Y%m%d_%H%M%S")
        suggested = f"{base}_{now}.png"

        path = filedialog.asksaveasfilename(
            defaultextension=".png",
            initialfile=suggested,
            filetypes=[("PNG", "*.png"), ("JPEG", "*.jpg"), ("Todos", "*.*")])
        if path:
            with open(path, "wb") as f:
                f.write(self.cur_bytes)
            self._set_status(f"💾 Guardado: {os.path.basename(path)}")
            if self.open_folder_var.get():
                folder = os.path.dirname(os.path.abspath(path))
                import subprocess, sys
                if sys.platform == "win32":
                    subprocess.Popen(["explorer", folder])
                elif sys.platform == "darwin":
                    subprocess.Popen(["open", folder])
                else:
                    subprocess.Popen(["xdg-open", folder])

    def _copy(self):
        self.clipboard_clear()
        self.clipboard_append(self._prompt.get("1.0", "end").strip())
        self._set_status("📋 Prompt copiado al portapapeles.")

    def _hist_select(self, _):
        sel = self._hist.curselection()
        if not sel or not PIL_AVAILABLE:
            return
        idx = sel[0]
        if idx < len(self._history):
            prompt, api, img = self._history[idx]
            self.cur_img = img
            self._show_img(img)
            self._prompt.delete("1.0", "end")
            self._prompt.insert("1.0", prompt)
            self._set_status(f"Historial · {api}")

    # ── IMG2IMG ───────────────────────────────
    def _i2i_set(self, img_bytes):
        """Establece la imagen base para img2img y actualiza la miniatura."""
        self.img2img_bytes = img_bytes
        if PIL_AVAILABLE and img_bytes:
            img = Image.open(io.BytesIO(img_bytes))
            img.thumbnail((80, 60), Image.LANCZOS)
            self._i2i_tk = ImageTk.PhotoImage(img)
            self._i2i_thumb.config(image=self._i2i_tk, text="", width=80, height=60)
            self._i2i_status.config(
                text=f"  ✅ Imagen base cargada — escribe cómo modificarla en el prompt")
        else:
            self._i2i_thumb.config(image="", text="Sin imagen", width=12, height=4)
            self._i2i_status.config(text="  Sin imagen base — se generará desde cero")

    def _i2i_load(self):
        path = filedialog.askopenfilename(
            title="Selecciona imagen base",
            filetypes=[("Imágenes", "*.png *.jpg *.jpeg *.webp"), ("Todos", "*.*")])
        if path:
            with open(path, "rb") as f:
                self._i2i_set(f.read())

    def _i2i_use_current(self):
        if self.cur_bytes:
            self._i2i_set(self.cur_bytes)

    def _i2i_clear(self):
        self.img2img_bytes = None
        if hasattr(self, "_i2i_thumb"):
            self._i2i_thumb.config(image="", text="Sin imagen", width=12, height=4)
        if hasattr(self, "_i2i_status"):
            self._i2i_status.config(text="  Sin imagen base — se generará desde cero")

    def _set_status(self, msg):
        self._status.set(msg)


if __name__ == "__main__":
    App().mainloop()
