# -*- coding: utf-8 -*-
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import os

try:
    from moviepy import ImageClip, AudioFileClip, concatenate_videoclips
    from moviepy import CompositeVideoClip
    MOVIEPY_OK = True
except ImportError:
    MOVIEPY_OK = False

class FotosAVideo:
    def __init__(self, root):
        self.root = root
        self.root.title("🖼️ Fotos a Video")
        
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
            'warning': '#ff9800'
        }
        
        self.root.configure(bg=self.colors['bg'])
        self.configurar_ventana()
        
        # Variables
        self.imagenes = []
        self.audio_path = None
        self.procesando = False
        
        if not MOVIEPY_OK:
            messagebox.showerror("Error", 
                               "MoviePy no está instalado.\nEjecuta: pip install moviepy")
            root.destroy()
            return
        
        self.crear_interfaz()
    
    def configurar_ventana(self):
        """Configura la ventana centrada y a 20px del borde superior"""
        ancho = 700
        alto = 600
        margen_superior = 20
        
        ancho_pantalla = self.root.winfo_screenwidth()
        x = (ancho_pantalla - ancho) // 2
        y = margen_superior
        
        self.root.geometry(f'{ancho}x{alto}+{x}+{y}')
        self.root.minsize(650, 550)
        self.root.resizable(True, True)
    
    def crear_interfaz(self):
        # Estilo para ttk
        style = ttk.Style()
        style.theme_use('clam')
        style.configure('TProgressbar', background=self.colors['accent'])
        
        # Frame principal
        main_frame = tk.Frame(self.root, bg=self.colors['bg'], padx=25, pady=15)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # === TÍTULO ===
        titulo_frame = tk.Frame(main_frame, bg=self.colors['bg'])
        titulo_frame.pack(fill=tk.X, pady=(0, 15))
        
        tk.Label(titulo_frame, 
                text="🖼️ FOTOS A VIDEO", 
                font=('Arial', 20, 'bold'),
                fg=self.colors['accent'],
                bg=self.colors['bg']).pack()
        
        tk.Label(titulo_frame,
                text="Convierte tus fotos en un video con música",
                font=('Arial', 10),
                fg='#666666',
                bg=self.colors['bg']).pack()
        
        # === SELECCIÓN DE IMÁGENES ===
        imagenes_frame = self.crear_frame_con_borde(main_frame, "1. SELECCIONA LAS FOTOS")
        imagenes_frame.pack(fill=tk.BOTH, pady=10, expand=True)
        
        # Botones para imágenes
        btn_imagenes_frame = tk.Frame(imagenes_frame.contenido, bg=self.colors['frame_bg'])
        btn_imagenes_frame.pack(fill=tk.X, pady=5)
        
        tk.Button(btn_imagenes_frame,
                 text="➕ Agregar Fotos",
                 bg=self.colors['accent'],
                 fg=self.colors['button_text'],
                 font=('Arial', 10),
                 padx=15,
                 pady=5,
                 relief='flat',
                 cursor='hand2',
                 command=self.agregar_imagenes).pack(side=tk.LEFT, padx=5)
        
        tk.Button(btn_imagenes_frame,
                 text="❌ Quitar Seleccionada",
                 bg='#f44336',
                 fg='white',
                 font=('Arial', 10),
                 padx=15,
                 pady=5,
                 relief='flat',
                 cursor='hand2',
                 command=self.quitar_imagen).pack(side=tk.LEFT, padx=5)
        
        tk.Button(btn_imagenes_frame,
                 text="🔄 Limpiar Todas",
                 bg='#ff9800',
                 fg='white',
                 font=('Arial', 10),
                 padx=15,
                 pady=5,
                 relief='flat',
                 cursor='hand2',
                 command=self.limpiar_imagenes).pack(side=tk.LEFT, padx=5)
        
        # Lista de imágenes
        list_frame = tk.Frame(imagenes_frame.contenido, bg='#ffffff', height=150)
        list_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        list_frame.pack_propagate(False)
        
        scrollbar = tk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.lista_imagenes = tk.Listbox(list_frame,
                                        bg='#ffffff',
                                        fg=self.colors['fg'],
                                        selectbackground=self.colors['info_bg'],
                                        selectforeground='#1976D2',
                                        yscrollcommand=scrollbar.set,
                                        font=('Arial', 10))
        self.lista_imagenes.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        scrollbar.config(command=self.lista_imagenes.yview)
        
        # Contador de imágenes
        self.contador_label = tk.Label(imagenes_frame.contenido,
                                      text="📸 0 imágenes seleccionadas",
                                      bg=self.colors['frame_bg'],
                                      fg='#666666',
                                      font=('Arial', 9))
        self.contador_label.pack(anchor='w', pady=5)
        
        # === SELECCIÓN DE AUDIO ===
        audio_frame = self.crear_frame_con_borde(main_frame, "2. AÑADE MÚSICA (OPCIONAL)")
        audio_frame.pack(fill=tk.X, pady=10)
        
        # Botón y label de audio
        audio_btn_frame = tk.Frame(audio_frame.contenido, bg=self.colors['frame_bg'])
        audio_btn_frame.pack(fill=tk.X, pady=5)
        
        self.audio_label = tk.Label(audio_btn_frame,
                                   text="🎵 Ningún audio seleccionado",
                                   fg='#999999',
                                   bg=self.colors['frame_bg'],
                                   font=('Arial', 10),
                                   anchor='w')
        self.audio_label.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        tk.Button(audio_btn_frame,
                 text="Seleccionar Audio",
                 bg=self.colors['accent'],
                 fg='white',
                 font=('Arial', 10),
                 padx=15,
                 pady=5,
                 relief='flat',
                 cursor='hand2',
                 command=self.seleccionar_audio).pack(side=tk.RIGHT)
        
        # Info del audio
        self.audio_info = tk.Label(audio_frame.contenido,
                                  text="Formatos soportados: MP3, WAV, M4A",
                                  bg=self.colors['frame_bg'],
                                  fg='#666666',
                                  font=('Arial', 9))
        self.audio_info.pack(anchor='w', pady=5)
        
        # === CONFIGURACIÓN ===
        config_frame = self.crear_frame_con_borde(main_frame, "3. CONFIGURACIÓN")
        config_frame.pack(fill=tk.X, pady=10)
        
        # Duración por imagen
        duracion_frame = tk.Frame(config_frame.contenido, bg=self.colors['frame_bg'])
        duracion_frame.pack(fill=tk.X, pady=10)
        
        tk.Label(duracion_frame,
                text="Duración por foto (segundos):",
                bg=self.colors['frame_bg'],
                fg=self.colors['fg'],
                font=('Arial', 10)).pack(side=tk.LEFT, padx=5)
        
        self.duracion_var = tk.StringVar(value="3")
        self.duracion_entry = tk.Entry(duracion_frame,
                                      textvariable=self.duracion_var,
                                      width=8,
                                      font=('Arial', 11),
                                      bg='#ffffff',
                                      relief='solid',
                                      bd=1)
        self.duracion_entry.pack(side=tk.LEFT, padx=5)
        
        tk.Label(duracion_frame,
                text="segundos",
                bg=self.colors['frame_bg'],
                fg='#666666',
                font=('Arial', 9)).pack(side=tk.LEFT)
        
        # Resolución
        resolucion_frame = tk.Frame(config_frame.contenido, bg=self.colors['frame_bg'])
        resolucion_frame.pack(fill=tk.X, pady=10)
        
        tk.Label(resolucion_frame,
                text="Resolución del video:",
                bg=self.colors['frame_bg'],
                fg=self.colors['fg'],
                font=('Arial', 10)).pack(side=tk.LEFT, padx=5)
        
        self.resolucion_var = tk.StringVar(value="1920x1080")
        resoluciones = ["1920x1080 (Full HD)", "1280x720 (HD)", "854x480 (SD)", "640x360 (Pequeño)"]
        self.resolucion_combo = ttk.Combobox(resolucion_frame,
                                            values=resoluciones,
                                            width=20,
                                            state='readonly')
        self.resolucion_combo.pack(side=tk.LEFT, padx=5)
        self.resolucion_combo.set(resoluciones[0])
        
        # FPS
        fps_frame = tk.Frame(config_frame.contenido, bg=self.colors['frame_bg'])
        fps_frame.pack(fill=tk.X, pady=10)
        
        tk.Label(fps_frame,
                text="FPS (fotogramas por segundo):",
                bg=self.colors['frame_bg'],
                fg=self.colors['fg'],
                font=('Arial', 10)).pack(side=tk.LEFT, padx=5)
        
        self.fps_var = tk.StringVar(value="24")
        tk.Spinbox(fps_frame,
                  from_=1,
                  to=60,
                  textvariable=self.fps_var,
                  width=8,
                  font=('Arial', 11),
                  bg='#ffffff',
                  relief='solid',
                  bd=1).pack(side=tk.LEFT, padx=5)
        
        # === BOTÓN DE PROCESAR ===
        boton_frame = tk.Frame(main_frame, bg=self.colors['bg'])
        boton_frame.pack(pady=15)
        
        self.procesar_btn = tk.Button(boton_frame,
                                      text="🎬 CREAR VIDEO",
                                      bg=self.colors['accent'],
                                      fg='white',
                                      font=('Arial', 14, 'bold'),
                                      padx=40,
                                      pady=12,
                                      relief='flat',
                                      cursor='hand2',
                                      command=self.iniciar_procesar)
        self.procesar_btn.pack()
        
        # Efecto hover
        self.procesar_btn.bind('<Enter>', lambda e: e.widget.config(bg=self.colors['accent_light']))
        self.procesar_btn.bind('<Leave>', lambda e: e.widget.config(bg=self.colors['accent']))
        
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
    
    def crear_frame_con_borde(self, parent, titulo):
        """Crea un frame con borde y título"""
        frame = tk.Frame(parent, bg=self.colors['bg'])
        
        # Título
        tk.Label(frame, 
                text=titulo,
                bg=self.colors['bg'],
                fg=self.colors['accent'],
                font=('Arial', 11, 'bold')).pack(anchor='w')
        
        tk.Frame(frame, bg='#cccccc', height=1).pack(fill=tk.X, pady=(2, 5))
        
        # Contenido (fondo blanco)
        contenido = tk.Frame(frame, bg='#ffffff', relief='solid', bd=1)
        contenido.pack(fill=tk.X, padx=1, pady=1)
        
        frame.contenido = contenido
        return frame
    
    def agregar_imagenes(self):
        archivos = filedialog.askopenfilenames(
            title="Seleccionar imágenes",
            filetypes=[
                ("Imágenes", "*.jpg *.jpeg *.png *.bmp *.gif"),
                ("JPG", "*.jpg"),
                ("JPEG", "*.jpeg"),
                ("PNG", "*.png"),
                ("Todos", "*.*")
            ]
        )
        
        for archivo in archivos:
            if archivo not in self.imagenes:
                self.imagenes.append(archivo)
                nombre = os.path.basename(archivo)
                self.lista_imagenes.insert(tk.END, f"📷 {nombre}")
        
        self.contador_label.config(text=f"📸 {len(self.imagenes)} imágenes seleccionadas")
    
    def quitar_imagen(self):
        seleccion = self.lista_imagenes.curselection()
        if seleccion:
            idx = seleccion[0]
            self.lista_imagenes.delete(idx)
            del self.imagenes[idx]
            self.contador_label.config(text=f"📸 {len(self.imagenes)} imágenes seleccionadas")
    
    def limpiar_imagenes(self):
        self.lista_imagenes.delete(0, tk.END)
        self.imagenes = []
        self.contador_label.config(text="📸 0 imágenes seleccionadas")
    
    def seleccionar_audio(self):
        archivo = filedialog.askopenfilename(
            title="Seleccionar audio",
            filetypes=[
                ("Audio", "*.mp3 *.wav *.m4a *.ogg"),
                ("MP3", "*.mp3"),
                ("WAV", "*.wav"),
                ("M4A", "*.m4a"),
                ("Todos", "*.*")
            ]
        )
        
        if archivo:
            self.audio_path = archivo
            nombre = os.path.basename(archivo)
            self.audio_label.config(text=f"🎵 {nombre}", fg=self.colors['fg'])
            
            # Mostrar duración del audio
            try:
                audio_clip = AudioFileClip(archivo)
                duracion = audio_clip.duration
                audio_clip.close()
                self.audio_info.config(text=f"Duración: {duracion:.1f} segundos")
            except:
                self.audio_info.config(text="No se pudo leer el audio")
    
    def iniciar_procesar(self):
        if len(self.imagenes) == 0:
            messagebox.showerror("Error", "Selecciona al menos una imagen")
            return
        
        try:
            duracion = float(self.duracion_var.get())
            if duracion <= 0:
                raise ValueError
        except:
            messagebox.showerror("Error", "La duración debe ser un número positivo")
            return
        
        if self.procesando:
            return
        
        hilo = threading.Thread(target=self.procesar_video)
        hilo.daemon = True
        hilo.start()
    
    def procesar_video(self):
        try:
            self.procesando = True
            self.procesar_btn.config(state='disabled', bg='#cccccc')
            self.progreso.start()
            self.estado_label.config(text="⏳ Procesando imágenes...", fg=self.colors['warning'])
            
            # Obtener configuración
            duracion = float(self.duracion_var.get())
            
            # Obtener resolución
            resolucion_text = self.resolucion_combo.get()
            if "1920x1080" in resolucion_text:
                tamaño = (1920, 1080)
            elif "1280x720" in resolucion_text:
                tamaño = (1280, 720)
            elif "854x480" in resolucion_text:
                tamaño = (854, 480)
            else:
                tamaño = (640, 360)
            
            fps = int(self.fps_var.get())
            
            # Crear clips de imagen
            clips = []
            total = len(self.imagenes)
            
            for i, img_path in enumerate(self.imagenes):
                # Actualizar estado
                self.estado_label.config(text=f"⏳ Procesando imagen {i+1} de {total}...", 
                                       fg=self.colors['warning'])
                
                # Crear clip con tamaño fijo
                clip = (ImageClip(img_path)
                       .with_duration(duracion)
                       .resized(new_size=tamaño))
                clips.append(clip)
            
            # Concatenar todos los clips
            self.estado_label.config(text="⏳ Uniendo imágenes...", fg=self.colors['warning'])
            video = concatenate_videoclips(clips, method="compose")
            
            # Añadir audio si existe
            if self.audio_path:
                self.estado_label.config(text="⏳ Añadiendo audio...", fg=self.colors['warning'])
                audio = AudioFileClip(self.audio_path)
                
                # Si el audio es más corto que el video, se repite
                if audio.duration < video.duration:
                    # Repetir audio para que coincida
                    n_repeticiones = int(video.duration / audio.duration) + 1
                    audios = [audio] * n_repeticiones
                    audio_final = concatenate_videoclips(audios)
                    audio_final = audio_final.subclipped(0, video.duration)
                else:
                    audio_final = audio.subclipped(0, video.duration)
                
                video = video.with_audio(audio_final)
            
            # Guardar video
            archivo_salida = filedialog.asksaveasfilename(
                title="Guardar video",
                defaultextension=".mp4",
                filetypes=[("MP4", "*.mp4")],
                initialfile="video_fotos.mp4"
            )
            
            if archivo_salida:
                self.estado_label.config(text="⏳ Guardando video...", fg=self.colors['warning'])
                video.write_videofile(archivo_salida, fps=fps, logger=None)
                self.estado_label.config(text="✅ Video creado!", fg=self.colors['success'])
                messagebox.showinfo("Éxito", f"Video guardado:\n{os.path.basename(archivo_salida)}")
            else:
                self.estado_label.config(text="⏸️ Cancelado", fg=self.colors['warning'])
            
            # Limpiar
            video.close()
            if self.audio_path and 'audio' in locals():
                audio.close()
                if 'audio_final' in locals():
                    audio_final.close()
            
        except Exception as e:
            self.estado_label.config(text="❌ Error", fg=self.colors['error'])
            messagebox.showerror("Error", f"Error al crear video:\n{str(e)}")
        
        finally:
            self.progreso.stop()
            self.procesando = False
            self.procesar_btn.config(state='normal', bg=self.colors['accent'])

if __name__ == "__main__":
    try:
        root = tk.Tk()
        app = FotosAVideo(root)
        root.mainloop()
    except Exception as e:
        messagebox.showerror("Error fatal", f"Error al iniciar:\n{str(e)}")