# -*- coding: utf-8 -*-
import tkinter as tk
from tkinterdnd2 import DND_FILES, TkinterDnD
from tkinter import messagebox
import pypdf
import pyperclip

class ExtractorPDF:
    def __init__(self, root):
        self.root = root
        self.root.title("PDF a Portapapeles (DnD)")
        
        # --- Configuración de dimensiones ---
        ancho_ventana = 400
        alto_ventana = 350
        distancia_superior = 50
        
        # Obtener dimensiones y calcular centro
        ancho_pantalla = root.winfo_screenwidth()
        posicion_x = (ancho_pantalla // 2) - (ancho_ventana // 2)
        
        # Aplicar geometría corregida
        root.geometry(f"{ancho_ventana}x{alto_ventana}+{posicion_x}+{distancia_superior}")
        self.root.configure(bg='#1e1e1e')

        # Área de soltar archivos (Drop Target)
        self.drop_label = tk.Label(
            root, 
            text="⬇️ ARRASTRA TU PDF AQUÍ ⬇️", 
            bg='#333333', fg='#00d1b2', 
            font=("Segoe UI", 12, "bold"),
            width=30, height=8,
            relief="groove", bd=2
        )
        self.drop_label.pack(padx=20, pady=20, fill=tk.BOTH, expand=True)

        # Configurar el Drag and Drop
        self.drop_label.drop_target_register(DND_FILES)
        self.drop_label.dnd_bind('<<Drop>>', self.procesar_pdf)

        self.status = tk.Label(root, text="Listo para extraer", bg='#1e1e1e', fg='white', font=("Segoe UI", 9))
        self.status.pack(pady=10)

    def procesar_pdf(self, event):
        # Limpiar la ruta (por si trae llaves {} de Windows)
        path = event.data.strip().strip('{}')
        
        if path.lower().endswith('.pdf'):
            try:
                with open(path, 'rb') as f:
                    reader = pypdf.PdfReader(f)
                    texto_completo = ""
                    for pagina in reader.pages:
                        extraido = pagina.extract_text()
                        if extraido:
                            texto_completo += extraido + "\n"
                
                if texto_completo.strip():
                    pyperclip.copy(texto_completo)
                    self.status.config(text="✅ ¡Texto copiado al portapapeles!", fg="#27ae60")
                    self.drop_label.config(text="¡LOGRADO!\nSuelta otro PDF aquí")
                else:
                    self.status.config(text="⚠️ El PDF parece no tener texto extraíble", fg="#f1c40f")
            
            except Exception as e:
                self.status.config(text=f"❌ Error: {str(e)[:30]}...", fg="#e74c3c")
        else:
            self.status.config(text="⚠️ Por favor, suelta solo archivos .PDF", fg="#f1c40f")

if __name__ == "__main__":
    try:
        # Iniciamos con TkinterDnD para que funcione el arrastrar y soltar
        app = TkinterDnD.Tk()
        gui = ExtractorPDF(app)
        app.mainloop()
    except Exception as e:
        # Si algo falla al arrancar, esto nos avisará aunque sea un .pyw
        root_error = tk.Tk()
        root_error.withdraw()
        messagebox.showerror("Error crítico", f"No se pudo iniciar la aplicación:\n{e}")