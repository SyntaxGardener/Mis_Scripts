# -*- coding: utf-8 -*-

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import os
import sys
import traceback

# ✅ ELIMINA TODOS LOS PRINT E INPUT
# No uses print() en archivos .pyw porque crean consola

try:
    from moviepy import VideoFileClip
    MOVIEPY_OK = True
except ImportError:
    MOVIEPY_OK = False

class CortadorVideo:
    def __init__(self, root):
        self.root = root
        self.root.title("✂️ Cortador de Video")
        
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
        
        self.video_path = None
        self.duracion_actual = None
        
        if not MOVIEPY_OK:
            messagebox.showerror("Error", 
                               "MoviePy no está instalado.\nEjecuta: pip install moviepy")
            root.destroy()
            return
        
        self.crear_interfaz()
    
    def configurar_ventana(self):
        """Configura la ventana centrada y a 20px del borde superior"""
        ancho = 650
        alto = 580
        margen_superior = 20
        
        ancho_pantalla = self.root.winfo_screenwidth()
        x = (ancho_pantalla - ancho) // 2
        y = margen_superior
        
        self.root.geometry(f'{ancho}x{alto}+{x}+{y}')
        self.root.minsize(600, 500)
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
                text="✂️ CORTADOR DE VIDEO", 
                font=('Arial', 20, 'bold'),
                fg=self.colors['accent'],
                bg=self.colors['bg']).pack()
        
        # === SELECCIÓN DE VIDEO ===
        video_frame = self.crear_frame_con_borde(main_frame, "1. SELECCIONA UN VIDEO")
        video_frame.pack(fill=tk.X, pady=10)
        
        # Botón seleccionar video
        btn_frame = tk.Frame(video_frame, bg=self.colors['frame_bg'])
        btn_frame.pack(fill=tk.X, pady=5)
        
        self.video_label = tk.Label(btn_frame, 
                                   text="📁 Ningún video seleccionado", 
                                   fg='#999999',
                                   bg=self.colors['frame_bg'],
                                   font=('Arial', 10),
                                   anchor='w')
        self.video_label.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        self.btn_seleccionar = tk.Button(btn_frame,
                                        text="Seleccionar Video",
                                        bg=self.colors['accent'],
                                        fg=self.colors['button_text'],
                                        font=('Arial', 10, 'bold'),
                                        padx=15,
                                        pady=5,
                                        relief='flat',
                                        cursor='hand2',
                                        command=self.seleccionar_video)
        self.btn_seleccionar.pack(side=tk.RIGHT)
        
        # Efecto hover
        self.btn_seleccionar.bind('<Enter>', lambda e: e.widget.config(bg=self.colors['accent_light']))
        self.btn_seleccionar.bind('<Leave>', lambda e: e.widget.config(bg=self.colors['accent']))
        
        # Información del video
        self.info_frame = tk.Frame(video_frame, bg=self.colors['info_bg'], height=40)
        self.info_label = tk.Label(self.info_frame, 
                                  text="",
                                  bg=self.colors['info_bg'],
                                  fg='#1976D2',
                                  font=('Arial', 10),
                                  padx=10,
                                  pady=5)
        self.info_label.pack(fill=tk.BOTH, expand=True)
        
        # === TIEMPOS DE CORTE ===
        tiempo_frame = self.crear_frame_con_borde(main_frame, "2. DEFINE LOS TIEMPOS")
        tiempo_frame.pack(fill=tk.X, pady=10)
        
        # Controles
        controles_frame = tk.Frame(tiempo_frame, bg=self.colors['frame_bg'])
        controles_frame.pack(pady=15)
        
        # Inicio
        tk.Label(controles_frame, 
                text="Inicio (s):", 
                font=('Arial', 11),
                bg=self.colors['frame_bg'],
                fg=self.colors['fg']).grid(row=0, column=0, padx=5, pady=5)
        
        self.inicio_entry = tk.Entry(controles_frame, 
                                    width=8, 
                                    font=('Arial', 12),
                                    bg='#ffffff',
                                    relief='solid',
                                    bd=1)
        self.inicio_entry.grid(row=0, column=1, padx=5, pady=5)
        self.inicio_entry.insert(0, "0")
        
        # Fin
        tk.Label(controles_frame, 
                text="Fin (s):", 
                font=('Arial', 11),
                bg=self.colors['frame_bg'],
                fg=self.colors['fg']).grid(row=0, column=2, padx=5, pady=5)
        
        self.fin_entry = tk.Entry(controles_frame, 
                                 width=8, 
                                 font=('Arial', 12),
                                 bg='#ffffff',
                                 relief='solid',
                                 bd=1)
        self.fin_entry.grid(row=0, column=3, padx=5, pady=5)
        self.fin_entry.insert(0, "10")
        
        # Ayuda
        tk.Label(tiempo_frame,
                text="💡 Ejemplo: 0 a 10 = primeros 10 segundos", 
                fg='#666666',
                bg=self.colors['frame_bg'],
                font=('Arial', 9)).pack(pady=5)
        
        self.duracion_label = tk.Label(tiempo_frame,
                                      text="",
                                      fg='#666666',
                                      bg=self.colors['frame_bg'],
                                      font=('Arial', 9))
        self.duracion_label.pack()
        
        # === BOTÓN DE PROCESAR ===
        boton_frame = tk.Frame(main_frame, bg=self.colors['bg'])
        boton_frame.pack(pady=20)
        
        self.procesar_btn = tk.Button(boton_frame, 
                                      text="✂️ CORTAR VIDEO", 
                                      bg=self.colors['accent'], 
                                      fg=self.colors['button_text'], 
                                      font=('Arial', 14, 'bold'),
                                      padx=40, 
                                      pady=12,
                                      relief='flat',
                                      cursor='hand2',
                                      state='disabled',
                                      command=self.iniciar_corte)
        self.procesar_btn.pack()
        
        # Efecto hover
        self.procesar_btn.bind('<Enter>', self.on_enter_procesar)
        self.procesar_btn.bind('<Leave>', self.on_leave_procesar)
        
        # === BARRA DE PROGRESO ===
        progreso_frame = tk.Frame(main_frame, bg=self.colors['bg'])
        progreso_frame.pack(fill=tk.X, pady=10)
        
        self.progreso = ttk.Progressbar(progreso_frame, mode='indeterminate', length=400)
        self.progreso.pack()
        
        self.estado_label = tk.Label(progreso_frame, 
                                    text="✅ Listo", 
                                    fg=self.colors['success'],
                                    bg=self.colors['bg'],
                                    font=('Arial', 10))
        self.estado_label.pack(pady=5)
    
    def on_enter_procesar(self, event):
        if self.procesar_btn['state'] == 'normal':
            event.widget.config(bg=self.colors['accent_light'])
    
    def on_leave_procesar(self, event):
        if self.procesar_btn['state'] == 'normal':
            event.widget.config(bg=self.colors['accent'])
    
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
    
    def seleccionar_video(self):
        archivo = filedialog.askopenfilename(
            title="Selecciona un video",
            filetypes=[
                ("Videos", "*.mp4 *.avi *.mov *.mkv *.webm"),
                ("MP4", "*.mp4"),
                ("AVI", "*.avi"),
                ("MOV", "*.mov"),
                ("MKV", "*.mkv"),
                ("Todos", "*.*")
            ]
        )
        
        if archivo:
            self.video_path = archivo
            nombre = os.path.basename(archivo)
            self.video_label.config(text=f"📹 {nombre}", fg=self.colors['fg'])
            
            try:
                clip = VideoFileClip(archivo)
                duracion = clip.duration
                tamaño = clip.size
                fps = clip.fps
                self.duracion_actual = duracion
                clip.close()
                
                info_text = f"Duración: {duracion:.1f}s  |  {tamaño[0]}x{tamaño[1]}  |  {fps:.1f} fps"
                self.info_label.config(text=info_text)
                
                if not self.info_frame.winfo_ismapped():
                    self.info_frame.pack(fill=tk.X, pady=(10, 0))
                
                self.fin_entry.delete(0, tk.END)
                self.fin_entry.insert(0, f"{duracion:.1f}")
                
                self.duracion_label.config(text=f"Duración total: {duracion:.1f} segundos")
                self.procesar_btn.config(state='normal', bg=self.colors['accent'])
                
            except Exception as e:
                self.info_label.config(text="❌ Error al leer el video")
                self.info_frame.pack(fill=tk.X, pady=(10, 0))
                messagebox.showerror("Error", f"No se pudo leer el video")
    
    def iniciar_corte(self):
        hilo = threading.Thread(target=self.cortar_video)
        hilo.daemon = True
        hilo.start()
    
    def cortar_video(self):
        try:
            self.procesar_btn.config(state='disabled', bg='#cccccc')
            self.progreso.start()
            self.estado_label.config(text="⏳ Procesando...", fg=self.colors['warning'])
            
            inicio = float(self.inicio_entry.get())
            fin = float(self.fin_entry.get())
            
            if inicio >= fin:
                raise ValueError("El inicio debe ser menor que el fin")
            
            clip = VideoFileClip(self.video_path)
            
            if inicio < 0 or fin > clip.duration:
                raise ValueError(f"Tiempos fuera de rango (0-{clip.duration:.1f}s)")
            
            fragmento = clip.subclipped(inicio, fin)
            
            archivo_salida = filedialog.asksaveasfilename(
                title="Guardar video",
                defaultextension=".mp4",
                filetypes=[("MP4", "*.mp4")],
                initialfile="video_cortado.mp4"
            )
            
            if archivo_salida:
                self.estado_label.config(text="💾 Guardando...", fg=self.colors['warning'])
                fragmento.write_videofile(archivo_salida, logger=None)
                self.estado_label.config(text=f"✅ Guardado", fg=self.colors['success'])
                messagebox.showinfo("Éxito", "Video guardado correctamente")
            else:
                self.estado_label.config(text="⏸️ Cancelado", fg=self.colors['warning'])
            
            fragmento.close()
            clip.close()
            
        except Exception as e:
            self.estado_label.config(text=f"❌ Error", fg=self.colors['error'])
            messagebox.showerror("Error", str(e))
        
        finally:
            self.progreso.stop()
            if self.video_path:
                self.procesar_btn.config(state='normal', bg=self.colors['accent'])

if __name__ == "__main__":
    try:
        root = tk.Tk()
        app = CortadorVideo(root)
        root.mainloop()
    except Exception as e:
        messagebox.showerror("Error fatal", f"Error al iniciar:\n{e}")