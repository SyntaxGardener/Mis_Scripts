#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
from threading import Thread
from datetime import datetime
import re
import time
import random
import json
from urllib.parse import urljoin, urlparse, parse_qs
from collections import defaultdict

# Verificar dependencias
try:
    import requests
    from PIL import Image, ExifTags
    import bs4
    from bs4 import BeautifulSoup
    DEPENDENCIAS_OK = True
except ImportError as e:
    DEPENDENCIAS_OK = False
    ERROR_DEP = str(e)

class DescargadorPremium:
    def __init__(self, root):
        self.root = root
        self.root.title("🖼️ Descargador de Imágenes")
        # 1. Definimos el tamaño que queremos
        ancho = 650
        alto = 800
        
        # 2. Calculamos la posición (Esto es lo que va dentro de init)
        pos_x = (self.root.winfo_screenwidth() // 2) - (ancho // 2)
        
        # 3. Aplicamos la magia: Ancho x Alto + Derecha + Arriba (0)
        self.root.geometry(f"{ancho}x{alto}+{pos_x}+0")
        
        # Configurar cierre
        self.root.protocol("WM_DELETE_WINDOW", self.cerrar_app)
        
        # Variables de control
        self.carpeta_destino = tk.StringVar(value="imagenes_descargadas")
        self.url = tk.StringVar()
        self.descargando = False
        
        # Control de peticiones
        self.peticiones_por_dominio = defaultdict(list)
        self.ultimo_error_429 = {}
        
        # Estadísticas
        self.descargadas = 0
        self.fallidas = 0
        self.errores_429 = 0
        self.metadatos_guardados = []
        
        self.setup_ui()
        
    def cerrar_app(self):
        """Cierra la aplicación correctamente"""
        if self.descargando:
            if messagebox.askyesno("Confirmar", "¿Cancelar descargas y salir?"):
                self.descargando = False
                self.root.quit()
                self.root.destroy()
        else:
            self.root.quit()
            self.root.destroy()
    
    def setup_ui(self):
        # Frame principal con scroll
        main_canvas = tk.Canvas(self.root)
        scrollbar = ttk.Scrollbar(self.root, orient="vertical", command=main_canvas.yview)
        main_frame = ttk.Frame(main_canvas)
        
        main_canvas.configure(yscrollcommand=scrollbar.set)
        main_canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        main_canvas.create_window((0, 0), window=main_frame, anchor="nw")
        main_frame.bind("<Configure>", lambda e: main_canvas.configure(scrollregion=main_canvas.bbox("all")))
        
        # Título
        titulo = ttk.Label(main_frame, text="🖼️ Descargador de Imágenes", 
                          font=('Arial', 18, 'bold'))
        titulo.pack(pady=15)
        
        # Frame URL
        url_frame = ttk.LabelFrame(main_frame, text="🌐 URL del sitio", padding="10")
        url_frame.pack(fill=tk.X, padx=10, pady=5)
        
        url_entry_frame = ttk.Frame(url_frame)
        url_entry_frame.pack(fill=tk.X)
        
        ttk.Label(url_entry_frame, text="URL:", font=('Arial', 10)).pack(side=tk.LEFT, padx=5)
        self.url_entry = ttk.Entry(url_entry_frame, textvariable=self.url, font=('Arial', 10))
        self.url_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        self.url_entry.focus()
        
        ttk.Button(url_entry_frame, text="📋 Pegar", command=self.pegar_url).pack(side=tk.LEFT, padx=2)
        
        # Frame carpeta
        carpeta_frame = ttk.LabelFrame(main_frame, text="📁 Carpeta de destino", padding="10")
        carpeta_frame.pack(fill=tk.X, padx=10, pady=5)
        
        carpeta_entry_frame = ttk.Frame(carpeta_frame)
        carpeta_entry_frame.pack(fill=tk.X)
        
        ttk.Label(carpeta_entry_frame, text="Carpeta:", font=('Arial', 10)).pack(side=tk.LEFT, padx=5)
        ttk.Entry(carpeta_entry_frame, textvariable=self.carpeta_destino, font=('Arial', 10)).pack(
            side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        ttk.Button(carpeta_entry_frame, text="📁 Examinar", command=self.seleccionar_carpeta).pack(side=tk.LEFT, padx=2)
        
        # SELECTOR DE CALIDAD
        calidad_frame = ttk.LabelFrame(main_frame, text="⚡ Selector de Calidad", padding="10")
        calidad_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Calidad mínima
        calidad_min_frame = ttk.Frame(calidad_frame)
        calidad_min_frame.pack(fill=tk.X, pady=2)
        
        ttk.Label(calidad_min_frame, text="Calidad mínima:").pack(side=tk.LEFT, padx=5)
        self.calidad_min = tk.StringVar(value="0")
        ttk.Entry(calidad_min_frame, textvariable=self.calidad_min, width=8).pack(side=tk.LEFT, padx=5)
        ttk.Label(calidad_min_frame, text="(0 = todas, 1 = baja, 2 = media, 3 = alta)").pack(side=tk.LEFT, padx=5)
        
        # Tamaño mínimo (KB)
        tamaño_frame = ttk.Frame(calidad_frame)
        tamaño_frame.pack(fill=tk.X, pady=2)
        
        ttk.Label(tamaño_frame, text="Tamaño mínimo (KB):").pack(side=tk.LEFT, padx=5)
        self.tamaño_min = tk.StringVar(value="0")
        ttk.Entry(tamaño_frame, textvariable=self.tamaño_min, width=8).pack(side=tk.LEFT, padx=5)
        
        ttk.Label(tamaño_frame, text="Resolución mínima:").pack(side=tk.LEFT, padx=20)
        self.resolucion_min = tk.StringVar(value="0x0")
        ttk.Entry(tamaño_frame, textvariable=self.resolucion_min, width=12).pack(side=tk.LEFT, padx=5)
        ttk.Label(tamaño_frame, text="(ancho x alto, ej: 800x600)").pack(side=tk.LEFT, padx=5)
        
        # Opciones de calidad
        opciones_calidad_frame = ttk.Frame(calidad_frame)
        opciones_calidad_frame.pack(fill=tk.X, pady=5)
        
        self.solo_mayor_resolucion = tk.BooleanVar(value=False)
        ttk.Checkbutton(opciones_calidad_frame, text="Solo la mayor resolución de cada imagen", 
                       variable=self.solo_mayor_resolucion).pack(side=tk.LEFT, padx=20)
        
        self.ignorar_thumbnails = tk.BooleanVar(value=True)
        ttk.Checkbutton(opciones_calidad_frame, text="Ignorar thumbnails (miniaturas)", 
                       variable=self.ignorar_thumbnails).pack(side=tk.LEFT, padx=20)
        
        # METADATOS
        metadatos_frame = ttk.LabelFrame(main_frame, text="📋 Metadatos", padding="10")
        metadatos_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.guardar_metadatos = tk.BooleanVar(value=True)
        ttk.Checkbutton(metadatos_frame, text="Guardar metadatos (título, alt, descripción)", 
                       variable=self.guardar_metadatos).grid(row=0, column=0, sticky=tk.W, padx=5)
        
        self.guardar_exif = tk.BooleanVar(value=True)
        ttk.Checkbutton(metadatos_frame, text="Guardar metadatos EXIF de las imágenes", 
                       variable=self.guardar_exif).grid(row=1, column=0, sticky=tk.W, padx=5)
        
        self.guardar_json = tk.BooleanVar(value=True)
        ttk.Checkbutton(metadatos_frame, text="Crear archivo JSON con todos los metadatos", 
                       variable=self.guardar_json).grid(row=2, column=0, sticky=tk.W, padx=5)
        
        # CONTROL DE VELOCIDAD
        velocidad_frame = ttk.LabelFrame(main_frame, text="🐢 Control de Velocidad", padding="10")
        velocidad_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Espera entre imágenes
        ttk.Label(velocidad_frame, text="Espera entre imágenes (seg):").grid(row=0, column=0, padx=5, pady=2)
        self.espera_var = tk.StringVar(value="3")
        ttk.Entry(velocidad_frame, textvariable=self.espera_var, width=5).grid(row=0, column=1, padx=5)
        
        # Máx peticiones/minuto
        ttk.Label(velocidad_frame, text="Máx peticiones/minuto:").grid(row=0, column=2, padx=5)
        self.max_peticiones_var = tk.StringVar(value="10")
        ttk.Entry(velocidad_frame, textvariable=self.max_peticiones_var, width=5).grid(row=0, column=3, padx=5)
        
        # Modo lento
        self.modo_lento = tk.BooleanVar(value=False)
        ttk.Checkbutton(velocidad_frame, text="Modo ultra lento", 
                       variable=self.modo_lento).grid(row=1, column=0, columnspan=4, sticky=tk.W, padx=5)
        
        # BOTONES DE ACCIÓN
        botones_frame = ttk.Frame(main_frame)
        botones_frame.pack(pady=15)
        
        self.btn_descargar = ttk.Button(botones_frame, text="🚀 DESCARGAR", 
                                       command=self.iniciar_descarga, width=15)
        self.btn_descargar.pack(side=tk.LEFT, padx=5)
        
        self.btn_cancelar = ttk.Button(botones_frame, text="⏹️ Cancelar", 
                                      command=self.cancelar_descarga, state=tk.DISABLED, width=12)
        self.btn_cancelar.pack(side=tk.LEFT, padx=5)
        
        self.btn_reparar = ttk.Button(botones_frame, text="🔧 REPARAR", 
                                     command=self.reparar_carpeta, width=12)
        self.btn_reparar.pack(side=tk.LEFT, padx=5)
        
        self.btn_metadatos = ttk.Button(botones_frame, text="📋 VER METADATOS", 
                                       command=self.ver_metadatos, width=15)
        self.btn_metadatos.pack(side=tk.LEFT, padx=5)
        
        # BARRA DE PROGRESO
        self.progreso = ttk.Progressbar(main_frame, mode='determinate')
        self.progreso.pack(fill=tk.X, padx=10, pady=5)
        
        # ESTADÍSTICAS
        self.stats_label = ttk.Label(main_frame, text="Listo para comenzar...", font=('Arial', 10))
        self.stats_label.pack(pady=5)
        
        # ÁREA DE LOG
        ttk.Label(main_frame, text="📋 Registro de actividad:").pack(anchor=tk.W, padx=10, pady=(10,0))
        
        self.log_area = scrolledtext.ScrolledText(main_frame, height=12, font=('Courier', 9))
        self.log_area.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Configurar colores del log
        self.log_area.tag_config('exito', foreground='green')
        self.log_area.tag_config('error', foreground='red')
        self.log_area.tag_config('info', foreground='blue')
        self.log_area.tag_config('warning', foreground='orange')
        self.log_area.tag_config('429', foreground='purple')
        self.log_area.tag_config('calidad', foreground='dark orange')
        self.log_area.tag_config('metadata', foreground='brown')
        
        # Atajos de teclado
        self.root.bind('<Control-v>', lambda e: self.pegar_url())
        self.root.bind('<Return>', lambda e: self.iniciar_descarga())
        
        # Mensaje inicial
        self.log("🖼️ Descargador Premium iniciado", 'info')
        self.log("📝 Configura calidad y metadatos antes de descargar", 'info')
    
    def pegar_url(self):
        """Pega URL del portapapeles"""
        try:
            url = self.root.clipboard_get().strip()
            if not url.startswith(('http://', 'https://')):
                url = 'https://' + url
            self.url.set(url)
            self.log(f"📋 URL pegada: {url}", 'info')
        except:
            self.log("❌ No hay URL en el portapapeles", 'error')
    
    def seleccionar_carpeta(self):
        """Selecciona carpeta de destino"""
        carpeta = filedialog.askdirectory(title="Seleccionar carpeta")
        if carpeta:
            self.carpeta_destino.set(carpeta)
            self.log(f"📁 Carpeta seleccionada: {carpeta}", 'info')
    
    def log(self, mensaje, tipo='info'):
        """Añade mensaje al log con timestamp"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_area.insert(tk.END, f"[{timestamp}] ", 'info')
        self.log_area.insert(tk.END, f"{mensaje}\n", tipo)
        self.log_area.see(tk.END)
        self.root.update_idletasks()
    
    # FUNCIONES DE CALIDAD
    def evaluar_calidad(self, url_img, tamaño_bytes):
        """Evalúa la calidad de una imagen por URL y tamaño"""
        
        calidad = 0  # 0 = baja, 1 = media, 2 = alta, 3 = original
        
        # Por tamaño
        tamaño_kb = tamaño_bytes / 1024
        if tamaño_kb > 500:
            calidad = 3
        elif tamaño_kb > 200:
            calidad = 2
        elif tamaño_kb > 50:
            calidad = 1
        
        # Por palabras clave en URL (detectar thumbnails)
        url_lower = url_img.lower()
        if any(x in url_lower for x in ['thumb', 'thumbnail', 'small', 'mini', 'ico', 'icon']):
            calidad = 0
        
        # Por parámetros de tamaño en URL
        if '?' in url_img:
            params = parse_qs(urlparse(url_img).query)
            for param in params:
                if any(x in param.lower() for x in ['w=', 'width=', 'h=', 'height=', 'size=']):
                    try:
                        valor = int(params[param][0])
                        if valor < 300:
                            calidad = 0
                        elif valor < 800:
                            calidad = 1
                        else:
                            calidad = 2
                    except:
                        pass
        
        return calidad
    
    def cumple_filtros_calidad(self, url_img, tamaño_bytes):
        """Verifica si una imagen cumple los filtros de calidad"""
        
        # Filtro por calidad mínima
        try:
            calidad_min = int(self.calidad_min.get())
            calidad_img = self.evaluar_calidad(url_img, tamaño_bytes)
            
            if calidad_img < calidad_min:
                return False, f"Calidad {calidad_img} < {calidad_min}"
        except:
            pass
        
        # Filtro por tamaño mínimo
        try:
            tamaño_min_kb = int(self.tamaño_min.get())
            if tamaño_min_kb > 0 and (tamaño_bytes / 1024) < tamaño_min_kb:
                return False, f"Tamaño {tamaño_bytes/1024:.1f}KB < {tamaño_min_kb}KB"
        except:
            pass
        
        # Ignorar thumbnails
        if self.ignorar_thumbnails.get():
            url_lower = url_img.lower()
            if any(x in url_lower for x in ['thumb', 'thumbnail', '50x50', '100x100']):
                return False, "Es thumbnail"
        
        return True, "OK"
    
    # FUNCIONES DE METADATOS
    def extraer_metadatos_img(self, img_tag, url_img):
        """Extrae metadatos de una etiqueta img"""
        
        metadatos = {
            'url': url_img,
            'src_original': img_tag.get('src', ''),
            'alt': img_tag.get('alt', ''),
            'title': img_tag.get('title', ''),
            'width': img_tag.get('width', ''),
            'height': img_tag.get('height', ''),
            'class': str(img_tag.get('class', '')),
            'id': img_tag.get('id', ''),
            'loading': img_tag.get('loading', ''),
            'fecha_descarga': datetime.now().isoformat(),
        }
        
        # Atributos comunes de WordPress y otros CMS
        for attr in ['data-src', 'data-lazy-src', 'data-original', 'data-highres']:
            if img_tag.get(attr):
                metadatos[attr] = img_tag.get(attr)
        
        # Descripción de figura si existe
        parent = img_tag.parent
        if parent and parent.name == 'figure':
            figcaption = parent.find('figcaption')
            if figcaption:
                metadatos['figcaption'] = figcaption.get_text().strip()
        
        return metadatos
    
    def extraer_metadatos_pagina(self, soup):
        """Extrae metadatos de la página"""
        
        metadatos_pagina = {
            'titulo': soup.title.string if soup.title else '',
            'url': self.url.get(),
            'fecha': datetime.now().isoformat(),
        }
        
        # Meta tags
        for meta in soup.find_all('meta'):
            if meta.get('name'):
                metadatos_pagina[f'meta_{meta["name"]}'] = meta.get('content', '')
            elif meta.get('property'):
                metadatos_pagina[f'og_{meta["property"]}'] = meta.get('content', '')
        
        return metadatos_pagina
    
    def guardar_metadatos_exif(self, ruta_imagen):
        """Extrae y guarda metadatos EXIF de una imagen"""
        try:
            with Image.open(ruta_imagen) as img:
                exif = {}
                
                # Obtener EXIF si existe
                if hasattr(img, '_getexif') and img._getexif():
                    for tag_id, value in img._getexif().items():
                        tag = ExifTags.TAGS.get(tag_id, tag_id)
                        exif[tag] = str(value)
                
                # Información básica
                exif['formato'] = img.format
                exif['modo'] = img.mode
                exif['tamaño'] = f"{img.width}x{img.height}"
                
                return exif
        except:
            return {}
    
    def guardar_metadatos_json(self, carpeta, metadatos_lista):
        """Guarda todos los metadatos en un archivo JSON"""
        
        ruta_json = os.path.join(carpeta, "metadatos.json")
        
        # Estructura completa
        data = {
            'fecha_generacion': datetime.now().isoformat(),
            'url_origen': self.url.get(),
            'total_imagenes': len(metadatos_lista),
            'imagenes': metadatos_lista
        }
        
        with open(ruta_json, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        self.log(f"📋 Metadatos guardados en: {ruta_json}", 'metadata')
        return ruta_json
    
    # FUNCIONES DE DESCARGA
    def esperar_segun_dominio(self, url):
        """Espera inteligente para evitar 429"""
        
        dominio = urlparse(url).netloc
        ahora = time.time()
        
        # Actualizar límites
        try:
            self.max_peticiones_por_minuto = int(self.max_peticiones_var.get())
        except:
            self.max_peticiones_por_minuto = 10
            
        if self.modo_lento.get():
            self.max_peticiones_por_minuto = 5
        
        # Limpiar peticiones viejas
        self.peticiones_por_dominio[dominio] = [
            t for t in self.peticiones_por_dominio[dominio] 
            if ahora - t < 60
        ]
        
        # Si hubo 429 reciente
        if dominio in self.ultimo_error_429:
            tiempo_desde_error = ahora - self.ultimo_error_429[dominio]
            if tiempo_desde_error < 300:  # 5 minutos
                espera_castigo = 20 - (tiempo_desde_error / 15)
                if espera_castigo > 0:
                    time.sleep(espera_castigo)
        
        # Control de tasa
        peticiones_ahora = len(self.peticiones_por_dominio[dominio])
        if peticiones_ahora >= self.max_peticiones_por_minuto:
            tiempo_espera = 60 - (ahora - self.peticiones_por_dominio[dominio][0])
            if tiempo_espera > 0:
                time.sleep(tiempo_espera)
        
        # Espera base
        try:
            espera = float(self.espera_var.get())
        except:
            espera = 3
            
        if self.modo_lento.get():
            espera *= 2
        
        time.sleep(random.uniform(espera * 0.8, espera * 1.2))
        
        # Registrar petición
        self.peticiones_por_dominio[dominio].append(time.time())
    
    def obtener_imagenes_con_metadatos(self, url):
        """Obtiene imágenes y sus metadatos"""
        try:
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
            respuesta = requests.get(url, headers=headers, timeout=15)
            
            soup = BeautifulSoup(respuesta.text, 'html.parser')
            
            # Extraer metadatos de la página
            metadatos_pagina = self.extraer_metadatos_pagina(soup)
            
            # Encontrar todas las imágenes
            imagenes_info = []
            urls_vistas = set()
            
            for img in soup.find_all('img'):
                src = img.get('src')
                if not src:
                    continue
                
                url_completa = urljoin(url, src)
                
                # Evitar duplicados
                if url_completa in urls_vistas:
                    continue
                urls_vistas.add(url_completa)
                
                # Solo imágenes con extensiones comunes
                if any(url_completa.lower().endswith(ext) for ext in 
                      ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp']):
                    
                    # Extraer metadatos de esta imagen
                    metadatos_img = self.extraer_metadatos_img(img, url_completa)
                    imagenes_info.append({
                        'url': url_completa,
                        'metadatos': metadatos_img,
                        'metadatos_pagina': metadatos_pagina
                    })
            
            self.log(f"📸 Encontradas {len(imagenes_info)} imágenes con metadatos", 'exito')
            return imagenes_info
            
        except Exception as e:
            self.log(f"❌ Error analizando web: {str(e)}", 'error')
            return []
    
    def descargar_con_calidad(self, img_info, carpeta, indice, total):
        """Descarga una imagen aplicando filtros de calidad"""
        
        url_img = img_info['url']
        metadatos = img_info['metadatos']
        
        # Headers
        headers = {
            'User-Agent': random.choice([
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            ]),
            'Accept': 'image/webp,image/apng,image/*,*/*;q=0.8',
            'Referer': self.url.get(),
        }
        
        # Hacer HEAD request para obtener tamaño
        try:
            head = requests.head(url_img, timeout=10, headers=headers)
            tamaño = int(head.headers.get('content-length', 0))
        except:
            tamaño = 0
        
        # Verificar filtros de calidad
        cumple, razon = self.cumple_filtros_calidad(url_img, tamaño)
        if not cumple:
            self.log(f"    ⏭️ {indice}/{total}: Descartada - {razon}", 'calidad')
            return False, f"Descartada por calidad: {razon}"
        
        # Esperar según dominio
        self.esperar_segun_dominio(url_img)
        
        # Descargar
        try:
            respuesta = requests.get(url_img, timeout=15, headers=headers)
            
            if respuesta.status_code == 429:
                self.errores_429 += 1
                return False, "429 Too Many Requests"
            
            if respuesta.status_code != 200:
                return False, f"HTTP {respuesta.status_code}"
            
            # Guardar imagen
            exito, nombre_archivo, ruta = self.guardar_imagen(respuesta.content, carpeta, metadatos)
            
            if exito and self.guardar_metadatos.get():
                # Añadir metadatos EXIF si se solicita
                if self.guardar_exif.get():
                    exif = self.guardar_metadatos_exif(ruta)
                    metadatos['exif'] = exif
                
                # Guardar metadatos individuales
                ruta_meta = ruta + '.json'
                with open(ruta_meta, 'w', encoding='utf-8') as f:
                    json.dump({
                        'imagen': metadatos,
                        'pagina': img_info['metadatos_pagina'],
                        'archivo': nombre_archivo,
                        'tamaño_bytes': len(respuesta.content),
                    }, f, indent=2, ensure_ascii=False)
                
                self.metadatos_guardados.append({
                    'archivo': nombre_archivo,
                    'ruta': ruta,
                    'metadatos': metadatos,
                    'pagina': img_info['metadatos_pagina']
                })
            
            return True, nombre_archivo
            
        except Exception as e:
            return False, str(e)
    
    def guardar_imagen(self, data, carpeta, metadatos):
        """Guarda la imagen con nombre basado en metadatos"""
        
        # Detectar formato
        if data.startswith(b'\xff\xd8'):
            extension = '.jpg'
        elif data.startswith(b'\x89PNG'):
            extension = '.png'
        elif data.startswith(b'GIF87a') or data.startswith(b'GIF89a'):
            extension = '.gif'
        elif data.startswith(b'RIFF') and len(data) > 12 and data[8:12] == b'WEBP':
            extension = '.webp'
        elif data.startswith(b'BM'):
            extension = '.bmp'
        else:
            extension = '.jpg'
        
        # Generar nombre a partir de metadatos
        if metadatos.get('alt') and metadatos['alt'].strip():
            nombre_base = re.sub(r'[^\w\s-]', '', metadatos['alt'])[:40]
            nombre_base = re.sub(r'[-\s]+', '_', nombre_base)
        elif metadatos.get('title') and metadatos['title'].strip():
            nombre_base = re.sub(r'[^\w\s-]', '', metadatos['title'])[:40]
            nombre_base = re.sub(r'[-\s]+', '_', nombre_base)
        else:
            # Extraer de la URL
            path = urlparse(metadatos['url']).path
            nombre_base = os.path.basename(path)
            if not nombre_base or '.' not in nombre_base:
                nombre_base = f"imagen_{int(time.time())}"
            else:
                nombre_base = os.path.splitext(nombre_base)[0]
                nombre_base = re.sub(r'[^\w\.-]', '', nombre_base)[:40]
        
        if not nombre_base:
            nombre_base = f"imagen_{int(time.time())}"
        
        nombre_final = f"{nombre_base}{extension}"
        ruta = os.path.join(carpeta, nombre_final)
        
        # Evitar duplicados
        contador = 1
        while os.path.exists(ruta):
            nombre_final = f"{nombre_base}_{contador}{extension}"
            ruta = os.path.join(carpeta, nombre_final)
            contador += 1
        
        # Guardar
        with open(ruta, 'wb') as f:
            f.write(data)
        
        # Verificar
        try:
            with Image.open(ruta) as img:
                img.verify()
            return True, nombre_final, ruta
        except:
            os.remove(ruta)
            return False, "Imagen corrupta", None
    
    def iniciar_descarga(self):
        """Inicia el proceso de descarga"""
        if not self.url.get():
            messagebox.showwarning("URL requerida", "Por favor, introduce una URL")
            return
        
        url = self.url.get()
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
            self.url.set(url)
        
        # Resetear estadísticas
        self.descargadas = 0
        self.fallidas = 0
        self.errores_429 = 0
        self.metadatos_guardados = []
        
        self.descargando = True
        self.btn_descargar.config(state=tk.DISABLED)
        self.btn_cancelar.config(state=tk.NORMAL)
        self.btn_reparar.config(state=tk.DISABLED)
        self.btn_metadatos.config(state=tk.DISABLED)
        self.log_area.delete(1.0, tk.END)
        self.progreso['value'] = 0
        
        thread = Thread(target=self.proceso_descarga)
        thread.daemon = True
        thread.start()
    
    def cancelar_descarga(self):
        """Cancela la descarga"""
        self.descargando = False
        self.log("⏹️ Cancelando descarga...", 'warning')
    
    def proceso_descarga(self):
        """Proceso principal de descarga"""
        try:
            url = self.url.get()
            carpeta = self.carpeta_destino.get()
            
            self.log(f"🌐 Analizando: {url}", 'info')
            self.log(f"⚡ Filtros de calidad activados", 'calidad')
            os.makedirs(carpeta, exist_ok=True)
            
            # Obtener imágenes con metadatos
            imagenes_info = self.obtener_imagenes_con_metadatos(url)
            
            if not imagenes_info:
                self.log("❌ No se encontraron imágenes", 'error')
                self.finalizar_descarga()
                return
            
            total = len(imagenes_info)
            self.log(f"📸 Procesando {total} imágenes con filtros de calidad...", 'info')
            
            # Descargar
            for i, img_info in enumerate(imagenes_info, 1):
                if not self.descargando:
                    break
                
                # Descargar con calidad
                exito, resultado = self.descargar_con_calidad(img_info, carpeta, i, total)
                
                if exito:
                    self.log(f"    ✅ {i}/{total}: {resultado}", 'exito')
                    self.descargadas += 1
                else:
                    if "429" in resultado:
                        self.log(f"    ⚠️ {i}/{total}: {resultado}", '429')
                    else:
                        self.log(f"    ❌ {i}/{total}: {resultado}", 'error')
                    self.fallidas += 1
                
                # Actualizar progreso
                progreso = (i / total) * 100
                self.progreso['value'] = progreso
                self.stats_label.config(
                    text=f"📊 {i}/{total} | ✅ {self.descargadas} | ❌ {self.fallidas} | 429: {self.errores_429}")
                self.root.update_idletasks()
            
            # Guardar metadatos globales
            if self.guardar_json.get() and self.metadatos_guardados:
                ruta_json = self.guardar_metadatos_json(carpeta, self.metadatos_guardados)
                self.log(f"📋 JSON global guardado en: {ruta_json}", 'metadata')
            
            # Resumen
            self.log(f"\n✨ Proceso completado!", 'exito')
            self.log(f"   ✅ Descargadas: {self.descargadas}", 'exito')
            self.log(f"   ❌ Fallidas: {self.fallidas}", 'error')
            self.log(f"   ⚠️ Errores 429: {self.errores_429}", 'warning')
            self.log(f"   📋 Imágenes con metadatos: {len(self.metadatos_guardados)}", 'metadata')
            
            messagebox.showinfo("Completado", 
                               f"✅ {self.descargadas} descargadas\n"
                               f"📋 {len(self.metadatos_guardados)} con metadatos\n"
                               f"❌ {self.fallidas} fallidas")
            
        except Exception as e:
            self.log(f"❌ Error general: {str(e)}", 'error')
            messagebox.showerror("Error", f"Error: {str(e)}")
        finally:
            self.finalizar_descarga()
    
    def ver_metadatos(self):
        """Muestra los metadatos guardados"""
        if not self.metadatos_guardados:
            messagebox.showinfo("Metadatos", "No hay metadatos guardados aún")
            return
        
        # Crear ventana de metadatos
        meta_win = tk.Toplevel(self.root)
        meta_win.title("📋 Metadatos guardados")
        meta_win.geometry("600x400")
        
        text_area = scrolledtext.ScrolledText(meta_win, font=('Courier', 10))
        text_area.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Configurar tags para colores
        text_area.tag_config('archivo', foreground='blue', font=('Courier', 10, 'bold'))
        
        # Mostrar metadatos
        for item in self.metadatos_guardados:
            text_area.insert(tk.END, f"📸 {item['archivo']}\n", 'archivo')
            text_area.insert(tk.END, f"   Alt: {item['metadatos'].get('alt', 'N/A')}\n")
            text_area.insert(tk.END, f"   Title: {item['metadatos'].get('title', 'N/A')}\n")
            if 'exif' in item['metadatos']:
                text_area.insert(tk.END, f"   EXIF: {len(item['metadatos']['exif'])} campos\n")
            text_area.insert(tk.END, "-" * 50 + "\n")
    
    def reparar_carpeta(self):
        """Repara imágenes en una carpeta"""
        carpeta = filedialog.askdirectory(title="Seleccionar carpeta con imágenes")
        if not carpeta:
            return
        
        self.log(f"\n🔧 Reparando imágenes en: {carpeta}", 'info')
        reparadas = 0
        corruptas = 0
        
        for archivo in os.listdir(carpeta):
            ruta = os.path.join(carpeta, archivo)
            if os.path.isfile(ruta) and archivo.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.webp')):
                try:
                    with Image.open(ruta) as img:
                        # Intentar guardar de nuevo
                        img.save(ruta)
                        self.log(f"  ✅ {archivo}", 'exito')
                        reparadas += 1
                except:
                    self.log(f"  ❌ {archivo} (corrupta)", 'error')
                    corruptas += 1
        
        self.log(f"\n✨ Reparación completada:", 'exito')
        self.log(f"   ✅ Reparadas: {reparadas}", 'exito')
        self.log(f"   ❌ Corruptas: {corruptas}", 'error')
        
        messagebox.showinfo("Reparación", f"✅ {reparadas} reparadas\n❌ {corruptas} corruptas")
    
    def finalizar_descarga(self):
        """Vuelve al estado inicial"""
        self.descargando = False
        self.btn_descargar.config(state=tk.NORMAL)
        self.btn_cancelar.config(state=tk.DISABLED)
        self.btn_reparar.config(state=tk.NORMAL)
        self.btn_metadatos.config(state=tk.NORMAL if self.metadatos_guardados else tk.DISABLED)
        self.progreso['value'] = 0

def main():
    """Función principal"""
    if not DEPENDENCIAS_OK:
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror(
            "Error de dependencias",
            f"Faltan dependencias: {ERROR_DEP}\n\n"
            "Instala los requisitos:\n"
            "pip install requests pillow beautifulsoup4"
        )
        return
    
    try:
        root = tk.Tk()
        app = DescargadorPremium(root)
        root.mainloop()
    except Exception as e:
        messagebox.showerror("Error", f"Error al iniciar: {str(e)}")

if __name__ == "__main__":
    main()