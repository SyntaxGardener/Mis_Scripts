# -*- coding: utf-8 -*-

import tkinter as tk
from tkinter import ttk, filedialog, colorchooser, messagebox
import threading
import os
# Importaciones correctas para MoviePy 2.2.1
from moviepy import VideoFileClip, TextClip, CompositeVideoClip, ImageClip, concatenate_videoclips

class AñadirTextoVideo:
    def __init__(self, root):
        self.root = root
        self.root.title("📝 Añadir Texto o Carátulas a Video")
        ancho = 600
        alto = 700
        margen_superior = 20
        
        ancho_pantalla = self.root.winfo_screenwidth()
        x = (ancho_pantalla - ancho) // 2
        y = margen_superior
        
        self.root.geometry(f'{ancho}x{alto}+{x}+{y}')
        
        self.video_path = None
        self.caratula_path = None
        self.contra_path = None
        self.color_seleccionado = 'white'
        
        # Obtener la ruta de la fuente incluida
        self.ruta_fuente = self.obtener_ruta_fuente()
        
        self.crear_interfaz()
    
    def obtener_ruta_fuente(self):
        """Busca la fuente en la carpeta fonts/ del script"""
        # Obtener la ruta del directorio donde está el script
        ruta_script = os.path.dirname(os.path.abspath(__file__))
        
        # Posibles nombres de fuente (para que funcione con diferentes descargas)
        posibles_fuentes = [
            os.path.join(ruta_script, "fonts", "OpenSans.ttf"),
            os.path.join(ruta_script, "fonts", "OpenSans-Regular.ttf"),
            os.path.join(ruta_script, "fonts", "arial.ttf"),
            os.path.join(ruta_script, "fonts", "LiberationSans-Regular.ttf"),
            os.path.join(ruta_script, "fonts", "DejaVuSans.ttf"),
        ]
        
        for fuente in posibles_fuentes:
            if os.path.exists(fuente):
                return fuente
        
        # Si no encuentra ninguna, mostrar advertencia y usar None
        messagebox.showwarning("Fuente no encontrada", 
                               "No se encontró ninguna fuente en la carpeta 'fonts'.\n"
                               "El texto podría no mostrarse correctamente.")
        return None
    
    def crear_interfaz(self):
        # Crear pestañas
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill='both', expand=True, padx=10, pady=5)
        
        # Pestaña 1: Añadir texto
        self.tab_texto = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_texto, text="📝 Añadir Texto")
        self.crear_pestana_texto()
        
        # Pestaña 2: Carátula/Contraportada con imágenes
        self.tab_caratula = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_caratula, text="🎬 Carátula/Contraportada")
        self.crear_pestana_caratula()
    
    def crear_pestana_texto(self):
        # Título
        tk.Label(self.tab_texto, text="📝 AÑADIR TEXTO A VIDEO", 
                font=('Arial', 16, 'bold'), fg='#4CAF50').pack(pady=10)
        
        # Mostrar fuente que se está usando
        if self.ruta_fuente:
            nombre_fuente = os.path.basename(self.ruta_fuente)
            tk.Label(self.tab_texto, text=f"✅ Usando fuente: {nombre_fuente}", 
                    fg='green', font=('Arial', 9)).pack()
        else:
            tk.Label(self.tab_texto, text="⚠️ Usando fuente del sistema (puede fallar)", 
                    fg='orange', font=('Arial', 9)).pack()
        
        # Selector de video
        video_frame = tk.Frame(self.tab_texto)
        video_frame.pack(fill=tk.X, padx=20, pady=10)
        
        tk.Label(video_frame, text="🎥 Video:", 
                font=('Arial', 11)).pack(anchor='w')
        
        btn_frame = tk.Frame(video_frame)
        btn_frame.pack(fill=tk.X, pady=5)
        
        self.video_label = tk.Label(btn_frame, text="Ningún video seleccionado", 
                                   fg='gray', width=40, anchor='w')
        self.video_label.pack(side=tk.LEFT)
        
        tk.Button(btn_frame, text="Seleccionar Video", 
                 bg='#4CAF50', fg='white', padx=15,
                 command=self.seleccionar_video).pack(side=tk.RIGHT)
        
        # Info del video
        self.video_info = tk.Label(video_frame, text="", fg='blue', font=('Arial', 9))
        self.video_info.pack(anchor='w')
        
        # Separador
        tk.Frame(self.tab_texto, height=1, bg='#ccc').pack(fill=tk.X, padx=20, pady=15)
        
        # Configuración del texto
        config_frame = tk.Frame(self.tab_texto)
        config_frame.pack(padx=20, pady=10, fill=tk.X)
        
        # Texto a añadir
        tk.Label(config_frame, text="📝 Texto:", 
                font=('Arial', 11)).grid(row=0, column=0, sticky='w', pady=5)
        
        self.texto_entry = tk.Entry(config_frame, width=30, font=('Arial', 11))
        self.texto_entry.grid(row=0, column=1, columnspan=3, pady=5, padx=5)
        self.texto_entry.insert(0, "¡Hola Mundo!")
        
        # Posición
        tk.Label(config_frame, text="📍 Posición:", 
                font=('Arial', 11)).grid(row=1, column=0, sticky='w', pady=5)
        
        self.posicion = ttk.Combobox(config_frame, 
                                     values=['center', 'top', 'bottom', 'left', 'right'],
                                     width=15)
        self.posicion.grid(row=1, column=1, pady=5, padx=5)
        self.posicion.set('center')
        
        # Tamaño
        tk.Label(config_frame, text="🔤 Tamaño:", 
                font=('Arial', 11)).grid(row=2, column=0, sticky='w', pady=5)
        
        self.tamaño = tk.Scale(config_frame, from_=20, to=100, orient=tk.HORIZONTAL, length=200)
        self.tamaño.grid(row=2, column=1, columnspan=2, pady=5, padx=5)
        self.tamaño.set(50)
        
        # Color (fila 3)
        tk.Label(config_frame, text="🎨 Color:", 
                font=('Arial', 11)).grid(row=3, column=0, sticky='w', pady=5)
        
        self.color_btn = tk.Button(config_frame, text="Seleccionar Color", 
                                  bg='#2196F3', fg='white',
                                  command=self.seleccionar_color)
        self.color_btn.grid(row=3, column=1, pady=5, padx=5)
        
        self.color_label = tk.Label(config_frame, text="white", bg='white', width=10)
        self.color_label.grid(row=3, column=2, pady=5)
        
        # Color de borde (fila 4)
        tk.Label(config_frame, text="⚫ Borde:", 
                font=('Arial', 11)).grid(row=4, column=0, sticky='w', pady=5)
        
        self.borde_var = tk.BooleanVar(value=True)
        tk.Checkbutton(config_frame, text="Añadir borde negro", 
                      variable=self.borde_var).grid(row=4, column=1, columnspan=2, sticky='w')
        
        # Duración (fila 5 y 6)
        tk.Label(config_frame, text="⏱️ Duración:", 
                font=('Arial', 11)).grid(row=5, column=0, sticky='w', pady=5)
        
        self.duracion_completa = tk.BooleanVar(value=True)
        tk.Radiobutton(config_frame, text="Video completo", 
                      variable=self.duracion_completa, value=True).grid(row=5, column=1, sticky='w')
        tk.Radiobutton(config_frame, text="Duración personalizada:", 
                      variable=self.duracion_completa, value=False).grid(row=6, column=1, sticky='w')
        
        self.duracion_entry = tk.Entry(config_frame, width=10)
        self.duracion_entry.grid(row=6, column=2, sticky='w')
        self.duracion_entry.insert(0, "5")
        self.duracion_entry.config(state='disabled')
        
        def toggle_duracion():
            if self.duracion_completa.get():
                self.duracion_entry.config(state='disabled')
            else:
                self.duracion_entry.config(state='normal')
        
        self.duracion_completa.trace('w', lambda *args: toggle_duracion())
        
        # Botón de procesar
        tk.Button(self.tab_texto, text="📝 AÑADIR TEXTO", 
                 bg='#4CAF50', fg='white', font=('Arial', 14, 'bold'),
                 padx=30, pady=10, cursor='hand2',
                 command=self.procesar_texto).pack(pady=20)
        
        # Barra de progreso
        self.progreso = ttk.Progressbar(self.tab_texto, mode='indeterminate')
        self.progreso.pack(fill=tk.X, padx=20, pady=5)
        
        self.estado_label = tk.Label(self.tab_texto, text="Listo", fg='green')
        self.estado_label.pack()
    
    def crear_pestana_caratula(self):
        # Título
        tk.Label(self.tab_caratula, text="🎬 AÑADIR CARÁTULA Y CONTRAPORTADA", 
                font=('Arial', 14, 'bold'), fg='#FF6B6B').pack(pady=10)
        
        # Frame para carátula
        frame_caratula = tk.LabelFrame(self.tab_caratula, text="Carátula (inicio)", 
                                      padx=10, pady=10, font=('Arial', 11, 'bold'))
        frame_caratula.pack(fill=tk.X, padx=20, pady=10)
        
        # Seleccionar imagen carátula
        tk.Label(frame_caratula, text="🖼️ Imagen:").grid(row=0, column=0, sticky='w', pady=5)
        
        btn_frame_caratula = tk.Frame(frame_caratula)
        btn_frame_caratula.grid(row=0, column=1, columnspan=2, sticky='w', pady=5)
        
        self.caratula_label = tk.Label(btn_frame_caratula, text="Ninguna imagen", 
                                      fg='gray', width=30, anchor='w')
        self.caratula_label.pack(side=tk.LEFT)
        
        tk.Button(btn_frame_caratula, text="Seleccionar", 
                 bg='#4CAF50', fg='white',
                 command=self.seleccionar_caratula).pack(side=tk.RIGHT, padx=5)
        
        # Duración carátula
        tk.Label(frame_caratula, text="⏱️ Duración (seg):").grid(row=1, column=0, sticky='w', pady=5)
        self.caratula_duracion = tk.Entry(frame_caratula, width=10)
        self.caratula_duracion.grid(row=1, column=1, pady=5, padx=5, sticky='w')
        self.caratula_duracion.insert(0, "3")
        
        # Separador
        ttk.Separator(self.tab_caratula, orient='horizontal').pack(fill=tk.X, padx=20, pady=10)
        
        # Frame para contraportada
        frame_contra = tk.LabelFrame(self.tab_caratula, text="Contraportada (final)", 
                                    padx=10, pady=10, font=('Arial', 11, 'bold'))
        frame_contra.pack(fill=tk.X, padx=20, pady=10)
        
        # Seleccionar imagen contraportada
        tk.Label(frame_contra, text="🖼️ Imagen:").grid(row=0, column=0, sticky='w', pady=5)
        
        btn_frame_contra = tk.Frame(frame_contra)
        btn_frame_contra.grid(row=0, column=1, columnspan=2, sticky='w', pady=5)
        
        self.contra_label = tk.Label(btn_frame_contra, text="Ninguna imagen", 
                                    fg='gray', width=30, anchor='w')
        self.contra_label.pack(side=tk.LEFT)
        
        tk.Button(btn_frame_contra, text="Seleccionar", 
                 bg='#4CAF50', fg='white',
                 command=self.seleccionar_contra).pack(side=tk.RIGHT, padx=5)
        
        # Duración contraportada
        tk.Label(frame_contra, text="⏱️ Duración (seg):").grid(row=1, column=0, sticky='w', pady=5)
        self.contra_duracion = tk.Entry(frame_contra, width=10)
        self.contra_duracion.grid(row=1, column=1, pady=5, padx=5, sticky='w')
        self.contra_duracion.insert(0, "3")
        
        # Opciones adicionales
        opciones_frame = tk.LabelFrame(self.tab_caratula, text="Opciones", 
                                      padx=10, pady=10, font=('Arial', 11, 'bold'))
        opciones_frame.pack(fill=tk.X, padx=20, pady=10)
        
        self.usar_mismo_video = tk.BooleanVar(value=True)
        tk.Checkbutton(opciones_frame, text="Usar el mismo video seleccionado en la pestaña 'Añadir Texto'", 
                      variable=self.usar_mismo_video).pack(anchor='w')
        
        # Botón procesar
        tk.Button(self.tab_caratula, text="🎬 AÑADIR IMÁGENES", 
                 bg='#FF6B6B', fg='white', font=('Arial', 12, 'bold'),
                 padx=20, pady=10, cursor='hand2',
                 command=self.procesar_caratula).pack(pady=20)
        
        # Barra de progreso para carátula
        self.progreso_caratula = ttk.Progressbar(self.tab_caratula, mode='indeterminate')
        self.progreso_caratula.pack(fill=tk.X, padx=20, pady=5)
        
        self.estado_caratula_label = tk.Label(self.tab_caratula, text="Listo", fg='green')
        self.estado_caratula_label.pack()
    
    def seleccionar_video(self):
        archivo = filedialog.askopenfilename(
            title="Seleccionar Video",
            filetypes=[("Videos", "*.mp4 *.avi *.mov *.mkv"), ("Todos", "*.*")]
        )
        if archivo:
            self.video_path = archivo
            self.video_label.config(text=os.path.basename(archivo), fg='black')
            
            try:
                clip = VideoFileClip(archivo)
                info = f"Duración: {clip.duration:.2f}s | {clip.size[0]}x{clip.size[1]}"
                self.video_info.config(text=info)
                clip.close()
            except Exception as e:
                self.video_info.config(text=f"Error: {str(e)}")
    
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
        color = colorchooser.askcolor(title="Seleccionar color")[1]
        if color:
            self.color_seleccionado = color
            self.color_label.config(bg=color, text="")
    
    def procesar_texto(self):
        if not self.video_path:
            messagebox.showerror("Error", "Selecciona un video")
            return
        
        if not self.texto_entry.get():
            messagebox.showerror("Error", "Escribe un texto")
            return
        
        threading.Thread(target=self.añadir_texto, daemon=True).start()
    
    def procesar_caratula(self):
        # Determinar qué video usar
        video_a_usar = self.video_path if self.usar_mismo_video.get() else None
        
        if not video_a_usar:
            # Si no quiere usar el mismo o no hay, seleccionar uno nuevo
            video_a_usar = filedialog.askopenfilename(
                title="Seleccionar video",
                filetypes=[("Videos", "*.mp4 *.avi *.mov *.mkv"), ("Todos", "*.*")]
            )
        
        if not video_a_usar:
            messagebox.showerror("Error", "Selecciona un video")
            return
        
        if not self.caratula_path and not self.contra_path:
            messagebox.showerror("Error", "Selecciona al menos una imagen")
            return
        
        self.video_path_caratula = video_a_usar
        threading.Thread(target=self.añadir_caratula_contra, daemon=True).start()
    
    def añadir_texto(self):
        self.progreso.start()
        self.estado_label.config(text="Procesando...", fg='orange')
        
        try:
            # Cargar video
            clip = VideoFileClip(self.video_path)
            
            # Determinar duración del texto
            if self.duracion_completa.get():
                duracion_texto = clip.duration
            else:
                duracion_texto = float(self.duracion_entry.get())
            
            # Verificar que tenemos una fuente
            if not self.ruta_fuente:
                # Si no hay fuente incluida, intentar con Arial
                fuente_a_usar = "Arial"
            else:
                fuente_a_usar = self.ruta_fuente
            
            # Crear texto con la fuente incluida y borde incluido en el constructor
            texto = TextClip(
                font=fuente_a_usar,
                text=self.texto_entry.get(),
                font_size=self.tamaño.get(),
                color=self.color_seleccionado,
                stroke_color='black' if self.borde_var.get() else None,
                stroke_width=2 if self.borde_var.get() else 0
            ).with_duration(duracion_texto)
            
            # Posicionar texto
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
            
            # Componer
            if duracion_texto < clip.duration:
                texto = texto.with_start(0)
            
            video_final = CompositeVideoClip([clip, texto])
            
            # Guardar
            archivo_salida = filedialog.asksaveasfilename(
                defaultextension=".mp4",
                filetypes=[("MP4", "*.mp4")],
                initialfile="video_con_texto.mp4"
            )
            
            if archivo_salida:
                video_final.write_videofile(archivo_salida, logger=None)
                self.estado_label.config(text=f"✅ Guardado en {os.path.basename(archivo_salida)}", fg='green')
            else:
                self.estado_label.config(text="Operación cancelada", fg='orange')
            
            # Limpiar
            clip.close()
            texto.close()
            video_final.close()
            
        except Exception as e:
            self.estado_label.config(text=f"❌ Error: {str(e)}", fg='red')
        
        self.progreso.stop()
    
    def añadir_caratula_contra(self):
        self.progreso_caratula.start()
        self.estado_caratula_label.config(text="Procesando...", fg='orange')
        
        try:
            # Cargar video original
            clip = VideoFileClip(self.video_path_caratula)
            
            clips = []
            
            # Añadir carátula si existe
            if self.caratula_path:
                caratula = (ImageClip(self.caratula_path)
                           .with_duration(float(self.caratula_duracion.get()))
                           .resized(new_size=clip.size))
                clips.append(caratula)
            
            # Añadir video
            clips.append(clip)
            
            # Añadir contraportada si existe
            if self.contra_path:
                contra = (ImageClip(self.contra_path)
                         .with_duration(float(self.contra_duracion.get()))
                         .resized(new_size=clip.size))
                clips.append(contra)
            
            # Combinar todo
            video_final = concatenate_videoclips(clips)
            
            # Guardar
            archivo_salida = filedialog.asksaveasfilename(
                defaultextension=".mp4",
                filetypes=[("MP4", "*.mp4")],
                initialfile="video_con_imagenes.mp4"
            )
            
            if archivo_salida:
                video_final.write_videofile(archivo_salida, logger=None)
                self.estado_caratula_label.config(text=f"✅ Guardado en {os.path.basename(archivo_salida)}", fg='green')
            else:
                self.estado_caratula_label.config(text="Operación cancelada", fg='orange')
            
            # Limpiar
            for c in clips:
                c.close()
            
        except Exception as e:
            self.estado_caratula_label.config(text=f"❌ Error: {str(e)}", fg='red')
        
        self.progreso_caratula.stop()

if __name__ == "__main__":
    root = tk.Tk()
    app = AñadirTextoVideo(root)
    root.mainloop()