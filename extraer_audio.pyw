# -*- coding: utf-8 -*-
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import os

try:
    from moviepy import VideoFileClip
    MOVIEPY_OK = True
except ImportError:
    MOVIEPY_OK = False

class ExtraerAudio:
    def __init__(self, root):
        self.root = root
        self.root.title("🎵 Extraer Audio a MP3")
        
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
        self.video_path = None
        self.procesando = False
        
        if not MOVIEPY_OK:
            messagebox.showerror("Error", 
                               "MoviePy no está instalado.\nEjecuta: pip install moviepy")
            root.destroy()
            return
        
        self.crear_interfaz()
    
    def configurar_ventana(self):
        """Configura la ventana centrada y a 20px del borde superior"""
        ancho = 500
        alto = 450
        margen_superior = 20
        
        ancho_pantalla = self.root.winfo_screenwidth()
        x = (ancho_pantalla - ancho) // 2
        y = margen_superior
        
        self.root.geometry(f'{ancho}x{alto}+{x}+{y}')
        self.root.minsize(450, 400)
        self.root.resizable(False, False)
    
    def crear_interfaz(self):
        # Frame principal
        main_frame = tk.Frame(self.root, bg=self.colors['bg'], padx=20, pady=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # === TÍTULO ===
        tk.Label(main_frame, 
                text="🎵 EXTRAER AUDIO", 
                font=('Arial', 24, 'bold'),
                fg=self.colors['accent'],
                bg=self.colors['bg']).pack(pady=(0, 20))
        
        # === MARCO PARA VIDEO ===
        video_frame = tk.Frame(main_frame, bg='white', relief='solid', bd=1, padx=10, pady=10)
        video_frame.pack(fill=tk.X, pady=5)
        
        tk.Label(video_frame, text="📁 VIDEO", 
                font=('Arial', 11, 'bold'),
                bg='white', fg=self.colors['accent']).pack(anchor='w')
        
        # Botón y label
        btn_frame = tk.Frame(video_frame, bg='white')
        btn_frame.pack(fill=tk.X, pady=5)
        
        self.video_label = tk.Label(btn_frame,
                                   text="Ningún video seleccionado",
                                   fg='#999999',
                                   bg='white',
                                   font=('Arial', 9),
                                   anchor='w')
        self.video_label.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        self.btn_video = tk.Button(btn_frame,
                                  text="Seleccionar",
                                  bg=self.colors['accent'],
                                  fg='white',
                                  font=('Arial', 9, 'bold'),
                                  padx=10,
                                  pady=2,
                                  relief='flat',
                                  cursor='hand2',
                                  command=self.seleccionar_video)
        self.btn_video.pack(side=tk.RIGHT)
        
        # Información del video
        self.info_label = tk.Label(video_frame,
                                  text="",
                                  bg='white',
                                  fg='#1976D2',
                                  font=('Arial', 9),
                                  anchor='w')
        self.info_label.pack(anchor='w', pady=2)
        
        # === MARCO PARA CALIDAD ===
        calidad_frame = tk.Frame(main_frame, bg='white', relief='solid', bd=1, padx=10, pady=10)
        calidad_frame.pack(fill=tk.X, pady=10)
        
        tk.Label(calidad_frame, text="🎚️ CALIDAD MP3", 
                font=('Arial', 11, 'bold'),
                bg='white', fg=self.colors['accent']).pack(anchor='w')
        
        self.calidad_var = tk.StringVar(value="192")
        
        calidades = [
            ("Alta (320 kbps)", "320"),
            ("Buena (192 kbps)", "192"),
            ("Normal (128 kbps)", "128")
        ]
        
        for texto, valor in calidades:
            rb = tk.Radiobutton(calidad_frame,
                              text=texto,
                              variable=self.calidad_var,
                              value=valor,
                              bg='white',
                              fg=self.colors['fg'],
                              selectcolor='white',
                              font=('Arial', 9))
            rb.pack(anchor='w', padx=10, pady=2)
        
        # === BOTÓN DE EXTRACCIÓN (GRANDE Y VISIBLE) ===
        self.boton_extraer = tk.Button(main_frame,
                                      text="🎵 EXTRAER AUDIO AHORA",
                                      bg=self.colors['accent'],
                                      fg='white',
                                      font=('Arial', 16, 'bold'),
                                      padx=30,
                                      pady=15,
                                      relief='raised',
                                      bd=2,
                                      cursor='hand2',
                                      state='disabled',
                                      command=self.iniciar_extraccion)
        self.boton_extraer.pack(pady=20, fill=tk.X)
        
        # Efecto hover
        self.boton_extraer.bind('<Enter>', self.on_enter_boton)
        self.boton_extraer.bind('<Leave>', self.on_leave_boton)
        
        # === BARRA DE PROGRESO ===
        self.progreso = ttk.Progressbar(main_frame, mode='indeterminate', length=400)
        self.progreso.pack(pady=5)
        
        self.estado_label = tk.Label(main_frame,
                                    text="✅ Listo",
                                    fg=self.colors['success'],
                                    bg=self.colors['bg'],
                                    font=('Arial', 10, 'bold'))
        self.estado_label.pack()
    
    def on_enter_boton(self, event):
        if self.boton_extraer['state'] == 'normal':
            event.widget.config(bg=self.colors['accent_light'])
    
    def on_leave_boton(self, event):
        if self.boton_extraer['state'] == 'normal':
            event.widget.config(bg=self.colors['accent'])
    
    def seleccionar_video(self):
        archivo = filedialog.askopenfilename(
            title="Selecciona un video",
            filetypes=[
                ("Videos", "*.mp4 *.avi *.mov *.mkv *.webm"),
                ("MP4", "*.mp4"),
                ("AVI", "*.avi"),
                ("MOV", "*.mov"),
                ("Todos", "*.*")
            ]
        )
        
        if archivo:
            self.video_path = archivo
            nombre = os.path.basename(archivo)
            self.video_label.config(text=f"🎬 {nombre}", fg=self.colors['fg'])
            
            try:
                # Obtener información básica
                clip = VideoFileClip(archivo)
                duracion = clip.duration
                tiene_audio = clip.audio is not None
                
                minutos = int(duracion // 60)
                segundos = int(duracion % 60)
                
                if tiene_audio:
                    info_text = f"✅ Duración: {minutos}:{segundos:02d} - Con audio"
                    self.info_label.config(text=info_text, fg='green')
                    self.boton_extraer.config(state='normal', bg=self.colors['accent'])
                else:
                    info_text = f"⚠️ Duración: {minutos}:{segundos:02d} - SIN AUDIO"
                    self.info_label.config(text=info_text, fg='red')
                    self.boton_extraer.config(state='disabled', bg='#cccccc')
                    messagebox.showwarning("Sin audio", "Este video no tiene pista de audio")
                
                clip.close()
                
            except Exception as e:
                self.info_label.config(text=f"❌ Error al leer video", fg='red')
                print(f"Error: {e}")
    
    def iniciar_extraccion(self):
        if not self.video_path:
            return
        
        hilo = threading.Thread(target=self.extraer_audio)
        hilo.daemon = True
        hilo.start()
    
    def extraer_audio(self):
        try:
            self.procesando = True
            self.boton_extraer.config(state='disabled', bg='#cccccc')
            self.progreso.start()
            self.estado_label.config(text="⏳ Cargando video...", fg=self.colors['warning'])
            
            # Cargar video
            clip = VideoFileClip(self.video_path)
            
            if not clip.audio:
                raise Exception("El video no tiene audio")
            
            # Preguntar dónde guardar
            nombre_sugerido = os.path.splitext(os.path.basename(self.video_path))[0] + ".mp3"
            archivo_salida = filedialog.asksaveasfilename(
                title="Guardar audio MP3",
                defaultextension=".mp3",
                filetypes=[("MP3", "*.mp3")],
                initialfile=nombre_sugerido
            )
            
            if not archivo_salida:
                self.estado_label.config(text="⏸️ Cancelado", fg=self.colors['warning'])
                return
            
            # Extraer audio
            self.estado_label.config(text="⏳ Extrayendo audio...", fg=self.colors['warning'])
            calidad = self.calidad_var.get()
            
            clip.audio.write_audiofile(
                archivo_salida, 
                codec='libmp3lame', 
                bitrate=f'{calidad}k',
                logger=None
            )
            
            # Confirmación
            if os.path.exists(archivo_salida):
                tamaño = os.path.getsize(archivo_salida) / (1024 * 1024)  # MB
                self.estado_label.config(text=f"✅ Audio guardado ({tamaño:.1f} MB)", fg='green')
                
                # Mostrar mensaje de éxito
                self.root.after(100, lambda: messagebox.showinfo(
                    "✅ Éxito", 
                    f"Audio extraído correctamente:\n\n{os.path.basename(archivo_salida)}\n\n"
                    f"📁 Carpeta: {os.path.dirname(archivo_salida)}"
                ))
            
            clip.close()
            
        except Exception as e:
            self.estado_label.config(text=f"❌ Error", fg='red')
            self.root.after(100, lambda: messagebox.showerror("Error", f"Error al extraer audio:\n{str(e)}"))
        
        finally:
            self.progreso.stop()
            self.procesando = False
            if self.video_path:
                # Verificar si el video tiene audio antes de habilitar
                try:
                    clip_test = VideoFileClip(self.video_path)
                    tiene_audio = clip_test.audio is not None
                    clip_test.close()
                    if tiene_audio:
                        self.boton_extraer.config(state='normal', bg=self.colors['accent'])
                except:
                    pass

if __name__ == "__main__":
    try:
        root = tk.Tk()
        app = ExtraerAudio(root)
        root.mainloop()
    except Exception as e:
        messagebox.showerror("Error fatal", f"Error al iniciar:\n{str(e)}")