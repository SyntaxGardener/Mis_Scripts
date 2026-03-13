#!/usr/bin/env python
# -*- coding: utf-8 -*-

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import os
from pathlib import Path

try:
    from moviepy import VideoFileClip, AudioFileClip, ImageClip, TextClip
    from moviepy import CompositeVideoClip, concatenate_videoclips
    MOVIEPY_AVAILABLE = True
except ImportError as e:
    MOVIEPY_AVAILABLE = False
    print(f"Error importando moviepy: {e}")

class EditorVideoApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Editor de Video con MoviePy")
        self.root.geometry("1000x650")
        self.root.minsize(900, 550)
        
        # Configurar estilo
        self.style = ttk.Style()
        self.style.theme_use('clam')
        
        # Colores personalizados
        self.colors = {
            'bg': '#2b2b2b',
            'fg': '#ffffff',
            'select': '#404040',
            'accent': '#4CAF50',
            'menu_bg': '#333333',
            'content_bg': '#3c3c3c'
        }
        
        self.style.configure('Menu.TButton', 
                            padding=10, 
                            relief='flat',
                            background=self.colors['menu_bg'],
                            foreground='white',
                            font=('Arial', 11))
        
        self.style.map('Menu.TButton',
                      background=[('selected', self.colors['accent']),
                                 ('active', '#555555')])
        
        self.style.configure('Content.TLabelframe',
                            background=self.colors['content_bg'],
                            foreground='white')
        
        self.style.configure('Content.TLabelframe.Label',
                            foreground='white',
                            font=('Arial', 12, 'bold'))
        
        # Variables de estado
        self.archivo_video = None
        self.archivos_concatenar = []
        self.archivos_imagenes = []
        self.archivo_audio = None
        self.procesando = False
        self.clip_actual = None
        self.current_tool = "inicio"
        
        self.crear_interfaz()
        
        # Verificar moviepy
        if not MOVIEPY_AVAILABLE:
            messagebox.showerror(
                "Error de dependencia",
                "MoviePy no está instalado correctamente.\n"
                "Instálalo con: pip install moviepy"
            )
    
    def crear_interfaz(self):
        """Crea la interfaz con menú lateral"""
        
        # Frame principal dividido en dos partes
        main_panel = ttk.Frame(self.root)
        main_panel.pack(fill=tk.BOTH, expand=True)
        
        # ===== MENÚ LATERAL IZQUIERDO =====
        menu_frame = tk.Frame(main_panel, bg=self.colors['menu_bg'], width=200)
        menu_frame.pack(side=tk.LEFT, fill=tk.Y)
        menu_frame.pack_propagate(False)
        
        # Título del menú
        titulo = tk.Label(menu_frame, 
                         text="🎬 EDITOR VIDEO", 
                         bg=self.colors['menu_bg'],
                         fg=self.colors['accent'],
                         font=('Arial', 14, 'bold'),
                         pady=20)
        titulo.pack(fill=tk.X)
        
        # Botones del menú
        self.menu_buttons = {}
        
        opciones_menu = [
            ("🏠 Inicio", "inicio"),
            ("📁 Archivos", "archivos"),
            ("✂️ Cortar", "cortar"),
            ("🎵 Extraer Audio", "audio"),
            ("🔗 Concatenar", "concatenar"),
            ("🖼️ Fotos a Video", "fotos"),
            ("📝 Añadir Texto", "texto"),
            ("⚡ Efectos", "efectos")
        ]
        
        for texto, comando in opciones_menu:
            btn = tk.Button(menu_frame,
                          text=texto,
                          bg=self.colors['menu_bg'],
                          fg='white',
                          bd=0,
                          font=('Arial', 11),
                          padx=20,
                          pady=10,
                          anchor='w',
                          cursor='hand2',
                          command=lambda x=comando: self.cambiar_herramienta(x))
            btn.pack(fill=tk.X)
            self.menu_buttons[comando] = btn
        
        # Separador
        tk.Frame(menu_frame, bg='#555555', height=1).pack(fill=tk.X, pady=10)
        
        # Barra de estado rápida en menú
        self.menu_estado = tk.Label(menu_frame,
                                   text="✅ Listo",
                                   bg=self.colors['menu_bg'],
                                   fg='#4CAF50',
                                   font=('Arial', 10),
                                   pady=10)
        self.menu_estado.pack(side=tk.BOTTOM, fill=tk.X)
        
        # ===== CONTENEDOR DERECHO =====
        self.content_frame = tk.Frame(main_panel, bg=self.colors['content_bg'])
        self.content_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        # Barra superior del contenido
        self.header_frame = tk.Frame(self.content_frame, 
                                    bg=self.colors['content_bg'],
                                    height=50)
        self.header_frame.pack(fill=tk.X, padx=20, pady=(20, 0))
        
        self.header_label = tk.Label(self.header_frame,
                                    text="🏠 Inicio",
                                    bg=self.colors['content_bg'],
                                    fg='white',
                                    font=('Arial', 16, 'bold'))
        self.header_label.pack(side=tk.LEFT)
        
        # Frame para el contenido activo
        self.active_frame = tk.Frame(self.content_frame, bg=self.colors['content_bg'])
        self.active_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Barra de progreso (siempre visible abajo)
        self.progress_frame = tk.Frame(self.content_frame, bg=self.colors['content_bg'], height=40)
        self.progress_frame.pack(fill=tk.X, side=tk.BOTTOM, padx=20, pady=10)
        
        self.progreso = ttk.Progressbar(self.progress_frame, mode='indeterminate')
        self.progreso.pack(fill=tk.X, pady=5)
        
        self.estado_detallado = tk.Label(self.progress_frame,
                                        text="Listo para procesar",
                                        bg=self.colors['content_bg'],
                                        fg='#888888',
                                        font=('Arial', 9))
        self.estado_detallado.pack()
        
        # Mostrar inicio por defecto
        self.cambiar_herramienta("inicio")
    
    def cambiar_herramienta(self, herramienta):
        """Cambia la herramienta activa en el panel derecho"""
        self.current_tool = herramienta
        
        # Actualizar colores de botones del menú
        for key, btn in self.menu_buttons.items():
            if key == herramienta:
                btn.config(bg=self.colors['accent'])
            else:
                btn.config(bg=self.colors['menu_bg'])
        
        # Actualizar header
        headers = {
            "inicio": "🏠 Inicio",
            "archivos": "📁 Archivos",
            "cortar": "✂️ Cortar Video",
            "audio": "🎵 Extraer Audio",
            "concatenar": "🔗 Concatenar Videos",
            "fotos": "🖼️ Crear Video desde Fotos",
            "texto": "📝 Añadir Texto",
            "efectos": "⚡ Efectos"
        }
        self.header_label.config(text=headers.get(herramienta, "Editor"))
        
        # Limpiar y mostrar nuevo contenido
        for widget in self.active_frame.winfo_children():
            widget.destroy()
        
        # Cargar la herramienta correspondiente
        if herramienta == "inicio":
            self.mostrar_inicio()
        elif herramienta == "archivos":
            self.mostrar_archivos()
        elif herramienta == "cortar":
            self.mostrar_cortar()
        elif herramienta == "audio":
            self.mostrar_audio()
        elif herramienta == "concatenar":
            self.mostrar_concatenar()
        elif herramienta == "fotos":
            self.mostrar_fotos()
        elif herramienta == "texto":
            self.mostrar_texto()
        elif herramienta == "efectos":
            self.mostrar_efectos()
    
    def mostrar_inicio(self):
        """Pantalla de inicio"""
        frame = tk.Frame(self.active_frame, bg=self.colors['content_bg'])
        frame.pack(fill=tk.BOTH, expand=True)
        
        # Logo o título grande
        tk.Label(frame,
                text="🎬",
                bg=self.colors['content_bg'],
                fg=self.colors['accent'],
                font=('Arial', 72)).pack(pady=30)
        
        tk.Label(frame,
                text="Editor de Video",
                bg=self.colors['content_bg'],
                fg='white',
                font=('Arial', 24, 'bold')).pack()
        
        tk.Label(frame,
                text="con MoviePy",
                bg=self.colors['content_bg'],
                fg='#888888',
                font=('Arial', 16)).pack()
        
        # Información
        info_frame = tk.Frame(frame, bg=self.colors['content_bg'])
        info_frame.pack(pady=40)
        
        caracteristicas = [
            "✓ Cortar y unir videos",
            "✓ Extraer audio a MP3",
            "✓ Crear videos desde fotos",
            "✓ Añadir textos personalizados",
            "✓ Cambiar velocidad",
            "✓ Redimensionar videos"
        ]
        
        for carac in caracteristicas:
            tk.Label(info_frame,
                    text=carac,
                    bg=self.colors['content_bg'],
                    fg='white',
                    font=('Arial', 11)).pack(anchor='w', pady=2)
    
    def mostrar_archivos(self):
        """Panel de selección de archivos"""
        frame = tk.Frame(self.active_frame, bg=self.colors['content_bg'])
        frame.pack(fill=tk.BOTH, expand=True)
        
        # Video principal
        video_frame = tk.Frame(frame, bg=self.colors['content_bg'])
        video_frame.pack(fill=tk.X, pady=10)
        
        tk.Label(video_frame,
                text="🎥 Video Principal:",
                bg=self.colors['content_bg'],
                fg='white',
                font=('Arial', 11, 'bold')).pack(anchor='w')
        
        btn_video = tk.Button(video_frame,
                            text="Seleccionar Video",
                            bg=self.colors['accent'],
                            fg='white',
                            font=('Arial', 10),
                            padx=20,
                            pady=5,
                            cursor='hand2',
                            command=self.seleccionar_video)
        btn_video.pack(anchor='w', pady=5)
        
        self.video_label = tk.Label(video_frame,
                                   text="Ningún video seleccionado",
                                   bg=self.colors['content_bg'],
                                   fg='#888888',
                                   font=('Arial', 10))
        self.video_label.pack(anchor='w')
        
        self.video_info = tk.Label(video_frame,
                                  text="",
                                  bg=self.colors['content_bg'],
                                  fg='#4CAF50',
                                  font=('Arial', 9))
        self.video_info.pack(anchor='w', pady=2)
        
        # Separador
        tk.Frame(frame, bg='#555555', height=1).pack(fill=tk.X, pady=15)
        
        # Audio
        audio_frame = tk.Frame(frame, bg=self.colors['content_bg'])
        audio_frame.pack(fill=tk.X, pady=10)
        
        tk.Label(audio_frame,
                text="🎵 Audio:",
                bg=self.colors['content_bg'],
                fg='white',
                font=('Arial', 11, 'bold')).pack(anchor='w')
        
        btn_audio = tk.Button(audio_frame,
                            text="Seleccionar Audio",
                            bg=self.colors['accent'],
                            fg='white',
                            font=('Arial', 10),
                            padx=20,
                            pady=5,
                            cursor='hand2',
                            command=self.seleccionar_audio)
        btn_audio.pack(anchor='w', pady=5)
        
        self.audio_label = tk.Label(audio_frame,
                                   text="Ningún audio seleccionado",
                                   bg=self.colors['content_bg'],
                                   fg='#888888',
                                   font=('Arial', 10))
        self.audio_label.pack(anchor='w')
    
    def mostrar_cortar(self):
        """Panel para cortar video"""
        self.crear_panel_cortar(self.active_frame)
    
    def mostrar_audio(self):
        """Panel para extraer audio"""
        frame = tk.Frame(self.active_frame, bg=self.colors['content_bg'])
        frame.pack(fill=tk.BOTH, expand=True)
        
        tk.Label(frame,
                text="Extraer Audio del Video",
                bg=self.colors['content_bg'],
                fg='white',
                font=('Arial', 14, 'bold')).pack(anchor='w', pady=10)
        
        tk.Label(frame,
                text="Convierte el audio de tu video a formato MP3",
                bg=self.colors['content_bg'],
                fg='#888888',
                font=('Arial', 10)).pack(anchor='w', pady=(0, 20))
        
        btn = tk.Button(frame,
                       text="🎵 Extraer Audio",
                       bg=self.colors['accent'],
                       fg='white',
                       font=('Arial', 12, 'bold'),
                       padx=30,
                       pady=10,
                       cursor='hand2',
                       command=lambda: self.ejecutar_en_hilo(self.extraer_audio))
        btn.pack(pady=20)
    
    def mostrar_concatenar(self):
        """Panel para concatenar videos"""
        self.crear_panel_concatenar(self.active_frame)
    
    def mostrar_fotos(self):
        """Panel para crear video desde fotos"""
        self.crear_panel_fotos(self.active_frame)
    
    def mostrar_texto(self):
        """Panel para añadir texto"""
        self.crear_panel_texto(self.active_frame)
    
    def mostrar_efectos(self):
        """Panel para efectos"""
        self.crear_panel_efectos(self.active_frame)
    
    def crear_panel_cortar(self, parent):
        """Crea el panel de corte de video"""
        frame = tk.Frame(parent, bg=self.colors['content_bg'])
        frame.pack(fill=tk.BOTH, expand=True)
        
        tk.Label(frame,
                text="Cortar Video",
                bg=self.colors['content_bg'],
                fg='white',
                font=('Arial', 14, 'bold')).pack(anchor='w', pady=10)
        
        # Controles
        control_frame = tk.Frame(frame, bg=self.colors['content_bg'])
        control_frame.pack(anchor='w', pady=10)
        
        tk.Label(control_frame,
                text="Inicio (segundos):",
                bg=self.colors['content_bg'],
                fg='white').grid(row=0, column=0, padx=5, pady=5, sticky='w')
        
        self.corte_inicio = tk.Entry(control_frame, width=10, bg='#555555', fg='white', insertbackground='white')
        self.corte_inicio.grid(row=0, column=1, padx=5, pady=5)
        self.corte_inicio.insert(0, "0")
        
        tk.Label(control_frame,
                text="Fin (segundos):",
                bg=self.colors['content_bg'],
                fg='white').grid(row=1, column=0, padx=5, pady=5, sticky='w')
        
        self.corte_fin = tk.Entry(control_frame, width=10, bg='#555555', fg='white', insertbackground='white')
        self.corte_fin.grid(row=1, column=1, padx=5, pady=5)
        self.corte_fin.insert(0, "10")
        
        # Botón
        btn = tk.Button(frame,
                       text="✂️ Cortar Video",
                       bg=self.colors['accent'],
                       fg='white',
                       font=('Arial', 12, 'bold'),
                       padx=30,
                       pady=10,
                       cursor='hand2',
                       command=lambda: self.ejecutar_en_hilo(self.cortar_video))
        btn.pack(pady=20)
    
    def crear_panel_concatenar(self, parent):
        """Crea el panel de concatenación"""
        frame = tk.Frame(parent, bg=self.colors['content_bg'])
        frame.pack(fill=tk.BOTH, expand=True)
        
        tk.Label(frame,
                text="Concatenar Videos",
                bg=self.colors['content_bg'],
                fg='white',
                font=('Arial', 14, 'bold')).pack(anchor='w', pady=10)
        
        # Lista
        tk.Label(frame,
                text="Videos seleccionados:",
                bg=self.colors['content_bg'],
                fg='white').pack(anchor='w', pady=5)
        
        list_frame = tk.Frame(frame, bg='#555555')
        list_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        scrollbar = tk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.lista_videos = tk.Listbox(list_frame,
                                      bg='#404040',
                                      fg='white',
                                      selectbackground=self.colors['accent'],
                                      yscrollcommand=scrollbar.set)
        self.lista_videos.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        scrollbar.config(command=self.lista_videos.yview)
        
        # Botones
        btn_frame = tk.Frame(frame, bg=self.colors['content_bg'])
        btn_frame.pack(fill=tk.X, pady=10)
        
        tk.Button(btn_frame,
                 text="➕ Agregar Video",
                 bg='#555555',
                 fg='white',
                 padx=15,
                 pady=5,
                 cursor='hand2',
                 command=self.agregar_video_concatenar).pack(side=tk.LEFT, padx=2)
        
        tk.Button(btn_frame,
                 text="❌ Quitar",
                 bg='#555555',
                 fg='white',
                 padx=15,
                 pady=5,
                 cursor='hand2',
                 command=self.quitar_video_concatenar).pack(side=tk.LEFT, padx=2)
        
        tk.Button(btn_frame,
                 text="🔄 Limpiar",
                 bg='#555555',
                 fg='white',
                 padx=15,
                 pady=5,
                 cursor='hand2',
                 command=self.limpiar_lista_videos).pack(side=tk.LEFT, padx=2)
        
        # Botón principal
        tk.Button(frame,
                 text="🔗 Unir Videos",
                 bg=self.colors['accent'],
                 fg='white',
                 font=('Arial', 12, 'bold'),
                 padx=30,
                 pady=10,
                 cursor='hand2',
                 command=lambda: self.ejecutar_en_hilo(self.concatenar_videos)).pack(pady=10)
    
    def crear_panel_fotos(self, parent):
        """Crea el panel de fotos a video"""
        frame = tk.Frame(parent, bg=self.colors['content_bg'])
        frame.pack(fill=tk.BOTH, expand=True)
        
        tk.Label(frame,
                text="Crear Video desde Fotos",
                bg=self.colors['content_bg'],
                fg='white',
                font=('Arial', 14, 'bold')).pack(anchor='w', pady=10)
        
        # Lista de imágenes
        tk.Label(frame,
                text="Imágenes seleccionadas:",
                bg=self.colors['content_bg'],
                fg='white').pack(anchor='w', pady=5)
        
        list_frame = tk.Frame(frame, bg='#555555')
        list_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        scrollbar = tk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.lista_imagenes = tk.Listbox(list_frame,
                                        bg='#404040',
                                        fg='white',
                                        selectbackground=self.colors['accent'],
                                        yscrollcommand=scrollbar.set)
        self.lista_imagenes.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        scrollbar.config(command=self.lista_imagenes.yview)
        
        # Duración
        dur_frame = tk.Frame(frame, bg=self.colors['content_bg'])
        dur_frame.pack(fill=tk.X, pady=10)
        
        tk.Label(dur_frame,
                text="Duración por imagen (segundos):",
                bg=self.colors['content_bg'],
                fg='white').pack(side=tk.LEFT, padx=5)
        
        self.duracion_imagen = tk.Entry(dur_frame, width=8, bg='#555555', fg='white')
        self.duracion_imagen.pack(side=tk.LEFT, padx=5)
        self.duracion_imagen.insert(0, "3")
        
        # Botones
        btn_frame = tk.Frame(frame, bg=self.colors['content_bg'])
        btn_frame.pack(fill=tk.X, pady=10)
        
        tk.Button(btn_frame,
                 text="➕ Agregar Imágenes",
                 bg='#555555',
                 fg='white',
                 padx=15,
                 pady=5,
                 cursor='hand2',
                 command=self.agregar_imagenes).pack(side=tk.LEFT, padx=2)
        
        tk.Button(btn_frame,
                 text="❌ Quitar",
                 bg='#555555',
                 fg='white',
                 padx=15,
                 pady=5,
                 cursor='hand2',
                 command=self.quitar_imagen).pack(side=tk.LEFT, padx=2)
        
        # Botón principal
        tk.Button(frame,
                 text="🎬 Crear Video",
                 bg=self.colors['accent'],
                 fg='white',
                 font=('Arial', 12, 'bold'),
                 padx=30,
                 pady=10,
                 cursor='hand2',
                 command=lambda: self.ejecutar_en_hilo(self.crear_video_imagenes)).pack(pady=10)
    
    def crear_panel_texto(self, parent):
        """Crea el panel de texto"""
        frame = tk.Frame(parent, bg=self.colors['content_bg'])
        frame.pack(fill=tk.BOTH, expand=True)
        
        tk.Label(frame,
                text="Añadir Texto al Video",
                bg=self.colors['content_bg'],
                fg='white',
                font=('Arial', 14, 'bold')).pack(anchor='w', pady=10)
        
        # Campos
        campos_frame = tk.Frame(frame, bg=self.colors['content_bg'])
        campos_frame.pack(anchor='w', pady=10)
        
        # Texto
        tk.Label(campos_frame,
                text="Texto:",
                bg=self.colors['content_bg'],
                fg='white').grid(row=0, column=0, padx=5, pady=5, sticky='w')
        
        self.texto_entrada = tk.Entry(campos_frame, width=40, bg='#555555', fg='white')
        self.texto_entrada.grid(row=0, column=1, padx=5, pady=5, columnspan=3)
        
        # Posición
        tk.Label(campos_frame,
                text="Posición:",
                bg=self.colors['content_bg'],
                fg='white').grid(row=1, column=0, padx=5, pady=5, sticky='w')
        
        self.posicion_texto = ttk.Combobox(campos_frame, 
                                          values=['center', 'top', 'bottom', 'left', 'right'],
                                          width=10)
        self.posicion_texto.grid(row=1, column=1, padx=5, pady=5)
        self.posicion_texto.set('center')
        
        # Color
        tk.Label(campos_frame,
                text="Color:",
                bg=self.colors['content_bg'],
                fg='white').grid(row=1, column=2, padx=5, pady=5, sticky='w')
        
        self.color_texto = ttk.Combobox(campos_frame,
                                       values=['white', 'black', 'red', 'blue', 'green', 'yellow'],
                                       width=8)
        self.color_texto.grid(row=1, column=3, padx=5, pady=5)
        self.color_texto.set('white')
        
        # Tamaño
        tk.Label(campos_frame,
                text="Tamaño:",
                bg=self.colors['content_bg'],
                fg='white').grid(row=2, column=0, padx=5, pady=5, sticky='w')
        
        self.tamano_texto = tk.Entry(campos_frame, width=8, bg='#555555', fg='white')
        self.tamano_texto.grid(row=2, column=1, padx=5, pady=5)
        self.tamano_texto.insert(0, "50")
        
        # Botón
        tk.Button(frame,
                 text="📝 Añadir Texto",
                 bg=self.colors['accent'],
                 fg='white',
                 font=('Arial', 12, 'bold'),
                 padx=30,
                 pady=10,
                 cursor='hand2',
                 command=lambda: self.ejecutar_en_hilo(self.anadir_texto)).pack(pady=20)
    
    def crear_panel_efectos(self, parent):
        """Crea el panel de efectos"""
        frame = tk.Frame(parent, bg=self.colors['content_bg'])
        frame.pack(fill=tk.BOTH, expand=True)
        
        tk.Label(frame,
                text="Efectos de Video",
                bg=self.colors['content_bg'],
                fg='white',
                font=('Arial', 14, 'bold')).pack(anchor='w', pady=10)
        
        # Velocidad
        vel_frame = tk.Frame(frame, bg=self.colors['content_bg'])
        vel_frame.pack(anchor='w', pady=10)
        
        tk.Label(vel_frame,
                text="Velocidad (0.5=lento, 2=rápido):",
                bg=self.colors['content_bg'],
                fg='white').pack(side=tk.LEFT, padx=5)
        
        self.velocidad_factor = tk.Entry(vel_frame, width=8, bg='#555555', fg='white')
        self.velocidad_factor.pack(side=tk.LEFT, padx=5)
        self.velocidad_factor.insert(0, "1.5")
        
        tk.Button(vel_frame,
                 text="⚡ Aplicar",
                 bg='#555555',
                 fg='white',
                 padx=15,
                 pady=5,
                 cursor='hand2',
                 command=lambda: self.ejecutar_en_hilo(self.cambiar_velocidad)).pack(side=tk.LEFT, padx=10)
        
        # Separador
        tk.Frame(frame, bg='#555555', height=1).pack(fill=tk.X, pady=15)
        
        # Redimensionar
        red_frame = tk.Frame(frame, bg=self.colors['content_bg'])
        red_frame.pack(anchor='w', pady=10)
        
        tk.Label(red_frame,
                text="Redimensionar ancho (px):",
                bg=self.colors['content_bg'],
                fg='white').pack(side=tk.LEFT, padx=5)
        
        self.redimensionar_ancho = tk.Entry(red_frame, width=8, bg='#555555', fg='white')
        self.redimensionar_ancho.pack(side=tk.LEFT, padx=5)
        self.redimensionar_ancho.insert(0, "640")
        
        tk.Button(red_frame,
                 text="📏 Aplicar",
                 bg='#555555',
                 fg='white',
                 padx=15,
                 pady=5,
                 cursor='hand2',
                 command=lambda: self.ejecutar_en_hilo(self.redimensionar_video)).pack(side=tk.LEFT, padx=10)
    
    # ==================== FUNCIONALIDADES (igual que antes) ====================
    
    def seleccionar_video(self):
        archivo = filedialog.askopenfilename(
            title="Seleccionar Video",
            filetypes=[("Archivos de video", "*.mp4 *.avi *.mov *.mkv *.webm"), ("Todos", "*.*")]
        )
        if archivo:
            self.archivo_video = archivo
            nombre = os.path.basename(archivo)
            self.video_label.config(text=nombre, fg='white')
            
            # Obtener información del video
            try:
                clip = VideoFileClip(archivo)
                duracion = clip.duration
                size = clip.size
                fps = clip.fps
                clip.close()
                
                info = f"Duración: {duracion:.2f}s | Dimensiones: {size[0]}x{size[1]} | FPS: {fps:.2f}"
                self.video_info.config(text=info)
            except:
                self.video_info.config(text="No se pudo leer información del video")
    
    def seleccionar_audio(self):
        archivo = filedialog.askopenfilename(
            title="Seleccionar Audio",
            filetypes=[("Archivos de audio", "*.mp3 *.wav *.aac *.ogg"), ("Todos", "*.*")]
        )
        if archivo:
            self.archivo_audio = archivo
            nombre = os.path.basename(archivo)
            self.audio_label.config(text=nombre, fg='white')
    
    def agregar_video_concatenar(self):
        archivos = filedialog.askopenfilenames(
            title="Seleccionar Videos para Concatenar",
            filetypes=[("Archivos de video", "*.mp4 *.avi *.mov *.mkv"), ("Todos", "*.*")]
        )
        for archivo in archivos:
            if archivo not in self.archivos_concatenar:
                self.archivos_concatenar.append(archivo)
                self.lista_videos.insert(tk.END, os.path.basename(archivo))
    
    def quitar_video_concatenar(self):
        seleccion = self.lista_videos.curselection()
        if seleccion:
            idx = seleccion[0]
            self.lista_videos.delete(idx)
            del self.archivos_concatenar[idx]
    
    def limpiar_lista_videos(self):
        self.lista_videos.delete(0, tk.END)
        self.archivos_concatenar = []
    
    def agregar_imagenes(self):
        archivos = filedialog.askopenfilenames(
            title="Seleccionar Imágenes",
            filetypes=[("Imágenes", "*.jpg *.jpeg *.png *.bmp *.gif"), ("Todos", "*.*")]
        )
        for archivo in archivos:
            if archivo not in self.archivos_imagenes:
                self.archivos_imagenes.append(archivo)
                self.lista_imagenes.insert(tk.END, os.path.basename(archivo))
    
    def quitar_imagen(self):
        seleccion = self.lista_imagenes.curselection()
        if seleccion:
            idx = seleccion[0]
            self.lista_imagenes.delete(idx)
            del self.archivos_imagenes[idx]
    
    def ejecutar_en_hilo(self, func):
        """Ejecuta una función en un hilo separado para no bloquear la GUI"""
        if self.procesando:
            messagebox.showwarning("Atención", "Ya hay un proceso en ejecución")
            return
        
        hilo = threading.Thread(target=func)
        hilo.daemon = True
        hilo.start()
    
    def iniciar_progreso(self, mensaje):
        """Activa la barra de progreso"""
        self.procesando = True
        self.progreso.start(10)
        self.menu_estado.config(text="⏳ Procesando...", fg='orange')
        self.estado_detallado.config(text=mensaje, fg='orange')
        self.root.update()
    
    def detener_progreso(self, mensaje, exito=True):
        """Detiene la barra de progreso"""
        self.progreso.stop()
        self.procesando = False
        color = "#4CAF50" if exito else "#f44336"
        self.menu_estado.config(text="✅ Listo" if exito else "❌ Error", fg=color)
        self.estado_detallado.config(text=mensaje, fg=color)
        self.root.update()
    
    def guardar_archivo(self, titulo, extensiones, nombre_defecto="output.mp4"):
        """Diálogo para guardar archivo"""
        return filedialog.asksaveasfilename(
            title=titulo,
            defaultextension=extensiones[0],
            filetypes=extensiones,
            initialfile=nombre_defecto
        )
    
    # ==================== OPERACIONES DE MOVIEPY ====================
    
    def cortar_video(self):
        if not self.archivo_video:
            self.detener_progreso("Error: Selecciona un video primero", False)
            return
        
        try:
            inicio = float(self.corte_inicio.get())
            fin = float(self.corte_fin.get())
            
            self.iniciar_progreso(f"Cortando video de {inicio}s a {fin}s...")
            
            clip = VideoFileClip(self.archivo_video)
            fragmento = clip.subclipped(inicio, fin)
            
            archivo_salida = self.guardar_archivo(
                "Guardar video cortado",
                [("MP4", "*.mp4"), ("Todos", "*.*")],
                "video_cortado.mp4"
            )
            
            if archivo_salida:
                fragmento.write_videofile(archivo_salida, logger=None)
                fragmento.close()
                clip.close()
                self.detener_progreso(f"✅ Video guardado en: {os.path.basename(archivo_salida)}")
            else:
                fragmento.close()
                clip.close()
                self.detener_progreso("Operación cancelada")
                
        except Exception as e:
            self.detener_progreso(f"❌ Error: {str(e)}", False)
    
    def extraer_audio(self):
        if not self.archivo_video:
            self.detener_progreso("Error: Selecciona un video primero", False)
            return
        
        try:
            self.iniciar_progreso("Extrayendo audio...")
            
            clip = VideoFileClip(self.archivo_video)
            audio = clip.audio
            
            archivo_salida = self.guardar_archivo(
                "Guardar audio extraído",
                [("MP3", "*.mp3"), ("WAV", "*.wav"), ("Todos", "*.*")],
                "audio_extraido.mp3"
            )
            
            if archivo_salida:
                audio.write_audiofile(archivo_salida, logger=None)
                clip.close()
                self.detener_progreso(f"✅ Audio guardado en: {os.path.basename(archivo_salida)}")
            else:
                clip.close()
                self.detener_progreso("Operación cancelada")
                
        except Exception as e:
            self.detener_progreso(f"❌ Error: {str(e)}", False)
    
    def concatenar_videos(self):
        if len(self.archivos_concatenar) < 2:
            self.detener_progreso("Error: Selecciona al menos 2 videos", False)
            return
        
        try:
            self.iniciar_progreso("Concatenando videos...")
            
            clips = []
            for archivo in self.archivos_concatenar:
                clip = VideoFileClip(archivo)
                clips.append(clip)
            
            video_final = concatenate_videoclips(clips)
            
            archivo_salida = self.guardar_archivo(
                "Guardar video concatenado",
                [("MP4", "*.mp4"), ("Todos", "*.*")],
                "video_concatenado.mp4"
            )
            
            if archivo_salida:
                video_final.write_videofile(archivo_salida, logger=None)
                video_final.close()
                for clip in clips:
                    clip.close()
                self.detener_progreso(f"✅ Video guardado en: {os.path.basename(archivo_salida)}")
            else:
                video_final.close()
                for clip in clips:
                    clip.close()
                self.detener_progreso("Operación cancelada")
                
        except Exception as e:
            self.detener_progreso(f"❌ Error: {str(e)}", False)
    
    def crear_video_imagenes(self):
        if not self.archivos_imagenes:
            self.detener_progreso("Error: Selecciona al menos una imagen", False)
            return
        
        try:
            duracion = float(self.duracion_imagen.get())
            self.iniciar_progreso(f"Creando video con {len(self.archivos_imagenes)} imágenes...")
            
            clips_imagen = []
            for img_path in self.archivos_imagenes:
                clip_img = ImageClip(img_path).with_duration(duracion)
                clips_imagen.append(clip_img)
            
            video_sin_audio = concatenate_videoclips(clips_imagen, method="compose")
            
            # Si hay audio seleccionado, añadirlo
            if self.archivo_audio:
                audio = AudioFileClip(self.archivo_audio)
                video_final = video_sin_audio.with_audio(audio)
            else:
                video_final = video_sin_audio
            
            archivo_salida = self.guardar_archivo(
                "Guardar video de imágenes",
                [("MP4", "*.mp4"), ("Todos", "*.*")],
                "video_imagenes.mp4"
            )
            
            if archivo_salida:
                video_final.write_videofile(archivo_salida, fps=24, logger=None)
                video_final.close()
                for clip in clips_imagen:
                    clip.close()
                self.detener_progreso(f"✅ Video guardado en: {os.path.basename(archivo_salida)}")
            else:
                video_final.close()
                for clip in clips_imagen:
                    clip.close()
                self.detener_progreso("Operación cancelada")
                
        except Exception as e:
            self.detener_progreso(f"❌ Error: {str(e)}", False)
    
    def anadir_texto(self):
        if not self.archivo_video:
            self.detener_progreso("Error: Selecciona un video primero", False)
            return
        
        if not self.texto_entrada.get():
            self.detener_progreso("Error: Escribe un texto", False)
            return
        
        try:
            texto = self.texto_entrada.get()
            posicion = self.posicion_texto.get()
            color = self.color_texto.get()
            tamano = int(self.tamano_texto.get())
            
            self.iniciar_progreso("Añadiendo texto al video...")
            
            clip_video = VideoFileClip(self.archivo_video)
            
            # Crear clip de texto
            texto_clip = TextClip(
                text=texto,
                font_size=tamano,
                color=color,
                font="Arial",
                stroke_color='black',
                stroke_width=2
            ).with_duration(clip_video.duration).with_position(posicion)
            
            # Componer
            video_final = CompositeVideoClip([clip_video, texto_clip])
            
            archivo_salida = self.guardar_archivo(
                "Guardar video con texto",
                [("MP4", "*.mp4"), ("Todos", "*.*")],
                "video_con_texto.mp4"
            )
            
            if archivo_salida:
                video_final.write_videofile(archivo_salida, logger=None)
                video_final.close()
                clip_video.close()
                texto_clip.close()
                self.detener_progreso(f"✅ Video guardado en: {os.path.basename(archivo_salida)}")
            else:
                video_final.close()
                clip_video.close()
                texto_clip.close()
                self.detener_progreso("Operación cancelada")
                
        except Exception as e:
            self.detener_progreso(f"❌ Error: {str(e)}", False)
    
    def cambiar_velocidad(self):
        if not self.archivo_video:
            self.detener_progreso("Error: Selecciona un video primero", False)
            return
        
        try:
            factor = float(self.velocidad_factor.get())
            self.iniciar_progreso(f"Cambiando velocidad x{factor}...")
            
            clip = VideoFileClip(self.archivo_video)
            clip_modificado = clip.with_speed_scaled(factor)
            
            archivo_salida = self.guardar_archivo(
                "Guardar video con velocidad modificada",
                [("MP4", "*.mp4"), ("Todos", "*.*")],
                "video_velocidad_modificada.mp4"
            )
            
            if archivo_salida:
                clip_modificado.write_videofile(archivo_salida, logger=None)
                clip_modificado.close()
                clip.close()
                self.detener_progreso(f"✅ Video guardado en: {os.path.basename(archivo_salida)}")
            else:
                clip_modificado.close()
                clip.close()
                self.detener_progreso("Operación cancelada")
                
        except Exception as e:
            self.detener_progreso(f"❌ Error: {str(e)}", False)
    
    def redimensionar_video(self):
        if not self.archivo_video:
            self.detener_progreso("Error: Selecciona un video primero", False)
            return
        
        try:
            ancho = int(self.redimensionar_ancho.get())
            self.iniciar_progreso(f"Redimensionando video a ancho {ancho}px...")
            
            clip = VideoFileClip(self.archivo_video)
            clip_redimensionado = clip.resized(width=ancho)
            
            archivo_salida = self.guardar_archivo(
                "Guardar video redimensionado",
                [("MP4", "*.mp4"), ("Todos", "*.*")],
                "video_redimensionado.mp4"
            )
            
            if archivo_salida:
                clip_redimensionado.write_videofile(archivo_salida, logger=None)
                clip_redimensionado.close()
                clip.close()
                self.detener_progreso(f"✅ Video guardado en: {os.path.basename(archivo_salida)}")
            else:
                clip_redimensionado.close()
                clip.close()
                self.detener_progreso("Operación cancelada")
                
        except Exception as e:
            self.detener_progreso(f"❌ Error: {str(e)}", False)


def main():
    root = tk.Tk()
    
    # Configurar icono si existe
    try:
        root.iconbitmap(default='icono.ico')
    except:
        pass
    
    app = EditorVideoApp(root)
    
    # Manejar cierre de ventana
    def on_closing():
        if app.procesando:
            if messagebox.askyesno("Confirmar", "Hay un proceso en ejecución. ¿Seguro que quieres salir?"):
                root.destroy()
        else:
            root.destroy()
    
    root.protocol("WM_DELETE_WINDOW", on_closing)
    root.mainloop()

if __name__ == "__main__":
    main()