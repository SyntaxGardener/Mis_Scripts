import sys
import os
import subprocess
import tkinter as tk
from tkinter import messagebox

class ControlEnergiaApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Control de Energía")
        
        # Configuración de colores (Interfaz Clara)
        self.bg_color = "#F4F5F7"      # Gris muy claro / blanco
        self.card_bg = "#FFFFFF"       # Blanco puro para tarjetas
        self.text_color = "#1D2125"    # Texto oscuro
        self.btn_bg = "#E9EACD"        # Color de botones suave
        self.btn_hover = "#D8D9B8"     # Color de botones al pasar el ratón
        self.accent_red = "#E54D42"    # Rojo para apagado directo
        self.accent_blue = "#0065FF"   # Azul para apagado seguro
        self.accent_green = "#22A06B"  # Verde para suspensión
        
        self.root.configure(bg=self.bg_color)
        self.root.resizable(False, False)
        
        # Quitar bordes predeterminados complejos (opcional para un diseño más limpio)
        self.root.attributes("-topmost", True)  # Se mantiene visible al abrirse
        
        # Dimensiones de la ventana
        width = 420
        height = 360
        
        # Posicionamiento: Centrado horizontalmente y a 5 px del borde superior
        screen_width = self.root.winfo_screenwidth()
        x_position = (screen_width // 2) - (width // 2)
        y_position = 5
        
        self.root.geometry(f"{width}x{height}+{x_position}+{y_position}")
        
        # Estructura de la Interfaz
        container = tk.Frame(root, bg=self.bg_color, padx=20, pady=15)
        container.pack(fill="both", expand=True)
        
        # Título
        title_label = tk.Label(
            container, 
            text="Control de Energía - Windows", 
            font=("Segoe UI", 14, "bold"), 
            bg=self.bg_color, 
            fg=self.text_color
        )
        title_label.pack(pady=(0, 15))
        
        # Botón 1: Apagado Seguro (con confirmación)
        btn1 = tk.Button(
            container,
            text="🛡️  Apagado Seguro (Aviso de 5s)",
            font=("Segoe UI", 10, "bold"),
            bg="#E6F0FF",
            fg=self.accent_blue,
            activebackground="#CCE0FF",
            activeforeground=self.accent_blue,
            bd=0,
            padx=10,
            pady=10,
            cursor="hand2",
            command=self.apagado_seguro
        )
        btn1.pack(fill="x", pady=6)
        
        # Botón 2: Apagado Directo
        btn2 = tk.Button(
            container,
            text="⚡  Apagado Rápido (Inmediato)",
            font=("Segoe UI", 10, "bold"),
            bg="#FFEBE6",
            fg=self.accent_red,
            activebackground="#FFD6CE",
            activeforeground=self.accent_red,
            bd=0,
            padx=10,
            pady=10,
            cursor="hand2",
            command=self.apagado_directo
        )
        btn2.pack(fill="x", pady=6)
        
        # Botón 3: Suspensión (Reposo)
        btn3 = tk.Button(
            container,
            text="🌙  Poner en Suspensión (Reposo)",
            font=("Segoe UI", 10, "bold"),
            bg="#E3FCEF",
            fg=self.accent_green,
            activebackground="#ABF5D1",
            activeforeground=self.accent_green,
            bd=0,
            padx=10,
            pady=10,
            cursor="hand2",
            command=self.suspender
        )
        btn3.pack(fill="x", pady=6)
        
        # Botón 4: Cancelar / Salir
        btn_exit = tk.Button(
            container,
            text="Cancelar",
            font=("Segoe UI", 9),
            bg="#DFE1E6",
            fg=self.text_color,
            activebackground="#C1C7D0",
            bd=0,
            pady=6,
            cursor="hand2",
            command=self.root.quit
        )
        btn_exit.pack(fill="x", pady=(15, 0))

    def apagado_seguro(self):
        # Muestra una ventana de confirmación antes de iniciar el apagado
        confirmar = messagebox.askokcancel(
            "Confirmar Apagado Seguro", 
            "Se iniciará un apagado seguro con 5 segundos de margen.\n\n¿Deseas continuar?"
        )
        if confirmar:
            # Da 5 segundos de margen (permite cancelar desde la consola de Windows si se desea)
            subprocess.run(["shutdown", "/s", "/t", "5", "/c", "Apagado programado en 5 segundos. Guarde su trabajo."])
            self.root.quit()

    def apagado_directo(self):
        confirmar = messagebox.askyesno(
            "Confirmar Apagado Directo", 
            "⚠️ ¡Atención! Se apagarán todos los programas de inmediato.\nLos datos no guardados se perderán.\n\n¿Apagar ahora mismo?"
        )
        if confirmar:
            subprocess.run(["shutdown", "/s", "/t", "0"])
            self.root.quit()

    def suspender(self):
        self.root.quit()
        subprocess.run(["rundll32.exe", "powrprof.dll,SetSuspendState", "0,1,0"])

if __name__ == "__main__":
    root = tk.Tk()
    app = ControlEnergiaApp(root)
    root.mainloop()