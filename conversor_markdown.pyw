# -*- coding: utf-8 -*-
"""
markitdown.pyw  –  Convierte archivos y URLs a Markdown
Parte del TOOLBOX · RCM
"""

import tkinter as tk
from tkinter import filedialog, messagebox
import threading
import os
import sys

# ── Instalación automática de markitdown si falta ──────────────────────────
def _asegurar_markitdown():
    try:
        import markitdown  # noqa
        return True
    except ImportError:
        import subprocess
        r = subprocess.run(
            [sys.executable, "-m", "pip", "install", "markitdown", "-q"],
            capture_output=True
        )
        return r.returncode == 0

# ── Paleta idéntica al menú principal ──────────────────────────────────────
BG_ROOT     = "#0d0d0d"
BG_PANEL    = "#141414"
BG_CARD     = "#1c1c1c"
BG_CARD_HOV = "#272727"
BG_SEARCH   = "#1e1e1e"
FG_MAIN     = "#e8e8e8"
FG_MUTED    = "#666666"
FG_DIM      = "#666666"
ACENTO      = "#4dd0e1"
ACENTO_OK   = "#4caf50"
ACENTO_ERR  = "#ef5350"
ACENTO_WARN = "#ff8c00"

FONT_TITLE  = ("Segoe UI Black", 14, "bold")
FONT_LABEL  = ("Segoe UI", 9)
FONT_BOLD   = ("Segoe UI", 9, "bold")
FONT_MONO   = ("Consolas", 9)
FONT_BTN    = ("Segoe UI", 9, "bold")

EXTENSIONES_ADMITIDAS = (
    ("Todos los admitidos",
     "*.pdf *.docx *.pptx *.xlsx *.xls *.csv *.html *.htm "
     "*.xml *.json *.zip *.epub *.mp3 *.wav *.jpg *.jpeg *.png *.webp"),
    ("PDF",           "*.pdf"),
    ("Word",          "*.docx"),
    ("PowerPoint",    "*.pptx"),
    ("Excel / CSV",   "*.xlsx *.xls *.csv"),
    ("Web",           "*.html *.htm"),
    ("Imagen",        "*.jpg *.jpeg *.png *.webp"),
    ("Audio",         "*.mp3 *.wav"),
    ("Todos",         "*.*"),
)


class MarkItDownApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("MarkItDown · TOOLBOX")
        self.root.configure(bg=BG_ROOT)
        self.root.resizable(True, True)

        ancho, alto = 760, 700
        sw = self.root.winfo_screenwidth()
        px = (sw - ancho) // 2
        self.root.geometry(f"{ancho}x{alto}+{px}+5")
        self.root.minsize(580, 500)

        self._archivos   = []
        self._ultimo_dir = os.path.expanduser("~")
        self._en_proceso = False

        self._construir_ui()

    # ── UI ────────────────────────────────────────────────────────────────
    def _construir_ui(self):
        hdr = tk.Frame(self.root, bg=BG_ROOT)
        hdr.pack(fill="x", padx=20, pady=(14, 4))
        tk.Label(hdr, text="MarkItDown", fg=FG_MAIN, bg=BG_ROOT,
                 font=FONT_TITLE).pack(side="left")
        tk.Label(hdr, text=" · convierte archivos y URLs a Markdown",
                 fg=FG_MUTED, bg=BG_ROOT,
                 font=("Segoe UI", 10)).pack(side="left", pady=(3, 0))

        zona = tk.Frame(self.root, bg=BG_PANEL)
        zona.pack(fill="x", padx=20, pady=(6, 0))

        # — Archivos —
        sec_arch = tk.Frame(zona, bg=BG_PANEL)
        sec_arch.pack(fill="x", padx=12, pady=(10, 4))
        tk.Label(sec_arch, text="ARCHIVOS", fg=FG_MUTED, bg=BG_PANEL,
                 font=FONT_BOLD).pack(side="left")
        self.lbl_num = tk.Label(sec_arch, text="ninguno seleccionado",
                                fg=FG_DIM, bg=BG_PANEL, font=FONT_MONO)
        self.lbl_num.pack(side="left", padx=10)

        fila_btns = tk.Frame(zona, bg=BG_PANEL)
        fila_btns.pack(fill="x", padx=12, pady=(0, 6))
        self._btn(fila_btns, "＋ Añadir archivos", ACENTO,
                  self._seleccionar_archivos).pack(side="left", padx=(0, 6))
        self._btn(fila_btns, "✕ Limpiar lista", "#555",
                  self._limpiar_lista).pack(side="left")

        frame_lista = tk.Frame(zona, bg=BG_PANEL)
        frame_lista.pack(fill="x", padx=12, pady=(0, 4))
        self.lb_archivos = tk.Listbox(
            frame_lista, bg=BG_CARD, fg=FG_MAIN,
            selectbackground=ACENTO, selectforeground=BG_ROOT,
            font=FONT_MONO, height=4, borderwidth=0,
            highlightthickness=0, activestyle="none"
        )
        sb_lista = tk.Scrollbar(frame_lista, orient="vertical",
                                command=self.lb_archivos.yview)
        self.lb_archivos.config(yscrollcommand=sb_lista.set)
        self.lb_archivos.pack(side="left", fill="x", expand=True)
        sb_lista.pack(side="right", fill="y")

        self._btn(zona, "✕ Quitar seleccionado", "#333",
                  self._quitar_seleccionado).pack(anchor="e", padx=12, pady=(2, 8))

        tk.Frame(zona, bg="#2a2a2a", height=1).pack(fill="x", padx=12, pady=4)

        # — URL —
        sec_url = tk.Frame(zona, bg=BG_PANEL)
        sec_url.pack(fill="x", padx=12, pady=(6, 4))
        tk.Label(sec_url, text="URL", fg=FG_MUTED, bg=BG_PANEL,
                 font=FONT_BOLD).pack(side="left")
        tk.Label(sec_url, text="  (página web o enlace directo a archivo)",
                 fg=FG_DIM, bg=BG_PANEL, font=FONT_LABEL).pack(side="left")

        url_frame = tk.Frame(zona, bg=BG_PANEL)
        url_frame.pack(fill="x", padx=12, pady=(0, 10))
        self.entry_url = tk.Entry(
            url_frame, bg=BG_SEARCH, fg=FG_MUTED,
            insertbackground="white", borderwidth=0,
            font=FONT_MONO, relief="flat"
        )
        self.entry_url.pack(side="left", fill="x", expand=True, ipady=6, padx=(0, 8))
        self.entry_url.insert(0, "https://")
        self.entry_url.bind("<FocusIn>",  self._url_focus_in)
        self._btn(url_frame, "Convertir URL", ACENTO,
                  self._convertir_url).pack(side="right")

        # — Carpeta de salida —
        sec_out = tk.Frame(zona, bg=BG_PANEL)
        sec_out.pack(fill="x", padx=12, pady=(0, 4))
        tk.Label(sec_out, text="GUARDAR EN", fg=FG_MUTED, bg=BG_PANEL,
                 font=FONT_BOLD).pack(side="left")
        tk.Label(sec_out, text="  (vacío = misma carpeta que el archivo origen)",
                 fg=FG_DIM, bg=BG_PANEL, font=FONT_LABEL).pack(side="left")

        salida_frame = tk.Frame(zona, bg=BG_PANEL)
        salida_frame.pack(fill="x", padx=12, pady=(4, 10))
        self.entry_salida = tk.Entry(
            salida_frame, bg=BG_SEARCH, fg=FG_MAIN,
            insertbackground="white", borderwidth=0,
            font=FONT_MONO, relief="flat"
        )
        self.entry_salida.pack(side="left", fill="x", expand=True, ipady=6, padx=(0, 8))
        self._btn(salida_frame, "Elegir…", "#444",
                  self._elegir_carpeta_salida).pack(side="right")

        # ── Botón principal ──
        tk.Frame(self.root, bg="#1a1a1a", height=1).pack(fill="x", padx=20, pady=(8, 0))

        accion = tk.Frame(self.root, bg=BG_ROOT)
        accion.pack(fill="x", padx=20, pady=10)

        self.btn_convertir = tk.Button(
            accion, text="▶  CONVERTIR ARCHIVOS",
            font=("Segoe UI Black", 11),
            bg=ACENTO, fg=BG_ROOT,
            relief="flat", padx=20, pady=10,
            activebackground="#80deea", activeforeground=BG_ROOT,
            cursor="hand2", command=self._convertir_archivos
        )
        self.btn_convertir.pack(side="left")
        self.btn_convertir.bind("<Enter>", lambda e: self.btn_convertir.config(bg="#80deea"))
        self.btn_convertir.bind("<Leave>", lambda e: self.btn_convertir.config(bg=ACENTO))

        self.canvas_prog = tk.Canvas(accion, bg=BG_PANEL,
                                     height=6, highlightthickness=0, bd=0)
        self.canvas_prog.pack(side="left", fill="x", expand=True, padx=(14, 0))

        # ── Log ──
        log_hdr = tk.Frame(self.root, bg=BG_ROOT)
        log_hdr.pack(fill="x", padx=20, pady=(4, 2))
        tk.Label(log_hdr, text="RESULTADO", fg=FG_MUTED, bg=BG_ROOT,
                 font=FONT_BOLD).pack(side="left")
        self._btn(log_hdr, "Limpiar log", "#333",
                  self._limpiar_log).pack(side="right")

        log_frame = tk.Frame(self.root, bg=BG_ROOT)
        log_frame.pack(fill="both", expand=True, padx=20, pady=(0, 14))
        self.txt_log = tk.Text(
            log_frame, bg=BG_CARD, fg=FG_MAIN,
            insertbackground="white", font=FONT_MONO,
            borderwidth=0, highlightthickness=0,
            state="disabled", wrap="word"
        )
        sb_log = tk.Scrollbar(log_frame, orient="vertical",
                              command=self.txt_log.yview)
        self.txt_log.config(yscrollcommand=sb_log.set)
        self.txt_log.pack(side="left", fill="both", expand=True)
        sb_log.pack(side="right", fill="y")

        self.txt_log.tag_config("ok",   foreground=ACENTO_OK)
        self.txt_log.tag_config("err",  foreground=ACENTO_ERR)
        self.txt_log.tag_config("info", foreground=ACENTO)
        self.txt_log.tag_config("warn", foreground=ACENTO_WARN)
        self.txt_log.tag_config("dim",  foreground=FG_MUTED)

        self._log("info", "Listo. Añade archivos o pega una URL y pulsa Convertir.\n")
        self._log("dim",  "Formatos: PDF · DOCX · PPTX · XLSX · CSV · HTML · imágenes · audio\n")

    # ── helpers ───────────────────────────────────────────────────────────
    def _btn(self, parent, texto, color, cmd):
        b = tk.Button(parent, text=texto, font=FONT_BTN,
                      bg=BG_CARD, fg=color, relief="flat", padx=8, pady=4,
                      activebackground=BG_CARD_HOV, activeforeground="white",
                      cursor="hand2", command=cmd)
        b.bind("<Enter>", lambda e, w=b: w.config(bg=BG_CARD_HOV))
        b.bind("<Leave>", lambda e, w=b: w.config(bg=BG_CARD))
        return b

    def _log(self, tag, texto):
        """Seguro desde cualquier hilo."""
        def _do():
            self.txt_log.config(state="normal")
            self.txt_log.insert("end", texto, tag)
            self.txt_log.see("end")
            self.txt_log.config(state="disabled")
        self.root.after(0, _do)

    def _limpiar_log(self):
        self.txt_log.config(state="normal")
        self.txt_log.delete("1.0", "end")
        self.txt_log.config(state="disabled")

    def _set_progreso(self, pct):
        def _do():
            self.canvas_prog.update_idletasks()
            w = self.canvas_prog.winfo_width()
            h = self.canvas_prog.winfo_height()
            self.canvas_prog.delete("all")
            self.canvas_prog.create_rectangle(0, 0, w, h, fill=BG_CARD, outline="")
            if pct > 0:
                self.canvas_prog.create_rectangle(
                    0, 0, max(4, int(w * pct)), h, fill=ACENTO, outline="")
        self.root.after(0, _do)

    # ── archivos ──────────────────────────────────────────────────────────
    def _seleccionar_archivos(self):
        rutas = filedialog.askopenfilenames(
            title="Seleccionar archivos",
            initialdir=self._ultimo_dir,
            filetypes=EXTENSIONES_ADMITIDAS
        )
        for r in rutas:
            if r not in self._archivos:
                self._archivos.append(r)
                self.lb_archivos.insert("end", os.path.basename(r))
        if rutas:
            self._ultimo_dir = os.path.dirname(rutas[0])
        self._actualizar_contador()

    def _quitar_seleccionado(self):
        sel = self.lb_archivos.curselection()
        if not sel:
            return
        idx = sel[0]
        self.lb_archivos.delete(idx)
        del self._archivos[idx]
        self._actualizar_contador()

    def _limpiar_lista(self):
        self._archivos = []
        self.lb_archivos.delete(0, "end")
        self._actualizar_contador()

    def _actualizar_contador(self):
        n = len(self._archivos)
        self.lbl_num.config(
            text=f"{n} archivo{'s' if n!=1 else ''} seleccionado{'s' if n!=1 else ''}" if n else "ninguno seleccionado",
            fg=ACENTO if n else FG_DIM
        )

    def _elegir_carpeta_salida(self):
        d = filedialog.askdirectory(title="Carpeta de destino",
                                    initialdir=self._ultimo_dir)
        if d:
            self.entry_salida.delete(0, "end")
            self.entry_salida.insert(0, d)

    # ── URL ───────────────────────────────────────────────────────────────
    def _url_focus_in(self, _):
        if self.entry_url.get() == "https://":
            self.entry_url.delete(0, "end")
            self.entry_url.config(fg=FG_MAIN)

    def _convertir_url(self):
        url = self.entry_url.get().strip()
        if not url or url == "https://":
            messagebox.showwarning("URL vacía", "Introduce una URL válida.")
            return
        if self._en_proceso:
            return
        carpeta = self.entry_salida.get().strip() or os.path.expanduser("~")
        threading.Thread(target=self._tarea_url, args=(url, carpeta), daemon=True).start()

    def _tarea_url(self, url, carpeta):
        self._en_proceso = True
        self._log("info", f"\n▶ Procesando URL: {url}\n")
        self._set_progreso(0.3)
        try:
            from markitdown import MarkItDown
            md = MarkItDown()
            resultado = md.convert(url)
            texto = resultado.text_content or ""

            from urllib.parse import urlparse
            parsed = urlparse(url)
            nombre_base = (parsed.netloc + parsed.path).replace("/", "_")
            nombre_base = "".join(c for c in nombre_base if c.isalnum() or c in "-_.")
            nombre_base = nombre_base[:80] or "pagina_web"
            dest = os.path.join(carpeta, nombre_base + ".md")

            with open(dest, "w", encoding="utf-8") as f:
                f.write(texto)

            self._set_progreso(1.0)
            self._log("ok", f"  ✓  Guardado en: {dest}\n")
            self.root.after(800, lambda: self._set_progreso(0.0))
        except Exception as e:
            self._set_progreso(0.0)
            self._log("err", f"  ✗  {type(e).__name__}: {e}\n")
        finally:
            self._en_proceso = False

    # ── conversión de archivos ────────────────────────────────────────────
    def _convertir_archivos(self):
        if self._en_proceso:
            return
        if not self._archivos:
            messagebox.showwarning("Sin archivos", "Añade al menos un archivo a la lista.")
            return
        carpeta_forzada = self.entry_salida.get().strip() or None
        self._en_proceso = True
        self.root.after(0, lambda: self.btn_convertir.config(
            state="disabled", text="⏳ Procesando…"))
        threading.Thread(
            target=self._tarea_archivos,
            args=(list(self._archivos), carpeta_forzada),
            daemon=True
        ).start()

    def _tarea_archivos(self, rutas, carpeta_forzada):
        total = len(rutas)
        ok_n  = 0
        err_n = 0
        self._log("info", f"\n▶ Convirtiendo {total} archivo(s)…\n")

        try:
            from markitdown import MarkItDown
            md = MarkItDown()
        except Exception as e:
            self._log("err", f"  ✗  No se pudo cargar MarkItDown: {e}\n")
            self.root.after(0, lambda: self.btn_convertir.config(
                state="normal", text="▶  CONVERTIR ARCHIVOS"))
            self._en_proceso = False
            return

        for i, ruta in enumerate(rutas, 1):
            nombre = os.path.basename(ruta)
            self._log("dim", f"  [{i}/{total}]  {nombre}  … ")
            self._set_progreso(i / total * 0.95)

            try:
                if not os.path.isfile(ruta):
                    raise FileNotFoundError(f"Archivo no encontrado: {ruta}")

                resultado = md.convert(ruta)
                texto = resultado.text_content or ""

                dest_dir = carpeta_forzada if carpeta_forzada else os.path.dirname(ruta)
                if not os.path.isdir(dest_dir):
                    os.makedirs(dest_dir, exist_ok=True)

                base = os.path.splitext(os.path.basename(ruta))[0]
                dest = os.path.join(dest_dir, base + ".md")
                if os.path.exists(dest):
                    dest = os.path.join(dest_dir, base + "_converted.md")

                with open(dest, "w", encoding="utf-8") as f:
                    f.write(texto)

                ok_n += 1
                self._log("ok", f"✓  {os.path.basename(dest)}\n")

            except Exception as e:
                err_n += 1
                self._log("err", f"✗  {type(e).__name__}: {e}\n")

        self._set_progreso(1.0)
        tag = "ok" if err_n == 0 else ("warn" if ok_n > 0 else "err")
        self._log(tag, f"\n{'─'*44}\n  Total: {total}  ·  ✓ {ok_n}  ·  ✗ {err_n}\n")
        self.root.after(800, lambda: self._set_progreso(0.0))
        self.root.after(0, lambda: self.btn_convertir.config(
            state="normal", text="▶  CONVERTIR ARCHIVOS"))
        self._en_proceso = False


# ── Punto de entrada ──────────────────────────────────────────────────────
if __name__ == "__main__":
    if not _asegurar_markitdown():
        import tkinter.messagebox as mb
        mb.showerror("Error", "No se pudo instalar markitdown.\n"
                               "Ejecuta: pip install markitdown")
        sys.exit(1)
    root = tk.Tk()
    app = MarkItDownApp(root)
    root.mainloop()
