# -*- coding: utf-8 -*-

import tkinter as tk
from tkinter import ttk, filedialog, colorchooser, messagebox
import threading, os, sys, tempfile, subprocess

import pygame
from moviepy import (VideoFileClip, TextClip, CompositeVideoClip,
                     ImageClip, concatenate_videoclips)
from moviepy.audio.io.AudioFileClip import AudioFileClip
from moviepy.video.fx import CrossFadeIn, CrossFadeOut, FadeIn, FadeOut
from PIL import Image, ImageTk

if sys.platform == 'win32':
    import ctypes
    ctypes.windll.kernel32.SetConsoleTitleW("VideoStudio")

# ── Paleta minimalista ────────────────────────────────────────────────────────
BG, CARD, BORDER = '#F5F5F5', '#FFFFFF', '#E0E0E0'
TEXT, TEXT_S     = '#212121', '#757575'
ACCENT           = '#1976D2'
GREEN            = '#388E3C'
RED              = '#C62828'
ORANGE           = '#E65100'
PURPLE           = '#6A1B9A'
SEL_BG           = '#BBDEFB'

FN  = ('Segoe UI', 9)
FNB = ('Segoe UI', 9,  'bold')
FNS = ('Segoe UI', 8)
FNT = ('Segoe UI', 11, 'bold')
FMO = ('Consolas', 9)


def fmt(s):
    return f"{int(s//60)}:{int(s%60):02d}"


def mkbtn(parent, text, cmd, bg=ACCENT, fg='white',
          w=None, state='normal', font=None):
    kw = dict(text=text, command=cmd, bg=bg, fg=fg,
              activebackground=bg, activeforeground=fg,
              relief='flat', font=font or FNB, state=state,
              cursor='hand2', bd=0, padx=10, pady=6)
    if w: kw['width'] = w
    return tk.Button(parent, **kw)


def crd(parent):
    """Card frame — devuelve (outer, inner)"""
    outer = tk.Frame(parent, bg=CARD,
                     highlightthickness=1, highlightbackground=BORDER)
    inner = tk.Frame(outer, bg=CARD, padx=8, pady=6)
    inner.pack(fill='both', expand=True)
    return outer, inner


# ── Línea de tiempo ───────────────────────────────────────────────────────────
class Timeline(tk.Canvas):
    PAD = 14; TY = 28; TH = 14; HW = 7

    def __init__(self, parent, on_seek=None, on_range=None, **kw):
        super().__init__(parent, height=70, bg=CARD,
                         highlightthickness=0, **kw)
        self.on_seek = on_seek; self.on_range = on_range
        self.duration = 0; self.current = 0
        self.in_t = 0; self.out_t = 0; self._drag = None
        self.bind('<Button-1>',        self._click)
        self.bind('<B1-Motion>',       self._motion)
        self.bind('<ButtonRelease-1>', self._release)
        self.bind('<Configure>',       lambda e: self._draw())

    def load(self, dur):
        self.duration = dur
        self.in_t, self.out_t, self.current = 0, dur, 0
        self._draw()

    def set_pos(self, t):
        self.current = max(0, min(t, self.duration)); self._draw()

    def set_in_out(self, a, b):
        self.in_t, self.out_t = a, b; self._draw()

    def get_in_out(self):
        return min(self.in_t, self.out_t), max(self.in_t, self.out_t)

    def _W(self): return max(1, self.winfo_width())

    def _t2x(self, t):
        if self.duration <= 0: return self.PAD
        return self.PAD + (t / self.duration) * (self._W() - 2*self.PAD)

    def _x2t(self, x):
        if self.duration <= 0: return 0
        return max(0.0, min(float(self.duration),
            (x - self.PAD) / (self._W() - 2*self.PAD) * self.duration))

    def _draw(self):
        self.delete('all')
        W = self._W()
        p, ty, th, hw = self.PAD, self.TY, self.TH, self.HW
        self.create_rectangle(p, ty, W-p, ty+th,
                               fill=BORDER, outline=BORDER, width=1)
        if self.duration <= 0:
            self.create_text(W//2, ty+th//2, text="Abre un video para empezar",
                             fill=TEXT_S, font=FNS); return
        x1 = self._t2x(min(self.in_t, self.out_t))
        x2 = self._t2x(max(self.in_t, self.out_t))
        self.create_rectangle(x1, ty, x2, ty+th, fill=SEL_BG, outline='')
        step = next((s for s in [.5,1,2,5,10,15,30,60,120,300,600]
                     if self.duration > 0 and
                     s/self.duration*(W-2*p) >= 50), 600)
        t = 0.0
        while t <= self.duration + 0.001:
            x = self._t2x(t)
            self.create_line(x, ty+th, x, ty+th+4, fill=TEXT_S)
            self.create_text(x, ty+th+12, text=fmt(t),
                             fill=TEXT_S, font=('Consolas', 7), anchor='center')
            t += step
        xin = self._t2x(self.in_t)
        self.create_rectangle(xin-hw, ty-2, xin+hw, ty+th+2,
                               fill=ACCENT, outline='white', width=1)
        self.create_text(xin, ty-10, text='IN', fill=ACCENT,
                         font=('Segoe UI', 7, 'bold'), anchor='center')
        xout = self._t2x(self.out_t)
        self.create_rectangle(xout-hw, ty-2, xout+hw, ty+th+2,
                               fill=ORANGE, outline='white', width=1)
        self.create_text(xout, ty-10, text='OUT', fill=ORANGE,
                         font=('Segoe UI', 7, 'bold'), anchor='center')
        xc = self._t2x(self.current)
        self.create_line(xc, 4, xc, ty+th+2, fill=RED, width=2)
        self.create_polygon(xc-5, 4, xc+5, 4, xc, 12, fill=RED, outline='')

    def _near(self, x):
        di = abs(x - self._t2x(self.in_t))
        do = abs(x - self._t2x(self.out_t))
        if di <= 10 and di <= do: return 'in'
        if do <= 10: return 'out'
        return None

    def _click(self, e):
        h = self._near(e.x)
        if h: self._drag = h
        else:
            self._drag = 'seek'
            if self.on_seek: self.on_seek(self._x2t(e.x))

    def _motion(self, e):
        t = self._x2t(e.x)
        if   self._drag == 'in':   self.in_t  = t; self._draw(); self._notify()
        elif self._drag == 'out':  self.out_t = t; self._draw(); self._notify()
        elif self._drag == 'seek':
            if self.on_seek: self.on_seek(t)

    def _release(self, e):
        self._drag = None; self._notify()

    def _notify(self):
        if self.on_range: self.on_range(*self.get_in_out())


# ══════════════════════════════ TAB: CORTADOR ════════════════════════════════
class TabCortador:
    def __init__(self, frame, root):
        self.frame = frame
        self.root  = root
        self.video_path   = None; self.video_clip = None
        self.duracion     = 0;    self.playing    = False
        self.current_time = 0;    self.update_job = None
        self.audio_loaded = False; self.temp_audio = None
        self.frags_g = []; self.frags_e = []
        self.v_sep      = tk.BooleanVar(value=False)
        self.v_trans    = tk.BooleanVar(value=False)
        self.v_trans_dur= tk.DoubleVar(value=0.5)
        self._build()

    def _build(self):
        body = tk.Frame(self.frame, bg=BG)
        body.pack(fill='both', expand=True, padx=10, pady=8)
        body.columnconfigure(0, weight=3)
        body.columnconfigure(1, weight=2, minsize=290)
        body.rowconfigure(0, weight=1)

        # ── Columna izquierda ─────────────────────────────────────────────
        left = tk.Frame(body, bg=BG)
        left.grid(row=0, column=0, sticky='nsew', padx=(0, 6))
        left.columnconfigure(0, weight=1)
        left.rowconfigure(1, weight=1)

        # Abrir video
        oc, oi = crd(left)
        oc.grid(row=0, column=0, sticky='ew', pady=(0, 4))
        r = tk.Frame(oi, bg=CARD)
        r.pack(fill='x')
        self.lbl_video = tk.Label(r, text="Ningún video seleccionado",
                                  fg=TEXT_S, bg=CARD, anchor='w', font=FN)
        self.lbl_video.pack(side='left', fill='x', expand=True)
        mkbtn(r, "📂 Abrir", self._open, GREEN).pack(side='right')
        self.lbl_info = tk.Label(oi, text="", fg=TEXT_S, bg=CARD,
                                 font=FNS, anchor='w')
        self.lbl_info.pack(fill='x')

        # Visor
        vc, vi = crd(left)
        vc.grid(row=1, column=0, sticky='nsew', pady=(0, 4))
        vi.pack_configure(padx=0, pady=0)
        self.visor = tk.Label(vi, bg='#111111')
        self.visor.pack(fill='both', expand=True)

        # Controles
        cc, ci = crd(left)
        cc.grid(row=2, column=0, sticky='ew', pady=(0, 4))
        ctrl = tk.Frame(ci, bg=CARD)
        ctrl.pack(fill='x')
        self.btn_play  = mkbtn(ctrl, "▶", self._toggle_play, GREEN,  w=3, state='disabled')
        self.btn_pause = mkbtn(ctrl, "⏸", self._pause,       ORANGE, w=3, state='disabled')
        self.btn_stop  = mkbtn(ctrl, "⏹", self._stop,        RED,    w=3, state='disabled')
        for b in (self.btn_play, self.btn_pause, self.btn_stop):
            b.pack(side='left', padx=(0, 3))
        tk.Label(ctrl, text="Vol", bg=CARD, fg=TEXT_S, font=FNS).pack(side='left', padx=(10, 2))
        self.vol = tk.Scale(ctrl, from_=0, to=100, orient='horizontal', length=60,
                            command=self._set_vol, bg=CARD, highlightthickness=0,
                            showvalue=0, troughcolor=BORDER, sliderrelief='flat')
        self.vol.set(70); self.vol.pack(side='left')
        self.lbl_time = tk.Label(ctrl, text="0:00 / 0:00",
                                 bg=CARD, fg=TEXT_S, font=FMO)
        self.lbl_time.pack(side='right', padx=4)
        tk.Label(ci, text="Espacio=Play  I=In  O=Out  ←/→=±1s  Mayús+←/→=±5s",
                 bg=CARD, fg=TEXT_S, font=('Segoe UI', 7)).pack()

        # Timeline
        tc, ti = crd(left)
        tc.grid(row=3, column=0, sticky='ew')
        hdr = tk.Frame(ti, bg=CARD)
        hdr.pack(fill='x')
        tk.Label(hdr, text="Línea de tiempo", font=FNB, fg=TEXT, bg=CARD).pack(side='left')
        tk.Label(hdr, text="Clic = saltar  ·  Arrastrar IN / OUT = ajustar",
                 font=FNS, fg=TEXT_S, bg=CARD).pack(side='left', padx=8)
        self.tl = Timeline(ti, on_seek=self._seek_to, on_range=self._on_range)
        self.tl.pack(fill='x', pady=(0, 4))
        tr = tk.Frame(ti, bg=CARD)
        tr.pack(fill='x')
        self.lbl_in  = tk.Label(tr, text="IN: –",       fg=ACCENT, bg=CARD, font=FNB)
        self.lbl_out = tk.Label(tr, text="OUT: –",      fg=ORANGE, bg=CARD, font=FNB)
        self.lbl_dur = tk.Label(tr, text="Duración: –", fg=GREEN,  bg=CARD, font=FNB)
        self.lbl_in.pack(side='left')
        self.lbl_out.pack(side='left', padx=14)
        self.lbl_dur.pack(side='right')
        mk = tk.Frame(ti, bg=CARD)
        mk.pack(fill='x', pady=(4, 0))
        self.btn_in     = mkbtn(mk, "[ I ] Marcar In",  self._mark_in,  ACCENT, state='disabled')
        self.btn_out    = mkbtn(mk, "[ O ] Marcar Out", self._mark_out, ORANGE, state='disabled')
        self.btn_go_in  = mkbtn(mk, "⏮ Ir a In",        self._go_in,   PURPLE, state='disabled')
        self.btn_go_out = mkbtn(mk, "⏭ Ir a Out",       self._go_out,  PURPLE, state='disabled')
        for b in (self.btn_in, self.btn_out, self.btn_go_in, self.btn_go_out):
            b.pack(side='left', padx=(0, 4))

        # ── Columna derecha ───────────────────────────────────────────────
        right = tk.Frame(body, bg=BG)
        right.grid(row=0, column=1, sticky='nsew')
        right.columnconfigure(0, weight=1)
        right.rowconfigure(0, weight=1)

        rc, ri = crd(right)
        rc.grid(row=0, column=0, sticky='nsew')
        ri.columnconfigure(0, weight=1)
        ri.rowconfigure(0, weight=1)

        # Sub-pestañas guardar / eliminar
        sty = ttk.Style()
        sty.configure('C.TNotebook',     background=CARD, borderwidth=0)
        sty.configure('C.TNotebook.Tab', background=BORDER,
                      foreground=TEXT, font=FNB, padding=[8, 5])
        sty.map('C.TNotebook.Tab',
                background=[('selected', ACCENT)],
                foreground=[('selected', 'maroon')])
        self.nb = ttk.Notebook(ri, style='C.TNotebook')
        self.nb.grid(row=0, column=0, sticky='nsew')
        self.nb.bind('<<NotebookTabChanged>>', self._on_frag_tab)
        self.tab_g = tk.Frame(self.nb, bg=CARD)
        self.tab_e = tk.Frame(self.nb, bg=CARD)
        self.nb.add(self.tab_g, text="  ✅ Guardar  ")
        self.nb.add(self.tab_e, text="  🗑️ Eliminar  ")
        self._build_frag_tab(self.tab_g, 'g')
        self._build_frag_tab(self.tab_e, 'e')

        # Opciones
        opt = tk.Frame(ri, bg=CARD, padx=4, pady=4)
        opt.grid(row=1, column=0, sticky='ew')
        tk.Label(opt, text="Opciones de exportación", font=FNB,
                 fg=TEXT, bg=CARD).pack(anchor='w', pady=(0, 4))
        tk.Checkbutton(opt, text="Guardar fragmentos en archivos separados",
                       variable=self.v_sep, bg=CARD, fg=TEXT, font=FN,
                       activebackground=CARD).pack(anchor='w')
        tr2 = tk.Frame(opt, bg=CARD)
        tr2.pack(fill='x', pady=(2, 0))
        tk.Checkbutton(tr2, text="Transiciones  dur:",
                       variable=self.v_trans, bg=CARD, fg=TEXT, font=FN,
                       activebackground=CARD, command=self._upd_trans).pack(side='left')
        self.spin = tk.Spinbox(tr2, from_=0.1, to=5.0, increment=0.1,
                               textvariable=self.v_trans_dur, width=4,
                               state='disabled', font=FN)
        self.spin.pack(side='left', padx=2)
        tk.Label(tr2, text="s", bg=CARD, font=FN).pack(side='left')

        self.btn_proc = tk.Button(
            ri, text="✂️  PROCESAR VIDEO", command=self._iniciar,
            bg=ACCENT, fg='white', font=('Segoe UI', 11, 'bold'),
            relief='flat', pady=10, cursor='hand2', state='disabled',
            activebackground=ACCENT, activeforeground='white')
        self.btn_proc.grid(row=2, column=0, sticky='ew', padx=4, pady=(6, 0))

        self.progress = ttk.Progressbar(ri, mode='indeterminate')
        self.progress.grid(row=3, column=0, sticky='ew', padx=4, pady=(4, 0))

        self.lbl_st = tk.Label(ri, text="Abre un video para empezar",
                               fg=TEXT_S, bg=CARD, font=FNS, anchor='w')
        self.lbl_st.grid(row=4, column=0, sticky='ew', padx=4, pady=(2, 6))

    def _build_frag_tab(self, frame, key):
        is_g  = (key == 'g')
        color = GREEN if is_g else RED
        top   = tk.Frame(frame, bg=CARD, pady=4, padx=4)
        top.pack(fill='x')
        add = mkbtn(top, "➕ Añadir fragmento" if is_g else "➕ Añadir a eliminar",
                    lambda k=key: self._add(k), color, state='disabled')
        add.pack(side='left')
        clr = mkbtn(top, "Limpiar", lambda k=key: self._clear(k),
                    BORDER, fg=TEXT, state='disabled')
        clr.pack(side='right')
        tk.Label(frame,
                 text=("Se concatenan y exportan en orden." if is_g
                       else "Se eliminan del video final."),
                 fg=TEXT_S, bg=CARD, font=FNS, anchor='w').pack(fill='x', padx=4)
        lf = tk.Frame(frame, bg=CARD, padx=4, pady=2)
        lf.pack(fill='both', expand=True)
        lst = tk.Listbox(lf, bg=BG, fg=TEXT, font=FMO, relief='flat',
                         selectbackground=SEL_BG, selectforeground=TEXT,
                         highlightthickness=1, highlightcolor=BORDER,
                         activestyle='none')
        lst.pack(side='left', fill='both', expand=True)
        scr = tk.Scrollbar(lf, command=lst.yview)
        scr.pack(side='right', fill='y')
        lst.config(yscrollcommand=scr.set)
        bot = tk.Frame(frame, bg=CARD, padx=4)
        bot.pack(fill='x', pady=(2, 6))
        rm  = mkbtn(bot, "❌ Quitar",
                    lambda k=key: self._remove(k), RED, state='disabled')
        rm.pack(side='left', padx=(0, 4))
        prv = mkbtn(bot, "▶ Previsualizar",
                    lambda k=key: self._preview(k), ACCENT, state='disabled')
        prv.pack(side='left')
        if is_g:
            self.btn_add_g=add; self.btn_clr_g=clr
            self.btn_rm_g=rm;   self.btn_prv_g=prv; self.lst_g=lst
        else:
            self.btn_add_e=add; self.btn_clr_e=clr
            self.btn_rm_e=rm;   self.btn_prv_e=prv; self.lst_e=lst

    # ── Atajos ────────────────────────────────────────────────────────────────
    def bind_keys(self):
        r = self.root
        r.bind('<space>',       lambda e: self._toggle_play())
        r.bind('<i>',           lambda e: self._mark_in())
        r.bind('<o>',           lambda e: self._mark_out())
        r.bind('<Left>',        lambda e: self._step(-1))
        r.bind('<Right>',       lambda e: self._step(+1))
        r.bind('<Shift-Left>',  lambda e: self._step(-5))
        r.bind('<Shift-Right>', lambda e: self._step(+5))
        r.bind('<Home>',        lambda e: self._seek_to(0))
        r.bind('<End>',         lambda e: self._seek_to(self.duracion))

    def unbind_keys(self):
        for s in ('<space>','<i>','<o>','<Left>','<Right>',
                  '<Shift-Left>','<Shift-Right>','<Home>','<End>'):
            try: self.root.unbind(s)
            except: pass

    def _step(self, d):
        if self.video_clip: self._seek_to(self.current_time + d)

    # ── Video ─────────────────────────────────────────────────────────────────
    def _open(self):
        f = filedialog.askopenfilename(
            title="Selecciona un video",
            filetypes=[("Videos", "*.mp4 *.avi *.mov *.mkv *.mpg *.mpeg"),
                       ("Todos", "*.*")])
        if not f: return
        self.video_path = f
        n = os.path.basename(f)
        self.lbl_video.config(text=f"📹 {n[:50]}{'…' if len(n)>50 else ''}", fg=TEXT)
        try:
            self.video_clip = VideoFileClip(f)
            self.duracion   = self.video_clip.duration
            res = f"{self.video_clip.size[0]}×{self.video_clip.size[1]}"
            self.lbl_info.config(
                text=f"{fmt(self.duracion)}  ·  {res}  ·  "
                     f"{self.video_clip.fps:.0f} fps", fg=TEXT_S)
            self._status("⏳ Extrayendo audio…")
            self.root.update()
            if self._ext_audio(f):
                self.audio_loaded = True
                pygame.mixer.music.load(self.temp_audio)
                pygame.mixer.music.set_volume(0.7)
            self.tl.load(self.duracion)
            self._show_frame(0)
            self.frags_g=[]; self.frags_e=[]; self._refresh()
            self._enable_all()
            self._on_range(0, self.duracion)
            self._status("✅ Video cargado")
        except Exception as e:
            self._status("❌ Error al cargar")
            messagebox.showerror("Error", str(e))

    def _ext_audio(self, path):
        try:
            if self.temp_audio and os.path.exists(self.temp_audio):
                os.unlink(self.temp_audio)
            self.temp_audio = tempfile.NamedTemporaryFile(
                suffix='.wav', delete=False).name
            si=None; fl=0
            if sys.platform == 'win32':
                si = subprocess.STARTUPINFO()
                si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                si.wShowWindow = subprocess.SW_HIDE
                fl = subprocess.CREATE_NO_WINDOW
            subprocess.run(
                ['ffmpeg','-i',path,'-vn','-acodec','pcm_s16le',
                 '-ar','44100','-ac','2','-y',self.temp_audio],
                capture_output=True, startupinfo=si, creationflags=fl)
            return (os.path.exists(self.temp_audio) and
                    os.path.getsize(self.temp_audio) > 0)
        except: return False

    def _enable_all(self):
        for w in (self.btn_play, self.btn_pause, self.btn_stop,
                  self.btn_in, self.btn_out, self.btn_go_in, self.btn_go_out,
                  self.btn_add_g, self.btn_rm_g, self.btn_clr_g, self.btn_prv_g,
                  self.btn_add_e, self.btn_rm_e, self.btn_clr_e, self.btn_prv_e,
                  self.btn_proc):
            w.config(state='normal')

    def _set_vol(self, v):
        if self.audio_loaded:
            pygame.mixer.music.set_volume(int(v)/100)

    # ── Reproducción ──────────────────────────────────────────────────────────
    def _show_frame(self, t):
        try:
            w = max(self.visor.winfo_width(),  1)
            h = max(self.visor.winfo_height(), 1)
            if w < 50: w, h = 520, 280
            img = Image.fromarray(self.video_clip.get_frame(t))
            img.thumbnail((w, h), Image.Resampling.LANCZOS)
            bg = Image.new('RGB', (w, h), '#111111')
            bg.paste(img, ((w-img.width)//2, (h-img.height)//2))
            tk_img = ImageTk.PhotoImage(bg)
            self.visor.config(image=tk_img); self.visor.image = tk_img
            self.current_time = t
            self.lbl_time.config(text=f"{fmt(t)} / {fmt(self.duracion)}")
            self.tl.set_pos(t)
        except: pass

    def _seek_to(self, t):
        was = self.playing
        if was: self._pause()
        t = max(0, min(t, self.duracion))
        self._show_frame(t)
        if was:
            self.playing = True
            self.btn_play.config(state='disabled')
            self.btn_pause.config(state='normal')
            if self.audio_loaded:
                try: pygame.mixer.music.play(start=t)
                except: pass
            self._loop()

    def _toggle_play(self):
        if not self.video_clip: return
        if self.playing: self._pause()
        else:
            self.playing = True
            self.btn_play.config(state='disabled')
            self.btn_pause.config(state='normal')
            if self.audio_loaded:
                try: pygame.mixer.music.play(start=self.current_time)
                except: pass
            self._loop()

    def _pause(self):
        self.playing = False
        self.btn_play.config(state='normal')
        self.btn_pause.config(state='disabled')
        if self.audio_loaded:
            try: pygame.mixer.music.pause()
            except: pass
        if self.update_job: self.root.after_cancel(self.update_job)

    def _stop(self):
        self._pause(); self.current_time = 0; self._show_frame(0)
        if self.audio_loaded:
            try: pygame.mixer.music.stop()
            except: pass

    def _loop(self):
        if self.playing and self.current_time < self.duracion:
            self._show_frame(self.current_time)
            self.current_time = min(self.current_time + 1/25, self.duracion)
            self.update_job = self.root.after(40, self._loop)
        elif self.current_time >= self.duracion:
            self._stop()

    # ── Marcado IN/OUT ────────────────────────────────────────────────────────
    def _mark_in(self):
        if not self.video_clip: return
        _, o = self.tl.get_in_out()
        self.tl.set_in_out(self.current_time, o)
        self._on_range(*self.tl.get_in_out())

    def _mark_out(self):
        if not self.video_clip: return
        i, _ = self.tl.get_in_out()
        self.tl.set_in_out(i, self.current_time)
        self._on_range(*self.tl.get_in_out())

    def _go_in(self):
        a, _ = self.tl.get_in_out(); self._seek_to(a)

    def _go_out(self):
        _, b = self.tl.get_in_out(); self._seek_to(b)

    def _on_range(self, a, b):
        self.lbl_in.config( text=f"IN:  {fmt(a)}")
        self.lbl_out.config(text=f"OUT: {fmt(b)}")
        self.lbl_dur.config(text=f"Duración: {fmt(b-a)}")

    # ── Fragmentos ────────────────────────────────────────────────────────────
    def _ftab(self):
        return 'g' if self.nb.index('current') == 0 else 'e'

    def _on_frag_tab(self, e):
        self.btn_proc.config(bg=ACCENT if self._ftab()=='g' else RED)

    def _add(self, key=None):
        key = key or self._ftab()
        a, b = self.tl.get_in_out()
        if b - a < 0.1:
            messagebox.showwarning("Aviso","El fragmento es muy corto.\nAjusta IN y OUT.")
            return
        (self.frags_g if key=='g' else self.frags_e).append({'inicio':a,'fin':b})
        self._refresh()
        self._status(f"✅ Fragmento añadido  {fmt(a)} → {fmt(b)}")

    def _remove(self, key=None):
        key = key or self._ftab()
        lst   = self.lst_g if key=='g' else self.lst_e
        frags = self.frags_g if key=='g' else self.frags_e
        sel   = lst.curselection()
        if not sel: self._status("Selecciona un fragmento primero"); return
        del frags[sel[0]]; self._refresh()

    def _clear(self, key=None):
        key = key or self._ftab()
        if key=='g': self.frags_g=[]
        else:        self.frags_e=[]
        self._refresh()

    def _refresh(self):
        for lst, frags in ((self.lst_g, self.frags_g),
                           (self.lst_e, self.frags_e)):
            lst.delete(0, tk.END)
            for i, f in enumerate(frags):
                lst.insert('end',
                    f"  {i+1:2d}.  {fmt(f['inicio'])}  →  "
                    f"{fmt(f['fin'])}   ({f['fin']-f['inicio']:.1f}s)")

    # ── Previsualización de fragmento ─────────────────────────────────────────
    def _preview(self, key=None):
        key   = key or self._ftab()
        lst   = self.lst_g if key == 'g' else self.lst_e
        frags = self.frags_g if key == 'g' else self.frags_e
        sel   = lst.curselection()
        if not sel:
            messagebox.showinfo("Aviso", "Selecciona un fragmento de la lista primero.")
            return
        if not self.video_clip:
            return
        frag = frags[sel[0]]
        ini, fin = frag['inicio'], frag['fin']

        # ── Ventana emergente ─────────────────────────────────────────────
        win = tk.Toplevel(self.root)
        win.title(f"▶ Previsualización  —  {fmt(ini)} → {fmt(fin)}")
        win.configure(bg=BG)
        win.resizable(True, True)
        # Tamaño proporcional al video, máx 720×520
        vw, vh = self.video_clip.size
        scale  = min(720/vw, 460/vh, 1.0)
        pw, ph = int(vw*scale), int(vh*scale)
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        wx = (sw - pw) // 2
        wy = max(10, (sh - ph - 130) // 2)
        win.geometry(f"{pw}x{ph+130}+{wx}+{wy}")
        win.transient(self.root)

        # Visor
        canvas = tk.Label(win, bg='#111111', width=pw, height=ph)
        canvas.pack(fill='both', expand=True)

        # Barra de progreso del fragmento
        prog_var = tk.DoubleVar(value=0)
        prog_bar = ttk.Progressbar(win, variable=prog_var, maximum=100)
        prog_bar.pack(fill='x', padx=8, pady=(4, 0))

        # Etiqueta de tiempo
        lbl_t = tk.Label(win, text=f"{fmt(ini)} / {fmt(fin)}",
                         bg=BG, fg=TEXT_S, font=FMO)
        lbl_t.pack()

        # Botones
        brow = tk.Frame(win, bg=BG)
        brow.pack(pady=6)

        # Estado interno de la ventana
        state = {'playing': False, 't': ini, 'job': None}

        def show(t):
            try:
                img = Image.fromarray(self.video_clip.get_frame(t))
                img.thumbnail((pw, ph), Image.Resampling.LANCZOS)
                bg_img = Image.new('RGB', (pw, ph), '#111111')
                bg_img.paste(img, ((pw-img.width)//2, (ph-img.height)//2))
                tk_img = ImageTk.PhotoImage(bg_img)
                canvas.config(image=tk_img); canvas.image = tk_img
                lbl_t.config(text=f"{fmt(t)} / {fmt(fin)}")
                pct = (t - ini) / max(fin - ini, 0.001) * 100
                prog_var.set(pct)
            except: pass

        def loop():
            if not state['playing']: return
            if state['t'] >= fin:
                state['t'] = ini        # rebobinar al final
                state['playing'] = False
                btn_play.config(text="▶ Play")
                show(ini)
                return
            show(state['t'])
            state['t'] = min(state['t'] + 1/25, fin)
            state['job'] = win.after(40, loop)

        def play():
            if state['t'] >= fin: state['t'] = ini
            state['playing'] = True
            btn_play.config(text="⏸ Pausa")
            loop()

        def pause():
            state['playing'] = False
            if state['job']: win.after_cancel(state['job'])
            btn_play.config(text="▶ Play")

        def toggle():
            if state['playing']: pause()
            else: play()

        def stop():
            pause(); state['t'] = ini; show(ini)
            btn_play.config(text="▶ Play")

        def on_close():
            pause()
            win.destroy()

        btn_play = mkbtn(brow, "▶ Play", toggle, GREEN)
        btn_play.pack(side='left', padx=(0, 6))
        mkbtn(brow, "⏹ Stop", stop, RED).pack(side='left', padx=6)
        mkbtn(brow, "✖ Cerrar", on_close, BORDER, fg=TEXT).pack(side='left', padx=6)

        win.protocol("WM_DELETE_WINDOW", on_close)

        # Mostrar primer frame al abrir
        show(ini)
        # Arrancar reproducción automáticamente
        win.after(200, play)

    # ── Procesamiento ─────────────────────────────────────────────────────────
    def _iniciar(self):
        t = self._ftab()
        if t=='g' and not self.frags_g:
            messagebox.showwarning("Aviso","No hay fragmentos en «Guardar»."); return
        if t=='e' and not self.frags_e:
            messagebox.showwarning("Aviso","No hay fragmentos en «Eliminar»."); return
        threading.Thread(target=self._proc, args=(t,), daemon=True).start()

    def _proc(self, tab):
        try:
            self.btn_proc.config(state='disabled', bg='#BDBDBD')
            self.progress.start()
            if tab=='g':
                self._sep() if self.v_sep.get() else self._concat()
            else:
                self._elim()
        except Exception as e:
            self._status("❌ Error")
            messagebox.showerror("Error", str(e))
        finally:
            self.progress.stop()
            if self.video_path:
                self.btn_proc.config(
                    state='normal',
                    bg=ACCENT if self._ftab()=='g' else RED)

    def _concat(self):
        dest = filedialog.asksaveasfilename(
            title="Guardar video recortado", defaultextension=".mp4",
            filetypes=[("MP4","*.mp4")], initialfile="video_recortado.mp4")
        if not dest: return
        self._status("💾 Concatenando fragmentos…")
        clip  = VideoFileClip(self.video_path)
        frags = sorted(self.frags_g, key=lambda x: x['inicio'])
        clips = [clip.subclipped(f['inicio'],f['fin'])
                 for f in frags if f['fin']-f['inicio']>0.1]
        if not clips:
            messagebox.showwarning("Aviso","No hay fragmentos válidos.")
            clip.close(); return
        if self.v_trans.get() and len(clips) > 1:
            d = self.v_trans_dur.get()
            proc = []
            for i, c in enumerate(clips):
                if i > 0:            c = CrossFadeIn(d).apply(c)
                if i < len(clips)-1: c = CrossFadeOut(d).apply(c)
                proc.append(c)
            final = concatenate_videoclips(proc, method='compose')
        else:
            final = concatenate_videoclips(clips)
        final.write_videofile(dest, logger=None, codec='libx264', audio_codec='aac')
        for c in clips: c.close()
        final.close(); clip.close()
        dur = sum(f['fin']-f['inicio'] for f in frags)
        self._status("✅ Video exportado")
        messagebox.showinfo("✅ Listo",
            f"Guardado en:\n{dest}\n\nFragmentos: {len(frags)}  ·  Duración: {fmt(dur)}")

    def _sep(self):
        carpeta = filedialog.askdirectory(title="Carpeta para los fragmentos")
        if not carpeta: return
        self._status("💾 Exportando fragmentos…")
        clip = VideoFileClip(self.video_path); n = 0
        for i, f in enumerate(self.frags_g, 1):
            if f['fin']-f['inicio'] < 0.1: continue
            nom = (f"frag_{i:02d}_{fmt(f['inicio']).replace(':','-')}"
                   f"_a_{fmt(f['fin']).replace(':','-')}.mp4")
            c = clip.subclipped(f['inicio'], f['fin'])
            c.write_videofile(os.path.join(carpeta, nom),
                              logger=None, codec='libx264', audio_codec='aac')
            c.close(); n += 1
        clip.close()
        self._status("✅ Fragmentos exportados")
        messagebox.showinfo("✅ Listo", f"Guardados {n} archivos en:\n{carpeta}")

    def _elim(self):
        dest = filedialog.asksaveasfilename(
            title="Guardar video editado", defaultextension=".mp4",
            filetypes=[("MP4","*.mp4")], initialfile="video_editado.mp4")
        if not dest: return
        self._status("💾 Eliminando fragmentos…")
        clip   = VideoFileClip(self.video_path)
        elim   = sorted(self.frags_e, key=lambda x: x['inicio'])
        tramos = []; cur = 0.0
        for f in elim:
            if f['inicio'] > cur: tramos.append((cur, f['inicio']))
            cur = max(cur, f['fin'])
        if cur < self.duracion: tramos.append((cur, self.duracion))
        clips = [clip.subclipped(a, b) for a, b in tramos if b-a > 0.1]
        if not clips:
            messagebox.showwarning("Aviso","No queda nada del video.")
            clip.close(); return
        final = concatenate_videoclips(clips) if len(clips)>1 else clips[0]
        final.write_videofile(dest, logger=None, codec='libx264', audio_codec='aac')
        for c in clips: c.close()
        if len(clips)>1: final.close()
        clip.close()
        self._status("✅ Video exportado")
        messagebox.showinfo("✅ Listo",
            f"Guardado en:\n{dest}\n\n"
            f"Eliminados: {len(elim)}  ·  "
            f"Original: {fmt(self.duracion)}  →  Final: {fmt(sum(b-a for a,b in tramos))}")

    def _status(self, msg):
        col = (GREEN if msg.startswith("✅") else
               RED   if msg.startswith("❌") else
               ORANGE if msg.startswith(("💾","⏳")) else TEXT_S)
        self.lbl_st.config(text=msg, fg=col)

    def _upd_trans(self):
        self.spin.config(state='normal' if self.v_trans.get() else 'disabled')


# ══════════════════════════════ TAB: EDITOR ══════════════════════════════════
class TabEditor:
    def __init__(self, frame, root):
        self.frame = frame; self.root = root
        self.video_paths   = {}
        self.color_sel     = 'white'
        self.pos_custom    = None
        self.lista_textos  = []
        self.audio_path    = None
        self.caratula_path = None
        self.contra_path   = None
        self.mapa_fuentes  = self._cargar_fuentes()
        self._build()

    def _cargar_fuentes(self):
        mapa = {}
        # 1. Fuentes del sistema Windows
        sys_fonts = r"C:\Windows\Fonts"
        if os.path.exists(sys_fonts):
            for f in os.listdir(sys_fonts):
                if f.lower().endswith('.ttf'):
                    n = os.path.splitext(f)[0].replace('_', ' ').title()
                    mapa[n] = os.path.join(sys_fonts, f)
        # 2. Carpeta local fonts/ (tiene prioridad si hay nombre duplicado)
        local = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fonts")
        if os.path.exists(local):
            for f in os.listdir(local):
                if f.lower().endswith('.ttf'):
                    n = os.path.splitext(f)[0].replace('_', ' ').title()
                    mapa[n] = os.path.join(local, f)
        return mapa or {"Arial": "Arial", "Calibri": "Calibri",
                        "Times New Roman": "Times New Roman"}

    def _build(self):
        sty = ttk.Style()
        sty.configure('E.TNotebook',     background=BG,    borderwidth=0)
        sty.configure('E.TNotebook.Tab', background=BORDER,
                      foreground=TEXT, font=FNS, padding=[8, 5])
        sty.map('E.TNotebook.Tab',
                background=[('selected', PURPLE)],
                foreground=[('selected', 'maroon')])
        nb = ttk.Notebook(self.frame, style='E.TNotebook')
        nb.pack(fill='both', expand=True, padx=8, pady=6)
        for label, builder in [
            ("📝 Texto Simple",     self._build_texto),
            ("📚 Múltiples textos", self._build_multi),
            ("✨ Efectos",          self._build_efectos),
            ("🎵 Música",           self._build_musica),
            ("✂️ Recortar",         self._build_recortar),
            ("🎬 Carátulas",        self._build_caratulas),
            ("💧 Marca de agua",    self._build_watermark),
            ("⚡ Velocidad",        self._build_velocidad),
            ("⬛ Encuadre",         self._build_crop),
            ("💬 Subtítulos .SRT",  self._build_srt),
        ]:
            tab = tk.Frame(nb, bg=CARD)
            nb.add(tab, text=f"  {label}  ")
            builder(tab)

    def _scrollable(self, parent):
        """Devuelve un frame interior con scroll vertical"""
        canvas = tk.Canvas(parent, bg=CARD, highlightthickness=0)
        vsb    = tk.Scrollbar(parent, orient='vertical', command=canvas.yview)
        canvas.configure(yscrollcommand=vsb.set)
        vsb.pack(side='right', fill='y')
        canvas.pack(fill='both', expand=True)
        inner = tk.Frame(canvas, bg=CARD)
        wid   = canvas.create_window((0,0), window=inner, anchor='nw')
        inner.bind('<Configure>',
            lambda e: canvas.configure(scrollregion=canvas.bbox('all')))
        canvas.bind('<Configure>',
            lambda e: canvas.itemconfig(wid, width=e.width))
        canvas.bind('<MouseWheel>',
            lambda e: canvas.yview_scroll(int(-1*(e.delta/120)), 'units'))
        return inner

    def _video_row(self, parent, pid):
        row = tk.Frame(parent, bg=CARD)
        row.pack(fill='x', padx=6, pady=(6, 2))
        lbl  = tk.Label(row, text="Ningún video seleccionado",
                        fg=TEXT_S, bg=CARD, anchor='w', font=FN)
        lbl.pack(side='left', fill='x', expand=True)
        info = tk.Label(parent, text="", fg=TEXT_S, bg=CARD, font=FNS, anchor='w')
        def sel():
            f = filedialog.askopenfilename(
                title="Seleccionar video",
                filetypes=[("Videos","*.mp4 *.avi *.mov *.mkv"),("Todos","*.*")])
            if f:
                self.video_paths[pid] = f
                lbl.config(text=f"📹 {os.path.basename(f)[:45]}", fg=TEXT)
                try:
                    c = VideoFileClip(f)
                    info.config(text=f"{fmt(c.duration)}  ·  {c.size[0]}×{c.size[1]}")
                    c.close()
                except: pass
        mkbtn(row, "📂 Abrir", sel, GREEN).pack(side='right')
        info.pack(fill='x', padx=6)
        tk.Frame(parent, bg=BORDER, height=1).pack(fill='x', padx=6, pady=6)
        return lbl, info

    def _prog_row(self, parent):
        prog = ttk.Progressbar(parent, mode='indeterminate')
        prog.pack(fill='x', padx=6, pady=(4,0))
        st = tk.Label(parent, text="✅ Listo", fg=GREEN, bg=CARD, font=FNS)
        st.pack()
        return prog, st

    def _st(self, lbl, msg):
        col = (GREEN if msg.startswith("✅") else
               RED   if msg.startswith("❌") else ORANGE)
        lbl.config(text=msg, fg=col)

    # ── Texto simple ──────────────────────────────────────────────────────────
    def _build_texto(self, f):
        p = self._scrollable(f)
        tk.Label(p, text="📝 Añadir texto al video", font=FNB,
                 fg=PURPLE, bg=CARD).pack(anchor='w', padx=6, pady=(8,4))
        pid = 'texto'
        self._video_row(p, pid)
        cfg = tk.Frame(p, bg=CARD, padx=10)
        cfg.pack(fill='x')

        def row(lbl, r):
            tk.Label(cfg, text=lbl, bg=CARD, font=FN, anchor='w').grid(
                row=r, column=0, sticky='w', pady=3, padx=(0,8))

        row("Texto:", 0)
        self.t_texto = tk.Entry(cfg, width=34, font=FN)
        self.t_texto.grid(row=0, column=1, columnspan=3, pady=3, sticky='w')
        self.t_texto.insert(0, "¡Hola Mundo!")

        row("Posición:", 1)
        pf = tk.Frame(cfg, bg=CARD)
        pf.grid(row=1, column=1, columnspan=3, sticky='w', pady=3)
        self.t_pos = ttk.Combobox(
            pf, values=['center','top','bottom','left','right','personalizada'], width=14)
        self.t_pos.pack(side='left'); self.t_pos.set('center')
        mkbtn(pf, "👆 Elegir con clic",
              lambda: self._pos_preview(pid), ORANGE,
              font=FNS).pack(side='left', padx=8)
        self.t_pos_lbl = tk.Label(pf, text="", fg=ACCENT, bg=CARD, font=FNS)
        self.t_pos_lbl.pack(side='left')

        row("Tamaño:", 2)
        self.t_size = tk.Scale(cfg, from_=10, to=150, orient='horizontal', length=220,
                               bg=CARD, highlightthickness=0, troughcolor=BORDER)
        self.t_size.grid(row=2, column=1, columnspan=2, sticky='w', pady=3)
        self.t_size.set(50)

        row("Fuente:", 3)
        self.t_fuente = ttk.Combobox(
            cfg, values=sorted(self.mapa_fuentes.keys()), width=28)
        self.t_fuente.grid(row=3, column=1, columnspan=2, pady=3, sticky='w')
        self.t_fuente.set('Arial')

        row("Color:", 4)
        cf2 = tk.Frame(cfg, bg=CARD)
        cf2.grid(row=4, column=1, sticky='w', pady=3)
        mkbtn(cf2, "Elegir", self._pick_color, ACCENT, font=FNS).pack(side='left')
        self.t_color_lbl = tk.Label(cf2, text="   ", bg='white',
                                    width=3, relief='sunken')
        self.t_color_lbl.pack(side='left', padx=4)

        row("Borde:", 5)
        self.t_borde = tk.BooleanVar(value=True)
        tk.Checkbutton(cfg, text="Borde negro", variable=self.t_borde,
                       bg=CARD, font=FN, activebackground=CARD).grid(
            row=5, column=1, sticky='w')

        row("Duración:", 6)
        self.t_dur_full = tk.BooleanVar(value=True)
        tk.Radiobutton(cfg, text="Video completo", variable=self.t_dur_full, value=True,
                       bg=CARD, font=FN, activebackground=CARD).grid(
            row=6, column=1, sticky='w')
        drf = tk.Frame(cfg, bg=CARD)
        drf.grid(row=7, column=1, sticky='w')
        tk.Radiobutton(drf, text="Personalizada:", variable=self.t_dur_full, value=False,
                       bg=CARD, font=FN, activebackground=CARD).pack(side='left')
        self.t_dur_e = tk.Entry(drf, width=6, font=FN)
        self.t_dur_e.pack(side='left', padx=4)
        self.t_dur_e.insert(0, "5"); self.t_dur_e.config(state='disabled')
        tk.Label(drf, text="seg", bg=CARD, font=FN).pack(side='left')
        def _upd(*_):
            self.t_dur_e.config(state='normal' if not self.t_dur_full.get() else 'disabled')
        self.t_dur_full.trace('w', _upd)

        self.t_prog, self.t_st_lbl = self._prog_row(p)
        mkbtn(p, "📝 PROCESAR TEXTO",
              lambda: self._proc_texto(pid), PURPLE,
              font=('Segoe UI',11,'bold')).pack(pady=8, padx=6, fill='x')

    def _pos_preview(self, pid):
        vp = self.video_paths.get(pid)
        if not vp:
            messagebox.showerror("Error", "Selecciona un video primero"); return
        if not self.t_texto.get():
            messagebox.showerror("Error", "Escribe un texto primero"); return

        try:
            clip = VideoFileClip(vp)
            vw, vh = clip.size

            # Tamaño de la ventana proporcional al video, máx 800×520
            scale  = min(800/vw, 520/vh, 1.0)
            pw, ph = int(vw*scale), int(vh*scale)
            sw = self.root.winfo_screenwidth()
            sh = self.root.winfo_screenheight()
            wx = (sw - pw) // 2
            wy = max(10, (sh - ph - 160) // 2)

            win = tk.Toplevel(self.root)
            win.title("👆 Haz clic para posicionar el texto")
            win.configure(bg=BG)
            win.geometry(f"{pw}x{ph+120}+{wx}+{wy}")
            win.resizable(False, False)
            win.transient(self.root)
            win.grab_set()

            # Controles de tiempo
            top = tk.Frame(win, bg=BG, pady=4)
            top.pack(fill='x', padx=8)
            tk.Label(top, text="Frame en segundo:", bg=BG, font=FNS).pack(side='left')
            t_entry = tk.Entry(top, width=6, font=FN)
            t_entry.pack(side='left', padx=4)
            t_entry.insert(0, f"{clip.duration/2:.1f}")

            # Canvas para mostrar el frame
            canvas = tk.Canvas(win, width=pw, height=ph,
                               bg='#111111', cursor='crosshair',
                               highlightthickness=0)
            canvas.pack()

            # Info de posición
            info = tk.Frame(win, bg=BG, pady=4)
            info.pack(fill='x', padx=8)
            lbl_xy = tk.Label(info, text="Haz clic en el video para elegir la posición",
                              fg=TEXT_S, bg=BG, font=FNS)
            lbl_xy.pack(side='left')

            state = {'x': None, 'y': None, 'tk_img': None}

            def cargar_frame(*_):
                try:
                    t = float(t_entry.get())
                    t = max(0, min(t, clip.duration - 0.01))
                    frame = clip.get_frame(t)
                    img   = Image.fromarray(frame)
                    img   = img.resize((pw, ph), Image.Resampling.LANCZOS)
                    tk_img = ImageTk.PhotoImage(img)
                    state['tk_img'] = tk_img
                    canvas.delete('all')
                    canvas.create_image(0, 0, anchor='nw', image=tk_img)
                    # Redibujar marcador si ya hay posición
                    if state['x'] is not None:
                        _dibujar_marcador(state['x'], state['y'])
                except: pass

            def _dibujar_marcador(cx, cy):
                canvas.delete('marker')
                r = 8
                canvas.create_oval(cx-r, cy-r, cx+r, cy+r,
                                   outline=RED, width=2, tags='marker')
                canvas.create_line(cx-14, cy, cx+14, cy,
                                   fill=RED, width=2, tags='marker')
                canvas.create_line(cx, cy-14, cx, cy+14,
                                   fill=RED, width=2, tags='marker')
                # Etiqueta con el texto encima
                canvas.create_text(cx, cy-22,
                                   text=self.t_texto.get(),
                                   fill='yellow', font=('Arial', 11, 'bold'),
                                   tags='marker')

            def on_click(e):
                state['x'], state['y'] = e.x, e.y
                _dibujar_marcador(e.x, e.y)
                # Convertir coordenadas de pantalla a coordenadas del video real
                rx = int(e.x / scale)
                ry = int(e.y / scale)
                lbl_xy.config(text=f"Posición: X={rx}  Y={ry}", fg=ACCENT)

            def actualizar_frame():
                cargar_frame()

            def usar():
                if state['x'] is None:
                    messagebox.showwarning("Aviso",
                        "Haz clic en el video para elegir la posición")
                    return
                rx = int(state['x'] / scale)
                ry = int(state['y'] / scale)
                self.pos_custom = (rx, ry)
                self.t_pos.set('personalizada')
                self.t_pos_lbl.config(text=f"X={rx}  Y={ry}")
                clip.close()
                win.destroy()

            def cancelar():
                clip.close()
                win.destroy()

            mkbtn(info, "Actualizar frame", actualizar_frame,
                  ACCENT, font=FNS).pack(side='right', padx=(8,0))

            btns = tk.Frame(win, bg=BG, pady=6)
            btns.pack(fill='x', padx=8)
            mkbtn(btns, "✅ Usar esta posición", usar,
                  GREEN, font=FNB).pack(side='left', padx=(0,8))
            mkbtn(btns, "✖ Cancelar", cancelar,
                  BORDER, fg=TEXT, font=FNB).pack(side='left')

            canvas.bind('<Button-1>', on_click)
            win.protocol("WM_DELETE_WINDOW", cancelar)
            cargar_frame()

        except Exception as e:
            messagebox.showerror("Error", f"No se pudo abrir la previsualización:\n{e}")

    def _pick_color(self):
        c = colorchooser.askcolor(title="Seleccionar color",
                                  initialcolor=self.color_sel)[1]
        if c: self.color_sel=c; self.t_color_lbl.config(bg=c)

    def _proc_texto(self, pid):
        vp = self.video_paths.get(pid)
        if not vp: messagebox.showerror("Error","Selecciona un video"); return
        if not self.t_texto.get(): messagebox.showerror("Error","Escribe un texto"); return
        threading.Thread(target=self._proc_texto_t, args=(vp,), daemon=True).start()

    def _proc_texto_t(self, vp):
        self.t_prog.start(); self._st(self.t_st_lbl,"⏳ Procesando…")
        try:
            clip = VideoFileClip(vp)
            dur  = clip.duration if self.t_dur_full.get() else float(self.t_dur_e.get())
            fn   = self.mapa_fuentes.get(self.t_fuente.get(), self.t_fuente.get())
            tc   = TextClip(font=fn, text=self.t_texto.get(),
                            font_size=self.t_size.get(), color=self.color_sel,
                            stroke_color='black' if self.t_borde.get() else None,
                            stroke_width=2 if self.t_borde.get() else 0
                            ).with_duration(dur)
            pos = self.t_pos.get()
            if pos=='center':     tc = tc.with_position(('center','center'))
            elif pos=='top':      tc = tc.with_position(('center',50))
            elif pos=='bottom':   tc = tc.with_position(('center',clip.h-100))
            elif pos=='left':     tc = tc.with_position((50,'center'))
            elif pos=='right':    tc = tc.with_position((clip.w-200,'center'))
            elif pos=='personalizada' and self.pos_custom:
                tc = tc.with_position(self.pos_custom)
            vf   = CompositeVideoClip([clip, tc])
            dest = filedialog.asksaveasfilename(
                defaultextension=".mp4", filetypes=[("MP4","*.mp4")],
                initialfile="video_con_texto.mp4")
            if dest:
                vf.write_videofile(dest, logger=None)
                self._st(self.t_st_lbl, f"✅ Guardado: {os.path.basename(dest)}")
            else:
                self._st(self.t_st_lbl,"⏸️ Cancelado")
            clip.close(); tc.close(); vf.close()
        except Exception as e:
            self._st(self.t_st_lbl, f"❌ Error: {e}")
        self.t_prog.stop()

    # ── Múltiples textos ──────────────────────────────────────────────────────
    def _build_multi(self, f):
        pid = 'multi'
        self._video_row(f, pid)
        tk.Label(f, text="Textos programados:", font=FNB,
                 fg=TEXT, bg=CARD).pack(anchor='w', padx=6)
        lf = tk.Frame(f, bg=CARD, padx=6)
        lf.pack(fill='x')
        self.m_lst = tk.Listbox(lf, height=5, font=FMO, bg=BG,
                                selectbackground=SEL_BG, relief='flat',
                                highlightthickness=1, highlightcolor=BORDER)
        self.m_lst.pack(side='left', fill='x', expand=True)
        scr = tk.Scrollbar(lf, command=self.m_lst.yview)
        scr.pack(side='right', fill='y')
        self.m_lst.config(yscrollcommand=scr.set)
        brow = tk.Frame(f, bg=CARD, padx=6)
        brow.pack(fill='x', pady=2)
        mkbtn(brow,"➕ Añadir",   self._m_add,    GREEN, font=FNS).pack(side='left',padx=(0,3))
        mkbtn(brow,"✏️ Editar",   self._m_edit,   ORANGE,font=FNS).pack(side='left',padx=3)
        mkbtn(brow,"❌ Eliminar", self._m_remove, RED,   font=FNS).pack(side='left',padx=3)
        lf2 = tk.LabelFrame(f, text="Nuevo texto", bg=CARD, padx=8, pady=6, font=FNB)
        lf2.pack(fill='x', padx=6, pady=4)
        tk.Label(lf2,text="Texto:", bg=CARD,font=FN).grid(row=0,column=0,sticky='w')
        self.m_texto = tk.Entry(lf2, width=38, font=FN)
        self.m_texto.grid(row=0,column=1,columnspan=4,padx=4,pady=2,sticky='w')
        tk.Label(lf2,text="Inicio:",bg=CARD,font=FN).grid(row=1,column=0,sticky='w',pady=4)
        self.m_ini = tk.Entry(lf2, width=6, font=FN)
        self.m_ini.grid(row=1,column=1,sticky='w',padx=4); self.m_ini.insert(0,"0")
        tk.Label(lf2,text="Dur:",bg=CARD,font=FN).grid(row=1,column=2,sticky='w')
        self.m_dur = tk.Entry(lf2, width=6, font=FN)
        self.m_dur.grid(row=1,column=3,sticky='w',padx=4); self.m_dur.insert(0,"5")
        tk.Label(lf2,text="Tamaño:",bg=CARD,font=FN).grid(row=2,column=0,sticky='w',pady=4)
        self.m_tam = tk.Scale(lf2, from_=10, to=100, orient='horizontal', length=140,
                              bg=CARD, highlightthickness=0, troughcolor=BORDER)
        self.m_tam.grid(row=2,column=1,columnspan=2,sticky='w',padx=4)
        self.m_tam.set(20)
        tk.Label(lf2,text="Pos:",bg=CARD,font=FN).grid(row=2,column=3,sticky='w')
        self.m_pos = ttk.Combobox(
            lf2, values=['center','top','bottom','left','right'], width=10)
        self.m_pos.grid(row=2,column=4,sticky='w',padx=4); self.m_pos.set('center')
        self.m_prog, self.m_st_lbl = self._prog_row(f)
        mkbtn(f,"📚 PROCESAR MÚLTIPLES TEXTOS",
              lambda: self._proc_multi(pid), PURPLE,
              font=('Segoe UI',11,'bold')).pack(pady=8, padx=6, fill='x')

    def _m_add(self):
        txt = self.m_texto.get()
        if not txt: messagebox.showwarning("Aviso","El texto no puede estar vacío"); return
        try: ini=float(self.m_ini.get()); dur=float(self.m_dur.get()); tam=int(self.m_tam.get())
        except: messagebox.showwarning("Aviso","Inicio, duración y tamaño deben ser números"); return
        pos = self.m_pos.get()
        self.lista_textos.append({'texto':txt,'inicio':ini,'duracion':dur,'tamaño':tam,'posicion':pos})
        self.m_lst.insert(tk.END, f"{txt}  |  In:{ini}s  Dur:{dur}s  Tam:{tam}  Pos:{pos}")
        self.m_texto.delete(0,tk.END)

    def _m_edit(self):
        sel = self.m_lst.curselection()
        if not sel: messagebox.showwarning("Aviso","Selecciona un texto para editar"); return
        idx = sel[0]; d = self.lista_textos[idx]
        self.m_texto.delete(0,tk.END); self.m_texto.insert(0,d['texto'])
        self.m_ini.delete(0,tk.END);   self.m_ini.insert(0,str(d['inicio']))
        self.m_dur.delete(0,tk.END);   self.m_dur.insert(0,str(d['duracion']))
        self.m_tam.set(d['tamaño']); self.m_pos.set(d['posicion'])
        self.m_lst.delete(idx); self.lista_textos.pop(idx)

    def _m_remove(self):
        sel = self.m_lst.curselection()
        if sel: self.m_lst.delete(sel[0]); self.lista_textos.pop(sel[0])

    def _proc_multi(self, pid):
        vp = self.video_paths.get(pid)
        if not vp: messagebox.showerror("Error","Selecciona un video"); return
        if not self.lista_textos: messagebox.showerror("Error","Añade al menos un texto"); return
        threading.Thread(target=self._proc_multi_t, args=(vp,), daemon=True).start()

    def _proc_multi_t(self, vp):
        self.m_prog.start(); self._st(self.m_st_lbl,"⏳ Procesando…")
        try:
            clip = VideoFileClip(vp); tcs = []
            for item in self.lista_textos:
                tc = TextClip(font=self.mapa_fuentes.get('Arial','Arial'),
                              text=item['texto'], font_size=item['tamaño'],
                              color='white', stroke_color='black', stroke_width=2
                              ).with_duration(item['duracion']).with_start(item['inicio'])
                p = item['posicion']
                if p=='center':   tc=tc.with_position(('center','center'))
                elif p=='top':    tc=tc.with_position(('center',50))
                elif p=='bottom': tc=tc.with_position(('center',clip.h-100))
                elif p=='left':   tc=tc.with_position((50,'center'))
                elif p=='right':  tc=tc.with_position((clip.w-200,'center'))
                tcs.append(tc)
            vf   = CompositeVideoClip([clip]+tcs)
            dest = filedialog.asksaveasfilename(
                defaultextension=".mp4", filetypes=[("MP4","*.mp4")],
                initialfile="video_multi_texto.mp4")
            if dest: vf.write_videofile(dest, logger=None); self._st(self.m_st_lbl,"✅ Guardado")
            else:    self._st(self.m_st_lbl,"⏸️ Cancelado")
            clip.close(); [c.close() for c in tcs]; vf.close()
        except Exception as e: self._st(self.m_st_lbl, f"❌ {e}")
        self.m_prog.stop()

    # ── Efectos ───────────────────────────────────────────────────────────────
    def _build_efectos(self, f):
        pid = 'efectos'
        self._video_row(f, pid)
        cfg = tk.Frame(f, bg=CARD, padx=10)
        cfg.pack(fill='x')
        self.e_fadein  = tk.BooleanVar(value=False)
        self.e_fadeout = tk.BooleanVar(value=False)
        tk.Label(cfg,text="Fade In:",font=FNB,bg=CARD).grid(row=0,column=0,sticky='w',pady=4)
        tk.Checkbutton(cfg,text="Activar",variable=self.e_fadein,
                       bg=CARD,font=FN,activebackground=CARD).grid(row=0,column=1,sticky='w')
        tk.Label(cfg,text="Duración (s):",bg=CARD,font=FN).grid(row=1,column=0,sticky='w',pady=4)
        self.e_fi_dur = tk.Entry(cfg, width=8, font=FN)
        self.e_fi_dur.grid(row=1,column=1,sticky='w',padx=4); self.e_fi_dur.insert(0,"2")
        tk.Label(cfg,text="Fade Out:",font=FNB,bg=CARD).grid(row=2,column=0,sticky='w',pady=4)
        tk.Checkbutton(cfg,text="Activar",variable=self.e_fadeout,
                       bg=CARD,font=FN,activebackground=CARD).grid(row=2,column=1,sticky='w')
        tk.Label(cfg,text="Duración (s):",bg=CARD,font=FN).grid(row=3,column=0,sticky='w',pady=4)
        self.e_fo_dur = tk.Entry(cfg, width=8, font=FN)
        self.e_fo_dur.grid(row=3,column=1,sticky='w',padx=4); self.e_fo_dur.insert(0,"2")
        self.ef_prog, self.ef_st_lbl = self._prog_row(f)
        mkbtn(f,"✨ APLICAR EFECTOS",
              lambda: self._proc_efectos(pid), ORANGE,
              font=('Segoe UI',11,'bold')).pack(pady=8, padx=6, fill='x')

    def _proc_efectos(self, pid):
        vp = self.video_paths.get(pid)
        if not vp: messagebox.showerror("Error","Selecciona un video"); return
        threading.Thread(target=self._proc_efectos_t, args=(vp,), daemon=True).start()

    def _proc_efectos_t(self, vp):
        self.ef_prog.start(); self._st(self.ef_st_lbl,"⏳ Procesando…")
        try:
            clip = VideoFileClip(vp)
            if self.e_fadein.get():  clip=clip.with_effects([FadeIn(float(self.e_fi_dur.get()))])
            if self.e_fadeout.get(): clip=clip.with_effects([FadeOut(float(self.e_fo_dur.get()))])
            dest = filedialog.asksaveasfilename(
                defaultextension=".mp4", filetypes=[("MP4","*.mp4")],
                initialfile="video_efectos.mp4")
            if dest: clip.write_videofile(dest, logger=None); self._st(self.ef_st_lbl,"✅ Guardado")
            else:    self._st(self.ef_st_lbl,"⏸️ Cancelado")
            clip.close()
        except Exception as e: self._st(self.ef_st_lbl, f"❌ {e}")
        self.ef_prog.stop()

    # ── Música ────────────────────────────────────────────────────────────────
    def _build_musica(self, f):
        pid = 'musica'
        self._video_row(f, pid)
        ar = tk.Frame(f, bg=CARD, padx=6)
        ar.pack(fill='x')
        self.m_audio_lbl = tk.Label(ar, text="Ningún audio seleccionado",
                                    fg=TEXT_S, bg=CARD, anchor='w', font=FN)
        self.m_audio_lbl.pack(side='left', fill='x', expand=True)
        mkbtn(ar,"📂 Abrir audio", self._sel_audio, ACCENT).pack(side='right')
        tk.Label(f,text="Volumen:",bg=CARD,font=FN,anchor='w').pack(anchor='w',padx=6,pady=(8,0))
        self.m_vol = tk.Scale(f, from_=0, to=100, orient='horizontal', length=350,
                              bg=CARD, highlightthickness=0, troughcolor=BORDER)
        self.m_vol.pack(padx=6, pady=4); self.m_vol.set(50)
        self.m_orig = tk.BooleanVar(value=True)
        tk.Checkbutton(f, text="Mantener audio original del video",
                       variable=self.m_orig, bg=CARD, font=FN,
                       activebackground=CARD).pack(anchor='w', padx=6)
        self.mu_prog, self.mu_st_lbl = self._prog_row(f)
        mkbtn(f,"🎵 AÑADIR MÚSICA",
              lambda: self._proc_musica(pid), ACCENT,
              font=('Segoe UI',11,'bold')).pack(pady=8, padx=6, fill='x')

    def _sel_audio(self):
        f = filedialog.askopenfilename(
            title="Seleccionar audio",
            filetypes=[("Audio","*.mp3 *.wav *.m4a *.ogg"),("Todos","*.*")])
        if f: self.audio_path=f; self.m_audio_lbl.config(text=os.path.basename(f), fg=TEXT)

    def _proc_musica(self, pid):
        vp = self.video_paths.get(pid)
        if not vp: messagebox.showerror("Error","Selecciona un video"); return
        if not self.audio_path: messagebox.showerror("Error","Selecciona un archivo de música"); return
        threading.Thread(target=self._proc_musica_t, args=(vp,), daemon=True).start()

    def _proc_musica_t(self, vp):
        self.mu_prog.start(); self._st(self.mu_st_lbl,"⏳ Procesando…")
        try:
            video = VideoFileClip(vp)
            audio = AudioFileClip(self.audio_path).with_volume_scaled(self.m_vol.get()/100)
            if audio.duration > video.duration:
                audio = audio.subclipped(0, video.duration)
            if self.m_orig.get() and video.audio is not None:
                from moviepy.audio.CompositeAudioClip import CompositeAudioClip
                audio_final = CompositeAudioClip([video.audio.with_volume_scaled(0.3), audio])
            else:
                audio_final = audio
            vc   = video.with_audio(audio_final)
            dest = filedialog.asksaveasfilename(
                defaultextension=".mp4", filetypes=[("MP4","*.mp4")],
                initialfile="video_musica.mp4")
            if dest: vc.write_videofile(dest, logger=None); self._st(self.mu_st_lbl,"✅ Guardado")
            else:    self._st(self.mu_st_lbl,"⏸️ Cancelado")
            video.close(); audio.close()
        except Exception as e: self._st(self.mu_st_lbl, f"❌ {e}")
        self.mu_prog.stop()

    # ── Recortar ──────────────────────────────────────────────────────────────
    def _build_recortar(self, f):
        pid = 'recortar'
        self._video_row(f, pid)
        cfg = tk.Frame(f, bg=CARD, padx=10)
        cfg.pack(fill='x')
        tk.Label(cfg,text="Inicio (s):",bg=CARD,font=FN).grid(row=0,column=0,sticky='w',pady=4)
        self.r_ini = tk.Entry(cfg, width=8, font=FN)
        self.r_ini.grid(row=0,column=1,sticky='w',padx=4); self.r_ini.insert(0,"0")
        tk.Label(cfg,text="Fin (s):",bg=CARD,font=FN).grid(row=1,column=0,sticky='w',pady=4)
        self.r_fin = tk.Entry(cfg, width=8, font=FN)
        self.r_fin.grid(row=1,column=1,sticky='w',padx=4); self.r_fin.insert(0,"10")
        tk.Label(cfg,text="(vacío = hasta el final)",bg=CARD,font=FNS,
                 fg=TEXT_S).grid(row=2,column=1,sticky='w',padx=4)
        self.rc_prog, self.rc_st_lbl = self._prog_row(f)
        mkbtn(f,"✂️ RECORTAR VIDEO",
              lambda: self._proc_recortar(pid), RED,
              font=('Segoe UI',11,'bold')).pack(pady=8, padx=6, fill='x')

    def _proc_recortar(self, pid):
        vp = self.video_paths.get(pid)
        if not vp: messagebox.showerror("Error","Selecciona un video"); return
        threading.Thread(target=self._proc_recortar_t, args=(vp,), daemon=True).start()

    def _proc_recortar_t(self, vp):
        self.rc_prog.start(); self._st(self.rc_st_lbl,"⏳ Procesando…")
        try:
            clip = VideoFileClip(vp)
            ini  = float(self.r_ini.get())
            fin  = float(self.r_fin.get()) if self.r_fin.get().strip() else clip.duration
            cr   = clip.subclipped(ini, fin)
            dest = filedialog.asksaveasfilename(
                defaultextension=".mp4", filetypes=[("MP4","*.mp4")],
                initialfile="video_recortado.mp4")
            if dest: cr.write_videofile(dest, logger=None); self._st(self.rc_st_lbl,"✅ Guardado")
            else:    self._st(self.rc_st_lbl,"⏸️ Cancelado")
            clip.close(); cr.close()
        except Exception as e: self._st(self.rc_st_lbl, f"❌ {e}")
        self.rc_prog.stop()

    # ── Carátulas ─────────────────────────────────────────────────────────────
    def _build_caratulas(self, f):
        pid = 'caratulas'
        self._video_row(f, pid)
        for attr, lbl_attr, dur_attr, titulo, sel_fn in [
            ('caratula_path','ca_lbl','ca_dur',"Carátula (inicio)", self._sel_caratula),
            ('contra_path',  'co_lbl','co_dur',"Contraportada (final)", self._sel_contra),
        ]:
            lf = tk.LabelFrame(f, text=titulo, bg=CARD, padx=8, pady=6, font=FNB)
            lf.pack(fill='x', padx=6, pady=4)
            r  = tk.Frame(lf, bg=CARD); r.pack(fill='x')
            lbl = tk.Label(r, text="Sin imagen", fg=TEXT_S, bg=CARD, anchor='w', font=FN)
            lbl.pack(side='left', fill='x', expand=True)
            mkbtn(r,"Seleccionar", sel_fn, GREEN, font=FNS).pack(side='right')
            dr = tk.Frame(lf, bg=CARD); dr.pack(fill='x', pady=(4,0))
            tk.Label(dr,text="Duración (s):",bg=CARD,font=FN).pack(side='left')
            entry = tk.Entry(dr, width=6, font=FN)
            entry.pack(side='left', padx=4); entry.insert(0,"3")
            setattr(self, lbl_attr, lbl); setattr(self, dur_attr, entry)
        self.cr_prog, self.cr_st_lbl = self._prog_row(f)
        mkbtn(f,"🎬 PROCESAR CARÁTULAS",
              lambda: self._proc_caratulas(pid), RED,
              font=('Segoe UI',11,'bold')).pack(pady=8, padx=6, fill='x')

    def _sel_caratula(self):
        f = filedialog.askopenfilename(
            title="Carátula",
            filetypes=[("Imágenes","*.png *.jpg *.jpeg *.bmp"),("Todos","*.*")])
        if f: self.caratula_path=f; self.ca_lbl.config(text=os.path.basename(f), fg=TEXT)

    def _sel_contra(self):
        f = filedialog.askopenfilename(
            title="Contraportada",
            filetypes=[("Imágenes","*.png *.jpg *.jpeg *.bmp"),("Todos","*.*")])
        if f: self.contra_path=f; self.co_lbl.config(text=os.path.basename(f), fg=TEXT)

    def _proc_caratulas(self, pid):
        vp = self.video_paths.get(pid)
        if not vp: messagebox.showerror("Error","Selecciona un video"); return
        if not self.caratula_path and not self.contra_path:
            messagebox.showerror("Error","Selecciona al menos una imagen"); return
        threading.Thread(target=self._proc_caratulas_t, args=(vp,), daemon=True).start()

    def _proc_caratulas_t(self, vp):
        self.cr_prog.start(); self._st(self.cr_st_lbl,"⏳ Procesando…")
        try:
            clip = VideoFileClip(vp); clips = []
            if self.caratula_path:
                clips.append(ImageClip(self.caratula_path)
                             .with_duration(float(self.ca_dur.get()))
                             .resized(new_size=clip.size))
            clips.append(clip)
            if self.contra_path:
                clips.append(ImageClip(self.contra_path)
                             .with_duration(float(self.co_dur.get()))
                             .resized(new_size=clip.size))
            vf   = concatenate_videoclips(clips)
            dest = filedialog.asksaveasfilename(
                defaultextension=".mp4", filetypes=[("MP4","*.mp4")],
                initialfile="video_caratulas.mp4")
            if dest: vf.write_videofile(dest, logger=None); self._st(self.cr_st_lbl,"✅ Guardado")
            else:    self._st(self.cr_st_lbl,"⏸️ Cancelado")
            for c in clips: c.close()
        except Exception as e: self._st(self.cr_st_lbl, f"❌ {e}")
        self.cr_prog.stop()

    # ── Marca de agua ─────────────────────────────────────────────────────────
    def _build_watermark(self, f):
        pid = 'watermark'
        self._video_row(f, pid)
        cfg = tk.Frame(f, bg=CARD, padx=10)
        cfg.pack(fill='x')

        # Tipo
        tk.Label(cfg, text="Tipo:", bg=CARD, font=FNB).grid(
            row=0, column=0, sticky='w', pady=4)
        self.wm_tipo = tk.StringVar(value='texto')
        tk.Radiobutton(cfg, text="Texto", variable=self.wm_tipo, value='texto',
                       bg=CARD, font=FN, activebackground=CARD,
                       command=self._wm_toggle).grid(row=0, column=1, sticky='w')
        tk.Radiobutton(cfg, text="Imagen", variable=self.wm_tipo, value='imagen',
                       bg=CARD, font=FN, activebackground=CARD,
                       command=self._wm_toggle).grid(row=0, column=2, sticky='w')

        # Texto
        tk.Label(cfg, text="Texto:", bg=CARD, font=FN).grid(
            row=1, column=0, sticky='w', pady=4)
        self.wm_texto = tk.Entry(cfg, width=28, font=FN)
        self.wm_texto.grid(row=1, column=1, columnspan=3, sticky='w', padx=4)
        self.wm_texto.insert(0, "© Mi canal")

        # Tamaño texto
        tk.Label(cfg, text="Tamaño:", bg=CARD, font=FN).grid(
            row=2, column=0, sticky='w', pady=4)
        self.wm_size = tk.Scale(cfg, from_=10, to=120, orient='horizontal',
                                length=180, bg=CARD, highlightthickness=0,
                                troughcolor=BORDER)
        self.wm_size.set(36)
        self.wm_size.grid(row=2, column=1, columnspan=2, sticky='w', padx=4)

        # Imagen
        tk.Label(cfg, text="Imagen:", bg=CARD, font=FN).grid(
            row=3, column=0, sticky='w', pady=4)
        img_row = tk.Frame(cfg, bg=CARD)
        img_row.grid(row=3, column=1, columnspan=3, sticky='w', pady=4)
        self.wm_img_lbl = tk.Label(img_row, text="Sin imagen",
                                   fg=TEXT_S, bg=CARD, font=FNS)
        self.wm_img_lbl.pack(side='left')
        mkbtn(img_row, "📂", self._wm_sel_img, ACCENT, w=3,
              font=FNS).pack(side='left', padx=4)
        self.wm_img_path = None

        # Opacidad
        tk.Label(cfg, text="Opacidad:", bg=CARD, font=FN).grid(
            row=4, column=0, sticky='w', pady=4)
        self.wm_opac = tk.Scale(cfg, from_=5, to=100, orient='horizontal',
                                length=180, bg=CARD, highlightthickness=0,
                                troughcolor=BORDER)
        self.wm_opac.set(60)
        self.wm_opac.grid(row=4, column=1, columnspan=2, sticky='w', padx=4)
        tk.Label(cfg, text="%", bg=CARD, font=FN).grid(row=4, column=3, sticky='w')

        # Posición
        tk.Label(cfg, text="Posición:", bg=CARD, font=FN).grid(
            row=5, column=0, sticky='w', pady=4)
        self.wm_pos = ttk.Combobox(
            cfg, values=['Abajo derecha', 'Abajo izquierda',
                         'Arriba derecha', 'Arriba izquierda', 'Centro'],
            state='readonly', width=18, font=FN)
        self.wm_pos.grid(row=5, column=1, columnspan=2, sticky='w', padx=4)
        self.wm_pos.current(0)

        # Margen
        tk.Label(cfg, text="Margen (px):", bg=CARD, font=FN).grid(
            row=6, column=0, sticky='w', pady=4)
        self.wm_margen = tk.Entry(cfg, width=6, font=FN)
        self.wm_margen.grid(row=6, column=1, sticky='w', padx=4)
        self.wm_margen.insert(0, "20")

        self._wm_toggle()  # estado inicial
        self.wm_prog, self.wm_st = self._prog_row(f)
        mkbtn(f, "💧 APLICAR MARCA DE AGUA",
              lambda: self._proc_watermark(pid), PURPLE,
              font=('Segoe UI', 11, 'bold')).pack(pady=8, padx=6, fill='x')

    def _wm_toggle(self):
        es_texto = (self.wm_tipo.get() == 'texto')
        st_t = 'normal' if es_texto  else 'disabled'
        st_i = 'normal' if not es_texto else 'disabled'
        self.wm_texto.config(state=st_t)
        self.wm_size.config(state=st_t)

    def _wm_sel_img(self):
        f = filedialog.askopenfilename(
            title="Imagen para marca de agua",
            filetypes=[("Imágenes", "*.png *.jpg *.jpeg *.bmp"), ("Todos", "*.*")])
        if f:
            self.wm_img_path = f
            self.wm_img_lbl.config(text=os.path.basename(f), fg=TEXT)

    def _proc_watermark(self, pid):
        vp = self.video_paths.get(pid)
        if not vp: messagebox.showerror("Error", "Selecciona un video"); return
        if self.wm_tipo.get() == 'imagen' and not self.wm_img_path:
            messagebox.showerror("Error", "Selecciona una imagen para la marca de agua")
            return
        threading.Thread(target=self._proc_watermark_t,
                         args=(vp,), daemon=True).start()

    def _proc_watermark_t(self, vp):
        self.wm_prog.start(); self._st(self.wm_st, "⏳ Procesando…")
        try:
            clip   = VideoFileClip(vp)
            opac   = self.wm_opac.get() / 100
            margen = int(self.wm_margen.get())
            pos_map = {
                'Abajo derecha':   lambda w, h, cw, ch: (cw-w-margen, ch-h-margen),
                'Abajo izquierda': lambda w, h, cw, ch: (margen, ch-h-margen),
                'Arriba derecha':  lambda w, h, cw, ch: (cw-w-margen, margen),
                'Arriba izquierda':lambda w, h, cw, ch: (margen, margen),
                'Centro':          lambda w, h, cw, ch: ('center', 'center'),
            }
            pos_fn = pos_map.get(self.wm_pos.get(), pos_map['Abajo derecha'])

            if self.wm_tipo.get() == 'texto':
                marca = TextClip(
                    font='Arial', text=self.wm_texto.get(),
                    font_size=self.wm_size.get(), color='white',
                    stroke_color='black', stroke_width=1
                ).with_duration(clip.duration).with_opacity(opac)
                mw, mh = marca.size
                pos = pos_fn(mw, mh, clip.w, clip.h)
                marca = marca.with_position(pos)
            else:
                from PIL import Image as PILImage
                img = PILImage.open(self.wm_img_path).convert('RGBA')
                # Escalar la marca a máx 25% del ancho del video
                max_w = clip.w // 4
                if img.width > max_w:
                    r = max_w / img.width
                    img = img.resize((max_w, int(img.height * r)),
                                     PILImage.Resampling.LANCZOS)
                # Aplicar opacidad al canal alpha
                r2, g2, b2, a = img.split()
                a = a.point(lambda x: int(x * opac))
                img.putalpha(a)
                tmp = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
                img.save(tmp.name); tmp.close()
                marca = (ImageClip(tmp.name)
                         .with_duration(clip.duration))
                mw, mh = marca.size
                pos = pos_fn(mw, mh, clip.w, clip.h)
                marca = marca.with_position(pos)
                os.unlink(tmp.name)

            vf   = CompositeVideoClip([clip, marca])
            dest = filedialog.asksaveasfilename(
                defaultextension=".mp4", filetypes=[("MP4", "*.mp4")],
                initialfile="video_marca.mp4")
            if dest:
                vf.write_videofile(dest, logger=None)
                self._st(self.wm_st, "✅ Guardado")
            else:
                self._st(self.wm_st, "⏸️ Cancelado")
            clip.close(); marca.close(); vf.close()
        except Exception as e: self._st(self.wm_st, f"❌ {e}")
        self.wm_prog.stop()

    # ── Velocidad ─────────────────────────────────────────────────────────────
    def _build_velocidad(self, f):
        pid = 'velocidad'
        self._video_row(f, pid)
        cfg = tk.Frame(f, bg=CARD, padx=10)
        cfg.pack(fill='x')

        tk.Label(cfg, text="Factor de velocidad:", bg=CARD, font=FNB).grid(
            row=0, column=0, sticky='w', pady=6)

        presets = tk.Frame(cfg, bg=CARD)
        presets.grid(row=1, column=0, columnspan=3, sticky='w', pady=4)
        tk.Label(presets, text="Presets rápidos:", bg=CARD, font=FNS,
                 fg=TEXT_S).pack(side='left', padx=(0, 8))
        self.vel_var = tk.DoubleVar(value=1.0)
        for label, val in [("¼×", 0.25), ("½×", 0.5), ("1×", 1.0),
                           ("1.5×", 1.5), ("2×", 2.0), ("4×", 4.0)]:
            mkbtn(presets, label,
                  lambda v=val: self.vel_var.set(v),
                  ACCENT if val != 1.0 else BORDER,
                  fg='white' if val != 1.0 else TEXT,
                  font=FNS).pack(side='left', padx=2)

        tk.Label(cfg, text="O introduce un valor exacto (0.1 – 10):",
                 bg=CARD, font=FNS, fg=TEXT_S).grid(
            row=2, column=0, sticky='w', pady=(8, 2))
        vel_row = tk.Frame(cfg, bg=CARD)
        vel_row.grid(row=3, column=0, sticky='w')
        self.vel_entry = tk.Entry(vel_row, textvariable=self.vel_var,
                                  width=8, font=FN)
        self.vel_entry.pack(side='left')
        tk.Label(vel_row, text="× velocidad", bg=CARD,
                 font=FN, fg=TEXT_S).pack(side='left', padx=6)

        tk.Label(cfg,
                 text="< 1 = cámara lenta  ·  > 1 = cámara rápida\n"
                      "El audio se ajusta automáticamente a la nueva duración.",
                 bg=CARD, font=FNS, fg=TEXT_S, justify='left').grid(
            row=4, column=0, columnspan=3, sticky='w', pady=(8, 0))

        self.vel_prog, self.vel_st = self._prog_row(f)
        mkbtn(f, "⚡ CAMBIAR VELOCIDAD",
              lambda: self._proc_velocidad(pid), ORANGE,
              font=('Segoe UI', 11, 'bold')).pack(pady=8, padx=6, fill='x')

    def _proc_velocidad(self, pid):
        vp = self.video_paths.get(pid)
        if not vp: messagebox.showerror("Error", "Selecciona un video"); return
        try:
            factor = float(self.vel_var.get())
            if not 0.1 <= factor <= 10: raise ValueError
        except:
            messagebox.showerror("Error", "El factor debe estar entre 0.1 y 10")
            return
        threading.Thread(target=self._proc_velocidad_t,
                         args=(vp, factor), daemon=True).start()

    def _proc_velocidad_t(self, vp, factor):
        self.vel_prog.start(); self._st(self.vel_st, "⏳ Procesando…")
        try:
            clip = VideoFileClip(vp)
            vf   = clip.with_multiply_speed(factor)
            dest = filedialog.asksaveasfilename(
                defaultextension=".mp4", filetypes=[("MP4", "*.mp4")],
                initialfile=f"video_{factor}x.mp4")
            if dest:
                vf.write_videofile(dest, logger=None)
                nueva_dur = clip.duration / factor
                self._st(self.vel_st, "✅ Guardado")
                messagebox.showinfo("✅ Listo",
                    f"Video guardado.\n\n"
                    f"Duración original: {fmt(clip.duration)}\n"
                    f"Duración nueva:    {fmt(nueva_dur)}")
            else:
                self._st(self.vel_st, "⏸️ Cancelado")
            clip.close(); vf.close()
        except Exception as e: self._st(self.vel_st, f"❌ {e}")
        self.vel_prog.stop()

    # ── Encuadre / Crop ───────────────────────────────────────────────────────
    def _build_crop(self, f):
        pid = 'crop'
        self._video_row(f, pid)
        cfg = tk.Frame(f, bg=CARD, padx=10)
        cfg.pack(fill='x')

        tk.Label(cfg, text="Relación de aspecto:", bg=CARD, font=FNB).grid(
            row=0, column=0, sticky='w', pady=6)

        presets_frame = tk.Frame(cfg, bg=CARD)
        presets_frame.grid(row=1, column=0, columnspan=4, sticky='w', pady=4)
        tk.Label(presets_frame, text="Presets:", bg=CARD,
                 font=FNS, fg=TEXT_S).pack(side='left', padx=(0, 8))

        self.crop_mode = tk.StringVar(value='16:9')
        for label in ['16:9', '9:16', '1:1', '4:3', '21:9', 'Personalizado']:
            tk.Radiobutton(
                presets_frame, text=label, variable=self.crop_mode,
                value=label, bg=CARD, font=FNS, activebackground=CARD,
                command=self._crop_toggle
            ).pack(side='left', padx=3)

        # Personalizado
        custom = tk.Frame(cfg, bg=CARD)
        custom.grid(row=2, column=0, columnspan=4, sticky='w', pady=4)
        tk.Label(custom, text="Ancho:", bg=CARD, font=FN).pack(side='left')
        self.crop_w = tk.Entry(custom, width=7, font=FN)
        self.crop_w.pack(side='left', padx=4)
        self.crop_w.insert(0, "1280")
        tk.Label(custom, text="Alto:", bg=CARD, font=FN).pack(side='left', padx=(8, 0))
        self.crop_h = tk.Entry(custom, width=7, font=FN)
        self.crop_h.pack(side='left', padx=4)
        self.crop_h.insert(0, "720")
        self.crop_custom_frame = custom

        # Posición del recorte
        tk.Label(cfg, text="Centrar en:", bg=CARD, font=FN).grid(
            row=3, column=0, sticky='w', pady=(8, 2))
        self.crop_anchor = ttk.Combobox(
            cfg, values=['Centro', 'Arriba', 'Abajo', 'Izquierda', 'Derecha'],
            state='readonly', width=14, font=FN)
        self.crop_anchor.grid(row=3, column=1, sticky='w', padx=4)
        self.crop_anchor.current(0)

        tk.Label(cfg,
                 text="Útil para adaptar video horizontal a vertical (9:16)\n"
                      "o eliminar franjas negras.",
                 bg=CARD, font=FNS, fg=TEXT_S, justify='left').grid(
            row=4, column=0, columnspan=4, sticky='w', pady=(8, 0))

        self._crop_toggle()
        self.crop_prog, self.crop_st = self._prog_row(f)
        mkbtn(f, "⬛ APLICAR ENCUADRE",
              lambda: self._proc_crop(pid), ACCENT,
              font=('Segoe UI', 11, 'bold')).pack(pady=8, padx=6, fill='x')

    def _crop_toggle(self):
        es_custom = (self.crop_mode.get() == 'Personalizado')
        for w in self.crop_custom_frame.winfo_children():
            if isinstance(w, tk.Entry):
                w.config(state='normal' if es_custom else 'disabled')

    def _proc_crop(self, pid):
        vp = self.video_paths.get(pid)
        if not vp: messagebox.showerror("Error", "Selecciona un video"); return
        threading.Thread(target=self._proc_crop_t, args=(vp,), daemon=True).start()

    def _proc_crop_t(self, vp):
        self.crop_prog.start(); self._st(self.crop_st, "⏳ Procesando…")
        try:
            clip = VideoFileClip(vp)
            vw, vh = clip.size
            mode   = self.crop_mode.get()

            ratio_map = {
                '16:9':  (16, 9), '9:16': (9, 16), '1:1': (1, 1),
                '4:3':   (4, 3),  '21:9': (21, 9),
            }
            if mode == 'Personalizado':
                tw = int(self.crop_w.get())
                th = int(self.crop_h.get())
            else:
                rx, ry = ratio_map[mode]
                # Calcular el mayor recuadro con esa proporción que cabe en el video
                if vw / vh > rx / ry:
                    th = vh; tw = int(vh * rx / ry)
                else:
                    tw = vw; th = int(vw * ry / rx)

            anchor = self.crop_anchor.get()
            anchor_map = {
                'Centro':    ((vw - tw) // 2, (vh - th) // 2),
                'Arriba':    ((vw - tw) // 2, 0),
                'Abajo':     ((vw - tw) // 2, vh - th),
                'Izquierda': (0, (vh - th) // 2),
                'Derecha':   (vw - tw, (vh - th) // 2),
            }
            x1, y1 = anchor_map.get(anchor, anchor_map['Centro'])
            x1 = max(0, min(x1, vw - tw))
            y1 = max(0, min(y1, vh - th))

            vf   = clip.cropped(x1=x1, y1=y1, x2=x1+tw, y2=y1+th)
            dest = filedialog.asksaveasfilename(
                defaultextension=".mp4", filetypes=[("MP4", "*.mp4")],
                initialfile=f"video_crop_{mode.replace(':','x')}.mp4")
            if dest:
                vf.write_videofile(dest, logger=None)
                self._st(self.crop_st, "✅ Guardado")
                messagebox.showinfo("✅ Listo",
                    f"Video guardado.\n\n"
                    f"Original: {vw}×{vh}\n"
                    f"Nuevo:    {tw}×{th}  ({mode})")
            else:
                self._st(self.crop_st, "⏸️ Cancelado")
            clip.close(); vf.close()
        except Exception as e: self._st(self.crop_st, f"❌ {e}")
        self.crop_prog.stop()

    # ── Subtítulos .SRT ───────────────────────────────────────────────────────
    def _build_srt(self, f):
        pid = 'srt'
        self._video_row(f, pid)
        cfg = tk.Frame(f, bg=CARD, padx=10)
        cfg.pack(fill='x')

        # Selector SRT
        tk.Label(cfg, text="Archivo .SRT:", bg=CARD, font=FNB).grid(
            row=0, column=0, sticky='w', pady=6)
        srt_row = tk.Frame(cfg, bg=CARD)
        srt_row.grid(row=0, column=1, columnspan=3, sticky='w', pady=6)
        self.srt_lbl = tk.Label(srt_row, text="Sin archivo SRT",
                                fg=TEXT_S, bg=CARD, font=FNS)
        self.srt_lbl.pack(side='left')
        mkbtn(srt_row, "📂", self._srt_sel, ACCENT, w=3,
              font=FNS).pack(side='left', padx=6)
        self.srt_path = None

        # Fuente
        tk.Label(cfg, text="Fuente:", bg=CARD, font=FN).grid(
            row=1, column=0, sticky='w', pady=4)
        self.srt_font = ttk.Combobox(
            cfg, values=sorted(self.mapa_fuentes.keys()) or ['Arial'],
            width=24, font=FN)
        self.srt_font.grid(row=1, column=1, columnspan=2, sticky='w', padx=4)
        self.srt_font.set('Arial')

        # Tamaño
        tk.Label(cfg, text="Tamaño:", bg=CARD, font=FN).grid(
            row=2, column=0, sticky='w', pady=4)
        self.srt_size = tk.Scale(cfg, from_=14, to=80, orient='horizontal',
                                 length=180, bg=CARD, highlightthickness=0,
                                 troughcolor=BORDER)
        self.srt_size.set(32)
        self.srt_size.grid(row=2, column=1, columnspan=2, sticky='w', padx=4)

        # Color
        tk.Label(cfg, text="Color:", bg=CARD, font=FN).grid(
            row=3, column=0, sticky='w', pady=4)
        srt_clr = tk.Frame(cfg, bg=CARD)
        srt_clr.grid(row=3, column=1, sticky='w', pady=4)
        self.srt_color = 'white'
        mkbtn(srt_clr, "Elegir", self._srt_color, ACCENT,
              font=FNS).pack(side='left')
        self.srt_clr_lbl = tk.Label(srt_clr, text="   ", bg='white',
                                    width=3, relief='sunken')
        self.srt_clr_lbl.pack(side='left', padx=6)

        # Posición vertical
        tk.Label(cfg, text="Posición V:", bg=CARD, font=FN).grid(
            row=4, column=0, sticky='w', pady=4)
        self.srt_vpos = ttk.Combobox(
            cfg, values=['Abajo (estándar)', 'Arriba', 'Centro'],
            state='readonly', width=18, font=FN)
        self.srt_vpos.grid(row=4, column=1, sticky='w', padx=4)
        self.srt_vpos.current(0)

        # Borde
        self.srt_borde = tk.BooleanVar(value=True)
        tk.Checkbutton(cfg, text="Borde negro (mayor legibilidad)",
                       variable=self.srt_borde, bg=CARD, font=FN,
                       activebackground=CARD).grid(
            row=5, column=0, columnspan=3, sticky='w', pady=4)

        tk.Label(cfg,
                 text="El archivo .SRT debe estar en el mismo idioma y\n"
                      "con los tiempos correspondientes al video.",
                 bg=CARD, font=FNS, fg=TEXT_S, justify='left').grid(
            row=6, column=0, columnspan=3, sticky='w', pady=(6, 0))

        self.srt_prog, self.srt_st = self._prog_row(f)
        mkbtn(f, "💬 INCRUSTRAR SUBTÍTULOS",
              lambda: self._proc_srt(pid), ACCENT,
              font=('Segoe UI', 11, 'bold')).pack(pady=8, padx=6, fill='x')

    def _srt_sel(self):
        f = filedialog.askopenfilename(
            title="Seleccionar archivo SRT",
            filetypes=[("SubRip", "*.srt"), ("Todos", "*.*")])
        if f:
            self.srt_path = f
            self.srt_lbl.config(text=os.path.basename(f), fg=TEXT)

    def _srt_color(self):
        c = colorchooser.askcolor(title="Color de subtítulos",
                                  initialcolor=self.srt_color)[1]
        if c:
            self.srt_color = c
            self.srt_clr_lbl.config(bg=c)

    def _parse_srt(self, path):
        """Parsea un .srt y devuelve lista de (inicio, fin, texto)"""
        import re
        with open(path, 'r', encoding='utf-8', errors='replace') as fh:
            content = fh.read()

        bloques = re.split(r'\n\n+', content.strip())
        subs = []
        tc   = re.compile(
            r'(\d+):(\d+):(\d+)[,.](\d+)\s*-->\s*(\d+):(\d+):(\d+)[,.](\d+)')
        for bloque in bloques:
            lineas = bloque.strip().splitlines()
            if len(lineas) < 2: continue
            m = None
            for ln in lineas:
                m = tc.match(ln.strip())
                if m: break
            if not m: continue
            def ts(*g): return (int(g[0])*3600 + int(g[1])*60 +
                                int(g[2]) + int(g[3])/1000)
            t_in  = ts(*m.groups()[:4])
            t_out = ts(*m.groups()[4:])
            texto = '\n'.join(l for l in lineas if not l.strip().isdigit()
                              and not tc.match(l.strip()))
            texto = re.sub(r'<[^>]+>', '', texto).strip()
            if texto: subs.append((t_in, t_out, texto))
        return subs

    def _proc_srt(self, pid):
        vp = self.video_paths.get(pid)
        if not vp: messagebox.showerror("Error", "Selecciona un video"); return
        if not self.srt_path:
            messagebox.showerror("Error", "Selecciona un archivo .SRT"); return
        threading.Thread(target=self._proc_srt_t, args=(vp,), daemon=True).start()

    def _proc_srt_t(self, vp):
        self.srt_prog.start(); self._st(self.srt_st, "⏳ Parseando SRT…")
        try:
            subs = self._parse_srt(self.srt_path)
            if not subs:
                raise ValueError("No se encontraron subtítulos válidos en el archivo")

            clip    = VideoFileClip(vp)
            fn      = self.mapa_fuentes.get(self.srt_font.get(), 'Arial')
            sz      = self.srt_size.get()
            color   = self.srt_color
            borde   = self.srt_borde.get()
            vpos    = self.srt_vpos.get()
            margin  = 30

            pos_map = {
                'Abajo (estándar)': lambda th: ('center', clip.h - th - margin),
                'Arriba':           lambda th: ('center', margin),
                'Centro':           lambda th: ('center', 'center'),
            }
            pos_fn = pos_map.get(vpos, pos_map['Abajo (estándar)'])

            self._st(self.srt_st, f"⏳ Generando {len(subs)} subtítulos…")
            tc_clips = []
            for t_in, t_out, texto in subs:
                if t_out > clip.duration: t_out = clip.duration
                if t_in  >= t_out: continue
                dur = t_out - t_in
                tc  = TextClip(
                    font=fn, text=texto, font_size=sz, color=color,
                    stroke_color='black' if borde else None,
                    stroke_width=2 if borde else 0,
                    method='caption', size=(clip.w - margin*2, None)
                ).with_duration(dur).with_start(t_in)
                pos = pos_fn(tc.h)
                tc  = tc.with_position(pos)
                tc_clips.append(tc)

            self._st(self.srt_st, "⏳ Componiendo video…")
            vf   = CompositeVideoClip([clip] + tc_clips)
            dest = filedialog.asksaveasfilename(
                defaultextension=".mp4", filetypes=[("MP4", "*.mp4")],
                initialfile="video_subtitulado.mp4")
            if dest:
                vf.write_videofile(dest, logger=None)
                self._st(self.srt_st, "✅ Guardado")
                messagebox.showinfo("✅ Listo",
                    f"Video guardado.\n{len(subs)} subtítulos integrados.")
            else:
                self._st(self.srt_st, "⏸️ Cancelado")
            clip.close()
            for tc in tc_clips: tc.close()
            vf.close()
        except Exception as e: self._st(self.srt_st, f"❌ {e}")
        self.srt_prog.stop()


# ══════════════════════════ TAB: UNIR ══════════════════════════════════
class TabUnir:
    def __init__(self, frame, root):
        self.frame = frame; self.root = root; self.videos = []
        self._build()

    def _build(self):
        body = tk.Frame(self.frame, bg=BG)
        body.pack(fill='both', expand=True, padx=10, pady=8)
        body.columnconfigure(0, weight=3)
        body.columnconfigure(1, weight=2, minsize=270)
        body.rowconfigure(0, weight=1)

        # ── Izquierda: lista ──────────────────────────────────────────────
        left = tk.Frame(body, bg=BG)
        left.grid(row=0, column=0, sticky='nsew', padx=(0,6))
        left.columnconfigure(0, weight=1)
        left.rowconfigure(1, weight=1)

        hc, hi = crd(left)
        hc.grid(row=0, column=0, sticky='ew', pady=(0,4))
        tk.Label(hi, text="Videos a unir", font=FNB, fg=TEXT, bg=CARD).pack(anchor='w')
        tk.Label(hi, text="El orden de la lista determina el orden del video final",
                 font=FNS, fg=TEXT_S, bg=CARD).pack(anchor='w')

        lc, li = crd(left)
        lc.grid(row=1, column=0, sticky='nsew')
        brow = tk.Frame(li, bg=CARD)
        brow.pack(fill='x', pady=(0,4))
        mkbtn(brow,"➕ Agregar", self._agregar, GREEN,  font=FNS).pack(side='left',padx=(0,3))
        mkbtn(brow,"⬆ Subir",   self._subir,   ACCENT, font=FNS).pack(side='left',padx=3)
        mkbtn(brow,"⬇ Bajar",   self._bajar,   ACCENT, font=FNS).pack(side='left',padx=3)
        mkbtn(brow,"❌ Quitar",  self._quitar,  RED,    font=FNS).pack(side='left',padx=3)
        mkbtn(brow,"🗑️ Limpiar", self._limpiar, ORANGE, font=FNS).pack(side='left',padx=3)
        lf = tk.Frame(li, bg=CARD)
        lf.pack(fill='both', expand=True)
        self.lst = tk.Listbox(lf, bg=BG, fg=TEXT, font=FMO, relief='flat',
                              selectbackground=SEL_BG, selectforeground=TEXT,
                              highlightthickness=1, highlightcolor=BORDER,
                              activestyle='none')
        self.lst.pack(side='left', fill='both', expand=True)
        scr = tk.Scrollbar(lf, command=self.lst.yview)
        scr.pack(side='right', fill='y')
        self.lst.config(yscrollcommand=scr.set)
        ir = tk.Frame(li, bg=CARD)
        ir.pack(fill='x', pady=(4,0))
        self.lbl_count = tk.Label(ir, text="0 videos", fg=TEXT_S, bg=CARD, font=FNS)
        self.lbl_count.pack(side='left')
        self.lbl_dur   = tk.Label(ir, text="", fg=TEXT_S, bg=CARD, font=FNS)
        self.lbl_dur.pack(side='right')

        # ── Derecha: opciones + procesar ──────────────────────────────────
        right = tk.Frame(body, bg=BG)
        right.grid(row=0, column=1, sticky='nsew')
        right.columnconfigure(0, weight=1)

        oc, oi = crd(right)
        oc.grid(row=0, column=0, sticky='ew')
        tk.Label(oi, text="Método de unión", font=FNB,
                 fg=TEXT, bg=CARD).pack(anchor='w', pady=(0,4))
        self.metodo = tk.StringVar(value='compose')
        tk.Radiobutton(oi, text="Compose  (recomendado — mejor calidad  - un solo formato para todos)",
                       variable=self.metodo, value='compose',
                       bg=CARD, font=FN, activebackground=CARD).pack(anchor='w')
        tk.Radiobutton(oi, text="Chain  (más rápido — cada vídeo mantiene su formato original)",
                       variable=self.metodo, value='chain',
                       bg=CARD, font=FN, activebackground=CARD).pack(anchor='w')

        self.btn_proc = tk.Button(
            right, text="🔗  UNIR VÍDEOS", command=self._iniciar,
            bg=ACCENT, fg='white', font=('Segoe UI',11,'bold'),
            relief='flat', pady=10, cursor='hand2', state='disabled',
            activebackground=ACCENT, activeforeground='white')
        self.btn_proc.grid(row=1, column=0, sticky='ew', pady=(8,0))

        self.progress = ttk.Progressbar(right, mode='indeterminate')
        self.progress.grid(row=2, column=0, sticky='ew', pady=(4,0))

        self.lbl_st = tk.Label(right, text="Añade al menos 2 videos para empezar",
                               fg=TEXT_S, bg=BG, font=FNS, anchor='w')
        self.lbl_st.grid(row=3, column=0, sticky='ew', pady=(4,0))

    def _agregar(self):
        files = filedialog.askopenfilenames(
            title="Seleccionar videos",
            filetypes=[("Videos","*.mp4 *.avi *.mov *.mkv *.webm"),("Todos","*.*")])
        for f in files:
            if f not in self.videos:
                self.videos.append(f)
                self.lst.insert(tk.END, f"  🎬  {os.path.basename(f)}")
        self._info()

    def _subir(self):
        s = self.lst.curselection()
        if s and s[0] > 0:
            i = s[0]; self.videos[i],self.videos[i-1]=self.videos[i-1],self.videos[i]
            self._refresh_lst(); self.lst.selection_set(i-1)

    def _bajar(self):
        s = self.lst.curselection()
        if s and s[0] < len(self.videos)-1:
            i = s[0]; self.videos[i],self.videos[i+1]=self.videos[i+1],self.videos[i]
            self._refresh_lst(); self.lst.selection_set(i+1)

    def _quitar(self):
        s = self.lst.curselection()
        if s: i=s[0]; self.lst.delete(i); del self.videos[i]; self._info()

    def _limpiar(self):
        self.lst.delete(0,tk.END); self.videos=[]; self._info()

    def _refresh_lst(self):
        self.lst.delete(0,tk.END)
        for v in self.videos: self.lst.insert(tk.END, f"  🎬  {os.path.basename(v)}")

    def _info(self):
        n = len(self.videos)
        self.lbl_count.config(text=f"{n} video{'s' if n!=1 else ''}")
        if n >= 2:
            self.btn_proc.config(state='normal')
            threading.Thread(target=self._calc_dur, daemon=True).start()
        else:
            self.btn_proc.config(state='disabled'); self.lbl_dur.config(text="")

    def _calc_dur(self):
        total = 0.0
        for v in self.videos:
            try: c=VideoFileClip(v); total+=c.duration; c.close()
            except: pass
        self.lbl_dur.config(text=f"Total: {fmt(total)}")

    def _iniciar(self):
        if len(self.videos) < 2:
            messagebox.showerror("Error","Selecciona al menos 2 videos"); return
        threading.Thread(target=self._unir, daemon=True).start()

    def _unir(self):
        try:
            self.btn_proc.config(state='disabled', bg='#BDBDBD')
            self.progress.start()
            self.lbl_st.config(text="⏳ Cargando videos…", fg=ORANGE)
            clips = []
            for i, vp in enumerate(self.videos):
                self.lbl_st.config(text=f"⏳ Cargando {i+1}/{len(self.videos)}…", fg=ORANGE)
                clips.append(VideoFileClip(vp))
            self.lbl_st.config(text="⏳ Concatenando…", fg=ORANGE)
            final = concatenate_videoclips(clips, method=self.metodo.get())
            dest  = filedialog.asksaveasfilename(
                title="Guardar video concatenado",
                defaultextension=".mp4", filetypes=[("MP4","*.mp4")],
                initialfile="video_concatenado.mp4")
            if dest:
                self.lbl_st.config(text="⏳ Guardando…", fg=ORANGE)
                final.write_videofile(dest, logger=None)
                self.lbl_st.config(text="✅ Video guardado", fg=GREEN)
                messagebox.showinfo("✅ Listo",
                    f"Guardado:\n{os.path.basename(dest)}\n"
                    f"Duración: {fmt(final.duration)}")
            else:
                self.lbl_st.config(text="⏸️ Cancelado", fg=TEXT_S)
            final.close()
            for c in clips: c.close()
        except Exception as e:
            self.lbl_st.config(text="❌ Error", fg=RED)
            messagebox.showerror("Error", str(e))
        finally:
            self.progress.stop()
            if len(self.videos) >= 2:
                self.btn_proc.config(state='normal', bg=ACCENT)


# ══════════════════════════ TAB: IMÁGENES → PDF ══════════════════════════════
class TabFotosVideo:
    def __init__(self, frame, root):
        self.frame      = frame; self.root = root
        self.imagenes   = []; self.miniaturas = []
        self.sel_idx    = -1;  self.sel_frame  = None
        self.audio_path = None
        self.procesando = False
        self._build()

    def _build(self):
        body = tk.Frame(self.frame, bg=BG)
        body.pack(fill='both', expand=True, padx=10, pady=8)
        body.columnconfigure(0, weight=3)
        body.columnconfigure(1, weight=1, minsize=240)
        body.rowconfigure(0, weight=1)

        # ── Izquierda: cuadrícula de miniaturas ───────────────────────────
        left = tk.Frame(body, bg=BG)
        left.grid(row=0, column=0, sticky='nsew', padx=(0,6))
        left.rowconfigure(0, weight=1); left.columnconfigure(0, weight=1)

        gc = tk.Frame(left, bg=CARD,
                      highlightthickness=1, highlightbackground=BORDER)
        gc.grid(row=0, column=0, sticky='nsew')
        gc.rowconfigure(0, weight=1); gc.columnconfigure(0, weight=1)

        canvas = tk.Canvas(gc, bg=CARD, highlightthickness=0)
        vsb = tk.Scrollbar(gc, orient='vertical',   command=canvas.yview)
        hsb = tk.Scrollbar(gc, orient='horizontal', command=canvas.xview)
        canvas.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        vsb.pack(side='right', fill='y')
        hsb.pack(side='bottom', fill='x')
        canvas.pack(fill='both', expand=True)
        canvas.bind('<MouseWheel>',
            lambda e: canvas.yview_scroll(int(-1*(e.delta/120)), 'units'))
        self.grid_frame = tk.Frame(canvas, bg=CARD)
        self.grid_frame.bind('<Configure>',
            lambda e: canvas.configure(scrollregion=canvas.bbox('all')))
        canvas.create_window((0, 0), window=self.grid_frame, anchor='nw')

        # ── Derecha: controles ────────────────────────────────────────────
        right = tk.Frame(body, bg=BG)
        right.grid(row=0, column=1, sticky='nsew')
        right.columnconfigure(0, weight=1)

        # Cargar fotos
        lc, li = crd(right)
        lc.grid(row=0, column=0, sticky='ew')
        tk.Label(li, text="Fotos", font=FNB, fg=TEXT, bg=CARD).pack(anchor='w', pady=(0,4))
        mkbtn(li,"📂 Añadir fotos",       self._sel_files,  ACCENT, font=FNS).pack(fill='x',pady=2)
        mkbtn(li,"📁 Desde carpeta",       self._sel_folder, ACCENT, font=FNS).pack(fill='x',pady=2)
        mkbtn(li,"➕ Añadir más",          self._add_more,   GREEN,  font=FNS).pack(fill='x',pady=2)
        tk.Frame(li, bg=BORDER, height=1).pack(fill='x', pady=4)
        mkbtn(li,"⬆ Subir",               self._subir,      ACCENT, font=FNS).pack(fill='x',pady=2)
        mkbtn(li,"⬇ Bajar",               self._bajar,      ACCENT, font=FNS).pack(fill='x',pady=2)
        mkbtn(li,"🔤 Ordenar por nombre",  self._por_nombre, PURPLE, font=FNS).pack(fill='x',pady=2)
        mkbtn(li,"❌ Eliminar seleccionada",self._eliminar,  RED,    font=FNS).pack(fill='x',pady=2)
        mkbtn(li,"🗑️ Limpiar todo",         self._limpiar,  ORANGE, font=FNS).pack(fill='x',pady=2)
        self.lbl_count = tk.Label(li, text="0 fotos", fg=TEXT_S, bg=CARD, font=FNS)
        self.lbl_count.pack(anchor='w', pady=(4,0))

        # Música
        mc, mi = crd(right)
        mc.grid(row=1, column=0, sticky='ew', pady=(6,0))
        tk.Label(mi, text="Música (opcional)", font=FNB,
                 fg=TEXT, bg=CARD).pack(anchor='w', pady=(0,4))
        ar = tk.Frame(mi, bg=CARD)
        ar.pack(fill='x')
        self.lbl_audio = tk.Label(ar, text="Sin audio", fg=TEXT_S,
                                  bg=CARD, anchor='w', font=FNS)
        self.lbl_audio.pack(side='left', fill='x', expand=True)
        mkbtn(ar,"📂", self._sel_audio, ACCENT, w=3, font=FNS).pack(side='right')

        # Configuración
        cc, ci = crd(right)
        cc.grid(row=2, column=0, sticky='ew', pady=(6,0))
        tk.Label(ci, text="Configuración", font=FNB, fg=TEXT, bg=CARD).pack(anchor='w', pady=(0,6))

        def row_cfg(lbl, widget_fn):
            r = tk.Frame(ci, bg=CARD); r.pack(fill='x', pady=2)
            tk.Label(r, text=lbl, bg=CARD, fg=TEXT, font=FNS,
                     width=16, anchor='w').pack(side='left')
            widget_fn(r)

        self.v_dur = tk.StringVar(value="3")
        row_cfg("Seg por foto:", lambda r: tk.Entry(
            r, textvariable=self.v_dur, width=6, font=FN
        ).pack(side='left'))

        self.v_res = tk.StringVar()
        res_cb = ttk.Combobox(ci, textvariable=self.v_res, state='readonly',
                              values=["1920×1080 (Full HD)", "1280×720 (HD)",
                                      "854×480 (SD)", "640×360 (Pequeño)"],
                              font=FNS)
        res_cb.pack(fill='x', pady=2); res_cb.current(0)

        self.v_fps = tk.StringVar(value="24")
        row_cfg("FPS:", lambda r: tk.Spinbox(
            r, from_=1, to=60, textvariable=self.v_fps,
            width=6, font=FN
        ).pack(side='left'))

        # Procesar
        self.btn_proc = tk.Button(
            right, text="🎬  CREAR VIDEO", command=self._iniciar,
            bg=GREEN, fg='white', font=('Segoe UI',11,'bold'),
            relief='flat', pady=10, cursor='hand2',
            activebackground=GREEN, activeforeground='white')
        self.btn_proc.grid(row=3, column=0, sticky='ew', pady=(8,0))

        self.progress = ttk.Progressbar(right, mode='indeterminate')
        self.progress.grid(row=4, column=0, sticky='ew', pady=(4,0))

        self.lbl_st = tk.Label(right, text="Añade fotos para empezar",
                               fg=TEXT_S, bg=BG, font=FNS, anchor='w')
        self.lbl_st.grid(row=5, column=0, sticky='ew', pady=(2,0))

    # ── Miniaturas ────────────────────────────────────────────────────────────
    def _actualizar(self):
        for w in self.grid_frame.winfo_children(): w.destroy()
        self.miniaturas=[]; self.sel_idx=-1; self.sel_frame=None
        self.lbl_count.config(text=f"{len(self.imagenes)} fotos")
        if not self.imagenes:
            tk.Label(self.grid_frame, text="Sin fotos seleccionadas",
                     fg=TEXT_S, bg=CARD, font=FN).pack(pady=40); return
        cols = 4
        for i, path in enumerate(self.imagenes):
            r, c = divmod(i, cols)
            mf = tk.Frame(self.grid_frame, bg=CARD, relief='raised', bd=1)
            mf.grid(row=r, column=c, padx=4, pady=4, sticky='n')
            try:
                img = Image.open(path)
                img.thumbnail((110,110), Image.Resampling.LANCZOS)
                tk_img = ImageTk.PhotoImage(img)
                self.miniaturas.append(tk_img)
                lbl = tk.Label(mf, image=tk_img, bg=CARD, cursor='hand2')
                lbl.pack(padx=2, pady=2)
                nom = os.path.basename(path)
                if len(nom) > 16: nom = nom[:13]+'…'
                tk.Label(mf, text=nom, bg=CARD, font=FNS).pack()
                lbl.bind('<Button-1>', lambda e, idx=i, ff=mf: self._select(idx, ff))
                mf.bind('<Button-1>',  lambda e, idx=i, ff=mf: self._select(idx, ff))
            except:
                tk.Label(mf, text="❌ Error", bg='#EEE',
                         width=12, height=6, font=FNS).pack(padx=2, pady=2)

    def _select(self, idx, frame):
        if self.sel_frame and self.sel_frame.winfo_exists():
            try: self.sel_frame.config(relief='raised', bd=1, bg=CARD)
            except: pass
        self.sel_frame = frame
        frame.config(relief='solid', bd=2, bg=SEL_BG)
        self.sel_idx = idx

    def _reselect(self, idx):
        frames = [w for w in self.grid_frame.winfo_children()
                  if isinstance(w, tk.Frame)]
        if idx < len(frames): self._select(idx, frames[idx])

    # ── Gestión de fotos ──────────────────────────────────────────────────────
    def _sel_files(self):
        files = filedialog.askopenfilenames(
            title="Seleccionar fotos",
            filetypes=[("Imágenes","*.jpg *.jpeg *.png *.bmp *.gif *.tiff *.webp"),
                       ("Todos","*.*")])
        if files: self.imagenes=list(files); self._actualizar()

    def _sel_folder(self):
        folder = filedialog.askdirectory(title="Seleccionar carpeta")
        if folder:
            exts = {'.jpg','.jpeg','.png','.bmp','.gif','.tiff','.webp'}
            self.imagenes = sorted(
                os.path.join(folder, f) for f in os.listdir(folder)
                if os.path.splitext(f)[1].lower() in exts)
            self._actualizar()

    def _add_more(self):
        files = filedialog.askopenfilenames(
            title="Añadir fotos",
            filetypes=[("Imágenes","*.jpg *.jpeg *.png *.bmp *.gif *.tiff *.webp"),
                       ("Todos","*.*")])
        for f in files:
            if f not in self.imagenes: self.imagenes.append(f)
        self._actualizar()

    def _subir(self):
        if self.sel_idx > 0:
            i = self.sel_idx
            self.imagenes[i], self.imagenes[i-1] = self.imagenes[i-1], self.imagenes[i]
            self._actualizar(); self.root.after(100, lambda: self._reselect(i-1))

    def _bajar(self):
        if 0 <= self.sel_idx < len(self.imagenes)-1:
            i = self.sel_idx
            self.imagenes[i], self.imagenes[i+1] = self.imagenes[i+1], self.imagenes[i]
            self._actualizar(); self.root.after(100, lambda: self._reselect(i+1))

    def _por_nombre(self):
        self.imagenes.sort(key=lambda x: os.path.basename(x).lower())
        self._actualizar()

    def _eliminar(self):
        if 0 <= self.sel_idx < len(self.imagenes):
            del self.imagenes[self.sel_idx]; self._actualizar()

    def _limpiar(self):
        if messagebox.askyesno("Confirmar","¿Eliminar todas las fotos?"):
            self.imagenes=[]; self._actualizar()

    def _sel_audio(self):
        f = filedialog.askopenfilename(
            title="Seleccionar audio",
            filetypes=[("Audio","*.mp3 *.wav *.m4a *.ogg"),("Todos","*.*")])
        if f:
            self.audio_path = f
            self.lbl_audio.config(text=os.path.basename(f), fg=TEXT)

    # ── Procesamiento ─────────────────────────────────────────────────────────
    def _iniciar(self):
        if not self.imagenes:
            messagebox.showerror("Error","Selecciona al menos una foto"); return
        try:
            dur = float(self.v_dur.get())
            if dur <= 0: raise ValueError
        except:
            messagebox.showerror("Error","La duración debe ser un número positivo"); return
        if self.procesando: return
        threading.Thread(target=self._procesar, daemon=True).start()

    def _procesar(self):
        self.procesando = True
        self.btn_proc.config(state='disabled', bg='#BDBDBD')
        self.progress.start()
        try:
            dur  = float(self.v_dur.get())
            fps  = int(self.v_fps.get())
            res_map = {"1920×1080 (Full HD)":(1920,1080), "1280×720 (HD)":(1280,720),
                       "854×480 (SD)":(854,480), "640×360 (Pequeño)":(640,360)}
            tam  = res_map.get(self.v_res.get(), (1920,1080))

            clips = []
            total = len(self.imagenes)
            for i, p in enumerate(self.imagenes):
                self.lbl_st.config(
                    text=f"⏳ Procesando foto {i+1}/{total}…", fg=ORANGE)
                clips.append(ImageClip(p).with_duration(dur).resized(new_size=tam))

            self.lbl_st.config(text="⏳ Uniendo fotos…", fg=ORANGE)
            video = concatenate_videoclips(clips, method='compose')

            if self.audio_path:
                self.lbl_st.config(text="⏳ Añadiendo música…", fg=ORANGE)
                audio = AudioFileClip(self.audio_path)
                if audio.duration < video.duration:
                    reps  = int(video.duration / audio.duration) + 1
                    audio = concatenate_videoclips([audio]*reps)
                audio = audio.subclipped(0, video.duration)
                video = video.with_audio(audio)

            dest = filedialog.asksaveasfilename(
                title="Guardar video",
                defaultextension=".mp4", filetypes=[("MP4","*.mp4")],
                initialfile="fotos_a_video.mp4")
            if dest:
                self.lbl_st.config(text="⏳ Guardando…", fg=ORANGE)
                video.write_videofile(dest, fps=fps, logger=None)
                self.lbl_st.config(text="✅ Video creado", fg=GREEN)
                messagebox.showinfo("✅ Listo",
                    f"Video guardado:\n{dest}\n\n"
                    f"Fotos: {total}  ·  Duración: {fmt(video.duration)}")
            else:
                self.lbl_st.config(text="⏸️ Cancelado", fg=TEXT_S)
            video.close()

        except Exception as e:
            self.lbl_st.config(text="❌ Error", fg=RED)
            messagebox.showerror("Error", str(e))
        finally:
            self.progress.stop()
            self.procesando = False
            self.btn_proc.config(state='normal', bg=GREEN)


# ══════════════════════════ TAB: CONVERTIR FORMATO ═══════════════════════════
class TabConvertir:
    # Formatos de salida con sus opciones
    FORMATOS = {
        "MP4  (H.264)":   {"ext": ".mp4",  "vcodec": "libx264",  "acodec": "aac"},
        "MP4  (H.265)":   {"ext": ".mp4",  "vcodec": "libx265",  "acodec": "aac"},
        "AVI":            {"ext": ".avi",  "vcodec": "mpeg4",    "acodec": "mp3"},
        "MOV":            {"ext": ".mov",  "vcodec": "libx264",  "acodec": "aac"},
        "MKV":            {"ext": ".mkv",  "vcodec": "libx264",  "acodec": "aac"},
        "WEBM":           {"ext": ".webm", "vcodec": "libvpx",   "acodec": "libvorbis"},
        "GIF  (sin audio)":{"ext":".gif",  "vcodec": None,       "acodec": None},
        "Solo audio MP3": {"ext": ".mp3",  "vcodec": None,       "acodec": "mp3"},
        "Solo audio WAV": {"ext": ".wav",  "vcodec": None,       "acodec": "pcm_s16le"},
        "Solo audio AAC": {"ext": ".aac",  "vcodec": None,       "acodec": "aac"},
    }

    CALIDADES = {
        "Alta  (CRF 18)":  18,
        "Media (CRF 23)":  23,
        "Baja  (CRF 28)":  28,
    }

    RESOLUCIONES = {
        "Original":         None,
        "4K  (3840×2160)":  (3840, 2160),
        "Full HD (1920×1080)": (1920, 1080),
        "HD  (1280×720)":   (1280, 720),
        "SD  (854×480)":    (854, 480),
    }

    def __init__(self, frame, root):
        self.frame      = frame
        self.root       = root
        self.videos     = []   # lista de rutas
        self.procesando = False
        self._build()

    def _build(self):
        body = tk.Frame(self.frame, bg=BG)
        body.pack(fill='both', expand=True, padx=10, pady=8)
        body.columnconfigure(0, weight=3)
        body.columnconfigure(1, weight=2, minsize=280)
        body.rowconfigure(0, weight=1)

        # ── Izquierda: lista de videos ────────────────────────────────────
        left = tk.Frame(body, bg=BG)
        left.grid(row=0, column=0, sticky='nsew', padx=(0, 6))
        left.columnconfigure(0, weight=1)
        left.rowconfigure(1, weight=1)

        # Cabecera
        hc, hi = crd(left)
        hc.grid(row=0, column=0, sticky='ew', pady=(0, 4))
        tk.Label(hi, text="Videos a convertir", font=FNB,
                 fg=TEXT, bg=CARD).pack(anchor='w')
        tk.Label(hi, text="Puedes convertir varios archivos a la vez",
                 font=FNS, fg=TEXT_S, bg=CARD).pack(anchor='w')

        # Lista
        lc, li = crd(left)
        lc.grid(row=1, column=0, sticky='nsew')

        brow = tk.Frame(li, bg=CARD)
        brow.pack(fill='x', pady=(0, 4))
        mkbtn(brow, "➕ Añadir videos", self._agregar, ACCENT, font=FNS).pack(side='left', padx=(0,3))
        mkbtn(brow, "❌ Quitar",         self._quitar,  RED,    font=FNS).pack(side='left', padx=3)
        mkbtn(brow, "🗑️ Limpiar",        self._limpiar, ORANGE, font=FNS).pack(side='left', padx=3)

        lf = tk.Frame(li, bg=CARD)
        lf.pack(fill='both', expand=True)
        self.lst = tk.Listbox(lf, bg=BG, fg=TEXT, font=FMO, relief='flat',
                              selectbackground=SEL_BG, selectforeground=TEXT,
                              highlightthickness=1, highlightcolor=BORDER,
                              activestyle='none')
        self.lst.pack(side='left', fill='both', expand=True)
        scr = tk.Scrollbar(lf, command=self.lst.yview)
        scr.pack(side='right', fill='y')
        self.lst.config(yscrollcommand=scr.set)

        self.lbl_count = tk.Label(li, text="0 archivos",
                                  fg=TEXT_S, bg=CARD, font=FNS)
        self.lbl_count.pack(anchor='w', pady=(4, 0))

        # ── Derecha: opciones + procesar ──────────────────────────────────
        right = tk.Frame(body, bg=BG)
        right.grid(row=0, column=1, sticky='nsew')
        right.columnconfigure(0, weight=1)

        # Formato de salida
        fc, fi = crd(right)
        fc.grid(row=0, column=0, sticky='ew')
        tk.Label(fi, text="Formato de salida", font=FNB,
                 fg=TEXT, bg=CARD).pack(anchor='w', pady=(0, 6))

        self.v_fmt = tk.StringVar()
        fmt_cb = ttk.Combobox(fi, textvariable=self.v_fmt,
                              values=list(self.FORMATOS.keys()),
                              state='readonly', font=FN)
        fmt_cb.pack(fill='x'); fmt_cb.current(0)
        fmt_cb.bind('<<ComboboxSelected>>', self._on_fmt_change)

        self.lbl_fmt_info = tk.Label(fi, text="Video: H.264  ·  Audio: AAC",
                                     fg=TEXT_S, bg=CARD, font=FNS, anchor='w')
        self.lbl_fmt_info.pack(fill='x', pady=(4, 0))

        # Calidad
        qc, qi = crd(right)
        qc.grid(row=1, column=0, sticky='ew', pady=(6, 0))
        tk.Label(qi, text="Calidad de video", font=FNB,
                 fg=TEXT, bg=CARD).pack(anchor='w', pady=(0, 6))

        self.v_cal = tk.StringVar()
        cal_cb = ttk.Combobox(qi, textvariable=self.v_cal,
                              values=list(self.CALIDADES.keys()),
                              state='readonly', font=FN)
        cal_cb.pack(fill='x'); cal_cb.current(0)
        tk.Label(qi, text="CRF más bajo = mayor calidad y mayor tamaño",
                 fg=TEXT_S, bg=CARD, font=FNS).pack(anchor='w', pady=(4, 0))

        # Resolución
        rc, ri = crd(right)
        rc.grid(row=2, column=0, sticky='ew', pady=(6, 0))
        tk.Label(ri, text="Resolución de salida", font=FNB,
                 fg=TEXT, bg=CARD).pack(anchor='w', pady=(0, 6))

        self.v_res = tk.StringVar()
        res_cb = ttk.Combobox(ri, textvariable=self.v_res,
                              values=list(self.RESOLUCIONES.keys()),
                              state='readonly', font=FN)
        res_cb.pack(fill='x'); res_cb.current(0)

        # Carpeta de destino
        dc, di = crd(right)
        dc.grid(row=3, column=0, sticky='ew', pady=(6, 0))
        tk.Label(di, text="Carpeta de destino", font=FNB,
                 fg=TEXT, bg=CARD).pack(anchor='w', pady=(0, 4))

        dr = tk.Frame(di, bg=CARD); dr.pack(fill='x')
        self.lbl_dest = tk.Label(dr, text="Misma carpeta que el original",
                                 fg=TEXT_S, bg=CARD, font=FNS, anchor='w')
        self.lbl_dest.pack(side='left', fill='x', expand=True)
        mkbtn(dr, "📁", self._sel_dest, ACCENT, w=3, font=FNS).pack(side='right')
        self.dest_folder = None  # None = misma carpeta

        # Botón procesar
        self.btn_proc = tk.Button(
            right, text="🔄  CONVERTIR",
            command=self._iniciar,
            bg=PURPLE, fg='white', font=('Segoe UI', 11, 'bold'),
            relief='flat', pady=10, cursor='hand2', state='disabled',
            activebackground=PURPLE, activeforeground='white')
        self.btn_proc.grid(row=4, column=0, sticky='ew', pady=(10, 0))

        self.progress = ttk.Progressbar(right, mode='indeterminate')
        self.progress.grid(row=5, column=0, sticky='ew', pady=(4, 0))

        self.lbl_st = tk.Label(right, text="Añade videos para empezar",
                               fg=TEXT_S, bg=BG, font=FNS, anchor='w')
        self.lbl_st.grid(row=6, column=0, sticky='ew', pady=(4, 0))

    # ── Helpers ───────────────────────────────────────────────────────────────
    def _on_fmt_change(self, e=None):
        cfg = self.FORMATOS.get(self.v_fmt.get(), {})
        vc  = cfg.get('vcodec') or '—'
        ac  = cfg.get('acodec') or '—'
        self.lbl_fmt_info.config(text=f"Codec video: {vc}  ·  Codec audio: {ac}")

    def _sel_dest(self):
        f = filedialog.askdirectory(title="Seleccionar carpeta de destino")
        if f:
            self.dest_folder = f
            nom = f if len(f) <= 40 else '…' + f[-38:]
            self.lbl_dest.config(text=nom, fg=TEXT)

    def _agregar(self):
        files = filedialog.askopenfilenames(
            title="Seleccionar videos",
            filetypes=[("Videos", "*.mp4 *.avi *.mov *.mkv *.webm *.m4v *.mpg *.mpeg"),
                       ("Todos", "*.*")])
        for f in files:
            if f not in self.videos:
                self.videos.append(f)
                self.lst.insert(tk.END, f"  🎬  {os.path.basename(f)}")
        self._update_count()

    def _quitar(self):
        sel = self.lst.curselection()
        if sel:
            i = sel[0]; self.lst.delete(i); del self.videos[i]
            self._update_count()

    def _limpiar(self):
        self.lst.delete(0, tk.END); self.videos = []
        self._update_count()

    def _update_count(self):
        n = len(self.videos)
        self.lbl_count.config(text=f"{n} archivo{'s' if n != 1 else ''}")
        self.btn_proc.config(state='normal' if n > 0 else 'disabled')

    def _status(self, msg):
        col = (GREEN if msg.startswith("✅") else
               RED   if msg.startswith("❌") else
               ORANGE if msg.startswith("⏳") else TEXT_S)
        self.lbl_st.config(text=msg, fg=col)

    # ── Procesamiento ─────────────────────────────────────────────────────────
    def _iniciar(self):
        if not self.videos: return
        if self.procesando: return
        threading.Thread(target=self._convertir, daemon=True).start()

    def _convertir(self):
        self.procesando = True
        self.btn_proc.config(state='disabled', bg='#BDBDBD')
        self.progress.start()
        total   = len(self.videos)
        ok      = 0
        errores = []

        try:
            cfg  = self.FORMATOS[self.v_fmt.get()]
            ext  = cfg['ext']
            vc   = cfg['vcodec']
            ac   = cfg['acodec']
            crf  = self.CALIDADES.get(self.v_cal.get(), 23)
            res  = self.RESOLUCIONES.get(self.v_res.get())
            solo_audio = (vc is None and ac is not None)
            gif        = (ext == '.gif')

            for i, src in enumerate(self.videos):
                nombre = os.path.basename(src)
                self._status(f"⏳ [{i+1}/{total}]  {nombre}…")

                carpeta = (self.dest_folder
                           if self.dest_folder
                           else os.path.dirname(src))
                base    = os.path.splitext(nombre)[0]
                dest    = os.path.join(carpeta, base + ext)

                # Evitar sobreescribir el propio archivo
                if os.path.abspath(src) == os.path.abspath(dest):
                    base += "_convertido"
                    dest  = os.path.join(carpeta, base + ext)

                try:
                    clip = VideoFileClip(src)

                    # Redimensionar si hace falta
                    if res:
                        clip = clip.resized(new_size=res)

                    if gif:
                        clip.write_gif(dest, logger=None)

                    elif solo_audio:
                        if clip.audio is None:
                            raise ValueError("El video no tiene pista de audio")
                        clip.audio.write_audiofile(dest, logger=None,
                                                   codec=ac)
                    else:
                        kw = dict(logger=None, audio_codec=ac)
                        if vc:
                            kw['codec'] = vc
                        if vc in ('libx264', 'libx265', 'mpeg4'):
                            kw['ffmpeg_params'] = ['-crf', str(crf)]
                        clip.write_videofile(dest, **kw)

                    clip.close()
                    ok += 1

                except Exception as e:
                    errores.append(f"{nombre}: {e}")
                    try: clip.close()
                    except: pass

        except Exception as e:
            self._status(f"❌ Error inesperado: {e}")
            messagebox.showerror("Error", str(e))
        else:
            if ok == total:
                self._status(f"✅ {ok} archivo{'s' if ok!=1 else ''} convertido{'s' if ok!=1 else ''}")
                messagebox.showinfo("✅ Listo",
                    f"Conversión completada.\n{ok} de {total} archivos convertidos.")
            else:
                self._status(f"⚠️ {ok}/{total} convertidos — {len(errores)} con error")
                detalle = "\n".join(errores[:8])
                messagebox.showwarning("Completado con errores",
                    f"{ok} de {total} convertidos.\n\nErrores:\n{detalle}")
        finally:
            self.progress.stop()
            self.procesando = False
            self.btn_proc.config(
                state='normal' if self.videos else 'disabled',
                bg=PURPLE)


# ══════════════════════════ APLICACIÓN PRINCIPAL ═════════════════════════════
class VideoStudio:
    WIN_W, WIN_H = 1060, 720

    def __init__(self, root):
        self.root = root
        root.title("🎬 Video Studio")
        root.configure(bg=BG)
        sw, sh = root.winfo_screenwidth(), root.winfo_screenheight()
        x = (sw - self.WIN_W) // 2
        root.geometry(f"{self.WIN_W}x{self.WIN_H}+{x}+20")
        root.minsize(900, 620)

        pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=1024)
        self._build()

    def _build(self):
        root = self.root

        # Barra superior
        top = tk.Frame(root, bg=ACCENT)
        top.pack(fill='x')
        tk.Label(top, text="🎬  VIDEO STUDIO",
                 font=FNT, fg='white', bg=ACCENT, pady=8).pack(side='left', padx=14)
        tk.Label(top,
                 text="Cortador  ·  Editor  ·  Unir  ·  Fotos a Video  ·  Convertir",
                 fg='#BBDEFB', bg=ACCENT, font=FNS).pack(side='left', padx=4)

        # Notebook principal
        sty = ttk.Style()
        sty.configure('M.TNotebook',     background=BG,    borderwidth=0)
        sty.configure('M.TNotebook.Tab', background=BORDER,
                      foreground=TEXT, font=FNB, padding=[14, 7])
        sty.map('M.TNotebook.Tab',
                background=[('selected', ACCENT)],
                foreground=[('selected', 'maroon')])

        self.nb = ttk.Notebook(root, style='M.TNotebook')
        self.nb.pack(fill='both', expand=True)

        frames = []
        for label in ["  ✂️  Cortador  ",
                      "  🎬  Editor  ",
                      "  🔗  Unir  ",
                      "  🖼️  Fotos a Video  ",
                      "  🔄  Convertir  "]:
            f = tk.Frame(self.nb, bg=BG)
            self.nb.add(f, text=label)
            frames.append(f)

        self.cortador  = TabCortador(   frames[0], root)
        self.editor    = TabEditor(     frames[1], root)
        self.concat    = TabUnir( frames[2], root)
        self.img_pdf   = TabFotosVideo( frames[3], root)
        self.convertir = TabConvertir(  frames[4], root)

        self.cortador.bind_keys()
        self.nb.bind('<<NotebookTabChanged>>', self._on_tab)

    def _on_tab(self, e):
        if self.nb.index('current') == 0:
            self.cortador.bind_keys()
        else:
            self.cortador.unbind_keys()

    def __del__(self):
        try:
            c = self.cortador
            if c.temp_audio and os.path.exists(c.temp_audio):
                os.unlink(c.temp_audio)
            pygame.mixer.quit()
        except: pass


# ── Entry point ───────────────────────────────────────────────────────────────
if __name__ == '__main__':
    root = tk.Tk()
    app  = VideoStudio(root)
    root.mainloop()
