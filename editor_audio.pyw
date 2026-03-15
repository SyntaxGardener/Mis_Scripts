# -*- coding: utf-8 -*-
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import os
import time

try:
    from moviepy import AudioFileClip, concatenate_audioclips
    MOVIEPY_OK = True
except ImportError:
    MOVIEPY_OK = False

try:
    import pygame
    PYGAME_OK = True
except ImportError:
    PYGAME_OK = False

try:
    from tkinterdnd2 import TkinterDnD, DND_FILES
    DND_OK = True
except ImportError:
    DND_OK = False


# ── Utilidades ────────────────────────────────────────────
def seg_a_mmss(s):
    s = max(0.0, float(s))
    return f"{int(s // 60):02d}:{int(s % 60):02d}"


def parsear_dnd(data):
    """Extrae lista de rutas del evento drag-and-drop (maneja espacios/llaves)."""
    rutas = []
    data = data.strip()
    i = 0
    while i < len(data):
        if data[i] == '{':
            j = data.index('}', i)
            rutas.append(data[i+1:j])
            i = j + 1
        else:
            j = data.find(' ', i)
            if j == -1:
                rutas.append(data[i:])
                break
            rutas.append(data[i:j])
            i = j
        while i < len(data) and data[i] == ' ':
            i += 1
    return [r for r in rutas if r]


def aplicar_fades(clip, fade_in, fade_out):
    """Aplica fade-in y fade-out al clip (compatible moviepy 1.x y 2.x)."""
    if fade_in <= 0 and fade_out <= 0:
        return clip
    try:
        from moviepy import afx
        efectos = []
        if fade_in > 0:
            efectos.append(afx.AudioFadeIn(fade_in))
        if fade_out > 0:
            efectos.append(afx.AudioFadeOut(fade_out))
        return clip.with_effects(efectos)
    except Exception:
        if fade_in > 0:
            clip = clip.audio_fadein(fade_in)
        if fade_out > 0:
            clip = clip.audio_fadeout(fade_out)
        return clip


# ── Paleta de colores ─────────────────────────────────────
C = {
    'bg':            '#F0F2F5',
    'card':          '#FFFFFF',
    'fg':            '#1A1A2E',
    'fg_muted':      '#6B7280',
    'player_bg':     '#1E293B',
    'success':       '#15803D',
    'success_bg':    '#DCFCE7',
    'warning':       '#B45309',
    'error':         '#B91C1C',
    'error_bg':      '#FEE2E2',
    'info':          '#1D4ED8',
    'unir':          '#0EA5E9',
    'eliminar':      '#EF4444',
    'extraer':       '#10B981',
    'inicio_c':      '#3B82F6',
    'fin_c':         '#8B5CF6',
    'fade_bg':       '#F5F3FF',
    'fade_fg':       '#6D28D9',
    'convertir':     '#F59E0B',
}

AUDIO_EXT = "*.mp3 *.wav *.m4a *.ogg *.flac *.aac"


# ═════════════════════════════════════════════════════════
class EditorAudio:
    def __init__(self, root):
        self.root = root
        self.root.title("Editor de Audio")
        self.root.configure(bg=C['bg'])
        self._config_ventana()

        self.modo = "unir"
        self.ultimo_dir = os.path.expanduser("~")
        self.procesando = False

        # Modo unir
        self.archivos_unir = []

        # Modo convertir
        self.archivos_convertir = []

        # Modos eliminar / extraer
        self.audio_path = None
        self.audio_dur = 0.0
        self.fragmentos_eliminar = []

        # Reproduccion
        self.reproduciendo = False
        self.pausado = False
        self.pos_actual = 0.0
        self._play_offset = 0.0
        self._arrastrando = False
        self._hilo_repro = None

        if not MOVIEPY_OK:
            messagebox.showerror("Error",
                "MoviePy no esta instalado.\nEjecuta: pip install moviepy")
            root.destroy()
            return

        if PYGAME_OK:
            pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=4096)
        else:
            if not messagebox.askyesno("Sin reproductor",
                "pygame no esta instalado. No podras previsualizar el audio.\n"
                "Continuar de todas formas?"):
                root.destroy()
                return

        self._build_ui()
        self._bind_keys()

    # ──────────────────────────────────────────────────────
    # SETUP
    # ──────────────────────────────────────────────────────
    def _config_ventana(self):
        w, h = 840, 780
        x = (self.root.winfo_screenwidth() - w) // 2
        self.root.geometry(f"{w}x{h}+{x}+5")
        self.root.minsize(760, 670)

    def _bind_keys(self):
        self.root.bind("<space>", lambda e: self._toggle_play())
        self.root.bind("<s>",     lambda e: self.detener())
        self.root.bind("<S>",     lambda e: self.detener())

    def _toggle_play(self):
        if self.modo not in ("eliminar", "extraer") or not PYGAME_OK:
            return
        if self.reproduciendo and not self.pausado:
            self.pausar()
        else:
            self.reproducir()

    # ──────────────────────────────────────────────────────
    # BUILD UI
    # ──────────────────────────────────────────────────────
    def _build_ui(self):
        style = ttk.Style()
        style.theme_use('clam')
        style.configure('TProgressbar', background=C['extraer'])
        style.configure('Vol.Horizontal.TScale', background=C['player_bg'])

        wrap = tk.Frame(self.root, bg=C['bg'], padx=16, pady=6)
        wrap.pack(fill=tk.BOTH, expand=True)

        # Titulo
        tk.Label(wrap, text="EDITOR DE AUDIO",
                 font=('Arial', 16, 'bold'), fg=C['fg'], bg=C['bg']).pack()
        sub = "MP3  WAV  M4A  OGG  FLAC"
        if DND_OK:
            sub += "   |   arrastra archivos directamente"
        tk.Label(wrap, text=sub, font=('Arial', 9), fg=C['fg_muted'], bg=C['bg']).pack(pady=(0, 4))

        # Selector de modo
        mc = self._card(wrap, pady=5)
        mc.pack(fill=tk.X, pady=(0, 5))
        tk.Label(mc, text="MODO", font=('Arial', 8, 'bold'),
                 fg=C['fg_muted'], bg=C['card']).pack(anchor='w')
        self.modo_var = tk.StringVar(value="unir")
        modos_lista = [
            ("unir",     "Unir audios",         "Concatena varios archivos en uno"),
            ("eliminar", "Eliminar fragmentos",  "Borra una o varias secciones"),
            ("extraer",  "Extraer fragmento",    "Guarda solo la seccion elegida"),
            ("convertir","Convertir formato",    "Cambia el formato de uno o varios archivos"),
        ]
        grid = tk.Frame(mc, bg=C['card'])
        grid.pack(fill=tk.X, pady=2)
        for col in range(2):
            grid.columnconfigure(col, weight=1)
        for idx, (valor, etiqueta, desc) in enumerate(modos_lista):
            row, col = divmod(idx, 2)
            f = tk.Frame(grid, bg=C['card'])
            f.grid(row=row, column=col, sticky='w', padx=8, pady=1)
            tk.Radiobutton(f, text=etiqueta, variable=self.modo_var, value=valor,
                           bg=C['card'], fg=C[valor], selectcolor=C['card'],
                           activebackground=C['card'], font=('Arial', 10, 'bold'),
                           command=self._cambiar_modo).pack(anchor='w')
            tk.Label(f, text=desc, font=('Arial', 8), fg=C['fg_muted'],
                     bg=C['card']).pack(anchor='w', padx=20)

        # Paneles de modo
        self.panel_wrap = tk.Frame(wrap, bg=C['bg'])
        self.panel_wrap.pack(fill=tk.BOTH, expand=True, pady=(0, 3))
        self.panel_unir      = tk.Frame(self.panel_wrap, bg=C['bg'])
        self.panel_eliminar  = tk.Frame(self.panel_wrap, bg=C['bg'])
        self.panel_extraer   = tk.Frame(self.panel_wrap, bg=C['bg'])
        self.panel_convertir = tk.Frame(self.panel_wrap, bg=C['bg'])
        self._build_panel_unir()
        self._build_panel_eliminar()
        self._build_panel_extraer()
        self._build_panel_convertir()
        self.panel_unir.pack(fill=tk.BOTH, expand=True)

        # ── Fundidos (compartido por todos los modos)
        self._build_panel_fundidos(wrap)

        # Boton procesar
        btn_row = tk.Frame(wrap, bg=C['bg'])
        btn_row.pack(pady=4)
        self.procesar_btn = tk.Button(btn_row, text=self._label_boton(),
                                      bg=C['unir'], fg='white',
                                      font=('Arial', 13, 'bold'),
                                      padx=40, pady=8, relief='flat',
                                      cursor='hand2', state='disabled',
                                      command=self._iniciar_procesar)
        self.procesar_btn.pack()

        # Estado / progreso
        pie = tk.Frame(wrap, bg=C['bg'])
        pie.pack(fill=tk.X)
        self.barra = ttk.Progressbar(pie, mode='indeterminate', length=420)
        self.barra.pack()
        self.estado_lbl = tk.Label(pie, text="Listo",
                                   fg=C['success'], bg=C['bg'], font=('Arial', 9))
        self.estado_lbl.pack(pady=1)
        tk.Label(wrap, text="[Espacio] Play/Pausa    [S] Stop",
                 font=('Arial', 8), fg='#9CA3AF', bg=C['bg']).pack()

    # ──────────────────────────────────────────────────────
    # PANEL FUNDIDOS
    # ──────────────────────────────────────────────────────
    def _build_panel_fundidos(self, parent):
        card = tk.Frame(parent, bg=C['fade_bg'], relief='solid', bd=1, padx=10, pady=5)
        card.pack(fill=tk.X, pady=(0, 3))

        tk.Label(card, text="FUNDIDOS  (aplicados al audio resultante)",
                 font=('Arial', 9, 'bold'), fg=C['fade_fg'], bg=C['fade_bg']).pack(anchor='w')

        row = tk.Frame(card, bg=C['fade_bg'])
        row.pack(pady=(3, 1))

        for label, attr in [("Fade in  (s):", "fade_in_var"), ("Fade out  (s):", "fade_out_var")]:
            tk.Label(row, text=label, font=('Arial', 9), fg=C['fg'], bg=C['fade_bg']).pack(side=tk.LEFT, padx=(0, 4))
            var = tk.DoubleVar(value=0.0)
            setattr(self, attr, var)
            sp = tk.Spinbox(row, from_=0, to=30, increment=0.5, textvariable=var,
                            width=5, font=('Arial', 10), justify='center',
                            relief='flat', bg='white',
                            highlightbackground=C['fade_fg'], highlightthickness=1)
            sp.pack(side=tk.LEFT, padx=(0, 20))

        tk.Label(card,
                 text="0 = sin fundido  |  el fade-out empieza antes del final  |  maximo 30 s",
                 font=('Arial', 8), fg=C['fg_muted'], bg=C['fade_bg']).pack(anchor='w')

    # ──────────────────────────────────────────────────────
    # PANEL UNIR
    # ──────────────────────────────────────────────────────
    def _build_panel_convertir(self):
        p = self.panel_convertir

        card = self._card(p)
        card.pack(fill=tk.BOTH, expand=True, pady=(0, 3))

        hdr = tk.Frame(card, bg=C['card'])
        hdr.pack(fill=tk.X)
        tk.Label(hdr, text="ARCHIVOS A CONVERTIR",
                 font=('Arial', 9, 'bold'), fg=C['fg_muted'], bg=C['card']).pack(side=tk.LEFT)
        if DND_OK:
            tk.Label(hdr, text="  arrastra aqui para agregar",
                     font=('Arial', 8), fg=C['convertir'], bg=C['card']).pack(side=tk.LEFT)

        btn_row = tk.Frame(card, bg=C['card'])
        btn_row.pack(fill=tk.X, pady=6)
        for txt, col, cmd in [
            ("+ Agregar",  C['convertir'], self._conv_agregar),
            ("Quitar",     C['eliminar'],  self._conv_quitar),
            ("Vaciar",     C['fg_muted'],  self._conv_vaciar),
        ]:
            tk.Button(btn_row, text=txt, bg=col, fg='white',
                      font=('Arial', 9, 'bold'), padx=9, pady=4,
                      relief='flat', cursor='hand2',
                      command=cmd).pack(side=tk.LEFT, padx=2)

        lc = tk.Frame(card, bg='#FFFBEB', height=120)
        lc.pack(fill=tk.BOTH, expand=True)
        lc.pack_propagate(False)
        sb = tk.Scrollbar(lc)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        self.lista_conv = tk.Listbox(lc, bg='#FFFBEB', fg=C['fg'],
                                     selectbackground='#FDE68A',
                                     yscrollcommand=sb.set,
                                     font=('Arial', 9), activestyle='dotbox',
                                     selectmode=tk.EXTENDED)
        self.lista_conv.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb.config(command=self.lista_conv.yview)
        if DND_OK:
            self.lista_conv.drop_target_register(DND_FILES)
            self.lista_conv.dnd_bind('<<Drop>>', self._dnd_convertir)

        footer = tk.Frame(card, bg=C['card'])
        footer.pack(fill=tk.X, pady=2)
        self.conv_count_lbl = tk.Label(footer, text="0 archivos",
                                       bg=C['card'], fg=C['fg_muted'], font=('Arial', 9))
        self.conv_count_lbl.pack(side=tk.LEFT)
        self.conv_prog_lbl = tk.Label(footer, text="",
                                      bg=C['card'], fg=C['convertir'], font=('Arial', 9, 'bold'))
        self.conv_prog_lbl.pack(side=tk.RIGHT)

        opt = self._card(p, pady=6)
        opt.pack(fill=tk.X)
        tk.Label(opt, text="OPCIONES DE CONVERSION",
                 font=('Arial', 9, 'bold'), fg=C['fg_muted'], bg=C['card']).pack(anchor='w')

        fmt_row = tk.Frame(opt, bg=C['card'])
        fmt_row.pack(fill=tk.X, pady=4)
        tk.Label(fmt_row, text="Formato de salida:", font=('Arial', 10),
                 fg=C['fg'], bg=C['card']).pack(side=tk.LEFT, padx=(0, 8))
        self.conv_fmt_var = tk.StringVar(value="mp3")
        for label, val in [("MP3","mp3"),("WAV","wav"),("OGG","ogg"),("FLAC","flac"),("M4A","m4a")]:
            tk.Radiobutton(fmt_row, text=label, variable=self.conv_fmt_var, value=val,
                           bg=C['card'], fg=C['fg'], selectcolor=C['card'],
                           activebackground=C['card'], font=('Arial', 10, 'bold'),
                           command=self._conv_fmt_changed).pack(side=tk.LEFT, padx=6)

        qual_row = tk.Frame(opt, bg=C['card'])
        qual_row.pack(fill=tk.X, pady=(0, 2))
        tk.Label(qual_row, text="Calidad MP3/OGG/M4A:", font=('Arial', 10),
                 fg=C['fg'], bg=C['card']).pack(side=tk.LEFT, padx=(0, 8))
        self.conv_bitrate_var = tk.StringVar(value="192k")
        self.conv_bitrate_menu = ttk.Combobox(qual_row,
                                              values=["96k","128k","192k","256k","320k"],
                                              textvariable=self.conv_bitrate_var,
                                              width=6, state='readonly', font=('Arial', 10))
        self.conv_bitrate_menu.pack(side=tk.LEFT, padx=(0, 12))
        tk.Label(qual_row, text="(ignorado para WAV y FLAC)",
                 font=('Arial', 8), fg=C['fg_muted'], bg=C['card']).pack(side=tk.LEFT)

        dest_row = tk.Frame(opt, bg=C['card'])
        dest_row.pack(fill=tk.X, pady=(4, 0))
        tk.Label(dest_row, text="Destino:", font=('Arial', 10),
                 fg=C['fg'], bg=C['card']).pack(side=tk.LEFT, padx=(0, 8))
        self.conv_dest_var = tk.StringVar(value="Misma carpeta que el original")
        tk.Label(dest_row, textvariable=self.conv_dest_var,
                 font=('Arial', 9), fg=C['info'], bg=C['card'],
                 anchor='w', width=36).pack(side=tk.LEFT)
        tk.Button(dest_row, text="Elegir...", bg=C['convertir'], fg='white',
                  font=('Arial', 9, 'bold'), padx=8, pady=2,
                  relief='flat', cursor='hand2',
                  command=self._conv_elegir_destino).pack(side=tk.LEFT, padx=4)
        tk.Button(dest_row, text="Misma carpeta", bg=C['fg_muted'], fg='white',
                  font=('Arial', 9, 'bold'), padx=8, pady=2, relief='flat', cursor='hand2',
                  command=lambda: (setattr(self, 'conv_dest_dir', None) or
                                   self.conv_dest_var.set("Misma carpeta que el original"))
                  ).pack(side=tk.LEFT)
        self.conv_dest_dir = None

    def _conv_fmt_changed(self):
        fmt = self.conv_fmt_var.get()
        self.conv_bitrate_menu.config(
            state='disabled' if fmt in ('wav', 'flac') else 'readonly')

    def _conv_elegir_destino(self):
        d = filedialog.askdirectory(title="Carpeta de destino", initialdir=self.ultimo_dir)
        if d:
            self.conv_dest_dir = d
            self.conv_dest_var.set(d)
        else:
            self.conv_dest_dir = None
            self.conv_dest_var.set("Misma carpeta que el original")

    def _conv_agregar(self):
        archivos = filedialog.askopenfilenames(
            title="Selecciona archivos para convertir",
            initialdir=self.ultimo_dir,
            filetypes=[("Audio", AUDIO_EXT), ("Todos", "*.*")])
        for f in archivos:
            if f not in self.archivos_convertir:
                self.archivos_convertir.append(f)
                self.ultimo_dir = os.path.dirname(f)
        self._refrescar_lista_convertir()

    def _conv_quitar(self):
        sel = list(self.lista_conv.curselection())
        for i in reversed(sel):
            del self.archivos_convertir[i]
        self._refrescar_lista_convertir()

    def _conv_vaciar(self):
        self.archivos_convertir.clear()
        self._refrescar_lista_convertir()

    def _refrescar_lista_convertir(self):
        self.lista_conv.delete(0, tk.END)
        for i, a in enumerate(self.archivos_convertir, 1):
            self.lista_conv.insert(tk.END, f"  {i}.  {os.path.basename(a)}")
        n = len(self.archivos_convertir)
        self.conv_count_lbl.config(text=f"{n} archivo{'s' if n!=1 else ''}")
        self.conv_prog_lbl.config(text="")
        self._update_boton()

    def _dnd_convertir(self, event):
        rutas = parsear_dnd(event.data)
        ext_ok = set(AUDIO_EXT.replace('*', '').split())
        for r in rutas:
            if any(r.lower().endswith(e) for e in ext_ok) and r not in self.archivos_convertir:
                self.archivos_convertir.append(r)
                self.ultimo_dir = os.path.dirname(r)
        self._refrescar_lista_convertir()

    def _build_panel_unir(self):
        card = self._card(self.panel_unir)
        card.pack(fill=tk.BOTH, expand=True)

        hdr = tk.Frame(card, bg=C['card'])
        hdr.pack(fill=tk.X)
        tk.Label(hdr, text="ARCHIVOS A UNIR (en orden de aparicion)",
                 font=('Arial', 9, 'bold'), fg=C['fg_muted'], bg=C['card']).pack(side=tk.LEFT)
        if DND_OK:
            tk.Label(hdr, text="  arrastra aqui para agregar",
                     font=('Arial', 8), fg=C['unir'], bg=C['card']).pack(side=tk.LEFT)

        btn_row = tk.Frame(card, bg=C['card'])
        btn_row.pack(fill=tk.X, pady=6)
        for txt, col, cmd in [
            ("+ Agregar",  C['unir'],     self._unir_agregar),
            ("Subir",      C['info'],     self._unir_subir),
            ("Bajar",      C['info'],     self._unir_bajar),
            ("Quitar",     C['eliminar'], self._unir_quitar),
            ("Vaciar",     C['fg_muted'], self._unir_vaciar),
        ]:
            tk.Button(btn_row, text=txt, bg=col, fg='white',
                      font=('Arial', 9, 'bold'), padx=9, pady=4,
                      relief='flat', cursor='hand2',
                      command=cmd).pack(side=tk.LEFT, padx=2)

        lc = tk.Frame(card, bg='#F9FAFB', height=160)
        lc.pack(fill=tk.BOTH, expand=True)
        lc.pack_propagate(False)
        sb = tk.Scrollbar(lc)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        self.lista_unir = tk.Listbox(lc, bg='#F9FAFB', fg=C['fg'],
                                     selectbackground='#DBEAFE',
                                     yscrollcommand=sb.set,
                                     font=('Arial', 9), activestyle='dotbox')
        self.lista_unir.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb.config(command=self.lista_unir.yview)

        # Drag & drop en la lista
        if DND_OK:
            self.lista_unir.drop_target_register(DND_FILES)
            self.lista_unir.dnd_bind('<<Drop>>', self._dnd_unir)

        footer = tk.Frame(card, bg=C['card'])
        footer.pack(fill=tk.X, pady=4)
        self.unir_count_lbl = tk.Label(footer, text="0 archivos",
                                       bg=C['card'], fg=C['fg_muted'], font=('Arial', 9))
        self.unir_count_lbl.pack(side=tk.LEFT)
        self.unir_dur_lbl = tk.Label(footer, text="",
                                     bg=C['card'], fg=C['info'], font=('Arial', 9, 'bold'))
        self.unir_dur_lbl.pack(side=tk.RIGHT)

    # ──────────────────────────────────────────────────────
    # PANEL ELIMINAR
    # ──────────────────────────────────────────────────────
    def _build_panel_eliminar(self):
        p = self.panel_eliminar
        arc = self._card(p, pady=5)
        arc.pack(fill=tk.X, pady=(0, 3))
        self._build_arc_row(arc, "eliminar")
        self._build_reproductor(p, "eliminar")

        bottom = tk.Frame(p, bg=C['bg'])
        bottom.pack(fill=tk.BOTH, expand=True)
        bottom.columnconfigure(0, weight=1)
        bottom.columnconfigure(1, weight=1)

        # Izquierda: definir fragmento
        rng = self._card(bottom, pady=5)
        rng.grid(row=0, column=0, sticky='nsew', padx=(0, 4))
        tk.Label(rng, text="DEFINIR FRAGMENTO",
                 font=('Arial', 9, 'bold'), fg=C['fg_muted'], bg=C['card']).pack(anchor='w')
        sc_f = tk.Frame(rng, bg=C['card'])
        sc_f.pack(fill=tk.X, pady=3)
        sc_f.columnconfigure(1, weight=1)
        self.elim_ini_sc, self.elim_ini_ent, self.elim_ini_lbl = \
            self._fila_tiempo(sc_f, 0, "INICIO", C['inicio_c'], '#DBEAFE',
                              lambda v: self._rng_changed("eliminar", "ini", v))
        self.elim_fin_sc, self.elim_fin_ent, self.elim_fin_lbl = \
            self._fila_tiempo(sc_f, 1, "FIN", C['fin_c'], '#EDE9FE',
                              lambda v: self._rng_changed("eliminar", "fin", v))
        self.elim_dur_lbl = tk.Label(rng, text="Fragmento: -",
                                     bg=C['error_bg'], fg=C['error'],
                                     font=('Arial', 9, 'bold'), padx=6, pady=3)
        self.elim_dur_lbl.pack(fill=tk.X, pady=(3, 4))
        tk.Button(rng, text="+ Anadir a la lista",
                  bg=C['eliminar'], fg='white',
                  font=('Arial', 10, 'bold'), pady=7, relief='flat', cursor='hand2',
                  command=self._elim_anadir).pack(fill=tk.X)
        tk.Label(rng, text="Mueve los sliders, escribe los segundos  /  marca mientras reproduces",
                 bg=C['card'], fg='#9CA3AF', font=('Arial', 8),
                 justify='left').pack(anchor='w', pady=(3, 0))

        # Derecha: lista de fragmentos
        lst = self._card(bottom, pady=5)
        lst.grid(row=0, column=1, sticky='nsew', padx=(4, 0))
        tk.Label(lst, text="FRAGMENTOS A ELIMINAR",
                 font=('Arial', 9, 'bold'), fg=C['fg_muted'], bg=C['card']).pack(anchor='w')
        lb_f = tk.Frame(lst, bg='#FFF5F5', height=110)
        lb_f.pack(fill=tk.BOTH, expand=True, pady=4)
        lb_f.pack_propagate(False)
        sb2 = tk.Scrollbar(lb_f)
        sb2.pack(side=tk.RIGHT, fill=tk.Y)
        self.elim_lista = tk.Listbox(lb_f, bg='#FFF5F5', fg=C['fg'],
                                     selectbackground='#FECACA',
                                     yscrollcommand=sb2.set,
                                     font=('Courier', 9), activestyle='dotbox')
        self.elim_lista.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb2.config(command=self.elim_lista.yview)
        btn2 = tk.Frame(lst, bg=C['card'])
        btn2.pack(fill=tk.X, pady=(2, 0))
        tk.Button(btn2, text="Quitar seleccionado",
                  bg=C['eliminar'], fg='white',
                  font=('Arial', 9, 'bold'), padx=6, pady=3,
                  relief='flat', cursor='hand2',
                  command=self._elim_quitar).pack(side=tk.LEFT, padx=(0, 4))
        tk.Button(btn2, text="Vaciar lista",
                  bg=C['fg_muted'], fg='white',
                  font=('Arial', 9, 'bold'), padx=6, pady=3,
                  relief='flat', cursor='hand2',
                  command=self._elim_vaciar).pack(side=tk.LEFT)
        self.elim_resumen_lbl = tk.Label(lst, text="",
                                         bg=C['card'], fg=C['error'],
                                         font=('Arial', 8, 'bold'))
        self.elim_resumen_lbl.pack(anchor='w', pady=(2, 0))

    # ──────────────────────────────────────────────────────
    # PANEL EXTRAER
    # ──────────────────────────────────────────────────────
    def _build_panel_extraer(self):
        p = self.panel_extraer
        arc = self._card(p, pady=8)
        arc.pack(fill=tk.X, pady=(0, 5))
        self._build_arc_row(arc, "extraer")
        self._build_reproductor(p, "extraer")
        rng = self._card(p, pady=5)
        rng.pack(fill=tk.X)
        tk.Label(rng, text="FRAGMENTO A EXTRAER",
                 font=('Arial', 9, 'bold'), fg=C['fg_muted'], bg=C['card']).pack(anchor='w')
        sc_f = tk.Frame(rng, bg=C['card'])
        sc_f.pack(fill=tk.X, pady=6)
        sc_f.columnconfigure(1, weight=1)
        self.extr_ini_sc, self.extr_ini_ent, self.extr_ini_lbl = \
            self._fila_tiempo(sc_f, 0, "INICIO", C['inicio_c'], '#DBEAFE',
                              lambda v: self._rng_changed("extraer", "ini", v))
        self.extr_fin_sc, self.extr_fin_ent, self.extr_fin_lbl = \
            self._fila_tiempo(sc_f, 1, "FIN", C['fin_c'], '#EDE9FE',
                              lambda v: self._rng_changed("extraer", "fin", v))
        self.extr_dur_lbl = tk.Label(rng, text="Fragmento: -",
                                     bg=C['success_bg'], fg=C['success'],
                                     font=('Arial', 9, 'bold'), padx=6, pady=3)
        self.extr_dur_lbl.pack(fill=tk.X, pady=(3, 0))
        tk.Label(rng, text="Mueve los sliders, escribe los segundos\no marca mientras reproduces",
                 bg=C['card'], fg='#9CA3AF', font=('Arial', 8),
                 justify='left').pack(anchor='w', pady=(6, 0))

    # ──────────────────────────────────────────────────────
    # WIDGETS REUTILIZABLES
    # ──────────────────────────────────────────────────────
    def _card(self, parent, pady=10):
        return tk.Frame(parent, bg=C['card'], relief='solid', bd=1, padx=10, pady=pady)

    def _build_arc_row(self, parent, modo):
        tk.Label(parent, text="ARCHIVO DE AUDIO",
                 font=('Arial', 9, 'bold'), fg=C['fg_muted'], bg=C['card']).pack(anchor='w')
        fila = tk.Frame(parent, bg=C['card'])
        fila.pack(fill=tk.X, pady=2)
        lbl = tk.Label(fila, text="Ningun archivo  |  arrastra aqui o usa Abrir..." if DND_OK
                       else "Ningun archivo seleccionado",
                       fg='#9CA3AF', bg=C['card'], font=('Arial', 9), anchor='w')
        lbl.pack(side=tk.LEFT, fill=tk.X, expand=True)
        tk.Button(fila, text="Abrir...", bg=C[modo], fg='white',
                  font=('Arial', 9, 'bold'), padx=10, pady=2,
                  relief='flat', cursor='hand2',
                  command=lambda m=modo: self._abrir_audio(m)).pack(side=tk.RIGHT)
        info = tk.Label(parent, text="", bg=C['card'], fg=C['success'], font=('Arial', 9))
        info.pack(anchor='w')

        # Drag & drop en la etiqueta del archivo
        if DND_OK:
            for widget in (lbl, parent):
                widget.drop_target_register(DND_FILES)
                widget.dnd_bind('<<Drop>>', lambda e, m=modo: self._dnd_audio(e, m))

        setattr(self, f"_{modo}_arc_lbl",  lbl)
        setattr(self, f"_{modo}_info_lbl", info)

    def _build_reproductor(self, parent, modo):
        color = C[modo]
        if not PYGAME_OK:
            wf = tk.Frame(parent, bg='#FEF3C7', relief='solid', bd=1, padx=10, pady=6)
            wf.pack(fill=tk.X, pady=(0, 5))
            tk.Label(wf, text="Reproductor no disponible (instala pygame)",
                     bg='#FEF3C7', fg='#92400E', font=('Arial', 9)).pack()
            return

        pl = tk.Frame(parent, bg=C['player_bg'], padx=10, pady=5)
        pl.pack(fill=tk.X, pady=(0, 3))

        # Cabecera: titulo + volumen
        hdr = tk.Frame(pl, bg=C['player_bg'])
        hdr.pack(fill=tk.X)
        tk.Label(hdr, text="REPRODUCTOR",
                 font=('Arial', 9, 'bold'), bg=C['player_bg'], fg='white').pack(side=tk.LEFT)
        # Volumen
        tk.Label(hdr, text="   VOL", font=('Arial', 8),
                 bg=C['player_bg'], fg='#94A3B8').pack(side=tk.LEFT)
        vol_sc = tk.Scale(hdr, from_=0, to=100, orient=tk.HORIZONTAL,
                          showvalue=False, length=90,
                          bg=C['player_bg'], troughcolor='#475569',
                          highlightthickness=0, activebackground='#94A3B8',
                          command=lambda v: self._set_volumen(int(v)))
        vol_sc.set(80)
        vol_sc.pack(side=tk.LEFT, padx=4)
        self.vol_lbl = tk.Label(hdr, text="80%", font=('Arial', 8),
                                bg=C['player_bg'], fg='#94A3B8', width=4)
        self.vol_lbl.pack(side=tk.LEFT)
        if PYGAME_OK:
            pygame.mixer.music.set_volume(0.80)

        # Barra de posicion
        pos_row = tk.Frame(pl, bg=C['player_bg'])
        pos_row.pack(fill=tk.X, pady=2)
        t_act = tk.Label(pos_row, text="00:00", width=5,
                         bg=C['player_bg'], fg='white', font=('Courier', 9, 'bold'))
        t_act.pack(side=tk.LEFT)
        repro_sc = tk.Scale(pos_row, from_=0, to=100,
                            orient=tk.HORIZONTAL, showvalue=False,
                            bg=C['player_bg'], troughcolor='#334155',
                            highlightthickness=0, activebackground=color)
        repro_sc.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=6)
        t_tot = tk.Label(pos_row, text="00:00", width=5,
                         bg=C['player_bg'], fg='#94A3B8', font=('Courier', 9))
        t_tot.pack(side=tk.RIGHT)
        repro_sc.bind('<Button-1>',        lambda e: self._sc_click())
        repro_sc.bind('<B1-Motion>',       lambda e, s=repro_sc, l=t_act: self._sc_drag(s, l))
        repro_sc.bind('<ButtonRelease-1>', lambda e, s=repro_sc: self._sc_release(s))

        # Controles + salto
        ctrl = tk.Frame(pl, bg=C['player_bg'])
        ctrl.pack(pady=2)
        skip_col = '#475569'
        for txt, seg in [("-30s", -30), ("-5s", -5)]:
            tk.Button(ctrl, text=txt, bg=skip_col, fg='white',
                      font=('Arial', 9), padx=7, pady=4, relief='flat', cursor='hand2',
                      command=lambda s=seg: self._saltar(s)).pack(side=tk.LEFT, padx=2)
        play_b  = self._player_btn(ctrl, "Play",  '#16A34A', self.reproducir)
        pause_b = self._player_btn(ctrl, "Pausa", '#D97706', self.pausar)
        stop_b  = self._player_btn(ctrl, "Stop",  '#DC2626', self.detener)
        for b in (play_b, pause_b, stop_b):
            b.pack(side=tk.LEFT, padx=3)
            b.config(state='disabled')
        for txt, seg in [("+5s", 5), ("+30s", 30)]:
            tk.Button(ctrl, text=txt, bg=skip_col, fg='white',
                      font=('Arial', 9), padx=7, pady=4, relief='flat', cursor='hand2',
                      command=lambda s=seg: self._saltar(s)).pack(side=tk.LEFT, padx=2)

        # Marcar tiempos
        marc = tk.Frame(pl, bg=C['player_bg'])
        marc.pack(pady=(2, 0))
        tk.Button(marc, text="<< Marcar INICIO",
                  bg=C['inicio_c'], fg='white',
                  font=('Arial', 9, 'bold'), padx=8, pady=2, relief='flat', cursor='hand2',
                  command=lambda m=modo: self._marcar_inicio(m)).pack(side=tk.LEFT, padx=3)
        tk.Button(marc, text="Marcar FIN >>",
                  bg=C['fin_c'], fg='white',
                  font=('Arial', 9, 'bold'), padx=8, pady=2, relief='flat', cursor='hand2',
                  command=lambda m=modo: self._marcar_fin(m)).pack(side=tk.LEFT, padx=3)
        tk.Label(marc, text="(mientras se reproduce)",
                 bg=C['player_bg'], fg='#64748B', font=('Arial', 8)).pack(side=tk.LEFT, padx=6)

        setattr(self, f"_sc_{modo}",      repro_sc)
        setattr(self, f"_t_act_{modo}",   t_act)
        setattr(self, f"_t_tot_{modo}",   t_tot)
        setattr(self, f"_play_b_{modo}",  play_b)
        setattr(self, f"_pause_b_{modo}", pause_b)
        setattr(self, f"_stop_b_{modo}",  stop_b)

    def _player_btn(self, parent, text, color, cmd):
        return tk.Button(parent, text=text, bg=color, fg='white',
                         font=('Arial', 9, 'bold'), padx=14, pady=4,
                         relief='flat', cursor='hand2', command=cmd)

    def _fila_tiempo(self, parent, row, label, color, trough, cmd):
        pady_top = 0 if row == 0 else 6
        tk.Label(parent, text=label, font=('Arial', 8, 'bold'),
                 fg=color, bg=C['card'], width=6).grid(
            row=row, column=0, sticky='w', padx=(0, 4), pady=(pady_top, 0))
        sc = tk.Scale(parent, from_=0, to=100,
                      orient=tk.HORIZONTAL, showvalue=False,
                      bg=C['card'], troughcolor=trough,
                      highlightthickness=0, activebackground=color,
                      command=cmd)
        sc.grid(row=row, column=1, sticky='ew', padx=4, pady=(pady_top, 0))
        entry = tk.Entry(parent, width=7, font=('Arial', 10), justify='center')
        entry.grid(row=row, column=2, padx=4, pady=(pady_top, 0))
        entry.insert(0, "0")
        entry.bind('<FocusOut>', lambda e, s=sc, en=entry, c=cmd: self._entry_sync(s, en, c))
        entry.bind('<Return>',   lambda e, s=sc, en=entry, c=cmd: self._entry_sync(s, en, c))
        mmss = tk.Label(parent, text="(00:00)", fg=color, bg=C['card'],
                        font=('Arial', 8), width=7)
        mmss.grid(row=row, column=3, pady=(pady_top, 0))
        return sc, entry, mmss

    def _entry_sync(self, scale, entry, cmd):
        try:
            v = float(entry.get())
            v = max(0.0, min(v, self.audio_dur))
            entry.delete(0, tk.END)
            entry.insert(0, f"{v:.1f}")
            scale.set(int(v))
            cmd(v)
        except ValueError:
            pass

    # ──────────────────────────────────────────────────────
    # VOLUMEN
    # ──────────────────────────────────────────────────────
    def _set_volumen(self, v):
        self.vol_lbl.config(text=f"{v}%")
        if PYGAME_OK:
            pygame.mixer.music.set_volume(v / 100.0)

    # ──────────────────────────────────────────────────────
    # DRAG & DROP
    # ──────────────────────────────────────────────────────
    def _dnd_unir(self, event):
        rutas = parsear_dnd(event.data)
        ext_ok = set(AUDIO_EXT.replace('*', '').split())
        for r in rutas:
            if any(r.lower().endswith(e) for e in ext_ok) and r not in self.archivos_unir:
                self.archivos_unir.append(r)
                self.ultimo_dir = os.path.dirname(r)
        self._refrescar_lista_unir()

    def _dnd_audio(self, event, modo):
        rutas = parsear_dnd(event.data)
        if rutas:
            self._cargar_audio(rutas[0], modo)

    # ──────────────────────────────────────────────────────
    # CAMBIO DE MODO
    # ──────────────────────────────────────────────────────
    def _cambiar_modo(self):
        self.modo = self.modo_var.get()
        self.detener()
        for p in (self.panel_unir, self.panel_eliminar, self.panel_extraer, self.panel_convertir):
            p.pack_forget()
        {'unir':      self.panel_unir,
         'eliminar':  self.panel_eliminar,
         'extraer':   self.panel_extraer,
         'convertir': self.panel_convertir}[self.modo].pack(fill=tk.BOTH, expand=True)
        self.procesar_btn.config(text=self._label_boton(), bg=C[self.modo])
        self._update_boton()

    def _label_boton(self):
        return {'unir':      "UNIR AUDIOS",
                'eliminar':  "ELIMINAR FRAGMENTOS",
                'extraer':   "EXTRAER FRAGMENTO",
                'convertir': "CONVERTIR ARCHIVOS"}[self.modo]

    # ──────────────────────────────────────────────────────
    # ABRIR / CARGAR AUDIO
    # ──────────────────────────────────────────────────────
    def _abrir_audio(self, modo):
        f = filedialog.askopenfilename(
            title="Selecciona un archivo de audio",
            initialdir=self.ultimo_dir,
            filetypes=[("Audio", AUDIO_EXT), ("Todos", "*.*")])
        if f:
            self._cargar_audio(f, modo)

    def _cargar_audio(self, f, modo):
        self.detener()
        self.ultimo_dir = os.path.dirname(f)
        self.audio_path = f
        nombre = os.path.basename(f)
        try:
            clip = AudioFileClip(f)
            dur = clip.duration
            self.audio_dur = dur
            clip.close()
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo leer el archivo:\n{e}")
            return

        maximo = int(dur)
        info_txt = f"Duracion: {seg_a_mmss(dur)}  ({dur:.1f} s)"
        getattr(self, f"_{modo}_arc_lbl").config(text=nombre, fg=C['fg'])
        getattr(self, f"_{modo}_info_lbl").config(text=info_txt)

        if modo == "eliminar":
            for sc in (self.elim_ini_sc, self.elim_fin_sc):
                sc.configure(to=maximo)
            self.elim_ini_sc.set(0);   self.elim_fin_sc.set(maximo)
            self.elim_ini_ent.delete(0, tk.END); self.elim_ini_ent.insert(0, "0")
            self.elim_fin_ent.delete(0, tk.END); self.elim_fin_ent.insert(0, str(maximo))
            self._actualizar_dur_lbl("eliminar")
            self.fragmentos_eliminar.clear()
            self._refrescar_lista_fragmentos()
        else:
            for sc in (self.extr_ini_sc, self.extr_fin_sc):
                sc.configure(to=maximo)
            self.extr_ini_sc.set(0);   self.extr_fin_sc.set(maximo)
            self.extr_ini_ent.delete(0, tk.END); self.extr_ini_ent.insert(0, "0")
            self.extr_fin_ent.delete(0, tk.END); self.extr_fin_ent.insert(0, str(maximo))
            self._actualizar_dur_lbl("extraer")

        if PYGAME_OK:
            getattr(self, f"_sc_{modo}").configure(to=maximo)
            getattr(self, f"_t_tot_{modo}").config(text=seg_a_mmss(dur))
            for attr in (f"_play_b_{modo}", f"_pause_b_{modo}", f"_stop_b_{modo}"):
                getattr(self, attr).config(state='normal')

        self._update_boton()

    # ──────────────────────────────────────────────────────
    # SLIDERS DE RANGO
    # ──────────────────────────────────────────────────────
    def _rng_changed(self, modo, cual, val):
        val = float(val)
        if modo == "eliminar":
            ini_sc, ini_ent, ini_lbl = self.elim_ini_sc, self.elim_ini_ent, self.elim_ini_lbl
            fin_sc, fin_ent, fin_lbl = self.elim_fin_sc, self.elim_fin_ent, self.elim_fin_lbl
        else:
            ini_sc, ini_ent, ini_lbl = self.extr_ini_sc, self.extr_ini_ent, self.extr_ini_lbl
            fin_sc, fin_ent, fin_lbl = self.extr_fin_sc, self.extr_fin_ent, self.extr_fin_lbl
        try:
            ini = float(ini_ent.get())
            fin = float(fin_ent.get())
        except ValueError:
            ini, fin = 0.0, self.audio_dur
        if cual == "ini":
            val = min(val, fin)
            ini_sc.set(int(val))
            ini_ent.delete(0, tk.END); ini_ent.insert(0, f"{val:.1f}")
            ini_lbl.config(text=f"({seg_a_mmss(val)})")
        else:
            val = max(val, ini)
            fin_sc.set(int(val))
            fin_ent.delete(0, tk.END); fin_ent.insert(0, f"{val:.1f}")
            fin_lbl.config(text=f"({seg_a_mmss(val)})")
        self._actualizar_dur_lbl(modo)

    def _actualizar_dur_lbl(self, modo):
        try:
            if modo == "eliminar":
                ini = float(self.elim_ini_ent.get())
                fin = float(self.elim_fin_ent.get())
                lbl = self.elim_dur_lbl
            else:
                ini = float(self.extr_ini_ent.get())
                fin = float(self.extr_fin_ent.get())
                lbl = self.extr_dur_lbl
            dur = fin - ini
            lbl.config(text=f"Fragmento: {seg_a_mmss(dur)}  ({dur:.1f} s)" if dur > 0
                       else "El inicio debe ser menor que el fin")
        except Exception:
            pass

    # ──────────────────────────────────────────────────────
    # FRAGMENTOS A ELIMINAR
    # ──────────────────────────────────────────────────────
    def _elim_anadir(self):
        try:
            ini = float(self.elim_ini_ent.get())
            fin = float(self.elim_fin_ent.get())
        except ValueError:
            messagebox.showwarning("Aviso", "Los tiempos no son validos."); return
        if ini >= fin:
            messagebox.showwarning("Aviso", "El inicio debe ser menor que el fin."); return
        if ini < 0 or fin > self.audio_dur:
            messagebox.showwarning("Aviso", f"Tiempos fuera de rango (0 - {self.audio_dur:.1f} s)."); return
        for f in self.fragmentos_eliminar:
            if not (fin <= f['ini'] or ini >= f['fin']):
                messagebox.showwarning("Solapamiento",
                    f"Se solapa con {seg_a_mmss(f['ini'])} - {seg_a_mmss(f['fin'])}."); return
        self.fragmentos_eliminar.append({'ini': ini, 'fin': fin})
        self.fragmentos_eliminar.sort(key=lambda x: x['ini'])
        self._refrescar_lista_fragmentos()
        self._update_boton()

    def _elim_quitar(self):
        sel = self.elim_lista.curselection()
        if sel:
            del self.fragmentos_eliminar[sel[0]]
            self._refrescar_lista_fragmentos()
            self._update_boton()

    def _elim_vaciar(self):
        self.fragmentos_eliminar.clear()
        self._refrescar_lista_fragmentos()
        self._update_boton()

    def _refrescar_lista_fragmentos(self):
        self.elim_lista.delete(0, tk.END)
        total = 0.0
        for i, f in enumerate(self.fragmentos_eliminar, 1):
            dur = f['fin'] - f['ini']
            total += dur
            self.elim_lista.insert(tk.END,
                f"  {i}.  {seg_a_mmss(f['ini'])} -> {seg_a_mmss(f['fin'])}   ({dur:.1f}s)")
        n = len(self.fragmentos_eliminar)
        if n:
            resta = self.audio_dur - total
            self.elim_resumen_lbl.config(
                text=f"{n} fragmento{'s' if n>1 else ''}  |  "
                     f"Eliminado: {seg_a_mmss(total)}  |  "
                     f"Resultado: {seg_a_mmss(resta)}")
        else:
            self.elim_resumen_lbl.config(text="")

    # ──────────────────────────────────────────────────────
    # MARCAR TIEMPOS
    # ──────────────────────────────────────────────────────
    def _marcar_inicio(self, modo):
        if not self.reproduciendo: return
        t = self.pos_actual
        if modo == "eliminar":
            self.elim_ini_ent.delete(0, tk.END); self.elim_ini_ent.insert(0, f"{t:.1f}")
            self.elim_ini_sc.set(int(t));  self.elim_ini_lbl.config(text=f"({seg_a_mmss(t)})")
        else:
            self.extr_ini_ent.delete(0, tk.END); self.extr_ini_ent.insert(0, f"{t:.1f}")
            self.extr_ini_sc.set(int(t));  self.extr_ini_lbl.config(text=f"({seg_a_mmss(t)})")
        self._actualizar_dur_lbl(modo)
        self.estado_lbl.config(text=f"Inicio -> {seg_a_mmss(t)}", fg=C['inicio_c'])

    def _marcar_fin(self, modo):
        if not self.reproduciendo: return
        t = self.pos_actual
        if modo == "eliminar":
            self.elim_fin_ent.delete(0, tk.END); self.elim_fin_ent.insert(0, f"{t:.1f}")
            self.elim_fin_sc.set(int(t));  self.elim_fin_lbl.config(text=f"({seg_a_mmss(t)})")
        else:
            self.extr_fin_ent.delete(0, tk.END); self.extr_fin_ent.insert(0, f"{t:.1f}")
            self.extr_fin_sc.set(int(t));  self.extr_fin_lbl.config(text=f"({seg_a_mmss(t)})")
        self._actualizar_dur_lbl(modo)
        self.estado_lbl.config(text=f"Fin -> {seg_a_mmss(t)}", fg=C['fin_c'])

    # ──────────────────────────────────────────────────────
    # REPRODUCTOR
    # ──────────────────────────────────────────────────────
    def _saltar(self, segundos):
        if not self.audio_path or not PYGAME_OK: return
        nueva_pos = max(0.0, min(self.pos_actual + segundos, self.audio_dur))
        self.pos_actual = nueva_pos
        for modo in ("eliminar", "extraer"):
            if self.modo == modo and hasattr(self, f"_sc_{modo}"):
                getattr(self, f"_sc_{modo}").set(int(nueva_pos))
                getattr(self, f"_t_act_{modo}").config(text=seg_a_mmss(nueva_pos))
        if self.reproduciendo and not self.pausado:
            pygame.mixer.music.stop()
            pygame.mixer.music.load(self.audio_path)
            self._play_offset = nueva_pos
            pygame.mixer.music.play(start=nueva_pos)

    def reproducir(self):
        if not self.audio_path or not PYGAME_OK: return
        if self.reproduciendo and self.pausado:
            pygame.mixer.music.unpause()
            self.pausado = False
            self.estado_lbl.config(text="Reproduciendo...", fg=C['warning'])
        elif not self.reproduciendo:
            try:
                pygame.mixer.music.load(self.audio_path)
                self._play_offset = self.pos_actual
                pygame.mixer.music.play(start=self.pos_actual)
                self.reproduciendo = True
                self.pausado = False
                self.estado_lbl.config(text="Reproduciendo...", fg=C['warning'])
                if not (self._hilo_repro and self._hilo_repro.is_alive()):
                    self._hilo_repro = threading.Thread(
                        target=self._hilo_progreso, daemon=True)
                    self._hilo_repro.start()
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo reproducir:\n{e}")

    def pausar(self):
        if self.reproduciendo and not self.pausado and PYGAME_OK:
            pygame.mixer.music.pause()
            self.pausado = True
            self.estado_lbl.config(text="Pausado", fg=C['warning'])

    def detener(self):
        if not PYGAME_OK: return
        if self.reproduciendo:
            pygame.mixer.music.stop()
        self.reproduciendo = False
        self.pausado = False
        self.pos_actual = 0.0
        self._play_offset = 0.0
        for modo in ("eliminar", "extraer"):
            if hasattr(self, f"_sc_{modo}"):
                getattr(self, f"_sc_{modo}").set(0)
                getattr(self, f"_t_act_{modo}").config(text="00:00")
        self.estado_lbl.config(text="Detenido", fg=C['info'])

    def _hilo_progreso(self):
        while self.reproduciendo:
            if not self.pausado and pygame.mixer.music.get_busy():
                pos = self._play_offset + pygame.mixer.music.get_pos() / 1000.0
                self.pos_actual = pos
                if not self._arrastrando:
                    self.root.after(0, self._refrescar_repro_ui, pos)
                time.sleep(0.1)
            elif self.reproduciendo and not self.pausado:
                self.root.after(0, self.detener)
                break
            else:
                time.sleep(0.1)

    def _refrescar_repro_ui(self, pos):
        if self.modo in ("eliminar", "extraer"):
            m = self.modo
            if hasattr(self, f"_sc_{m}"):
                getattr(self, f"_sc_{m}").set(int(pos))
                getattr(self, f"_t_act_{m}").config(text=seg_a_mmss(pos))

    def _sc_click(self):
        self._arrastrando = True
        if self.reproduciendo and not self.pausado and PYGAME_OK:
            pygame.mixer.music.pause()

    def _sc_drag(self, sc, t_lbl):
        t_lbl.config(text=seg_a_mmss(sc.get()))

    def _sc_release(self, sc):
        self._arrastrando = False
        if self.audio_path and PYGAME_OK:
            self.pos_actual = float(sc.get())
            if self.reproduciendo:
                pygame.mixer.music.stop()
                pygame.mixer.music.load(self.audio_path)
                self._play_offset = self.pos_actual
                pygame.mixer.music.play(start=self.pos_actual)
                self.pausado = False

    # ──────────────────────────────────────────────────────
    # ESTADO BOTÓN
    # ──────────────────────────────────────────────────────
    def _update_boton(self):
        ok = (
            (self.modo == "unir"     and len(self.archivos_unir) >= 2) or
            (self.modo == "eliminar" and self.audio_path and len(self.fragmentos_eliminar) >= 1) or
            (self.modo == "extraer"  and self.audio_path) or
            (self.modo == "convertir" and len(self.archivos_convertir) >= 1)
        )
        self.procesar_btn.config(
            state='normal' if ok else 'disabled',
            bg=C[self.modo] if ok else '#9CA3AF')

    # ──────────────────────────────────────────────────────
    # LEER FUNDIDOS
    # ──────────────────────────────────────────────────────
    def _get_fades(self):
        try:
            fi = max(0.0, float(self.fade_in_var.get()))
        except Exception:
            fi = 0.0
        try:
            fo = max(0.0, float(self.fade_out_var.get()))
        except Exception:
            fo = 0.0
        return fi, fo

    # ──────────────────────────────────────────────────────
    # PROCESADO
    # ──────────────────────────────────────────────────────
    def _iniciar_procesar(self):
        if not self.procesando:
            threading.Thread(target=self._procesar, daemon=True).start()

    def _procesar(self):
        try:
            self.procesando = True
            self.procesar_btn.config(state='disabled', bg='#9CA3AF')
            self.barra.start()
            {'unir':      self._proc_unir,
             'eliminar':  self._proc_eliminar,
             'extraer':   self._proc_extraer,
             'convertir': self._proc_convertir}[self.modo]()
        except Exception as e:
            self.estado_lbl.config(text="Error", fg=C['error'])
            messagebox.showerror("Error", str(e))
        finally:
            self.barra.stop()
            self.procesando = False
            self._update_boton()

    def _proc_unir(self):
        fi, fo = self._get_fades()
        clips = []
        for i, path in enumerate(self.archivos_unir, 1):
            self.estado_lbl.config(
                text=f"Cargando {i}/{len(self.archivos_unir)}...", fg=C['warning'])
            clips.append(AudioFileClip(path))
        self.estado_lbl.config(text="Uniendo...", fg=C['warning'])
        final = concatenate_audioclips(clips)
        if fi > 0 or fo > 0:
            self.estado_lbl.config(text="Aplicando fundidos...", fg=C['warning'])
            final = aplicar_fades(final, fi, fo)
        out = filedialog.asksaveasfilename(
            title="Guardar audio unido", initialdir=self.ultimo_dir,
            defaultextension=".mp3",
            filetypes=[("MP3", "*.mp3"), ("WAV", "*.wav"), ("Todos", "*.*")],
            initialfile="audios_unidos.mp3")
        if not out:
            final.close()
            for c in clips: c.close()
            self.estado_lbl.config(text="Cancelado", fg=C['warning']); return
        self.estado_lbl.config(text="Guardando...", fg=C['warning'])
        final.write_audiofile(out, **self._codec(out))
        dur = final.duration
        final.close()
        for c in clips: c.close()
        self.estado_lbl.config(text="Audios unidos", fg=C['success'])
        extra = f"\nFade in: {fi}s  |  Fade out: {fo}s" if fi > 0 or fo > 0 else ""
        messagebox.showinfo("Listo",
            f"Guardado: {os.path.basename(out)}\n"
            f"Duracion total: {seg_a_mmss(dur)}  ({dur:.1f} s){extra}")

    def _proc_eliminar(self):
        fi, fo = self._get_fades()
        self.estado_lbl.config(text="Cargando audio...", fg=C['warning'])
        clip = AudioFileClip(self.audio_path)
        tramos = []
        cursor = 0.0
        for f in self.fragmentos_eliminar:
            if cursor < f['ini']:
                tramos.append(clip.subclipped(cursor, f['ini']))
            cursor = f['fin']
        if cursor < clip.duration:
            tramos.append(clip.subclipped(cursor, clip.duration))
        if not tramos:
            clip.close()
            messagebox.showwarning("Aviso", "Los fragmentos marcados cubren todo el audio."); return
        self.estado_lbl.config(text="Eliminando fragmentos...", fg=C['warning'])
        final = concatenate_audioclips(tramos)
        if fi > 0 or fo > 0:
            self.estado_lbl.config(text="Aplicando fundidos...", fg=C['warning'])
            final = aplicar_fades(final, fi, fo)
        nombre_base = os.path.splitext(os.path.basename(self.audio_path))[0]
        out = filedialog.asksaveasfilename(
            title="Guardar audio resultante", initialdir=self.ultimo_dir,
            defaultextension=".mp3",
            filetypes=[("MP3", "*.mp3"), ("WAV", "*.wav"), ("Todos", "*.*")],
            initialfile=f"{nombre_base}_editado.mp3")
        if not out:
            final.close(); clip.close()
            self.estado_lbl.config(text="Cancelado", fg=C['warning']); return
        self.estado_lbl.config(text="Guardando...", fg=C['warning'])
        final.write_audiofile(out, **self._codec(out))
        dur = final.duration
        n = len(self.fragmentos_eliminar)
        final.close(); clip.close()
        self.estado_lbl.config(text="Fragmentos eliminados", fg=C['success'])
        extra = f"\nFade in: {fi}s  |  Fade out: {fo}s" if fi > 0 or fo > 0 else ""
        messagebox.showinfo("Listo",
            f"Guardado: {os.path.basename(out)}\n"
            f"{n} fragmento{'s' if n>1 else ''} eliminado{'s' if n>1 else ''}\n"
            f"Duracion resultante: {seg_a_mmss(dur)}  ({dur:.1f} s){extra}")

    def _proc_extraer(self):
        fi, fo = self._get_fades()
        try:
            ini = float(self.extr_ini_ent.get())
            fin = float(self.extr_fin_ent.get())
        except ValueError:
            raise ValueError("Los tiempos no son validos.")
        if ini >= fin:
            raise ValueError("El inicio debe ser menor que el fin.")
        if ini < 0 or fin > self.audio_dur:
            raise ValueError(f"Tiempos fuera de rango (0 - {self.audio_dur:.1f} s).")
        self.estado_lbl.config(text="Cargando audio...", fg=C['warning'])
        clip = AudioFileClip(self.audio_path)
        self.estado_lbl.config(text="Extrayendo...", fg=C['warning'])
        frag = clip.subclipped(ini, fin)
        if fi > 0 or fo > 0:
            self.estado_lbl.config(text="Aplicando fundidos...", fg=C['warning'])
            frag = aplicar_fades(frag, fi, fo)
        nombre_base = os.path.splitext(os.path.basename(self.audio_path))[0]
        out = filedialog.asksaveasfilename(
            title="Guardar fragmento extraido", initialdir=self.ultimo_dir,
            defaultextension=".mp3",
            filetypes=[("MP3", "*.mp3"), ("WAV", "*.wav"), ("Todos", "*.*")],
            initialfile=f"{nombre_base}_extracto.mp3")
        if not out:
            frag.close(); clip.close()
            self.estado_lbl.config(text="Cancelado", fg=C['warning']); return
        self.estado_lbl.config(text="Guardando...", fg=C['warning'])
        frag.write_audiofile(out, **self._codec(out))
        dur = fin - ini
        frag.close(); clip.close()
        self.estado_lbl.config(text="Fragmento extraido", fg=C['success'])
        extra = f"\nFade in: {fi}s  |  Fade out: {fo}s" if fi > 0 or fo > 0 else ""
        messagebox.showinfo("Listo",
            f"Guardado: {os.path.basename(out)}\n"
            f"Duracion: {seg_a_mmss(dur)}  ({dur:.1f} s){extra}")

    def _proc_convertir(self):
        fmt = self.conv_fmt_var.get()
        bitrate = self.conv_bitrate_var.get()
        dest_dir = self.conv_dest_dir
        total = len(self.archivos_convertir)
        ok = 0
        errores = []
        for i, path in enumerate(self.archivos_convertir, 1):
            nombre_base = os.path.splitext(os.path.basename(path))[0]
            carpeta = dest_dir if dest_dir else os.path.dirname(path)
            out = os.path.join(carpeta, f"{nombre_base}.{fmt}")
            if os.path.abspath(out) == os.path.abspath(path):
                out = os.path.join(carpeta, f"{nombre_base}_conv.{fmt}")
            self.root.after(0, self.conv_prog_lbl.config,
                            {'text': f"{i}/{total} convirtiendo..."})
            self.estado_lbl.config(
                text=f"Convirtiendo {i}/{total}: {os.path.basename(path)}",
                fg=C['warning'])
            try:
                clip = AudioFileClip(path)
                params = {'logger': None}
                if fmt == 'mp3':
                    params['codec'] = 'libmp3lame'
                    params['bitrate'] = bitrate
                elif fmt == 'wav':
                    params['codec'] = 'pcm_s16le'
                elif fmt == 'ogg':
                    params['codec'] = 'libvorbis'
                    params['bitrate'] = bitrate
                elif fmt == 'flac':
                    params['codec'] = 'flac'
                elif fmt == 'm4a':
                    params['codec'] = 'aac'
                    params['bitrate'] = bitrate
                clip.write_audiofile(out, **params)
                clip.close()
                ok += 1
            except Exception as e:
                errores.append(f"{os.path.basename(path)}: {e}")
        self.root.after(0, self.conv_prog_lbl.config,
                        {'text': f"{ok}/{total} convertidos"})
        self.estado_lbl.config(
            text=f"Conversion terminada ({ok}/{total})", fg=C['success'])
        msg = f"Convertidos: {ok} de {total}\nFormato: {fmt.upper()}"
        if fmt not in ('wav', 'flac'):
            msg += f"  |  Calidad: {bitrate}"
        destino_txt = dest_dir if dest_dir else "misma carpeta que cada original"
        msg += f"\nDestino: {destino_txt}"
        if errores:
            msg += f"\n\nErrores ({len(errores)}):\n" + "\n".join(errores)
        messagebox.showinfo("Conversion completada", msg)

    @staticmethod
    def _codec(path):
        if path.lower().endswith('.wav'):
            return {'codec': 'pcm_s16le', 'logger': None}
        return {'codec': 'libmp3lame', 'bitrate': '192k', 'logger': None}

    # ──────────────────────────────────────────────────────
    # LISTA UNIR
    # ──────────────────────────────────────────────────────
    def _unir_agregar(self):
        archivos = filedialog.askopenfilenames(
            title="Selecciona audios para unir", initialdir=self.ultimo_dir,
            filetypes=[("Audio", AUDIO_EXT), ("Todos", "*.*")])
        for f in archivos:
            if f not in self.archivos_unir:
                self.archivos_unir.append(f)
                self.ultimo_dir = os.path.dirname(f)
        self._refrescar_lista_unir()

    def _unir_quitar(self):
        sel = self.lista_unir.curselection()
        if sel:
            del self.archivos_unir[sel[0]]
            self._refrescar_lista_unir()

    def _unir_subir(self):
        sel = self.lista_unir.curselection()
        if sel and sel[0] > 0:
            i = sel[0]
            self.archivos_unir[i], self.archivos_unir[i-1] = \
                self.archivos_unir[i-1], self.archivos_unir[i]
            self._refrescar_lista_unir()
            self.lista_unir.selection_set(i-1)

    def _unir_bajar(self):
        sel = self.lista_unir.curselection()
        if sel and sel[0] < len(self.archivos_unir)-1:
            i = sel[0]
            self.archivos_unir[i], self.archivos_unir[i+1] = \
                self.archivos_unir[i+1], self.archivos_unir[i]
            self._refrescar_lista_unir()
            self.lista_unir.selection_set(i+1)

    def _unir_vaciar(self):
        self.archivos_unir.clear()
        self._refrescar_lista_unir()

    def _refrescar_lista_unir(self):
        self.lista_unir.delete(0, tk.END)
        for i, a in enumerate(self.archivos_unir, 1):
            self.lista_unir.insert(tk.END, f"  {i}.  {os.path.basename(a)}")
        n = len(self.archivos_unir)
        self.unir_count_lbl.config(text=f"{n} archivo{'s' if n!=1 else ''}")
        self.unir_dur_lbl.config(text="")
        if n >= 2:
            threading.Thread(target=self._calc_dur_unir, daemon=True).start()
        self._update_boton()

    def _calc_dur_unir(self):
        total = 0.0
        for a in self.archivos_unir:
            try:
                c = AudioFileClip(a)
                total += c.duration
                c.close()
            except Exception:
                pass
        self.root.after(0, self.unir_dur_lbl.config,
                        {'text': f"Total: {seg_a_mmss(total)}  ({total:.0f} s)"})


# ═════════════════════════════════════════════════════════
if __name__ == "__main__":
    if DND_OK:
        root = TkinterDnD.Tk()
    else:
        root = tk.Tk()
    app = EditorAudio(root)
    root.mainloop()
