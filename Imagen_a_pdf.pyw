import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk
import os

class ConversorImagenesPDF:
    def __init__(self, root):
        self.root = root
        self.root.title("Conversor Imágenes a PDF")
        
        ancho = 900
        alto = 700
        
        pos_x = (self.root.winfo_screenwidth() // 2) - (ancho // 2)
        self.root.geometry(f"{ancho}x{alto}+{pos_x}+20")
        
        self.imagenes = []
        self.miniaturas = []  # Para mantener referencia a las miniaturas
        
        # Frame principal
        main_frame = tk.Frame(root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Frame superior para botones
        top_frame = tk.Frame(main_frame)
        top_frame.pack(fill=tk.X, pady=5)
        
        # Botones
        tk.Button(top_frame, text="Seleccionar Imágenes", 
                 command=self.seleccionar_imagenes, 
                 bg="blue", fg="white", padx=10, pady=5).pack(side=tk.LEFT, padx=5)
        
        tk.Button(top_frame, text="Seleccionar Carpeta", 
                 command=self.seleccionar_carpeta, 
                 bg="green", fg="white", padx=10, pady=5).pack(side=tk.LEFT, padx=5)
        
        tk.Button(top_frame, text="Añadir más imágenes", 
                 command=self.anadir_imagenes, 
                 bg="orange", fg="black", padx=10, pady=5).pack(side=tk.LEFT, padx=5)
        
        # Frame para el visor de miniaturas
        visor_frame = tk.Frame(main_frame)
        visor_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        # Canvas y scrollbars para el visor de miniaturas
        self.canvas = tk.Canvas(visor_frame, bg='#f0f0f0')
        scrollbar_y = tk.Scrollbar(visor_frame, orient=tk.VERTICAL, command=self.canvas.yview)
        scrollbar_x = tk.Scrollbar(visor_frame, orient=tk.HORIZONTAL, command=self.canvas.xview)
        
        # Frame contenedor para las miniaturas
        self.miniaturas_frame = tk.Frame(self.canvas, bg='#f0f0f0')
        self.miniaturas_frame.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        
        self.canvas.create_window((0, 0), window=self.miniaturas_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=scrollbar_y.set, xscrollcommand=scrollbar_x.set)
        
        # Empaquetar canvas y scrollbars
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar_y.pack(side=tk.RIGHT, fill=tk.Y)
        scrollbar_x.pack(side=tk.BOTTOM, fill=tk.X)
        
        # Frame inferior para controles
        bottom_frame = tk.Frame(main_frame)
        bottom_frame.pack(fill=tk.X, pady=10)
        
        # Botones de ordenamiento
        orden_frame = tk.Frame(bottom_frame)
        orden_frame.pack(side=tk.LEFT, padx=5)
        
        tk.Button(orden_frame, text="▲ Subir", command=self.subir_imagen,
                 bg="orange", fg="black", padx=10, pady=5).pack(side=tk.LEFT, padx=2)
        
        tk.Button(orden_frame, text="▼ Bajar", command=self.bajar_imagen,
                 bg="orange", fg="black", padx=10, pady=5).pack(side=tk.LEFT, padx=2)
        
        tk.Button(orden_frame, text="Ordenar por nombre", command=self.ordenar_por_nombre,
                 bg="purple", fg="white", padx=10, pady=5).pack(side=tk.LEFT, padx=2)
        
        tk.Button(orden_frame, text="Eliminar seleccionada", command=self.eliminar_imagen,
                 bg="red", fg="white", padx=10, pady=5).pack(side=tk.LEFT, padx=2)
        
        tk.Button(orden_frame, text="Limpiar todo", command=self.limpiar_todo,
                 bg="gray", fg="white", padx=10, pady=5).pack(side=tk.LEFT, padx=2)
        
        # Contador de imágenes
        self.contador_label = tk.Label(bottom_frame, text="0 imágenes", font=('Arial', 10, 'bold'))
        self.contador_label.pack(side=tk.RIGHT, padx=20)
        
        # Botón convertir
        tk.Button(bottom_frame, text="Convertir a PDF", 
                 command=self.convertir_a_pdf, 
                 bg="red", fg="white", padx=20, pady=10).pack(side=tk.RIGHT, padx=5)
        
        # Variable para almacenar la miniatura seleccionada
        self.seleccion_actual = None
        self.borde_seleccion = None
        self.indice_seleccionado = -1
        
        # Habilitar scroll con rueda del mouse
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)
    
    def _on_mousewheel(self, event):
        self.canvas.yview_scroll(int(-1*(event.delta/120)), "units")
    
    def seleccionar_imagenes(self):
        archivos = filedialog.askopenfilenames(
            title="Seleccionar imágenes",
            filetypes=[
                ("Imágenes", "*.jpg *.jpeg *.png *.bmp *.gif *.tiff *.webp"),
                ("Todos los archivos", "*.*")
            ]
        )
        if archivos:
            self.imagenes = list(archivos)
            self.actualizar_miniaturas()
    
    def anadir_imagenes(self):
        """Añade más imágenes a la lista existente"""
        archivos = filedialog.askopenfilenames(
            title="Añadir más imágenes",
            filetypes=[
                ("Imágenes", "*.jpg *.jpeg *.png *.bmp *.gif *.tiff *.webp"),
                ("Todos los archivos", "*.*")
            ]
        )
        if archivos:
            # Añadir las nuevas imágenes a la lista existente
            for archivo in archivos:
                if archivo not in self.imagenes:  # Evitar duplicados
                    self.imagenes.append(archivo)
            self.actualizar_miniaturas()
    
    def seleccionar_carpeta(self):
        carpeta = filedialog.askdirectory(title="Seleccionar carpeta con imágenes")
        if carpeta:
            extensiones = {'.jpg', '.jpeg', '.png', '.bmp', '.gif', '.tiff', '.webp'}
            self.imagenes = []
            for archivo in os.listdir(carpeta):
                ext = os.path.splitext(archivo)[1].lower()
                if ext in extensiones:
                    self.imagenes.append(os.path.join(carpeta, archivo))
            self.imagenes.sort()
            self.actualizar_miniaturas()
    
    def crear_miniatura(self, img_path, size=(150, 150)):
        """Crea una miniatura de la imagen"""
        try:
            # Verificar que el archivo existe
            if not os.path.exists(img_path):
                print(f"El archivo no existe: {img_path}")
                return None
                
            imagen = Image.open(img_path)
            imagen.thumbnail(size, Image.Resampling.LANCZOS)
            return ImageTk.PhotoImage(imagen)
        except Exception as e:
            print(f"Error al crear miniatura para {img_path}: {e}")
            return None
    
    def actualizar_miniaturas(self):
        """Actualiza el visor de miniaturas"""
        # Limpiar frame de miniaturas
        for widget in self.miniaturas_frame.winfo_children():
            widget.destroy()
        
        self.miniaturas = []  # Limpiar lista de miniaturas
        self.seleccion_actual = None
        self.indice_seleccionado = -1
        
        # Actualizar contador
        self.contador_label.config(text=f"{len(self.imagenes)} imágenes")
        
        if not self.imagenes:
            # Mostrar mensaje si no hay imágenes
            mensaje = tk.Label(self.miniaturas_frame, text="No hay imágenes seleccionadas", 
                              font=('Arial', 14), fg='gray', bg='#f0f0f0')
            mensaje.pack(pady=50)
            return
        
        # Crear miniaturas en grid
        fila = 0
        columna = 0
        max_columnas = 5  # Número de miniaturas por fila
        
        for i, img_path in enumerate(self.imagenes):
            # Frame para cada miniatura con su nombre
            miniatura_frame = tk.Frame(self.miniaturas_frame, bg='white', relief=tk.RAISED, borderwidth=1)
            miniatura_frame.grid(row=fila, column=columna, padx=5, pady=5, sticky="n")
            
            # Crear y mostrar miniatura
            foto = self.crear_miniatura(img_path)
            if foto:
                self.miniaturas.append(foto)  # Guardar referencia
                
                # Label para la imagen
                img_label = tk.Label(miniatura_frame, image=foto, bg='white', cursor="hand2")
                img_label.pack(padx=2, pady=2)
                
                # Nombre del archivo (truncado si es muy largo)
                nombre = os.path.basename(img_path)
                if len(nombre) > 20:
                    nombre = nombre[:17] + "..."
                
                tk.Label(miniatura_frame, text=nombre, bg='white', font=('Arial', 8)).pack(padx=2, pady=2)
                
                # Bind events para selección
                img_label.bind("<Button-1>", lambda e, idx=i, f=miniatura_frame: self.seleccionar_miniatura(idx, f))
                miniatura_frame.bind("<Button-1>", lambda e, idx=i, f=miniatura_frame: self.seleccionar_miniatura(idx, f))
                
                # Doble clic para ver información
                img_label.bind("<Double-Button-1>", lambda e, path=img_path: self.mostrar_info(path))
            else:
                # Si no se pudo crear la miniatura, mostrar un placeholder
                placeholder = tk.Label(miniatura_frame, text="❌ Error\n{0}".format(os.path.basename(img_path)[:15]), 
                                      bg='lightgray', width=15, height=8)
                placeholder.pack(padx=2, pady=2)
                
                # Botón para eliminar esta imagen
                eliminar_btn = tk.Button(miniatura_frame, text="Eliminar", 
                                       command=lambda idx=i: self.eliminar_imagen_especifica(idx),
                                       bg='red', fg='white', font=('Arial', 8))
                eliminar_btn.pack(pady=2)
            
            # Actualizar posición en grid
            columna += 1
            if columna >= max_columnas:
                columna = 0
                fila += 1
    
    def mostrar_info(self, ruta):
        """Muestra información de la imagen"""
        try:
            imagen = Image.open(ruta)
            info = f"Archivo: {os.path.basename(ruta)}\n"
            info += f"Ruta: {ruta}\n"
            info += f"Dimensiones: {imagen.size[0]} x {imagen.size[1]} píxeles\n"
            info += f"Formato: {imagen.format}\n"
            info += f"Modo: {imagen.mode}"
            
            messagebox.showinfo("Información de la imagen", info)
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo leer la imagen: {e}")
    
    def eliminar_imagen_especifica(self, indice):
        """Elimina una imagen específica por su índice"""
        if 0 <= indice < len(self.imagenes):
            del self.imagenes[indice]
            self.actualizar_miniaturas()
    
    def seleccionar_miniatura(self, indice, frame):
        """Selecciona una miniatura y resalta el borde"""
        # Quitar selección anterior
        if self.seleccion_actual is not None and self.seleccion_actual.winfo_exists():
            try:
                self.seleccion_actual.config(relief=tk.RAISED, borderwidth=1, highlightbackground="white")
            except:
                pass
        
        # Seleccionar nueva miniatura
        self.seleccion_actual = frame
        self.seleccion_actual.config(relief=tk.SOLID, borderwidth=3, highlightbackground="blue", highlightcolor="blue")
        self.indice_seleccionado = indice
    
    def subir_imagen(self):
        """Mueve la imagen seleccionada hacia arriba"""
        if hasattr(self, 'indice_seleccionado') and self.indice_seleccionado > 0:
            idx = self.indice_seleccionado
            self.imagenes[idx], self.imagenes[idx-1] = self.imagenes[idx-1], self.imagenes[idx]
            self.actualizar_miniaturas()
            # Seleccionar la misma imagen en su nueva posición
            self.root.after(100, lambda: self.seleccionar_por_indice(idx-1))
    
    def bajar_imagen(self):
        """Mueve la imagen seleccionada hacia abajo"""
        if hasattr(self, 'indice_seleccionado') and self.indice_seleccionado < len(self.imagenes) - 1:
            idx = self.indice_seleccionado
            self.imagenes[idx], self.imagenes[idx+1] = self.imagenes[idx+1], self.imagenes[idx]
            self.actualizar_miniaturas()
            # Seleccionar la misma imagen en su nueva posición
            self.root.after(100, lambda: self.seleccionar_por_indice(idx+1))
    
    def ordenar_por_nombre(self):
        """Ordena las imágenes por nombre"""
        self.imagenes.sort(key=lambda x: os.path.basename(x).lower())
        self.actualizar_miniaturas()
    
    def eliminar_imagen(self):
        """Elimina la imagen seleccionada de la lista"""
        if hasattr(self, 'indice_seleccionado') and self.indice_seleccionado >= 0:
            idx = self.indice_seleccionado
            if 0 <= idx < len(self.imagenes):
                del self.imagenes[idx]
                self.actualizar_miniaturas()
                if self.imagenes:
                    nuevo_idx = min(idx, len(self.imagenes)-1)
                    self.root.after(100, lambda: self.seleccionar_por_indice(nuevo_idx))
    
    def limpiar_todo(self):
        """Limpia todas las imágenes"""
        if messagebox.askyesno("Confirmar", "¿Estás seguro de que quieres eliminar todas las imágenes?"):
            self.imagenes = []
            self.actualizar_miniaturas()
    
    def seleccionar_por_indice(self, indice):
        """Selecciona una miniatura por su índice"""
        if 0 <= indice < len(self.miniaturas_frame.winfo_children()):
            frames = self.miniaturas_frame.winfo_children()
            if indice < len(frames):
                # Buscar el frame que contiene la imagen (no el mensaje de error)
                frame_valido = None
                for i, frame in enumerate(frames):
                    if i == indice and frame.winfo_children():
                        frame_valido = frame
                        break
                
                if frame_valido:
                    self.seleccionar_miniatura(indice, frame_valido)
    
    def convertir_a_pdf(self):
        if not self.imagenes:
            messagebox.showwarning("Advertencia", "No hay imágenes seleccionadas")
            return
        
        archivo_salida = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDF", "*.pdf")],
            title="Guardar PDF como"
        )
        
        if archivo_salida:
            try:
                imagenes_procesadas = []
                imagenes_fallidas = []
                
                for img_path in self.imagenes:
                    try:
                        if not os.path.exists(img_path):
                            imagenes_fallidas.append(f"{img_path} (archivo no encontrado)")
                            continue
                            
                        imagen = Image.open(img_path)
                        if imagen.mode != 'RGB':
                            imagen = imagen.convert('RGB')
                        imagenes_procesadas.append(imagen)
                    except Exception as e:
                        imagenes_fallidas.append(f"{img_path} ({str(e)})")
                
                if not imagenes_procesadas:
                    messagebox.showerror("Error", "No se pudo procesar ninguna imagen")
                    return
                
                if imagenes_fallidas:
                    msg = f"No se pudieron procesar {len(imagenes_fallidas)} imágenes:\n"
                    msg += "\n".join(imagenes_fallidas[:5])
                    if len(imagenes_fallidas) > 5:
                        msg += f"\n... y {len(imagenes_fallidas)-5} más"
                    
                    if not messagebox.askyesno("Advertencia", msg + "\n\n¿Continuar con las imágenes válidas?"):
                        return
                
                # Crear PDF
                primera_imagen = imagenes_procesadas[0]
                if len(imagenes_procesadas) > 1:
                    primera_imagen.save(
                        archivo_salida,
                        save_all=True,
                        append_images=imagenes_procesadas[1:]
                    )
                else:
                    primera_imagen.save(archivo_salida)
                
                # Cerrar todas las imágenes para liberar memoria
                for img in imagenes_procesadas:
                    img.close()
                
                total_validas = len(imagenes_procesadas)
                total_original = len(self.imagenes)
                
                if total_validas == total_original:
                    messagebox.showinfo("Éxito", f"PDF creado correctamente:\n{archivo_salida}")
                else:
                    messagebox.showwarning("Advertencia", 
                        f"PDF creado con {total_validas} de {total_original} imágenes:\n{archivo_salida}")
                
            except Exception as e:
                messagebox.showerror("Error", f"Error al crear PDF: {e}")

if __name__ == "__main__":
    root = tk.Tk()
    app = ConversorImagenesPDF(root)
    root.mainloop()