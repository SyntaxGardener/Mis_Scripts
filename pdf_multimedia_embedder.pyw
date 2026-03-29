"""
PDF Multimedia Embedder  v2.0
==============================
Incrusta audio y/o video en un PDF con vista previa interactiva.

Dependencias:
    pip install pypdf reportlab pillow pdf2image
    (también necesitas poppler instalado en el sistema)
      Windows: https://github.com/oschwartz10612/poppler-windows
      macOS:   brew install poppler
      Linux:   apt install poppler-utils

Uso:
    pythonw pdf_multimedia_embedder.pyw   (Windows, sin consola)
    python3  pdf_multimedia_embedder.pyw
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
import threading
from pathlib import Path
import sys
BASE = Path(__file__).parent
POPPLER_PATH = str(BASE / "poppler" / "Library" / "bin")

# ─────────────────────────────────────────────────────────────────────────────
#  Utilidades MIME / tipo
# ─────────────────────────────────────────────────────────────────────────────

def _mime(path):
    ext = Path(path).suffix.lower()
    return {
        ".mp3": "audio/mpeg",  ".wav": "audio/wav",   ".ogg": "audio/ogg",
        ".aac": "audio/aac",   ".flac": "audio/flac",  ".m4a": "audio/mp4",
        ".mp4": "video/mp4",   ".avi": "video/x-msvideo",
        ".mov": "video/quicktime", ".mkv": "video/x-matroska",
        ".webm": "video/webm", ".wmv": "video/x-ms-wmv",
    }.get(ext, "application/octet-stream")


def _is_audio(path):
    return _mime(path).startswith("audio/")


# ─────────────────────────────────────────────────────────────────────────────
#  Modo A — Launch + miniatura (Adobe Acrobat/Reader)
# ─────────────────────────────────────────────────────────────────────────────

def embed_real(pdf_in, media_file, pdf_out, page_num=0, rect=(50, 650, 300, 750),
               thumbnail_path=None):
    """
    Igual que el Modo B pero con acción /Launch en lugar de URI.
    Dibuja la miniatura/placeholder visual Y añade la acción Launch para Acrobat.
    """
    import shutil, tempfile
    from pypdf import PdfReader, PdfWriter
    from pypdf.generic import (
        ArrayObject, DictionaryObject, NameObject, NumberObject,
        BooleanObject, create_string_object,
    )
    from reportlab.pdfgen import canvas as rl_canvas

    # Copiar multimedia junto al PDF de salida
    pdf_out_dir = Path(pdf_out).parent
    media_dest  = pdf_out_dir / Path(media_file).name
    if Path(media_file).resolve() != media_dest.resolve():
        shutil.copy2(media_file, media_dest)
    filename = media_dest.name

    reader = PdfReader(pdf_in)
    writer = PdfWriter()
    for p in reader.pages:
        writer.add_page(p)

    # --- Overlay visual (igual que Modo B) ---
    orig_page = reader.pages[page_num]
    pw = float(orig_page.mediabox.width)
    ph = float(orig_page.mediabox.height)

    tmp = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
    tmp.close()

    c = rl_canvas.Canvas(tmp.name, pagesize=(pw, ph))
    x1, y1, x2, y2 = rect
    label = ("▶  " if not _is_audio(media_file) else "♪  ") + Path(media_file).name

    if thumbnail_path and os.path.isfile(thumbnail_path):
        try:
            c.drawImage(thumbnail_path, x1, y1, width=x2-x1, height=y2-y1,
                        preserveAspectRatio=True, mask="auto")
        except Exception:
            _draw_placeholder(c, x1, y1, x2, y2, label, _is_audio(media_file))
    else:
        _draw_placeholder(c, x1, y1, x2, y2, label, _is_audio(media_file))
    c.save()

    from pypdf import PdfReader as PR2
    ov = PR2(tmp.name)
    writer.pages[page_num].merge_page(ov.pages[0])
    os.unlink(tmp.name)

    # --- Acción Launch ---
    fs = DictionaryObject({
        NameObject("/Type"): NameObject("/Filespec"),
        NameObject("/F"):    create_string_object(filename),
        NameObject("/UF"):   create_string_object(filename),
    })
    fs_ref = writer._add_object(fs)

    launch_action = DictionaryObject({
        NameObject("/Type"):      NameObject("/Action"),
        NameObject("/S"):         NameObject("/Launch"),
        NameObject("/F"):         fs_ref,
        NameObject("/NewWindow"): BooleanObject(True),
    })
    action_ref = writer._add_object(launch_action)

    annot = DictionaryObject({
        NameObject("/Type"):    NameObject("/Annot"),
        NameObject("/Subtype"): NameObject("/Link"),
        NameObject("/Rect"):    ArrayObject([
            NumberObject(x1), NumberObject(y1),
            NumberObject(x2), NumberObject(y2),
        ]),
        NameObject("/Border"): ArrayObject([NumberObject(0)] * 3),
        NameObject("/A"):       action_ref,
    })
    ann_ref = writer._add_object(annot)

    page = writer.pages[page_num]
    if "/Annots" not in page:
        page[NameObject("/Annots")] = ArrayObject()
    page[NameObject("/Annots")].append(ann_ref)

    with open(pdf_out, "wb") as out:
        writer.write(out)


# ─────────────────────────────────────────────────────────────────────────────
#  Modo B — Enlace + miniatura (compatible con todo visor)
# ─────────────────────────────────────────────────────────────────────────────

def embed_link(pdf_in, media_file, pdf_out, page_num=0,
               rect=(50, 650, 300, 750), thumbnail_path=None):
    from pypdf import PdfReader, PdfWriter
    from pypdf.generic import (
        ArrayObject, DictionaryObject, NameObject, NumberObject,
        create_string_object,
    )
    from reportlab.pdfgen import canvas as rl_canvas
    import tempfile

    reader = PdfReader(pdf_in)
    writer = PdfWriter()
    for p in reader.pages:
        writer.add_page(p)

    # --- Overlay con placeholder ---
    orig_page = reader.pages[page_num]
    pw = float(orig_page.mediabox.width)
    ph = float(orig_page.mediabox.height)

    tmp = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
    tmp.close()

    c = rl_canvas.Canvas(tmp.name, pagesize=(pw, ph))
    x1, y1, x2, y2 = rect
    label = ("▶  " if not _is_audio(media_file) else "♪  ") + Path(media_file).name

    if thumbnail_path and os.path.isfile(thumbnail_path):
        try:
            c.drawImage(thumbnail_path, x1, y1, width=x2-x1, height=y2-y1,
                        preserveAspectRatio=True, mask="auto")
        except Exception:
            _draw_placeholder(c, x1, y1, x2, y2, label, _is_audio(media_file))
    else:
        _draw_placeholder(c, x1, y1, x2, y2, label, _is_audio(media_file))
    c.save()

    from pypdf import PdfReader as PR2
    ov = PR2(tmp.name)
    writer.pages[page_num].merge_page(ov.pages[0])
    os.unlink(tmp.name)

    # --- Anotación URI con ruta relativa ---
    import shutil
    pdf_out_dir  = Path(pdf_out).parent
    media_dest   = pdf_out_dir / Path(media_file).name
    if Path(media_file).resolve() != media_dest.resolve():
        shutil.copy2(media_file, media_dest)
    # URI relativa: solo el nombre del archivo (misma carpeta que el PDF)
    from urllib.parse import quote
    rel_uri = quote(media_dest.name, safe="")
    link = DictionaryObject({
        NameObject("/Type"):    NameObject("/Annot"),
        NameObject("/Subtype"): NameObject("/Link"),
        NameObject("/Rect"):    ArrayObject([
            NumberObject(x1), NumberObject(y1),
            NumberObject(x2), NumberObject(y2),
        ]),
        NameObject("/Border"): ArrayObject([NumberObject(0)] * 3),
        NameObject("/A"): DictionaryObject({
            NameObject("/S"):   NameObject("/URI"),
            NameObject("/URI"): create_string_object(rel_uri),
        }),
    })
    ann_ref = writer._add_object(link)

    page = writer.pages[page_num]
    if "/Annots" not in page:
        page[NameObject("/Annots")] = ArrayObject()
    page[NameObject("/Annots")].append(ann_ref)

    with open(pdf_out, "wb") as out:
        writer.write(out)


def _draw_placeholder(c, x1, y1, x2, y2, label, is_audio):
    from reportlab.lib.colors import HexColor
    w, h = x2 - x1, y2 - y1
    bg = HexColor("#0f3460") if is_audio else HexColor("#1a1a2e")
    ac = HexColor("#e94560")

    c.setFillColor(bg)
    c.roundRect(x1, y1, w, h, 6, fill=1, stroke=0)
    c.setStrokeColor(ac)
    c.setLineWidth(1.5)
    c.roundRect(x1, y1, w, h, 6, fill=0, stroke=1)

    r = min(w, h) * 0.14
    cx, cy = x1 + w * 0.12, y1 + h * 0.5
    c.setFillColor(ac)
    c.circle(cx, cy, r, fill=1, stroke=0)
    c.setFillColor(HexColor("#ffffff"))
    if not is_audio:
        p = c.beginPath()
        p.moveTo(cx - r*.3, cy - r*.5)
        p.lineTo(cx - r*.3, cy + r*.5)
        p.lineTo(cx + r*.5, cy)
        p.close()
        c.drawPath(p, fill=1, stroke=0)
    else:
        c.setFont("Helvetica-Bold", r * 1.3)
        c.drawCentredString(cx, cy - r * .4, "♪")

    fs = max(6, min(9, h * 0.16))
    c.setFillColor(HexColor("#ffffff"))
    c.setFont("Helvetica", fs)
    max_c = int(w * 0.075)
    txt = label if len(label) <= max_c else label[:max_c - 1] + "…"
    c.drawString(x1 + w * 0.26, y1 + h * 0.52, txt)
    c.setFillColor(HexColor("#aaaaaa"))
    c.setFont("Helvetica-Oblique", max(5, fs * .85))
    c.drawString(x1 + w * 0.26, y1 + h * 0.24, "Haz clic para abrir")


# ─────────────────────────────────────────────────────────────────────────────
#  Constantes UI
# ─────────────────────────────────────────────────────────────────────────────

AUDIO_EXT = ("*.mp3","*.wav","*.ogg","*.aac","*.flac","*.m4a")
VIDEO_EXT = ("*.mp4","*.avi","*.mov","*.mkv","*.webm","*.wmv")
IMAGE_EXT = ("*.png","*.jpg","*.jpeg","*.gif","*.bmp","*.webp")
MEDIA_TYPES = [
    ("Multimedia", " ".join(AUDIO_EXT + VIDEO_EXT)),
    ("Audio",      " ".join(AUDIO_EXT)),
    ("Vídeo",      " ".join(VIDEO_EXT)),
    ("Todos",      "*.*"),
]

C = dict(
    BG    = "#f0f2f5",
    CARD  = "#dde1ea",
    ACC   = "#1a6bbf",
    FG    = "#1a1c2e",
    DIM   = "#5a6080",
    ENTRY = "#ffffff",
    SEL   = "#c5cfe0",
)

PREVIEW_W = 520   # anchura fija del canvas de previsualización


# ─────────────────────────────────────────────────────────────────────────────
#  Widget de vista previa con selector de zona
# ─────────────────────────────────────────────────────────────────────────────

class PDFPreview(tk.Frame):
    """
    Muestra una página del PDF como imagen y permite al usuario
    arrastrar un rectángulo para definir la zona de inserción.
    Devuelve la zona en coordenadas PDF (puntos, origen abajo-izquierda).
    """

    def __init__(self, master, **kw):
        super().__init__(master, bg=C["BG"], **kw)
        self._img        = None   # PhotoImage actual
        self._pil_img    = None   # PIL Image
        self._scale      = 1.0    # px_canvas / pt_pdf  (eje Y)
        self._pdf_w      = 0
        self._pdf_h      = 0
        self._canvas_h   = 0
        self._rect_id    = None
        self._sx = self._sy = self._ex = self._ey = 0
        self._rect_pdf   = None   # (x1,y1,x2,y2) en puntos PDF

        # ── Canvas de previsualización ────────────────────────────────────
        self.canvas = tk.Canvas(self, bg="#d0d5e8", cursor="crosshair",
                                highlightthickness=0,
                                width=PREVIEW_W, height=int(PREVIEW_W * 1.414))
        self.canvas.pack(fill="both", expand=True)

        self._label_hint = tk.Label(self,
                                    text="← Carga un PDF para ver la vista previa",
                                    bg=C["BG"], fg=C["DIM"],
                                    font=("Segoe UI", 11))
        self._label_hint.place(relx=.5, rely=.5, anchor="center")

        self._label_coords = tk.Label(self,
                                      text="", bg=C["BG"], fg=C["ACC"],
                                      font=("Courier New", 9))
        self._label_coords.pack(pady=(2, 0))

        self.canvas.bind("<ButtonPress-1>",   self._on_press)
        self.canvas.bind("<B1-Motion>",       self._on_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_release)

    # ── Carga de PDF ─────────────────────────────────────────────────────

    def load_pdf(self, pdf_path, page_num=0):
        try:
            from pdf2image import convert_from_path
        except ImportError:
            messagebox.showerror(
                "Dependencia faltante",
                "Instala pdf2image:\n  pip install pdf2image\n"
                "y poppler en el sistema."
            )
            return False

        try:
            import sys as _sys, subprocess as _sp
            if _sys.platform == "win32":
                # Parchear Popen temporalmente para ocultar la consola de poppler
                _orig_popen = _sp.Popen
                class _HiddenPopen(_orig_popen):
                    def __init__(self, *a, **kw):
                        kw.setdefault("creationflags", 0)
                        kw["creationflags"] |= _sp.CREATE_NO_WINDOW
                        super().__init__(*a, **kw)
                _sp.Popen = _HiddenPopen
            try:
                pages = convert_from_path(pdf_path, dpi=96,
                                          first_page=page_num + 1,
                                          last_page=page_num + 1,
                                          size=(PREVIEW_W, None),
                                          poppler_path=POPPLER_PATH)
            finally:
                if _sys.platform == "win32":
                    _sp.Popen = _orig_popen
                      
        except Exception as e:
            messagebox.showerror("Error al renderizar PDF", str(e))
            return False

        if not pages:
            return False

        pil = pages[0]
        self._pil_img  = pil
        self._canvas_h = pil.height

        # Dimensiones reales del PDF (en puntos)
        from pypdf import PdfReader
        reader = PdfReader(pdf_path)
        page   = reader.pages[page_num]
        self._pdf_w = float(page.mediabox.width)
        self._pdf_h = float(page.mediabox.height)

        # Escala: cuántos puntos PDF por píxel del canvas
        self._scale = self._pdf_h / self._canvas_h   # pt / px

        self.canvas.config(width=PREVIEW_W, height=self._canvas_h)
        self._img = self._pil_to_photo(pil)
        self.canvas.delete("all")
        self.canvas.create_image(0, 0, anchor="nw", image=self._img)
        self._rect_id = None
        self._rect_pdf = None
        self._label_hint.place_forget()
        self._label_coords.config(text="Arrastra para marcar la zona")
        return True

    @staticmethod
    def _pil_to_photo(pil_img):
        import io, base64
        buf = io.BytesIO()
        pil_img.save(buf, format="PNG")
        return tk.PhotoImage(data=base64.b64encode(buf.getvalue()))

    # ── Interacción ratón ─────────────────────────────────────────────────

    def _on_press(self, event):
        self._sx, self._sy = event.x, event.y
        if self._rect_id:
            self.canvas.delete(self._rect_id)
        self._rect_id = self.canvas.create_rectangle(
            self._sx, self._sy, self._sx, self._sy,
            outline="#e94560", width=2, dash=(4, 2))

    def _on_drag(self, event):
        self._ex, self._ey = event.x, event.y
        if self._rect_id:
            self.canvas.coords(self._rect_id,
                               self._sx, self._sy,
                               self._ex, self._ey)

    def _on_release(self, event):
        self._ex, self._ey = event.x, event.y
        if abs(self._ex - self._sx) < 5 or abs(self._ey - self._sy) < 5:
            return  # clic sin arrastrar
        self._rect_pdf = self._canvas_to_pdf(
            min(self._sx, self._ex), min(self._sy, self._ey),
            max(self._sx, self._ex), max(self._sy, self._ey),
        )
        x1, y1, x2, y2 = [round(v) for v in self._rect_pdf]
        self._label_coords.config(
            text=f"Zona PDF (pt): x1={x1}  y1={y1}  x2={x2}  y2={y2}"
        )

    def _canvas_to_pdf(self, cx1, cy1, cx2, cy2):
        """
        Convierte coordenadas canvas (px, origen arriba-izq)
        a coordenadas PDF (pt, origen abajo-izq).
        """
        s = self._scale
        pdf_x1 = cx1 * s
        pdf_x2 = cx2 * s
        # Invertir eje Y
        pdf_y1 = self._pdf_h - cy2 * s
        pdf_y2 = self._pdf_h - cy1 * s
        return (pdf_x1, pdf_y1, pdf_x2, pdf_y2)

    def get_rect(self):
        """Devuelve la zona seleccionada en puntos PDF, o None si no hay."""
        return self._rect_pdf


# ─────────────────────────────────────────────────────────────────────────────
#  Ventana principal
# ─────────────────────────────────────────────────────────────────────────────

class App(tk.Tk):

    def __init__(self):
        super().__init__()
        self.title("PDF Multimedia Embedder  v2.0")
        self.resizable(True, True)
        self._current_page = 0
        self._setup_style()
        self._build_ui()
        self._position_window()

    # ── Estilo ────────────────────────────────────────────────────────────

    def _setup_style(self):
        self.configure(bg=C["BG"])
        s = ttk.Style(self)
        s.theme_use("clam")

        s.configure(".",
                    background=C["BG"], foreground=C["FG"],
                    font=("Segoe UI", 11))
        s.configure("TFrame",       background=C["BG"])
        s.configure("Card.TFrame",  background=C["CARD"])
        s.configure("TLabel",       background=C["BG"],   foreground=C["FG"])
        s.configure("Dim.TLabel",   background=C["BG"],   foreground=C["DIM"],
                    font=("Segoe UI", 10))
        s.configure("Card.TLabel",  background=C["CARD"], foreground=C["FG"])
        s.configure("Head.TLabel",  background=C["BG"],   foreground=C["ACC"],
                    font=("Segoe UI", 15, "bold"))
        s.configure("Sub.TLabel",   background=C["BG"],   foreground=C["DIM"],
                    font=("Segoe UI", 10))
        s.configure("Acc.TLabel",   background=C["BG"],   foreground=C["ACC"],
                    font=("Segoe UI", 10, "bold"))

        s.configure("TEntry",
                    fieldbackground=C["ENTRY"], foreground=C["FG"],
                    insertcolor=C["FG"], borderwidth=1)
        s.configure("TButton",
                    background=C["CARD"], foreground=C["FG"],
                    relief="flat", padding=(10, 5))
        s.map("TButton", background=[("active", C["SEL"])])

        s.configure("Accent.TButton",
                    background=C["ACC"], foreground="#ffffff",
                    font=("Segoe UI", 11, "bold"), padding=(22, 9))
        s.map("Accent.TButton", background=[("active", "#145499")])

        s.configure("TRadiobutton",  background=C["BG"], foreground=C["FG"])
        s.map("TRadiobutton",
              background=[("active", C["BG"])],
              foreground=[("active", C["ACC"])])
        s.configure("TSpinbox",
                    fieldbackground=C["ENTRY"], foreground=C["FG"],
                    arrowcolor=C["FG"], borderwidth=1)
        s.configure("TCheckbutton",  background=C["BG"], foreground=C["FG"])

    # ── Construcción UI ───────────────────────────────────────────────────

    def _build_ui(self):
        # ═══ Layout raíz: izquierda (controles) | derecha (vista previa) ═
        root = ttk.Frame(self)
        root.pack(fill="both", expand=True, padx=0, pady=0)

        left  = ttk.Frame(root)
        left.pack(side="left", fill="both", expand=False,
                  padx=(20, 10), pady=14)

        right = ttk.Frame(root)
        right.pack(side="left", fill="both", expand=True,
                   padx=(0, 14), pady=14)

        # ── Columna izquierda ─────────────────────────────────────────────

        # Cabecera
        ttk.Label(left, text="🎬  PDF Multimedia Embedder",
                  style="Head.TLabel").pack(anchor="w")
        ttk.Label(left, text="Incrusta audio y vídeo en documentos PDF  ·  v2.0",
                  style="Sub.TLabel").pack(anchor="w", pady=(1, 10))

        tk.Frame(left, height=1, bg=C["CARD"]).pack(fill="x", pady=(0, 10))
        self._section(left, "Archivos")

        self.pdf_in_var = tk.StringVar()
        self._file_row(left, "PDF de entrada", self.pdf_in_var,
                       [("PDF", "*.pdf")], save=False,
                       on_change=self._on_pdf_selected)

        # Página
        pf = ttk.Frame(left)
        pf.pack(fill="x", padx=4, pady=3)
        ttk.Label(pf, text="Página:", width=20,
                  anchor="w").pack(side="left")
        self.page_var = tk.IntVar(value=0)
        self._total_pages = 0
        ttk.Button(pf, text="◀", width=2,
                   command=self._prev_page).pack(side="left")
        # Campo editable: escribe el número y pulsa Enter para saltar
        self._page_entry = ttk.Entry(pf, textvariable=self.page_var,
                                     width=5, justify="center")
        self._page_entry.pack(side="left", padx=2)
        self._page_entry.bind("<Return>",   lambda e: self._on_page_changed())
        self._page_entry.bind("<FocusOut>", lambda e: self._on_page_changed())
        self._total_label = tk.Label(pf, text="/ —", bg=C["BG"], fg=C["DIM"],
                                     font=("Segoe UI", 10))
        self._total_label.pack(side="left")
        ttk.Button(pf, text="▶", width=2,
                   command=self._next_page).pack(side="left", padx=(2, 0))

        self.media_var = tk.StringVar()
        self._file_row(left, "Archivo multimedia", self.media_var,
                       MEDIA_TYPES, save=False)

        self.pdf_out_var = tk.StringVar()
        self._file_row(left, "PDF de salida", self.pdf_out_var,
                       [("PDF", "*.pdf")], save=True)

        tk.Frame(left, height=1, bg=C["CARD"]).pack(fill="x", pady=(10, 6))

        # ── Modo ─────────────────────────────────────────────────────────
        self._section(left, "Modo de incrustación")

        self.mode_var = tk.StringVar(value="link")
        for val, title, desc in [
            ("link", "Modo B — Enlace URI",
             "Chrome, SumatraPDF y otros visores modernos"),
            ("real", "Modo A — Launch (Acrobat)",
             "Adobe Acrobat / Reader — abre con app del sistema"),
        ]:
            f = tk.Frame(left, bg=C["CARD"], padx=8)
            f.pack(fill="x", pady=2, ipady=5)
            tk.Radiobutton(
                f, text=title, variable=self.mode_var, value=val,
                bg=C["CARD"], fg=C["FG"],
                activebackground=C["CARD"], activeforeground=C["ACC"],
                selectcolor=C["ENTRY"], font=("Segoe UI", 10),
                bd=0
            ).pack(side="left")
            tk.Label(f, text=desc, bg=C["CARD"], fg=C["DIM"],
                     font=("Segoe UI", 8)).pack(side="left", padx=(4, 0))

        tk.Frame(left, height=1, bg=C["CARD"]).pack(fill="x", pady=(10, 6))

        # ── Miniatura opcional ────────────────────────────────────────────
        self._section(left, "Miniatura personalizada  (solo Modo B, opcional)")
        self.thumb_var = tk.StringVar()
        self._file_row(left, "Imagen", self.thumb_var,
                       [("Imágenes", " ".join(IMAGE_EXT))], save=False)

        tk.Frame(left, height=1, bg=C["CARD"]).pack(fill="x", pady=(10, 8))

        # ── Botón + estado ────────────────────────────────────────────────
        bf = ttk.Frame(left)
        bf.pack(fill="x")
        ttk.Button(bf, text="⚡  Incrustar ahora",
                   style="Accent.TButton",
                   command=self._run).pack(side="right")

        self.status_var = tk.StringVar(value="Listo.")
        tk.Label(bf, textvariable=self.status_var,
                 bg=C["BG"], fg=C["DIM"],
                 font=("Segoe UI", 9, "italic")).pack(side="left")

        # ── Columna derecha: vista previa ─────────────────────────────────
        ttk.Label(right, text="Vista previa · arrastra para marcar zona",
                  style="Acc.TLabel").pack(anchor="w", pady=(0, 6))

        self.preview = PDFPreview(right)
        self.preview.pack(fill="both", expand=True)

    # ── Sección helper ────────────────────────────────────────────────────

    def _section(self, parent, text):
        f = ttk.Frame(parent)
        f.pack(fill="x", pady=(6, 3))
        tk.Label(f, text=text.upper(), bg=C["BG"], fg=C["ACC"],
                 font=("Segoe UI", 8, "bold")).pack(side="left")

    def _file_row(self, parent, label, var, ftypes, save=False,
                  on_change=None):
        row = ttk.Frame(parent)
        row.pack(fill="x", pady=3)
        ttk.Label(row, text=label, width=20, anchor="w").pack(side="left")
        e = ttk.Entry(row, textvariable=var, width=34)
        e.pack(side="left", padx=(0, 6))
        if on_change:
            var.trace_add("write", lambda *_: on_change())
        ttk.Button(row, text="…",
                   command=lambda: self._browse(var, ftypes, save,
                                                on_change)).pack(side="left")

    def _browse(self, var, ftypes, save, callback=None):
        if save:
            path = filedialog.asksaveasfilename(
                filetypes=ftypes,
                defaultextension=".pdf"
            )
        else:
            path = filedialog.askopenfilename(filetypes=ftypes)
        if path:
            var.set(path)
            if callback:
                callback()

    def _prev_page(self):
        p = self.page_var.get()
        if p > 0:
            self.page_var.set(p - 1)
            self._on_page_changed()

    def _next_page(self):
        p = self.page_var.get()
        if self._total_pages == 0 or p < self._total_pages - 1:
            self.page_var.set(p + 1)
            self._on_page_changed()

    def _on_page_changed(self):
        # Clampar valor introducido manualmente
        try:
            p = self.page_var.get()
        except Exception:
            p = 0
        p = max(0, min(p, self._total_pages - 1) if self._total_pages > 0 else p)
        self.page_var.set(p)
        path = self.pdf_in_var.get().strip()
        if os.path.isfile(path):
            self._load_preview(path, p)

    def _on_pdf_selected(self):
        """Cuando se elige PDF: renderizar página y sugerir nombre de salida."""
        path = self.pdf_in_var.get().strip()
        if not os.path.isfile(path):
            return

        # Contar páginas totales
        try:
            from pypdf import PdfReader
            self._total_pages = len(PdfReader(path).pages)
            self._total_label.config(text=f"/ {self._total_pages}")
        except Exception:
            self._total_pages = 0
            self._total_label.config(text="/ —")

        self.page_var.set(0)

        # Sugerir nombre de salida
        if not self.pdf_out_var.get().strip():
            p    = Path(path)
            sugg = p.parent / (p.stem + "_con_multimedia" + p.suffix)
            self.pdf_out_var.set(str(sugg))

        self._load_preview(path, self.page_var.get())

    def _load_preview(self, path, page):
        self.status_var.set("Cargando vista previa…")
        self.update()

        def _worker():
            ok = self.preview.load_pdf(path, page)
            # Actualizar UI desde el hilo principal
            self.after(0, lambda: self.status_var.set(
                "Vista previa cargada.  Arrastra para marcar zona."
                if ok else "No se pudo renderizar el PDF."))

        threading.Thread(target=_worker, daemon=True).start()

    # ── Acción principal ──────────────────────────────────────────────────

    def _run(self):
        pdf_in  = self.pdf_in_var.get().strip()
        media   = self.media_var.get().strip()
        pdf_out = self.pdf_out_var.get().strip()
        mode    = self.mode_var.get()
        page    = self.page_var.get()
        thumb   = self.thumb_var.get().strip() or None
        rect    = self.preview.get_rect()

        errors = []
        if not pdf_in:                    errors.append("Selecciona un PDF de entrada.")
        if not media:                     errors.append("Selecciona un archivo multimedia.")
        if not pdf_out:                   errors.append("Indica dónde guardar el PDF de salida.")
        if not os.path.isfile(pdf_in or ""): errors.append("El PDF de entrada no existe.")
        if not os.path.isfile(media or ""): errors.append("El archivo multimedia no existe.")
        if rect is None:
            errors.append(
                "Marca la zona de inserción en la vista previa\n"
                "(arrastra el ratón sobre la página del PDF)."
            )
        if errors:
            messagebox.showerror("Campos incompletos", "\n".join(errors))
            return

        self.status_var.set("Procesando…")
        self.update()

        try:
            if mode == "real":
                embed_real(pdf_in, media, pdf_out, page_num=page, rect=rect, thumbnail_path=thumb)
            else:
                embed_link(pdf_in, media, pdf_out,
                           page_num=page, rect=rect, thumbnail_path=thumb)

            name = Path(pdf_out).name
            self.status_var.set(f"✓  Guardado: {name}")

            # ── Encadenar: el PDF de salida pasa a ser la nueva entrada ──
            self.pdf_in_var.set(pdf_out)
            try:
                from pypdf import PdfReader
                self._total_pages = len(PdfReader(pdf_out).pages)
                self._total_label.config(text=f"/ {self._total_pages}")
            except Exception:
                pass

            if mode == "real":
                info = (f"PDF guardado:\n{pdf_out}\n\n"
                        "✅  Modo A (Acrobat/Launch)\n"
                        "El multimedia se ha copiado junto al PDF.\n"
                        "Acrobat pedirá confirmación al hacer clic — acepta.")
            else:
                info = (f"PDF guardado:\n{pdf_out}\n\n"
                        "✅  Modo B (URI)\n"
                        "El multimedia se ha copiado junto al PDF.\n"
                        "Funciona en Chrome y visores modernos.")
            messagebox.showinfo("¡Listo!", info)

        except ImportError as e:
            self.status_var.set("Error: falta dependencia.")
            messagebox.showerror(
                "Dependencia no encontrada",
                f"{e}\n\nInstala con:\n  pip install pypdf reportlab pillow pdf2image"
            )
        except Exception as e:
            self.status_var.set("Error al procesar.")
            messagebox.showerror("Error", str(e))

    # ── Posicionado de ventana ─────────────────────────────────────────────

    def _position_window(self):
        """Centra horizontalmente y sitúa a 5 px del borde superior."""
        self.update_idletasks()
        w = self.winfo_reqwidth()
        h = self.winfo_reqheight()
        sw = self.winfo_screenwidth()
        x = (sw - w) // 2
        y = 5
        self.geometry(f"{w}x{h}+{x}+{y}")


# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    App().mainloop()
