# -*- coding: utf-8 -*-
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import os

try:
    from moviepy import VideoFileClip, concatenate_videoclips
    MOVIEPY_OK = True
except ImportError:
    MOVIEPY_OK = False

class ConcatenarVideos:
    def __init__(self, root):
        self.root = root
        self.root.title("🔗 Concatenar Videos")
        
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
        self.videos = []
        self.procesando = False
        
        if not MOVIEPY_OK:
            messagebox.showerror("Error", 
                               "MoviePy no está instalado.\nEjecuta: pip install moviepy")
            root.destroy()
            return
        
        self.crear_interfaz()
    
    def configurar_ventana(self):
        """Configura la ventana centrada y a 20px del borde superior"""
        ancho = 750
        alto = 650
        margen_superior = 20
        
        ancho_pantalla = self.root.winfo_screenwidth()
        x = (ancho_pantalla - ancho) // 2
        y = margen_superior
        
        self.root.geometry(f'{ancho}x{alto}+{x}+{y}')
        self.root.minsize(700, 600)
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
                text="🔗 CONCATENAR VIDEOS", 
                font=('Arial', 20, 'bold'),
                fg=self.colors['accent'],
                bg=self.colors['bg']).pack()
        
        tk.Label(titulo_frame,
                text="Une varios videos en uno solo, en el orden que elijas",
                font=('Arial', 10),
                fg='#666666',
                bg=self.colors['bg']).pack()
        
        # === LISTA DE VIDEOS ===
        lista_frame = self.crear_frame_con_borde(main_frame, "1. VIDEOS A CONCATENAR")
        lista_frame.pack(fill=tk.BOTH, pady=10, expand=True)
        
        # Botones para videos
        btn_frame = tk.Frame(lista_frame.contenido, bg=self.colors['frame_bg'])
        btn_frame.pack(fill=tk.X, pady=5)
        
        # Botones en fila
        tk.Button(btn_frame,
                 text="➕ Agregar Videos",
                 bg=self.colors['accent'],
                 fg='white',
                 font=('Arial', 10),
                 padx=15,
                 pady=5,
                 relief='flat',
                 cursor='hand2',
                 command=self.agregar_videos).pack(side=tk.LEFT, padx=2)
        
        tk.Button(btn_frame,
                 text="⬆ Subir",
                 bg='#2196F3',
                 fg='white',
                 font=('Arial', 10),
                 padx=10,
                 pady=5,
                 relief='flat',
                 cursor='hand2',
                 command=self.subir_video).pack(side=tk.LEFT, padx=2)
        
        tk.Button(btn_frame,
                 text="⬇ Bajar",
                 bg='#2196F3',
                 fg='white',
                 font=('Arial', 10),
                 padx=10,
                 pady=5,
                 relief='flat',
                 cursor='hand2',
                 command=self.bajar_video).pack(side=tk.LEFT, padx=2)
        
        tk.Button(btn_frame,
                 text="❌ Quitar",
                 bg='#f44336',
                 fg='white',
                 font=('Arial', 10),
                 padx=15,
                 pady=5,
                 relief='flat',
                 cursor='hand2',
                 command=self.quitar_video).pack(side=tk.LEFT, padx=2)
        
        tk.Button(btn_frame,
                 text="🔄 Limpiar Todo",
                 bg='#ff9800',
                 fg='white',
                 font=('Arial', 10),
                 padx=15,
                 pady=5,
                 relief='flat',
                 cursor='hand2',
                 command=self.limpiar_videos).pack(side=tk.LEFT, padx=2)
        
        # Lista de videos con scroll
        list_container = tk.Frame(lista_frame.contenido, bg='#ffffff', height=200)
        list_container.pack(fill=tk.BOTH, expand=True, pady=5)
        list_container.pack_propagate(False)
        
        scrollbar_y = tk.Scrollbar(list_container)
        scrollbar_y.pack(side=tk.RIGHT, fill=tk.Y)
        
        scrollbar_x = tk.Scrollbar(list_container, orient=tk.HORIZONTAL)
        scrollbar_x.pack(side=tk.BOTTOM, fill=tk.X)
        
        self.lista_videos = tk.Listbox(list_container,
                                      bg='#ffffff',
                                      fg=self.colors['fg'],
                                      selectbackground=self.colors['info_bg'],
                                      selectforeground='#1976D2',
                                      yscrollcommand=scrollbar_y.set,
                                      xscrollcommand=scrollbar_x.set,
                                      font=('Arial', 10),
                                      selectmode=tk.SINGLE)
        self.lista_videos.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        scrollbar_y.config(command=self.lista_videos.yview)
        scrollbar_x.config(command=self.lista_videos.xview)
        
        # Información de videos
        self.info_frame = tk.Frame(lista_frame.contenido, bg=self.colors['frame_bg'])
        self.info_frame.pack(fill=tk.X, pady=5)
        
        self.contador_label = tk.Label(self.info_frame,
                                      text="📹 0 videos seleccionados",
                                      bg=self.colors['frame_bg'],
                                      fg='#666666',
                                      font=('Arial', 9))
        self.contador_label.pack(side=tk.LEFT)
        
        self.duracion_total_label = tk.Label(self.info_frame,
                                            text="",
                                            bg=self.colors['frame_bg'],
                                            fg='#666666',
                                            font=('Arial', 9))
        self.duracion_total_label.pack(side=tk.RIGHT)
        
        # === CONFIGURACIÓN ===
        config_frame = self.crear_frame_con_borde(main_frame, "2. CONFIGURACIÓN")
        config_frame.pack(fill=tk.X, pady=10)
        
        # Método de concatenación
        metodo_frame = tk.Frame(config_frame.contenido, bg=self.colors['frame_bg'])
        metodo_frame.pack(fill=tk.X, pady=10)
        
        tk.Label(metodo_frame,
                text="Método de unión:",
                bg=self.colors['frame_bg'],
                fg=self.colors['fg'],
                font=('Arial', 10)).pack(side=tk.LEFT, padx=5)
        
        self.metodo_var = tk.StringVar(value="compose")
        metodo_compose = tk.Radiobutton(metodo_frame,
                                       text="Compose (recomendado)",
                                       variable=self.metodo_var,
                                       value="compose",
                                       bg=self.colors['frame_bg'],
                                       fg=self.colors['fg'],
                                       selectcolor=self.colors['frame_bg'],
                                       font=('Arial', 9))
        metodo_compose.pack(side=tk.LEFT, padx=10)
        
        metodo_chain = tk.Radiobutton(metodo_frame,
                                     text="Chain (más rápido)",
                                     variable=self.metodo_var,
                                     value="chain",
                                     bg=self.colors['frame_bg'],
                                     fg=self.colors['fg'],
                                     selectcolor=self.colors['frame_bg'],
                                     font=('Arial', 9))
        metodo_chain.pack(side=tk.LEFT, padx=10)
        
        # Tooltip informativo
        tk.Label(config_frame.contenido,
                text="💡 Compose: mejor calidad, más lento | Chain: más rápido, requiere mismo formato",
                bg=self.colors['frame_bg'],
                fg='#666666',
                font=('Arial', 8)).pack(anchor='w', padx=5, pady=(0, 5))
        
        # === BOTÓN DE PROCESAR ===
        boton_frame = tk.Frame(main_frame, bg=self.colors['bg'])
        boton_frame.pack(pady=15)
        
        self.procesar_btn = tk.Button(boton_frame,
                                      text="🔗 CONCATENAR VIDEOS",
                                      bg=self.colors['accent'],
                                      fg='white',
                                      font=('Arial', 14, 'bold'),
                                      padx=40,
                                      pady=12,
                                      relief='flat',
                                      cursor='hand2',
                                      state='disabled',
                                      command=self.iniciar_concatenar)
        self.procesar_btn.pack()
        
        # Efecto hover
        self.procesar_btn.bind('<Enter>', lambda e: e.widget.config(bg=self.colors['accent_light']) if e.widget['state'] == 'normal' else None)
        self.procesar_btn.bind('<Leave>', lambda e: e.widget.config(bg=self.colors['accent']) if e.widget['state'] == 'normal' else None)
        
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
        contenido = tk.Frame(frame, bg='#ffffff', relief='solid', bd=1, padx=10, pady=10)
        contenido.pack(fill=tk.X, padx=1, pady=1)
        
        frame.contenido = contenido
        return frame
    
    def agregar_videos(self):
        archivos = filedialog.askopenfilenames(
            title="Seleccionar videos para concatenar",
            filetypes=[
                ("Videos", "*.mp4 *.avi *.mov *.mkv *.webm *.m4v"),
                ("MP4", "*.mp4"),
                ("AVI", "*.avi"),
                ("MOV", "*.mov"),
                ("MKV", "*.mkv"),
                ("Todos", "*.*")
            ]
        )
        
        for archivo in archivos:
            if archivo not in self.videos:
                self.videos.append(archivo)
                nombre = os.path.basename(archivo)
                self.lista_videos.insert(tk.END, f"🎬 {nombre}")
        
        self.actualizar_info()
    
    def quitar_video(self):
        seleccion = self.lista_videos.curselection()
        if seleccion:
            idx = seleccion[0]
            self.lista_videos.delete(idx)
            del self.videos[idx]
            self.actualizar_info()
    
    def subir_video(self):
        seleccion = self.lista_videos.curselection()
        if seleccion and seleccion[0] > 0:
            idx = seleccion[0]
            # Intercambiar en la lista
            self.videos[idx], self.videos[idx-1] = self.videos[idx-1], self.videos[idx]
            # Actualizar listbox
            self.actualizar_listbox()
            # Mantener selección
            self.lista_videos.selection_set(idx-1)
    
    def bajar_video(self):
        seleccion = self.lista_videos.curselection()
        if seleccion and seleccion[0] < len(self.videos)-1:
            idx = seleccion[0]
            # Intercambiar en la lista
            self.videos[idx], self.videos[idx+1] = self.videos[idx+1], self.videos[idx]
            # Actualizar listbox
            self.actualizar_listbox()
            # Mantener selección
            self.lista_videos.selection_set(idx+1)
    
    def limpiar_videos(self):
        self.lista_videos.delete(0, tk.END)
        self.videos = []
        self.actualizar_info()
    
    def actualizar_listbox(self):
        self.lista_videos.delete(0, tk.END)
        for video in self.videos:
            nombre = os.path.basename(video)
            self.lista_videos.insert(tk.END, f"🎬 {nombre}")
    
    def actualizar_info(self):
        """Actualiza contadores y habilita botón"""
        count = len(self.videos)
        self.contador_label.config(text=f"📹 {count} videos seleccionados")
        
        if count >= 2:
            self.procesar_btn.config(state='normal', bg=self.colors['accent'])
            
            # Calcular duración total aproximada
            self.estado_label.config(text="⏳ Calculando duración...", fg=self.colors['warning'])
            
            def calcular_duracion():
                try:
                    duracion_total = 0
                    for video in self.videos:
                        try:
                            clip = VideoFileClip(video)
                            duracion_total += clip.duration
                            clip.close()
                        except:
                            pass
                    
                    minutos = int(duracion_total // 60)
                    segundos = int(duracion_total % 60)
                    self.duracion_total_label.config(text=f"⏱️ Duración total: {minutos}:{segundos:02d}")
                except:
                    self.duracion_total_label.config(text="")
                finally:
                    self.estado_label.config(text="✅ Listo", fg=self.colors['success'])
            
            threading.Thread(target=calcular_duracion, daemon=True).start()
        else:
            self.procesar_btn.config(state='disabled', bg='#cccccc')
            self.duracion_total_label.config(text="")
    
    def iniciar_concatenar(self):
        if len(self.videos) < 2:
            messagebox.showerror("Error", "Selecciona al menos 2 videos para concatenar")
            return
        
        if self.procesando:
            return
        
        hilo = threading.Thread(target=self.concatenar)
        hilo.daemon = True
        hilo.start()
    
    def concatenar(self):
        try:
            self.procesando = True
            self.procesar_btn.config(state='disabled', bg='#cccccc')
            self.progreso.start()
            self.estado_label.config(text="⏳ Cargando videos...", fg=self.colors['warning'])
            
            metodo = self.metodo_var.get()
            clips = []
            
            # Cargar todos los videos
            for i, video_path in enumerate(self.videos):
                self.estado_label.config(text=f"⏳ Cargando video {i+1} de {len(self.videos)}...", 
                                       fg=self.colors['warning'])
                try:
                    clip = VideoFileClip(video_path)
                    clips.append(clip)
                except Exception as e:
                    raise Exception(f"Error cargando {os.path.basename(video_path)}:\n{str(e)}")
            
            # Concatenar
            self.estado_label.config(text="⏳ Concatenando videos...", fg=self.colors['warning'])
            video_final = concatenate_videoclips(clips, method=metodo)
            
            # Guardar
            archivo_salida = filedialog.asksaveasfilename(
                title="Guardar video concatenado",
                defaultextension=".mp4",
                filetypes=[("MP4", "*.mp4")],
                initialfile="video_concatenado.mp4"
            )
            
            if archivo_salida:
                self.estado_label.config(text="⏳ Guardando video...", fg=self.colors['warning'])
                video_final.write_videofile(archivo_salida, logger=None)
                
                # Mostrar información del video final
                minutos = int(video_final.duration // 60)
                segundos = int(video_final.duration % 60)
                
                self.estado_label.config(text=f"✅ Video guardado ({minutos}:{segundos:02d})", 
                                       fg=self.colors['success'])
                messagebox.showinfo("Éxito", 
                                  f"Video concatenado guardado:\n{os.path.basename(archivo_salida)}\n\n"
                                  f"Duración total: {minutos}:{segundos:02d}")
            else:
                self.estado_label.config(text="⏸️ Cancelado", fg=self.colors['warning'])
            
            # Limpiar
            video_final.close()
            for clip in clips:
                clip.close()
            
        except Exception as e:
            self.estado_label.config(text="❌ Error", fg=self.colors['error'])
            messagebox.showerror("Error", f"Error al concatenar:\n{str(e)}")
        
        finally:
            self.progreso.stop()
            self.procesando = False
            if len(self.videos) >= 2:
                self.procesar_btn.config(state='normal', bg=self.colors['accent'])

if __name__ == "__main__":
    try:
        root = tk.Tk()
        app = ConcatenarVideos(root)
        root.mainloop()
    except Exception as e:
        messagebox.showerror("Error fatal", f"Error al iniciar:\n{str(e)}")