# -*- coding: utf-8 -*-
import os
import re
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from PIL import Image, ImageTk
from pypdf import PdfReader, PdfWriter
import fitz  # PyMuPDF


# ─────────────────────────────────────────────────────────────────────────────
#  LÓGICA PRINCIPAL
# ─────────────────────────────────────────────────────────────────────────────

ruta_pdf    = ""
total_pags  = 0
rot_map     = {}   # {idx_base0: grados}

def seleccionar_pdf():
    global ruta_pdf, total_pags, rot_map
    f = filedialog.askopenfilename(
        title="Selecciona el PDF a separar",
        filetypes=[("PDF", "*.pdf")])
    if not f:
        return
    ruta_pdf   = f
    rot_map    = {}
    total_pags = len(PdfReader(f).pages)
    lbl_archivo.config(
        text=f"📄  {os.path.basename(f)}",
        fg="#2c3e50", font=("Arial", 10, "bold"))
    lbl_total.config(text=f"Total: {total_pags} páginas", fg="#2980b9")
    ent_cortes.delete(0, tk.END)
    btn_ejecutar.config(state="normal", bg="#28B463")


def ejecutar():
    if not ruta_pdf:
        messagebox.showwarning("Aviso", "Selecciona primero un PDF.")
        return
    cortes_txt = ent_cortes.get().strip()
    if not cortes_txt:
        messagebox.showwarning("Aviso", "Indica los cortes.")
        return

    dest = filedialog.askdirectory(title="Carpeta de destino")
    if not dest:
        return

    try:
        reader = PdfReader(ruta_pdf)
        base   = os.path.splitext(os.path.basename(ruta_pdf))[0]
        cortes = cortes_txt.replace(" ", "").split(",")

        progreso["maximum"] = len(cortes)
        progreso["value"]   = 0
        ventana.update_idletasks()

        modo_nombre = var_nombre.get()   # 1=original+n, 2=texto pág1, 3=personalizado

        for i, c in enumerate(cortes):
            writer = PdfWriter()
            if "-" in c:
                ini, fin = map(int, c.split("-"))
                pags = list(range(ini - 1, fin))
            else:
                pags = [int(c) - 1]

            for p in pags:
                page = reader.pages[p]
                rot  = rot_map.get(p, 0)
                if rot:
                    page.rotate(rot)
                writer.add_page(page)

            # ── Nombre del archivo resultante ────────────────────────────────
            if modo_nombre == 1:
                # Nombre original + número correlativo
                name = f"{base}-{i+1}"

            elif modo_nombre == 2:
                # Detectar texto clave en la primera página del corte
                campo = ent_campo.get().strip()
                if campo:
                    texto_pag = reader.pages[pags[0]].extract_text() or ""
                    patron    = re.escape(campo) + r"[:\s]*([^\n\r]{1,80})"
                    match     = re.search(patron, texto_pag, re.IGNORECASE)
                    name      = (match.group(1).strip().replace(",", "")
                                 if match else f"{base}-{i+1}")
                else:
                    name = f"{base}-{i+1}"

            elif modo_nombre == 3:
                # Prefijo personalizado + número
                prefijo = ent_prefijo.get().strip() or base
                name    = f"{prefijo}-{i+1}"

            name = re.sub(r'[\\/*?:"<>|]', "", name).strip()
            if not name:
                name = f"{base}-{i+1}"

            with open(os.path.join(dest, f"{name}.pdf"), "wb") as f_out:
                writer.write(f_out)

            progreso["value"] = i + 1
            ventana.update_idletasks()

        messagebox.showinfo("Éxito",
                            f"PDF dividido en {len(cortes)} parte(s).\n"
                            f"Guardado en:\n{dest}")
        ent_cortes.delete(0, tk.END)
        progreso["value"] = 0

        if chk_abrir_var.get():
            os.startfile(dest)

    except Exception as e:
        messagebox.showerror("Error", str(e))


# ─────────────────────────────────────────────────────────────────────────────
#  VISOR DE PÁGINAS (solo previsualización, sin grupos)
# ─────────────────────────────────────────────────────────────────────────────

def abrir_visor():
    if not ruta_pdf:
        messagebox.showwarning("Aviso", "Selecciona primero un PDF.")
        return

    THUMB_W, THUMB_H = 90, 126
    CELL_W,  CELL_H  = 110, 160
    COLS = 6

    doc = fitz.open(ruta_pdf)
    n   = len(doc)

    sw = ventana.winfo_screenwidth()
    sh = ventana.winfo_screenheight()
    tw = min(940, sw - 80)
    th = min(sh - 60, 760)

    top = tk.Toplevel(ventana)
    top.title(f"Vista previa — {os.path.basename(ruta_pdf)}  ({n} pág.)")
    top.geometry(f"{tw}x{th}+{(sw-tw)//2}+{(sh-th)//2}")
    top.configure(bg="white")
    top.grab_set()

    # ── Barra superior ───────────────────────────────────────────────────────
    bar = tk.Frame(top, bg="#2c3e50", pady=5)
    bar.pack(fill="x")
    tk.Label(bar,
             text="Clic en miniatura para ampliar · Las rotaciones se aplican al separar",
             bg="#2c3e50", fg="#ecf0f1",
             font=("Arial", 9)).pack(side="left", padx=8)

    # Controles de rotación
    lbl_rot_info = tk.Label(bar, text="Selecciona y rota:",
                            bg="#2c3e50", fg="#bdc3c7", font=("Arial", 9))
    lbl_rot_info.pack(side="left", padx=(16, 2))
    tk.Button(bar, text="↺ 90° izq.",
              command=lambda: _rotar_sel(-90),
              bg="#8e44ad", fg="white", font=("Arial", 9),
              cursor="hand2").pack(side="left", padx=2)
    tk.Button(bar, text="↻ 90° der.",
              command=lambda: _rotar_sel(90),
              bg="#8e44ad", fg="white", font=("Arial", 9),
              cursor="hand2").pack(side="left", padx=2)

    lbl_sel_cnt = tk.Label(bar, text="0 sel.", bg="#2c3e50",
                           fg="#ecf0f1", font=("Arial", 9))
    lbl_sel_cnt.pack(side="left", padx=8)

    tk.Button(bar, text="✖ Cerrar",
              command=lambda: _cerrar(),
              bg="#7f8c8d", fg="white", font=("Arial", 9),
              cursor="hand2").pack(side="right", padx=8)

    # ── Canvas scrollable ────────────────────────────────────────────────────
    fc = tk.Frame(top, bg="#f0f2f5")
    fc.pack(fill="both", expand=True, padx=4, pady=4)

    canvas = tk.Canvas(fc, bg="#f0f2f5", highlightthickness=0)
    vsb    = tk.Scrollbar(fc, orient="vertical", command=canvas.yview)
    canvas.configure(yscrollcommand=vsb.set)
    vsb.pack(side="right", fill="y")
    canvas.pack(side="left", fill="both", expand=True)

    inner = tk.Frame(canvas, bg="#f0f2f5")
    canvas.create_window((0, 0), window=inner, anchor="nw")

    thumb_refs = []
    seleccion  = set()   # índices seleccionados para rotar

    def _render_all():
        nonlocal thumb_refs
        thumb_refs = []
        for w in inner.winfo_children():
            w.destroy()

        for idx in range(n):
            page = doc[idx]
            zoom = min(THUMB_W / page.rect.width,
                       THUMB_H / page.rect.height)
            pix  = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), alpha=False)
            img  = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)

            rot = rot_map.get(idx, 0)
            if rot:
                img = img.rotate(-rot, expand=True)
                img.thumbnail((THUMB_W, THUMB_H), Image.LANCZOS)

            photo = ImageTk.PhotoImage(img)
            thumb_refs.append(photo)

            en_sel = idx in seleccion
            bg_c   = "#d5e8fd" if en_sel else "white"
            brd_c  = "#2980b9" if en_sel else "#bdc3c7"

            row, col = divmod(idx, COLS)
            cell = tk.Frame(inner, bg=bg_c, bd=2, relief="solid",
                            highlightthickness=2,
                            highlightbackground=brd_c,
                            width=CELL_W, height=CELL_H)
            cell.grid(row=row, column=col, padx=3, pady=3)
            cell.grid_propagate(False)

            lbl_img = tk.Label(cell, image=photo, bg=bg_c, cursor="hand2")
            lbl_img.pack(pady=(4, 1))

            txt = f"{'✓ ' if en_sel else ''}Pág. {idx+1}"
            if rot:
                txt += f"  [{rot}°]"
            tk.Label(cell, text=txt, bg=bg_c, font=("Arial", 8),
                     fg="#1a5276" if en_sel else "#666").pack()

            for w in (lbl_img, cell):
                w.bind("<Button-1>", lambda e, i=idx: _toggle(i))
                w.bind("<Double-Button-1>", lambda e, i=idx: _ampliar(i))

        inner.update_idletasks()
        canvas.configure(scrollregion=canvas.bbox("all"))

    def _toggle(idx):
        if idx in seleccion:
            seleccion.discard(idx)
        else:
            seleccion.add(idx)
        lbl_sel_cnt.config(text=f"{len(seleccion)} sel.")
        _render_all()

    def _rotar_sel(grados):
        for idx in seleccion:
            rot_map[idx] = (rot_map.get(idx, 0) + grados) % 360
        _render_all()

    def _ampliar(idx):
        amp   = tk.Toplevel(top)
        amp.title(f"Pág. {idx+1}")
        page  = doc[idx]
        max_w = int(sw * 0.75)
        max_h = int(sh * 0.85)
        zoom  = min(2.0, max_w / page.rect.width, max_h / page.rect.height)
        pix   = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), alpha=False)
        img   = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
        rot   = rot_map.get(idx, 0)
        if rot:
            img = img.rotate(-rot, expand=True)
        ph    = ImageTk.PhotoImage(img)
        win_w = min(img.width + 20,  max_w)
        win_h = min(img.height + 40, max_h)
        amp.geometry(f"{win_w}x{win_h}")
        c2    = tk.Canvas(amp, bg="#555")
        sb_v  = tk.Scrollbar(amp, orient="vertical",   command=c2.yview)
        sb_h  = tk.Scrollbar(amp, orient="horizontal", command=c2.xview)
        c2.configure(yscrollcommand=sb_v.set, xscrollcommand=sb_h.set)
        sb_v.pack(side="right",  fill="y")
        sb_h.pack(side="bottom", fill="x")
        c2.pack(fill="both", expand=True)
        c2.create_image(0, 0, anchor="nw", image=ph)
        c2.configure(scrollregion=c2.bbox("all"))
        c2.image = ph

    def _cerrar():
        doc.close()
        top.destroy()

    canvas.bind("<MouseWheel>",
                lambda e: canvas.yview_scroll(-1 * (e.delta // 120), "units"))
    inner.bind("<Configure>",
               lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
    top.protocol("WM_DELETE_WINDOW", _cerrar)

    _render_all()


# ─────────────────────────────────────────────────────────────────────────────
#  INTERFAZ
# ─────────────────────────────────────────────────────────────────────────────

ventana = tk.Tk()
ventana.title("Separador de Cerificados Académicos")

AW, AH = 560, 580
ventana.geometry(
    f"{AW}x{AH}+{(ventana.winfo_screenwidth()//2)-(AW//2)}+40")
ventana.configure(bg="white")
ventana.resizable(False, False)

try:
    ico = tk.PhotoImage(file="pdf-icono.png")
    ventana.iconphoto(False, ico)
except Exception:
    pass

pad = dict(padx=16, pady=0)

# ── Encabezado ────────────────────────────────────────────────────────────────
tk.Label(ventana, text="📂  Separador de Certificados Académicos",
         font=("Arial", 14, "bold"), bg="white",
         fg="#2c3e50").pack(anchor="w", padx=16, pady=(5, 6))
tk.Frame(ventana, bg="#ecf0f1", height=2).pack(fill="x", padx=16)

# ── Selección de archivo ──────────────────────────────────────────────────────
f_btn = tk.Frame(ventana, bg="white")
f_btn.pack(fill="x", padx=16, pady=(10, 2))
tk.Button(f_btn, text="📂 Seleccionar PDF",
          command=seleccionar_pdf,
          bg="#3498db", fg="white",
          font=("Arial", 10), cursor="hand2").pack(side="left", fill="x", expand=True)
tk.Button(f_btn, text="👁️ Vista previa páginas",
          command=abrir_visor,
          bg="#8e44ad", fg="white",
          font=("Arial", 10), cursor="hand2").pack(side="left", padx=(6, 0))

lbl_archivo = tk.Label(ventana, text="Ningún archivo seleccionado",
                       bg="white", fg="gray", font=("Arial", 9))
lbl_archivo.pack(anchor="w", padx=16)
lbl_total = tk.Label(ventana, text="", bg="white", fg="#2980b9",
                     font=("Arial", 9, "bold"))
lbl_total.pack(anchor="w", padx=16)

tk.Frame(ventana, bg="#ecf0f1", height=2).pack(fill="x", padx=16, pady=8)

# ── Cortes ────────────────────────────────────────────────────────────────────
tk.Label(ventana, text="Cortes  (ej: 1-3, 4-6, 7)",
         bg="white", font=("Arial", 10, "bold"), fg="#2c3e50").pack(anchor="w", padx=16)
tk.Label(ventana,
         text="Cada bloque separado por coma se convierte en un PDF independiente.",
         bg="white", fg="gray", font=("Arial", 8)).pack(anchor="w", padx=16)

ent_cortes = tk.Entry(ventana, font=("Consolas", 12))
ent_cortes.pack(fill="x", padx=16, pady=(4, 0))

tk.Frame(ventana, bg="#ecf0f1", height=2).pack(fill="x", padx=16, pady=8)

# ── Nombre de los archivos resultantes ───────────────────────────────────────
tk.Label(ventana, text="Nombre de los archivos resultantes:",
         bg="white", font=("Arial", 10, "bold"), fg="#2c3e50").pack(anchor="w", padx=16)

var_nombre = tk.IntVar(value=1)

# Opción 1 — nombre original + nº
tk.Radiobutton(ventana,
               text="Nombre original + número  (ej: documento-1.pdf, documento-2.pdf)",
               variable=var_nombre, value=1,
               bg="white", font=("Arial", 9),
               command=lambda: _toggle_nombre_opts()).pack(anchor="w", padx=20)

# Opción 2 — detectar texto en la página
f_op2 = tk.Frame(ventana, bg="white")
f_op2.pack(anchor="w", padx=20, fill="x")
tk.Radiobutton(f_op2,
               text="Detectar texto en la 1ª página del bloque — campo a buscar:",
               variable=var_nombre, value=2,
               bg="white", font=("Arial", 9),
               command=lambda: _toggle_nombre_opts()).pack(side="left")
ent_campo = tk.Entry(f_op2, font=("Arial", 9), width=22)
ent_campo.insert(0, "Apellidos y nombre")
ent_campo.pack(side="left", padx=(4, 0))

# Opción 3 — prefijo personalizado
f_op3 = tk.Frame(ventana, bg="white")
f_op3.pack(anchor="w", padx=20, fill="x")
tk.Radiobutton(f_op3,
               text="Prefijo personalizado + número:",
               variable=var_nombre, value=3,
               bg="white", font=("Arial", 9),
               command=lambda: _toggle_nombre_opts()).pack(side="left")
ent_prefijo = tk.Entry(f_op3, font=("Arial", 9), width=22)
ent_prefijo.pack(side="left", padx=(4, 0))


def _toggle_nombre_opts():
    """Activa/desactiva los campos de texto según la opción elegida."""
    v = var_nombre.get()
    ent_campo.config(state="normal" if v == 2 else "disabled")
    ent_prefijo.config(state="normal" if v == 3 else "disabled")

_toggle_nombre_opts()   # estado inicial

tk.Frame(ventana, bg="#ecf0f1", height=2).pack(fill="x", padx=16, pady=8)

# ── Opciones finales ──────────────────────────────────────────────────────────
chk_abrir_var = tk.BooleanVar(value=True)
tk.Checkbutton(ventana, text="📂  Abrir carpeta de destino al finalizar",
               variable=chk_abrir_var,
               bg="white", font=("Arial", 9)).pack(anchor="w", padx=16)

progreso = ttk.Progressbar(ventana, mode="determinate")
progreso.pack(fill="x", padx=16, pady=(8, 4))

btn_ejecutar = tk.Button(ventana,
                         text="✂️  SEPARAR PDF",
                         command=ejecutar,
                         bg="#95a5a6", fg="white",
                         font=("Arial", 12, "bold"),
                         height=2, cursor="hand2",
                         state="disabled")
btn_ejecutar.pack(fill="x", padx=16, pady=(4, 14))

ventana.mainloop()
