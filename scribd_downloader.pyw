#!/usr/bin/env python3
# scribd.pyw - Descargador de Scribd (con mejora de calidad)

import sys
import os
import re
import json
import shutil
import requests
import img2pdf
from bs4 import BeautifulSoup

# Intentar importar PIL para mejorar calidad
try:
    from PIL import Image, ImageEnhance
    PIL_DISPONIBLE = True
except ImportError:
    PIL_DISPONIBLE = False

# ============================================================
# CONFIGURACIÓN
# ============================================================

CONFIG_FILE = os.path.join(os.path.dirname(__file__), "config.json")

def get_config():
    default = {
        "carpeta": os.path.join(os.path.expanduser("~"), "Downloads", "Scribd"),
        "mejorar_calidad": True,  # Nueva opción
        "factor_escala": 2  # Factor de aumento (2 = doble tamaño)
    }
    
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                return json.load(f)
        except:
            pass
    
    os.makedirs(default["carpeta"], exist_ok=True)
    guardar_config(default)
    return default

def guardar_config(config):
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=2)

# ============================================================
# DESCARGADOR MEJORADO
# ============================================================

class ScribdDownloader:
    def __init__(self, carpeta=None, callback=None, mejorar_calidad=True):
        self.callback = callback
        self.carpeta = carpeta or get_config()["carpeta"]
        self.images_dir = os.path.join(self.carpeta, "images")
        self.images = []
        self.total = 0
        self.mejorar_calidad = mejorar_calidad
        
        os.makedirs(self.images_dir, exist_ok=True)
        os.makedirs(self.carpeta, exist_ok=True)
    
    def log(self, msg):
        if self.callback:
            self.callback(msg)
    
    def limpiar_imagenes(self):
        try:
            if os.path.exists(self.images_dir):
                shutil.rmtree(self.images_dir)
                self.log("🧹 Imágenes temporales eliminadas")
                return True
        except Exception as e:
            self.log(f"⚠️ No se pudo eliminar: {e}")
            return False
    
    def mejorar_imagen(self, path):
        """Mejora la calidad de la imagen usando PIL"""
        if not PIL_DISPONIBLE:
            return False
        
        try:
            img = Image.open(path)
            
            # Aumentar tamaño (x2 para mejor calidad)
            factor = 2
            new_size = (img.width * factor, img.height * factor)
            img = img.resize(new_size, Image.Resampling.LANCZOS)
            
            # Mejorar nitidez
            enhancer = ImageEnhance.Sharpness(img)
            img = enhancer.enhance(1.5)
            
            # Mejorar contraste
            enhancer = ImageEnhance.Contrast(img)
            img = enhancer.enhance(1.2)
            
            # Guardar con alta calidad
            img.save(path, quality=95, optimize=True)
            return True
        except Exception as e:
            self.log(f"⚠️ No se pudo mejorar calidad: {e}")
            return False
    
    def get_total_pages(self, url):
        try:
            soup = BeautifulSoup(requests.get(url).text, "html.parser")
            span = soup.find("span", {"data-e2e": "total-pages"})
            if span:
                return int(span.get_text().replace("/", "").strip())
        except:
            pass
        return None
    
    def save_image(self, content, page_num):
        path = os.path.join(self.images_dir, f"{page_num}.jpg")
        
        if content.endswith(".jsonp"):
            content = content.replace("/pages/", "/images/").replace(".jsonp", ".jpg")
            
            # Intentar obtener imágenes de mayor calidad
            # Algunos servidores responden a parámetros de calidad
            if '?' not in content:
                content += "?quality=high&width=2000"
        
        try:
            # Descargar imagen
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            r = requests.get(content, stream=True, headers=headers)
            with open(path, "wb") as f:
                shutil.copyfileobj(r.raw, f)
            
            # MEJORAR CALIDAD si está activado
            if self.mejorar_calidad:
                self.mejorar_imagen(path)
            
            self.images.append(path)
            self.log(f"📄 Página {page_num}/{self.total}")
            return True
        except Exception as e:
            self.log(f"⚠️ Error página {page_num}: {e}")
            return False
    
    def save_text(self, jsonp, filename):
        try:
            r = requests.get(jsonp).text
            page = r[11:12]
            texto = (r.replace(f'window.page{page}_callback(["', '')
                     .replace("\\n", "").replace("\\", "").replace('"]);', ''))
            
            soup = BeautifulSoup(texto, "html.parser")
            with open(filename, "a", encoding="utf-8") as f:
                for span in soup.find_all("span", {"class": "a"}):
                    f.write(span.get_text() + "\n")
            self.log(f"📝 Página extraída")
            return True
        except:
            return False
    
    def sanitize_title(self, title):
        for ch in r' *\"/\\<>:|(),':
            title = title.replace(ch, "_")
        return title
    
    def convert_to_pdf(self, title):
        if not self.images:
            return None
        sorted_imgs = sorted(self.images, key=lambda x: int(os.path.basename(x).split('.')[0]))
        pdf_path = os.path.join(self.carpeta, f"{title}.pdf")
        
        # Configurar img2pdf para mejor calidad
        with open(pdf_path, "wb") as f:
            f.write(img2pdf.convert(sorted_imgs))
        
        return pdf_path
    
    def download(self, url, mode="pdf"):
        self.log("🚀 Descargando...")
        self.images = []
        
        if self.mejorar_calidad and PIL_DISPONIBLE:
            self.log("✨ Mejora de calidad activada (x2)")
        elif self.mejorar_calidad and not PIL_DISPONIBLE:
            self.log("⚠️ PIL no instalado. Instala: pip install Pillow")
        
        try:
            html = requests.get(url).text
            soup = BeautifulSoup(html, "html.parser")
            
            self.total = self.get_total_pages(url) or "?"
            title = self.sanitize_title(soup.find("title").get_text())
            self.log(f"📖 {title}")
            
            if mode == "pdf":
                # Descargar imágenes
                for img in soup.find_all("img", {"class": "absimg"}, src=True):
                    self.save_image(img["src"], len(self.images) + 1)
                
                for script in soup.find_all("script", type="text/javascript"):
                    if script.string:
                        for jsonp in re.findall(r"https://.*?\.jsonp", script.string):
                            self.save_image(jsonp, len(self.images) + 1)
                
                # Crear PDF
                pdf = self.convert_to_pdf(title)
                
                # Limpiar imágenes temporales
                self.limpiar_imagenes()
                
                if pdf:
                    self.log(f"✅ PDF guardado en: {pdf}")
                    if self.mejorar_calidad and PIL_DISPONIBLE:
                        self.log("✨ Calidad mejorada aplicada")
                    return pdf
                else:
                    self.log("❌ Error al crear el PDF")
                    return None
            
            else:  # Modo texto
                txt_path = os.path.join(self.carpeta, f"{title}.txt")
                for script in soup.find_all("script", type="text/javascript"):
                    if script.string:
                        for jsonp in re.findall(r"https://.*?\.jsonp", script.string):
                            self.save_text(jsonp, txt_path)
                
                self.limpiar_imagenes()
                self.log(f"✅ Texto guardado en: {txt_path}")
                return txt_path
                
        except Exception as e:
            self.log(f"❌ Error: {e}")
            try:
                self.limpiar_imagenes()
            except:
                pass
            return None

# ============================================================
# INTERFAZ GRÁFICA (con opción de calidad)
# ============================================================

def main():
    try:
        import tkinter as tk
        from tkinter import ttk, scrolledtext, filedialog, messagebox
        import threading
    except ImportError:
        try:
            import ctypes
            ctypes.MessageBoxW(0, "Tkinter no está instalado.\nEn Linux: sudo apt install python3-tk", "Error", 0x10)
        except:
            pass
        return
    
    class App:
        def __init__(self):
            self.root = tk.Tk()
            self.root.title("Scribd Downloader - Mejorado")
            self.root.geometry("680x560")
            
            try:
                self.root.iconbitmap(default='scribd.ico')
            except:
                pass
            
            self.config = get_config()
            self.carpeta = self.config["carpeta"]
            self.mejorar_calidad = self.config.get("mejorar_calidad", True)
            self.descargando = False
            
            self.crear_widgets()
            
            # Centrar ventana
            self.root.update_idletasks()
            w = self.root.winfo_width()
            h = self.root.winfo_height()
            x = (self.root.winfo_screenwidth() // 2) - (w // 2)
            y = (self.root.winfo_screenheight() // 2) - (h // 2)
            self.root.geometry(f'{w}x{h}+{x}+{y}')
            
            self.root.mainloop()
        
        def crear_widgets(self):
            # URL
            frame = ttk.LabelFrame(self.root, text="📎 URL del documento", padding=10)
            frame.pack(fill=tk.X, padx=10, pady=5)
            
            row = ttk.Frame(frame)
            row.pack(fill=tk.X)
            
            self.url = ttk.Entry(row, font=('Arial', 10))
            self.url.pack(side=tk.LEFT, fill=tk.X, expand=True)
            
            ttk.Button(row, text="📋 Pegar", command=self.pegar).pack(side=tk.RIGHT, padx=5)
            
            # Carpeta
            frame = ttk.LabelFrame(self.root, text="📂 Carpeta de descarga", padding=10)
            frame.pack(fill=tk.X, padx=10, pady=5)
            
            row = ttk.Frame(frame)
            row.pack(fill=tk.X)
            
            self.label_carpeta = ttk.Label(row, text=self.carpeta, foreground='#0066cc')
            self.label_carpeta.pack(side=tk.LEFT, fill=tk.X, expand=True)
            
            ttk.Button(row, text="📁 Cambiar", command=self.cambiar_carpeta).pack(side=tk.RIGHT, padx=2)
            ttk.Button(row, text="📂 Abrir", command=self.abrir_carpeta).pack(side=tk.RIGHT, padx=2)
            
            # Opciones
            frame = ttk.LabelFrame(self.root, text="⚙️ Opciones", padding=10)
            frame.pack(fill=tk.X, padx=10, pady=5)
            
            # Modo de descarga
            self.modo = tk.StringVar(value="pdf")
            ttk.Radiobutton(frame, text="📸 PDF (imágenes)", variable=self.modo, value="pdf").pack(anchor=tk.W)
            ttk.Radiobutton(frame, text="📝 Solo texto", variable=self.modo, value="text").pack(anchor=tk.W)
            
            # Mejora de calidad (solo para PDF)
            calidad_frame = ttk.Frame(frame)
            calidad_frame.pack(anchor=tk.W, pady=5)
            
            self.calidad_var = tk.BooleanVar(value=self.mejorar_calidad)
            ttk.Checkbutton(
                calidad_frame,
                text="✨ Mejorar calidad (x2) - Requiere Pillow",
                variable=self.calidad_var
            ).pack(anchor=tk.W)
            
            # Verificar si Pillow está instalado
            try:
                import PIL
                ttk.Label(
                    calidad_frame,
                    text="✅ Pillow instalado",
                    foreground='green',
                    font=('Arial', 8)
                ).pack(anchor=tk.W)
            except ImportError:
                ttk.Label(
                    calidad_frame,
                    text="⚠️ Pillow no instalado. Instala: pip install Pillow",
                    foreground='orange',
                    font=('Arial', 8)
                ).pack(anchor=tk.W)
            
            # Botón descargar
            self.btn = ttk.Button(self.root, text="⬇️ DESCARGAR", command=self.iniciar)
            self.btn.pack(pady=10)
            
            # Progreso
            self.progress = ttk.Progressbar(self.root, mode='indeterminate')
            self.progress.pack(fill=tk.X, padx=10)
            
            # Log
            frame = ttk.LabelFrame(self.root, text="📋 Registro", padding=10)
            frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
            
            self.log = scrolledtext.ScrolledText(
                frame, 
                height=12, 
                font=('Consolas', 9), 
                bg='#1e1e1e', 
                fg='#d4d4d4'
            )
            self.log.pack(fill=tk.BOTH, expand=True)
            
            self.log.tag_config('ok', foreground='#4ec9b0')
            self.log.tag_config('error', foreground='#f44747')
            self.log.tag_config('info', foreground='#569cd6')
            self.log.tag_config('warning', foreground='#dcdcaa')
            
            self.escribir("💡 Bienvenido a Scribd Downloader", 'info')
            self.escribir(f"📂 Descargas en: {self.carpeta}", 'info')
            self.escribir("📌 Pega la URL y presiona Descargar", 'info')
            self.escribir("🧹 Las imágenes temporales se eliminan automáticamente", 'info')
        
        def pegar(self):
            try:
                url = self.root.clipboard_get()
                self.url.delete(0, tk.END)
                self.url.insert(0, url)
                self.escribir("📋 URL pegada", 'ok')
            except:
                self.escribir("❌ No se pudo pegar", 'error')
        
        def escribir(self, msg, tag=None):
            self.log.insert(tk.END, msg + "\n", tag)
            self.log.see(tk.END)
            self.root.update()
        
        def cambiar_carpeta(self):
            folder = filedialog.askdirectory(initialdir=self.carpeta)
            if folder:
                self.carpeta = folder
                self.config["carpeta"] = folder
                guardar_config(self.config)
                self.label_carpeta.config(text=folder)
                self.escribir(f"📂 Carpeta cambiada a: {folder}", 'ok')
        
        def abrir_carpeta(self):
            if os.path.exists(self.carpeta):
                os.startfile(self.carpeta)
            else:
                self.escribir(f"❌ La carpeta no existe", 'error')
        
        def iniciar(self):
            if self.descargando:
                return
            
            url = self.url.get().strip()
            if not url:
                self.escribir("❌ Ingresa una URL", 'error')
                return
            
            if 'scribd.com' not in url or not url.startswith('https://'):
                self.escribir("❌ URL inválida (debe ser de Scribd)", 'error')
                return
            
            # Guardar preferencia de calidad
            self.mejorar_calidad = self.calidad_var.get()
            self.config["mejorar_calidad"] = self.mejorar_calidad
            guardar_config(self.config)
            
            self.descargando = True
            self.btn.config(state=tk.DISABLED, text="⏳ DESCARGANDO...")
            self.progress.start()
            
            threading.Thread(target=self.descargar, args=(url,), daemon=True).start()
        
        def descargar(self, url):
            def log(msg):
                self.root.after(0, lambda: self.escribir(msg))
            
            downloader = ScribdDownloader(
                carpeta=self.carpeta, 
                callback=log,
                mejorar_calidad=self.mejorar_calidad
            )
            resultado = downloader.download(url, mode=self.modo.get())
            
            self.root.after(0, self.finalizar, resultado)
        
        def finalizar(self, resultado):
            self.descargando = False
            self.progress.stop()
            self.btn.config(state=tk.NORMAL, text="⬇️ DESCARGAR")
            
            if resultado:
                self.escribir(f"✅ ¡Descarga completada!", 'ok')
                self.escribir(f"📁 {resultado}", 'ok')
                if messagebox.askyesno("Completado", f"✅ Descargado en:\n{resultado}\n\n¿Abrir carpeta?"):
                    self.abrir_carpeta()
            else:
                self.escribir("❌ Falló la descarga", 'error')
    
    App()

# ============================================================
# PUNTO DE ENTRADA
# ============================================================

if __name__ == "__main__":
    main()