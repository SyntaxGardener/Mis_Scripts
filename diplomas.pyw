import pandas as pd
from PIL import Image, ImageDraw, ImageFont, ImageTk
import tkinter as tk
from tkinter import filedialog, messagebox
import os

class GeneradorFinal:
    def __init__(self, root):
        self.root = root
        self.root.title("Generador de Diplomas")
        # 1. Definimos el tamaño que queremos
        ancho = 450
        alto = 420
        
        # 2. Calculamos la posición (Esto es lo que va dentro de init)
        pos_x = (self.root.winfo_screenwidth() // 2) - (ancho // 2)
        
        # 3. Aplicamos la magia: Ancho x Alto + Derecha + Arriba (30)
        self.root.geometry(f"{ancho}x{alto}+{pos_x}+30")
        
        self.img_path = ""
        self.puntos = [] 

        tk.Label(root, text="GENERADOR DE DIPLOMAS", font=("Arial", 12, "bold")).pack(pady=15)
        
        # --- PASO 1 ---
        frame1 = tk.LabelFrame(root, text=" 1. Configurar Diseño ", padx=10, pady=10)
        frame1.pack(padx=20, pady=10, fill="x")
        
        tk.Button(frame1, text="Seleccionar Imagen y Marcar", command=self.iniciar_marcado, 
                  bg="#2196F3", fg="white", height=2).pack(fill="x")
        
        # --- PASO 2 ---
        frame2 = tk.LabelFrame(root, text=" 2. Ejecutar ", padx=10, pady=10)
        frame2.pack(padx=20, pady=10, fill="x")
        
        # Añadimos 'disabledforeground' para que el texto sea blanco siempre
        self.btn_generar = tk.Button(frame2, text="Cargar Excel y Generar PDFs", command=self.procesar, 
                                    state=tk.DISABLED, bg="#4CAF50", fg="white", 
                                    disabledforeground="white", font=("Arial", 10, "bold"), height=2)
        self.btn_generar.pack(fill="x")

        self.lbl_status = tk.Label(root, text="Esperando imagen...", fg="grey", font=("Arial", 9, "bold"))
        self.lbl_status.pack(pady=20)

    def iniciar_marcado(self):
        self.img_path = filedialog.askopenfilename(filetypes=[("Imágenes", "*.png *.jpg *.jpeg")])
        if not self.img_path: return

        self.win_marcar = tk.Toplevel(self.root)
        self.win_marcar.title("Configuración de puntos")
        self.win_marcar.grab_set() 
        
        img_full = Image.open(self.img_path)
        self.scale_factor = max(img_full.width / 1100, img_full.height / 700) if img_full.width > 1100 else 1.0
        img_view = img_full.resize((int(img_full.width / self.scale_factor), int(img_full.height / self.scale_factor)))

        self.tk_img = ImageTk.PhotoImage(img_view)
        
        self.instrucciones_var = tk.StringVar(value="📍 PASO 1: Haga clic donde irá el NOMBRE")
        lbl_instrucciones = tk.Label(self.win_marcar, textvariable=self.instrucciones_var, bg="#FFF176", fg="#000", font=("Arial", 12, "bold"), pady=10)
        lbl_instrucciones.pack(fill="x")

        self.canvas = tk.Canvas(self.win_marcar, width=img_view.width, height=img_view.height, cursor="cross")
        self.canvas.pack()
        self.canvas.create_image(0, 0, anchor=tk.NW, image=self.tk_img)
        
        self.puntos = []
        self.canvas.bind("<Button-1>", self.registrar_clic)

    def registrar_clic(self, event):
        x_real = int(event.x * self.scale_factor)
        y_real = int(event.y * self.scale_factor)
        self.puntos.append((x_real, y_real))
        
        n = len(self.puntos)
        self.canvas.create_oval(event.x-6, event.y-6, event.x+6, event.y+6, fill="#F44336", outline="white", width=2)
        self.canvas.create_text(event.x, event.y-20, text=f"Punto {n}", fill="red", font=("Arial", 10, "bold"))

        if n == 1:
            self.instrucciones_var.set("📍 PASO 2: Ahora haga clic para el MOTIVO")
        elif n == 2:
            self.instrucciones_var.set("📍 PASO 3: Por último, clic para el AÑO")
        elif n == 3:
            self.instrucciones_var.set("✅ ¡CONFIGURADO! Cerrando...")
            self.root.after(600, self.finalizar_marcado)

    def finalizar_marcado(self):
        self.win_marcar.destroy()
        self.btn_generar.config(state=tk.NORMAL)
        self.lbl_status.config(text="✓ DISEÑO LISTO. Cargue el Excel.", fg="green")

    def dibujar_texto_ajustado(self, draw, posicion, texto, fuente_path, tamaño_max, color, max_ancho):
        tamaño = tamaño_max
        try:
            fuente = ImageFont.truetype(fuente_path, tamaño)
        except:
            fuente = ImageFont.load_default()
            
        while tamaño > 10:
            fuente = ImageFont.truetype(fuente_path, tamaño)
            if fuente.getlength(str(texto)) <= max_ancho:
                break
            tamaño -= 2
        
        draw.text(posicion, str(texto), fill=color, font=fuente, anchor="mm")

    def procesar(self):
        exc_path = filedialog.askopenfilename(filetypes=[("Excel", "*.xlsx")])
        dest_dir = filedialog.askdirectory()
        if not exc_path or not dest_dir: return

        try:
            df = pd.read_excel(exc_path, header=None)
            df = df.dropna(how='all').dropna(axis=1, how='all')
            df.columns = [str(c).strip().lower() for c in df.iloc[0]]
            df = df[1:]

            verde_oscuro = (10, 125, 10)

            count = 0
            for _, fila in df.iterrows():
                if pd.isna(fila['nombre']): continue
                
                img = Image.open(self.img_path).convert("RGB")
                draw = ImageDraw.Draw(img)
                ancho_lim = img.width * 0.85
                
                self.dibujar_texto_ajustado(draw, self.puntos[0], fila['nombre'], "arialbd.ttf", 90, "black", ancho_lim)
                self.dibujar_texto_ajustado(draw, self.puntos[1], fila['motivo'], "arial.ttf", 60, verde_oscuro, ancho_lim)
                self.dibujar_texto_ajustado(draw, self.puntos[2], fila['fecha'], "arial.ttf", 20, "black", ancho_lim)

                nombre_pdf = f"Diploma_{str(fila['nombre']).replace(' ', '_')}.pdf"
                img.save(os.path.join(dest_dir, nombre_pdf), "PDF")
                count += 1

            messagebox.showinfo("Hecho", f"Se han generado {count} diplomas correctamente.")
            self.btn_generar.config(state=tk.DISABLED)

        except Exception as e:
            messagebox.showerror("Error", f"Error: {e}")

if __name__ == "__main__":
    root = tk.Tk()
    GeneradorFinal(root)
    root.mainloop()