# -*- coding: utf-8 -*-
"""
NotebookLM Toolbox · GUI unificada
pip install notebooklm-py
"""
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
import subprocess, threading, os, re, sys, tempfile

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
    ("login",     "🔑", "Login"),
    ("listar",    "📚", "Notebooks"),
    ("nuevo",     "📒", "Nuevo"),
    ("fuentes",   "📎", "Fuentes"),
    ("generar",   "⚙",  "Generar"),
    ("descargar", "⬇",  "Descargar"),
]

# ── Utilidades ───────────────────────────────────────────────────────────────

def _nlm_cmd():
    """Usa python.exe (no pythonw.exe) para que la consola de login funcione correctamente."""
    exe = sys.executable
    # pythonw.exe no tiene consola — lo cambiamos por python.exe
    if exe.lower().endswith("pythonw.exe"):
        exe = exe[:-len("pythonw.exe")] + "python.exe"
    return [exe, "-m", "notebooklm"]

def run_cmd(cmd, out, on_done=None):
    if cmd[0] == "notebooklm":
        cmd = _nlm_cmd() + ["--storage", STORAGE] + cmd[1:]

    def _log(txt, tag=None):
        out.config(state="normal")
        out.insert("end", txt + "\n", tag or "")
        out.see("end")
        out.config(state="disabled")

    _log(f"$ {' '.join(cmd)}", "cmd")

    def _run():
        try:
            env = os.environ.copy()
            env["PYTHONIOENCODING"] = "utf-8"
            env["PYTHONUTF8"] = "1"
            env["COLUMNS"] = "300"
            r = subprocess.run(cmd, capture_output=True, text=True,
                               encoding="utf-8", errors="replace", env=env)
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
        x = (root.winfo_screenwidth() // 2) - (w // 2)
        y = 5
        root.geometry(f"{w}x{h}+{x}+{y}")
        root.minsize(700, 500)

        self.nav_btns    = {}
        self.secciones   = {}
        self.seccion_act = None
        self.nb_id       = ""

        self._build_sidebar()
        self.content = tk.Frame(root, bg=BG_CONTENT)
        self.content.pack(side="left", fill="both", expand=True)

        self._init_secciones()
        if os.path.exists(STORAGE):
            self.mostrar("listar")
        else:
            self.mostrar("login")

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
        inner.pack(fill="both", expand=True, padx=16, pady=(0, 14))
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

    def _get_nb_id(self):
        nid = self.nb_id.strip()
        if not nid:
            messagebox.showwarning(
                "Sin notebook activo",
                "Primero ve a 📚 Notebooks, pega el ID y pulsa ✓ Usar.",
                parent=self.root)
            return None
        return nid

    # ── Secciones ────────────────────────────────────────────────────────────

    def _init_secciones(self):
        self.secciones["login"]     = self._sec_login()
        self.secciones["listar"]    = self._sec_listar()
        self.secciones["nuevo"]     = self._sec_nuevo()
        self.secciones["fuentes"]   = self._sec_fuentes()
        self.secciones["generar"]   = self._sec_generar()
        self.secciones["descargar"] = self._sec_descargar()

    # ·· Login ················································

    def _sec_login(self):
        f = tk.Frame(self.content, bg=BG_CONTENT)
        c = self._card(f, "🔑  Login con Google")

        self.lbl_auth_status = tk.Label(c, bg=BG_CARD, font=("Segoe UI", 10))
        self.lbl_auth_status.pack(anchor="w", pady=(0, 10))
        self._actualizar_estado_auth()

        info = (
            "Al pulsar 'Iniciar Login' se abrirá una terminal y el navegador.\n"
            "1. Inicia sesión con tu cuenta de Google.\n"
            "2. Espera a ver la página principal de NotebookLM.\n"
            "3. Pulsa ENTER en la terminal para guardar la sesión."
        )
        tk.Label(c, text=info, bg=BG_CARD, fg=FG_DIM,
                 font=("Segoe UI", 9), justify="left").pack(anchor="w", pady=(0, 12))

        btn_login = self._btn(c, "🌐  Iniciar Login",
                              lambda: self._hacer_login(btn_login))
        btn_login.pack(fill="x")

        self.out_login = self._out(f)
        return f

    def _actualizar_estado_auth(self):
        if os.path.exists(STORAGE):
            self.lbl_auth_status.config(
                text=f"✅  Sesión guardada  ({os.path.basename(STORAGE)})",
                fg=SUCCESS_FG)
        else:
            self.lbl_auth_status.config(
                text="⚠️  No hay sesión guardada todavía.",
                fg=WARN_FG)

    def _hacer_login(self, btn_login):
        btn_login.config(state="disabled", text="Abriendo navegador…")
        btn_guardar.config(state="disabled", bg="#94a3b8")

        self.out_login.config(state="normal")
        self.out_login.insert("end",
            "ℹ️  Se abrirá una ventana de terminal.\n"
            "   1. Inicia sesión con Google en el navegador.\n"
            "   2. Cuando veas NotebookLM, pulsa ENTER en esa terminal.\n"
            "   3. Vuelve aquí y pulsa '💾 Guardar sesión'.\n\n", "")
        self.out_login.config(state="disabled")

        def _run():
            try:
                cmd = _nlm_cmd() + ["login", "--storage", STORAGE]
                cmd_str = " ".join(f'"{c}"' if " " in c else c for c in cmd)
                subprocess.Popen(
                    ["cmd", "/k", cmd_str],
                    creationflags=subprocess.CREATE_NEW_CONSOLE,
                    close_fds=True,
                ).wait()
            except Exception as e:
                self.root.after(0, lambda err=e: (
                    self.out_login.config(state="normal"),
                    self.out_login.insert("end", f"❌ Error: {err}\n", "err"),
                    self.out_login.config(state="disabled"),
                ))
            self.root.after(0, lambda: (
                btn_login.config(state="normal", text="🌐  Iniciar Login"),
                self._actualizar_estado_auth(),
            ))

        threading.Thread(target=_run, daemon=True).start()
    def _guardar_auth(self, btn_guardar):
        import shutil, glob
        posibles = [
            os.path.join(os.environ.get("USERPROFILE",   ""), ".notebooklm", "storage_state.json"),
            os.path.join(os.environ.get("APPDATA",       ""), ".notebooklm", "storage_state.json"),
            os.path.join(os.environ.get("LOCALAPPDATA",  ""), ".notebooklm", "storage_state.json"),
        ]
        extra = glob.glob(os.path.join(os.environ.get("USERPROFILE", ""),
                                       ".notebooklm", "*.json"))
        posibles += extra
        # Filtrar el propio STORAGE para no copiarlo sobre sí mismo
        posibles = [p for p in posibles if os.path.exists(p) and os.path.abspath(p) != os.path.abspath(STORAGE)]
        origen = posibles[0] if posibles else None
        out = self.out_login
        if not origen:
            out.config(state="normal")
            out.insert("end", "❌ No se encontró el archivo de sesión.\n"
                               "   ¿Completaste el login en el navegador?\n", "err")
            out.config(state="disabled")
            return
        try:
            shutil.copy2(origen, STORAGE)
            self._actualizar_estado_auth()
            self._log_ok(out, f"✅ Sesión guardada en:\n   {STORAGE}")
            btn_guardar.config(state="disabled", bg="#94a3b8")
        except Exception as e:
            out.config(state="normal")
            out.insert("end", f"❌ Error al copiar: {e}\n", "err")
            out.config(state="disabled")

    # ·· Notebooks ············································

    def _sec_listar(self):
        f = tk.Frame(self.content, bg=BG_CONTENT)
        c = self._card(f, "📚  Notebooks · Listar y seleccionar")

        row = tk.Frame(c, bg=BG_CARD)
        row.pack(fill="x", pady=(0, 4))
        self._lbl(row, "Notebook activo — ID:").pack(side="left")
        self.ent_nb_id = self._entry(row, width=30)
        self.ent_nb_id.pack(side="left", padx=8)

        self.lbl_nb_activo = tk.Label(row, text="", fg=SUCCESS_FG, bg=BG_CARD,
                                      font=("Segoe UI", 9))
        self.lbl_nb_activo.pack(side="left")

        def usar():
            nid = self.ent_nb_id.get().strip()
            if nid:
                self.nb_id = nid
                self.lbl_nb_activo.config(text="✅ Activo")
                self._log_ok(self.out_listar, f"✅ Notebook activo: {nid}")
            else:
                messagebox.showwarning("Aviso", "Introduce un ID", parent=self.root)

        self._btn(row, "✓  Usar", usar).pack(side="left")

        # Hint clic
        tk.Label(c, text="💡 Haz clic en una línea del resultado para seleccionar su ID automáticamente",
                 fg=FG_DIM, bg=BG_CARD, font=("Segoe UI", 8)).pack(anchor="w", pady=(0, 6))

        self._btn(c, "🔄  Listar todos los notebooks",
                  lambda: run_cmd(["notebooklm", "list"], self.out_listar)).pack(fill="x")

        self.out_listar = self._out(f)

        # Clic en resultado → extraer UUID y ponerlo en el campo
        UUID_RE = re.compile(r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}',
                             re.IGNORECASE)

        def _clic_resultado(event):
            widget = event.widget
            idx = widget.index(f"@{event.x},{event.y}")
            linea = widget.get(f"{idx} linestart", f"{idx} lineend")
            m = UUID_RE.search(linea)
            if m:
                nid = m.group(0)
                self.ent_nb_id.delete(0, "end")
                self.ent_nb_id.insert(0, nid)
                self.nb_id = nid
                self.lbl_nb_activo.config(text="✅ Activo")
                self._log_ok(self.out_listar, f"✅ Notebook activo: {nid}")

        self.out_listar.bind("<Button-1>", _clic_resultado)

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
            nid = self._get_nb_id()
            if not nid: return
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
            run_cmd(["notebooklm", "source", "add", src, "--notebook", nid],
                    self.out_fuentes, on_done=done)

        btn_add = self._btn(c, "➕  Añadir fuente", añadir)
        btn_add.pack(fill="x")
        self.out_fuentes = self._out(f)
        return f

    # ·· Generar ··············································

    def _sec_generar(self):
        TIPOS = {
            "🎙  Podcast":      ("audio",      [("Formato",      ["deep-dive","brief","critique","debate"], "--format"),
                                                 ("Duración",     ["short","default","long"],                 "--length")], True),
            "📝  Quiz":         ("quiz",        [("Dificultad",   ["easy","medium","hard"],                  "--difficulty"),
                                                 ("Cantidad",     ["fewer","default","more"],                 "--quantity")], False),
            "🃏  Flashcards":   ("flashcards",  [("Dificultad",   ["easy","medium","hard"],                  "--difficulty"),
                                                 ("Cantidad",     ["fewer","default","more"],                 "--quantity")], False),
            "📄  Informe":      ("report",      [("Plantilla",    ["briefing-doc","study-guide","blog-post","custom"],     "--format")],   True),
            "🗺  Mapa Mental":  ("mind-map",    [], True),
            "📊  Presentación": ("slide-deck",  [("Detalle",      ["detailed","presenter"],                  "--format")],   True),
            "🖼  Infografía":   ("infographic", [("Orientación",  ["portrait","landscape","square"],          "--orientation")], True),
            "🎬  Vídeo":        ("video",        [("Estilo",      ["whiteboard","slides","animated","talking-head","documentary"], "--style")], True),
        }

        f = tk.Frame(self.content, bg=BG_CONTENT)
        c = self._card(f, "⚙  Generar Contenido")
        c.columnconfigure(1, weight=1)

        # Tipo
        self._lbl(c, "¿Qué generar?").grid(row=0, column=0, sticky="w", pady=(0, 6), padx=(0, 10))
        combo_tipo = ttk.Combobox(c, values=list(TIPOS.keys()),
                                   state="readonly", font=("Segoe UI", 10))
        combo_tipo.current(0)
        combo_tipo.grid(row=0, column=1, sticky="ew", pady=(0, 6))

        # Opciones dinámicas (frame contenedor en grid)
        opts_f = tk.Frame(c, bg=BG_CARD)
        opts_f.grid(row=1, column=0, columnspan=2, sticky="ew")
        opts_f.columnconfigure(1, weight=1)

        lbl_warn = tk.Label(c, text="", fg=WARN_FG, bg=BG_CARD, font=("Segoe UI", 8))
        lbl_warn.grid(row=2, column=0, columnspan=2, sticky="w", pady=(2, 4))

        combos_opts = {}

        def actualizar(*_):
            for w in opts_f.winfo_children():
                w.destroy()
            combos_opts.clear()
            _, opciones, wait = TIPOS[combo_tipo.get()]
            lbl_warn.config(text="⏳ Puede tardar varios minutos." if wait else "")
            for i, (lbl_txt, vals, flag) in enumerate(opciones):
                tk.Label(opts_f, text=f"{lbl_txt}:", fg=FG_MAIN, bg=BG_CARD,
                         font=("Segoe UI", 10), anchor="w").grid(
                             row=i, column=0, sticky="w", pady=2, padx=(0, 10))
                cb = ttk.Combobox(opts_f, values=vals, state="readonly",
                                   font=("Segoe UI", 10))
                cb.current(0)
                cb.grid(row=i, column=1, sticky="ew", pady=2)
                combos_opts[flag] = cb

        combo_tipo.bind("<<ComboboxSelected>>", actualizar)
        actualizar()

        # Idioma
        self._lbl(c, "Idioma:").grid(row=3, column=0, sticky="w", pady=(4, 6), padx=(0, 10))
        ent_lang = ttk.Combobox(c, values=["es","en","fr","de","it","pt","ja","ko","zh"],
                                 font=("Segoe UI", 10))
        ent_lang.set("es")
        ent_lang.grid(row=3, column=1, sticky="ew", pady=(4, 6))

        btn_gen = self._btn(c, "▶  Generar", None)
        btn_gen.grid(row=4, column=0, columnspan=3, sticky="ew", pady=(2, 0))

        def generar():
            nid = self._get_nb_id()
            if not nid: return
            lang = ent_lang.get().strip() or "es"
            cmd_name, _, _ = TIPOS[combo_tipo.get()]
            cmd = ["notebooklm", "generate", cmd_name, "--notebook", nid,
                   "--language", lang, "--no-wait"]
            for flag, cb in combos_opts.items():
                cmd += [flag, cb.get()]
            btn_gen.config(state="disabled", text="Lanzando… ⏳")
            def done(ok):
                self.root.after(0, lambda: btn_gen.config(state="normal", text="▶  Generar"))
                if ok: self._log_ok(self.out_generar,
                                    "✅ Tarea lanzada. Espera unos minutos y descarga desde ⬇ Descargar.")
            run_cmd(cmd, self.out_generar, on_done=done)

        btn_gen.config(command=generar)

        # ── Estado de tarea ──────────────────────────────────
        self._lbl(c, "Task ID:").grid(row=5, column=0, sticky="w", pady=(8, 0), padx=(0, 10))
        self.ent_task_id = self._entry(c)
        self.ent_task_id.grid(row=5, column=1, sticky="ew", pady=(8, 0), padx=(0, 6))

        def ver_estado():
            tid = self.ent_task_id.get().strip()
            if tid:
                run_cmd(["notebooklm", "artifact", "poll", tid], self.out_generar)
            else:
                nid = self._get_nb_id()
                if nid:
                    run_cmd(["notebooklm", "artifact", "list", "--notebook", nid], self.out_generar)

        self._btn(c, "🔍 Ver estado", ver_estado).grid(row=5, column=2, sticky="e", pady=(8, 0))

        # Auto-capturar el task ID de la salida al generar
        _orig_generar = generar
        def generar_con_capture():
            _orig_generar()
            # Monitorizar la salida para extraer el task ID
            def _watch():
                import time, re
                for _ in range(30):
                    time.sleep(0.3)
                    self.out_generar.config(state="normal")
                    texto = self.out_generar.get("1.0", "end")
                    self.out_generar.config(state="disabled")
                    m = re.search(r"Started:\s*([0-9a-f-]{36})", texto)
                    if m:
                        tid = m.group(1)
                        self.root.after(0, lambda t=tid: (
                            self.ent_task_id.delete(0, "end"),
                            self.ent_task_id.insert(0, t)
                        ))
                        break
            threading.Thread(target=_watch, daemon=True).start()

        btn_gen.config(command=generar_con_capture)

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
            "📄  Informe":      ("report",      ".md",   [("Markdown","*.md")],                                   None),
            "🎬  Vídeo":        ("video",       ".mp4",  [("MP4","*.mp4")],                                      None),
        }

        f = tk.Frame(self.content, bg=BG_CONTENT)
        c = self._card(f, "⬇  Descargar Artefacto Generado")
        c.columnconfigure(1, weight=1)

        # Tipo
        self._lbl(c, "Tipo:").grid(row=0, column=0, sticky="w", pady=(0, 6), padx=(0, 10))
        combo_art = ttk.Combobox(c, values=list(ARTS.keys()),
                                  state="readonly", font=("Segoe UI", 10))
        combo_art.current(0)
        combo_art.grid(row=0, column=1, columnspan=2, sticky="ew", pady=(0, 6))

        # Formato (condicional) — fila 1, se rellena dinámicamente
        fmt_lbl = tk.Label(c, text="", fg=FG_MAIN, bg=BG_CARD, font=("Segoe UI", 10), anchor="w")
        fmt_lbl.grid(row=1, column=0, sticky="w", pady=(0, 6), padx=(0, 10))
        self._combo_fmt = None
        fmt_frame = tk.Frame(c, bg=BG_CARD)
        fmt_frame.grid(row=1, column=1, columnspan=2, sticky="ew", pady=(0, 6))
        fmt_frame.columnconfigure(0, weight=1)

        def actualizar_fmt(*_):
            for w in fmt_frame.winfo_children():
                w.destroy()
            self._combo_fmt = None
            fmts = ARTS[combo_art.get()][3]
            if fmts:
                fmt_lbl.config(text="Formato:")
                cb = ttk.Combobox(fmt_frame, values=fmts, state="readonly",
                                   font=("Segoe UI", 10))
                cb.current(0)
                cb.grid(row=0, column=0, sticky="ew")
                self._combo_fmt = cb
            else:
                fmt_lbl.config(text="")

        combo_art.bind("<<ComboboxSelected>>", actualizar_fmt)
        actualizar_fmt()

        # Nombre (opcional)
        self._lbl(c, "Nombre:").grid(row=2, column=0, sticky="w", pady=(0, 6), padx=(0, 10))
        ent_name = self._entry(c)
        ent_name.grid(row=2, column=1, columnspan=2, sticky="ew", pady=(0, 6))
        tk.Label(c, text="(opcional, busca por título)", fg=FG_DIM, bg=BG_CARD,
                 font=("Segoe UI", 8)).grid(row=2, column=3, sticky="w", padx=(6, 0))

        # Destino
        self._lbl(c, "Guardar como:").grid(row=3, column=0, sticky="w", pady=(0, 10), padx=(0, 10))
        ent_dest = self._entry(c)
        ent_dest.grid(row=3, column=1, sticky="ew", pady=(0, 10), padx=(0, 6))

        def examinar():
            art = ARTS[combo_art.get()]
            ruta = filedialog.asksaveasfilename(
                parent=self.root, defaultextension=art[1],
                filetypes=art[2] + [("Todos","*.*")])
            if ruta:
                ent_dest.delete(0, "end")
                ent_dest.insert(0, ruta)

        tk.Button(c, text="📂", bg=BG_BTN_HOV, fg=FG_MAIN, relief="flat",
                  cursor="hand2", font=("Segoe UI", 11), padx=10,
                  command=examinar).grid(row=3, column=2, pady=(0, 10))

        def descargar():
            nid = self._get_nb_id()
            if not nid: return
            dest = ent_dest.get().strip()
            if not dest:
                messagebox.showwarning("Aviso", "Elige dónde guardar", parent=self.root); return
            art = ARTS[combo_art.get()]
            cmd = ["notebooklm", "download", art[0], "--notebook", nid]
            nombre = ent_name.get().strip()
            if nombre:
                cmd += ["--name", nombre]
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
        btn_dl.grid(row=4, column=0, columnspan=3, sticky="ew")
        self.out_descargar = self._out(f)
        return f


# ── Main ─────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    root = tk.Tk()
    App(root)
    root.mainloop()
