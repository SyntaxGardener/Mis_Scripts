import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from PIL import Image
import os
import subprocess

class ImageConverterApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Conversor de Formatos")
        
        # --- Configuración de Geometría ---
        width = 450
        height = 400 # Altura generosa para evitar cortes
        screen_width = self.root.winfo_screenwidth()
        
        # Centrado horizontal, 5px desde el borde superior
        pos_x = (screen_width // 2) - (width // 2)
        pos_y = 5 
        
        self.root.geometry(f"{width}x{height}+{pos_x}+{pos_y}")
        self.root.resizable(False, False)

        # --- Variables ---
        self.file_path = None
        self.open_folder_var = tk.BooleanVar(value=True)

        # --- Interfaz ---
        self.main_frame = ttk.Frame(root, padding="25")
        self.main_frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(self.main_frame, text="1. Selecciona la imagen (JFIF, WebP, etc.):", font=('Segoe UI', 10, 'bold')).pack(pady=5)
        
        self.btn_select = ttk.Button(self.main_frame, text="Buscar Archivo", command=self.load_file)
        self.btn_select.pack(pady=5)

        self.lbl_file = ttk.Label(self.main_frame, text="Sin archivo seleccionado", foreground="gray", wraplength=350, justify="center")
        self.lbl_file.pack(pady=15)

        ttk.Label(self.main_frame, text="2. Formato de destino:", font=('Segoe UI', 10, 'bold')).pack(pady=5)
        self.format_var = tk.StringVar(value="ICO")
        self.combo_format = ttk.Combobox(self.main_frame, textvariable=self.format_var, state="readonly")
        # Incluimos los formatos más comunes para salir del paso
        self.combo_format['values'] = ("ICO", "PNG", "JPG", "BMP", "WEBP")
        self.combo_format.pack(pady=5)

        # Checkbox con margen extra
        self.chk_open = ttk.Checkbutton(self.main_frame, text="Abrir carpeta al finalizar", variable=self.open_folder_var)
        self.chk_open.pack(pady=25)

        # Botón de acción destacado
        self.btn_convert = ttk.Button(self.main_frame, text="CONVERTIR AHORA", command=self.convert_image)
        self.btn_convert.pack(pady=5)

    def load_file(self):
        # Filtros exhaustivos para que no se escape nada de lo que descarga Google
        file_types = [
            ("Todos los formatos soportados", "*.jfif *.webp *.jpg *.jpeg *.png *.bmp *.tiff"),
            ("Google Images (JFIF/WebP)", "*.jfif *.webp"),
            ("Formatos Estándar", "*.jpg *.png *.bmp")
        ]
        path = filedialog.askopenfilename(filetypes=file_types)
        if path:
            self.file_path = path
            self.lbl_file.config(text=f"Cargado: {os.path.basename(self.file_path)}", foreground="black")

    def convert_image(self):
        if not self.file_path:
            messagebox.showwarning("Atención", "Selecciona una imagen primero.")
            return

        nombre_base = os.path.splitext(os.path.basename(self.file_path))[0]
        ext_destino = self.format_var.get().lower()
        
        # Sugerir el mismo nombre original
        ruta_guardado = filedialog.asksaveasfilename(
            initialfile=nombre_base,
            defaultextension=f".{ext_destino}",
            filetypes=[(ext_destino.upper(), f"*.{ext_destino}")]
        )

        if not ruta_guardado:
            return

        try:
            img = Image.open(self.file_path)
            
            # Lógica para ICO (con varios tamaños para que luzca bien en Windows)
            if ext_destino == "ico":
                icon_sizes = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
                img.save(ruta_guardado, format='ICO', sizes=icon_sizes)
            
            # Lógica para JPG (eliminar transparencias de WebP/PNG)
            elif ext_destino == "jpg":
                if img.mode in ("RGBA", "LA", "P"):
                    img = img.convert("RGB")
                img.save(ruta_guardado, format='JPEG', quality=95)
            
            else:
                img.save(ruta_guardado, format=ext_destino.upper())
            
            # Finalización
            if self.open_folder_var.get():
                subprocess.Popen(f'explorer /select,"{os.path.normpath(ruta_guardado)}"')
            else:
                messagebox.showinfo("Hecho", "Imagen convertida con éxito.")

        except Exception as e:
            messagebox.showerror("Error", f"Vaya, algo falló: {e}")

if __name__ == "__main__":
    root = tk.Tk()
    app = ImageConverterApp(root)
    root.mainloop()