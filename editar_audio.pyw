# -*- coding: utf-8 -*-
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import os

try:
    from moviepy import AudioFileClip, concatenate_audioclips
    MOVIEPY_OK = True
except ImportError:
    MOVIEPY_OK = False

class EditorAudio:
    def __init__(self, root):
        self.root = root
        self.root.title("🎵 Editor de Audio - Cortar y Unir")
        
        # Configurar colores claros
        self.colors = {
            'bg': '#f0f0f0',
            'fg': '#333333',
            'accent': '#4CAF50',
            'accent_light': '#81C784',
            'button_text': '#ffffff',
            'frame_bg': '#ffffff',
            'info_bg': '#e3f2fd',
            'success': '#4CAF50',
            'error': '#f44336',
            'warning': '#ff9800',
            'audio_accent': '#FF6B6B'  # Color para audio (rojizo)
        }
        
        self.root.configure(bg=self.colors['bg'])
        self.configurar_ventana()
        
        # Variables
        self.archivos_audio = []  # Lista para múltiples audios (unión)
        self.audio_actual = None   # Audio actual para cortar
        self.duracion_actual = 0
        self.procesando = False
        self.modo = "cortar"  # "cortar" o "unir"
        
        if not MOVIEPY_OK:
            messagebox.showerror("Error", 
                               "MoviePy no está instalado.\nEjecuta: pip install moviepy")
            root.destroy()
            return
        
        self.crear_interfaz()
    
    def configurar_ventana(self):
        """Configura la ventana centrada y a 20px del borde superior"""
        ancho = 700
        alto = 650
        margen_superior = 20
        
        ancho_pantalla = self.root.winfo_screenwidth()
        x = (ancho_pantalla - ancho) // 2
        y = margen_superior
        
        self.root.geometry(f'{ancho}x{alto}+{x}+{y}')
        self.root.minsize(650, 600)
        self.root.resizable(True, True)
    
    def crear_interfaz(self):
        # Estilo para ttk
        style = ttk.Style()
        style.theme_use('clam')
        style.configure('TProgressbar', background=self.colors['audio_accent'])
        
        # Frame principal
        main_frame = tk.Frame(self.root, bg=self.colors['bg'], padx=20, pady=15)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # === TÍTULO ===
        titulo_frame = tk.Frame(main_frame, bg=self.colors['bg'])
        titulo_frame.pack(fill=tk.X, pady=(0, 15))
        
        tk.Label(titulo_frame, 
                text="🎵 EDITOR DE AUDIO", 
                font=('Arial', 22, 'bold'),
                fg=self.colors['audio_accent'],
                bg=self.colors['bg']).pack()
        
        tk.Label(titulo_frame,
                text="Corta y une archivos de audio (MP3, WAV, M4A, OGG)",
                font=('Arial', 10),
                fg='#666666',
                bg=self.colors['bg']).pack()
        
        # === SELECTOR DE MODO ===
        modo_frame = tk.Frame(main_frame, bg='white', relief='solid', bd=1, padx=10, pady=10)
        modo_frame.pack(fill=tk.X, pady=5)
        
        tk.Label(modo_frame, text="🎚️ MODO DE TRABAJO", 
                font=('Arial', 11, 'bold'),
                bg='white', fg=self.colors['audio_accent']).pack(anchor='w')
        
        modo_selector = tk.Frame(modo_frame, bg='white')
        modo_selector.pack(pady=5)
        
        self.modo_var = tk.StringVar(value="cortar")
        
        rb_cortar = tk.Radiobutton(modo_selector,
                                  text="✂️ CORTAR AUDIO",
                                  variable=self.modo_var,
                                  value="cortar",
                                  bg='white',
                                  fg=self.colors['fg'],
                                  selectcolor='white',
                                  font=('Arial', 10, 'bold'),
                                  command=self.cambiar_modo)
        rb_cortar.pack(side=tk.LEFT, padx=10)
        
        rb_unir = tk.Radiobutton(modo_selector,
                                text="🔗 UNIR AUDIOS",
                                variable=self.modo_var,
                                value="unir",
                                bg='white',
                                fg=self.colors['fg'],
                                selectcolor='white',
                                font=('Arial', 10, 'bold'),
                                command=self.cambiar_modo)
        rb_unir.pack(side=tk.LEFT, padx=10)
        
        # === FRAME PARA MODO CORTAR ===
        self.cortar_frame = tk.Frame(main_frame, bg=self.colors['bg'])
        self.cortar_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        self.crear_panel_cortar()
        
        # === FRAME PARA MODO UNIR ===
        self.unir_frame = tk.Frame(main_frame, bg=self.colors['bg'])
        # No se packea inicialmente
        self.crear_panel_unir()
        
        # === BOTÓN DE PROCESAR ===
        boton_frame = tk.Frame(main_frame, bg=self.colors['bg'])
        boton_frame.pack(pady=15)
        
        self.procesar_btn = tk.Button(boton_frame,
                                      text=self.get_texto_boton(),
                                      bg=self.colors['audio_accent'],
                                      fg='white',
                                      font=('Arial', 14, 'bold'),
                                      padx=40,
                                      pady=12,
                                      relief='raised',
                                      bd=2,
                                      cursor='hand2',
                                      state='disabled',
                                      command=self.iniciar_procesar)
        self.procesar_btn.pack()
        
        # Efecto hover
        self.procesar_btn.bind('<Enter>', self.on_enter_boton)
        self.procesar_btn.bind('<Leave>', self.on_leave_boton)
        
        # === BARRA DE PROGRESO ===
        progreso_frame = tk.Frame(main_frame, bg=self.colors['bg'])
        progreso_frame.pack(fill=tk.X, pady=5)
        
        self.progreso = ttk.Progressbar(progreso_frame, mode='indeterminate', length=400)
        self.progreso.pack()
        
        self.estado_label = tk.Label(progreso_frame,
                                    text="✅ Listo",
                                    fg=self.colors['success'],
                                    bg=self.colors['bg'],
                                    font=('Arial', 10))
        self.estado_label.pack(pady=5)
    
    def crear_panel_cortar(self):
        """Crea el panel para cortar audio"""
        # === SELECCIÓN DE AUDIO ===
        audio_frame = tk.Frame(self.cortar_frame, bg='white', relief='solid', bd=1, padx=10, pady=10)
        audio_frame.pack(fill=tk.X, pady=5)
        
        tk.Label(audio_frame, text="🎵 ARCHIVO DE AUDIO", 
                font=('Arial', 11, 'bold'),
                bg='white', fg=self.colors['audio_accent']).pack(anchor='w')
        
        btn_frame = tk.Frame(audio_frame, bg='white')
        btn_frame.pack(fill=tk.X, pady=5)
        
        self.cortar_audio_label = tk.Label(btn_frame,
                                         text="📁 Ningún audio seleccionado",
                                         fg='#999999',
                                         bg='white',
                                         font=('Arial', 9),
                                         anchor='w')
        self.cortar_audio_label.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        tk.Button(btn_frame,
                text="Seleccionar Audio",
                bg=self.colors['audio_accent'],
                fg='white',
                font=('Arial', 9, 'bold'),
                padx=10,
                pady=2,
                relief='flat',
                cursor='hand2',
                command=self.seleccionar_audio_cortar).pack(side=tk.RIGHT)
        
        self.cortar_info_label = tk.Label(audio_frame,
                                        text="",
                                        bg='white',
                                        fg='#1976D2',
                                        font=('Arial', 9),
                                        anchor='w')
        self.cortar_info_label.pack(anchor='w', pady=2)
        
        # === TIEMPOS DE CORTE ===
        tiempos_frame = tk.Frame(self.cortar_frame, bg='white', relief='solid', bd=1, padx=10, pady=10)
        tiempos_frame.pack(fill=tk.X, pady=5)
        
        tk.Label(tiempos_frame, text="✂️ TIEMPOS DE CORTE", 
                font=('Arial', 11, 'bold'),
                bg='white', fg=self.colors['audio_accent']).pack(anchor='w')
        
        # Entradas de tiempo
        entry_frame = tk.Frame(tiempos_frame, bg='white')
        entry_frame.pack(pady=10)
        
        tk.Label(entry_frame, text="Inicio (seg):", bg='white').grid(row=0, column=0, padx=5, pady=2)
        self.inicio_entry = tk.Entry(entry_frame, width=10, font=('Arial', 11))
        self.inicio_entry.grid(row=0, column=1, padx=5, pady=2)
        self.inicio_entry.insert(0, "0")
        
        tk.Label(entry_frame, text="Fin (seg):", bg='white').grid(row=1, column=0, padx=5, pady=2)
        self.fin_entry = tk.Entry(entry_frame, width=10, font=('Arial', 11))
        self.fin_entry.grid(row=1, column=1, padx=5, pady=2)
        self.fin_entry.insert(0, "10")
        
        # Barra deslizadora
        self.cortar_scale = tk.Scale(tiempos_frame,
                                    from_=0,
                                    to=100,
                                    orient=tk.HORIZONTAL,
                                    length=400,
                                    showvalue=False,
                                    bg='white',
                                    troughcolor='#e0e0e0')
        self.cortar_scale.pack(pady=5)
        
        # Labels para mostrar tiempo actual
        tiempo_actual_frame = tk.Frame(tiempos_frame, bg='white')
        tiempo_actual_frame.pack(fill=tk.X)
        
        self.inicio_label = tk.Label(tiempo_actual_frame, text="Inicio: 0s", bg='white', font=('Arial', 8))
        self.inicio_label.pack(side=tk.LEFT)
        
        self.fin_label = tk.Label(tiempo_actual_frame, text="Fin: 10s", bg='white', font=('Arial', 8))
        self.fin_label.pack(side=tk.RIGHT)
        
        # Bindings para la barra
        self.cortar_scale.bind('<B1-Motion>', self.actualizar_tiempos_cortar)
        self.inicio_entry.bind('<KeyRelease>', self.actualizar_scale_cortar)
        self.fin_entry.bind('<KeyRelease>', self.actualizar_scale_cortar)
        
        # Ayuda
        tk.Label(tiempos_frame,
                text="💡 Puedes escribir los segundos o usar la barra",
                bg='white',
                fg='#666666',
                font=('Arial', 8)).pack(pady=2)
    
    def crear_panel_unir(self):
        """Crea el panel para unir audios"""
        # === LISTA DE AUDIOS ===
        lista_frame = tk.Frame(self.unir_frame, bg='white', relief='solid', bd=1, padx=10, pady=10)
        lista_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        tk.Label(lista_frame, text="🔗 AUDIOS A UNIR", 
                font=('Arial', 11, 'bold'),
                bg='white', fg=self.colors['audio_accent']).pack(anchor='w')
        
        # Botones
        btn_frame = tk.Frame(lista_frame, bg='white')
        btn_frame.pack(fill=tk.X, pady=5)
        
        tk.Button(btn_frame,
                 text="➕ Agregar Audio",
                 bg=self.colors['audio_accent'],
                 fg='white',
                 font=('Arial', 9, 'bold'),
                 padx=10,
                 pady=2,
                 relief='flat',
                 cursor='hand2',
                 command=self.agregar_audio_unir).pack(side=tk.LEFT, padx=2)
        
        tk.Button(btn_frame,
                 text="⬆ Subir",
                 bg='#2196F3',
                 fg='white',
                 font=('Arial', 9),
                 padx=8,
                 pady=2,
                 relief='flat',
                 cursor='hand2',
                 command=self.subir_audio).pack(side=tk.LEFT, padx=2)
        
        tk.Button(btn_frame,
                 text="⬇ Bajar",
                 bg='#2196F3',
                 fg='white',
                 font=('Arial', 9),
                 padx=8,
                 pady=2,
                 relief='flat',
                 cursor='hand2',
                 command=self.bajar_audio).pack(side=tk.LEFT, padx=2)
        
        tk.Button(btn_frame,
                 text="❌ Quitar",
                 bg='#f44336',
                 fg='white',
                 font=('Arial', 9),
                 padx=8,
                 pady=2,
                 relief='flat',
                 cursor='hand2',
                 command=self.quitar_audio).pack(side=tk.LEFT, padx=2)
        
        # Lista de audios
        list_container = tk.Frame(lista_frame, bg='#ffffff', height=150)
        list_container.pack(fill=tk.BOTH, expand=True, pady=5)
        list_container.pack_propagate(False)
        
        scrollbar = tk.Scrollbar(list_container)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.lista_audios = tk.Listbox(list_container,
                                      bg='#ffffff',
                                      fg=self.colors['fg'],
                                      selectbackground=self.colors['info_bg'],
                                      yscrollcommand=scrollbar.set,
                                      font=('Arial', 9))
        self.lista_audios.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        scrollbar.config(command=self.lista_audios.yview)
        
        # Información
        self.unir_info_label = tk.Label(lista_frame,
                                       text="📊 0 audios seleccionados",
                                       bg='white',
                                       fg='#666666',
                                       font=('Arial', 9))
        self.unir_info_label.pack(anchor='w', pady=2)
        
        self.duracion_total_label = tk.Label(lista_frame,
                                            text="",
                                            bg='white',
                                            fg='#1976D2',
                                            font=('Arial', 9))
        self.duracion_total_label.pack(anchor='w')
    
    def cambiar_modo(self):
        """Cambia entre modo cortar y unir"""
        modo = self.modo_var.get()
        
        if modo == "cortar":
            self.unir_frame.pack_forget()
            self.cortar_frame.pack(fill=tk.BOTH, expand=True, pady=5)
            self.modo = "cortar"
        else:
            self.cortar_frame.pack_forget()
            self.unir_frame.pack(fill=tk.BOTH, expand=True, pady=5)
            self.modo = "unir"
        
        self.procesar_btn.config(text=self.get_texto_boton())
        self.actualizar_estado_boton()
    
    def get_texto_boton(self):
        """Retorna el texto del botón según el modo"""
        if self.modo == "cortar":
            return "✂️ CORTAR AUDIO"
        else:
            return "🔗 UNIR AUDIOS"
    
    def on_enter_boton(self, event):
        if self.procesar_btn['state'] == 'normal':
            event.widget.config(bg=self.colors['audio_accent'])
    
    def on_leave_boton(self, event):
        if self.procesar_btn['state'] == 'normal':
            event.widget.config(bg=self.colors['audio_accent'])
    
    def seleccionar_audio_cortar(self):
        archivo = filedialog.askopenfilename(
            title="Selecciona un archivo de audio",
            filetypes=[
                ("Audio", "*.mp3 *.wav *.m4a *.ogg *.flac"),
                ("MP3", "*.mp3"),
                ("WAV", "*.wav"),
                ("M4A", "*.m4a"),
                ("OGG", "*.ogg"),
                ("Todos", "*.*")
            ]
        )
        
        if archivo:
            self.audio_actual = archivo
            nombre = os.path.basename(archivo)
            self.cortar_audio_label.config(text=f"🎵 {nombre}", fg=self.colors['fg'])
            
            try:
                clip = AudioFileClip(archivo)
                duracion = clip.duration
                self.duracion_actual = duracion
                clip.close()
                
                minutos = int(duracion // 60)
                segundos = int(duracion % 60)
                
                info = f"📊 Duración: {minutos}:{segundos:02d} ({duracion:.1f} segundos)"
                self.cortar_info_label.config(text=info, fg='green')
                
                # Actualizar límites
                self.fin_entry.delete(0, tk.END)
                self.fin_entry.insert(0, f"{duracion:.1f}")
                
                self.cortar_scale.configure(to=int(duracion))
                
                self.actualizar_estado_boton()
                
            except Exception as e:
                self.cortar_info_label.config(text=f"❌ Error al leer audio", fg='red')
    
    def agregar_audio_unir(self):
        archivos = filedialog.askopenfilenames(
            title="Selecciona audios para unir",
            filetypes=[
                ("Audio", "*.mp3 *.wav *.m4a *.ogg *.flac"),
                ("MP3", "*.mp3"),
                ("WAV", "*.wav"),
                ("Todos", "*.*")
            ]
        )
        
        for archivo in archivos:
            if archivo not in self.archivos_audio:
                self.archivos_audio.append(archivo)
                nombre = os.path.basename(archivo)
                self.lista_audios.insert(tk.END, f"🎵 {nombre}")
        
        self.actualizar_info_unir()
    
    def quitar_audio(self):
        seleccion = self.lista_audios.curselection()
        if seleccion:
            idx = seleccion[0]
            self.lista_audios.delete(idx)
            del self.archivos_audio[idx]
            self.actualizar_info_unir()
    
    def subir_audio(self):
        seleccion = self.lista_audios.curselection()
        if seleccion and seleccion[0] > 0:
            idx = seleccion[0]
            self.archivos_audio[idx], self.archivos_audio[idx-1] = self.archivos_audio[idx-1], self.archivos_audio[idx]
            self.actualizar_listbox_unir()
            self.lista_audios.selection_set(idx-1)
    
    def bajar_audio(self):
        seleccion = self.lista_audios.curselection()
        if seleccion and seleccion[0] < len(self.archivos_audio)-1:
            idx = seleccion[0]
            self.archivos_audio[idx], self.archivos_audio[idx+1] = self.archivos_audio[idx+1], self.archivos_audio[idx]
            self.actualizar_listbox_unir()
            self.lista_audios.selection_set(idx+1)
    
    def actualizar_listbox_unir(self):
        self.lista_audios.delete(0, tk.END)
        for audio in self.archivos_audio:
            nombre = os.path.basename(audio)
            self.lista_audios.insert(tk.END, f"🎵 {nombre}")
    
    def actualizar_info_unir(self):
        count = len(self.archivos_audio)
        self.unir_info_label.config(text=f"📊 {count} audios seleccionados")
        
        if count >= 2:
            # Calcular duración total aproximada
            def calcular_duracion():
                try:
                    duracion_total = 0
                    for audio in self.archivos_audio:
                        try:
                            clip = AudioFileClip(audio)
                            duracion_total += clip.duration
                            clip.close()
                        except:
                            pass
                    
                    minutos = int(duracion_total // 60)
                    segundos = int(duracion_total % 60)
                    self.duracion_total_label.config(
                        text=f"⏱️ Duración total: {minutos}:{segundos:02d} ({duracion_total:.1f} s)")
                except:
                    self.duracion_total_label.config(text="")
            
            threading.Thread(target=calcular_duracion, daemon=True).start()
        else:
            self.duracion_total_label.config(text="")
        
        self.actualizar_estado_boton()
    
    def actualizar_estado_boton(self):
        """Habilita o deshabilita el botón según el modo"""
        if self.modo == "cortar" and self.audio_actual:
            self.procesar_btn.config(state='normal', bg=self.colors['audio_accent'])
        elif self.modo == "unir" and len(self.archivos_audio) >= 2:
            self.procesar_btn.config(state='normal', bg=self.colors['audio_accent'])
        else:
            self.procesar_btn.config(state='disabled', bg='#cccccc')
    
    def actualizar_tiempos_cortar(self, event=None):
        """Actualiza los campos de texto desde la barra"""
        if hasattr(self, 'duracion_actual') and self.duracion_actual > 0:
            valor = self.cortar_scale.get()
            
            # Determinar qué campo actualizar
            if self.ultimo_scale_move == 'inicio':
                self.inicio_entry.delete(0, tk.END)
                self.inicio_entry.insert(0, f"{valor:.1f}")
            else:
                self.fin_entry.delete(0, tk.END)
                self.fin_entry.insert(0, f"{valor:.1f}")
            
            self.actualizar_labels_tiempo()
    
    def actualizar_scale_cortar(self, event=None):
        """Actualiza la barra desde los campos de texto"""
        try:
            inicio = float(self.inicio_entry.get())
            fin = float(self.fin_entry.get())
            
            if 0 <= inicio <= self.duracion_actual and 0 <= fin <= self.duracion_actual:
                # No movemos la barra automáticamente para evitar conflictos
                pass
            
            self.actualizar_labels_tiempo()
        except:
            pass
    
    def actualizar_labels_tiempo(self):
        try:
            inicio = float(self.inicio_entry.get())
            fin = float(self.fin_entry.get())
            self.inicio_label.config(text=f"Inicio: {inicio:.1f}s")
            self.fin_label.config(text=f"Fin: {fin:.1f}s")
        except:
            pass
    
    def iniciar_procesar(self):
        if self.procesando:
            return
        
        hilo = threading.Thread(target=self.procesar)
        hilo.daemon = True
        hilo.start()
    
    def procesar(self):
        try:
            self.procesando = True
            self.procesar_btn.config(state='disabled', bg='#cccccc')
            self.progreso.start()
            
            if self.modo == "cortar":
                self.cortar_audio()
            else:
                self.unir_audios()
            
        except Exception as e:
            self.estado_label.config(text=f"❌ Error", fg='red')
            messagebox.showerror("Error", f"Error al procesar:\n{str(e)}")
        
        finally:
            self.progreso.stop()
            self.procesando = False
            self.actualizar_estado_boton()
    
    def cortar_audio(self):
        try:
            self.estado_label.config(text="⏳ Cargando audio...", fg=self.colors['warning'])
            
            inicio = float(self.inicio_entry.get())
            fin = float(self.fin_entry.get())
            
            if inicio >= fin:
                raise ValueError("El inicio debe ser menor que el fin")
            
            if inicio < 0 or fin > self.duracion_actual:
                raise ValueError(f"Tiempos fuera de rango (0-{self.duracion_actual:.1f}s)")
            
            # Cargar audio
            clip = AudioFileClip(self.audio_actual)
            
            # Cortar
            self.estado_label.config(text="⏳ Cortando audio...", fg=self.colors['warning'])
            fragmento = clip.subclipped(inicio, fin)
            
            # Guardar
            nombre_base = os.path.splitext(os.path.basename(self.audio_actual))[0]
            archivo_salida = filedialog.asksaveasfilename(
                title="Guardar audio cortado",
                defaultextension=".mp3",
                filetypes=[("MP3", "*.mp3"), ("WAV", "*.wav"), ("Todos", "*.*")],
                initialfile=f"{nombre_base}_cortado.mp3"
            )
            
            if archivo_salida:
                self.estado_label.config(text="⏳ Guardando...", fg=self.colors['warning'])
                
                # Determinar codec según extensión
                if archivo_salida.endswith('.mp3'):
                    codec = 'libmp3lame'
                    bitrate = '192k'
                elif archivo_salida.endswith('.wav'):
                    codec = 'pcm_s16le'
                    bitrate = None
                else:
                    codec = 'libmp3lame'
                    bitrate = '192k'
                
                params = {'codec': codec, 'logger': None}
                if bitrate:
                    params['bitrate'] = bitrate
                
                fragmento.write_audiofile(archivo_salida, **params)
                
                duracion_cortada = fin - inicio
                minutos = int(duracion_cortada // 60)
                segundos = int(duracion_cortada % 60)
                
                self.estado_label.config(text="✅ Audio cortado!", fg='green')
                messagebox.showinfo("Éxito", 
                                  f"Audio cortado guardado:\n{os.path.basename(archivo_salida)}\n\n"
                                  f"Duración: {minutos}:{segundos:02d}")
            
            clip.close()
            fragmento.close()
            
        except ValueError as e:
            self.estado_label.config(text="❌ Error", fg='red')
            messagebox.showerror("Error", str(e))
    
    def unir_audios(self):
        try:
            self.estado_label.config(text="⏳ Cargando audios...", fg=self.colors['warning'])
            
            clips = []
            for i, audio_path in enumerate(self.archivos_audio):
                self.estado_label.config(text=f"⏳ Cargando audio {i+1} de {len(self.archivos_audio)}...", 
                                       fg=self.colors['warning'])
                clip = AudioFileClip(audio_path)
                clips.append(clip)
            
            self.estado_label.config(text="�ls Uniendo audios...", fg=self.colors['warning'])
            audio_final = concatenate_audioclips(clips)
            
            # Guardar
            archivo_salida = filedialog.asksaveasfilename(
                title="Guardar audio unido",
                defaultextension=".mp3",
                filetypes=[("MP3", "*.mp3"), ("WAV", "*.wav"), ("Todos", "*.*")],
                initialfile="audios_unidos.mp3"
            )
            
            if archivo_salida:
                self.estado_label.config(text="⏳ Guardando...", fg=self.colors['warning'])
                
                if archivo_salida.endswith('.mp3'):
                    codec = 'libmp3lame'
                    bitrate = '192k'
                elif archivo_salida.endswith('.wav'):
                    codec = 'pcm_s16le'
                    bitrate = None
                else:
                    codec = 'libmp3lame'
                    bitrate = '192k'
                
                params = {'codec': codec, 'logger': None}
                if bitrate:
                    params['bitrate'] = bitrate
                
                audio_final.write_audiofile(archivo_salida, **params)
                
                duracion_total = audio_final.duration
                minutos = int(duracion_total // 60)
                segundos = int(duracion_total % 60)
                
                self.estado_label.config(text="✅ Audios unidos!", fg='green')
                messagebox.showinfo("Éxito", 
                                  f"Audios unidos guardados:\n{os.path.basename(archivo_salida)}\n\n"
                                  f"Duración total: {minutos}:{segundos:02d}")
            
            # Limpiar
            audio_final.close()
            for clip in clips:
                clip.close()
            
        except Exception as e:
            self.estado_label.config(text="❌ Error", fg='red')
            messagebox.showerror("Error", f"Error al unir:\n{str(e)}")

if __name__ == "__main__":
    try:
        root = tk.Tk()
        app = EditorAudio(root)
        root.mainloop()
    except Exception as e:
        messagebox.showerror("Error fatal", f"Error al iniciar:\n{str(e)}")