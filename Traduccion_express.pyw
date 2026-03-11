import tkinter as tk
from tkinter import messagebox
import pyperclip
from deep_translator import GoogleTranslator

class TraductorVisual:
    def __init__(self, root):
        self.root = root
        self.root.title("Traductor Express")
        self.root.geometry("400x250")
        self.root.attributes("-topmost", True)  # Siempre visible
        self.root.configure(bg='#2c3e50') # Color oscuro elegante

        # Estilos de etiquetas
        label_style = {"bg": '#2c3e50', "fg": '#ecf0f1', "font": ("Segoe UI", 10, "bold")}
        
        self.label_info = tk.Label(root, text="Contenido en el portapapeles:", **label_style)
        self.label_info.pack(pady=10)

        # Caja de texto para mostrar la traducción
        self.text_area = tk.Text(root, height=5, width=40, font=("Segoe UI", 10), 
                                 bg='#34495e', fg='white', bd=0, padx=10, pady=10)
        self.text_area.pack(pady=10)

        self.btn_copy = tk.Button(root, text="Copiar Traducción", command=self.copiar_manual,
                                  bg='#27ae60', fg='white', font=("Segoe UI", 9, "bold"), 
                                  relief="flat", cursor="hand2")
        self.btn_copy.pack(pady=5)

        self.ultimo_texto = ""
        self.chequear_portapapeles()

    def traducir(self, texto):
        try:
            # Usamos auto-detección para que sirva para cualquier idioma al español
            resultado = GoogleTranslator(source='auto', target='es').translate(texto)
            return resultado
        except Exception as e:
            return f"Error: {e}"

    def chequear_portapapeles(self):
        try:
            contenido = pyperclip.paste()
            
            if contenido != self.ultimo_texto and contenido.strip() != "":
                traduccion = self.traducir(contenido)
                
                # Actualizar la interfaz
                self.text_area.delete('1.0', tk.END)
                self.text_area.insert(tk.END, traduccion)
                
                self.ultimo_texto = contenido
                
        except Exception as e:
            print(f"Error en el hilo: {e}")

        # Se vuelve a ejecutar cada 1000ms (1 segundo)
        self.root.after(1000, self.chequear_portapapeles)

    def copiar_manual(self):
        contenido = self.text_area.get('1.0', tk.END).strip()
        pyperclip.copy(contenido)
        messagebox.showinfo("Listo", "Traducción copiada al portapapeles")

if __name__ == "__main__":
    app = tk.Tk()
    TraductorVisual(app)
    app.mainloop()