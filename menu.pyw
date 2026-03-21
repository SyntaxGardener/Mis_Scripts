# -*- coding: utf-8 -*-
import tkinter as tk
from tkinter import messagebox, simpledialog
import subprocess
import os
import sys
import shutil
import threading
import webbrowser

# ─────────────────────────────────────────────
#  CONFIGURACIÓN VISUAL
# ─────────────────────────────────────────────
ACENTO   = "#e8e8e8"   # color único para scripts normales
ACENTO_FAV = "#ffd54f" # dorado solo para favoritos

COLORES = {
    "FAVORITOS":      "#ffd54f",   # dorado
    "SISTEMA":        "#4dd0e1",   # cian
    "PDF/DOCX":       "#ef5350",   # rojo
    "ADMINISTRACIÓN": "#9b59b6",   # púrpura
    "CLASES":         "#66bb6a",   # verde
    "AULA":           "#ff7f24",   # naranja
    "AUDIO & VÍDEO":  "#ec407a",   # rosa
    "OTROS":          "#90a4ae",   # gris azulado
}

def hacer_icono_carpeta(parent, color, bg):
    c = tk.Canvas(parent, width=20, height=20,
                  bg=bg, highlightthickness=0)
    c.create_rectangle(1, 5, 8,  9,  fill=color, outline="")
    c.create_rectangle(1, 8, 19, 19, fill=color, outline="")
    return c

BG_ROOT     = "#0d0d0d"
BG_PANEL    = "#141414"
BG_CARD     = "#1c1c1c"
BG_CARD_HOV = "#272727"
BG_SEARCH   = "#1e1e1e"
FG_MUTED    = "#666666"
FG_DIM      = "#666666"
FG_MAIN     = "#e8e8e8"

FAV_FILE   = "favoritos.txt"
GITHUB_URL = "https://github.com/SyntaxGardener/"


# ─────────────────────────────────────────────
#  FUNCIONES DE SOPORTE
# ─────────────────────────────────────────────
def leer_favoritos():
    if os.path.exists(FAV_FILE):
        try:
            with open(FAV_FILE, "r", encoding="utf-8") as f:
                return [line.strip() for line in f.readlines()]
        except:
            return []
    return []

def guardar_favoritos(favoritos):
    with open(FAV_FILE, "w", encoding="utf-8") as f:
        for fav in favoritos:
            f.write(f"{fav}\n")

def obtener_info_sistema():
    v_python = f"Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    ruta_base = os.path.dirname(os.path.abspath(__file__))
    unidad = os.path.splitdrive(ruta_base)[0]
    try:
        total, usado, libre = shutil.disk_usage(unidad if unidad else "/")
        gb_libres = libre // (2**30)
        gb_total  = total // (2**30)
        return f"{v_python}   ·   {unidad if unidad else 'USB'}  {gb_libres} GB libres / {gb_total} GB"
    except:
        return v_python

def ejecutar_herramienta(ruta_archivo, ventana_principal):
    try:
        if not os.path.exists(ruta_archivo):
            messagebox.showerror("Error", f"El archivo NO existe en:\n{ruta_archivo}")
            return
        ruta_abs = os.path.abspath(ruta_archivo)
        exe_py = sys.executable.replace("pythonw.exe", "python.exe")
        if ruta_abs.lower().endswith(".py"):
            subprocess.Popen([exe_py, ruta_abs], creationflags=subprocess.CREATE_NEW_CONSOLE)
        elif ruta_abs.lower().endswith(".pyw"):
            subprocess.Popen([sys.executable, ruta_abs])
        else:
            os.startfile(ruta_abs)
    except Exception as e:
        messagebox.showerror("Error Crítico", f"Fallo al lanzar:\n{e}")


# ─────────────────────────────────────────────
#  CLASE PRINCIPAL
# ─────────────────────────────────────────────
class MenuFinalPerfecto:
    def __init__(self, root):
        self.root = root
        self.root.title("TOOLBOX · RCM")
        ancho, alto = 820, 780
        pos_x = (self.root.winfo_screenwidth()  // 2) - (ancho // 2)
        pos_y = (self.root.winfo_screenheight() // 2) - (alto  // 2)
        self.root.geometry(f"{ancho}x{alto}+{pos_x}+2")
        self.root.configure(bg=BG_ROOT)
        self.root.minsize(640, 500)

        # Rutas dinámicas
        self.base_dir  = os.path.dirname(os.path.abspath(__file__))
        self.ruta_git  = self._detectar_portable_git()
        self.ruta_config = os.path.normpath(os.path.join(self.base_dir, "..", "Config"))
        self.ruta_creds  = os.path.join(self.ruta_config, ".git-credentials").replace("\\", "/")

        if not os.path.exists(self.ruta_config):
            os.makedirs(self.ruta_config)

        self.favoritos        = leer_favoritos()
        self.estados_carpetas = {cat: False for cat in COLORES.keys()}

        self._construir_ui()
        self.cargar_scripts()
        threading.Thread(target=self.comprobar_git_status, daemon=True).start()

        # Atajos de teclado
        self.root.bind("<F5>",     lambda e: self.actualizar_todo())
        self.root.bind("<Escape>", lambda e: self._limpiar_busqueda())

    # ── UI ────────────────────────────────────
    def _construir_ui(self):
        # ── HEADER ────────────────────────────
        header = tk.Frame(self.root, bg=BG_ROOT)
        header.pack(fill="x", padx=20, pady=(14, 6))

        left = tk.Frame(header, bg=BG_ROOT)
        left.pack(side="left")

        tk.Label(left, text="TOOLBOX", fg=FG_MAIN, bg=BG_ROOT,
                 font=("Segoe UI Black", 17, "bold")).pack(side="left")

        sep = tk.Label(left, text=" · ", fg=FG_MUTED, bg=BG_ROOT,
                       font=("Segoe UI", 14))
        sep.pack(side="left")

        gh = tk.Label(left, text="SyntaxGardener", fg="#444", bg=BG_ROOT,
                      font=("Segoe UI", 10), cursor="hand2")
        gh.pack(side="left", pady=(4, 0))
        gh.bind("<Button-1>", lambda e: webbrowser.open(GITHUB_URL))
        gh.bind("<Enter>",    lambda e: gh.config(fg="#8b949e"))
        gh.bind("<Leave>",    lambda e: gh.config(fg="#444"))

        # Botones de acción (derecha)
        right = tk.Frame(header, bg=BG_ROOT)
        right.pack(side="right")

        self._hacer_boton_accion(right, "🔄 REFRESCAR", "#1a2a1a", "#4caf50", 
                                  self.actualizar_todo).pack(side="right", padx=3)

        self._hacer_boton_accion(right, "🛠 REPARAR", "#1e1212", "#c0392b",
                                  self.reparar_repositorio).pack(side="right", padx=3)

        self.btn_push = self._hacer_boton_accion(right, "☁ SUBIR", "#1c1c1c", FG_DIM,
                                                   self.realizar_push)
        self.btn_push.pack(side="right", padx=3)
        self.btn_push.config(state="disabled")

        self.btn_pull = self._hacer_boton_accion(right, "📥 DESCARGAR", "#1c1c1c", FG_DIM,
                                                   self.realizar_pull)
        self.btn_pull.pack(side="right", padx=3)

        # ── BUSCADOR ──────────────────────────
        search_outer = tk.Frame(self.root, bg=BG_SEARCH, pady=1)
        search_outer.pack(fill="x", padx=20, pady=(6, 2))

        search_inner = tk.Frame(search_outer, bg=BG_SEARCH, padx=10, pady=6)
        search_inner.pack(fill="x")

        tk.Label(search_inner, text="⌕", fg=FG_MUTED, bg=BG_SEARCH,
                 font=("Segoe UI", 13)).pack(side="left", padx=(0, 6))

        self.entry_busqueda = tk.Entry(search_inner, bg=BG_SEARCH, fg=FG_DIM,
                                       insertbackground="white", borderwidth=0,
                                       font=("Segoe UI", 11))
        self.entry_busqueda.pack(side="left", fill="x", expand=True)
        self.entry_busqueda.insert(0, "Buscar script…")
        self.entry_busqueda.bind("<FocusIn>",   self._on_search_focus)
        self.entry_busqueda.bind("<FocusOut>",  self._on_search_unfocus)
        self.entry_busqueda.bind("<KeyRelease>", self.filtrar_scripts)

        # ── BARRA DE ESTADO ───────────────────
        status = tk.Frame(self.root, bg=BG_PANEL, height=28)
        status.pack(fill="x", padx=20, pady=(2, 8))
        status.pack_propagate(False)

        self.lbl_modo = tk.Label(status, fg="#555", bg=BG_PANEL,
                                  font=("Segoe UI", 8, "bold"))
        self.lbl_modo.pack(side="left", padx=10)

        tk.Label(status, text="│", fg="#2a2a2a", bg=BG_PANEL).pack(side="left")

        self.lbl_git = tk.Label(status, text="git · buscando…", fg="#333",
                                 bg=BG_PANEL, font=("Consolas", 8))
        self.lbl_git.pack(side="left", padx=10)

        tk.Label(status, text="│", fg="#2a2a2a", bg=BG_PANEL).pack(side="left")

        self.lbl_commit = tk.Label(status, text="", fg="#888888",
                                    bg=BG_PANEL, font=("Consolas", 8))
        self.lbl_commit.pack(side="left", padx=6)

        self.lbl_info = tk.Label(status, fg="#888888", bg=BG_PANEL, font=("Consolas", 8))
        self.lbl_info.pack(side="right", padx=10)

        self.actualizar_barra_estado()

        # ── SCROLL ────────────────────────────
        outer = tk.Frame(self.root, bg=BG_ROOT)
        outer.pack(fill="both", expand=True, padx=20, pady=(0, 16))

        self.canvas = tk.Canvas(outer, bg=BG_ROOT, highlightthickness=0, bd=0)
        self.scrollbar = tk.Scrollbar(outer, orient="vertical",
                                       command=self.canvas.yview)
        self.scrollable_frame = tk.Frame(self.canvas, bg=BG_ROOT)

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )
        self._cw = self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.bind("<Configure>",
                         lambda e: self.canvas.itemconfig(self._cw, width=e.width))
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.canvas.pack(side="left",  fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")
        self.root.bind_all("<MouseWheel>", self._on_mousewheel)

    def _hacer_boton_accion(self, parent, texto, bg, fg, cmd):
        btn = tk.Button(parent, text=texto, font=("Segoe UI", 8, "bold"),
                        bg=bg, fg=fg, relief="flat", padx=8, pady=4,
                        activebackground="#333", activeforeground="white",
                        cursor="hand2", command=cmd)
        btn.bind("<Enter>", lambda e, b=btn: b.config(bg="#2e2e2e"))
        btn.bind("<Leave>", lambda e, b=btn, c=bg: b.config(bg=c))
        return btn

    # ── GIT ───────────────────────────────────
    def _detectar_portable_git(self):
        """Busca git.exe ejecutable en varias ubicaciones del USB.
        Prioriza mingw64/bin/git.exe (binario real) sobre cmd/git.exe (lanzador)."""
        unidad = os.path.splitdrive(self.base_dir)[0]  # p.ej. "E:"
        raices = [
            os.path.join(self.base_dir, "..", "PortableGit"),
            os.path.join(unidad, os.sep, "PortableGit"),
            os.path.join(self.base_dir, "..", "..", "PortableGit"),
        ]
        # mingw64/bin/git.exe es el binario real; cmd/git.exe es un lanzador
        # que puede fallar con WinError 2 si el entorno no está preparado
        subcarpetas = [
            os.path.join("mingw64", "bin", "git.exe"),
            os.path.join("cmd", "git.exe"),
            os.path.join("bin", "git.exe"),
        ]
        for raiz in raices:
            for sub in subcarpetas:
                ruta = os.path.normpath(os.path.join(raiz, sub))
                if os.path.exists(ruta):
                    return ruta
        return None  # Fallback al git del sistema

    def _entorno_git(self):
        """Entorno con PATH y HOME correctos para PortableGit.
        Usa un .gitconfig propio en el USB para evitar problemas de ownership
        y no depender del usuario de Windows."""
        env = os.environ.copy()
        if self.ruta_git and os.path.exists(self.ruta_git):
            git_dir  = os.path.dirname(self.ruta_git)
            if os.path.basename(os.path.dirname(git_dir)).lower() == "mingw64":
                git_root = os.path.normpath(os.path.join(git_dir, "..", ".."))
            else:
                git_root = os.path.normpath(os.path.join(git_dir, ".."))
            extra = os.pathsep.join([
                os.path.join(git_root, "mingw64", "bin"),
                os.path.join(git_root, "cmd"),
                os.path.join(git_root, "bin"),
                os.path.join(git_root, "usr", "bin"),
                git_dir,
            ])
            env["PATH"] = extra + os.pathsep + env.get("PATH", "")
            exec_path = os.path.join(git_root, "mingw64", "libexec", "git-core")
            if os.path.isdir(exec_path):
                env["GIT_EXEC_PATH"] = exec_path

        # .gitconfig propio en el USB → independiente del usuario de Windows
        gitconfig_usb = os.path.join(self.ruta_config, ".gitconfig")
        self._asegurar_gitconfig(gitconfig_usb)
        env["GIT_CONFIG_GLOBAL"] = gitconfig_usb
        # HOME también apuntará a Config/ para evitar cualquier lectura del perfil
        env["HOME"] = self.ruta_config
        return env

    def _asegurar_gitconfig(self, ruta):
        """Crea o completa el .gitconfig del USB con safe.directory=* y user básico."""
        lineas_requeridas = {
            "[safe]": "	directory = *",
            "[credential]": f"	helper = store --file {self.ruta_creds}",
        }
        contenido = ""
        if os.path.exists(ruta):
            with open(ruta, "r", encoding="utf-8") as f:
                contenido = f.read()

        for seccion, valor in lineas_requeridas.items():
            if valor.strip() not in contenido:
                if seccion not in contenido:
                    contenido += "\n" + seccion + "\n" + valor + "\n"
                else:
                    # insertar tras la cabecera de sección
                    contenido = contenido.replace(
                        seccion, seccion + "\n" + valor, 1)

        with open(ruta, "w", encoding="utf-8") as f:
            f.write(contenido)

    def obtener_comando_git(self):
        if self.ruta_git and os.path.exists(self.ruta_git):
            return self.ruta_git
        return "git"

    def _git_run(self, args, **kwargs):
        """Ejecuta git con el entorno correcto. Nunca lanza excepción."""
        cmd = self.obtener_comando_git()
        env = self._entorno_git()
        kw = dict(creationflags=subprocess.CREATE_NO_WINDOW,
                  env=env, capture_output=True, text=True, encoding="utf-8")
        kw.update(kwargs)
        try:
            return subprocess.run([cmd] + args, **kw)
        except Exception as e:
            class _R:
                returncode = -1
                stdout = ""
                stderr = str(e)
            return _R()

    def comprobar_git_status(self):
        # 1. safe.directory local (no necesita HOME escribible)
        self._git_run(["config", "--local", "safe.directory", self.base_dir],
                      cwd=self.base_dir)
        # 2. credential helper local al repo
        self._git_run(["config", "--local", "credential.helper",
                       f"store --file {self.ruta_creds}"],
                      cwd=self.base_dir)
        # 3. fetch (puede fallar sin internet, no es fatal)
        self._git_run(["fetch"], cwd=self.base_dir)

        # 4. cambios locales pendientes
        r_status = self._git_run(["status", "--porcelain"], cwd=self.base_dir)
        if r_status.returncode != 0:
            err = (r_status.stderr or "error desconocido").strip()[:70]
            self.root.after(0, lambda m=err: self.lbl_git.config(
                text=f"✗  {m}", fg="#c0392b"))
            return
        lineas = [l for l in r_status.stdout.strip().splitlines() if l]
        num_locales = len(lineas)

        # 5. commits por descargar
        r_rev = self._git_run(["rev-list", "HEAD..origin/main", "--count"],
                               cwd=self.base_dir)
        atrasado = 0
        if r_rev.returncode == 0:
            raw = r_rev.stdout.strip()
            atrasado = int(raw) if raw.isdigit() else 0

        # 6. último commit
        commit_msg = ""
        r_log = self._git_run(["log", "-1", "--pretty=format:%s · %ar"],
                               cwd=self.base_dir)
        if r_log.returncode == 0:
            commit_msg = r_log.stdout.strip()
            for largo, corto in [
                (" seconds ago", "s"), (" second ago", "s"),
                (" minutes ago", "m"), (" minute ago", "m"),
                (" hours ago", "h"),   (" hour ago", "h"),
                (" days ago", "d"),    (" day ago", "d"),
                (" weeks ago", "w"),   (" week ago", "w"),
                (" months ago", "mo"), (" month ago", "mo"),
                (" years ago", "a"),   (" year ago", "a"),
            ]:
                commit_msg = commit_msg.replace(largo, corto)
            commit_msg = commit_msg[:55] + "…" if len(commit_msg) > 55 else commit_msg
        self.root.after(0, lambda m=commit_msg:
                        self.lbl_commit.config(text=m))

        # 7. actualizar UI según estado
        if num_locales > 0:
            self.root.after(0, lambda: self.lbl_git.config(
                text=f"⬆  {num_locales} pendientes de subida", fg="#ff8c00"))
            self.root.after(0, lambda: self.btn_push.config(
                bg="#7a3800", fg="#ffb347", state="normal",
                text=f"☁ SUBIR ({num_locales})"))
            self.root.after(0, lambda: self.btn_pull.config(state="normal"))
        elif atrasado > 0:
            self.root.after(0, lambda: self.lbl_git.config(
                text=f"⬇  {atrasado} en nube", fg="#4dd0e1"))
            self.root.after(0, lambda: self.btn_push.config(
                bg="#1c1c1c", fg=FG_DIM, state="disabled", text="☁ SUBIR"))
            self.root.after(0, lambda: self.btn_pull.config(
                bg="#0d3640", fg="#4dd0e1", state="normal",
                text=f"📥 DESCARGAR ({atrasado})"))
        else:
            self.root.after(0, lambda: self.lbl_git.config(
                text="✓  sincronizado", fg="#4caf50"))
            self.root.after(0, lambda: self.btn_push.config(
                bg="#1c1c1c", fg=FG_DIM, state="disabled", text="☁ SUBIR"))
            self.root.after(0, lambda: self.btn_pull.config(
                bg="#1c1c1c", fg=FG_DIM, state="disabled", text="📥 DESCARGAR"))

    def realizar_push(self):
        cmd = self.obtener_comando_git()
        env = self._entorno_git()
        mensaje = simpledialog.askstring("Subir cambios",
                                         "Mensaje del commit:", parent=self.root)
        if mensaje:
            try:
                kw = dict(cwd=self.base_dir,
                          creationflags=subprocess.CREATE_NO_WINDOW, env=env)
                subprocess.run([cmd, "config", "credential.helper",
                                f"store --file {self.ruta_creds}"], **kw)
                subprocess.run([cmd, "add", "."], check=True, **kw)
                subprocess.run([cmd, "commit", "-m", mensaje], check=True, **kw)
                res = subprocess.run([cmd, "push"], capture_output=True, text=True, **kw)
                if res.returncode == 0:
                    messagebox.showinfo("Éxito", "¡Subido a GitHub correctamente!")
                    self.actualizar_todo()
                else:
                    messagebox.showerror("Error", f"Fallo al subir:\n{res.stderr}")
            except Exception as e:
                messagebox.showerror("Error", str(e))

    def realizar_pull(self):
        cmd = self.obtener_comando_git()
        env = self._entorno_git()
        try:
            kw = dict(cwd=self.base_dir,
                      creationflags=subprocess.CREATE_NO_WINDOW, env=env)
            subprocess.run([cmd, "rebase", "--abort"], **kw)
            subprocess.run([cmd, "config", "credential.helper",
                            f"store --file {self.ruta_creds}"], **kw)
            res = subprocess.run([cmd, "pull", "--no-rebase"],
                                 capture_output=True, text=True, **kw)
            if res.returncode == 0:
                messagebox.showinfo("Éxito", "¡Archivos actualizados!")
                self.actualizar_todo()
            else:
                messagebox.showwarning("Atención",
                    f"No se pudo sincronizar.\n{res.stderr or 'Comprueba los cambios locales.'}")
        except Exception as e:
            messagebox.showerror("Error", f"Error al descargar: {e}")

    def reparar_repositorio(self):
        if messagebox.askyesno("Reparar Git",
            "Esto cancelará errores de rebase/merge y\n"
            "sincronizará el repositorio con GitHub.\n\n¿Continuar?"):
            cmd = self.obtener_comando_git()
            env = self._entorno_git()
            try:
                kw = dict(cwd=self.base_dir,
                          creationflags=subprocess.CREATE_NO_WINDOW, env=env)
                subprocess.run([cmd, "rebase", "--abort"], **kw)
                subprocess.run([cmd, "merge",  "--abort"], **kw)
                subprocess.run([cmd, "fetch", "origin"], **kw)
                res = subprocess.run([cmd, "reset", "--hard", "origin/main"],
                                     capture_output=True, text=True, **kw)
                if res.returncode == 0:
                    messagebox.showinfo("Éxito", "Repositorio reparado y actualizado.")
                    self.actualizar_todo()
                else:
                    messagebox.showerror("Error", f"No se pudo reparar:\n{res.stderr}")
            except Exception as e:
                messagebox.showerror("Error Crítico", str(e))

    # ── UI: BARRA DE ESTADO ───────────────────
    def actualizar_barra_estado(self):
        es_usb = "C:" not in self.base_dir.upper()
        modo = "USB · PORTABLE" if es_usb else "PC LOCAL"
        if es_usb:
            if self.ruta_git and os.path.exists(self.ruta_git):
                modo += "  ✓ git"
            else:
                modo += "  ✗ git no encontrado"
        self.lbl_modo.config(text=f"📍  {modo}")
        self.lbl_info.config(text=obtener_info_sistema())

    # ── UI: SCRIPTS ───────────────────────────
    def cargar_scripts(self):
        for w in self.scrollable_frame.winfo_children():
            w.destroy()

        termino = self.entry_busqueda.get().lower()
        if termino in ("buscar script…", ""):
            termino = ""

        ignorar    = {"lanzador.bat", "iniciar.vbs", "generar_pptx.py", "favoritos.txt"}
        script_act = os.path.basename(__file__)

        try:
            archivos = [f for f in os.listdir(self.base_dir)
                        if f.lower().endswith(('.py', '.bat', '.pyw'))
                        and f not in ignorar
                        and f != script_act]
        except Exception as e:
            tk.Label(self.scrollable_frame, text=f"Error: {e}",
                     fg="#ff4d4d", bg=BG_ROOT).grid(row=0, column=0, pady=20)
            return

        cats = {cat: [] for cat in COLORES.keys()}

        for f in archivos:
            if termino and termino not in f.lower():
                continue
            cats[self.clasificar(f)].append(f)

        self.scrollable_frame.grid_columnconfigure((0, 1), weight=1)
        fila = 0

        for cat, lista in cats.items():
            if not lista:
                continue
            abierta = True if termino else self.estados_carpetas.get(cat, False)
            color   = COLORES[cat]

            # ── Cabecera de categoría ──
            hdr = tk.Frame(self.scrollable_frame, bg=BG_ROOT)
            hdr.grid(row=fila, column=0, columnspan=2,
                     sticky="ew", padx=0, pady=(12, 2))
            hdr.grid_columnconfigure(1, weight=1)

            hacer_icono_carpeta(hdr, color, BG_ROOT).grid(row=0, column=0, padx=(4, 6))

            btn_cat = tk.Button(
                hdr,
                text=f"{cat}  [{len(lista)}]{'   ▸' if not abierta else '   ▾'}",
                font=("Segoe UI", 11, "bold"),
                fg="#e0e0e0", bg=BG_ROOT, relief="flat", anchor="w",
                activeforeground="#ffffff", activebackground=BG_ROOT,
                cursor="hand2",
                command=lambda c=cat: self.toggle_carpeta(c)
            )
            btn_cat.grid(row=0, column=1, sticky="ew")
            fila += 1
            if abierta:
                for i, f in enumerate(sorted(lista)):
                    r, c = fila + (i // 2), i % 2
                    self.crear_boton(os.path.join(self.base_dir, f),
                                             r, c, color, f)
                fila += (len(lista) + 1) // 2

    def crear_boton(self, ruta, f, c, color, nombre_archivo):
        nombre = (os.path.splitext(os.path.basename(ruta))[0]
                  .replace("_", " ")
                  .capitalize())

        btn = tk.Button(
            self.scrollable_frame,
            text=nombre,
            font=("Segoe UI", 10, "bold"),
            bg=BG_CARD, fg="#cccccc",
            relief="flat", height=2,
            activebackground=BG_CARD_HOV,
            activeforeground="#ffffff",
            cursor="hand2",
            command=lambda: ejecutar_herramienta(ruta, self.root)
        )
        btn.grid(row=f, column=c, sticky="nsew", padx=4, pady=3)
        btn.bind("<Enter>", lambda e, b=btn: b.config(bg=BG_CARD_HOV))
        btn.bind("<Leave>", lambda e, b=btn: b.config(bg=BG_CARD))
        btn.bind("<Button-3>", lambda e, n=nombre_archivo: self.toggle_favorito(n))

    def clasificar(self, nombre):
        n = nombre.lower()
        if nombre in self.favoritos:
            return "FAVORITOS"
        if any(x in n for x in ["expulsar", "pc", "test", "usb", "windows",
                                  "imports", "limpieza", "metadatos", "borrar", "temp",
                                  "cerrar", "portapapeles", "organizador"]):
            return "SISTEMA"
        if any(x in n for x in ["pdf", "informe", "word", "doc", "tabla", "format", "docx"]):
            return "PDF/DOCX"
        if any(x in n for x in ["examen", "apuntes", "resumen", "presentacion", "notas"]):
            return "CLASES"
        if any(x in n for x in ["video", "audio", "caratula", "youtube",
                                  "voz", "mezclador"]):
            return "AUDIO & VÍDEO"
        if any(x in n for x in ["horario", "diligencia", "gestion",
                                  "certificado", "calculador", "diploma"]):
            return "ADMINISTRACIÓN"
        if any(x in n for x in ["bingo", "crono", "game", "pasapalabra",
                                  "picker", "clase", "qr", "juego"]):
            return "AULA"
        return "OTROS"

    # ── ACCIONES ──────────────────────────────
    def actualizar_todo(self):
        self.actualizar_barra_estado()
        self.cargar_scripts()
        threading.Thread(target=self.comprobar_git_status, daemon=True).start()

    def toggle_carpeta(self, cat):
        self.estados_carpetas[cat] = not self.estados_carpetas[cat]
        self.cargar_scripts()

    def filtrar_scripts(self, e):
        self.cargar_scripts()

    def toggle_favorito(self, n):
        if n in self.favoritos:
            self.favoritos.remove(n)
        else:
            self.favoritos.append(n)
        guardar_favoritos(self.favoritos)
        self.cargar_scripts()

    def _on_mousewheel(self, event):
        self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def _on_search_focus(self, e):
        if self.entry_busqueda.get() == "Buscar script…":
            self.entry_busqueda.delete(0, "end")
            self.entry_busqueda.config(fg=FG_MAIN)

    def _on_search_unfocus(self, e):
        if not self.entry_busqueda.get():
            self.entry_busqueda.insert(0, "Buscar script…")
            self.entry_busqueda.config(fg=FG_DIM)

    def _limpiar_busqueda(self):
        self.entry_busqueda.delete(0, "end")
        self.entry_busqueda.insert(0, "Buscar script…")
        self.entry_busqueda.config(fg=FG_DIM)
        self.cargar_scripts()


# ─────────────────────────────────────────────
if __name__ == "__main__":
    root = tk.Tk()
    app = MenuFinalPerfecto(root)
    root.mainloop()
