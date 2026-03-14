# -*- coding: utf-8 -*-


import tkinter as tk
from tkinter import ttk, filedialog, colorchooser, messagebox
import threading
import os
from moviepy import VideoFileClip, TextClip, CompositeVideoClip, ImageClip, concatenate_videoclips
from moviepy.audio.io.AudioFileClip import AudioFileClip
from moviepy.video.fx import FadeIn, FadeOut
from PIL import Image, ImageTk

class EditorVideoCompleto:
    def __init__(self, root):
        self.root = root
        self.root.title("🎬 Editor de Video Completo")
        ancho = 800
        alto = 725
        margen_superior = 2
        
        ancho_pantalla = self.root.winfo_screenwidth()
        x = (ancho_pantalla - ancho) // 2
        y = margen_superior
        
        self.root.geometry(f'{ancho}x{alto}+{x}+{y}')
        self.root.resizable(True, True)
        
        # Variables compartidas (rutas de archivos)
        self.video_paths = {}  # Diccionario para guardar rutas por pestaña
        self.audio_path = None
        self.caratula_path = None
        self.contra_path = None
        
        # Variables de configuración
        self.color_seleccionado = 'white'
        self.posicion_personalizada = None
        self.subtitulos_color = 'white'
        self.lista_textos = []
        
        # Mapeo de fuentes
        self.mapa_fuentes = self.cargar_fuentes()
        
        self.crear_interfaz()
    
    def cargar_fuentes(self):
        """Carga las fuentes disponibles de la carpeta fonts"""
        mapa = {}
        ruta_script = os.path.dirname(os.path.abspath(__file__))
        carpeta_fonts = os.path.join(ruta_script, "fonts")
        
        if os.path.exists(carpeta_fonts):
            for archivo in os.listdir(carpeta_fonts):
                if archivo.lower().endswith('.ttf'):
                    nombre_sin_ext = os.path.splitext(archivo)[0]
                    nombre_amigable = nombre_sin_ext.replace('_', ' ').title()
                    mapa[nombre_amigable] = os.path.join(carpeta_fonts, archivo)
        
        # Fuentes por defecto si no encuentra ninguna
        if not mapa:
            mapa = {
                "Arial": "Arial",
                "Calibri": "Calibri",
                "Times New Roman": "Times New Roman"
            }
        
        return mapa
    
    def crear_interfaz(self):
        # Crear notebook para pestañas
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill='both', expand=True, padx=10, pady=5)
        
        # Pestaña 1: Texto simple
        self.tab_texto = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_texto, text="📝 Texto Simple")
        self.crear_pestana_texto()
        
        # Pestaña 2: Múltiples textos
        self.tab_multiple = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_multiple, text="📚 Múltiples Textos")
        self.crear_pestana_multiple_texto()
        
        # Pestaña 3: Efectos
        self.tab_efectos = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_efectos, text="✨ Efectos")
        self.crear_pestana_efectos()
        
        # Pestaña 4: Música
        self.tab_musica = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_musica, text="🎵 Música")
        self.crear_pestana_musica()
        
        # Pestaña 5: Recortar
        self.tab_recortar = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_recortar, text="✂️ Recortar")
        self.crear_pestana_recortar()
        
        # Pestaña 6: Carátulas
        self.tab_caratulas = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_caratulas, text="🎬 Carátulas")
        self.crear_pestana_caratulas()
    
    def formatear_duracion(self, segundos):
        horas = int(segundos // 3600)
        minutos = int((segundos % 3600) // 60)
        segs = int(segundos % 60)
        if horas > 0:
            return f"{horas:02d}:{minutos:02d}:{segs:02d}"
        else:
            return f"{minutos:02d}:{segs:02d}"
    
    def seleccionar_video_para_pestana(self, pestana_id, label_widget, info_widget):
        """Versión específica para cada pestaña"""
        archivo = filedialog.askopenfilename(
            title="Seleccionar Video",
            filetypes=[("Videos", "*.mp4 *.avi *.mov *.mkv"), ("Todos", "*.*")]
        )
        if archivo:
            # Guardar la ruta para esta pestaña
            self.video_paths[pestana_id] = archivo
            
            # Actualizar etiqueta
            label_widget.config(text=os.path.basename(archivo), fg='black')
            
            # Obtener información del video
            try:
                clip = VideoFileClip(archivo)
                duracion_formateada = self.formatear_duracion(clip.duration)
                info = f"Duración: {duracion_formateada} | {clip.size[0]}x{clip.size[1]}"
                info_widget.config(text=info)
                clip.close()
            except Exception as e:
                info_widget.config(text=f"Error: {str(e)}")
    
    def obtener_video_actual(self, pestana_id):
        """Obtiene el video de la pestaña actual"""
        if pestana_id in self.video_paths:
            return self.video_paths[pestana_id]
        return None
    
    # ========== PESTAÑA TEXTO SIMPLE ==========
    
    def crear_pestana_texto(self):
        pestana_id = "texto"
        
        tk.Label(self.tab_texto, text="📝 AÑADIR TEXTO SIMPLE", 
                font=('Arial', 16, 'bold'), fg='#4CAF50').pack(pady=10)
        
        self.mostrar_info_fuentes(self.tab_texto)
        
        # Selector de video específico para esta pestaña
        frame = tk.Frame(self.tab_texto)
        frame.pack(fill=tk.X, padx=20, pady=5)
        
        tk.Label(frame, text="🎥 Video:", font=('Arial', 11)).pack(anchor='w')
        
        btn_frame = tk.Frame(frame)
        btn_frame.pack(fill=tk.X, pady=5)
        
        # Etiquetas específicas para esta pestaña
        self.video_label_texto = tk.Label(btn_frame, text="Ningún video seleccionado", fg='gray', width=50, anchor='w')
        self.video_label_texto.pack(side=tk.LEFT)
        
        tk.Button(btn_frame, text="Seleccionar Video", bg='#4CAF50', fg='white', padx=15,
                 command=lambda: self.seleccionar_video_para_pestana(
                     pestana_id, self.video_label_texto, self.video_info_texto)).pack(side=tk.RIGHT)
        
        self.video_info_texto = tk.Label(frame, text="", fg='blue', font=('Arial', 9))
        self.video_info_texto.pack(anchor='w')
        
        tk.Frame(self.tab_texto, height=1, bg='#ccc').pack(fill=tk.X, padx=20, pady=10)
        
        # Configuración del texto
        config_frame = tk.Frame(self.tab_texto)
        config_frame.pack(padx=20, pady=5, fill=tk.X)
        
        # Texto
        tk.Label(config_frame, text="📝 Texto:", font=('Arial', 11)).grid(row=0, column=0, sticky='w', pady=5)
        self.texto_entry = tk.Entry(config_frame, width=40, font=('Arial', 11))
        self.texto_entry.grid(row=0, column=1, columnspan=3, pady=5, padx=5)
        self.texto_entry.insert(0, "¡Hola Mundo!")
        
        # Posición
        tk.Label(config_frame, text="📍 Posición:", font=('Arial', 11)).grid(row=1, column=0, sticky='w', pady=5)
        
        pos_frame = tk.Frame(config_frame)
        pos_frame.grid(row=1, column=1, columnspan=2, sticky='w', pady=5)
        
        self.posicion = ttk.Combobox(pos_frame, 
                                     values=['center', 'top', 'bottom', 'left', 'right', 'personalizada'],
                                     width=15)
        self.posicion.pack(side=tk.LEFT)
        self.posicion.set('center')
        
        tk.Button(pos_frame, text="👆 Elegir con clic", bg='#FF9800', fg='white',
                 command=lambda: self.previsualizar_posicion(pestana_id)).pack(side=tk.LEFT, padx=5)
        
        # Tamaño
        tk.Label(config_frame, text="🔤 Tamaño:", font=('Arial', 11)).grid(row=2, column=0, sticky='w', pady=5)
        self.tamaño = tk.Scale(config_frame, from_=20, to=100, orient=tk.HORIZONTAL, length=300)
        self.tamaño.grid(row=2, column=1, columnspan=2, pady=5, padx=5)
        self.tamaño.set(50)
        
        # Fuente
        tk.Label(config_frame, text="🔤 Fuente:", font=('Arial', 11)).grid(row=3, column=0, sticky='w', pady=5)
        self.fuente = ttk.Combobox(config_frame, values=sorted(self.mapa_fuentes.keys()), width=30)
        self.fuente.grid(row=3, column=1, columnspan=2, pady=5, padx=5)
        self.fuente.set('Arial')
        
        # Color
        tk.Label(config_frame, text="🎨 Color:", font=('Arial', 11)).grid(row=4, column=0, sticky='w', pady=5)
        color_frame = tk.Frame(config_frame)
        color_frame.grid(row=4, column=1, columnspan=2, pady=5, padx=5)
        tk.Button(color_frame, text="Seleccionar", bg='#2196F3', fg='white',
                 command=self.seleccionar_color).pack(side=tk.LEFT)
        self.color_label = tk.Label(color_frame, text="  ", bg='white', width=5, relief=tk.SUNKEN)
        self.color_label.pack(side=tk.LEFT, padx=5)
        
        # Borde
        tk.Label(config_frame, text="⚫ Borde:", font=('Arial', 11)).grid(row=5, column=0, sticky='w', pady=5)
        self.borde_var = tk.BooleanVar(value=True)
        tk.Checkbutton(config_frame, text="Añadir borde negro", variable=self.borde_var).grid(row=5, column=1, sticky='w')
        
        # Duración
        tk.Label(config_frame, text="⏱️ Duración:", font=('Arial', 11)).grid(row=6, column=0, sticky='w', pady=5)
        self.duracion_completa = tk.BooleanVar(value=True)
        tk.Radiobutton(config_frame, text="Video completo", variable=self.duracion_completa, value=True).grid(row=6, column=1, sticky='w')
        
        duracion_frame = tk.Frame(config_frame)
        duracion_frame.grid(row=7, column=1, columnspan=2, sticky='w')
        tk.Radiobutton(duracion_frame, text="Personalizada:", variable=self.duracion_completa, value=False).pack(side=tk.LEFT)
        self.duracion_entry = tk.Entry(duracion_frame, width=8)
        self.duracion_entry.pack(side=tk.LEFT, padx=5)
        self.duracion_entry.insert(0, "5")
        self.duracion_entry.config(state='disabled')
        tk.Label(duracion_frame, text="seg").pack(side=tk.LEFT)
        
        def toggle_duracion(*args):
            self.duracion_entry.config(state='normal' if not self.duracion_completa.get() else 'disabled')
        self.duracion_completa.trace('w', toggle_duracion)
        
        tk.Button(self.tab_texto, text="📝 PROCESAR TEXTO", bg='#4CAF50', fg='white',
                 font=('Arial', 14, 'bold'), padx=30, pady=10, 
                 command=lambda: self.procesar_texto(pestana_id)).pack(pady=20)
        
        self.progreso_texto = ttk.Progressbar(self.tab_texto, mode='indeterminate')
        self.progreso_texto.pack(fill=tk.X, padx=20, pady=5)
        
        self.estado_texto = tk.Label(self.tab_texto, text="✅ Listo", fg='green')
        self.estado_texto.pack()
    
    def previsualizar_posicion(self, pestana_id):
        video_path = self.obtener_video_actual(pestana_id)
        if not video_path:
            messagebox.showerror("Error", "Primero selecciona un video")
            return
        
        if not self.texto_entry.get():
            messagebox.showerror("Error", "Escribe un texto para previsualizar")
            return
        
        try:
            preview_window = tk.Toplevel(self.root)
            preview_window.title("🎬 Previsualización - Haz clic para posicionar el texto")
            preview_window.geometry("900x750")
            preview_window.transient(self.root)
            preview_window.grab_set()
            
            control_frame = tk.Frame(preview_window)
            control_frame.pack(fill=tk.X, padx=10, pady=5)
            
            tk.Label(control_frame, text="Tiempo de previsualización (seg):").pack(side=tk.LEFT)
            tiempo_preview = tk.Entry(control_frame, width=8)
            tiempo_preview.pack(side=tk.LEFT, padx=5)
            tiempo_preview.insert(0, "2")
            
            tk.Label(control_frame, text=f"Texto: {self.texto_entry.get()}", 
                    fg='blue', font=('Arial', 9)).pack(side=tk.RIGHT, padx=10)
            
            actualizar_btn = tk.Button(control_frame, text="Actualizar frame", 
                                      command=lambda: self.cargar_frame_preview(
                                          preview_window, canvas, tiempo_preview.get(), video_path))
            actualizar_btn.pack(side=tk.LEFT, padx=10)
            
            canvas_frame = tk.Frame(preview_window, bg='black')
            canvas_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
            
            canvas = tk.Canvas(canvas_frame, bg='black', highlightthickness=0)
            canvas.pack(fill=tk.BOTH, expand=True)
            
            coord_label = tk.Label(preview_window, text="Haz clic en el video para posicionar el texto", 
                                  font=('Arial', 10), fg='blue')
            coord_label.pack(pady=5)
            
            seleccion_frame = tk.Frame(preview_window)
            seleccion_frame.pack(fill=tk.X, padx=10, pady=5)
            
            tk.Label(seleccion_frame, text="Posición seleccionada:").pack(side=tk.LEFT)
            
            x_label = tk.Label(seleccion_frame, text="X: --", width=8, font=('Arial', 10, 'bold'))
            x_label.pack(side=tk.LEFT, padx=5)
            
            y_label = tk.Label(seleccion_frame, text="Y: --", width=8, font=('Arial', 10, 'bold'))
            y_label.pack(side=tk.LEFT, padx=5)
            
            btn_frame = tk.Frame(preview_window)
            btn_frame.pack(fill=tk.X, padx=10, pady=10)
            
            tk.Button(btn_frame, text="✅ Usar esta posición", bg='#4CAF50', fg='white',
                     font=('Arial', 11, 'bold'), padx=20,
                     command=lambda: self.usar_posicion_preview(
                         preview_window, x_label, y_label)).pack(side=tk.LEFT, padx=5)
            
            tk.Button(btn_frame, text="❌ Cancelar", bg='#F44336', fg='white',
                     font=('Arial', 11, 'bold'), padx=20,
                     command=preview_window.destroy).pack(side=tk.LEFT, padx=5)
            
            preview_window.click_x = tk.IntVar(value=-1)
            preview_window.click_y = tk.IntVar(value=-1)
            
            self.cargar_frame_preview(preview_window, canvas, tiempo_preview.get(), video_path)
            
            def on_click(event):
                if not hasattr(preview_window, 'video_width'):
                    return
                
                x_ratio = preview_window.video_width / canvas.winfo_width()
                y_ratio = preview_window.video_height / canvas.winfo_height()
                
                x = int(event.x * x_ratio)
                y = int(event.y * y_ratio)
                
                x = max(0, min(x, preview_window.video_width))
                y = max(0, min(y, preview_window.video_height))
                
                preview_window.click_x.set(x)
                preview_window.click_y.set(y)
                
                x_label.config(text=f"X: {x}")
                y_label.config(text=f"Y: {y}")
                
                canvas.delete("selector")
                r = 10
                canvas.create_oval(event.x - r, event.y - r, event.x + r, event.y + r,
                                  outline='red', width=3, tag="selector")
                canvas.create_text(event.x, event.y - 25, text=f"({x}, {y})",
                                  fill='red', font=('Arial', 10, 'bold'), tag="selector")
                canvas.create_text(event.x, event.y + 25, text=self.texto_entry.get(),
                                  fill='yellow', font=('Arial', 16, 'bold'), tag="selector")
            
            canvas.bind("<Button-1>", on_click)
            
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo abrir la previsualización:\n{str(e)}")
    
    def cargar_frame_preview(self, preview_window, canvas, tiempo_str, video_path):
        try:
            tiempo = float(tiempo_str)
            clip = VideoFileClip(video_path)
            
            if tiempo > clip.duration:
                tiempo = clip.duration / 2
            
            frame = clip.get_frame(tiempo)
            
            img = Image.fromarray(frame)
            
            canvas.update_idletasks()
            max_width = canvas.winfo_width() - 20
            max_height = canvas.winfo_height() - 20
            
            if max_width < 10:
                max_width = 800
                max_height = 600
            
            img.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)
            
            preview_window.video_width = clip.size[0]
            preview_window.video_height = clip.size[1]
            
            photo = ImageTk.PhotoImage(img)
            
            canvas.delete("all")
            canvas.create_image(max_width//2 + 10, max_height//2 + 10, 
                               image=photo, anchor='center')
            canvas.image = photo
            
            clip.close()
            
        except Exception as e:
            print(f"Error cargando frame: {e}")
    
    def usar_posicion_preview(self, preview_window, x_label, y_label):
        x = preview_window.click_x.get()
        y = preview_window.click_y.get()
        
        if x < 0 or y < 0:
            messagebox.showwarning("Advertencia", "Haz clic en el video para seleccionar una posición")
            return
        
        self.posicion_personalizada = (x, y)
        self.posicion.set('personalizada')
        
        messagebox.showinfo("Éxito", f"Posición guardada: X={x}, Y={y}")
        preview_window.destroy()
    
    # ========== PESTAÑA MÚLTIPLES TEXTOS ==========
    
    def crear_pestana_multiple_texto(self):
        pestana_id = "multiple"
        
        tk.Label(self.tab_multiple, text="📚 MÚLTIPLES TEXTOS", 
                font=('Arial', 16, 'bold'), fg='#9C27B0').pack(pady=10)
        
        # Selector de video específico
        frame = tk.Frame(self.tab_multiple)
        frame.pack(fill=tk.X, padx=20, pady=5)
        
        tk.Label(frame, text="🎥 Video:", font=('Arial', 11)).pack(anchor='w')
        
        btn_frame = tk.Frame(frame)
        btn_frame.pack(fill=tk.X, pady=5)
        
        self.video_label_multiple = tk.Label(btn_frame, text="Ningún video seleccionado", fg='gray', width=50, anchor='w')
        self.video_label_multiple.pack(side=tk.LEFT)
        
        tk.Button(btn_frame, text="Seleccionar Video", bg='#4CAF50', fg='white', padx=15,
                 command=lambda: self.seleccionar_video_para_pestana(
                     pestana_id, self.video_label_multiple, self.video_info_multiple)).pack(side=tk.RIGHT)
        
        self.video_info_multiple = tk.Label(frame, text="", fg='blue', font=('Arial', 9))
        self.video_info_multiple.pack(anchor='w')
        
        # Resto de la interfaz...
        list_frame = tk.Frame(self.tab_multiple)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        tk.Label(list_frame, text="Textos programados:", font=('Arial', 12, 'bold')).pack(anchor='w')
        
        scroll_frame = tk.Frame(list_frame)
        scroll_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        self.textos_listbox = tk.Listbox(scroll_frame, height=6, width=70)
        scrollbar = tk.Scrollbar(scroll_frame)
        self.textos_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.textos_listbox.config(yscrollcommand=scrollbar.set)
        scrollbar.config(command=self.textos_listbox.yview)
        
        btn_frame_list = tk.Frame(list_frame)
        btn_frame_list.pack(fill=tk.X, pady=5)
        
        tk.Button(btn_frame_list, text="➕ Añadir", bg='#4CAF50', fg='white',
                 command=self.añadir_texto_lista).pack(side=tk.LEFT, padx=2)
        tk.Button(btn_frame_list, text="✏️ Editar", bg='#FF9800', fg='white',
                 command=self.editar_texto_lista).pack(side=tk.LEFT, padx=2)
        tk.Button(btn_frame_list, text="❌ Eliminar", bg='#F44336', fg='white',
                 command=self.eliminar_texto_lista).pack(side=tk.LEFT, padx=2)
        
        # Frame para nuevo texto (con más opciones)
        texto_frame = tk.LabelFrame(self.tab_multiple, text="Nuevo texto", padx=10, pady=10)
        texto_frame.pack(fill=tk.X, padx=20, pady=10)

        # Texto (fila 0)
        tk.Label(texto_frame, text="Texto:").grid(row=0, column=0, sticky='w')
        self.multiple_texto = tk.Entry(texto_frame, width=50)
        self.multiple_texto.grid(row=0, column=1, columnspan=5, padx=5, pady=2)

        # Inicio y Duración (fila 1)
        tk.Label(texto_frame, text="Inicio (seg):").grid(row=1, column=0, sticky='w')
        self.multiple_inicio = tk.Entry(texto_frame, width=8)
        self.multiple_inicio.grid(row=1, column=1, sticky='w', padx=5)
        self.multiple_inicio.insert(0, "0")

        tk.Label(texto_frame, text="Duración (seg):").grid(row=1, column=2, sticky='w', padx=(10,0))
        self.multiple_duracion = tk.Entry(texto_frame, width=8)
        self.multiple_duracion.grid(row=1, column=3, sticky='w', padx=5)
        self.multiple_duracion.insert(0, "5")

        # Tamaño y Posición (fila 2)
        tk.Label(texto_frame, text="Tamaño:").grid(row=2, column=0, sticky='w', pady=5)
        self.multiple_tamaño = tk.Scale(texto_frame, from_=10, to=100, orient=tk.HORIZONTAL, length=150)
        self.multiple_tamaño.grid(row=2, column=1, columnspan=2, sticky='w', padx=5)
        self.multiple_tamaño.set(20)

        tk.Label(texto_frame, text="Posición:").grid(row=2, column=3, sticky='w', padx=(10,0))
        self.multiple_posicion = ttk.Combobox(texto_frame, 
                                              values=['center', 'top', 'bottom', 'left', 'right'],
                                              width=10)
        self.multiple_posicion.grid(row=2, column=4, sticky='w')
        self.multiple_posicion.set('center')
              
        tk.Button(self.tab_multiple, text="📚 PROCESAR MÚLTIPLES TEXTOS", bg='#9C27B0', fg='white',
                 font=('Arial', 12, 'bold'), padx=20, pady=10, 
                 command=lambda: self.procesar_multiple_texto(pestana_id)).pack(pady=10)
        
        self.progreso_multiple = ttk.Progressbar(self.tab_multiple, mode='indeterminate')
        self.progreso_multiple.pack(fill=tk.X, padx=20, pady=5)
        
        self.estado_multiple = tk.Label(self.tab_multiple, text="✅ Listo", fg='green')
        self.estado_multiple.pack()
    
    # ========== PESTAÑA EFECTOS ==========
    
    def crear_pestana_efectos(self):
        pestana_id = "efectos"
        
        tk.Label(self.tab_efectos, text="✨ EFECTOS DE ENTRADA/SALIDA", 
                font=('Arial', 16, 'bold'), fg='#FF9800').pack(pady=10)
        
        # Selector de video específico
        frame = tk.Frame(self.tab_efectos)
        frame.pack(fill=tk.X, padx=20, pady=5)
        
        tk.Label(frame, text="🎥 Video:", font=('Arial', 11)).pack(anchor='w')
        
        btn_frame = tk.Frame(frame)
        btn_frame.pack(fill=tk.X, pady=5)
        
        self.video_label_efectos = tk.Label(btn_frame, text="Ningún video seleccionado", fg='gray', width=50, anchor='w')
        self.video_label_efectos.pack(side=tk.LEFT)
        
        tk.Button(btn_frame, text="Seleccionar Video", bg='#4CAF50', fg='white', padx=15,
                 command=lambda: self.seleccionar_video_para_pestana(
                     pestana_id, self.video_label_efectos, self.video_info_efectos)).pack(side=tk.RIGHT)
        
        self.video_info_efectos = tk.Label(frame, text="", fg='blue', font=('Arial', 9))
        self.video_info_efectos.pack(anchor='w')
        
        # Configuración de efectos
        efectos_frame = tk.Frame(self.tab_efectos)
        efectos_frame.pack(padx=20, pady=20, fill=tk.X)
        
        tk.Label(efectos_frame, text="🎬 Fade In:", font=('Arial', 11)).grid(row=0, column=0, sticky='w', pady=5)
        self.fade_in_var = tk.BooleanVar(value=False)
        tk.Checkbutton(efectos_frame, text="Activar fade in", variable=self.fade_in_var).grid(row=0, column=1, sticky='w')
        
        tk.Label(efectos_frame, text="Duración fade in (seg):").grid(row=1, column=0, sticky='w', pady=5)
        self.fade_in_duracion = tk.Entry(efectos_frame, width=10)
        self.fade_in_duracion.grid(row=1, column=1, sticky='w', padx=5)
        self.fade_in_duracion.insert(0, "2")
        
        tk.Label(efectos_frame, text="🎬 Fade Out:", font=('Arial', 11)).grid(row=2, column=0, sticky='w', pady=5)
        self.fade_out_var = tk.BooleanVar(value=False)
        tk.Checkbutton(efectos_frame, text="Activar fade out", variable=self.fade_out_var).grid(row=2, column=1, sticky='w')
        
        tk.Label(efectos_frame, text="Duración fade out (seg):").grid(row=3, column=0, sticky='w', pady=5)
        self.fade_out_duracion = tk.Entry(efectos_frame, width=10)
        self.fade_out_duracion.grid(row=3, column=1, sticky='w', padx=5)
        self.fade_out_duracion.insert(0, "2")
        
        tk.Button(self.tab_efectos, text="✨ APLICAR EFECTOS", bg='#FF9800', fg='white',
                 font=('Arial', 14, 'bold'), padx=30, pady=10, 
                 command=lambda: self.procesar_efectos(pestana_id)).pack(pady=20)
        
        self.progreso_efectos = ttk.Progressbar(self.tab_efectos, mode='indeterminate')
        self.progreso_efectos.pack(fill=tk.X, padx=20, pady=5)
        
        self.estado_efectos = tk.Label(self.tab_efectos, text="✅ Listo", fg='green')
        self.estado_efectos.pack()
    
    # ========== PESTAÑA MÚSICA ==========
    
    def crear_pestana_musica(self):
        pestana_id = "musica"
        
        tk.Label(self.tab_musica, text="🎵 MÚSICA DE FONDO", 
                font=('Arial', 16, 'bold'), fg='#2196F3').pack(pady=10)
        
        # Selector de video específico
        frame = tk.Frame(self.tab_musica)
        frame.pack(fill=tk.X, padx=20, pady=5)
        
        tk.Label(frame, text="🎥 Video:", font=('Arial', 11)).pack(anchor='w')
        
        btn_frame = tk.Frame(frame)
        btn_frame.pack(fill=tk.X, pady=5)
        
        self.video_label_musica = tk.Label(btn_frame, text="Ningún video seleccionado", fg='gray', width=50, anchor='w')
        self.video_label_musica.pack(side=tk.LEFT)
        
        tk.Button(btn_frame, text="Seleccionar Video", bg='#4CAF50', fg='white', padx=15,
                 command=lambda: self.seleccionar_video_para_pestana(
                     pestana_id, self.video_label_musica, self.video_info_musica)).pack(side=tk.RIGHT)
        
        self.video_info_musica = tk.Label(frame, text="", fg='blue', font=('Arial', 9))
        self.video_info_musica.pack(anchor='w')
        
        # Configuración de música
        musica_frame = tk.Frame(self.tab_musica)
        musica_frame.pack(padx=20, pady=20, fill=tk.X)
        
        tk.Label(musica_frame, text="🎵 Archivo de música:", font=('Arial', 11)).pack(anchor='w')
        
        audio_btn_frame = tk.Frame(musica_frame)
        audio_btn_frame.pack(fill=tk.X, pady=5)
        
        self.audio_label = tk.Label(audio_btn_frame, text="Ningún audio seleccionado", fg='gray', width=50, anchor='w')
        self.audio_label.pack(side=tk.LEFT)
        
        tk.Button(audio_btn_frame, text="Seleccionar Audio", bg='#2196F3', fg='white',
                 command=self.seleccionar_audio).pack(side=tk.RIGHT)
        
        tk.Label(musica_frame, text="Volumen de la música (0-100%):", font=('Arial', 11)).pack(anchor='w', pady=(10,0))
        self.volumen = tk.Scale(musica_frame, from_=0, to=100, orient=tk.HORIZONTAL, length=400)
        self.volumen.pack(fill=tk.X, pady=5)
        self.volumen.set(50)
        
        opciones_frame = tk.Frame(musica_frame)
        opciones_frame.pack(fill=tk.X, pady=10)
        
        self.mantener_audio_original = tk.BooleanVar(value=True)
        tk.Checkbutton(opciones_frame, text="Mantener audio original del video", 
                      variable=self.mantener_audio_original).pack(anchor='w')
        
        tk.Button(self.tab_musica, text="🎵 AÑADIR MÚSICA", bg='#2196F3', fg='white',
                 font=('Arial', 14, 'bold'), padx=30, pady=10, 
                 command=lambda: self.procesar_musica(pestana_id)).pack(pady=20)
        
        self.progreso_musica = ttk.Progressbar(self.tab_musica, mode='indeterminate')
        self.progreso_musica.pack(fill=tk.X, padx=20, pady=5)
        
        self.estado_musica = tk.Label(self.tab_musica, text="✅ Listo", fg='green')
        self.estado_musica.pack()
    
    # ========== PESTAÑA RECORTAR ==========
    
    def crear_pestana_recortar(self):
        pestana_id = "recortar"
        
        tk.Label(self.tab_recortar, text="✂️ RECORTAR VIDEO", 
                font=('Arial', 16, 'bold'), fg='#F44336').pack(pady=10)
        
        # Selector de video específico
        frame = tk.Frame(self.tab_recortar)
        frame.pack(fill=tk.X, padx=20, pady=5)
        
        tk.Label(frame, text="🎥 Video:", font=('Arial', 11)).pack(anchor='w')
        
        btn_frame = tk.Frame(frame)
        btn_frame.pack(fill=tk.X, pady=5)
        
        self.video_label_recortar = tk.Label(btn_frame, text="Ningún video seleccionado", fg='gray', width=50, anchor='w')
        self.video_label_recortar.pack(side=tk.LEFT)
        
        tk.Button(btn_frame, text="Seleccionar Video", bg='#4CAF50', fg='white', padx=15,
                 command=lambda: self.seleccionar_video_para_pestana(
                     pestana_id, self.video_label_recortar, self.video_info_recortar)).pack(side=tk.RIGHT)
        
        self.video_info_recortar = tk.Label(frame, text="", fg='blue', font=('Arial', 9))
        self.video_info_recortar.pack(anchor='w')
        
        # Configuración de recorte
        recortar_frame = tk.Frame(self.tab_recortar)
        recortar_frame.pack(padx=20, pady=20, fill=tk.X)
        
        tk.Label(recortar_frame, text="Tiempo de inicio (seg):", font=('Arial', 11)).pack(anchor='w')
        self.recortar_inicio = tk.Entry(recortar_frame, width=10)
        self.recortar_inicio.pack(anchor='w', pady=5)
        self.recortar_inicio.insert(0, "0")
        
        tk.Label(recortar_frame, text="Tiempo de fin (seg):", font=('Arial', 11)).pack(anchor='w')
        self.recortar_fin = tk.Entry(recortar_frame, width=10)
        self.recortar_fin.pack(anchor='w', pady=5)
        self.recortar_fin.insert(0, "10")
        
        tk.Label(recortar_frame, text="(Dejar vacío para hasta el final)", font=('Arial', 8), fg='gray').pack(anchor='w')
        
        tk.Button(self.tab_recortar, text="✂️ RECORTAR VIDEO", bg='#F44336', fg='white',
                 font=('Arial', 14, 'bold'), padx=30, pady=10, 
                 command=lambda: self.procesar_recortar(pestana_id)).pack(pady=20)
        
        self.progreso_recortar = ttk.Progressbar(self.tab_recortar, mode='indeterminate')
        self.progreso_recortar.pack(fill=tk.X, padx=20, pady=5)
        
        self.estado_recortar = tk.Label(self.tab_recortar, text="✅ Listo", fg='green')
        self.estado_recortar.pack()
    
    # ========== PESTAÑA CARÁTULAS ==========
    
    def crear_pestana_caratulas(self):
        pestana_id = "caratulas"
        
        tk.Label(self.tab_caratulas, text="🎬 CARÁTULA Y CONTRAPORTADA", 
                font=('Arial', 16, 'bold'), fg='#FF6B6B').pack(pady=10)
        
        # Selector de video específico
        frame = tk.Frame(self.tab_caratulas)
        frame.pack(fill=tk.X, padx=20, pady=5)
        
        tk.Label(frame, text="🎥 Video:", font=('Arial', 11)).pack(anchor='w')
        
        btn_frame = tk.Frame(frame)
        btn_frame.pack(fill=tk.X, pady=5)
        
        self.video_label_caratulas = tk.Label(btn_frame, text="Ningún video seleccionado", fg='gray', width=50, anchor='w')
        self.video_label_caratulas.pack(side=tk.LEFT)
        
        tk.Button(btn_frame, text="Seleccionar Video", bg='#4CAF50', fg='white', padx=15,
                 command=lambda: self.seleccionar_video_para_pestana(
                     pestana_id, self.video_label_caratulas, self.video_info_caratulas)).pack(side=tk.RIGHT)
        
        self.video_info_caratulas = tk.Label(frame, text="", fg='blue', font=('Arial', 9))
        self.video_info_caratulas.pack(anchor='w')
        
        # Configuración de carátulas
        frame_caratula = tk.LabelFrame(self.tab_caratulas, text="Carátula (inicio)", padx=10, pady=10)
        frame_caratula.pack(fill=tk.X, padx=20, pady=10)
        
        tk.Label(frame_caratula, text="🖼️ Imagen:").grid(row=0, column=0, sticky='w')
        
        btn_frame1 = tk.Frame(frame_caratula)
        btn_frame1.grid(row=0, column=1, pady=5)
        self.caratula_label = tk.Label(btn_frame1, text="Ninguna imagen", fg='gray', width=40, anchor='w')
        self.caratula_label.pack(side=tk.LEFT)
        tk.Button(btn_frame1, text="Seleccionar", bg='#4CAF50', fg='white',
                 command=self.seleccionar_caratula).pack(side=tk.RIGHT)
        
        tk.Label(frame_caratula, text="⏱️ Duración (seg):").grid(row=1, column=0, sticky='w')
        self.caratula_duracion = tk.Entry(frame_caratula, width=8)
        self.caratula_duracion.grid(row=1, column=1, sticky='w')
        self.caratula_duracion.insert(0, "3")
        
        frame_contra = tk.LabelFrame(self.tab_caratulas, text="Contraportada (final)", padx=10, pady=10)
        frame_contra.pack(fill=tk.X, padx=20, pady=10)
        
        tk.Label(frame_contra, text="🖼️ Imagen:").grid(row=0, column=0, sticky='w')
        
        btn_frame2 = tk.Frame(frame_contra)
        btn_frame2.grid(row=0, column=1, pady=5)
        self.contra_label = tk.Label(btn_frame2, text="Ninguna imagen", fg='gray', width=40, anchor='w')
        self.contra_label.pack(side=tk.LEFT)
        tk.Button(btn_frame2, text="Seleccionar", bg='#4CAF50', fg='white',
                 command=self.seleccionar_contra).pack(side=tk.RIGHT)
        
        tk.Label(frame_contra, text="⏱️ Duración (seg):").grid(row=1, column=0, sticky='w')
        self.contra_duracion = tk.Entry(frame_contra, width=8)
        self.contra_duracion.grid(row=1, column=1, sticky='w')
        self.contra_duracion.insert(0, "3")
        
        tk.Button(self.tab_caratulas, text="🎬 PROCESAR CARÁTULAS", bg='#FF6B6B', fg='white',
                 font=('Arial', 14, 'bold'), padx=30, pady=10, 
                 command=lambda: self.procesar_caratulas(pestana_id)).pack(pady=20)
        
        self.progreso_caratulas = ttk.Progressbar(self.tab_caratulas, mode='indeterminate')
        self.progreso_caratulas.pack(fill=tk.X, padx=20, pady=5)
        
        self.estado_caratulas = tk.Label(self.tab_caratulas, text="✅ Listo", fg='green')
        self.estado_caratulas.pack()
    
    # ========== FUNCIONES AUXILIARES ==========
    
    def mostrar_info_fuentes(self, parent):
        ruta_script = os.path.dirname(os.path.abspath(__file__))
        carpeta_fonts = os.path.join(ruta_script, "fonts")
        
        if os.path.exists(carpeta_fonts):
            fuentes_encontradas = []
            for archivo in os.listdir(carpeta_fonts):
                if archivo.lower().endswith('.ttf'):
                    fuentes_encontradas.append(archivo)
            
            if fuentes_encontradas:
                info_text = f"✅ {len(fuentes_encontradas)} fuentes disponibles"
                tk.Label(parent, text=info_text, fg='green', font=('Arial', 9)).pack()
            else:
                tk.Label(parent, text="⚠️ Carpeta 'fonts' vacía", fg='orange', font=('Arial', 9)).pack()
        else:
            tk.Label(parent, text="⚠️ Crear carpeta 'fonts' junto al script", fg='orange', font=('Arial', 9)).pack()
    
    def seleccionar_audio(self):
        archivo = filedialog.askopenfilename(
            title="Seleccionar archivo de audio",
            filetypes=[("Audio", "*.mp3 *.wav *.m4a *.ogg"), ("Todos", "*.*")]
        )
        if archivo:
            self.audio_path = archivo
            self.audio_label.config(text=os.path.basename(archivo), fg='black')
    
    def seleccionar_caratula(self):
        archivo = filedialog.askopenfilename(
            title="Seleccionar imagen para carátula",
            filetypes=[("Imágenes", "*.png *.jpg *.jpeg *.gif *.bmp"), ("Todos", "*.*")]
        )
        if archivo:
            self.caratula_path = archivo
            self.caratula_label.config(text=os.path.basename(archivo), fg='black')
    
    def seleccionar_contra(self):
        archivo = filedialog.askopenfilename(
            title="Seleccionar imagen para contraportada",
            filetypes=[("Imágenes", "*.png *.jpg *.jpeg *.gif *.bmp"), ("Todos", "*.*")]
        )
        if archivo:
            self.contra_path = archivo
            self.contra_label.config(text=os.path.basename(archivo), fg='black')
    
    def seleccionar_color(self):
        color = colorchooser.askcolor(title="Seleccionar color", initialcolor=self.color_seleccionado)[1]
        if color:
            self.color_seleccionado = color
            self.color_label.config(bg=color)
    
    def obtener_ruta_fuente(self, nombre_fuente):
        if nombre_fuente in self.mapa_fuentes:
            return self.mapa_fuentes[nombre_fuente]
        return nombre_fuente
    
    def añadir_texto_lista(self):
        texto = self.multiple_texto.get()
        inicio = self.multiple_inicio.get()
        duracion = self.multiple_duracion.get()
        tamaño = self.multiple_tamaño.get()  # <--- NUEVO
        posicion = self.multiple_posicion.get()  # <--- NUEVO
        
        if not texto:
            messagebox.showwarning("Advertencia", "El texto no puede estar vacío")
            return
        
        try:
            inicio_float = float(inicio)
            duracion_float = float(duracion)
            tamaño_int = int(tamaño)  # <--- NUEVO
        except:
            messagebox.showwarning("Advertencia", "Inicio, duración y tamaño deben ser números")
            return
        
        # Mostrar en la lista con más información
        item = f"{texto} | Inicio:{inicio}s | Dur:{duracion}s | Tam:{tamaño} | Pos:{posicion}"
        self.textos_listbox.insert(tk.END, item)
        
        # Guardar todos los datos
        self.lista_textos.append({
            'texto': texto,
            'inicio': inicio_float,
            'duracion': duracion_float,
            'tamaño': tamaño_int,  # <--- NUEVO
            'posicion': posicion   # <--- NUEVO
        })
        
        # Limpiar campos
        self.multiple_texto.delete(0, tk.END)
        self.multiple_inicio.delete(0, tk.END)
        self.multiple_inicio.insert(0, "0")
        self.multiple_duracion.delete(0, tk.END)
        self.multiple_duracion.insert(0, "5")
        self.multiple_tamaño.set(20)  # <--- NUEVO
        self.multiple_posicion.set('center')  # <--- NUEVO
    
    def editar_texto_lista(self):
        seleccion = self.textos_listbox.curselection()
        if not seleccion:
            messagebox.showwarning("Advertencia", "Selecciona un texto para editar")
            return
        
        idx = seleccion[0]
        texto_data = self.lista_textos[idx]
        
        self.multiple_texto.delete(0, tk.END)
        self.multiple_texto.insert(0, texto_data['texto'])
        self.multiple_inicio.delete(0, tk.END)
        self.multiple_inicio.insert(0, str(texto_data['inicio']))
        self.multiple_duracion.delete(0, tk.END)
        self.multiple_duracion.insert(0, str(texto_data['duracion']))
        self.multiple_tamaño.set(texto_data['tamaño'])  # <--- NUEVO
        self.multiple_posicion.set(texto_data['posicion'])  # <--- NUEVO
        
        self.textos_listbox.delete(idx)
        self.lista_textos.pop(idx)
    
    def eliminar_texto_lista(self):
        seleccion = self.textos_listbox.curselection()
        if seleccion:
            idx = seleccion[0]
            self.textos_listbox.delete(idx)
            self.lista_textos.pop(idx)
    
    # ========== FUNCIONES DE PROCESAMIENTO ==========
    
    def procesar_texto(self, pestana_id):
        video_path = self.obtener_video_actual(pestana_id)
        if not video_path:
            messagebox.showerror("Error", "Selecciona un video")
            return
        
        if not self.texto_entry.get():
            messagebox.showerror("Error", "Escribe un texto")
            return
        
        threading.Thread(target=self._procesar_texto_thread, args=(video_path,), daemon=True).start()
    
    def _procesar_texto_thread(self, video_path):
        self.progreso_texto.start()
        self.estado_texto.config(text="⏳ Procesando...", fg='orange')
        
        try:
            clip = VideoFileClip(video_path)
            
            if self.duracion_completa.get():
                duracion_texto = clip.duration
            else:
                duracion_texto = float(self.duracion_entry.get())
            
            fuente = self.obtener_ruta_fuente(self.fuente.get())
            
            texto = TextClip(
                font=fuente,
                text=self.texto_entry.get(),
                font_size=self.tamaño.get(),
                color=self.color_seleccionado,
                stroke_color='black' if self.borde_var.get() else None,
                stroke_width=2 if self.borde_var.get() else 0
            ).with_duration(duracion_texto)
            
            if self.posicion.get() == 'center':
                texto = texto.with_position(('center', 'center'))
            elif self.posicion.get() == 'top':
                texto = texto.with_position(('center', 50))
            elif self.posicion.get() == 'bottom':
                texto = texto.with_position(('center', clip.h - 100))
            elif self.posicion.get() == 'left':
                texto = texto.with_position((50, 'center'))
            elif self.posicion.get() == 'right':
                texto = texto.with_position((clip.w - 200, 'center'))
            elif self.posicion.get() == 'personalizada' and self.posicion_personalizada:
                x, y = self.posicion_personalizada
                texto = texto.with_position((x, y))
            
            if duracion_texto < clip.duration:
                texto = texto.with_start(0)
            
            video_final = CompositeVideoClip([clip, texto])
            
            archivo_salida = filedialog.asksaveasfilename(
                defaultextension=".mp4",
                filetypes=[("MP4", "*.mp4")],
                initialfile="video_con_texto.mp4"
            )
            
            if archivo_salida:
                video_final.write_videofile(archivo_salida, logger=None)
                self.estado_texto.config(text=f"✅ Guardado: {os.path.basename(archivo_salida)}", fg='green')
            else:
                self.estado_texto.config(text="⏸️ Cancelado", fg='orange')
            
            clip.close()
            texto.close()
            video_final.close()
            
        except Exception as e:
            self.estado_texto.config(text=f"❌ Error: {str(e)}", fg='red')
        
        self.progreso_texto.stop()
    
    def procesar_multiple_texto(self, pestana_id):
        video_path = self.obtener_video_actual(pestana_id)
        if not video_path:
            messagebox.showerror("Error", "Selecciona un video")
            return
        
        if not self.lista_textos:
            messagebox.showerror("Error", "Añade al menos un texto")
            return
        
        threading.Thread(target=self._procesar_multiple_thread, args=(video_path,), daemon=True).start()
    
    def _procesar_multiple_thread(self, video_path):
        self.progreso_multiple.start()
        self.estado_multiple.config(text="⏳ Procesando...", fg='orange')
        
        try:
            clip = VideoFileClip(video_path)
            textos_clips = []
            
            for item in self.lista_textos:
                # Crear texto con su TAMAÑO individual
                texto = TextClip(
                    font=self.obtener_ruta_fuente("Arial"),
                    text=item['texto'],
                    font_size=item['tamaño'],  # Usar el tamaño guardado
                    color='white',
                    stroke_color='black',
                    stroke_width=2
                ).with_duration(item['duracion']).with_start(item['inicio'])
                
                # Posicionar con su POSICIÓN individual
                if item['posicion'] == 'center':
                    texto = texto.with_position(('center', 'center'))
                elif item['posicion'] == 'top':
                    texto = texto.with_position(('center', 50))
                elif item['posicion'] == 'bottom':
                    texto = texto.with_position(('center', clip.h - 100))
                elif item['posicion'] == 'left':
                    texto = texto.with_position((50, 'center'))
                elif item['posicion'] == 'right':
                    texto = texto.with_position((clip.w - 200, 'center'))
                
                textos_clips.append(texto)
            
            todos_clips = [clip] + textos_clips
            video_final = CompositeVideoClip(todos_clips)
            
            archivo_salida = filedialog.asksaveasfilename(
                defaultextension=".mp4",
                filetypes=[("MP4", "*.mp4")],
                initialfile="video_multiple_textos.mp4"
            )
            
            if archivo_salida:
                video_final.write_videofile(archivo_salida, logger=None)
                self.estado_multiple.config(text=f"✅ Guardado: {os.path.basename(archivo_salida)}", fg='green')
            else:
                self.estado_multiple.config(text="⏸️ Cancelado", fg='orange')
            
            clip.close()
            for tc in textos_clips:
                tc.close()
            video_final.close()
            
        except Exception as e:
            self.estado_multiple.config(text=f"❌ Error: {str(e)}", fg='red')
        
        self.progreso_multiple.stop()
    
    def procesar_efectos(self, pestana_id):
        video_path = self.obtener_video_actual(pestana_id)
        if not video_path:
            messagebox.showerror("Error", "Selecciona un video")
            return
        
        threading.Thread(target=self._procesar_efectos_thread, args=(video_path,), daemon=True).start()
    
    def _procesar_efectos_thread(self, video_path):
        self.progreso_efectos.start()
        self.estado_efectos.config(text="⏳ Procesando...", fg='orange')
        
        try:
            clip = VideoFileClip(video_path)
            
            if self.fade_in_var.get():
                fade_dur = float(self.fade_in_duracion.get())
                clip = clip.with_effects([FadeIn(fade_dur)])
            
            if self.fade_out_var.get():
                fade_dur = float(self.fade_out_duracion.get())
                clip = clip.with_effects([FadeOut(fade_dur)])
            
            archivo_salida = filedialog.asksaveasfilename(
                defaultextension=".mp4",
                filetypes=[("MP4", "*.mp4")],
                initialfile="video_con_efectos.mp4"
            )
            
            if archivo_salida:
                clip.write_videofile(archivo_salida, logger=None)
                self.estado_efectos.config(text=f"✅ Guardado: {os.path.basename(archivo_salida)}", fg='green')
            else:
                self.estado_efectos.config(text="⏸️ Cancelado", fg='orange')
            
            clip.close()
            
        except Exception as e:
            self.estado_efectos.config(text=f"❌ Error: {str(e)}", fg='red')
        
        self.progreso_efectos.stop()
    
    def procesar_musica(self, pestana_id):
        video_path = self.obtener_video_actual(pestana_id)
        if not video_path:
            messagebox.showerror("Error", "Selecciona un video")
            return
        
        if not self.audio_path:
            messagebox.showerror("Error", "Selecciona un archivo de música")
            return
        
        threading.Thread(target=self._procesar_musica_thread, args=(video_path,), daemon=True).start()
    
    def _procesar_musica_thread(self, video_path):
        self.progreso_musica.start()
        self.estado_musica.config(text="⏳ Procesando...", fg='orange')
        
        try:
            video = VideoFileClip(video_path)
            audio = AudioFileClip(self.audio_path)
            
            audio = audio.with_volume_scaled(self.volumen.get() / 100.0)
            
            if audio.duration > video.duration:
                audio = audio.subclipped(0, video.duration)
            
            if self.mantener_audio_original.get() and video.audio is not None:
                from moviepy.audio.CompositeAudioClip import CompositeAudioClip
                audio_original = video.audio.with_volume_scaled(0.3)
                audio_final = CompositeAudioClip([audio_original, audio])
            else:
                audio_final = audio
            
            video_con_audio = video.with_audio(audio_final)
            
            archivo_salida = filedialog.asksaveasfilename(
                defaultextension=".mp4",
                filetypes=[("MP4", "*.mp4")],
                initialfile="video_con_musica.mp4"
            )
            
            if archivo_salida:
                video_con_audio.write_videofile(archivo_salida, logger=None)
                self.estado_musica.config(text=f"✅ Guardado: {os.path.basename(archivo_salida)}", fg='green')
            else:
                self.estado_musica.config(text="⏸️ Cancelado", fg='orange')
            
            video.close()
            audio.close()
            
        except Exception as e:
            self.estado_musica.config(text=f"❌ Error: {str(e)}", fg='red')
        
        self.progreso_musica.stop()
    
    def procesar_recortar(self, pestana_id):
        video_path = self.obtener_video_actual(pestana_id)
        if not video_path:
            messagebox.showerror("Error", "Selecciona un video")
            return
        
        threading.Thread(target=self._procesar_recortar_thread, args=(video_path,), daemon=True).start()
    
    def _procesar_recortar_thread(self, video_path):
        self.progreso_recortar.start()
        self.estado_recortar.config(text="⏳ Procesando...", fg='orange')
        
        try:
            clip = VideoFileClip(video_path)
            
            inicio = float(self.recortar_inicio.get())
            
            if self.recortar_fin.get().strip():
                fin = float(self.recortar_fin.get())
            else:
                fin = clip.duration
            
            clip_recortado = clip.subclipped(inicio, fin)
            
            archivo_salida = filedialog.asksaveasfilename(
                defaultextension=".mp4",
                filetypes=[("MP4", "*.mp4")],
                initialfile="video_recortado.mp4"
            )
            
            if archivo_salida:
                clip_recortado.write_videofile(archivo_salida, logger=None)
                self.estado_recortar.config(text=f"✅ Guardado: {os.path.basename(archivo_salida)}", fg='green')
            else:
                self.estado_recortar.config(text="⏸️ Cancelado", fg='orange')
            
            clip.close()
            clip_recortado.close()
            
        except Exception as e:
            self.estado_recortar.config(text=f"❌ Error: {str(e)}", fg='red')
        
        self.progreso_recortar.stop()
    
    def procesar_caratulas(self, pestana_id):
        video_path = self.obtener_video_actual(pestana_id)
        if not video_path:
            messagebox.showerror("Error", "Selecciona un video")
            return
        
        if not self.caratula_path and not self.contra_path:
            messagebox.showerror("Error", "Selecciona al menos una imagen")
            return
        
        threading.Thread(target=self._procesar_caratulas_thread, args=(video_path,), daemon=True).start()
    
    def _procesar_caratulas_thread(self, video_path):
        self.progreso_caratulas.start()
        self.estado_caratulas.config(text="⏳ Procesando...", fg='orange')
        
        try:
            clip = VideoFileClip(video_path)
            clips = []
            
            if self.caratula_path:
                caratula = (ImageClip(self.caratula_path)
                           .with_duration(float(self.caratula_duracion.get()))
                           .resized(new_size=clip.size))
                clips.append(caratula)
            
            clips.append(clip)
            
            if self.contra_path:
                contra = (ImageClip(self.contra_path)
                         .with_duration(float(self.contra_duracion.get()))
                         .resized(new_size=clip.size))
                clips.append(contra)
            
            video_final = concatenate_videoclips(clips)
            
            archivo_salida = filedialog.asksaveasfilename(
                defaultextension=".mp4",
                filetypes=[("MP4", "*.mp4")],
                initialfile="video_con_caratulas.mp4"
            )
            
            if archivo_salida:
                video_final.write_videofile(archivo_salida, logger=None)
                self.estado_caratulas.config(text=f"✅ Guardado: {os.path.basename(archivo_salida)}", fg='green')
            else:
                self.estado_caratulas.config(text="⏸️ Cancelado", fg='orange')
            
            for c in clips:
                c.close()
            
        except Exception as e:
            self.estado_caratulas.config(text=f"❌ Error: {str(e)}", fg='red')
        
        self.progreso_caratulas.stop()

if __name__ == "__main__":
    root = tk.Tk()
    app = EditorVideoCompleto(root)
    root.mainloop()