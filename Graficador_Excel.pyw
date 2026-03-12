import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import pandas as pd
import matplotlib.pyplot as plt
import os

class GraficadorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Generador de Gráficos Excel")
        
        # --- Configuración de posición (Centrado, 20px superior) ---
        ancho_v, alto_v = 550, 480
        pos_x = (self.root.winfo_screenwidth() // 2) - (ancho_v // 2)
        self.root.geometry(f"{ancho_v}x{alto_v}+{pos_x}+20")
        self.root.resizable(False, False)

        self.df = None
        self.excel_file = None
        self.base_usb = ""

        # --- Interfaz ---
        tk.Label(root, text="Asistente de Gráficos", font=("Arial", 12, "bold")).pack(pady=10)

        self.btn_cargar = tk.Button(root, text="1. Seleccionar Archivo Excel", command=self.cargar_archivo, width=30)
        self.btn_cargar.pack(pady=5)

        self.lbl_archivo = tk.Label(root, text="Ningún archivo seleccionado", fg="gray")
        self.lbl_archivo.pack()

        # Selector de Hoja
        self.frame_hoja = tk.LabelFrame(root, text=" Paso 2: Selecciona la Hoja ", padx=10, pady=10)
        self.frame_hoja.pack(pady=10, fill="x", padx=20)
        
        self.combo_hojas = ttk.Combobox(self.frame_hoja, state="disabled")
        self.combo_hojas.pack(side="left", expand=True, fill="x", padx=5)
        self.combo_hojas.bind("<<ComboboxSelected>>", self.cargar_datos_hoja)

        # Selector de Columnas
        self.frame_cols = tk.LabelFrame(root, text=" Paso 3: Configura el Gráfico ", padx=10, pady=10)
        self.frame_cols.pack(pady=10, fill="x", padx=20)

        tk.Label(self.frame_cols, text="Eje X:").grid(row=0, column=0)
        self.combo_x = ttk.Combobox(self.frame_cols, state="disabled")
        self.combo_x.grid(row=0, column=1, sticky="ew", padx=5)

        tk.Label(self.frame_cols, text="Eje Y:").grid(row=1, column=0)
        self.combo_y = ttk.Combobox(self.frame_cols, state="disabled")
        self.combo_y.grid(row=1, column=1, sticky="ew", padx=5, pady=5)
        self.frame_cols.columnconfigure(1, weight=1)

        self.btn_graficar = tk.Button(root, text="GENERAR Y ELEGIR DESTINO", command=self.generar_y_guardar, 
                                      bg="#0078D7", fg="white", font=("Arial", 10, "bold"), state="disabled")
        self.btn_graficar.pack(pady=15, fill="x", padx=20)

    def cargar_archivo(self):
        # Detectar la raíz del USB basándose en la ubicación de este script
        self.base_usb = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        ruta_inicial = os.path.join(self.base_usb, "Datos")
        
        archivo = filedialog.askopenfilename(initialdir=ruta_inicial, filetypes=[("Excel", "*.xlsx *.xls")])

        if archivo:
            try:
                self.excel_file = pd.ExcelFile(archivo)
                hojas = self.excel_file.sheet_names
                self.combo_hojas.config(values=hojas, state="readonly")
                self.lbl_archivo.config(text=os.path.basename(archivo), fg="black")
                self.btn_graficar.config(state="disabled")
            except Exception as e:
                messagebox.showerror("Error", f"Error al abrir archivo: {e}")

    def cargar_datos_hoja(self, event):
        try:
            self.df = self.excel_file.parse(self.combo_hojas.get())
            columnas = list(self.df.columns)
            self.combo_x.config(values=columnas, state="readonly")
            self.combo_y.config(values=columnas, state="readonly")
            self.btn_graficar.config(state="normal")
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo cargar la hoja: {e}")

    def generar_y_guardar(self):
        try:
            x, y = self.combo_x.get(), self.combo_y.get()
            hoja = self.combo_hojas.get()
            if not x or not y: return
            
            # 1. Crear el gráfico en memoria
            plt.figure(figsize=(10, 6))
            plt.bar(self.df[x].astype(str), self.df[y], color="skyblue", edgecolor="navy")
            plt.title(f"Hoja: {hoja} | {y} vs {x}")
            plt.xticks(rotation=45, ha='right')
            plt.tight_layout()
            
            # 2. Preguntar dónde guardar
            nombre_sugerido = f"Grafico_{hoja}_{y}.png".replace(" ", "_")
            ruta_guardado = filedialog.asksaveasfilename(
                initialdir=self.base_usb,
                initialfile=nombre_sugerido,
                defaultextension=".png",
                filetypes=[("Imagen PNG", "*.png"), ("Documento PDF", "*.pdf"), ("Todos los archivos", "*.*")]
            )
            
            if ruta_guardado:
                plt.savefig(ruta_guardado)
                plt.show() # Muestra el gráfico después de guardar
                messagebox.showinfo("Éxito", "Gráfico exportado correctamente.")
            else:
                plt.close() # Si cancela el guardado, cerramos la figura para no saturar
                
        except Exception as e:
            messagebox.showerror("Error", f"Fallo al exportar: {e}")

if __name__ == "__main__":
    root = tk.Tk()
    app = GraficadorApp(root)
    root.mainloop()