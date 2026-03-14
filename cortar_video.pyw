# -*- coding: utf-8 -*-

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import os
import pygame
from moviepy import VideoFileClip, concatenate_videoclips
from moviepy.video.fx import CrossFadeIn, CrossFadeOut
from PIL import Image, ImageTk
import tempfile
import subprocess
import sys

# Ocultar consola en Windows
if sys.platform == "win32":
    import ctypes
    ctypes.windll.kernel32.SetConsoleTitleW("CortadorVideo")

class RangeSelector(tk.Canvas):
    """Selector de rango compacto integrado en la línea de tiempo"""
    
    def __init__(self, parent, from_=0, to=100, command=None, height=40, **kwargs):
        super().__init__(parent, height=height, bg='#f0f0f0', highlightthickness=0, **kwargs)
        
        self.from_ = from_
        self.to = to
        self.command = command
        self.dragging = None
        self.bind('<Button-1>', self.on_click)
        self.bind('<B1-Motion>', self.on_drag)
        self.bind('<ButtonRelease-1>', self.on_release)
        self.bind('<Configure>', lambda e: self.draw())
        
        self.low_pct = 0
        self.high_pct = 100
        self.current_pct = 0
        self.draw()
    
    def set_range(self, from_, to):
        self.from_ = from_
        self.to = to
        self.draw()
    
    def set_values(self, low, high):
        if self.to > self.from_:
            self.low_pct = ((low - self.from_) / (self.to - self.from_)) * 100
            self.high_pct = ((high - self.from_) / (self.to - self.from_)) * 100
            self.draw()
    
    def get_values(self):
        if self.to > self.from_:
            low = self.from_ + (self.low_pct / 100) * (self.to - self.from_)
            high = self.from_ + (self.high_pct / 100) * (self.to - self.from_)
            return low, high
        return self.from_, self.to
    
    def set_current(self, value):
        if self.to > self.from_:
            self.current_pct = ((value - self.from_) / (self.to - self.from_)) * 100
            self.draw()
    
    def draw(self):
        self.delete('all')
        w = self.winfo_width()
        if w <= 1:
            w = 400
        
        # Barra de fondo
        self.create_rectangle(10, 15, w-10, 25, fill='#dddddd', outline='#999999', width=1)
        
        # Rango seleccionado - siempre mostrar inicio < fin
        x1 = 10 + int((self.low_pct / 100) * (w - 20))
        x2 = 10 + int((self.high_pct / 100) * (w - 20))
        
        # Asegurar que x1 < x2 para el dibujo
        if x1 > x2:
            x1, x2 = x2, x1
        
        self.create_rectangle(x1, 15, x2, 25, fill='#4CAF50', outline='')
        
        # Marcadores (mantener sus posiciones originales)
        x1_orig = 10 + int((self.low_pct / 100) * (w - 20))
        x2_orig = 10 + int((self.high_pct / 100) * (w - 20))
        
        self.create_oval(x1_orig-4, 13, x1_orig+4, 21, fill='white', outline='#2196F3', width=2)
        self.create_oval(x2_orig-4, 13, x2_orig+4, 21, fill='white', outline='#FF9800', width=2)
        
        # Playhead (posición actual)
        x_current = 10 + int((self.current_pct / 100) * (w - 20))
        self.create_line(x_current, 10, x_current, 30, fill='red', width=2)
    
    def on_click(self, event):
        x = event.x
        w = self.winfo_width()
        x1 = 10 + int((self.low_pct / 100) * (w - 20))
        x2 = 10 + int((self.high_pct / 100) * (w - 20))
        
        # Detectar qué marcador está más cerca
        dist1 = abs(x - x1)
        dist2 = abs(x - x2)
        
        if dist1 < 8 and dist1 < dist2:
            self.dragging = 'low'
        elif dist2 < 8:
            self.dragging = 'high'
    
    def on_drag(self, event):
        if not self.dragging:
            return
        
        w = self.winfo_width()
        x = max(10, min(event.x, w-10))
        pct = ((x - 10) / (w - 20)) * 100
        
        if self.dragging == 'low':
            self.low_pct = max(0, min(pct, 100))
        elif self.dragging == 'high':
            self.high_pct = max(0, min(pct, 100))
        
        self.draw()
        
        # Llamar al comando con los valores ordenados
        if self.command:
            low, high = self.get_values()
            # Asegurar que low <= high para el comando
            if low > high:
                low, high = high, low
            self.command(low, high)
    
    def on_release(self, event):
        self.dragging = None
        if self.command:
            low, high = self.get_values()
            # Asegurar que low <= high para el comando
            if low > high:
                low, high = high, low
            self.command(low, high)


class CortadorVideo:
    def __init__(self, root):
        self.root = root
        self.root.title("✂️ Cortador de Video")
        
        # Configurar ventana
        ancho = 580
        alto = 820
        pos_x = (self.root.winfo_screenwidth() // 2) - (ancho // 2)
        self.root.geometry(f"{ancho}x{alto}+{pos_x}+20")
        self.root.minsize(550, 750)
        self.root.configure(bg='#f0f0f0')
        
        # Inicializar pygame mixer
        pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=1024)
        
        self.video_path = None
        self.video_clip = None
        self.duracion = 0
        self.playing = False
        self.current_time = 0
        self.fragmentos_guardar = []  # Fragmentos a GUARDAR
        self.fragmentos_eliminar = []  # Fragmentos a ELIMINAR
        self.modo = "guardar"
        self.update_job = None
        self.audio_loaded = False
        self.temp_audio_file = None
        
        # Opciones de procesamiento
        self.guardar_separado = tk.BooleanVar(value=False)
        self.usar_transiciones = tk.BooleanVar(value=False)
        self.duracion_transicion = tk.DoubleVar(value=0.5)
        
        self.crear_interfaz()
    
    def format_time(self, seconds):
        minutos = int(seconds // 60)
        segs = int(seconds % 60)
        return f"{minutos}:{segs:02d}"
    
    def crear_interfaz(self):
        # Frame principal con scroll
        main_canvas = tk.Canvas(self.root, bg='#f0f0f0', highlightthickness=0)
        scrollbar = tk.Scrollbar(self.root, orient='vertical', command=main_canvas.yview)
        scrollable_frame = tk.Frame(main_canvas, bg='#f0f0f0')
        
        scrollable_frame.bind('<Configure>', 
            lambda e: main_canvas.configure(scrollregion=main_canvas.bbox('all')))
        
        main_canvas.create_window((0, 0), window=scrollable_frame, anchor='nw')
        main_canvas.configure(yscrollcommand=scrollbar.set)
        
        main_canvas.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')
        
        # Contenido
        main_frame = tk.Frame(scrollable_frame, bg='#f0f0f0', padx=15, pady=10)
        main_frame.pack(fill='both', expand=True)
        
        # Título
        tk.Label(main_frame, text="✂️ CORTADOR DE VIDEO (Seleccionar/Borrar)", 
                font=('Arial', 14, 'bold'), fg='#4CAF50', bg='#f0f0f0').pack(pady=(0, 10))
        
        # === SECCIÓN VIDEO ===
        video_frame = tk.Frame(main_frame, bg='white', relief='solid', bd=1)
        video_frame.pack(fill='x', pady=5)
        
        # Cabecera
        tk.Label(video_frame, text="📹 VIDEO", font=('Arial', 10, 'bold'),
                fg='#4CAF50', bg='white').pack(anchor='w', padx=8, pady=5)
        
        # Info y botón en una línea
        info_line = tk.Frame(video_frame, bg='white')
        info_line.pack(fill='x', padx=8, pady=2)
        
        self.video_label = tk.Label(info_line, text="Ningún video seleccionado",
                                   fg='#999999', bg='white', anchor='w')
        self.video_label.pack(side='left', fill='x', expand=True)
        
        self.btn_seleccionar = tk.Button(info_line, text="Seleccionar",
                                        command=self.seleccionar_video,
                                        bg='#4CAF50', fg='white',
                                        relief='flat', padx=10, font=('Arial', 8))
        self.btn_seleccionar.pack(side='right')
        
        # Detalles del video
        self.info_label = tk.Label(video_frame, text="", bg='white', fg='#666666',
                                  font=('Arial', 8), anchor='w')
        self.info_label.pack(fill='x', padx=8, pady=2)
        
        # === VISOR ===
        visor_frame = tk.Frame(main_frame, bg='black', width=500, height=280)
        visor_frame.pack(pady=8)
        visor_frame.pack_propagate(False)
        
        self.video_visor = tk.Label(visor_frame, bg='black')
        self.video_visor.pack(expand=True)
        
        # === CONTROLES DE REPRODUCCIÓN ===
        control_frame = tk.Frame(main_frame, bg='white', relief='solid', bd=1)
        control_frame.pack(fill='x', pady=5)
        
        # Botones en una línea compacta
        buttons = tk.Frame(control_frame, bg='white')
        buttons.pack(pady=5)
        
        self.btn_play = tk.Button(buttons, text="▶", width=2,
                                  command=self.toggle_playback,
                                  bg='#4CAF50', fg='white',
                                  state='disabled', font=('Arial', 9))
        self.btn_play.pack(side='left', padx=1)
        
        self.btn_pause = tk.Button(buttons, text="⏸", width=2,
                                   command=self.pause_video,
                                   bg='#FF9800', fg='white',
                                   state='disabled', font=('Arial', 9))
        self.btn_pause.pack(side='left', padx=1)
        
        self.btn_stop = tk.Button(buttons, text="⏹", width=2,
                                  command=self.stop_video,
                                  bg='#F44336', fg='white',
                                  state='disabled', font=('Arial', 9))
        self.btn_stop.pack(side='left', padx=1)
        
        # Control de volumen
        tk.Label(buttons, text="🔊", bg='white', font=('Arial', 9)).pack(side='left', padx=(5,0))
        
        self.volume_scale = tk.Scale(buttons, from_=0, to=100, orient='horizontal',
                                     length=50, command=self.cambiar_volumen,
                                     bg='white', highlightthickness=0, showvalue=0)
        self.volume_scale.set(70)
        self.volume_scale.pack(side='left', padx=2)
        
        # Tiempo actual / total
        self.time_label = tk.Label(buttons, text="0:00 / 0:00",
                                   bg='white', font=('Arial', 8))
        self.time_label.pack(side='left', padx=10)
        
        # === SELECTOR DE MODO ===
        modo_frame = tk.Frame(main_frame, bg='white', relief='solid', bd=1)
        modo_frame.pack(fill='x', pady=5)
        
        tk.Label(modo_frame, text="🎯 MODO DE OPERACIÓN:",
                font=('Arial', 9), fg='#333333', bg='white').pack(anchor='w', padx=8, pady=5)
        
        modo_buttons = tk.Frame(modo_frame, bg='white')
        modo_buttons.pack(pady=5)
        
        self.btn_modo_guardar = tk.Button(modo_buttons, text="📋 Guardar selección",
                                         command=lambda: self.cambiar_modo("guardar"),
                                         bg='#4CAF50', fg='white',
                                         relief='flat', padx=10, font=('Arial', 8))
        self.btn_modo_guardar.pack(side='left', padx=2)
        
        self.btn_modo_eliminar = tk.Button(modo_buttons, text="🗑️ Eliminar selección",
                                          command=lambda: self.cambiar_modo("eliminar"),
                                          bg='#cccccc', fg='white',
                                          relief='flat', padx=10, font=('Arial', 8))
        self.btn_modo_eliminar.pack(side='left', padx=2)
        
        self.modo_label = tk.Label(modo_frame, text="Modo actual: Guardar fragmentos",
                                   bg='white', fg='#4CAF50', font=('Arial', 8, 'bold'))
        self.modo_label.pack(pady=2)
        
        # === SELECTOR DE RANGO ===
        selector_frame = tk.Frame(main_frame, bg='white', relief='solid', bd=1)
        selector_frame.pack(fill='x', pady=5)
        
        tk.Label(selector_frame, text="🎯 Arrastra los marcadores para seleccionar:",
                font=('Arial', 9), fg='#333333', bg='white').pack(anchor='w', padx=8, pady=5)
        
        # Selector personalizado
        self.range_selector = RangeSelector(selector_frame, height=35,
                                           command=self.on_range_changed)
        self.range_selector.pack(fill='x', padx=8, pady=2)
        
        # Botones de marcado
        mark_buttons = tk.Frame(selector_frame, bg='white')
        mark_buttons.pack(pady=5)
        
        self.btn_mark_start = tk.Button(mark_buttons, text="📌 Marcar Inicio",
                                        command=self.marcar_inicio,
                                        bg='#2196F3', fg='white',
                                        state='disabled', relief='flat',
                                        font=('Arial', 8), padx=5)
        self.btn_mark_start.pack(side='left', padx=2)
        
        self.btn_mark_end = tk.Button(mark_buttons, text="📍 Marcar Fin",
                                      command=self.marcar_fin,
                                      bg='#FF9800', fg='white',
                                      state='disabled', relief='flat',
                                      font=('Arial', 8), padx=5)
        self.btn_mark_end.pack(side='left', padx=2)
        
        self.btn_go_start = tk.Button(mark_buttons, text="⏮ Ir a Inicio",
                                      command=self.ir_a_inicio,
                                      bg='#9C27B0', fg='white',
                                      state='disabled', relief='flat',
                                      font=('Arial', 8), padx=5)
        self.btn_go_start.pack(side='left', padx=2)
        
        self.btn_go_end = tk.Button(mark_buttons, text="⏭ Ir a Fin",
                                    command=self.ir_a_fin,
                                    bg='#9C27B0', fg='white',
                                    state='disabled', relief='flat',
                                    font=('Arial', 8), padx=5)
        self.btn_go_end.pack(side='left', padx=2)
        
        # Tiempos del fragmento
        time_display = tk.Frame(selector_frame, bg='white')
        time_display.pack(fill='x', padx=8, pady=5)
        
        self.start_label = tk.Label(time_display, text="Inicio: 0:00",
                                    fg='#2196F3', bg='white', font=('Arial', 8, 'bold'))
        self.start_label.pack(side='left', padx=5)
        
        self.end_label = tk.Label(time_display, text="Fin: 0:00",
                                  fg='#FF9800', bg='white', font=('Arial', 8, 'bold'))
        self.end_label.pack(side='left', padx=5)
        
        self.duration_label = tk.Label(time_display, text="Duración: 0:00",
                                       fg='#4CAF50', bg='white', font=('Arial', 8, 'bold'))
        self.duration_label.pack(side='right', padx=5)
        
        # === GESTIÓN DE FRAGMENTOS ===
        lista_frame = tk.Frame(main_frame, bg='white', relief='solid', bd=1)
        lista_frame.pack(fill='x', pady=5)
        
        self.lista_titulo = tk.Label(lista_frame, text="📋 FRAGMENTOS SELECCIONADOS",
                font=('Arial', 9, 'bold'), fg='#4CAF50', bg='white')
        self.lista_titulo.pack(anchor='w', padx=8, pady=5)
        
        # Lista
        list_frame = tk.Frame(lista_frame, bg='white')
        list_frame.pack(fill='x', padx=8, pady=2)
        
        self.lista = tk.Listbox(list_frame, height=3, bg='white', font=('Arial', 8))
        self.lista.pack(side='left', fill='x', expand=True)
        
        scroll = tk.Scrollbar(list_frame)
        scroll.pack(side='right', fill='y')
        self.lista.config(yscrollcommand=scroll.set)
        scroll.config(command=self.lista.yview)
        
        # Botones de fragmentos
        frag_buttons = tk.Frame(lista_frame, bg='white')
        frag_buttons.pack(pady=5)
        
        self.btn_add = tk.Button(frag_buttons, text="➕ Añadir",
                                 command=self.aniadir_fragmento,
                                 bg='#4CAF50', fg='white',
                                 state='disabled', relief='flat',
                                 font=('Arial', 8), padx=8)
        self.btn_add.pack(side='left', padx=2)
        
        self.btn_delete = tk.Button(frag_buttons, text="❌ Quitar",
                                    command=self.eliminar_de_lista,
                                    bg='#F44336', fg='white',
                                    state='disabled', relief='flat',
                                    font=('Arial', 8), padx=8)
        self.btn_delete.pack(side='left', padx=2)
        
        self.btn_clear = tk.Button(frag_buttons, text="🗑️ Limpiar",
                                   command=self.limpiar_lista,
                                   bg='#9C27B0', fg='white',
                                   state='disabled', relief='flat',
                                   font=('Arial', 8), padx=8)
        self.btn_clear.pack(side='left', padx=2)
        
        # === OPCIONES DE PROCESAMIENTO ===
        opciones_frame = tk.Frame(main_frame, bg='white', relief='solid', bd=1)
        opciones_frame.pack(fill='x', pady=5)
        
        tk.Label(opciones_frame, text="⚙️ OPCIONES AVANZADAS",
                font=('Arial', 9, 'bold'), fg='#9C27B0', bg='white').pack(anchor='w', padx=8, pady=5)
        
        # Opción: Guardar fragmentos por separado
        tk.Checkbutton(opciones_frame, text="Guardar cada fragmento en archivos separados",
                      variable=self.guardar_separado, bg='white',
                      font=('Arial', 8)).pack(anchor='w', padx=15, pady=2)
        
        # Opción: Usar transiciones
        trans_frame = tk.Frame(opciones_frame, bg='white')
        trans_frame.pack(fill='x', padx=15, pady=2)
        
        tk.Checkbutton(trans_frame, text="Usar transiciones entre fragmentos",
                      variable=self.usar_transiciones, bg='white',
                      command=self.actualizar_opciones_transicion,
                      font=('Arial', 8)).pack(side='left')
        
        # Duración de la transición
        self.trans_label = tk.Label(trans_frame, text="Duración (s):", bg='white', font=('Arial', 8))
        self.trans_label.pack(side='left', padx=(10,2))
        
        self.trans_spinbox = tk.Spinbox(trans_frame, from_=0.1, to=3.0, increment=0.1,
                                        textvariable=self.duracion_transicion,
                                        width=5, state='disabled', font=('Arial', 8))
        self.trans_spinbox.pack(side='left')
        
        tk.Label(trans_frame, text="seg", bg='white', font=('Arial', 8)).pack(side='left')
        
        # === BOTÓN DE PROCESAR ===
        self.btn_process = tk.Button(main_frame, 
                                     text="✂️ PROCESAR VIDEO",
                                     command=self.iniciar_procesamiento,
                                     bg='#4CAF50', fg='white',
                                     font=('Arial', 12, 'bold'),
                                     padx=20, pady=10, relief='flat',
                                     state='disabled')
        self.btn_process.pack(pady=10)
        
        # === BARRA DE PROGRESO ===
        self.progress = ttk.Progressbar(main_frame, mode='indeterminate', length=350)
        self.progress.pack(pady=5)
        
        self.status_label = tk.Label(main_frame, text="✅ Listo",
                                     fg='#4CAF50', bg='#f0f0f0', font=('Arial', 8))
        self.status_label.pack()
        
        # Bind para actualizar selector
        self.range_selector.bind('<Configure>', lambda e: self.range_selector.draw())
    
    def actualizar_opciones_transicion(self):
        """Habilita/deshabilita el spinbox de duración de transición"""
        estado = 'normal' if self.usar_transiciones.get() else 'disabled'
        self.trans_spinbox.config(state=estado)
    
    def cambiar_modo(self, modo):
        """Cambia entre modo guardar y modo eliminar"""
        self.modo = modo
        if modo == "guardar":
            self.modo_label.config(text="Modo actual: Guardar fragmentos", fg='#4CAF50')
            self.btn_modo_guardar.config(bg='#4CAF50')
            self.btn_modo_eliminar.config(bg='#cccccc')
            self.lista_titulo.config(text="📋 FRAGMENTOS A GUARDAR", fg='#4CAF50')
            self.btn_add.config(bg='#4CAF50')
            self.btn_process.config(bg='#4CAF50')
        else:
            self.modo_label.config(text="Modo actual: Eliminar fragmentos", fg='#F44336')
            self.btn_modo_guardar.config(bg='#cccccc')
            self.btn_modo_eliminar.config(bg='#F44336')
            self.lista_titulo.config(text="🗑️ FRAGMENTOS A ELIMINAR", fg='#F44336')
            self.btn_add.config(bg='#F44336')
            self.btn_process.config(bg='#F44336')
        
        self.actualizar_lista()
    
    def actualizar_lista(self):
        """Actualiza la lista según el modo actual"""
        self.lista.delete(0, tk.END)
        fragmentos = self.fragmentos_guardar if self.modo == "guardar" else self.fragmentos_eliminar
        for i, frag in enumerate(fragmentos):
            self.lista.insert('end', f"{i+1}: {self.format_time(frag['inicio'])} - {self.format_time(frag['fin'])} ({(frag['fin']-frag['inicio']):.1f}s)")
    
    def extraer_audio_silencioso(self, video_path):
        """Extrae audio sin mostrar ventanas de consola"""
        try:
            if self.temp_audio_file and os.path.exists(self.temp_audio_file):
                os.unlink(self.temp_audio_file)
            
            self.temp_audio_file = tempfile.NamedTemporaryFile(suffix='.wav', delete=False).name
            
            startupinfo = None
            if sys.platform == "win32":
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startupinfo.wShowWindow = subprocess.SW_HIDE
            
            cmd = [
                'ffmpeg', '-i', video_path,
                '-vn', '-acodec', 'pcm_s16le',
                '-ar', '44100', '-ac', '2',
                '-y', self.temp_audio_file
            ]
            
            subprocess.run(
                cmd, 
                capture_output=True, 
                text=True,
                startupinfo=startupinfo,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
            )
            
            if os.path.exists(self.temp_audio_file) and os.path.getsize(self.temp_audio_file) > 0:
                return True
            return False
            
        except Exception as e:
            return False
    
    def seleccionar_video(self):
        archivo = filedialog.askopenfilename(
            title="Selecciona un video",
            filetypes=[("Videos", "*.mp4 *.avi *.mov *.mkv *.mpg *.mpeg"), ("Todos", "*.*")]
        )
        
        if archivo:
            self.video_path = archivo
            nombre = os.path.basename(archivo)
            if len(nombre) > 40:
                nombre = nombre[:37] + "..."
            self.video_label.config(text=f"📹 {nombre}", fg='black')
            
            try:
                self.video_clip = VideoFileClip(archivo)
                self.duracion = self.video_clip.duration
                
                self.info_label.config(
                    text=f"Duración: {self.format_time(self.duracion)} | {self.video_clip.size[0]}x{self.video_clip.size[1]}")
                
                # Extraer audio
                self.status_label.config(text="⏳ Cargando audio...", fg='#FF9800')
                self.root.update()
                
                if self.extraer_audio_silencioso(archivo):
                    self.audio_loaded = True
                    pygame.mixer.music.load(self.temp_audio_file)
                    pygame.mixer.music.set_volume(0.7)
                
                self.range_selector.set_range(0, self.duracion)
                self.range_selector.set_values(0, self.duracion)
                
                self.mostrar_frame(0)
                
                # Limpiar fragmentos
                self.fragmentos_guardar = []
                self.fragmentos_eliminar = []
                self.actualizar_lista()
                
                # Habilitar botones
                for btn in [self.btn_play, self.btn_pause, self.btn_stop,
                           self.btn_mark_start, self.btn_mark_end,
                           self.btn_go_start, self.btn_go_end,
                           self.btn_add, self.btn_delete, self.btn_clear,
                           self.btn_process]:
                    btn.config(state='normal')
                
                self.on_range_changed(0, self.duracion)
                self.status_label.config(text="✅ Video cargado", fg='#4CAF50')
                
            except Exception as e:
                self.status_label.config(text="❌ Error al cargar", fg='#F44336')
                messagebox.showerror("Error", f"No se pudo cargar el video")
    
    def cambiar_volumen(self, valor):
        if self.audio_loaded:
            volumen = int(valor) / 100
            pygame.mixer.music.set_volume(volumen)
    
    def mostrar_frame(self, tiempo):
        try:
            if self.video_clip:
                frame = self.video_clip.get_frame(tiempo)
                img = Image.fromarray(frame)
                img.thumbnail((500, 280), Image.Resampling.LANCZOS)
                
                new_img = Image.new('RGB', (500, 280), 'black')
                x = (500 - img.width) // 2
                y = (280 - img.height) // 2
                new_img.paste(img, (x, y))
                
                imgtk = ImageTk.PhotoImage(image=new_img)
                self.video_visor.config(image=imgtk)
                self.video_visor.image = imgtk
                
                self.current_time = tiempo
                self.time_label.config(
                    text=f"{self.format_time(tiempo)} / {self.format_time(self.duracion)}")
                self.range_selector.set_current(tiempo)
                
        except Exception:
            pass
    
    def toggle_playback(self):
        if not self.playing:
            self.playing = True
            self.btn_play.config(state='disabled')
            self.btn_pause.config(state='normal')
            
            if self.audio_loaded:
                try:
                    pygame.mixer.music.play(start=self.current_time)
                except:
                    pass
            
            self.reproducir()
    
    def pause_video(self):
        self.playing = False
        self.btn_play.config(state='normal')
        self.btn_pause.config(state='disabled')
        
        if self.audio_loaded:
            try:
                pygame.mixer.music.pause()
            except:
                pass
        
        if self.update_job:
            self.root.after_cancel(self.update_job)
    
    def stop_video(self):
        self.pause_video()
        self.current_time = 0
        self.mostrar_frame(0)
        
        if self.audio_loaded:
            try:
                pygame.mixer.music.stop()
            except:
                pass
    
    def reproducir(self):
        if self.playing and self.current_time < self.duracion:
            self.mostrar_frame(self.current_time)
            self.current_time = min(self.current_time + 1/25, self.duracion)
            self.update_job = self.root.after(40, self.reproducir)
        else:
            self.stop_video()
    
    def marcar_inicio(self):
        inicio, fin = self.range_selector.get_values()
        # Asegurar que inicio <= fin
        if self.current_time > fin:
            self.range_selector.set_values(fin, self.current_time)
        else:
            self.range_selector.set_values(self.current_time, fin)
    
    def marcar_fin(self):
        inicio, fin = self.range_selector.get_values()
        # Asegurar que inicio <= fin
        if self.current_time < inicio:
            self.range_selector.set_values(self.current_time, inicio)
        else:
            self.range_selector.set_values(inicio, self.current_time)
    
    def ir_a_inicio(self):
        self.pause_video()
        inicio, _ = self.range_selector.get_values()
        self.current_time = inicio
        self.mostrar_frame(inicio)
    
    def ir_a_fin(self):
        self.pause_video()
        _, fin = self.range_selector.get_values()
        self.current_time = fin
        self.mostrar_frame(fin)
    
    def on_range_changed(self, inicio, fin):
        """Callback cuando cambia el rango - siempre recibe inicio <= fin"""
        self.start_label.config(text=f"Inicio: {self.format_time(inicio)}")
        self.end_label.config(text=f"Fin: {self.format_time(fin)}")
        self.duration_label.config(text=f"Duración: {self.format_time(fin - inicio)}")
    
    def aniadir_fragmento(self):
        """Añade el fragmento actual a la lista según el modo"""
        inicio, fin = self.range_selector.get_values()
        # inicio y fin ya vienen ordenados (inicio <= fin)
        
        if inicio < fin:
            if self.modo == "guardar":
                self.fragmentos_guardar.append({'inicio': inicio, 'fin': fin})
            else:
                self.fragmentos_eliminar.append({'inicio': inicio, 'fin': fin})
            
            self.actualizar_lista()
            self.status_label.config(text="✅ Fragmento añadido", fg='#4CAF50')
        else:
            # Esto no debería ocurrir nunca ahora, pero lo dejamos por si acaso
            messagebox.showwarning("Advertencia", "El fragmento debe tener duración positiva")
    
    def eliminar_de_lista(self):
        """Elimina el fragmento seleccionado de la lista"""
        seleccion = self.lista.curselection()
        if seleccion:
            idx = seleccion[0]
            if self.modo == "guardar" and idx < len(self.fragmentos_guardar):
                del self.fragmentos_guardar[idx]
            elif self.modo == "eliminar" and idx < len(self.fragmentos_eliminar):
                del self.fragmentos_eliminar[idx]
            
            self.actualizar_lista()
            self.status_label.config(text="✅ Fragmento quitado", fg='#9C27B0')
    
    def limpiar_lista(self):
        """Limpia todos los fragmentos del modo actual"""
        if self.modo == "guardar":
            self.fragmentos_guardar = []
        else:
            self.fragmentos_eliminar = []
        
        self.actualizar_lista()
        self.status_label.config(text="✅ Lista limpiada", fg='#9C27B0')
    
    def iniciar_procesamiento(self):
        if self.modo == "guardar" and not self.fragmentos_guardar:
            messagebox.showwarning("Advertencia", "No hay fragmentos para guardar")
            return
        elif self.modo == "eliminar" and not self.fragmentos_eliminar:
            messagebox.showwarning("Advertencia", "No hay fragmentos para eliminar")
            return
        
        threading.Thread(target=self.procesar_video, daemon=True).start()
    
    def procesar_video(self):
        """Procesa el video según el modo"""
        try:
            self.btn_process.config(state='disabled', bg='#cccccc')
            self.progress.start()
            
            if self.modo == "guardar":
                if self.guardar_separado.get():
                    self.guardar_fragmentos_separados()
                else:
                    self.guardar_fragmentos_concatenados()
            else:
                self.eliminar_fragmentos()
            
        except Exception as e:
            self.status_label.config(text="❌ Error", fg='#F44336')
            messagebox.showerror("Error", str(e))
        
        finally:
            self.progress.stop()
            if self.video_path:
                self.btn_process.config(state='normal', bg='#4CAF50' if self.modo == "guardar" else '#F44336')
    
    def guardar_fragmentos_concatenados(self):
        """Guarda los fragmentos concatenados en un solo video (con o sin transiciones)"""
        archivo = filedialog.asksaveasfilename(
            title="Guardar video concatenado",
            defaultextension=".mp4",
            filetypes=[("MP4", "*.mp4")],
            initialfile="video_concatenado.mp4"
        )
        
        if archivo:
            self.status_label.config(text="💾 Concatenando fragmentos...", fg='#FF9800')
            
            clip = VideoFileClip(self.video_path)
            
            # Ordenar fragmentos por inicio
            fragmentos = sorted(self.fragmentos_guardar, key=lambda x: x['inicio'])
            clips = []
            
            for frag in fragmentos:
                if frag['fin'] - frag['inicio'] > 0.1:
                    clips.append(clip.subclipped(frag['inicio'], frag['fin']))
            
            if clips:
                # Aplicar transiciones si está activado
                if self.usar_transiciones.get() and len(clips) > 1:
                    duracion = self.duracion_transicion.get()
                    clips_con_transiciones = []
                    
                    for i, c in enumerate(clips):
                        if i > 0:
                            c = CrossFadeIn(duracion).apply(c)
                        if i < len(clips) - 1:
                            c = CrossFadeOut(duracion).apply(c)
                        clips_con_transiciones.append(c)
                    
                    video_final = concatenate_videoclips(clips_con_transiciones, method="compose")
                else:
                    video_final = concatenate_videoclips(clips)
                
                video_final.write_videofile(archivo, logger=None, codec='libx264', audio_codec='aac')
                
                for c in clips:
                    c.close()
                video_final.close()
                
                duracion_total = sum(frag['fin'] - frag['inicio'] for frag in fragmentos)
                self.status_label.config(text="✅ Video guardado", fg='#4CAF50')
                
                mensaje = f"Video concatenado guardado correctamente\n\n"
                mensaje += f"Fragmentos: {len(fragmentos)}\n"
                mensaje += f"Duración total: {self.format_time(duracion_total)}"
                
                if self.usar_transiciones.get() and len(fragmentos) > 1:
                    mensaje += f"\nTransiciones: {self.duracion_transicion.get()}s"
                
                messagebox.showinfo("Éxito", mensaje)
            else:
                messagebox.showwarning("Advertencia", "No hay fragmentos válidos para guardar")
            
            clip.close()
    
    def guardar_fragmentos_separados(self):
        """Guarda cada fragmento en un archivo independiente"""
        if not self.fragmentos_guardar:
            return
        
        # Pedir carpeta destino
        carpeta = filedialog.askdirectory(title="Selecciona carpeta para guardar los fragmentos")
        
        if carpeta:
            self.status_label.config(text="💾 Guardando fragmentos separados...", fg='#FF9800')
            
            clip = VideoFileClip(self.video_path)
            fragmentos_guardados = 0
            
            for i, frag in enumerate(self.fragmentos_guardar, 1):
                if frag['fin'] - frag['inicio'] > 0.1:
                    nombre = f"fragmento_{i:02d}_{self.format_time(frag['inicio']).replace(':', '-')}.mp4"
                    ruta = os.path.join(carpeta, nombre)
                    
                    fragmento = clip.subclipped(frag['inicio'], frag['fin'])
                    fragmento.write_videofile(ruta, logger=None, codec='libx264', audio_codec='aac')
                    fragmento.close()
                    
                    fragmentos_guardados += 1
            
            clip.close()
            
            self.status_label.config(text="✅ Fragmentos guardados", fg='#4CAF50')
            messagebox.showinfo("Éxito", 
                f"Se guardaron {fragmentos_guardados} fragmentos en:\n{carpeta}")
    
    def eliminar_fragmentos(self):
        """Elimina los fragmentos seleccionados del video"""
        archivo = filedialog.asksaveasfilename(
            title="Guardar video sin los fragmentos eliminados",
            defaultextension=".mp4",
            filetypes=[("MP4", "*.mp4")],
            initialfile="video_sin_fragmentos.mp4"
        )
        
        if archivo:
            self.status_label.config(text="💾 Eliminando fragmentos...", fg='#FF9800')
            
            clip = VideoFileClip(self.video_path)
            
            # Ordenar fragmentos a eliminar
            eliminar = sorted(self.fragmentos_eliminar, key=lambda x: x['inicio'])
            
            # Crear lista de fragmentos a CONSERVAR
            conservar = []
            inicio_actual = 0
            
            for frag in eliminar:
                if frag['inicio'] > inicio_actual:
                    conservar.append((inicio_actual, frag['inicio']))
                inicio_actual = max(inicio_actual, frag['fin'])
            
            if inicio_actual < self.duracion:
                conservar.append((inicio_actual, self.duracion))
            
            # Crear clips a conservar
            clips = []
            for inicio, fin in conservar:
                if fin - inicio > 0.1:
                    clips.append(clip.subclipped(inicio, fin))
            
            if clips:
                if len(clips) > 1:
                    video_final = concatenate_videoclips(clips)
                else:
                    video_final = clips[0]
                
                video_final.write_videofile(archivo, logger=None, codec='libx264', audio_codec='aac')
                
                for c in clips:
                    c.close()
                video_final.close()
                
                duracion_final = sum(fin-inicio for inicio, fin in conservar)
                self.status_label.config(text="✅ Video guardado sin fragmentos", fg='#4CAF50')
                messagebox.showinfo("Éxito", 
                    f"Video guardado correctamente\n\n"
                    f"Fragmentos eliminados: {len(eliminar)}\n"
                    f"Duración original: {self.format_time(self.duracion)}\n"
                    f"Duración final: {self.format_time(duracion_final)}")
            else:
                messagebox.showwarning("Advertencia", "No queda nada del video después de eliminar")
            
            clip.close()
    
    def __del__(self):
        try:
            if self.temp_audio_file and os.path.exists(self.temp_audio_file):
                os.unlink(self.temp_audio_file)
            pygame.mixer.quit()
        except:
            pass


if __name__ == "__main__":
    root = tk.Tk()
    app = CortadorVideo(root)
    root.mainloop()