import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image
import os

class ConversorImagenesPDF:
    def __init__(self, root):
        self.root = root
        self.root.title("Conversor Imágenes a PDF")
        self.root.geometry("500x400")
        
        self.imagenes = []
        
        # Frame principal
        main_frame = tk.Frame(root, padx=10, pady=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Botones
        tk.Button(main_frame, text="Seleccionar Imágenes", 
                 command=self.seleccionar_imagenes, 
                 bg="blue", fg="white", padx=10, pady=5).pack(pady=5)
        
        tk.Button(main_frame, text="Seleccionar Carpeta", 
                 command=self.seleccionar_carpeta, 
                 bg="green", fg="white", padx=10, pady=5).pack(pady=5)
        
        # Lista de imágenes
        self.lista_frame = tk.Frame(main_frame)
        self.lista_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        self.lista_text = tk.Text(self.lista_frame, height=10, state='disabled')
        scrollbar = tk.Scrollbar(self.lista_frame)
        self.lista_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Botón convertir
        tk.Button(main_frame, text="Convertir a PDF", 
                 command=self.convertir_a_pdf, 
                 bg="red", fg="white", padx=20, pady=10).pack(pady=10)
    
    def seleccionar_imagenes(self):
        archivos = filedialog.askopenfilenames(
            title="Seleccionar imágenes",
            filetypes=[("Imágenes", "*.jpg *.jpeg *.png *.bmp *.gif")]
        )
        if archivos:
            self.imagenes = list(archivos)
            self.actualizar_lista()
    
    def seleccionar_carpeta(self):
        carpeta = filedialog.askdirectory(title="Seleccionar carpeta con imágenes")
        if carpeta:
            extensiones = {'.jpg', '.jpeg', '.png', '.bmp', '.gif'}
            self.imagenes = []
            for archivo in os.listdir(carpeta):
                ext = os.path.splitext(archivo)[1].lower()
                if ext in extensiones:
                    self.imagenes.append(os.path.join(carpeta, archivo))
            self.imagenes.sort()
            self.actualizar_lista()
    
    def actualizar_lista(self):
        self.lista_text.config(state='normal')
        self.lista_text.delete(1.0, tk.END)
        for i, img in enumerate(self.imagenes, 1):
            nombre = os.path.basename(img)
            self.lista_text.insert(tk.END, f"{i}. {nombre}\n")
        self.lista_text.config(state='disabled')
    
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
                for img_path in self.imagenes:
                    imagen = Image.open(img_path)
                    if imagen.mode != 'RGB':
                        imagen = imagen.convert('RGB')
                    imagenes_procesadas.append(imagen)
                
                primera_imagen = imagenes_procesadas[0]
                if len(imagenes_procesadas) > 1:
                    primera_imagen.save(
                        archivo_salida,
                        save_all=True,
                        append_images=imagenes_procesadas[1:]
                    )
                else:
                    primera_imagen.save(archivo_salida)
                
                messagebox.showinfo("Éxito", f"PDF creado: {archivo_salida}")
                
            except Exception as e:
                messagebox.showerror("Error", f"Error al crear PDF: {e}")

if __name__ == "__main__":
    root = tk.Tk()
    app = ConversorImagenesPDF(root)
    root.mainloop()