import os
import pandas as pd
import tkinter as tk
from tkinter import filedialog, messagebox
from docxtpl import DocxTemplate
import threading

class GeneradorSencillo:
    def __init__(self, root):
        self.root = root
        self.root.title("Generador Batch")
        
        # Posicionamiento a 5px del borde superior
        w, h = 500, 380
        px = (self.root.winfo_screenwidth() // 2) - (w // 2)
        self.root.geometry(f"{w}x{h}+{px}+5")
        
        self.excel_path = tk.StringVar()
        self.template_path = tk.StringVar()
        self.output_dir = tk.StringVar()
        self.create_widgets()

    def create_widgets(self):
        pad = {'padx': 20, 'pady': 5}
        tk.Label(self.root, text="Generador de Múltiples Documentos", font=("Arial", 11, "bold")).pack(pady=15)

        for txt, var, cmd in [
            ("1. Selecciona el Excel:", self.excel_path, self.sel_ex),
            ("2. Selecciona la Plantilla Word - campos con {{ }} :", self.template_path, self.sel_wd),
            ("3. Carpeta de destino:", self.output_dir, self.sel_dir)
        ]:
            tk.Label(self.root, text=txt).pack(anchor="w", **pad)
            f = tk.Frame(self.root); f.pack(fill="x", **pad)
            tk.Entry(f, textvariable=var).pack(side="left", fill="x", expand=True)
            tk.Button(f, text="...", command=cmd, width=4).pack(side="right", padx=(5,0))

        self.btn = tk.Button(self.root, text="GENERAR AHORA", bg="#0078D7", fg="white", 
                            font=("Arial", 10, "bold"), height=2, command=self.run)
        self.btn.pack(pady=25, fill="x", padx=20)

    def sel_ex(self): self.excel_path.set(filedialog.askopenfilename(filetypes=[("Excel", "*.xlsx")]))
    def sel_wd(self): self.template_path.set(filedialog.askopenfilename(filetypes=[("Word", "*.docx")]))
    def sel_dir(self): self.output_dir.set(filedialog.askdirectory())

    def process(self):
        try:
            # Leer excel
            df = pd.read_excel(self.excel_path.get()).dropna(how='all')
            out = self.output_dir.get()
            tmpl = self.template_path.get()

            for i, row in df.iterrows():
                doc = DocxTemplate(tmpl)
                
                # LA MAGIA: Convertimos "fecha de nacimiento" en "fecha_de_nacimiento"
                # para que el Word no de error, pero el dato sea el mismo.
                datos = {str(k).replace(" ", "_"): v for k, v in row.to_dict().items()}
                
                # Rellenar plantilla
                doc.render(datos)
                
                # Nombre de archivo limpio
                nombre_archivo = "".join(c for c in str(row.iloc[0]) if c.isalnum() or c==" ")
                doc.save(os.path.join(out, f"Doc_{i+1}_{nombre_archivo[:15]}.docx"))

            messagebox.showinfo("Éxito", f"Se han generado {len(df)} archivos.")
            os.startfile(out)
        except Exception as e:
            messagebox.showerror("Error", str(e))
        finally:
            self.btn.config(state="normal", text="GENERAR AHORA")

    def run(self):
        if not all([self.excel_path.get(), self.template_path.get(), self.output_dir.get()]): return
        self.btn.config(state="disabled", text="Procesando...")
        threading.Thread(target=self.process, daemon=True).start()

if __name__ == "__main__":
    root = tk.Tk(); app = GeneradorSencillo(root); root.mainloop()