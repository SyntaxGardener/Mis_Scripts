import tkinter as tk
from tkinter import messagebox, filedialog
from docx import Document

class PasapalabraPro:
    def __init__(self, root):
        self.root = root
        self.root.title("Pasapalabra / Alphabetical")
                # --- CONFIGURACIÓN DE GEOMETRÍA DINÁMICA ---
        # Definimos el tamaño de la ventana
        ancho_ventana = 850
        alto_ventana = 760
        
        # Obtenemos el ancho de tu pantalla actual
        ancho_pantalla = self.root.winfo_screenwidth()
        
        # Calculamos la posición X para que esté centrada
        pos_x = (ancho_pantalla // 2) - (ancho_ventana // 2)
        # Posición Y en 0 para que esté pegada arriba
        pos_y = 0
        
        # Aplicamos la geometría: "Ancho x Alto + X + Y"
        self.root.geometry(f"{ancho_ventana}x{alto_ventana}+{pos_x}+{pos_y}")
        self.root.configure(bg="#1e272e")

        self.datos = []
        self.indice = 0
        self.aciertos = 0
        self.tiempo_total = 120 # Valor por defecto
        self.timer_id = None
        self.juego_activo = False

        self.main_container = tk.Frame(self.root, bg="#1e272e")
        self.main_container.pack(expand=True, fill="both")

        self.mostrar_pantalla_inicio()

    def mostrar_pantalla_inicio(self):
        for widget in self.main_container.winfo_children():
            widget.destroy()
        
        self.juego_activo = False
        if self.timer_id: self.root.after_cancel(self.timer_id)

        tk.Label(self.main_container, text="PASAPALABRA", font=("Arial", 50, "bold"), bg="#1e272e", fg="#f1c40f").pack(pady=(50, 10))
        tk.Label(self.main_container, text="Configura tu partida", font=("Arial", 14), bg="#1e272e", fg="white").pack(pady=10)

        # Selección de tiempo
        self.frame_tiempo = tk.Frame(self.main_container, bg="#1e272e")
        self.frame_tiempo.pack(pady=20)
        
        tk.Label(self.frame_tiempo, text="Segundos totales:", font=("Arial", 12), bg="#1e272e", fg="#95a5a6").pack(side="left")
        self.entry_tiempo = tk.Entry(self.frame_tiempo, font=("Arial", 14), width=5, justify="center")
        self.entry_tiempo.insert(0, "150")
        self.entry_tiempo.pack(side="left", padx=10)

        # Botón Cargar
        self.btn_cargar = tk.Button(self.main_container, text="Cargar Word y Comenzar", 
                                    font=("Arial", 16, "bold"), bg="#2ecc71", fg="white", 
                                    padx=30, pady=15, command=self.validar_y_cargar, 
                                    relief="flat", cursor="hand2")
        self.btn_cargar.pack(pady=20)

        tk.Label(self.main_container, text="ENTER para comprobar | ESPACIO para Pasapalabra", 
                 font=("Arial", 10), bg="#1e272e", fg="#95a5a6").pack(pady=20)

    def validar_y_cargar(self):
        try:
            self.tiempo_total = int(self.entry_tiempo.get())
            self.cargar_y_empezar()
        except ValueError:
            messagebox.showerror("Error", "Por favor, introduce un número válido para el tiempo.")

    def cargar_y_empezar(self):
        archivo = filedialog.askopenfilename(title="Selecciona el archivo Word", filetypes=[("Documentos de Word", "*.docx")])
        if not archivo: return

        try:
            doc = Document(archivo)
            self.datos = []
            tabla = doc.tables[0]
            for i, fila in enumerate(tabla.rows):
                if i == 0: continue 
                celdas = [c.text.strip() for c in fila.cells]
                if len(celdas) >= 3 and celdas[1] and celdas[2]:
                    self.datos.append({"letra": celdas[0].upper(), "pista": celdas[1], "correcta": celdas[2]})
            
            if self.datos:
                self.setup_ui_juego()
                self.juego_activo = True
                self.mostrar_pregunta()
                self.actualizar_reloj_global()
            else:
                messagebox.showwarning("Aviso", "Tabla no válida.")
        except Exception as e:
            messagebox.showerror("Error", f"Error: {e}")

    def setup_ui_juego(self):
        for widget in self.main_container.winfo_children(): widget.destroy()

        header = tk.Frame(self.main_container, bg="#1e272e")
        header.pack(fill="x", padx=40, pady=20)

        self.lbl_progreso = tk.Label(header, text="", font=("Arial", 12), bg="#1e272e", fg="#95a5a6")
        self.lbl_progreso.pack(side="left")

        self.lbl_timer = tk.Label(header, text=f"TIEMPO: {self.tiempo_total}", font=("Arial", 22, "bold"), bg="#1e272e", fg="#f39c12")
        self.lbl_timer.pack(side="left", padx=60)

        self.lbl_score = tk.Label(header, text="Aciertos: 0", font=("Arial", 18, "bold"), bg="#1e272e", fg="#2ecc71")
        self.lbl_score.pack(side="right")

        self.lbl_letra = tk.Label(self.main_container, text="", font=("Arial", 120, "bold"), bg="#1e272e", fg="#f1c40f")
        self.lbl_letra.pack()

        self.lbl_pista = tk.Label(self.main_container, text="", font=("Arial", 22, "italic"), bg="#1e272e", fg="white", wraplength=700)
        self.lbl_pista.pack(pady=10)

        self.lbl_error = tk.Label(self.main_container, text="", font=("Arial", 14, "bold"), bg="#1e272e", fg="#e74c3c")
        self.lbl_error.pack(pady=5)

        self.entry_var = tk.StringVar()
        self.entry = tk.Entry(self.main_container, textvariable=self.entry_var, font=("Arial", 32), justify="center", width=15, bg="#34495e", fg="white", borderwidth=0, insertbackground="white")
        self.entry.pack(pady=10)
        self.entry.focus_set()
        
        tk.Button(self.main_container, text="PASAPALABRA (Espacio)", font=("Arial", 14, "bold"), bg="#3498db", fg="white", padx=20, pady=10, command=self.pasapalabra, relief="flat").pack(pady=20)

        self.root.bind('<Return>', lambda e: self.comprobar())
        self.root.bind('<space>', lambda e: self.pasapalabra())

    def actualizar_reloj_global(self):
        if self.juego_activo and self.tiempo_total > 0:
            self.tiempo_total -= 1
            self.lbl_timer.config(text=f"TIEMPO: {self.tiempo_total}")
            if self.tiempo_total <= 10: self.lbl_timer.config(fg="#e74c3c") # Alerta rojo
            self.timer_id = self.root.after(1000, self.actualizar_reloj_global)
        elif self.tiempo_total <= 0:
            self.finalizar_juego("¡TIEMPO AGOTADO!")

    def mostrar_pregunta(self):
        if self.indice < len(self.datos):
            p = self.datos[self.indice]
            self.lbl_progreso.config(text=f"Palabras en el rosco: {len(self.datos) - self.indice}")
            self.lbl_letra.config(text=p["letra"], fg="#f1c40f")
            self.lbl_pista.config(text=p['pista'])
            self.lbl_error.config(text="")
            self.entry_var.set("")
            self.entry.config(state="normal")
            self.entry.focus_set()
            self.juego_activo = True
        else:
            self.finalizar_juego("¡HAS COMPLETADO EL ROSCO!")

    def comprobar(self):
        if self.entry.cget("state") == "disabled" or not self.juego_activo: return
        
        res_usuario = self.entry_var.get().strip().lower()
        res_correcta = self.datos[self.indice]["correcta"].lower()

        if res_usuario == res_correcta:
            self.indice += 1
            self.aciertos += 1
            self.lbl_score.config(text=f"Aciertos: {self.aciertos}")
            self.mostrar_pregunta()
        else:
            self.mostrar_fallo(f"INCORRECTO: Era {res_correcta.upper()}")

    def pasapalabra(self, event=None):
        if self.juego_activo:
            palabra_saltada = self.datos.pop(self.indice)
            self.datos.append(palabra_saltada)
            self.mostrar_pregunta()

    def mostrar_fallo(self, mensaje):
        self.juego_activo = False # Pausar reloj
        self.entry.config(state="disabled")
        self.lbl_letra.config(fg="#e74c3c")
        self.lbl_error.config(text=mensaje)
        self.root.after(1000, self.siguiente_automatico)

    def siguiente_automatico(self):
        if self.tiempo_total > 0:
            self.indice += 1
            self.mostrar_pregunta()
            self.actualizar_reloj_global()
            
           
    def finalizar_juego(self, motivo):
        self.juego_activo = False
        messagebox.showinfo("Resultados", f"{motivo}\nAciertos: {self.aciertos}")
        self.mostrar_pantalla_inicio()

if __name__ == "__main__":
    root = tk.Tk()
    app = PasapalabraPro(root)
    root.mainloop()