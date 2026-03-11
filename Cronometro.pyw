import tkinter as tk
from tkinter import messagebox

class CronometroDocenteFinal:
    def __init__(self, root):
        self.root = root
        self.root.title("Cronómetro para el Aula")
        ancho = 700
        alto = 650

        # Cálculo para centrar horizontalmente
        pos_x = (self.root.winfo_screenwidth() // 2) - (ancho // 2)

        # Aplicamos ambos valores a la geometría
        self.root.geometry(f"{ancho}x{alto}+{pos_x}+15")
        self.root.configure(bg="#2c3e50")

        self.tiempo_total = 0
        self.tiempo_restante = 0
        self.corriendo = False

        # --- PANEL DE CONFIGURACIÓN ---
        self.frame_controles = tk.Frame(root, bg="#34495e", pady=15)
        self.frame_controles.pack(fill="x")

        # Fila 1: Exposiciones (1 a 5 minutos)
        tk.Label(self.frame_controles, text="EXPOSICIONES (MINUTOS):", fg="#1abc9c", bg="#34495e", font=("Arial", 10, "bold")).pack()
        self.frame_corto = tk.Frame(self.frame_controles, bg="#34495e")
        self.frame_corto.pack(pady=5)
        for t in [1, 2, 3, 4, 5]:
            tk.Button(self.frame_corto, text=f"{t} min", width=8, command=lambda v=t: self.set_tiempo(v)).pack(side="left", padx=2)

        # Fila 2: Tiempo Manual (Aquí puedes poner 0.5 para medio minuto)
        tk.Label(self.frame_controles, text="TIEMPO MANUAL (EJ: 0.5 O 1.5):", fg="#ecf0f1", bg="#34495e", font=("Arial", 10, "bold")).pack(pady=(10,0))
        self.frame_manual = tk.Frame(self.frame_controles, bg="#34495e")
        self.frame_manual.pack(pady=5)
        
        self.entrada_manual = tk.Entry(self.frame_manual, font=("Arial", 14), width=10, justify="center")
        self.entrada_manual.insert(0, "0.5") # Sugerencia de medio minuto por defecto
        self.entrada_manual.pack(side="left", padx=5)
        tk.Button(self.frame_manual, text="FIJAR", command=self.fijar_manual, bg="#95a5a6", width=8).pack(side="left")

        # Fila 3: Exámenes
        tk.Label(self.frame_controles, text="EXÁMENES (MINUTOS):", fg="#3498db", bg="#34495e", font=("Arial", 10, "bold")).pack(pady=(10,0))
        self.frame_largo = tk.Frame(self.frame_controles, bg="#34495e")
        self.frame_largo.pack(pady=5)
        for t in [30, 60, 90, 120]:
            tk.Button(self.frame_largo, text=f"{t} min", width=8, command=lambda v=t: self.set_tiempo(v)).pack(side="left", padx=2)

        # --- RELOJ ---
        self.label_tiempo = tk.Label(root, text="00:00", font=("Helvetica", 140, "bold"), 
                                     bg="#2c3e50", fg="white")
        self.label_tiempo.pack(expand=True, fill="both")

        # --- BOTÓN DE ACCIÓN ---
        self.btn_main = tk.Button(root, text="INICIAR", command=self.toggle,
                                 font=("Arial", 20, "bold"), bg="#27ae60", fg="white", height=2)
        self.btn_main.pack(fill="x")

    def fijar_manual(self):
        try:
            # Acepta puntos o comas
            dato = self.entrada_manual.get().replace(',', '.')
            self.set_tiempo(float(dato))
        except ValueError:
            messagebox.showerror("Error", "Escribe un número (ej: 0.5 para 30 segundos)")

    def set_tiempo(self, mins):
        self.tiempo_total = int(mins * 60)
        self.tiempo_restante = self.tiempo_total
        self.corriendo = False
        self.actualizar_display()
        self.reset_visual()
        self.btn_main.config(text="INICIAR", bg="#27ae60", state="normal")

    def reset_visual(self):
        self.root.configure(bg="#2c3e50")
        self.label_tiempo.config(bg="#2c3e50", fg="white")

    def actualizar_display(self):
        mins, secs = divmod(self.tiempo_restante, 60)
        self.label_tiempo.config(text=f"{mins:02d}:{secs:02d}")

    def toggle(self):
        if self.tiempo_restante <= 0: return
        if not self.corriendo:
            self.corriendo = True
            self.btn_main.config(text="PAUSAR", bg="#e67e22")
            self.contar()
        else:
            self.corriendo = False
            self.btn_main.config(text="REANUDAR", bg="#27ae60")

    def contar(self):
        if self.corriendo and self.tiempo_restante > 0:
            self.tiempo_restante -= 1
            self.actualizar_display()
            
            # Semáforo: Amarillo al 25%, Rojo al 10%
            porcentaje = (self.tiempo_restante / self.tiempo_total) * 100
            if porcentaje <= 10:
                self.actualizar_color("#c0392b", "white") # Rojo
            elif porcentaje <= 25:
                self.actualizar_color("#f1c40f", "black") # Amarillo
            
            self.root.after(1000, self.contar)
        elif self.tiempo_restante == 0 and self.corriendo:
            self.corriendo = False
            self.actualizar_color("#7f8c8d", "white")
            self.btn_main.config(text="¡TIEMPO AGOTADO!", state="disabled")
            messagebox.showinfo("Aviso", "El tiempo ha concluido.")

    def actualizar_color(self, bg_color, fg_color):
        self.root.configure(bg=bg_color)
        self.label_tiempo.config(bg=bg_color, fg=fg_color)

if __name__ == "__main__":
    root = tk.Tk()
    app = CronometroDocenteFinal(root)
    root.mainloop()