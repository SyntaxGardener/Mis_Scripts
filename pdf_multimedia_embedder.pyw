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

def embed_real(pdf_in, pdf_out, items, thumbnail_path=None):
    """
    Modo A — incrusta TODOS los multimedia en una unica pasada.

    items : lista de tuplas (page_num, rect, media_file)
            donde rect = (x1, y1, x2, y2) en puntos PDF (origen abajo-izq.)

    Al procesar todos los items en un unico PdfWriter antes de escribir,
    se evita el problema de que add_attachment sobreescriba adjuntos previos.
    """
    import json, tempfile
    from pypdf import PdfReader, PdfWriter
    from pypdf.generic import (
        ArrayObject, DictionaryObject, NameObject, NumberObject,
        create_string_object,
    )
    from reportlab.pdfgen import canvas as rl_canvas

    if not items:
        raise ValueError("La lista de multimedia esta vacia.")

    reader = PdfReader(pdf_in)
    writer = PdfWriter()
    for p in reader.pages:
        writer.add_page(p)

    added_files = set()   # para no adjuntar dos veces el mismo archivo

    for (page_num, rect, media_file) in items:
        filename = Path(media_file).name
        pw = float(reader.pages[page_num].mediabox.width)
        ph = float(reader.pages[page_num].mediabox.height)

        # -- Overlay visual (placeholder / miniatura) ----------------------
        tmp = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
        tmp.close()
        c = rl_canvas.Canvas(tmp.name, pagesize=(pw, ph))
        x1, y1, x2, y2 = rect
        label = ("  " if not _is_audio(media_file) else "  ") + filename
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

        # -- Adjuntar el archivo (solo una vez por nombre) -----------------
        if filename not in added_files:
            with open(media_file, "rb") as f:
                media_data = f.read()
            writer.add_attachment(filename, media_data)
            added_files.add(filename)

        # -- Accion JavaScript: extraer a temp y abrir con reproductor -----
        js_code = (
            f'var f = {json.dumps(filename)};\n'
            f'this.exportDataObject({{cName: f, nLaunch: 2}});'
        )
        js_action = DictionaryObject({
            NameObject("/Type"): NameObject("/Action"),
            NameObject("/S"):    NameObject("/JavaScript"),
            NameObject("/JS"):   create_string_object(js_code),
        })
        js_ref = writer._add_object(js_action)

        # -- Anotacion /Link sobre el placeholder --------------------------
        annot = DictionaryObject({
            NameObject("/Type"):    NameObject("/Annot"),
            NameObject("/Subtype"): NameObject("/Link"),
            NameObject("/Rect"):    ArrayObject([
                NumberObject(x1), NumberObject(y1),
                NumberObject(x2), NumberObject(y2),
            ]),
            NameObject("/Border"): ArrayObject([NumberObject(0)] * 3),
            NameObject("/A"):       js_ref,
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

    # --- Anotación /Launch con ruta relativa ---
    # Usamos /Launch en lugar de /URI porque:
    #   · /URI con file:// está bloqueado por Chrome/Edge por política de seguridad.
    #   · /Launch con nombre relativo funciona en Acrobat y SumatraPDF,
    #     que buscan el archivo en la misma carpeta que el PDF.
    import shutil
    pdf_out_dir = Path(pdf_out).parent
    media_dest  = pdf_out_dir / Path(media_file).name
    if Path(media_file).resolve() != media_dest.resolve():
        shutil.copy2(media_file, media_dest)

    rel_name = Path(media_file).name   # nombre relativo — el visor resuelve la ruta

    link = DictionaryObject({
        NameObject("/Type"):    NameObject("/Annot"),
        NameObject("/Subtype"): NameObject("/Link"),
        NameObject("/Rect"):    ArrayObject([
            NumberObject(x1), NumberObject(y1),
            NumberObject(x2), NumberObject(y2),
        ]),
        NameObject("/Border"): ArrayObject([NumberObject(0)] * 3),
        NameObject("/A"): DictionaryObject({
            NameObject("/S"): NameObject("/Launch"),
            NameObject("/F"): create_string_object(rel_name),
        }),
    })
    ann_ref = writer._add_object(link)

    page = writer.pages[page_num]
    if "/Annots" not in page:
        page[NameObject("/Annots")] = ArrayObject()
    page[NameObject("/Annots")].append(ann_ref)

    with open(pdf_out, "wb") as out:
        writer.write(out)


# ─────────────────────────────────────────────────────────────────────────────
#  Modo C — HTML autocontenido (todo base64, sin internet ni instalaciones)
# ─────────────────────────────────────────────────────────────────────────────

def embed_html(pdf_in, html_out, items):
    """
    Genera un único .html autocontenido con todas las páginas del PDF y
    todos los multimedia embebidos en base64.

    items : lista de tuplas  (page_num, rect, media_file)
            donde rect = (x1, y1, x2, y2) en puntos PDF (origen abajo-izq.)

    Modo de reproducción: clic en placeholder → panel flotante central.
    Solo un reproductor abierto a la vez; cerrar devuelve la vista normal.
    """
    import base64, io, json
    from pathlib import Path
    from pypdf import PdfReader

    if not items:
        raise ValueError("La lista de multimedia está vacía.")

    # ── Dimensiones de cada página del PDF ──────────────────────────────
    reader = PdfReader(pdf_in)
    page_dims = []
    for pg in reader.pages:
        page_dims.append((float(pg.mediabox.width), float(pg.mediabox.height)))

    # ── Renderizar todas las páginas ─────────────────────────────────────
    try:
        from pdf2image import convert_from_path
    except ImportError:
        raise ImportError("pdf2image no está instalado.\n"
                          "Ejecuta:  pip install pdf2image")

    import sys as _sys, subprocess as _sp
    if _sys.platform == "win32":
        _orig = _sp.Popen
        class _NW(_orig):
            def __init__(self, *a, **kw):
                kw.setdefault("creationflags", 0)
                kw["creationflags"] |= _sp.CREATE_NO_WINDOW
                super().__init__(*a, **kw)
        _sp.Popen = _NW
    try:
        pages_pil = convert_from_path(pdf_in, dpi=120, poppler_path=POPPLER_PATH)
    finally:
        if _sys.platform == "win32":
            _sp.Popen = _orig

    # ── Páginas → base64 PNG ─────────────────────────────────────────────
    pages_b64 = []
    for img in pages_pil:
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        pages_b64.append(base64.b64encode(buf.getvalue()).decode())

    # ── Pre-codificar cada archivo multimedia ────────────────────────────
    # (un mismo archivo puede aparecer en varios ítems; lo cacheamos)
    _media_cache = {}
    def _get_data_uri(media_file):
        if media_file not in _media_cache:
            with open(media_file, "rb") as f:
                b64 = base64.b64encode(f.read()).decode()
            _media_cache[media_file] = f"data:{_mime(media_file)};base64,{b64}"
        return _media_cache[media_file]

    # ── Construir tabla de medias indexada (id → data_uri, mime, es_audio) ──
    # Cada placeholder guarda solo el índice; el JS resuelve el resto.
    media_index = []   # lista de dicts {src, mime, audio, name}
    media_id_map = {}  # media_file → índice en media_index

    for (_, __, media_file) in items:
        if media_file not in media_id_map:
            media_id_map[media_file] = len(media_index)
            media_index.append({
                "src":   _get_data_uri(media_file),
                "mime":  _mime(media_file),
                "audio": _is_audio(media_file),
                "name":  Path(media_file).name,
            })

    # ── Agrupar ítems por página ─────────────────────────────────────────
    from collections import defaultdict
    items_by_page = defaultdict(list)
    for (page_num, rect, media_file) in items:
        items_by_page[page_num].append((rect, media_file))

    # ── Construir bloques de página ──────────────────────────────────────
    blocks = []
    for i, b64 in enumerate(pages_b64):
        pdf_w, pdf_h = page_dims[i] if i < len(page_dims) else (595, 842)
        overlays = ""
        for (rect, media_file) in items_by_page.get(i, []):
            x1, y1, x2, y2 = rect
            left_pct   = x1 / pdf_w * 100
            top_pct    = (pdf_h - y2) / pdf_h * 100
            width_pct  = (x2 - x1) / pdf_w * 100
            height_pct = (y2 - y1) / pdf_h * 100
            mid        = media_id_map[media_file]
            name       = Path(media_file).name
            icon       = "♪" if _is_audio(media_file) else "▶"
            # El placeholder es un botón que llama a openPlayer(idx)
            import html as _html
            safe_name = _html.escape(name, quote=True)
            overlays += (
                f'<button class="ph" '
                f'style="left:{left_pct:.3f}%;top:{top_pct:.3f}%;'
                f'width:{width_pct:.3f}%;height:{height_pct:.3f}%;" '
                f'onclick="openPlayer({mid})" '
                f'title="{safe_name}">'
                f'<span class="ph-icon">{icon}</span>'
                f'<span class="ph-name">{safe_name}</span>'
                f'<span class="ph-hint">Clic para reproducir</span>'
                f'</button>'
            )
        blocks.append(
            f'<div class="page-wrap">'
            f'<img src="data:image/png;base64,{b64}" '
            f'style="width:100%;display:block;" alt="Página {i+1}">'
            f'{overlays}</div>'
        )

    pdf_stem   = Path(pdf_in).stem
    n_media    = len(items)
    media_desc = f"{n_media} elemento{'s' if n_media != 1 else ''} multimedia"

    # ── Serializar la tabla de medias como JSON para el script ───────────
    media_json = json.dumps(media_index, ensure_ascii=True)

    # ── CSS + JS del panel flotante ──────────────────────────────────────
    style = """
*{box-sizing:border-box;margin:0;padding:0}
body{background:#2a2d3e;padding:20px 12px;font-family:'Segoe UI',sans-serif}
.hdr{text-align:center;color:#9aa0b8;font-size:12px;margin-bottom:16px}
img{box-shadow:0 4px 20px rgba(0,0,0,.5)}

/* ── Placeholder ── */
.page-wrap{position:relative;max-width:900px;margin:0 auto 20px}
.ph{
  position:absolute;
  background:rgba(15,52,96,0.88);
  border:2px solid #e94560;
  border-radius:8px;
  cursor:pointer;
  display:flex;flex-direction:column;
  align-items:center;justify-content:center;
  gap:4px;
  padding:6px 4px;
  overflow:hidden;
  transition:background .15s,border-color .15s,transform .1s;
  color:#fff;
}
.ph:hover{background:rgba(15,52,96,1);border-color:#ff7b8a;transform:scale(1.03)}
.ph-icon{font-size:clamp(14px,3.5cqw,30px);line-height:1}
.ph-name{font-size:clamp(7px,1.4cqw,12px);opacity:.85;
         max-width:90%;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.ph-hint{font-size:clamp(6px,1.1cqw,10px);opacity:.55;font-style:italic}

/* ── Overlay oscuro ── */
#overlay{
  display:none;
  position:fixed;inset:0;
  background:rgba(0,0,0,.65);
  z-index:1000;
  align-items:center;justify-content:center;
}
#overlay.visible{display:flex}

/* ── Panel flotante ── */
#panel{
  background:#1a1c2e;
  border:2px solid #e94560;
  border-radius:12px;
  padding:14px;
  width:98vw;
  height:98vh;
  display:flex;flex-direction:column;
  gap:8px;
  box-shadow:0 8px 40px rgba(0,0,0,.7);
  position:relative;
}
#panel-title{
  color:#c8cfe8;
  font-size:13px;
  font-weight:600;
  white-space:nowrap;overflow:hidden;text-overflow:ellipsis;
  padding-right:28px;
  flex:none;
}
#panel-media{
  width:100%;
  flex:1 1 0;
  min-height:0;
  border-radius:6px;
  background:#000;
  object-fit:contain;
  display:block;
}
audio#panel-media{flex:none;background:#0f1a2e;height:54px}
.ctrl-btn.fs-btn{background:#1a2e1a;border-color:#4caf50;color:#a5d6a7;font-size:15px;padding:6px 10px}
.ctrl-btn.fs-btn:hover{background:#2a3e2a}

/* ── Barra de controles personalizados ── */
#ctrl-bar{
  display:flex;gap:8px;align-items:center;
}
.ctrl-btn{
  background:#2a2d3e;border:1px solid #3a3d5e;
  color:#c8cfe8;border-radius:6px;
  padding:6px 14px;font-size:12px;cursor:pointer;
  transition:background .12s;
}
.ctrl-btn:hover{background:#3a3d5e}
.ctrl-btn.close-btn{margin-left:auto;background:#3a0f18;border-color:#e94560;color:#ff8a98}
.ctrl-btn.close-btn:hover{background:#5a1525}

/* ── Botón X en esquina ── */
#btn-x{
  position:absolute;top:10px;right:12px;
  background:none;border:none;color:#9aa0b8;
  font-size:18px;cursor:pointer;line-height:1;padding:2px 4px;
  border-radius:4px;
}
#panel-dur{font-size:11px;font-weight:400;color:#e94560;
  background:rgba(233,69,96,.12);border:1px solid rgba(233,69,96,.35);
  border-radius:4px;padding:1px 6px;margin-left:6px;vertical-align:middle;
  white-space:nowrap}
"""

    script = f"""
const MEDIA = {media_json};

const overlay   = document.getElementById('overlay');
const panel     = document.getElementById('panel');
const panelTitle= document.getElementById('panel-name');
const panelDur  = document.getElementById('panel-dur');
const mediaEl   = document.getElementById('panel-media');
const btnPlay   = document.getElementById('btn-play');
const btnPause  = document.getElementById('btn-pause');
const btnStop   = document.getElementById('btn-stop');

function openPlayer(idx) {{
  const m = MEDIA[idx];
  // Limpiar source previo
  mediaEl.pause && mediaEl.pause();
  mediaEl.removeAttribute('src');
  // Reemplazar el elemento por el tipo correcto si cambia (audio<->video)
  const tag = m.audio ? 'audio' : 'video';
  if (mediaEl.tagName.toLowerCase() !== tag) {{
    const neo = document.createElement(tag);
    neo.id = 'panel-media';
    neo.style.cssText = mediaEl.style.cssText;
    if (!m.audio) {{ neo.style.background='#000'; neo.style.maxHeight='60vh'; }}
    else {{ neo.style.background='#0f1a2e'; neo.style.height='54px'; }}
    mediaEl.replaceWith(neo);
  }}
  const el = document.getElementById('panel-media');
  el.src  = m.src;
  el.type = m.mime;
  panelTitle.textContent = m.name;
  panelDur.textContent = '';
  overlay.classList.add('visible');
  el.play().catch(()=>{{}});
  // Reconectar botones al nuevo elemento
  _bindButtons();
}}

function closePlayer() {{
  const el = document.getElementById('panel-media');
  el.pause && el.pause();
  el.currentTime = 0;
  el.removeAttribute('src');
  overlay.classList.remove('visible');
}}

function _bindButtons() {{
  const el = document.getElementById('panel-media');
  btnPlay.onclick  = () => el.play();
  btnPause.onclick = () => el.pause();
  btnStop.onclick  = () => {{ el.pause(); el.currentTime = 0; }};
  el.onloadedmetadata = () => {{
    if (!isFinite(el.duration)) return;
    const s = Math.floor(el.duration);
    const h = Math.floor(s/3600), m = Math.floor((s%3600)/60), sec = s%60;
    panelDur.textContent = h>0
      ? h+'h '+String(m).padStart(2,'0')+'m '+String(sec).padStart(2,'0')+'s'
      : m>0 ? m+'m '+String(sec).padStart(2,'0')+'s' : sec+'s';
  }};
  document.getElementById('btn-fs').onclick = () => {{
    const target = document.getElementById('panel-media');
    const req = target.requestFullscreen
               || target.webkitRequestFullscreen
               || target.mozRequestFullScreen
               || target.msRequestFullscreen;
    if (req) req.call(target);
  }};
}}
_bindButtons();

document.getElementById('btn-close').onclick = closePlayer;
document.getElementById('btn-x').onclick     = closePlayer;
// Clic en el fondo oscuro cierra el panel
overlay.addEventListener('click', e => {{ if (e.target === overlay) closePlayer(); }});
// Tecla Escape
document.addEventListener('keydown', e => {{ if (e.key === 'Escape') closePlayer(); }});
"""

    html = (
        '<!DOCTYPE html>\n<html lang="es">\n<head>\n'
        '<meta charset="UTF-8">\n'
        '<meta name="viewport" content="width=device-width,initial-scale=1.0">\n'
        f'<title>{pdf_stem}</title>\n'
        f'<style>{style}</style>\n'
        '</head>\n<body>\n'
        f'<div class="hdr">&#128196; {pdf_stem} &nbsp;&middot;&nbsp; '
        f'{media_desc} &nbsp;&middot;&nbsp; '
        'PDF Multimedia Embedder &mdash; Modo C</div>\n'
        + "".join(blocks)
        # ── Panel flotante (único en el DOM) ──────────────────────────────
        + """
<div id="overlay">
  <div id="panel">
    <button id="btn-x" title="Cerrar">&#x2715;</button>
    <div id="panel-title"><span id="panel-name">&hellip;</span> <span id="panel-dur"></span></div>
    <audio id="panel-media" style="width:100%;background:#0f1a2e;height:54px;border-radius:6px"></audio>
    <div id="ctrl-bar">
      <button class="ctrl-btn" id="btn-play">&#9654; Play</button>
      <button class="ctrl-btn" id="btn-pause">&#9646;&#9646; Pausa</button>
      <button class="ctrl-btn" id="btn-stop">&#9632; Detener</button>
      <button class="ctrl-btn fs-btn" id="btn-fs" title="Pantalla completa">&#x26F6; Pantalla completa</button>
      <button class="ctrl-btn close-btn" id="btn-close">&#x2715; Cerrar</button>
    </div>
  </div>
</div>
"""
        + f'<script>{script}</script>\n'
        + "</body>\n</html>"
    )

    with open(html_out, "w", encoding="utf-8") as f:
        f.write(html)


# ─────────────────────────────────────────────────────────────────────────────
#  Modo D — HTML ligero + archivos multimedia en carpeta _media/
#  (ideal para pizarras digitales y dispositivos con poca RAM)
# ─────────────────────────────────────────────────────────────────────────────

def embed_html_linked(pdf_in, html_out, items):
    """
    Genera un .html ligero que referencia los multimedia por ruta relativa.
    Los archivos se copian en  <nombre_html>_media/  junto al HTML.

    items : lista de tuplas  (page_num, rect, media_file)
    """
    import io, json, shutil, html as _html_mod
    from pathlib import Path
    from pypdf import PdfReader

    if not items:
        raise ValueError("La lista de multimedia está vacía.")

    html_out  = Path(html_out)
    media_dir = html_out.parent / (html_out.stem + "_media")
    media_dir.mkdir(exist_ok=True)

    # ── Dimensiones PDF ──────────────────────────────────────────────────
    reader = PdfReader(pdf_in)
    page_dims = [(float(pg.mediabox.width), float(pg.mediabox.height))
                 for pg in reader.pages]

    # ── Renderizar páginas ───────────────────────────────────────────────
    try:
        from pdf2image import convert_from_path
    except ImportError:
        raise ImportError("pdf2image no está instalado.\nEjecuta:  pip install pdf2image")

    import sys as _sys, subprocess as _sp, base64
    if _sys.platform == "win32":
        _orig = _sp.Popen
        class _NW(_orig):
            def __init__(self, *a, **kw):
                kw.setdefault("creationflags", 0)
                kw["creationflags"] |= _sp.CREATE_NO_WINDOW
                super().__init__(*a, **kw)
        _sp.Popen = _NW
    try:
        pages_pil = convert_from_path(pdf_in, dpi=120, poppler_path=POPPLER_PATH)
    finally:
        if _sys.platform == "win32":
            _sp.Popen = _orig

    # Guardar páginas como PNG en _media/
    pages_src = []
    for i, img in enumerate(pages_pil):
        png_path = media_dir / f"page_{i+1}.png"
        img.save(png_path, format="PNG")
        pages_src.append(f"{html_out.stem}_media/page_{i+1}.png")

    # ── Copiar multimedia a _media/ ──────────────────────────────────────
    copied = {}   # media_file → nombre en _media/
    counters = {}
    for (_, __, media_file) in items:
        if media_file in copied:
            continue
        dest_name = Path(media_file).name
        dest = media_dir / dest_name
        # Evitar colisiones de nombre
        if dest.exists() and dest.resolve() != Path(media_file).resolve():
            stem, suf = Path(dest_name).stem, Path(dest_name).suffix
            n = counters.get(dest_name, 1)
            dest_name = f"{stem}_{n}{suf}"
            counters[dest_name] = n + 1
            dest = media_dir / dest_name
        if Path(media_file).resolve() != dest.resolve():
            shutil.copy2(media_file, dest)
        copied[media_file] = dest_name

    # ── Tabla de medias (sin base64 — solo ruta relativa) ────────────────
    media_index = []
    media_id_map = {}
    for (_, __, media_file) in items:
        if media_file not in media_id_map:
            media_id_map[media_file] = len(media_index)
            rel = f"{html_out.stem}_media/{copied[media_file]}"
            media_index.append({
                "src":   rel,
                "mime":  _mime(media_file),
                "audio": _is_audio(media_file),
                "name":  Path(media_file).name,
            })
    media_json = json.dumps(media_index, ensure_ascii=True)

    # ── Agrupar ítems por página ─────────────────────────────────────────
    from collections import defaultdict
    items_by_page = defaultdict(list)
    for (page_num, rect, media_file) in items:
        items_by_page[page_num].append((rect, media_file))

    # ── Construir bloques de página ──────────────────────────────────────
    blocks = []
    for i, img_src in enumerate(pages_src):
        pdf_w, pdf_h = page_dims[i] if i < len(page_dims) else (595, 842)
        overlays = ""
        for (rect, media_file) in items_by_page.get(i, []):
            x1, y1, x2, y2 = rect
            left_pct   = x1 / pdf_w * 100
            top_pct    = (pdf_h - y2) / pdf_h * 100
            width_pct  = (x2 - x1) / pdf_w * 100
            height_pct = (y2 - y1) / pdf_h * 100
            mid        = media_id_map[media_file]
            name       = Path(media_file).name
            icon       = "\u266a" if _is_audio(media_file) else "\u25b6"
            safe_name  = _html_mod.escape(name, quote=True)
            overlays += (
                f'<button class="ph" '
                f'style="left:{left_pct:.3f}%;top:{top_pct:.3f}%;'
                f'width:{width_pct:.3f}%;height:{height_pct:.3f}%;" '
                f'onclick="openPlayer({mid})" '
                f'title="{safe_name}">'
                f'<span class="ph-icon">{icon}</span>'
                f'<span class="ph-name">{safe_name}</span>'
                f'<span class="ph-hint">Clic para reproducir</span>'
                f'</button>'
            )
        blocks.append(
            f'<div class="page-wrap">'
            f'<img src="{img_src}" style="width:100%;display:block;" alt="P\u00e1gina {i+1}">'
            f'{overlays}</div>'
        )

    pdf_stem   = Path(pdf_in).stem
    n_media    = len(items)
    media_desc = f"{n_media} elemento{'s' if n_media != 1 else ''} multimedia"

    # ── Reutilizar el mismo CSS/JS/HTML que Modo C ───────────────────────
    # (copiamos style y script de embed_html — misma estructura de panel)
    style = """
*{box-sizing:border-box;margin:0;padding:0}
body{background:#2a2d3e;padding:20px 12px;font-family:'Segoe UI',sans-serif}
.hdr{text-align:center;color:#9aa0b8;font-size:12px;margin-bottom:16px}
img{box-shadow:0 4px 20px rgba(0,0,0,.5)}
.page-wrap{position:relative;max-width:900px;margin:0 auto 20px}
.ph{position:absolute;background:rgba(15,52,96,0.88);border:2px solid #e94560;
  border-radius:8px;cursor:pointer;display:flex;flex-direction:column;
  align-items:center;justify-content:center;gap:4px;padding:6px 4px;
  overflow:hidden;transition:background .15s,border-color .15s,transform .1s;color:#fff}
.ph:hover{background:rgba(15,52,96,1);border-color:#ff7b8a;transform:scale(1.03)}
.ph-icon{font-size:clamp(14px,3.5cqw,30px);line-height:1}
.ph-name{font-size:clamp(7px,1.4cqw,12px);opacity:.85;
  max-width:90%;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.ph-hint{font-size:clamp(6px,1.1cqw,10px);opacity:.55;font-style:italic}
#overlay{display:none;position:fixed;inset:0;background:rgba(0,0,0,.65);
  z-index:1000;align-items:center;justify-content:center}
#overlay.visible{display:flex}
#panel{background:#1a1c2e;border:2px solid #e94560;border-radius:12px;
  padding:14px;width:98vw;height:98vh;display:flex;flex-direction:column;
  gap:8px;box-shadow:0 8px 40px rgba(0,0,0,.7);position:relative}
#panel-title{color:#c8cfe8;font-size:13px;font-weight:600;
  white-space:nowrap;overflow:hidden;text-overflow:ellipsis;padding-right:28px;flex:none}
#panel-name{display:inline}
#panel-media{width:100%;flex:1 1 0;min-height:0;border-radius:6px;
  background:#000;object-fit:contain;display:block}
audio#panel-media{flex:none;background:#0f1a2e;height:54px}
#ctrl-bar{display:flex;gap:8px;align-items:center}
.ctrl-btn{background:#2a2d3e;border:1px solid #3a3d5e;color:#c8cfe8;
  border-radius:6px;padding:6px 14px;font-size:12px;cursor:pointer;transition:background .12s}
.ctrl-btn:hover{background:#3a3d5e}
.ctrl-btn.fs-btn{background:#1a2e1a;border-color:#4caf50;color:#a5d6a7;font-size:15px;padding:6px 10px}
.ctrl-btn.fs-btn:hover{background:#2a3e2a}
.ctrl-btn.close-btn{margin-left:auto;background:#3a0f18;border-color:#e94560;color:#ff8a98}
.ctrl-btn.close-btn:hover{background:#5a1525}
#btn-x{position:absolute;top:10px;right:12px;background:none;border:none;
  color:#9aa0b8;font-size:18px;cursor:pointer;line-height:1;padding:2px 4px;border-radius:4px}
#btn-x:hover{color:#ff8a98;background:rgba(233,69,96,.15)}
#panel-dur{font-size:11px;font-weight:400;color:#e94560;
  background:rgba(233,69,96,.12);border:1px solid rgba(233,69,96,.35);
  border-radius:4px;padding:1px 6px;margin-left:6px;vertical-align:middle;white-space:nowrap}
"""

    script = f"""
const MEDIA = {media_json};
const overlay   = document.getElementById('overlay');
const panelTitle= document.getElementById('panel-name');
const panelDur  = document.getElementById('panel-dur');
const mediaEl   = document.getElementById('panel-media');
const btnPlay   = document.getElementById('btn-play');
const btnPause  = document.getElementById('btn-pause');
const btnStop   = document.getElementById('btn-stop');
function openPlayer(idx) {{
  const m = MEDIA[idx];
  mediaEl.pause && mediaEl.pause();
  mediaEl.removeAttribute('src');
  const tag = m.audio ? 'audio' : 'video';
  if (mediaEl.tagName.toLowerCase() !== tag) {{
    const neo = document.createElement(tag);
    neo.id = 'panel-media';
    if (!m.audio) {{ neo.style.cssText='width:100%;flex:1 1 0;min-height:0;border-radius:6px;background:#000;object-fit:contain;display:block'; }}
    else {{ neo.style.cssText='width:100%;flex:none;background:#0f1a2e;height:54px;border-radius:6px'; }}
    mediaEl.replaceWith(neo);
  }}
  const el = document.getElementById('panel-media');
  el.src  = m.src;
  el.type = m.mime;
  panelTitle.textContent = m.name;
  panelDur.textContent = '';
  overlay.classList.add('visible');
  el.play().catch(()=>{{}});
  _bindButtons();
}}
function closePlayer() {{
  const el = document.getElementById('panel-media');
  el.pause && el.pause();
  el.currentTime = 0;
  el.removeAttribute('src');
  overlay.classList.remove('visible');
}}
function _bindButtons() {{
  const el = document.getElementById('panel-media');
  btnPlay.onclick  = () => el.play();
  btnPause.onclick = () => el.pause();
  btnStop.onclick  = () => {{ el.pause(); el.currentTime = 0; }};
  el.onloadedmetadata = () => {{
    if (!isFinite(el.duration)) return;
    const s=Math.floor(el.duration), h=Math.floor(s/3600), m=Math.floor((s%3600)/60), sec=s%60;
    panelDur.textContent = h>0 ? h+'h '+String(m).padStart(2,'0')+'m '+String(sec).padStart(2,'0')+'s'
                         : m>0 ? m+'m '+String(sec).padStart(2,'0')+'s' : sec+'s';
  }};
  document.getElementById('btn-fs').onclick = () => {{
    const t = document.getElementById('panel-media');
    (t.requestFullscreen||t.webkitRequestFullscreen||t.mozRequestFullScreen||t.msRequestFullscreen).call(t);
  }};
}}
_bindButtons();
document.getElementById('btn-close').onclick = closePlayer;
document.getElementById('btn-x').onclick     = closePlayer;
overlay.addEventListener('click', e => {{ if (e.target===overlay) closePlayer(); }});
document.addEventListener('keydown', e => {{ if (e.key==='Escape') closePlayer(); }});
"""

    html_content = (
        '<!DOCTYPE html>\n<html lang="es">\n<head>\n'
        '<meta charset="UTF-8">\n'
        '<meta name="viewport" content="width=device-width,initial-scale=1.0">\n'
        f'<title>{pdf_stem}</title>\n'
        f'<style>{style}</style>\n'
        '</head>\n<body>\n'
        f'<div class="hdr">&#128196; {pdf_stem} &nbsp;&middot;&nbsp; '
        f'{media_desc} &nbsp;&middot;&nbsp; '
        'PDF Multimedia Embedder &mdash; Modo D</div>\n'
        + "".join(blocks)
        + '''
<div id="overlay">
  <div id="panel">
    <button id="btn-x" title="Cerrar">&#x2715;</button>
    <div id="panel-title"><span id="panel-name">&hellip;</span><span id="panel-dur"></span></div>
    <audio id="panel-media" style="width:100%;flex:none;background:#0f1a2e;height:54px;border-radius:6px"></audio>
    <div id="ctrl-bar">
      <button class="ctrl-btn" id="btn-play">&#9654; Play</button>
      <button class="ctrl-btn" id="btn-pause">&#9646;&#9646; Pausa</button>
      <button class="ctrl-btn" id="btn-stop">&#9632; Detener</button>
      <button class="ctrl-btn fs-btn" id="btn-fs" title="Pantalla completa">&#x26F6; Pantalla completa</button>
      <button class="ctrl-btn close-btn" id="btn-close">&#x2715; Cerrar</button>
    </div>
  </div>
</div>
'''
        + f'<script>{script}</script>\n'
        + "</body>\n</html>"
    )

    with open(html_out, "w", encoding="utf-8") as f:
        f.write(html_content)


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
        self.title("PDF Multimedia Embedder  v3.0")
        self.resizable(True, True)
        self._current_page = 0
        self._last_loaded_page = -1
        self._html_items = []   # lista acumulada Modo C: [(page, rect, media), ...]
        self._html_d_items = []  # lista acumulada Modo D
        self._real_items = []   # lista acumulada Modo A: [(page, rect, media), ...]
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
        ttk.Label(left, text="Incrusta audio y vídeo en documentos PDF  ·  v3.0",
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
        # Campo editable: escribe el número y pulsa Enter o "Ir →" para saltar
        self._page_entry = ttk.Entry(pf, textvariable=self.page_var,
                                     width=5, justify="center")
        self._page_entry.pack(side="left", padx=2)
        self._page_entry.bind("<Return>", lambda e: self._on_page_changed())
        # FocusOut NO recarga — evita llamadas innecesarias a poppler al
        # hacer clic en otros campos de la interfaz.
        self._total_label = tk.Label(pf, text="/ —", bg=C["BG"], fg=C["DIM"],
                                     font=("Segoe UI", 10))
        self._total_label.pack(side="left")
        ttk.Button(pf, text="Ir →", width=5,
                   command=self._on_page_changed).pack(side="left", padx=(4, 0))
        ttk.Button(pf, text="▶", width=2,
                   command=self._next_page).pack(side="left", padx=(2, 0))

        self.media_var = tk.StringVar()
        self._file_row(left, "Archivo multimedia", self.media_var,
                       MEDIA_TYPES, save=False)

        self.pdf_out_var = tk.StringVar()
        self._file_row(left, "Archivo de salida", self.pdf_out_var,
                       [("PDF", "*.pdf")], save=True,
                       browse_cmd=self._browse_out)

        tk.Frame(left, height=1, bg=C["CARD"]).pack(fill="x", pady=(10, 6))

        # ── Modo ─────────────────────────────────────────────────────────
        self._section(left, "Modo de incrustación")

        self.mode_var = tk.StringVar(value="real")
        self.mode_var.trace_add("write", lambda *_: self._on_mode_changed())
        for val, title, desc in [
            ("real", "Modo A — PDF autosuficiente (Acrobat)",
             "Audio/vídeo incrustado dentro del PDF · clic → abre con reproductor del sistema"),
            ("link", "Modo B — Enlace URI",
             "Acrobat, SumatraPDF — requiere PDF + multimedia en la misma carpeta"),
            ("html", "Modo C — HTML autocontenido",
             "Un solo .html · funciona en cualquier navegador sin internet"),
            ("html_linked", "Modo D — HTML ligero + carpeta media",
             "HTML pequeño + archivos en carpeta · ideal para pizarras digitales y dispositivos con poca RAM"),
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

        # ── Panel Modo A: lista acumulada ─────────────────────────────────
        self._real_panel = ttk.Frame(left)
        self._real_panel.pack(fill="x")

        self._section(self._real_panel, "Multimedia añadido  (Modo A)")
        lf_a = ttk.Frame(self._real_panel)
        lf_a.pack(fill="x", pady=(2, 0))

        self._real_listbox = tk.Listbox(
            lf_a, height=4, bg=C["ENTRY"], fg=C["FG"],
            selectbackground=C["SEL"], font=("Courier New", 8),
            relief="flat", borderwidth=1, highlightthickness=0
        )
        self._real_listbox.pack(side="left", fill="x", expand=True)
        sb_a = ttk.Scrollbar(lf_a, orient="vertical",
                             command=self._real_listbox.yview)
        sb_a.pack(side="left", fill="y")
        self._real_listbox.config(yscrollcommand=sb_a.set)

        btn_row_a = ttk.Frame(self._real_panel)
        btn_row_a.pack(fill="x", pady=(4, 0))
        ttk.Button(btn_row_a, text="➕  Añadir a lista",
                   command=self._add_real_item).pack(side="left")
        ttk.Button(btn_row_a, text="🗑  Limpiar lista",
                   command=self._clear_real_items).pack(side="left", padx=(4, 0))
        ttk.Button(btn_row_a, text="✖  Eliminar seleccionado",
                   command=self._delete_real_item).pack(side="left", padx=(4, 0))

        ttk.Button(self._real_panel, text="⚡  Generar PDF",
                   style="Accent.TButton",
                   command=self._run).pack(fill="x", pady=(8, 2))

        # Ocultar panel hasta que se seleccione Modo A
        self._real_panel.pack_forget()

        # ── Panel Modo C: lista acumulada ─────────────────────────────────
        self._html_panel = ttk.Frame(left)
        self._html_panel.pack(fill="x")

        self._section(self._html_panel, "Multimedia añadido  (Modo C)")
        lf = ttk.Frame(self._html_panel)
        lf.pack(fill="x", pady=(2, 0))

        self._html_listbox = tk.Listbox(
            lf, height=4, bg=C["ENTRY"], fg=C["FG"],
            selectbackground=C["SEL"], font=("Courier New", 8),
            relief="flat", borderwidth=1, highlightthickness=0
        )
        self._html_listbox.pack(side="left", fill="x", expand=True)
        sb = ttk.Scrollbar(lf, orient="vertical",
                           command=self._html_listbox.yview)
        sb.pack(side="left", fill="y")
        self._html_listbox.config(yscrollcommand=sb.set)

        btn_row = ttk.Frame(self._html_panel)
        btn_row.pack(fill="x", pady=(4, 0))
        ttk.Button(btn_row, text="➕  Añadir a lista",
                   command=self._add_html_item).pack(side="left")
        ttk.Button(btn_row, text="🗑  Limpiar lista",
                   command=self._clear_html_items).pack(side="left", padx=(4, 0))
        ttk.Button(btn_row, text="✖  Eliminar seleccionado",
                   command=self._delete_html_item).pack(side="left", padx=(4, 0))

        ttk.Button(self._html_panel, text="⚡  Generar HTML",
                   style="Accent.TButton",
                   command=self._run).pack(fill="x", pady=(8, 2))

        # Ocultar panel hasta que se seleccione Modo C
        self._html_panel.pack_forget()


        # ── Panel Modo D: lista acumulada ─────────────────────────────────
        self._html_d_panel = ttk.Frame(left)
        self._html_d_panel.pack(fill="x")

        self._section(self._html_d_panel, "Multimedia añadido  (Modo D)")
        lf_d = ttk.Frame(self._html_d_panel)
        lf_d.pack(fill="x", pady=(2, 0))

        self._html_d_listbox = tk.Listbox(
            lf_d, height=4, bg=C["ENTRY"], fg=C["FG"],
            selectbackground=C["SEL"], font=("Courier New", 8),
            relief="flat", borderwidth=1, highlightthickness=0
        )
        self._html_d_listbox.pack(side="left", fill="x", expand=True)
        sb_d = ttk.Scrollbar(lf_d, orient="vertical",
                             command=self._html_d_listbox.yview)
        sb_d.pack(side="left", fill="y")
        self._html_d_listbox.config(yscrollcommand=sb_d.set)

        btn_row_d = ttk.Frame(self._html_d_panel)
        btn_row_d.pack(fill="x", pady=(4, 0))
        ttk.Button(btn_row_d, text="➕  Añadir a lista",
                   command=self._add_html_d_item).pack(side="left")
        ttk.Button(btn_row_d, text="🗑  Limpiar lista",
                   command=self._clear_html_d_items).pack(side="left", padx=(4, 0))
        ttk.Button(btn_row_d, text="✖  Eliminar seleccionado",
                   command=self._delete_html_d_item).pack(side="left", padx=(4, 0))

        ttk.Button(self._html_d_panel, text="⚡  Generar HTML ligero",
                   style="Accent.TButton",
                   command=self._run).pack(fill="x", pady=(8, 2))

        self._html_d_panel.pack_forget()

        tk.Frame(left, height=1, bg=C["CARD"]).pack(fill="x", pady=(10, 6))

        # ── Miniatura opcional ────────────────────────────────────────────
        self._section(left, "Miniatura personalizada  (solo Modos A y B, opcional)")
        self.thumb_var = tk.StringVar()
        self._file_row(left, "Imagen", self.thumb_var,
                       [("Imágenes", " ".join(IMAGE_EXT))], save=False)

        tk.Frame(left, height=1, bg=C["CARD"]).pack(fill="x", pady=(10, 8))

        # ── Botón Modo B + estado (para Modos A y C el botón está en su panel) ──
        bf = ttk.Frame(left)
        bf.pack(fill="x")
        self._run_btn = ttk.Button(bf, text="⚡  Incrustar ahora",
                   style="Accent.TButton",
                   command=self._run)
        self._run_btn.pack(side="right")

        self.status_var = tk.StringVar(value="Listo.")
        tk.Label(bf, textvariable=self.status_var,
                 bg=C["BG"], fg=C["DIM"],
                 font=("Segoe UI", 9, "italic")).pack(side="left")

        # ── Columna derecha: vista previa ─────────────────────────────────
        ttk.Label(right, text="Vista previa · arrastra para marcar zona",
                  style="Acc.TLabel").pack(anchor="w", pady=(0, 6))

        self.preview = PDFPreview(right)
        self.preview.pack(fill="both", expand=True)

        # Aplicar estado inicial del modo seleccionado
        self._on_mode_changed()

    # ── Sección helper ────────────────────────────────────────────────────

    def _section(self, parent, text):
        f = ttk.Frame(parent)
        f.pack(fill="x", pady=(6, 3))
        tk.Label(f, text=text.upper(), bg=C["BG"], fg=C["ACC"],
                 font=("Segoe UI", 8, "bold")).pack(side="left")

    def _file_row(self, parent, label, var, ftypes, save=False,
                  on_change=None, browse_cmd=None):
        row = ttk.Frame(parent)
        row.pack(fill="x", pady=3)
        ttk.Label(row, text=label, width=20, anchor="w").pack(side="left")
        e = ttk.Entry(row, textvariable=var, width=34)
        e.pack(side="left", padx=(0, 6))
        if on_change:
            var.trace_add("write", lambda *_: on_change())
        cmd = browse_cmd if browse_cmd else lambda: self._browse(var, ftypes, save, on_change)
        ttk.Button(row, text="…", command=cmd).pack(side="left")

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

    # ── Helpers Modo A ───────────────────────────────────────────────────

    def _add_real_item(self):
        """Valida campos y añade el ítem actual a la lista del Modo A."""
        pdf_in = self.pdf_in_var.get().strip()
        media  = self.media_var.get().strip()
        page   = self.page_var.get()
        rect   = self.preview.get_rect()

        errors = []
        if not pdf_in or not os.path.isfile(pdf_in):
            errors.append("Selecciona un PDF de entrada válido.")
        if not media or not os.path.isfile(media):
            errors.append("Selecciona un archivo multimedia válido.")
        if rect is None:
            errors.append("Marca la zona de inserción en la vista previa.")
        if errors:
            messagebox.showerror("Campos incompletos", "\n".join(errors))
            return

        self._real_items.append((page, rect, media))
        self._real_listbox.insert("end", f"Pág.{page+1}  {Path(media).name}")
        # Resetear zona marcada para la siguiente inserción
        self.preview._rect_pdf = None
        if self.preview._rect_id:
            self.preview.canvas.delete(self.preview._rect_id)
            self.preview._rect_id = None
        self.preview._label_coords.config(text="Arrastra para marcar la zona")
        self.status_var.set(f"Añadido: Pág.{page+1} — {Path(media).name}  ({len(self._real_items)} en lista)")

    def _clear_real_items(self):
        self._real_items.clear()
        self._real_listbox.delete(0, "end")
        self.status_var.set("Lista de Modo A vaciada.")

    def _delete_real_item(self):
        sel = self._real_listbox.curselection()
        if not sel:
            messagebox.showinfo("Sin selección", "Selecciona un ítem de la lista para eliminarlo.")
            return
        idx = sel[0]
        self._real_items.pop(idx)
        self._real_listbox.delete(idx)
        # Resetear zona marcada
        self.preview._rect_pdf = None
        if self.preview._rect_id:
            self.preview.canvas.delete(self.preview._rect_id)
            self.preview._rect_id = None
        self.preview._label_coords.config(text="Arrastra para marcar la zona")
        self.status_var.set(f"Ítem eliminado. Quedan {len(self._real_items)} en lista.")

    # ── Helpers Modo C ───────────────────────────────────────────────────

    def _add_html_item(self):
        """Valida campos y añade el ítem actual a la lista del Modo C."""
        pdf_in = self.pdf_in_var.get().strip()
        media  = self.media_var.get().strip()
        page   = self.page_var.get()
        rect   = self.preview.get_rect()

        errors = []
        if not pdf_in or not os.path.isfile(pdf_in):
            errors.append("Selecciona un PDF de entrada válido.")
        if not media or not os.path.isfile(media):
            errors.append("Selecciona un archivo multimedia válido.")
        if rect is None:
            errors.append("Marca la zona de inserción en la vista previa.")
        if errors:
            messagebox.showerror("Campos incompletos", "\n".join(errors))
            return

        self._html_items.append((page, rect, media))
        self._html_listbox.insert("end", f"Pág.{page+1}  {Path(media).name}")
        # Resetear zona marcada
        self.preview._rect_pdf = None
        if self.preview._rect_id:
            self.preview.canvas.delete(self.preview._rect_id)
            self.preview._rect_id = None
        self.preview._label_coords.config(text="Arrastra para marcar la zona")
        self.status_var.set(f"Añadido: Pág.{page+1} — {Path(media).name}  ({len(self._html_items)} en lista)")

    def _clear_html_items(self):
        self._html_items.clear()
        self._html_listbox.delete(0, "end")
        self.status_var.set("Lista de Modo C vaciada.")

    def _delete_html_item(self):
        sel = self._html_listbox.curselection()
        if not sel:
            messagebox.showinfo("Sin selección", "Selecciona un ítem de la lista para eliminarlo.")
            return
        idx = sel[0]
        self._html_items.pop(idx)
        self._html_listbox.delete(idx)
        # Resetear zona marcada
        self.preview._rect_pdf = None
        if self.preview._rect_id:
            self.preview.canvas.delete(self.preview._rect_id)
            self.preview._rect_id = None
        self.preview._label_coords.config(text="Arrastra para marcar la zona")
        self.status_var.set(f"Ítem eliminado. Quedan {len(self._html_items)} en lista.")


    # ── Helpers Modo D ───────────────────────────────────────────────────

    def _add_html_d_item(self):
        pdf_in = self.pdf_in_var.get().strip()
        media  = self.media_var.get().strip()
        page   = self.page_var.get()
        rect   = self.preview.get_rect()
        errors = []
        if not pdf_in or not os.path.isfile(pdf_in):
            errors.append("Selecciona un PDF de entrada válido.")
        if not media or not os.path.isfile(media):
            errors.append("Selecciona un archivo multimedia válido.")
        if rect is None:
            errors.append("Marca la zona de inserción en la vista previa.")
        if errors:
            messagebox.showerror("Campos incompletos", "\n".join(errors))
            return
        self._html_d_items.append((page, rect, media))
        self._html_d_listbox.insert("end", f"Pág.{page+1}  {Path(media).name}")
        self.preview._rect_pdf = None
        if self.preview._rect_id:
            self.preview.canvas.delete(self.preview._rect_id)
            self.preview._rect_id = None
        self.preview._label_coords.config(text="Arrastra para marcar la zona")
        self.status_var.set(f"Añadido: Pág.{page+1} — {Path(media).name}  ({len(self._html_d_items)} en lista)")

    def _clear_html_d_items(self):
        self._html_d_items.clear()
        self._html_d_listbox.delete(0, "end")
        self.status_var.set("Lista de Modo D vaciada.")

    def _delete_html_d_item(self):
        sel = self._html_d_listbox.curselection()
        if not sel:
            messagebox.showinfo("Sin selección", "Selecciona un ítem de la lista para eliminarlo.")
            return
        idx = sel[0]
        self._html_d_items.pop(idx)
        self._html_d_listbox.delete(idx)
        self.preview._rect_pdf = None
        if self.preview._rect_id:
            self.preview.canvas.delete(self.preview._rect_id)
            self.preview._rect_id = None
        self.preview._label_coords.config(text="Arrastra para marcar la zona")
        self.status_var.set(f"Ítem eliminado. Quedan {len(self._html_d_items)} en lista.")

    def _browse_out(self):
        """Diálogo de salida adaptado al modo seleccionado."""
        if self.mode_var.get() in ("html", "html_linked"):
            ftypes = [("HTML", "*.html"), ("Todos", "*.*")]
            ext    = ".html"
        else:
            ftypes = [("PDF", "*.pdf")]
            ext    = ".pdf"
        path = filedialog.asksaveasfilename(filetypes=ftypes,
                                            defaultextension=ext)
        if path:
            self.pdf_out_var.set(path)

    def _on_mode_changed(self):
        """Al cambiar de modo: muestra/oculta paneles de lista y ajusta extensión."""
        mode = self.mode_var.get()

        # Mostrar/ocultar paneles de lista acumulada y botón Modo B
        if mode == "real":
            self._real_panel.pack(fill="x")
            self._html_panel.pack_forget()
            self._html_d_panel.pack_forget()
            self._run_btn.pack_forget()
        elif mode == "html":
            self._html_panel.pack(fill="x")
            self._real_panel.pack_forget()
            self._html_d_panel.pack_forget()
            self._run_btn.pack_forget()
        elif mode == "html_linked":
            self._html_d_panel.pack(fill="x")
            self._real_panel.pack_forget()
            self._html_panel.pack_forget()
            self._run_btn.pack_forget()
        else:  # link — Modo B: botón simple visible, sin panel de lista
            self._real_panel.pack_forget()
            self._html_panel.pack_forget()
            self._html_d_panel.pack_forget()
            self._run_btn.pack(side="right")

        # Ajustar extensión del archivo de salida
        out = self.pdf_out_var.get().strip()
        if not out:
            return
        p = Path(out)
        if mode in ("html", "html_linked"):
            if p.suffix.lower() != ".html":
                self.pdf_out_var.set(str(p.with_suffix(".html")))
        else:
            if p.suffix.lower() == ".html":
                self.pdf_out_var.set(str(p.with_suffix(".pdf")))

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
        # Leer y sanear el valor del campo
        try:
            p = self.page_var.get()
        except Exception:
            p = 0
        if self._total_pages > 0:
            p = max(0, min(p, self._total_pages - 1))
        self.page_var.set(p)

        # Evitar recargar poppler si ya estamos en esa página
        if p == self._last_loaded_page:
            return

        path = self.pdf_in_var.get().strip()
        if os.path.isfile(path):
            self._last_loaded_page = p
            self._load_preview(path, p)

    def _on_pdf_selected(self):
        """Cuando se elige PDF: renderizar página y sugerir nombre de salida."""
        path = self.pdf_in_var.get().strip()
        if not os.path.isfile(path):
            return

        # Al cambiar el PDF de entrada, resetear todas las listas acumuladas
        self._html_items.clear()
        self._html_listbox.delete(0, "end")
        self._html_d_items.clear()
        self._html_d_listbox.delete(0, "end")
        self._real_items.clear()
        self._real_listbox.delete(0, "end")

        # Contar páginas totales
        try:
            from pypdf import PdfReader
            self._total_pages = len(PdfReader(path).pages)
            self._total_label.config(text=f"/ {self._total_pages}")
        except Exception:
            self._total_pages = 0
            self._total_label.config(text="/ —")

        self.page_var.set(0)
        self._last_loaded_page = -1

        # Sugerir nombre de salida
        if not self.pdf_out_var.get().strip():
            p    = Path(path)
            ext  = ".html" if self.mode_var.get() in ("html", "html_linked") else ".pdf"
            sugg = p.parent / (p.stem + "_con_multimedia" + ext)
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
        """
        Modo A y C: genera el archivo final a partir de la lista acumulada.
        Modo B: incrusta directamente el multimedia seleccionado (flujo simple).
        """
        pdf_in  = self.pdf_in_var.get().strip()
        pdf_out = self.pdf_out_var.get().strip()
        mode    = self.mode_var.get()
        thumb   = self.thumb_var.get().strip() or None

        # Validaciones comunes
        errors = []
        if not pdf_in or not os.path.isfile(pdf_in):
            errors.append("Selecciona un PDF de entrada válido.")
        if not pdf_out:
            errors.append("Indica dónde guardar el archivo de salida.")

        if mode == "real":
            if not self._real_items:
                errors.append(
                    "La lista del Modo A está vacía.\n"
                    "Usa el botón '➕ Añadir a lista' para ir añadiendo cada multimedia."
                )
        elif mode == "html":
            if not self._html_items:
                errors.append(
                    "La lista del Modo C está vacía.\n"
                    "Usa el botón '➕ Añadir a lista' para ir añadiendo cada multimedia."
                )
        elif mode == "html_linked":
            if not self._html_d_items:
                errors.append(
                    "La lista del Modo D está vacía.\n"
                    "Usa el botón '➕ Añadir a lista' para ir añadiendo cada multimedia."
                )
        else:  # link — flujo simple: necesita multimedia y zona marcada
            media = self.media_var.get().strip()
            rect  = self.preview.get_rect()
            page  = self.page_var.get()
            if not media or not os.path.isfile(media):
                errors.append("Selecciona un archivo multimedia.")
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
                embed_real(pdf_in, pdf_out, self._real_items, thumbnail_path=thumb)
                name = Path(pdf_out).name
                self.status_var.set(f"✓  Guardado: {name}")
                info = (f"PDF guardado:\n{pdf_out}\n\n"
                        f"✅  Modo A — {len(self._real_items)} elemento(s) incrustado(s)\n"
                        "El multimedia está DENTRO del PDF. No necesitas archivos externos.\n\n"
                        "Al hacer clic en Acrobat/Reader:\n"
                        "• Puede aparecer «¿Abrir este archivo?» → pulsa Abrir.\n"
                        "• Se abre con el reproductor predeterminado del sistema.")
                messagebox.showinfo("¡Listo!", info)

            elif mode == "html":
                embed_html(pdf_in, pdf_out, self._html_items)
                name = Path(pdf_out).name
                self.status_var.set(f"✓  Guardado: {name}")
                info = (f"HTML guardado:\n{pdf_out}\n\n"
                        f"✅  Modo C — {len(self._html_items)} elemento(s) embebido(s)\n"
                        "Un único archivo con todo embebido.\n"
                        "Ábrelo con cualquier navegador (Chrome, Edge, Firefox…)\n"
                        "sin internet, sin plugins, sin instalaciones.")
                messagebox.showinfo("¡Listo!", info)

            elif mode == "html_linked":
                embed_html_linked(pdf_in, pdf_out, self._html_d_items)
                media_folder = Path(pdf_out).stem + "_media"
                name = Path(pdf_out).name
                self.status_var.set(f"✓  Guardado: {name}")
                info = (f"HTML guardado:\n{pdf_out}\n\n"
                        f"✅  Modo D — {len(self._html_d_items)} elemento(s) enlazado(s)\n"
                        f"Los multimedia están en la carpeta: {media_folder}\n\n"
                        "⚠ Mueve SIEMPRE el HTML y la carpeta juntos.\n"
                        "Funciona en cualquier navegador, incluso en pizarras digitales.")
                messagebox.showinfo("¡Listo!", info)

            else:  # link
                embed_link(pdf_in, media, pdf_out,
                           page_num=page, rect=rect, thumbnail_path=thumb)
                name = Path(pdf_out).name
                self.status_var.set(f"✓  Guardado: {name}")
                # Encadenar para poder añadir más multimedia al mismo PDF
                self.pdf_in_var.set(pdf_out)
                self._last_loaded_page = -1
                try:
                    from pypdf import PdfReader
                    self._total_pages = len(PdfReader(pdf_out).pages)
                    self._total_label.config(text=f"/ {self._total_pages}")
                except Exception:
                    pass
                info = (f"PDF guardado:\n{pdf_out}\n\n"
                        "✅  Modo B (Launch relativo)\n"
                        "El multimedia se ha copiado junto al PDF.\n"
                        "Funciona en Acrobat y SumatraPDF.\n"
                        "⚠ PDF y multimedia deben permanecer en la misma carpeta.\n"
                        "⚠ Chrome/Edge bloquean este tipo de enlace por seguridad.")
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
