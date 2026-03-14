
# -*- coding: utf-8 -*-

import tkinter as tk
from tkinter import ttk, filedialog, colorchooser
import threading
import os
from moviepy import VideoFileClip, TextClip, CompositeVideoClip

class AñadirTextoVideo:
    def __init__(self, root):
        self.root = root
        self.root.title("📝 Añadir Texto a Video")
        ancho = 550
        alto = 550
        margen_superior = 20
        
        ancho_pantalla = self.root.winfo_screenwidth()
        x = (ancho_pantalla - ancho) // 2
        y = margen_superior
        
        self.root.geometry(f'{ancho}x{alto}+{x}+{y}')
        
        self.video_path = None
        self.crear_interfaz()
    
    def centrar_ventana(self):
        self.root.update_idletasks()
        ancho = 550
        alto = 550
        x = (self.root.winfo_screenwidth() // 2) - (ancho // 2)
        y = (self.root.winfo_screenheight() // 2) - (alto // 2)
        self.root.geometry(f'{ancho}x{alto}+{x}+{y}')
    
    def crear_interfaz(self):
        # Título
        tk.Label(self.root, text="📝 AÑADIR TEXTO A VIDEO", 
                font=('Arial', 16, 'bold'), fg='#4CAF50').pack(pady=10)
        
        # Selector de video
        video_frame = tk.Frame(self.root)
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
        tk.Frame(self.root, height=1, bg='#ccc').pack(fill=tk.X, padx=20, pady=15)
        
        # Configuración del texto
        config_frame = tk.Frame(self.root)
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
        
        # Color
        tk.Label(config_frame, text="🎨 Color:", 
                font=('Arial', 11)).grid(row=3, column=0, sticky='w', pady=5)
        
        self.color_btn = tk.Button(config_frame, text="Seleccionar Color", 
                                  bg='#2196F3', fg='white',
                                  command=self.seleccionar_color)
        self.color_btn.grid(row=3, column=1, pady=5, padx=5)
        
        self.color_label = tk.Label(config_frame, text="white", bg='white', width=10)
        self.color_label.grid(row=3, column=2, pady=5)
        self.color_seleccionado = 'white'
        
        # Color de borde
        tk.Label(config_frame, text="⚫ Borde:", 
                font=('Arial', 11)).grid(row=4, column=0, sticky='w', pady=5)
        
        self.borde_var = tk.BooleanVar(value=True)
        tk.Checkbutton(config_frame, text="Añadir borde negro", 
                      variable=self.borde_var).grid(row=4, column=1, columnspan=2, sticky='w')
        
        # Duración
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
        tk.Button(self.root, text="📝 AÑADIR TEXTO", 
                 bg='#4CAF50', fg='white', font=('Arial', 14, 'bold'),
                 padx=30, pady=10, cursor='hand2',
                 command=self.procesar).pack(pady=20)
        
        # Barra de progreso
        self.progreso = ttk.Progressbar(self.root, mode='indeterminate')
        self.progreso.pack(fill=tk.X, padx=20, pady=5)
        
        self.estado_label = tk.Label(self.root, text="Listo", fg='green')
        self.estado_label.pack()
    
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
            except:
                self.video_info.config(text="No se pudo leer info del video")
    
    def seleccionar_color(self):
        color = colorchooser.askcolor(title="Seleccionar color")[1]
        if color:
            self.color_seleccionado = color
            self.color_label.config(bg=color, text="")
    
    def procesar(self):
        if not self.video_path:
            messagebox.showerror("Error", "Selecciona un video")
            return
        
        if not self.texto_entry.get():
            messagebox.showerror("Error", "Escribe un texto")
            return
        
        threading.Thread(target=self.añadir_texto, daemon=True).start()
    
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
            
            # Crear texto
            texto = TextClip(
                text=self.texto_entry.get(),
                font_size=self.tamaño.get(),
                color=self.color_seleccionado,
                font="Arial",
                stroke_color='black' if self.borde_var.get() else None,
                stroke_width=2 if self.borde_var.get() else 0
            ).with_duration(duracion_texto).with_position(self.posicion.get())
            
            # Componer
            if duracion_texto < clip.duration:
                # Si el texto dura menos, ponerlo al inicio
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

if __name__ == "__main__":
    root = tk.Tk()
    app = AñadirTextoVideo(root)
    root.mainloop()