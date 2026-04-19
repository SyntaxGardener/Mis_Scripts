# -*- coding: utf-8 -*-
"""
NotebookLM Toolbox · GUI unificada
pip install notebooklm-py
"""
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
import subprocess, threading, os

try:
    import notebooklm as _nlm  # pip install notebooklm-py  (solo para que lo detecte el analizador)
except ImportError:
    _nlm = None

# ── Tema claro ───────────────────────────────────────────────────────────────
BG_ROOT     = "#f0f4f8"
BG_SIDEBAR  = "#ffffff"
BG_CARD     = "#ffffff"
BG_CONTENT  = "#f0f4f8"
BG_BTN_HOV  = "#f1f5f9"
FG_MAIN     = "#1e293b"
FG_DIM      = "#64748b"
ACCENT      = "#2563eb"
ACCENT_LT   = "#dbeafe"
BORDER      = "#e2e8f0"
SUCCESS_FG  = "#15803d"
ERROR_FG    = "#dc2626"
WARN_FG     = "#b45309"

STORAGE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "notebooklm_auth.json")

NAV = [
    ("listar",    "📚", "Notebooks"),
    ("nuevo",     "📒", "Nuevo"),
    ("fuentes",   "📎", "Fuentes"),
    ("generar",   "⚙",  "Generar"),
    ("descargar", "⬇",  "Descargar"),
]

# ── Utilidades ───────────────────────────────────────────────────────────────

def run_cmd(cmd, out, on_done=None):
    if cmd[0] == "notebooklm":
        cmd = [cmd[0], "--storage", STORAGE] + cmd[1:]

    def _log(txt, tag=None):
        out.config(state="normal")
        out.insert("end", txt + "\n", tag or "")
        out.see("end")
        out.config(state="disabled")

    _log(f"$ {' '.join(cmd)}", "cmd")

    def _run():
        try:
            r = subprocess.run(cmd, capture_output=True, text=True,
                               encoding="utf-8", errors="replace")
            _log((r.stdout or "") + (r.stderr or ""))
            if on_done:
                on_done(r.returncode == 0)
        except FileNotFoundError:
            _log("❌ 'notebooklm' no encontrado.\n   Ejecuta: pip install notebooklm-py", "err")
            if on_done:
                on_done(False)
    threading.Thread(target=_run, daemon=True).start()


# ── Aplicación ───────────────────────────────────────────────────────────────

class App:
    def __init__(self, root):
        self.root = root
        root.title("NotebookLM Toolbox")
        root.configure(bg=BG_ROOT)
        w, h = 900, 640
        x = (root.winfo_screenwidth()  // 2) - (w // 2)
        y = (root.winfo_screenheight() // 2) - (h // 2)
        root.geometry(f"{w}x{h}+{x}+{y}")
        root.minsize(700, 500)

        self.nav_btns   = {}
        self.secciones  = {}
        self.seccion_act = None

        self._build_sidebar()
        self.content = tk.Frame(root, bg=BG_CONTENT)
        self.content.pack(side="left", fill="both", expand=True)

        self._init_secciones()
        self.mostrar("listar")

    # ── Sidebar ──────────────────────────────────────────────────────────────

    def _build_sidebar(self):
        sb = tk.Frame(self.root, bg=BG_SIDEBAR, width=182)
        sb.pack(side="left", fill="y")
        sb.pack_propagate(False)

        # Header
        hdr = tk.Frame(sb, bg=ACCENT)
        hdr.pack(fill="x")
        tk.Label(hdr, text="NotebookLM", fg="white", bg=ACCENT,
                 font=("Segoe UI Black", 12, "bold"), pady=10).pack()
        tk.Label(hdr, text="Toolbox", fg="#bfdbfe", bg=ACCENT,
                 font=("Segoe UI", 9), pady=(0)).pack()
        tk.Frame(hdr, bg=ACCENT, height=10).pack()

        # Nav
        nav_f = tk.Frame(sb, bg=BG_SIDEBAR)
        nav_f.pack(fill="x", pady=10)

        for key, icon, label in NAV:
            btn = tk.Button(nav_f,
                            text=f"  {icon}  {label}",
                            anchor="w", relief="flat",
                            bg=BG_SIDEBAR, fg=FG_MAIN,
                            font=("Segoe UI", 10),
                            cursor="hand2", pady=9, padx=14,
                            activebackground=ACCENT_LT,
                            activeforeground=FG_MAIN,
                            command=lambda k=key: self.mostrar(k))
            btn.pack(fill="x", padx=8, pady=1)
            btn.bind("<Enter>",
                     lambda e, b=btn, k=key:
                     b.config(bg=ACCENT_LT) if k != self.seccion_act else None)
            btn.bind("<Leave>",
                     lambda e, b=btn, k=key:
                     b.config(bg=ACCENT if k == self.seccion_act else BG_SIDEBAR))
            self.nav_btns[key] = btn

        # Footer
        tk.Frame(sb, bg=BORDER, height=1).pack(fill="x", padx=12, pady=10)
        tk.Label(sb, text="Auth guardada en:\nnotebooklm_auth.json",
                 fg=FG_DIM, bg=BG_SIDEBAR,
                 font=("Segoe UI", 7), justify="left").pack(padx=12, anchor="w")

    def mostrar(self, nombre):
        if self.seccion_act and self.seccion_act in self.secciones:
            self.secciones[self.seccion_act].pack_forget()
        self.secciones[nombre].pack(fill="both", expand=True)
        self.seccion_act = nombre
        for k, b in self.nav_btns.items():
            b.config(bg=ACCENT if k == nombre else BG_SIDEBAR,
                     fg="white"  if k == nombre else FG_MAIN)

    # ── Helpers de UI ────────────────────────────────────────────────────────

    def _card(self, parent, titulo):
        """Crea una tarjeta con título. Devuelve el frame interior."""
        outer = tk.Frame(parent, bg=BG_CONTENT)
        outer.pack(fill="x", padx=20, pady=(16, 8))
        card = tk.Frame(outer, bg=BG_CARD,
                        highlightbackground=BORDER, highlightthickness=1)
        card.pack(fill="x")
        tk.Label(card, text=titulo, fg=FG_MAIN, bg=BG_CARD,
                 font=("Segoe UI", 12, "bold")).pack(anchor="w", padx=16, pady=(12, 4))
        inner = tk.Frame(card, bg=BG_CARD)
        inner.pack(fill="x", padx=16, pady=(0, 14))
        return inner

    def _out(self, parent):
        """Crea y devuelve el área de salida de texto."""
        f = tk.Frame(parent, bg=BG_CONTENT)
        f.pack(fill="both", expand=True, padx=20, pady=(0, 16))
        out = scrolledtext.ScrolledText(
            f, bg=BG_CARD, fg=FG_MAIN,
            font=("Consolas", 9), relief="flat",
            state="disabled", bd=0,
            highlightbackground=BORDER, highlightthickness=1)
        out.tag_configure("cmd", foreground=FG_DIM)
        out.tag_configure("ok",  foreground=SUCCESS_FG)
        out.tag_configure("err", foreground=ERROR_FG)
        out.pack(fill="both", expand=True)
        return out

    def _lbl(self, parent, text, w=None):
        kw = {"width": w, "anchor": "w"} if w else {}
        return tk.Label(parent, text=text, fg=FG_MAIN, bg=BG_CARD,
                        font=("Segoe UI", 10), **kw)

    def _entry(self, parent, width=None):
        kw = {"width": width} if width else {}
        return tk.Entry(parent, bg="#f8fafc", fg=FG_MAIN,
                        insertbackground=FG_MAIN, relief="solid",
                        highlightbackground=BORDER, highlightthickness=1,
                        font=("Segoe UI", 10), **kw)

    def _btn(self, parent, text, cmd):
        return tk.Button(parent, text=text, command=cmd,
                         bg=ACCENT, fg="white", relief="flat",
                         font=("Segoe UI", 10, "bold"), cursor="hand2",
                         pady=8, activebackground="#1d4ed8", activeforeground="white")

    def _log_ok(self, out, msg):
        out.config(state="normal")
        out.insert("end", msg + "\n", "ok")
        out.config(state="disabled")

    # ── Secciones ────────────────────────────────────────────────────────────

    def _init_secciones(self):
        self.secciones["listar"]    = self._sec_listar()
        self.secciones["nuevo"]     = self._sec_nuevo()
        self.secciones["fuentes"]   = self._sec_fuentes()
        self.secciones["generar"]   = self._sec_generar()
        self.secciones["descargar"] = self._sec_descargar()

    # ·· Notebooks ············································

    def _sec_listar(self):
        f = tk.Frame(self.content, bg=BG_CONTENT)
        c = self._card(f, "📚  Notebooks · Listar y seleccionar")

        row = tk.Frame(c, bg=BG_CARD)
        row.pack(fill="x", pady=(0, 8))
        self._lbl(row, "Notebook activo — ID:").pack(side="left")
        self.ent_nb_id = self._entry(row, width=30)
        self.ent_nb_id.pack(side="left", padx=8)

        def usar():
            nid = self.ent_nb_id.get().strip()
            if nid:
                run_cmd(["notebooklm", "use", nid], self.out_listar)
            else:
                messagebox.showwarning("Aviso", "Introduce un ID", parent=self.root)

        self._btn(row, "✓  Usar", usar).pack(side="left")
        self._btn(c, "🔄  Listar todos los notebooks",
                  lambda: run_cmd(["notebooklm", "list"], self.out_listar)).pack(fill="x")

        self.out_listar = self._out(f)
        self.root.after(400, lambda: run_cmd(["notebooklm", "list"], self.out_listar))
        return f

    # ·· Nuevo ················································

    def _sec_nuevo(self):
        f = tk.Frame(self.content, bg=BG_CONTENT)
        c = self._card(f, "📒  Crear Nuevo Notebook")

        self._lbl(c, "Nombre del notebook:").pack(anchor="w")
        ent = self._entry(c)
        ent.pack(fill="x", pady=(4, 10))

        def crear():
            nombre = ent.get().strip()
            if not nombre:
                messagebox.showwarning("Aviso", "Escribe un nombre", parent=self.root)
                return
            btn.config(state="disabled", text="Creando…")
            def done(ok):
                self.root.after(0, lambda: btn.config(state="normal", text="➕  Crear notebook"))
                if ok:
                    self._log_ok(self.out_nuevo, "✅ Creado. Copia el ID de arriba y selecciónalo en Notebooks.")
            run_cmd(["notebooklm", "create", nombre], self.out_nuevo, on_done=done)

        btn = self._btn(c, "➕  Crear notebook", crear)
        btn.pack(fill="x")
        self.out_nuevo = self._out(f)
        return f

    # ·· Fuentes ··············································

    def _sec_fuentes(self):
        f = tk.Frame(self.content, bg=BG_CONTENT)
        c = self._card(f, "📎  Añadir Fuentes al Notebook Activo")

        tipo_var = tk.StringVar(value="url")
        tipo_f = tk.Frame(c, bg=BG_CARD)
        tipo_f.pack(fill="x", pady=(0, 8))
        for val, lbl in [("url", "🌐  URL"), ("archivo", "📄  Archivo (PDF / DOCX / TXT)")]:
            tk.Radiobutton(tipo_f, text=lbl, variable=tipo_var, value=val,
                           bg=BG_CARD, fg=FG_MAIN, selectcolor=BG_CARD,
                           activebackground=BG_CARD, font=("Segoe UI", 10),
                           command=lambda: _cambiar()).pack(side="left", padx=(0, 16))

        # Panels
        p_url  = tk.Frame(c, bg=BG_CARD)
        self._lbl(p_url, "URL (web, YouTube, Google Drive):").pack(anchor="w")
        ent_url = self._entry(p_url)
        ent_url.pack(fill="x", pady=(4, 0))

        p_arch = tk.Frame(c, bg=BG_CARD)
        self._lbl(p_arch, "Archivo:").pack(anchor="w")
        arch_row = tk.Frame(p_arch, bg=BG_CARD)
        arch_row.pack(fill="x", pady=(4, 0))
        ent_arch = self._entry(arch_row)
        ent_arch.pack(side="left", fill="x", expand=True)

        def examinar():
            r = filedialog.askopenfilename(
                parent=self.root,
                filetypes=[("Documentos","*.pdf *.docx *.doc *.txt *.md"), ("Todos","*.*")])
            if r:
                ent_arch.delete(0, "end")
                ent_arch.insert(0, r)

        tk.Button(arch_row, text="📂", bg=BG_BTN_HOV, fg=FG_MAIN, relief="flat",
                  cursor="hand2", font=("Segoe UI", 11), padx=10,
                  command=examinar).pack(side="left", padx=(6, 0))

        # Spacer frame to keep button below panels
        spacer = tk.Frame(c, bg=BG_CARD, height=8)
        spacer.pack()

        def _cambiar():
            p_url.pack_forget()
            p_arch.pack_forget()
            (p_url if tipo_var.get() == "url" else p_arch).pack(fill="x", pady=(0, 6))

        _cambiar()

        def añadir():
            if tipo_var.get() == "url":
                src = ent_url.get().strip()
                if not src:
                    messagebox.showwarning("Aviso", "Introduce una URL", parent=self.root); return
            else:
                src = ent_arch.get().strip()
                if not src:
                    messagebox.showwarning("Aviso", "Selecciona un archivo", parent=self.root); return
                if not os.path.exists(src):
                    messagebox.showerror("Error", f"No encontrado:\n{src}", parent=self.root); return
            btn_add.config(state="disabled", text="Añadiendo…")
            def done(ok):
                self.root.after(0, lambda: btn_add.config(state="normal", text="➕  Añadir fuente"))
                if ok: self._log_ok(self.out_fuentes, "✅ Fuente añadida.")
            run_cmd(["notebooklm", "source", "add", src], self.out_fuentes, on_done=done)

        btn_add = self._btn(c, "➕  Añadir fuente", añadir)
        btn_add.pack(fill="x")
        self.out_fuentes = self._out(f)
        return f

    # ·· Generar ··············································

    def _sec_generar(self):
        TIPOS = {
            "🎙  Podcast":      ("audio",      [("Formato",      ["deep-dive","brief","critique","debate"], "--format"),
                                                 ("Duración",     ["short","medium","long"],                 "--length")], True),
            "📝  Quiz":         ("quiz",        [("Dificultad",   ["easy","medium","hard"],                  "--difficulty"),
                                                 ("Cantidad",     ["fewer","default","more"],                 "--quantity")], False),
            "🃏  Flashcards":   ("flashcards",  [("Dificultad",   ["easy","medium","hard"],                  "--difficulty"),
                                                 ("Cantidad",     ["fewer","default","more"],                 "--quantity")], False),
            "📄  Informe":      ("report",      [("Plantilla",    ["briefing","study-guide","blog-post"],     "--format")],   True),
            "🗺  Mapa Mental":  ("mind-map",    [], True),
            "📊  Presentación": ("slide-deck",  [("Detalle",      ["detailed","presenter"],                  "--format")],   True),
            "🖼  Infografía":   ("infographic", [("Orientación",  ["portrait","landscape","square"],          "--orientation")], True),
            "🎬  Vídeo":        ("video",        [("Estilo",      ["whiteboard","slides","animated","talking-head","documentary"], "--style")], True),
        }

        f = tk.Frame(self.content, bg=BG_CONTENT)
        c = self._card(f, "⚙  Generar Contenido")

        # Tipo
        t_row = tk.Frame(c, bg=BG_CARD)
        t_row.pack(fill="x", pady=(0, 8))
        self._lbl(t_row, "¿Qué generar?").pack(side="left")
        combo_tipo = ttk.Combobox(t_row, values=list(TIPOS.keys()),
                                   state="readonly", font=("Segoe UI", 10), width=26)
        combo_tipo.current(0)
        combo_tipo.pack(side="left", padx=8)

        # Opciones dinámicas
        opts_f  = tk.Frame(c, bg=BG_CARD)
        opts_f.pack(fill="x")
        lbl_warn = tk.Label(c, text="", fg=WARN_FG, bg=BG_CARD, font=("Segoe UI", 8))
        lbl_warn.pack(anchor="w", pady=(2, 6))

        combos_opts = {}

        def actualizar(*_):
            for w in opts_f.winfo_children():
                w.destroy()
            combos_opts.clear()
            _, opciones, wait = TIPOS[combo_tipo.get()]
            lbl_warn.config(text="⏳ Puede tardar varios minutos." if wait else "")
            for lbl_txt, vals, flag in opciones:
                row = tk.Frame(opts_f, bg=BG_CARD)
                row.pack(fill="x", pady=2)
                self._lbl(row, f"{lbl_txt}:", w=100).pack(side="left")
                cb = ttk.Combobox(row, values=vals, state="readonly",
                                   font=("Segoe UI", 10), width=16)
                cb.current(0)
                cb.pack(side="left")
                combos_opts[flag] = cb

        combo_tipo.bind("<<ComboboxSelected>>", actualizar)
        actualizar()

        def generar():
            cmd_name, _, wait = TIPOS[combo_tipo.get()]
            cmd = ["notebooklm", "generate", cmd_name]
            for flag, cb in combos_opts.items():
                cmd += [flag, cb.get()]
            if wait:
                cmd.append("--wait")
            btn_gen.config(state="disabled", text="Generando… ⏳")
            def done(ok):
                self.root.after(0, lambda: btn_gen.config(state="normal", text="▶  Generar"))
                if ok: self._log_ok(self.out_generar, "✅ Completado. Ve a Descargar para guardarlo.")
            run_cmd(cmd, self.out_generar, on_done=done)

        btn_gen = self._btn(c, "▶  Generar", generar)
        btn_gen.pack(fill="x")
        self.out_generar = self._out(f)
        return f

    # ·· Descargar ············································

    def _sec_descargar(self):
        ARTS = {
            "🎙  Podcast":      ("audio",      ".mp3",  [("Audio","*.mp3 *.mp4")],                              None),
            "📝  Quiz":         ("quiz",        ".json", [("JSON","*.json"),("Markdown","*.md"),("HTML","*.html")], ["json","markdown","html"]),
            "🃏  Flashcards":   ("flashcards",  ".json", [("JSON","*.json"),("Markdown","*.md"),("HTML","*.html")], ["json","markdown","html"]),
            "📊  Presentación": ("slide-deck",  ".pdf",  [("PDF","*.pdf"),("PowerPoint","*.pptx")],              None),
            "🗺  Mapa Mental":  ("mind-map",    ".json", [("JSON","*.json")],                                    None),
            "🖼  Infografía":   ("infographic", ".png",  [("PNG","*.png")],                                      None),
            "📋  Tabla datos":  ("data-table",  ".csv",  [("CSV","*.csv")],                                      None),
            "🎬  Vídeo":        ("video",       ".mp4",  [("MP4","*.mp4")],                                      None),
        }

        f = tk.Frame(self.content, bg=BG_CONTENT)
        c = self._card(f, "⬇  Descargar Artefacto Generado")

        # Tipo
        r1 = tk.Frame(c, bg=BG_CARD)
        r1.pack(fill="x", pady=(0, 6))
        self._lbl(r1, "Tipo:", w=100).pack(side="left")
        combo_art = ttk.Combobox(r1, values=list(ARTS.keys()),
                                  state="readonly", font=("Segoe UI", 10), width=26)
        combo_art.current(0)
        combo_art.pack(side="left")

        # Formato (condicional) — frame siempre presente, contenido dinámico
        r2 = tk.Frame(c, bg=BG_CARD)
        r2.pack(fill="x", pady=(0, 6))
        self._combo_fmt = None

        def actualizar_fmt(*_):
            for w in r2.winfo_children():
                w.destroy()
            self._combo_fmt = None
            fmts = ARTS[combo_art.get()][3]
            if fmts:
                self._lbl(r2, "Formato:", w=100).pack(side="left")
                cb = ttk.Combobox(r2, values=fmts, state="readonly",
                                   font=("Segoe UI", 10), width=16)
                cb.current(0)
                cb.pack(side="left")
                self._combo_fmt = cb

        combo_art.bind("<<ComboboxSelected>>", actualizar_fmt)
        actualizar_fmt()

        # Destino
        r3 = tk.Frame(c, bg=BG_CARD)
        r3.pack(fill="x", pady=(0, 10))
        self._lbl(r3, "Guardar como:", w=100).pack(side="left")
        ent_dest = self._entry(r3)
        ent_dest.pack(side="left", fill="x", expand=True)

        def examinar():
            art = ARTS[combo_art.get()]
            ruta = filedialog.asksaveasfilename(
                parent=self.root, defaultextension=art[1],
                filetypes=art[2] + [("Todos","*.*")])
            if ruta:
                ent_dest.delete(0, "end")
                ent_dest.insert(0, ruta)

        tk.Button(r3, text="📂", bg=BG_BTN_HOV, fg=FG_MAIN, relief="flat",
                  cursor="hand2", font=("Segoe UI", 11), padx=10,
                  command=examinar).pack(side="left", padx=(6, 0))

        def descargar():
            dest = ent_dest.get().strip()
            if not dest:
                messagebox.showwarning("Aviso", "Elige dónde guardar", parent=self.root); return
            art = ARTS[combo_art.get()]
            cmd = ["notebooklm", "download", art[0]]
            if self._combo_fmt:
                cmd += ["--format", self._combo_fmt.get()]
            cmd.append(dest)
            btn_dl.config(state="disabled", text="Descargando… ⏳")
            def done(ok):
                self.root.after(0, lambda: btn_dl.config(state="normal", text="⬇  Descargar"))
                if ok:
                    self._log_ok(self.out_descargar, f"✅ Guardado en: {dest}")
                    try:
                        os.startfile(os.path.dirname(os.path.abspath(dest)))
                    except Exception:
                        pass
            run_cmd(cmd, self.out_descargar, on_done=done)

        btn_dl = self._btn(c, "⬇  Descargar", descargar)
        btn_dl.pack(fill="x")
        self.out_descargar = self._out(f)
        return f


# ── Main ─────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    root = tk.Tk()
    App(root)
    root.mainloop()
