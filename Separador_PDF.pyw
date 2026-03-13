import tkinter as tk
from tkinter import filedialog, messagebox
import PyPDF2
import os
import re
import subprocess

class SeparadorPDF:
    def __init__(self, root):
        self.root = root
        self.root.title("Separador de PDF + Extraer páginas")
        
        # Ventana centrada arriba
        width = 550
        height = 500
        screen_width = self.root.winfo_screenwidth()
        x = (screen_width // 2) - (width // 2)
        y = 0 
        self.root.geometry(f"{width}x{height}+{x}+{y}")
        self.root.resizable(False, False)

        self.pdf_path = tk.StringVar()
        self.output_dir = tk.StringVar()
        self.paginas_info = tk.StringVar(value="Páginas totales: -")
        self.naming_option = tk.IntVar(value=2)
        self.open_folder = tk.BooleanVar(value=True)

        self.create_widgets()

    def create_widgets(self):
        # 1. Selección de archivo
        tk.Label(self.root, text="1. Selecciona el archivo PDF:", font=('Arial', 10, 'bold')).pack(anchor="w", padx=20, pady=(15, 5))
        file_frame = tk.Frame(self.root)
        file_frame.pack(fill="x", padx=20)
        tk.Entry(file_frame, textvariable=self.pdf_path, width=50).pack(side="left", expand=True, fill="x")
        tk.Button(file_frame, text="Buscar", command=self.select_file).pack(side="right", padx=5)
        
        # Previsualización de páginas (Label dinámico)
        tk.Label(self.root, textvariable=self.paginas_info, font=('Arial', 9, 'bold'), fg="#2E86C1").pack(anchor="w", padx=20)

        # 2. Configuración de división
        tk.Label(self.root, text="2. Indica los cortes (ej: 1-2, 3-5, 6):", font=('Arial', 10, 'bold')).pack(anchor="w", padx=20, pady=(10, 5))
        self.range_entry = tk.Entry(self.root, font=('Consolas', 11))
        self.range_entry.pack(fill="x", padx=20)
        tk.Label(self.root, text="Separa cada nuevo PDF con comas.", font=('Arial', 8, 'italic'), fg="#555").pack(anchor="w", padx=20)

        # 3. Carpeta de guardado
        tk.Label(self.root, text="3. Carpeta de guardado:", font=('Arial', 10, 'bold')).pack(anchor="w", padx=20, pady=(10, 5))
        dest_frame = tk.Frame(self.root)
        dest_frame.pack(fill="x", padx=20)
        tk.Entry(dest_frame, textvariable=self.output_dir, width=50).pack(side="left", expand=True, fill="x")
        tk.Button(dest_frame, text="Cambiar", command=self.select_output_dir).pack(side="right", padx=5)

        # 4. Opciones de nombre
        tk.Label(self.root, text="4. Criterio para nombrar:", font=('Arial', 10, 'bold')).pack(anchor="w", padx=20, pady=(10, 5))
        tk.Radiobutton(self.root, text="Nombre original + número (Apuntes/Temas)", variable=self.naming_option, value=2).pack(anchor="w", padx=30)
        tk.Radiobutton(self.root, text="Detectar 'Apellidos y nombre' (Certificados)", variable=self.naming_option, value=1).pack(anchor="w", padx=30)

        # Checkbox abrir carpeta
        tk.Checkbutton(self.root, text="Abrir carpeta al terminar", variable=self.open_folder).pack(anchor="w", padx=20, pady=10)

        # Botón Ejecutar
        self.btn_run = tk.Button(self.root, text="PROCESAR Y DIVIDIR", bg="#28B463", fg="white", 
                                font=('Arial', 12, 'bold'), command=self.process_pdf, cursor="hand2")
        self.btn_run.pack(pady=10, fill="x", padx=80)

    def select_file(self):
        path = filedialog.askopenfilename(filetypes=[("Archivos PDF", "*.pdf")])
        if path:
            self.pdf_path.set(path)
            try:
                reader = PyPDF2.PdfReader(path)
                self.paginas_info.set(f"Páginas totales: {len(reader.pages)}")
            except:
                self.paginas_info.set("Error al leer el PDF")
            
            if not self.output_dir.get():
                self.output_dir.set(os.path.dirname(path))

    def select_output_dir(self):
        path = filedialog.askdirectory()
        if path:
            self.output_dir.set(path)

    def extract_student_name(self, reader, pages):
        try:
            text = reader.pages[pages[0]].extract_text()
            match = re.search(r"Apellidos y nombre:\s*([^\n\r]+)", text)
            if match:
                return match.group(1).strip().replace(',', '')
        except:
            pass
        return None

    def parse_ranges(self, text):
        result = []
        try:
            for part in text.split(','):
                part = part.strip()
                if '-' in part:
                    start, end = map(int, part.split('-'))
                    result.append(list(range(start-1, end)))
                else:
                    result.append([int(part) - 1])
            return result
        except:
            raise ValueError("Formato de rangos no válido.")

    def reset_fields(self):
        """Limpia los campos para una nueva subida"""
        self.pdf_path.set("")
        self.range_entry.delete(0, tk.END)
        self.paginas_info.set("Páginas totales: -")
        # No reseteamos la carpeta de destino para comodidad del usuario

    def process_pdf(self):
        if not self.pdf_path.get() or not self.range_entry.get():
            messagebox.showwarning("Atención", "Selecciona un archivo e indica los rangos.")
            return

        try:
            reader = PyPDF2.PdfReader(self.pdf_path.get())
            ranges = self.parse_ranges(self.range_entry.get())
            base_name = os.path.splitext(os.path.basename(self.pdf_path.get()))[0]
            output_folder = self.output_dir.get()
            
            for i, pages in enumerate(ranges):
                writer = PyPDF2.PdfWriter()
                for p in pages:
                    writer.add_page(reader.pages[p])
                
                if self.naming_option.get() == 1:
                    detected = self.extract_student_name(reader, pages)
                    final_filename = detected if detected else f"{base_name}_{i+1}"
                else:
                    final_filename = f"{base_name}-{i+1}"
                
                final_filename = re.sub(r'[\\/*?:"<>|]', "", final_filename)
                output_path = os.path.join(output_folder, f"{final_filename}.pdf")
                
                with open(output_path, "wb") as f:
                    writer.write(f)

            messagebox.showinfo("Éxito", f"Se han generado {len(ranges)} archivos.")
            
            if self.open_folder.get():
                os.startfile(output_folder) if os.name == 'nt' else subprocess.run(['open', output_folder])
            
            # Limpiar para la siguiente tarea
            self.reset_fields()

        except Exception as e:
            messagebox.showerror("Error", f"Ocurrió un fallo: {str(e)}")

if __name__ == "__main__":
    root = tk.Tk()
    app = SeparadorPDF(root)
    root.mainloop()