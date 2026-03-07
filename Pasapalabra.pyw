import tkinter as tk
from tkinter import messagebox, filedialog
from docx import Document

class PasapalabraPro:
    def __init__(self, root):
        self.root = root
        self.root.title("Pasapalabra English - Word Loader")
        self.root.geometry("850x650")
        self.root.configure(bg="#1e272e")

        self.datos = []
        self.indice = 0
        self.aciertos = 0

        self.cargar_archivo_word()

        if self.datos:
            self.setup_ui()
            self.mostrar_pregunta()
        else:
            self.root.destroy()

    def cargar_archivo_word(self):
        archivo = filedialog.askopenfilename(
            title="Selecciona el archivo Word", 
            filetypes=[("Documentos de Word", "*.docx")]
        )
        if not archivo: return

        try:
            doc = Document(archivo)
            tabla = doc.tables[0]
            for i, fila in enumerate(tabla.rows):
                # OMITIR LA FILA 1 (Títulos: Letra, Pista, Respuesta)
                if i == 0: continue 
                
                celdas = [c.text.strip() for c in fila.cells]
                
                # Validamos que la fila tenga contenido real en Pista y Respuesta
                if len(celdas) >= 3 and celdas[1] and celdas[2]:
                    self.datos.append({
                        "letra": celdas[0].upper() if celdas[0] else "?",
                        "pista": celdas[1],
                        "correcta": celdas[2]
                    })
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo leer la tabla: {e}")

    def setup_ui(self):
        # Marcadores superiores
        self.header = tk.Frame(self.root, bg="#1e272e")
        self.header.pack(fill="x", padx=40, pady=25)

        self.lbl_progreso = tk.Label(self.header, text="", font=("Arial", 12), bg="#1e272e", fg="#95a5a6")
        self.lbl_progreso.pack(side="left")

        self.lbl_score = tk.Label(self.header, text="Aciertos: 0", font=("Arial", 16, "bold"), bg="#1e272e", fg="#2ecc71")
        self.lbl_score.pack(side="right")

        # Letra y Pista Central
        self.lbl_letra = tk.Label(self.root, text="", font=("Arial", 120, "bold"), bg="#1e272e", fg="#f1c40f")
        self.lbl_letra.pack()

        self.lbl_pista = tk.Label(self.root, text="", font=("Arial", 24, "italic"), bg="#1e272e", fg="white", wraplength=700, justify="center")
        self.lbl_pista.pack(pady=20)

        # Zona de respuesta y errores
        self.lbl_error = tk.Label(self.root, text="", font=("Arial", 14, "bold"), bg="#1e272e", fg="#e74c3c")
        self.lbl_error.pack(pady=10)

        self.entry_var = tk.StringVar()
        self.entry = tk.Entry(self.root, textvariable=self.entry_var, font=("Arial", 32), justify="center", width=15, bg="#34495e", fg="white", borderwidth=0, insertbackground="white")
        self.entry.pack(pady=10)
        self.entry.focus_set()
        
        self.root.bind('<Return>', lambda e: self.comprobar())

    def mostrar_pregunta(self):
        if self.indice < len(self.datos):
            p = self.datos[self.indice]
            self.lbl_progreso.config(text=f"Pregunta {self.indice + 1} de {len(self.datos)}")
            self.lbl_letra.config(text=p["letra"], fg="#f1c40f")
            self.lbl_pista.config(text=p['pista'])
            self.lbl_error.config(text="")
            self.entry_var.set("")
            self.entry.config(state="normal")
            self.entry.focus_set()
        else:
            messagebox.showinfo("Resultados", f"¡Juego Terminado!\nAciertos: {self.aciertos} de {len(self.datos)}")
            self.root.destroy()

    def comprobar(self):
        res_usuario = self.entry_var.get().strip().lower()
        res_correcta = self.datos[self.indice]["correcta"].lower()

        if res_usuario == res_correcta:
            self.aciertos += 1
            self.lbl_score.config(text=f"Aciertos: {self.aciertos}")
            self.indice += 1
            self.mostrar_pregunta()
        else:
            # Bloqueamos entrada y mostramos el fallo
            self.entry.config(state="disabled")
            self.lbl_letra.config(fg="#e74c3c")
            self.lbl_error.config(text=f"INCORRECTO: La respuesta era {res_correcta.upper()}")
            # Esperar 2.5 segundos para que los alumnos vean el fallo y pasar
            self.root.after(2500, self.siguiente_automatico)

    def siguiente_automatico(self):
        self.indice += 1
        self.mostrar_pregunta()

if __name__ == "__main__":
    root = tk.Tk()
    app = PasapalabraPro(root)
    root.mainloop()