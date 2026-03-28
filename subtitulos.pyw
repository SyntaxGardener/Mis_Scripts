# SubtitleGen  — subtitulos.pyw
# Requiere: pip install openai-whisper deep-translator   |   ffmpeg en el PATH del sistema o junto al .pyw
# ─────────────────────────────────────────────────────────────────────────────

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, colorchooser
import threading
import subprocess
import os
import sys
import re
import tempfile

# Añadir la carpeta del propio script al PATH para que ffmpeg se encuentre
# aunque no esté instalado en el sistema (ej. entorno portable en USB)
_script_dir = os.path.dirname(os.path.abspath(__file__))
if _script_dir not in os.environ.get("PATH", "").split(os.pathsep):
    os.environ["PATH"] = _script_dir + os.pathsep + os.environ.get("PATH", "")

# ── Paleta ────────────────────────────────────────────────────────────────────
BG        = "#cfd3dc"
BG2       = "#b8bdc9"
BG3       = "#dde1e8"
FG        = "#1c2030"
FG2       = "#444c60"
ACCENT    = "#3a5a8c"
ACCENT_LT = "#5a80b8"
BTN_BG    = "#3a5a8c"
BTN_FG    = "#f0f4ff"
SEP_CLR   = "#9aa1b3"
LOG_BG    = "#1a1e2b"
LOG_FG    = "#7ec98a"
EDIT_BG   = "#1e2235"
EDIT_SEL  = "#2a3a5c"
# ──────────────────────────────────────────────────────────────────────────────

LANGUAGES = {
    "Auto-detectar": None,
    "English":        "en",
    "Español":        "es",
    "Português":      "pt",
    "Deutsch":        "de",
    "Français":       "fr",
    "Italiano":       "it",
    "العربية":        "ar",
    "Українська":     "uk",
    "Русский":        "ru",
    "中文":            "zh",
    "日本語":          "ja",
    "한국어":          "ko",
    "Polski":         "pl",
    "Nederlands":     "nl",
    "Türkçe":         "tr",
    "हिन्दी":         "hi",
}

# Idiomas destino para traducción (nombre → código Google Translate)
TRANS_LANGUAGES = {
    "English":   "en",
    "Español":   "es",
    "Português": "pt",
    "Deutsch":   "de",
    "Français":  "fr",
    "Italiano":  "it",
    "العربية":   "ar",
    "Русский":   "ru",
    "中文":       "zh-CN",
    "日本語":     "ja",
    "한국어":     "ko",
    "Polski":    "pl",
    "Nederlands":"nl",
    "Türkçe":    "tr",
    "हिन्दी":    "hi",
    "Català":    "ca",
    "Galego":    "gl",
    "Euskara":   "eu",
    "Українська":"uk",
    "Română":    "ro",
    "Čeština":   "cs",
    "Svenska":   "sv",
    "Norsk":     "no",
    "Suomi":     "fi",
    "Magyar":    "hu",
}

MODELS    = ["tiny", "base", "small", "medium", "large", "large-v2", "large-v3"]
# Valores de Alignment ASS: 2=abajo-centro, 5=centro, 8=arriba-centro
# MarginV controla la distancia al borde correspondiente
POSITIONS = {"Abajo": 2, "Centro": 5, "Arriba": 8}
POS_MARGIN = {"Abajo": 20, "Centro": 0, "Arriba": 20}  # margen al borde
WIN_W     = 700
WIN_H     = 650   # altura fija — las pestañas caben sin scroll


# ══════════════════════════════════════════════════════════════════════════════
#  Helpers SRT
# ══════════════════════════════════════════════════════════════════════════════

def parse_srt(path: str) -> list:
    """Devuelve lista de dicts {idx, start, end, text} desde un .srt."""
    entries = []
    with open(path, encoding="utf-8", errors="replace") as f:
        content = f.read()
    blocks = re.split(r"\n{2,}", content.strip())
    for block in blocks:
        lines = block.strip().splitlines()
        if len(lines) < 3:
            continue
        try:
            idx = int(lines[0].strip())
            times = lines[1].strip()
            text = " ".join(lines[2:]).strip()
            m = re.match(
                r"(\d{2}:\d{2}:\d{2},\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2},\d{3})",
                times)
            if m:
                entries.append({"idx": idx, "start": m.group(1),
                                 "end": m.group(2), "text": text})
        except (ValueError, IndexError):
            continue
    return entries


def write_srt_from_entries(entries: list, path: str):
    def norm_time(t):
        return t.replace(".", ",") if "." in t else t
    with open(path, "w", encoding="utf-8") as f:
        for i, e in enumerate(entries, 1):
            f.write(f"{i}\n{norm_time(e['start'])} --> {norm_time(e['end'])}\n"
                    f"{e['text'].strip()}\n\n")


def srt_time_to_seconds(t: str) -> float:
    t = t.replace(",", ".")
    h, m, s = t.split(":")
    return int(h) * 3600 + int(m) * 60 + float(s)


# ══════════════════════════════════════════════════════════════════════════════
#  Editor de subtítulos con vídeo
# ══════════════════════════════════════════════════════════════════════════════

class SubtitleEditor(tk.Toplevel):
    """Ventana de edición de subtítulos con preview de vídeo (ffplay)."""

    COLS = ("idx", "inicio", "fin", "texto")
    COL_W = (45, 115, 115, 340)

    def __init__(self, master, srt_path: str, video_path: str = ""):
        super().__init__(master)
        self.title("✏️  Editor de subtítulos")
        self.configure(bg=BG)
        self.resizable(True, True)
        self.geometry("700x540")

        self.srt_path   = srt_path
        self.video_path = video_path
        self.entries    = []          # lista de dicts
        self._ffplay_proc = None      # proceso ffplay activo

        self._build_ui()
        self._load_srt()
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # ── UI ───────────────────────────────────────────────────────────────────

    def _build_ui(self):
        # Barra superior
        top = tk.Frame(self, bg=ACCENT, pady=6, padx=10)
        top.pack(fill=tk.X)
        tk.Label(top, text="✏️  Editor de subtítulos",
                 font=("Segoe UI", 12, "bold"),
                 bg=ACCENT, fg=BTN_FG).pack(side=tk.LEFT)
        if self.video_path:
            tk.Label(top, text=os.path.basename(self.video_path),
                     font=("Segoe UI", 8), bg=ACCENT, fg="#a8c4f0").pack(
                side=tk.RIGHT, padx=4)

        # Instrucciones
        tk.Label(self,
                 text="  Doble clic en una celda para editar · "
                      "Selecciona una fila y pulsa ▶ para saltar al momento del vídeo",
                 bg=BG, fg=FG2, font=("Segoe UI", 8), anchor=tk.W
                 ).pack(fill=tk.X, padx=8, pady=(4, 0))

        # ── Tabla ────────────────────────────────────────────────────────────
        tbl_frame = tk.Frame(self, bg=BG)
        tbl_frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=6)

        style = ttk.Style()
        style.configure("Sub.Treeview",
                        background=EDIT_BG, foreground="#c8d0e8",
                        fieldbackground=EDIT_BG,
                        font=("Consolas", 9), rowheight=22)
        style.configure("Sub.Treeview.Heading",
                        background=BG2, foreground=FG,
                        font=("Segoe UI", 8, "bold"))
        style.map("Sub.Treeview",
                  background=[("selected", EDIT_SEL)],
                  foreground=[("selected", "#ffffff")])

        self.tree = ttk.Treeview(tbl_frame, columns=self.COLS,
                                  show="headings", style="Sub.Treeview",
                                  selectmode="browse")
        heads = ("#", "Inicio", "Fin", "Texto")
        for col, head, w in zip(self.COLS, heads, self.COL_W):
            self.tree.heading(col, text=head)
            self.tree.column(col, width=w,
                             stretch=(col == "texto"), anchor=tk.W)

        vsb = ttk.Scrollbar(tbl_frame, orient=tk.VERTICAL,
                            command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.pack(fill=tk.BOTH, expand=True)

        self.tree.bind("<Double-1>", self._on_double_click)

        # ── Barra de botones ─────────────────────────────────────────────────
        bar = tk.Frame(self, bg=BG2, padx=8, pady=6)
        bar.pack(fill=tk.X)

        def btn(text, cmd, fg=BTN_FG, bg=BTN_BG):
            return tk.Button(bar, text=text, command=cmd,
                             bg=bg, fg=fg,
                             font=("Segoe UI", 8, "bold"),
                             relief=tk.FLAT, cursor="hand2",
                             activebackground=ACCENT_LT,
                             activeforeground=BTN_FG,
                             padx=8, pady=3)

        btn("▶  Ver en vídeo", self._preview_selected).pack(side=tk.LEFT, padx=3)
        btn("➕ Añadir fila",  self._add_row,
            bg="#2d6a2d").pack(side=tk.LEFT, padx=3)
        btn("🗑  Eliminar fila", self._delete_row,
            bg="#7a2020").pack(side=tk.LEFT, padx=3)
        btn("⬆ Subir", self._move_up).pack(side=tk.LEFT, padx=2)
        btn("⬇ Bajar", self._move_down).pack(side=tk.LEFT, padx=2)
        btn("🔗 Unir con siguiente", self._merge_with_next,
            bg="#4a3a7a").pack(side=tk.LEFT, padx=3)

        btn("💾  Guardar .srt", self._save_srt,
            bg="#1a5c3a").pack(side=tk.RIGHT, padx=3)
        btn("💾  Guardar como…", self._save_srt_as,
            bg="#1a4a5c").pack(side=tk.RIGHT, padx=3)

    # ── Carga ─────────────────────────────────────────────────────────────────

    def _load_srt(self):
        if not self.srt_path or not os.path.isfile(self.srt_path):
            return
        self.entries = parse_srt(self.srt_path)
        self._refresh_tree()

    def _refresh_tree(self, select_iid=None):
        self.tree.delete(*self.tree.get_children())
        for e in self.entries:
            iid = self.tree.insert("", tk.END,
                                   values=(e["idx"], e["start"],
                                           e["end"], e["text"]))
            if select_iid and e["idx"] == select_iid:
                self.tree.selection_set(iid)
                self.tree.see(iid)

    # ── Edición inline ────────────────────────────────────────────────────────

    def _on_double_click(self, event):
        region = self.tree.identify("region", event.x, event.y)
        if region != "cell":
            return
        row_id = self.tree.identify_row(event.y)
        col_id = self.tree.identify_column(event.x)
        if not row_id:
            return
        col_idx = int(col_id.replace("#", "")) - 1
        col_name = self.COLS[col_idx]
        if col_name == "idx":
            return   # no editar el número

        # Obtener bbox de la celda
        bbox = self.tree.bbox(row_id, col_id)
        if not bbox:
            return
        x, y, w, h = bbox
        current_val = self.tree.set(row_id, col_name)

        entry_var = tk.StringVar(value=current_val)
        editor = tk.Entry(self.tree, textvariable=entry_var,
                          bg="#2a3050", fg="#ffffff",
                          insertbackground="#ffffff",
                          relief=tk.FLAT, font=("Consolas", 9),
                          bd=0)
        editor.place(x=x, y=y, width=max(w, 200), height=h)
        editor.focus_set()
        editor.select_range(0, tk.END)

        def commit(_=None):
            new_val = entry_var.get().strip()
            self.tree.set(row_id, col_name, new_val)
            # Actualizar entries
            idx_val = int(self.tree.set(row_id, "idx"))
            for e in self.entries:
                if e["idx"] == idx_val:
                    e[col_name if col_name != "inicio" else "start"
                      if col_name == "inicio" else col_name] = new_val
                    # Mapear nombres de columna → clave dict
                    key_map = {"inicio": "start", "fin": "end",
                               "texto": "text", "idx": "idx"}
                    e[key_map[col_name]] = new_val
                    break
            editor.destroy()

        def cancel(_=None):
            editor.destroy()

        editor.bind("<Return>",  commit)
        editor.bind("<Tab>",     commit)
        editor.bind("<Escape>",  cancel)
        editor.bind("<FocusOut>", commit)

    # ── Operaciones de fila ───────────────────────────────────────────────────

    def _selected_entry_idx(self):
        sel = self.tree.selection()
        if not sel:
            return None, None
        row_id = sel[0]
        idx_val = int(self.tree.set(row_id, "idx"))
        for i, e in enumerate(self.entries):
            if e["idx"] == idx_val:
                return i, row_id
        return None, None

    def _add_row(self):
        i, _ = self._selected_entry_idx()
        new_idx = (self.entries[-1]["idx"] + 1) if self.entries else 1
        new_entry = {"idx": new_idx, "start": "00:00:00,000",
                     "end": "00:00:01,000", "text": "Nuevo subtítulo"}
        if i is None:
            self.entries.append(new_entry)
        else:
            self.entries.insert(i + 1, new_entry)
        self._renumber()
        self._refresh_tree()

    def _delete_row(self):
        i, _ = self._selected_entry_idx()
        if i is None:
            return
        if not messagebox.askyesno("Eliminar", "¿Eliminar este subtítulo?",
                                   parent=self):
            return
        self.entries.pop(i)
        self._renumber()
        self._refresh_tree()

    def _move_up(self):
        i, _ = self._selected_entry_idx()
        if i is None or i == 0:
            return
        self.entries[i], self.entries[i-1] = self.entries[i-1], self.entries[i]
        self._renumber()
        sel_idx = self.entries[i-1]["idx"]
        self._refresh_tree(select_iid=sel_idx)

    def _move_down(self):
        i, _ = self._selected_entry_idx()
        if i is None or i >= len(self.entries) - 1:
            return
        self.entries[i], self.entries[i+1] = self.entries[i+1], self.entries[i]
        self._renumber()
        sel_idx = self.entries[i+1]["idx"]
        self._refresh_tree(select_iid=sel_idx)

    def _renumber(self):
        for n, e in enumerate(self.entries, 1):
            e["idx"] = n

    def _merge_with_next(self):
        i, _ = self._selected_entry_idx()
        if i is None or i >= len(self.entries) - 1:
            messagebox.showwarning("Unir",
                                   "Selecciona una fila que tenga otra debajo.",
                                   parent=self)
            return
        a = self.entries[i]
        b = self.entries[i + 1]
        a["text"] = (a["text"].rstrip() + " " + b["text"].lstrip()).strip()
        a["end"]  = b["end"]
        self.entries.pop(i + 1)
        self._renumber()
        self._refresh_tree(select_iid=self.entries[i]["idx"])

    # ── Preview vídeo ─────────────────────────────────────────────────────────

    def _preview_selected(self):
        if not self.video_path or not os.path.isfile(self.video_path):
            messagebox.showwarning("Sin vídeo",
                                   "No se especificó un vídeo de entrada.\n"
                                   "Selecciónalo en la ventana principal primero.",
                                   parent=self)
            return
        i, _ = self._selected_entry_idx()
        if i is None:
            messagebox.showwarning("Selección",
                                   "Selecciona una fila para previsualizar.",
                                   parent=self)
            return
        entry   = self.entries[i]
        t_start = srt_time_to_seconds(entry["start"])
        t_end   = srt_time_to_seconds(entry["end"])
        # Empezar 1 s antes para contexto
        t_from  = max(0.0, t_start - 1.0)
        duration = t_end - t_start + 2.0

        # Escribir un .srt temporal con solo ese fragmento
        tmp_srt = tempfile.NamedTemporaryFile(
            suffix=".srt", delete=False, mode="w", encoding="utf-8")
        tmp_srt.write(
            f"1\n{entry['start']} --> {entry['end']}\n{entry['text']}\n\n")
        tmp_srt.close()

        # Cerrar ffplay anterior si sigue abierto
        if self._ffplay_proc and self._ffplay_proc.poll() is None:
            self._ffplay_proc.terminate()

        cmd = [
            "ffplay", "-autoexit",
            "-ss", str(t_from),
            "-t", str(duration),
            "-vf", f"subtitles='{self._escape_path(tmp_srt.name)}'",
            self.video_path
        ]

        try:
            kw = {}
            if sys.platform == "win32":
                kw["creationflags"] = subprocess.CREATE_NO_WINDOW
            self._ffplay_proc = subprocess.Popen(
                cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, **kw)
            threading.Thread(
                target=self._cleanup_tmp, args=(tmp_srt.name,), daemon=True
            ).start()
        except FileNotFoundError:
            os.unlink(tmp_srt.name)
            messagebox.showerror("Error",
                                 "'ffplay' no encontrado.\n"
                                 "Asegúrate de que ffmpeg (con ffplay) está en el PATH.",
                                 parent=self)

    def _cleanup_tmp(self, path):
        if self._ffplay_proc:
            self._ffplay_proc.wait()
        try:
            os.unlink(path)
        except OSError:
            pass

    @staticmethod
    def _escape_path(path: str) -> str:
        p = path.replace("\\", "/")
        if len(p) >= 2 and p[1] == ":":
            p = p[0] + "\\:" + p[2:]
        return p.replace("'", "\\'")

    # ── Guardar ───────────────────────────────────────────────────────────────

    def _save_srt(self):
        if not self.srt_path:
            self._save_srt_as()
            return
        write_srt_from_entries(self.entries, self.srt_path)
        messagebox.showinfo("Guardado",
                            f"Subtítulos guardados en:\n{self.srt_path}",
                            parent=self)

    def _save_srt_as(self):
        p = filedialog.asksaveasfilename(
            parent=self,
            defaultextension=".srt",
            filetypes=[("SubRip", "*.srt"), ("Todos", "*.*")],
            initialfile=os.path.basename(self.srt_path or "subtitulos.srt"))
        if p:
            self.srt_path = p
            write_srt_from_entries(self.entries, p)
            messagebox.showinfo("Guardado",
                                f"Subtítulos guardados en:\n{p}",
                                parent=self)

    def _on_close(self):
        if self._ffplay_proc and self._ffplay_proc.poll() is None:
            self._ffplay_proc.terminate()
        self.destroy()


# ══════════════════════════════════════════════════════════════════════════════
#  Aplicación principal
# ══════════════════════════════════════════════════════════════════════════════

class SubtitleGen:

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("SubtitleGen ~ Generación, Traducción e Incrustación de Subtítulos")
        self.root.configure(bg=BG)
        self.root.resizable(True, False)

        # ── Variables ────────────────────────────────────────────────────────
        self.video_path       = tk.StringVar()
        self.srt_path         = tk.StringVar()
        self.output_folder    = tk.StringVar()
        self.out_name         = tk.StringVar()
        self.language         = tk.StringVar(value="Auto-detectar")
        self.model            = tk.StringVar(value="small")
        self.font_size        = tk.IntVar(value=24)
        self.font_color       = tk.StringVar(value="#FFFFFF")
        self.position         = tk.StringVar(value="Abajo")
        self.open_folder      = tk.BooleanVar(value=True)
        self.max_seg_duration = tk.DoubleVar(value=4.0)
        # Traducción
        self.trans_lang       = tk.StringVar(value="Español")
        self.trans_srt_path   = tk.StringVar()
        # Incrustación dual
        self.dual_srt_bottom  = tk.StringVar()   # .srt parte inferior
        self.dual_srt_top     = tk.StringVar()   # .srt parte superior
        self.font_color_top   = tk.StringVar(value="#FFFF00")  # amarillo por defecto
        self._busy            = False

        self._build_ui()
        self.root.update_idletasks()
        self._place_window()

    # ── Layout ────────────────────────────────────────────────────────────────

    def _place_window(self):
        sw = self.root.winfo_screenwidth()
        self.root.geometry(f"{WIN_W}x{WIN_H}+{(sw - WIN_W) // 2}+5")

    def _build_ui(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TCombobox",
                        fieldbackground=BG3, background=BG3,
                        foreground=FG, selectbackground=ACCENT,
                        selectforeground=BTN_FG)
        style.configure("Horizontal.TProgressbar",
                        troughcolor=BG2, background=ACCENT, thickness=6)
        style.configure("TSeparator", background=SEP_CLR)
        # Estilo de pestañas
        style.configure("App.TNotebook",
                        background=BG, tabmargins=[2, 4, 0, 0])
        style.configure("App.TNotebook.Tab",
                        background=BG2, foreground=FG,
                        font=("Segoe UI", 9, "bold"),
                        padding=[12, 5])
        style.map("App.TNotebook.Tab",
                  background=[("selected", ACCENT)],
                  foreground=[("selected", BTN_FG)])

        root_frame = tk.Frame(self.root, bg=BG)
        root_frame.pack(fill=tk.BOTH, expand=True)

        # ── Cabecera fija ────────────────────────────────────────────────────
        hdr = tk.Frame(root_frame, bg=ACCENT, pady=6, padx=12)
        hdr.pack(fill=tk.X)
        tk.Label(hdr, text="🎬  SubtitleGen",
                 font=("Segoe UI", 13, "bold"),
                 bg=ACCENT, fg=BTN_FG).pack(side=tk.LEFT)
        tk.Label(hdr, text="Whisper + FFmpeg",
                 font=("Segoe UI", 8),
                 bg=ACCENT, fg="#a8c4f0").pack(side=tk.RIGHT, padx=4)

        # Vídeo de entrada — siempre visible encima de las pestañas
        vid_frame = tk.Frame(root_frame, bg=BG, padx=14, pady=6)
        vid_frame.pack(fill=tk.X)
        self._section(vid_frame, "📂  Vídeo de entrada")
        self._file_row(vid_frame, self.video_path, "Examinar…",
                       self._browse_video,
                       ftype=[("Vídeo", "*.mp4 *.mkv *.avi *.mov *.webm *.flv *.wmv *.ts"),
                               ("Todos", "*.*")])

        # ── Notebook ─────────────────────────────────────────────────────────
        nb = ttk.Notebook(root_frame, style="App.TNotebook")
        nb.pack(fill=tk.BOTH, expand=True, padx=10, pady=(4, 0))

        t1 = tk.Frame(nb, bg=BG, padx=14, pady=10)
        t2 = tk.Frame(nb, bg=BG, padx=14, pady=10)
        # t3 usa Canvas+scrollbar para que el log no quede tapado
        t3_outer = tk.Frame(nb, bg=BG)
        nb.add(t1, text="  🗣️  Generar  ")
        nb.add(t2, text="  🌐  Traducir  ")
        nb.add(t3_outer, text="  🔥  Incrustar  ")

        # Canvas scrollable que contiene todo el contenido de t3
        t3_canvas = tk.Canvas(t3_outer, bg=BG, highlightthickness=0)
        t3_vsb = ttk.Scrollbar(t3_outer, orient=tk.VERTICAL,
                                command=t3_canvas.yview)
        t3_canvas.configure(yscrollcommand=t3_vsb.set)
        t3_vsb.pack(side=tk.RIGHT, fill=tk.Y)
        t3_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        t3 = tk.Frame(t3_canvas, bg=BG, padx=14, pady=10)
        t3_win = t3_canvas.create_window((0, 0), window=t3, anchor="nw")

        def _t3_configure(event):
            t3_canvas.configure(scrollregion=t3_canvas.bbox("all"))

        def _t3_canvas_resize(event):
            t3_canvas.itemconfig(t3_win, width=event.width)

        t3.bind("<Configure>", _t3_configure)
        t3_canvas.bind("<Configure>", _t3_canvas_resize)

        # Scroll con rueda del ratón sobre t3
        def _t3_mousewheel(event):
            t3_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        t3_canvas.bind_all("<MouseWheel>", _t3_mousewheel)

        # ════════════════════════════════════════════
        # TAB 1 — Generar .srt
        # ════════════════════════════════════════════
        self._section(t1, "🗣️  Generar subtítulos (.srt) con Whisper")

        row_w = tk.Frame(t1, bg=BG)
        row_w.pack(fill=tk.X, pady=3)
        self._lbl(row_w, "Idioma:", side=tk.LEFT)
        ttk.Combobox(row_w, textvariable=self.language,
                     values=list(LANGUAGES.keys()),
                     state="readonly", width=16).pack(side=tk.LEFT, padx=(2, 14))
        self._lbl(row_w, "Modelo:", side=tk.LEFT)
        ttk.Combobox(row_w, textvariable=self.model,
                     values=MODELS, state="readonly", width=10).pack(side=tk.LEFT, padx=2)

        row_d = tk.Frame(t1, bg=BG)
        row_d.pack(fill=tk.X, pady=3)
        self._lbl(row_d, "Duración máx. segmento (s):", side=tk.LEFT)
        tk.Spinbox(row_d, from_=1.0, to=15.0, increment=0.5,
                   textvariable=self.max_seg_duration,
                   format="%.1f", width=5,
                   bg=BG3, fg=FG, relief=tk.FLAT,
                   font=("Segoe UI", 9),
                   buttonbackground=BG2).pack(side=tk.LEFT, padx=(3, 10))
        tk.Label(row_d, text="(2.5-4 canción / 4-5 diálogo / 5-6 documental)",
                 bg=BG, fg=FG2, font=("Segoe UI", 8)).pack(side=tk.LEFT)

        srt_row = tk.Frame(t1, bg=BG)
        srt_row.pack(fill=tk.X, pady=3)
        self._lbl(srt_row, "Archivo .srt:", side=tk.LEFT)
        tk.Entry(srt_row, textvariable=self.srt_path,
                 bg=BG3, fg=FG, relief=tk.FLAT,
                 font=("Segoe UI", 9)).pack(side=tk.LEFT, fill=tk.X,
                                             expand=True, ipady=3, padx=(4, 4))
        self._btn(srt_row, "Elegir .srt", self._browse_srt).pack(side=tk.RIGHT)

        self._big_btn(t1, "⚡  Generar .srt desde el vídeo", self._start_generate)

        edit_row = tk.Frame(t1, bg=BG)
        edit_row.pack(fill=tk.X, pady=(2, 0))
        self._btn(edit_row, "✏️  Abrir editor de subtítulos",
                  self._open_editor).pack(side=tk.LEFT)
        tk.Label(edit_row,
                 text="← edita y previsualiza el .srt antes de incrustar",
                 bg=BG, fg=FG2, font=("Segoe UI", 8)).pack(side=tk.LEFT, padx=6)

        # ════════════════════════════════════════════
        # TAB 2 — Traducir .srt
        # ════════════════════════════════════════════
        self._section(t2, "🌐  Traducir subtítulos (.srt)")

        trans_frame = tk.Frame(t2, bg=BG2, padx=10, pady=10)
        trans_frame.pack(fill=tk.X, pady=6)

        tr1 = tk.Frame(trans_frame, bg=BG2)
        tr1.pack(fill=tk.X, pady=2)
        self._lbl(tr1, "Idioma destino:", side=tk.LEFT, parent_bg=BG2)
        ttk.Combobox(tr1, textvariable=self.trans_lang,
                     values=list(TRANS_LANGUAGES.keys()),
                     state="readonly", width=14).pack(side=tk.LEFT, padx=(4, 16))
        tk.Label(tr1,
                 text="(usa el .srt de la pestaña Generar como origen)",
                 bg=BG2, fg=FG2, font=("Segoe UI", 8)).pack(side=tk.LEFT)

        tr2 = tk.Frame(trans_frame, bg=BG2)
        tr2.pack(fill=tk.X, pady=(6, 0))
        self._lbl(tr2, ".srt traducido:", side=tk.LEFT, parent_bg=BG2)
        tk.Entry(tr2, textvariable=self.trans_srt_path,
                 bg=BG3, fg=FG, relief=tk.FLAT,
                 font=("Segoe UI", 9)).pack(side=tk.LEFT, fill=tk.X,
                                             expand=True, ipady=3, padx=(4, 4))
        self._btn(tr2, "Elegir…", self._browse_trans_srt).pack(side=tk.RIGHT)

        tk.Label(trans_frame,
                 text="  Requiere:  pip install deep-translator",
                 bg=BG2, fg=FG2, font=("Segoe UI", 7, "italic")).pack(
            anchor=tk.W, pady=(6, 0))

        self._big_btn(t2, "🌐  Traducir .srt", self._start_translate)

        tk.Label(t2,
                 text="Al terminar se copiará el .srt traducido\n"
                      "para la incrustación (pestaña Incrustar).",
                 bg=BG, fg=FG2, font=("Segoe UI", 8),
                 justify=tk.LEFT).pack(anchor=tk.W, pady=(4, 0))

        # ════════════════════════════════════════════
        # TAB 3 — Incrustar
        # ════════════════════════════════════════════

        # ── Carpeta y nombre de salida (común a ambos modos) ─────────────────
        self._section(t3, "📁  Salida")

        out_row = tk.Frame(t3, bg=BG)
        out_row.pack(fill=tk.X, pady=2)
        self._lbl(out_row, "Carpeta:", side=tk.LEFT)
        tk.Entry(out_row, textvariable=self.output_folder,
                 bg=BG3, fg=FG, relief=tk.FLAT,
                 font=("Segoe UI", 9)).pack(side=tk.LEFT, fill=tk.X,
                                             expand=True, ipady=3, padx=(4, 4))
        self._btn(out_row, "Elegir…", self._browse_output).pack(side=tk.RIGHT)

        nm_row = tk.Frame(t3, bg=BG)
        nm_row.pack(fill=tk.X, pady=2)
        self._lbl(nm_row, "Nombre:", side=tk.LEFT)
        tk.Entry(nm_row, textvariable=self.out_name,
                 bg=BG3, fg=FG, relief=tk.FLAT,
                 font=("Segoe UI", 9)).pack(side=tk.LEFT, fill=tk.X,
                                             expand=True, ipady=3, padx=(4, 0))

        tk.Checkbutton(t3,
                       text="Abrir carpeta de salida al terminar",
                       variable=self.open_folder,
                       bg=BG, fg=FG2, selectcolor=BG2,
                       activebackground=BG,
                       font=("Segoe UI", 9)).pack(anchor=tk.W, pady=(2, 6))

        # ── Modo A : un solo .srt ─────────────────────────────────────────────
        self._section(t3, "🅐  Un idioma")

        modoA = tk.Frame(t3, bg=BG2, padx=10, pady=8)
        modoA.pack(fill=tk.X, pady=(2, 4))

        a0 = tk.Frame(modoA, bg=BG2)
        a0.pack(fill=tk.X, pady=2)
        self._lbl(a0, ".srt:", side=tk.LEFT, parent_bg=BG2)
        tk.Entry(a0, textvariable=self.srt_path,
                 bg=BG3, fg=FG, relief=tk.FLAT,
                 font=("Segoe UI", 9)).pack(side=tk.LEFT, fill=tk.X,
                                             expand=True, ipady=3, padx=(4, 4))
        self._btn(a0, "Elegir…", self._browse_srt).pack(side=tk.RIGHT)

        a1 = tk.Frame(modoA, bg=BG2)
        a1.pack(fill=tk.X, pady=(4, 2))
        self._lbl(a1, "Tamaño:", side=tk.LEFT, parent_bg=BG2)
        tk.Spinbox(a1, from_=8, to=96, textvariable=self.font_size,
                   width=5, bg=BG3, fg=FG, relief=tk.FLAT,
                   font=("Segoe UI", 9), buttonbackground=BG2).pack(side=tk.LEFT, padx=(3, 14))
        self._lbl(a1, "Posición:", side=tk.LEFT, parent_bg=BG2)
        ttk.Combobox(a1, textvariable=self.position,
                     values=list(POSITIONS.keys()),
                     state="readonly", width=9).pack(side=tk.LEFT, padx=(3, 14))
        self._lbl(a1, "Color:", side=tk.LEFT, parent_bg=BG2)
        self.color_swatch = tk.Label(a1, bg=self.font_color.get(),
                                     width=3, height=1,
                                     relief=tk.RIDGE, cursor="hand2", bd=1)
        self.color_swatch.pack(side=tk.LEFT, padx=(3, 2))
        self.color_swatch.bind("<Button-1>", self._pick_color)
        tk.Label(a1, textvariable=self.font_color,
                 bg=BG2, fg=ACCENT, font=("Courier", 8, "bold")).pack(side=tk.LEFT, padx=2)

        self._big_btn(t3, "🎬  Incrustar (un idioma)", self._start_burn)

        # ── Modo B : dos .srt (dual) ──────────────────────────────────────────
        self._section(t3, "🅑  Dos idiomas  —  original abajo · traducción arriba")

        modoB = tk.Frame(t3, bg=BG2, padx=10, pady=8)
        modoB.pack(fill=tk.X, pady=(2, 4))

        # Fila .srt inferior
        b0 = tk.Frame(modoB, bg=BG2)
        b0.pack(fill=tk.X, pady=2)
        tk.Label(b0, text="⬇  .srt abajo  :", bg=BG2, fg=FG2,
                 font=("Segoe UI", 9, "bold")).pack(side=tk.LEFT)
        tk.Entry(b0, textvariable=self.dual_srt_bottom,
                 bg=BG3, fg=FG, relief=tk.FLAT,
                 font=("Segoe UI", 9)).pack(side=tk.LEFT, fill=tk.X,
                                             expand=True, ipady=3, padx=(4, 4))
        self._btn(b0, "Elegir…",
                  lambda: self._browse_any_srt(self.dual_srt_bottom,
                                               "Seleccionar .srt inferior")).pack(side=tk.RIGHT)

        # Fila .srt superior
        b1 = tk.Frame(modoB, bg=BG2)
        b1.pack(fill=tk.X, pady=2)
        tk.Label(b1, text="⬆  .srt arriba:", bg=BG2, fg=FG2,
                 font=("Segoe UI", 9, "bold")).pack(side=tk.LEFT)
        tk.Entry(b1, textvariable=self.dual_srt_top,
                 bg=BG3, fg=FG, relief=tk.FLAT,
                 font=("Segoe UI", 9)).pack(side=tk.LEFT, fill=tk.X,
                                             expand=True, ipady=3, padx=(4, 4))
        self._btn(b1, "Elegir…",
                  lambda: self._browse_any_srt(self.dual_srt_top,
                                               "Seleccionar .srt superior")).pack(side=tk.RIGHT)

        # Estilos duales
        b2 = tk.Frame(modoB, bg=BG2)
        b2.pack(fill=tk.X, pady=(6, 2))
        self._lbl(b2, "Tamaño:", side=tk.LEFT, parent_bg=BG2)
        tk.Spinbox(b2, from_=8, to=96, textvariable=self.font_size,
                   width=5, bg=BG3, fg=FG, relief=tk.FLAT,
                   font=("Segoe UI", 9), buttonbackground=BG2).pack(side=tk.LEFT, padx=(3, 14))

        # Color abajo
        self._lbl(b2, "Color abajo:", side=tk.LEFT, parent_bg=BG2)
        self.color_swatch_bot = tk.Label(b2, bg=self.font_color.get(),
                                          width=3, height=1,
                                          relief=tk.RIDGE, cursor="hand2", bd=1)
        self.color_swatch_bot.pack(side=tk.LEFT, padx=(3, 2))
        self.color_swatch_bot.bind("<Button-1>", self._pick_color_bot)
        tk.Label(b2, textvariable=self.font_color,
                 bg=BG2, fg=ACCENT, font=("Courier", 8, "bold")).pack(side=tk.LEFT, padx=(2, 12))

        # Color arriba
        self._lbl(b2, "Color arriba:", side=tk.LEFT, parent_bg=BG2)
        self.color_swatch_top = tk.Label(b2, bg=self.font_color_top.get(),
                                          width=3, height=1,
                                          relief=tk.RIDGE, cursor="hand2", bd=1)
        self.color_swatch_top.pack(side=tk.LEFT, padx=(3, 2))
        self.color_swatch_top.bind("<Button-1>", self._pick_color_top)
        tk.Label(b2, textvariable=self.font_color_top,
                 bg=BG2, fg=ACCENT, font=("Courier", 8, "bold")).pack(side=tk.LEFT, padx=2)

        self._big_btn(t3, "🎬🌐  Incrustar (dos idiomas)", self._start_burn_dual)

        # ── Log fijo en la parte inferior ────────────────────────────────────
        bottom = tk.Frame(root_frame, bg=BG, padx=10, pady=4)
        bottom.pack(fill=tk.X, side=tk.BOTTOM)

        self.pbar = ttk.Progressbar(bottom, mode="indeterminate",
                                    style="Horizontal.TProgressbar")
        self.pbar.pack(fill=tk.X, pady=(0, 2))

        self.status_var = tk.StringVar(value="Listo.")
        tk.Label(bottom, textvariable=self.status_var,
                 bg=BG, fg=ACCENT,
                 font=("Segoe UI", 8, "italic"),
                 anchor=tk.W).pack(fill=tk.X)

        log_hdr = tk.Frame(bottom, bg=BG)
        log_hdr.pack(fill=tk.X, pady=(4, 1))
        tk.Label(log_hdr, text="📋  Log",
                 font=("Segoe UI", 8, "bold"),
                 bg=BG, fg=ACCENT).pack(side=tk.LEFT)
        tk.Frame(log_hdr, bg=SEP_CLR, height=1).pack(
            side=tk.LEFT, fill=tk.X, expand=True, padx=(8, 0), pady=5)

        log_wrap = tk.Frame(bottom, bg=LOG_BG, bd=1, relief=tk.FLAT)
        log_wrap.pack(fill=tk.X)

        self.log = tk.Text(log_wrap, height=5,
                           bg=LOG_BG, fg=LOG_FG,
                           font=("Consolas", 8),
                           relief=tk.FLAT, wrap=tk.WORD,
                           insertbackground=LOG_FG)
        sb = tk.Scrollbar(log_wrap, command=self.log.yview,
                          troughcolor=LOG_BG, bg=BG2)
        self.log.configure(yscrollcommand=sb.set)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        self.log.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

        self._log("SubtitleGen iniciado.")
        self._log("Dependencias:  pip install openai-whisper deep-translator  |  ffmpeg en el PATH")

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _section(self, parent, title):
        f = tk.Frame(parent, bg=BG)
        f.pack(fill=tk.X, pady=(9, 2))
        tk.Label(f, text=title, font=("Segoe UI", 9, "bold"),
                 bg=BG, fg=ACCENT).pack(side=tk.LEFT)
        tk.Frame(f, bg=SEP_CLR, height=1).pack(
            side=tk.LEFT, fill=tk.X, expand=True, padx=(8, 0), pady=6)

    def _lbl(self, parent, text, side=tk.LEFT, parent_bg=None):
        tk.Label(parent, text=text,
                 bg=parent_bg or BG, fg=FG2,
                 font=("Segoe UI", 9)).pack(side=side)

    def _btn(self, parent, text, cmd):
        return tk.Button(parent, text=text, command=cmd,
                         bg=BTN_BG, fg=BTN_FG,
                         font=("Segoe UI", 8, "bold"),
                         relief=tk.FLAT, cursor="hand2",
                         activebackground=ACCENT_LT,
                         activeforeground=BTN_FG,
                         padx=8, pady=3)

    def _big_btn(self, parent, text, cmd):
        tk.Button(parent, text=text, command=cmd,
                  bg=ACCENT, fg=BTN_FG,
                  font=("Segoe UI", 10, "bold"),
                  relief=tk.FLAT, cursor="hand2",
                  activebackground=ACCENT_LT,
                  activeforeground=BTN_FG,
                  pady=6).pack(fill=tk.X, pady=5)

    def _file_row(self, parent, var, btn_txt, cmd, ftype=None):
        f = tk.Frame(parent, bg=BG)
        f.pack(fill=tk.X, pady=3)
        tk.Entry(f, textvariable=var, bg=BG3, fg=FG,
                 relief=tk.FLAT, font=("Segoe UI", 9)).pack(
            side=tk.LEFT, fill=tk.X, expand=True, ipady=3, padx=(0, 4))
        self._btn(f, btn_txt, cmd).pack(side=tk.RIGHT)

    # ── Callbacks UI ─────────────────────────────────────────────────────────

    def _browse_video(self):
        p = filedialog.askopenfilename(
            title="Seleccionar vídeo",
            filetypes=[("Vídeo", "*.mp4 *.mkv *.avi *.mov *.webm *.flv *.wmv *.ts"),
                       ("Todos", "*.*")])
        if p:
            self.video_path.set(p)
            base = os.path.splitext(p)[0]
            if not self.srt_path.get():
                self.srt_path.set(base + ".srt")
            if not self.output_folder.get():
                self.output_folder.set(os.path.dirname(p))
            if not self.out_name.get():
                self.out_name.set(
                    os.path.splitext(os.path.basename(p))[0] + "_subtitled.mp4")

    def _browse_srt(self):
        p = filedialog.askopenfilename(
            title="Seleccionar archivo .srt",
            filetypes=[("SubRip", "*.srt"), ("Todos", "*.*")])
        if p:
            self.srt_path.set(p)

    def _browse_any_srt(self, var: tk.StringVar, title: str):
        p = filedialog.askopenfilename(
            title=title,
            filetypes=[("SubRip", "*.srt"), ("Todos", "*.*")])
        if p:
            var.set(p)

    def _browse_dual_srt(self):
        pass  # ya no se usa — mantenido por compatibilidad

    def _browse_trans_srt(self):
        p = filedialog.asksaveasfilename(
            title="Guardar .srt traducido como…",
            defaultextension=".srt",
            filetypes=[("SubRip", "*.srt"), ("Todos", "*.*")])
        if p:
            self.trans_srt_path.set(p)

    def _browse_output(self):
        d = filedialog.askdirectory(title="Carpeta de salida")
        if d:
            self.output_folder.set(d)

    def _pick_color(self, _event=None):
        result = colorchooser.askcolor(
            color=self.font_color.get(), title="Color del texto")
        if result and result[1]:
            hex_c = result[1].upper()
            self.font_color.set(hex_c)
            self.color_swatch.configure(bg=hex_c)
            if hasattr(self, "color_swatch_bot"):
                self.color_swatch_bot.configure(bg=hex_c)

    def _pick_color_bot(self, _event=None):
        result = colorchooser.askcolor(
            color=self.font_color.get(), title="Color subtítulo inferior")
        if result and result[1]:
            hex_c = result[1].upper()
            self.font_color.set(hex_c)
            self.color_swatch_bot.configure(bg=hex_c)

    def _pick_color_top(self, _event=None):
        result = colorchooser.askcolor(
            color=self.font_color_top.get(), title="Color subtítulo superior")
        if result and result[1]:
            hex_c = result[1].upper()
            self.font_color_top.set(hex_c)
            self.color_swatch_top.configure(bg=hex_c)

    def _open_editor(self):
        srt = self.srt_path.get()
        if not srt:
            messagebox.showwarning("Sin .srt",
                                   "Indica primero la ruta del archivo .srt.")
            return
        if not os.path.isfile(srt):
            messagebox.showwarning("Archivo no encontrado",
                                   f"El archivo .srt no existe todavía:\n{srt}\n\n"
                                   "Genera el .srt primero o elige uno existente.")
            return
        SubtitleEditor(self.root, srt_path=srt,
                       video_path=self.video_path.get())

    # ── Log / status ─────────────────────────────────────────────────────────

    def _log(self, msg: str):
        self.log.insert(tk.END, msg + "\n")
        self.log.see(tk.END)
        self.root.update_idletasks()

    def _status(self, msg: str):
        self.status_var.set(msg)
        self.root.update_idletasks()

    # ── Guardianes ───────────────────────────────────────────────────────────

    def _guard(self, checks: list) -> bool:
        for ok, msg in checks:
            if not ok:
                messagebox.showwarning("Atención", msg)
                return False
        return True

    # ── Generar .srt ─────────────────────────────────────────────────────────

    def _start_generate(self):
        if self._busy:
            return
        if not self._guard([
            (bool(self.video_path.get()), "Selecciona un vídeo primero."),
            (bool(self.srt_path.get()),   "Indica la ruta del archivo .srt."),
        ]):
            return
        self._busy = True
        threading.Thread(target=self._generate_thread, daemon=True).start()

    def _generate_thread(self):
        self.pbar.start(10)
        self._status("Cargando modelo Whisper…")
        try:
            import whisper
        except ImportError:
            self._log("❌  openai-whisper no instalado.")
            self._log("    Ejecuta:  pip install openai-whisper")
            messagebox.showerror("Error", "openai-whisper no está instalado.\n"
                                          "Ejecuta:  pip install openai-whisper")
            self.pbar.stop(); self._busy = False; return

        video     = self.video_path.get()
        srt_out   = self.srt_path.get()
        lang_code = LANGUAGES.get(self.language.get())
        model_id  = self.model.get()

        try:
            import io, os as _os
            _real_stderr = sys.stderr
            _real_stdout = sys.stdout
            # Suprimir cualquier salida de consola de Whisper/tqdm antes del import
            _devnull = open(_os.devnull, "w")
            sys.stderr = _devnull
            sys.stdout = _devnull

            self._log(f"▶  Cargando modelo '{model_id}'…")
            self._status(f"Cargando modelo '{model_id}'… (descarga si es la primera vez)")
            model = whisper.load_model(model_id)
            self._log(f"✔  Modelo '{model_id}' cargado.")
            self._log(f"▶  Transcribiendo: {os.path.basename(video)}")
            self._status("Transcribiendo vídeo… (puede tardar varios minutos)")

            # Usamos decode_options para capturar progreso segmento a segmento
            _seg_counter = [0]

            class _ProgressHook:
                """Hook mínimo para capturar cada segmento transcrito."""
                def __init__(hook_self, log_fn, status_fn, root):
                    hook_self._log = log_fn
                    hook_self._status = status_fn
                    hook_self._root = root

                def __call__(hook_self, seek, total):
                    _seg_counter[0] += 1
                    pct = int(seek / total * 100) if total else 0
                    hook_self._status(
                        f"Transcribiendo… segmento {_seg_counter[0]}  "
                        f"({pct}% del audio procesado)")
                    hook_self._root.update_idletasks()

            progress_hook = _ProgressHook(self._log, self._status, self.root)

            kwargs = {"verbose": False, "fp16": False, "word_timestamps": True}
            if lang_code:
                kwargs["language"] = lang_code

            # Comprobar si esta versión de Whisper acepta progress_callback
            # usando inspect, sin ejecutar la transcripción dos veces
            import inspect
            if "progress_callback" in inspect.signature(model.transcribe).parameters:
                kwargs["progress_callback"] = progress_hook
            result = model.transcribe(video, **kwargs)

            sys.stderr = _real_stderr
            sys.stdout = _real_stdout
            _devnull.close()

            max_dur = self.max_seg_duration.get()
            segs = self._split_segments(result["segments"], max_dur)

            self._log(f"▶  Guardando .srt → {srt_out}")
            self._write_srt(segs, srt_out)
            self._log(f"✅  .srt generado con {len(segs)} segmentos.")
            self._status("✅  .srt generado correctamente")
            messagebox.showinfo("Éxito", f"Subtítulos generados:\n{srt_out}")

        except Exception as exc:
            try:
                sys.stderr = _real_stderr
                sys.stdout = _real_stdout
                _devnull.close()
            except UnboundLocalError:
                pass
            self._log(f"❌  {exc}")
            self._status("❌  Error al generar .srt")
            messagebox.showerror("Error", str(exc))
        finally:
            self.pbar.stop()
            self._busy = False

    @staticmethod
    def _split_segments(segments, max_dur: float) -> list:
        out = []
        for seg in segments:
            words = seg.get("words", [])
            if not words:
                out.append({"start": seg["start"], "end": seg["end"],
                             "text": seg["text"].strip()})
                continue

            chunk_words  = []
            chunk_start  = words[0]["start"]

            for i, w in enumerate(words):
                chunk_words.append(w["word"])
                chunk_end = w["end"]
                duration  = chunk_end - chunk_start
                next_gap  = (words[i + 1]["start"] - chunk_end
                             if i + 1 < len(words) else 0.0)
                is_last   = (i == len(words) - 1)

                if (duration >= max_dur) or (next_gap >= 0.15):
                    out.append({"start": chunk_start, "end": chunk_end,
                                "text": "".join(chunk_words).strip()})
                    if not is_last:
                        chunk_start = words[i + 1]["start"]
                        chunk_words = []

            if chunk_words:
                out.append({"start": chunk_start, "end": words[-1]["end"],
                            "text": "".join(chunk_words).strip()})
        return out

    @staticmethod
    def _write_srt(segments, path: str):
        def t(sec):
            h, rem = divmod(int(sec), 3600)
            m, s   = divmod(rem, 60)
            ms     = int((sec - int(sec)) * 1000)
            return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"
        with open(path, "w", encoding="utf-8") as f:
            for i, seg in enumerate(segments, 1):
                f.write(f"{i}\n{t(seg['start'])} --> {t(seg['end'])}\n"
                        f"{seg['text'].strip()}\n\n")

    # ── Traducir .srt ─────────────────────────────────────────────────────────

    def _start_translate(self):
        if self._busy:
            return
        srt = self.srt_path.get()
        out = self.trans_srt_path.get()
        if not out:
            # Sugerir nombre automático
            if srt:
                base, ext = os.path.splitext(srt)
                lang_code = TRANS_LANGUAGES.get(self.trans_lang.get(), "xx")
                out = f"{base}_{lang_code}{ext}"
                self.trans_srt_path.set(out)
        if not self._guard([
            (bool(srt),              "Indica la ruta del .srt de origen (sección 2)."),
            (os.path.isfile(srt),    f"El .srt de origen no existe:\n{srt}"),
            (bool(out),              "Indica la ruta del .srt traducido."),
        ]):
            return
        self._busy = True
        threading.Thread(target=self._translate_thread, daemon=True).start()

    def _translate_thread(self):
        self.pbar.start(10)
        srt_in  = self.srt_path.get()
        srt_out = self.trans_srt_path.get()
        lang_name = self.trans_lang.get()
        lang_code = TRANS_LANGUAGES.get(lang_name, "en")

        self._status(f"Traduciendo a {lang_name}…")

        try:
            from deep_translator import GoogleTranslator
        except ImportError:
            self._log("❌  deep-translator no instalado.")
            self._log("    Ejecuta:  pip install deep-translator")
            messagebox.showerror("Error",
                                 "deep-translator no está instalado.\n"
                                 "Ejecuta:  pip install deep-translator")
            self.pbar.stop(); self._busy = False; return

        try:
            entries  = parse_srt(srt_in)
            total    = len(entries)
            self._log(f"▶  Traduciendo {total} entradas al {lang_name}…")
            translator = GoogleTranslator(source="auto", target=lang_code)

            # Traducir en lotes de 20 para ser eficientes y no saturar la API
            BATCH = 20
            translated = []
            for start_i in range(0, total, BATCH):
                batch = entries[start_i: start_i + BATCH]
                texts = [e["text"] for e in batch]
                # Unir con separador poco frecuente para minimizar llamadas
                combined = "\n⟡\n".join(texts)
                result   = translator.translate(combined)
                parts    = result.split("⟡") if result else texts
                # Si la API devuelve distinto número de partes, usar original
                if len(parts) != len(batch):
                    parts = [translator.translate(t) or t for t in texts]
                for e, trans_text in zip(batch, parts):
                    new_e = dict(e)
                    new_e["text"] = trans_text.strip()
                    translated.append(new_e)
                self._log(f"   {min(start_i + BATCH, total)}/{total} entradas traducidas…")

            write_srt_from_entries(translated, srt_out)
            self._log(f"✅  .srt traducido guardado → {srt_out}")
            self._status("✅  Traducción completada")

            # Copiar automáticamente al campo ⬇ Abajo del Modo B (dos idiomas)
            self.dual_srt_bottom.set(srt_out)
            self._log("ℹ  .srt traducido asignado a ⬇ Abajo (Modo B – dos idiomas).")

        except Exception as exc:
            self._log(f"❌  {exc}")
            self._status("❌  Error en la traducción")
            messagebox.showerror("Error", str(exc))
        finally:
            self.pbar.stop()
            self._busy = False

    # ── Incrustar ─────────────────────────────────────────────────────────────

    def _start_burn(self):
        if self._busy:
            return
        srt = self.srt_path.get()
        if not self._guard([
            (bool(self.video_path.get()),    "Selecciona un vídeo primero."),
            (bool(srt),                      "Indica la ruta del archivo .srt."),
            (os.path.isfile(srt),            f"El archivo .srt no existe:\n{srt}"),
            (bool(self.output_folder.get()), "Selecciona la carpeta de salida."),
            (bool(self.out_name.get()),      "Indica el nombre del vídeo de salida."),
        ]):
            return
        self._busy = True
        threading.Thread(target=self._burn_thread, daemon=True).start()

    @staticmethod
    def _hex_to_ass(hex_color: str) -> str:
        h = hex_color.lstrip("#")
        r, g, b = h[0:2], h[2:4], h[4:6]
        return f"&H00{b}{g}{r}"

    @staticmethod
    def _escape_srt_path(path: str) -> str:
        p = path.replace("\\", "/")
        if len(p) >= 2 and p[1] == ":":
            p = p[0] + "\\:" + p[2:]
        p = p.replace("'", "\\'")
        return p

    def _burn_thread(self):
        self.pbar.start(10)
        self._status("Incrustando subtítulos con FFmpeg…")

        video      = self.video_path.get()
        srt        = self.srt_path.get()
        folder     = self.output_folder.get()
        out        = os.path.join(folder, self.out_name.get())
        font_size  = self.font_size.get()
        ass_color  = self._hex_to_ass(self.font_color.get())
        pos_name   = self.position.get()
        alignment  = POSITIONS.get(pos_name, 2)
        margin_v   = POS_MARGIN.get(pos_name, 20)
        srt_esc    = self._escape_srt_path(srt)

        force_style = (
            f"FontSize={font_size},"
            f"PrimaryColour={ass_color},"
            f"Alignment={alignment},"
            f"BorderStyle=1,Outline=1,Shadow=0,"
            f"Bold=0,MarginV={margin_v}"
        )

        cmd = [
            "ffmpeg", "-y",
            "-i", video,
            "-vf", f"subtitles='{srt_esc}':force_style='{force_style}'",
            "-c:a", "copy",
            out,
        ]

        self._run_ffmpeg(cmd, out)

    def _run_ffmpeg(self, cmd: list, out_path: str):
        """Ejecuta un comando ffmpeg, loguea la salida y notifica al terminar."""
        self._log("▶  Ejecutando FFmpeg…")
        self._log(f"   Salida → {out_path}")
        try:
            kw = dict(stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                      universal_newlines=True, errors="replace")
            if sys.platform == "win32":
                kw["creationflags"] = subprocess.CREATE_NO_WINDOW

            proc = subprocess.Popen(cmd, **kw)

            # Intentar extraer duración total y tiempo procesado para progreso real
            duration_sec = None
            re_duration = re.compile(r"Duration:\s*(\d+):(\d+):(\d+)\.(\d+)")
            re_time     = re.compile(r"time=(\d+):(\d+):(\d+)\.(\d+)")

            for line in proc.stdout:
                line = line.rstrip()
                if not line:
                    continue
                self._log(line)

                # Capturar duración total del vídeo
                if duration_sec is None:
                    m = re_duration.search(line)
                    if m:
                        h, mn, s, cs = map(int, m.groups())
                        duration_sec = h * 3600 + mn * 60 + s + cs / 100

                # Actualizar barra con progreso real si tenemos duración
                if duration_sec:
                    m = re_time.search(line)
                    if m:
                        h, mn, s, cs = map(int, m.groups())
                        elapsed = h * 3600 + mn * 60 + s + cs / 100
                        pct = min(int(elapsed / duration_sec * 100), 99)
                        self._status(f"Incrustando… {pct}%  ({elapsed:.0f}s / {duration_sec:.0f}s)")
                        # Actualizar barra determinista
                        self.pbar.stop()
                        self.pbar.configure(mode="determinate",
                                            maximum=100, value=pct)
                        self.root.update_idletasks()

            proc.wait()

            if proc.returncode == 0:
                self._log(f"✅  Vídeo guardado: {out_path}")
                self._status("✅  Subtítulos incrustados correctamente")
                messagebox.showinfo("Éxito", f"Vídeo listo:\n{out_path}")
                if self.open_folder.get():
                    self._open_folder(os.path.dirname(out_path))
            else:
                self._log(f"❌  FFmpeg terminó con código {proc.returncode}")
                self._status("❌  Error en FFmpeg")
                messagebox.showerror("Error",
                                     "FFmpeg terminó con error.\n"
                                     "Revisa el log para más detalles.")
        except FileNotFoundError:
            self._log("❌  'ffmpeg' no encontrado en el PATH.")
            self._log("    Descarga ffmpeg en:  https://ffmpeg.org/download.html")
            self._status("❌  ffmpeg no encontrado")
            messagebox.showerror("Error",
                                 "'ffmpeg' no está instalado o no está en el PATH.\n"
                                 "Descárgalo en: https://ffmpeg.org/download.html")
        except Exception as exc:
            self._log(f"❌  {exc}")
            self._status("❌  Error inesperado")
            messagebox.showerror("Error", str(exc))
        finally:
            self.pbar.stop()
            self.pbar.configure(mode="indeterminate", value=0)
            self._busy = False

    def _browse_dual_srt(self):
        p = filedialog.askopenfilename(
            title="Seleccionar .srt para la parte superior",
            filetypes=[("SubRip", "*.srt"), ("Todos", "*.*")])
        if p:
            self.dual_srt_path.set(p)

    def _start_burn_dual(self):
        if self._busy:
            return
        srt_bot = self.dual_srt_bottom.get()
        srt_top = self.dual_srt_top.get()
        if not self._guard([
            (bool(self.video_path.get()),    "Selecciona un vídeo primero (sección superior)."),
            (bool(srt_bot),                  "Indica el .srt inferior (⬇ abajo)."),
            (os.path.isfile(srt_bot),        f"El .srt inferior no existe:\n{srt_bot}"),
            (bool(srt_top),                  "Indica el .srt superior (⬆ arriba)."),
            (os.path.isfile(srt_top),        f"El .srt superior no existe:\n{srt_top}"),
            (bool(self.output_folder.get()), "Selecciona la carpeta de salida."),
            (bool(self.out_name.get()),      "Indica el nombre del vídeo de salida."),
        ]):
            return
        self._busy = True
        threading.Thread(target=self._burn_dual_thread, daemon=True).start()

    def _get_video_size(self, video: str) -> tuple:
        """Devuelve (width, height) del vídeo usando ffprobe. Fallback: (1280, 720)."""
        try:
            kw = dict(stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                      universal_newlines=True, errors="replace")
            if sys.platform == "win32":
                kw["creationflags"] = subprocess.CREATE_NO_WINDOW
            cmd = [
                "ffprobe", "-v", "error",
                "-select_streams", "v:0",
                "-show_entries", "stream=width,height",
                "-of", "csv=p=0",
                video,
            ]
            result = subprocess.run(cmd, **kw)
            line = result.stdout.strip().splitlines()[0]
            w, h = map(int, line.split(","))
            return w, h
        except Exception:
            return 1280, 720

    @staticmethod
    def _srt_to_ass(srt_path: str, ass_path: str,
                    font_size: int, ass_color: str,
                    alignment: int, margin_v: int,
                    play_res_x: int = 1280, play_res_y: int = 720):
        """
        Convierte un .srt a .ass con estilo propio.
        - Usa la resolución real del vídeo en PlayResX/PlayResY para que
          MarginV se interprete en píxeles reales sin escalar.
        - Añade {\\an8} como override explícito en cada línea de diálogo
          para forzar alineación superior-centro a nivel de evento,
          inmune a cualquier reinterpretación de FFmpeg.
        """
        entries = parse_srt(srt_path)

        def srt_t_to_ass(t: str) -> str:
            t = t.replace(",", ".")
            h, m, rest = t.split(":")
            s, ms_str = rest.split(".")
            cs = ms_str[:2]
            return f"{int(h)}:{m}:{s}.{cs}"

        # Override de alineación ASS: \an1-\an9 (numpad layout)
        align_override = {2: r"{\an2}", 5: r"{\an5}", 8: r"{\an8}"}
        override = align_override.get(alignment, "")

        # FontSize en ASS es relativo a PlayResY=288 (referencia estándar libass).
        # El usuario especifica el tamaño en "píxeles visuales" equivalentes al
        # force_style del .srt inferior. Hay que escalar a unidades ASS:
        #   ass_font_size = font_size_px * 288 / play_res_y
        ass_font_size = round(font_size * play_res_y / 288) if play_res_y else font_size

        header = (
            "[Script Info]\n"
            "ScriptType: v4.00+\n"
            "Collisions: Normal\n"
            f"PlayResX: {play_res_x}\n"
            f"PlayResY: {play_res_y}\n\n"
            "[V4+ Styles]\n"
            "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, "
            "OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, "
            "ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, "
            "Alignment, MarginL, MarginR, MarginV, Encoding\n"
            f"Style: Default,Arial,{ass_font_size},{ass_color},&H000000FF,"
            f"&H00000000,&H64000000,0,0,0,0,100,100,0,0,1,1,0,"
            f"{alignment},10,10,{margin_v},1\n\n"
            "[Events]\n"
            "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
        )

        with open(ass_path, "w", encoding="utf-8") as f:
            f.write(header)
            for e in entries:
                start = srt_t_to_ass(e["start"])
                end   = srt_t_to_ass(e["end"])
                text  = e["text"].replace("\n", "\\N")
                f.write(f"Dialogue: 0,{start},{end},Default,,0,0,0,,{override}{text}\n")

    def _burn_dual_thread(self):
        self.pbar.start(10)
        self._status("Incrustando subtítulos duales con FFmpeg…")

        video     = self.video_path.get()
        srt_bot   = self.dual_srt_bottom.get()
        srt_top   = self.dual_srt_top.get()
        folder    = self.output_folder.get()
        out       = os.path.join(folder, self.out_name.get())
        font_size = self.font_size.get()
        color_bot = self._hex_to_ass(self.font_color.get())
        color_top = self._hex_to_ass(self.font_color_top.get())

        try:
            vid_w, vid_h = self._get_video_size(video)
            self._log(f"ℹ  Resolución detectada: {vid_w}×{vid_h}")

            # El .srt inferior se incrusta con force_style normal (Alignment=2)
            bot_esc   = self._escape_srt_path(srt_bot)
            style_bot = (
                f"FontSize={font_size},PrimaryColour={color_bot},"
                f"Alignment=2,BorderStyle=1,Outline=1,Shadow=0,Bold=0,MarginV=8"
            )

            # El .srt superior → .ass con resolución real + override \an8 por línea
            tmp_ass = os.path.join(tempfile.gettempdir(), "_subtitlegen_top.ass")
            self._log("▶  Convirtiendo .srt superior a .ass temporal…")
            self._srt_to_ass(srt_top, tmp_ass,
                             font_size=font_size,
                             ass_color=color_top,
                             alignment=8,
                             margin_v=8,
                             play_res_x=vid_w,
                             play_res_y=vid_h)
            top_esc = self._escape_srt_path(tmp_ass)

            vf = (
                f"subtitles='{bot_esc}':force_style='{style_bot}',"
                f"ass='{top_esc}'"
            )

            cmd = ["ffmpeg", "-y", "-i", video, "-vf", vf, "-c:a", "copy", out]
            self._run_ffmpeg(cmd, out)

        except Exception as exc:
            self._log(f"❌  {exc}")
            self._status("❌  Error preparando subtítulos duales")
            messagebox.showerror("Error", str(exc))
            self.pbar.stop()
            self.pbar.configure(mode="indeterminate", value=0)
            self._busy = False

    @staticmethod
    def _open_folder(folder: str):
        try:
            if sys.platform == "win32":
                os.startfile(folder)
            elif sys.platform == "darwin":
                subprocess.Popen(["open", folder])
            else:
                subprocess.Popen(["xdg-open", folder])
        except Exception:
            pass


# ── Main ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    root = tk.Tk()
    root.minsize(WIN_W, 480)
    root.maxsize(root.winfo_screenwidth(), root.winfo_screenheight())
    app = SubtitleGen(root)
    root.mainloop()
