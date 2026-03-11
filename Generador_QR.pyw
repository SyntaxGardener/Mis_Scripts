import qrcode
import os
import platform
import subprocess
import tkinter as tk
from tkinter import messagebox, filedialog, colorchooser
from PIL import ImageTk, Image
import pyperclip 

class GeneradorQRPro:
    def __init__(self, root):
        self.root = root
        self.root.title("Generador de QR")

        # Variables de estado
        self.color_qr = "black"
        self.color_fondo = "white"
        self.img_preview = None
        self.abrir_carpeta_var = tk.BooleanVar(value=False)

        # --- Configuración de Dimensiones ---
        ancho_ventana = 500
        alto_ventana = 650
        pantalla_ancho = self.root.winfo_screenwidth()
        pos_x = (pantalla_ancho // 2) - (ancho_ventana // 2)
        pos_y = 25 

        self.root.geometry(f"{ancho_ventana}x{alto_ventana}+{pos_x}+{pos_y}")

        self.crear_widgets()
        self.crear_menu_derecho()
        self.actualizar_previsualizacion()

    def crear_menu_derecho(self):
        self.menu_contextual = tk.Menu(self.root, tearoff=0)
        self.menu_contextual.add_command(label="Pegar", command=self.pegar_texto)
        self.menu_contextual.add_command(label="Copiar", command=lambda: self.root.focus_get().event_generate('<<Copy>>'))
        self.menu_contextual.add_separator()
        self.menu_contextual.add_command(label="Seleccionar todo", command=lambda: self.entry_url.select_range(0, tk.END))

    def mostrar_menu_contextual(self, event):
        self.menu_contextual.tk_popup(event.x_root, event.y_root)

    def pegar_texto(self, event=None):
        try:
            texto_portapapeles = pyperclip.paste()
            self.entry_url.delete(0, tk.END)
            self.entry_url.insert(0, texto_portapapeles)
            self.root.after(100, self.actualizar_previsualizacion)
        except Exception as e:
            print(f"Error al pegar: {e}")

    def elegir_color(self, tipo):
        color = colorchooser.askcolor(title=f"Selecciona color del {tipo}")[1]
        if color:
            if tipo == "QR":
                self.color_qr = color
                self.btn_color_qr.config(bg=color)
            else:
                self.color_fondo = color
                self.btn_color_fondo.config(bg=color)
            self.actualizar_previsualizacion()

    def crear_widgets(self):
        # Título decorativo
        tk.Label(self.root, text="GENERADOR DE CÓDIGOS QR", font=("Arial", 14, "bold"), fg="#333").pack(pady=15)
        
        tk.Label(self.root, text="Contenido del QR:", font=("Arial", 10, "bold")).pack(pady=(5, 0))
        
        frame_entrada = tk.Frame(self.root)
        frame_entrada.pack(pady=5, padx=20, fill="x")
        
        self.entry_url = tk.Entry(frame_entrada, font=("Arial", 11))
        self.entry_url.pack(side="left", fill="x", expand=True, padx=(0, 5))
        
        self.entry_url.bind("<KeyRelease>", lambda e: self.actualizar_previsualizacion())
        self.entry_url.bind("<Control-v>", self.pegar_texto)
        self.entry_url.bind("<Control-V>", self.pegar_texto)
        self.entry_url.bind("<Button-3>", self.mostrar_menu_contextual)
        
        btn_pegar = tk.Button(frame_entrada, text="📋 Pegar", command=self.pegar_texto, bg="#e1e1e1", cursor="hand2")
        btn_pegar.pack(side="right")

        frame_colores = tk.Frame(self.root)
        frame_colores.pack(pady=10)

        self.btn_color_qr = tk.Button(frame_colores, text="Color QR", command=lambda: self.elegir_color("QR"), bg="black", fg="white", width=12, cursor="hand2")
        self.btn_color_qr.grid(row=0, column=0, padx=5)

        self.btn_color_fondo = tk.Button(frame_colores, text="Color Fondo", command=lambda: self.elegir_color("Fondo"), bg="white", width=12, cursor="hand2")
        self.btn_color_fondo.grid(row=0, column=1, padx=5)

        self.label_preview = tk.Label(self.root, bg="white", relief="groove", bd=2)
        self.label_preview.pack(pady=10)

        self.check_abrir = tk.Checkbutton(
            self.root, text="Abrir carpeta al finalizar", 
            variable=self.abrir_carpeta_var, font=("Arial", 9), cursor="hand2"
        )
        self.check_abrir.pack(pady=5)

        self.btn_generar = tk.Button(
            self.root, text="Guardar QR (Imagen o PDF)", 
            command=self.generar_y_abrir,
            bg="#4CAF50", fg="white", font=("Arial", 12, "bold"), height=2, cursor="hand2"
        )
        self.btn_generar.pack(pady=10, fill="x", padx=60)

    def obtener_imagen_qr(self):
        texto = self.entry_url.get().strip()
        if not texto: texto = "Vista Previa"
        qr = qrcode.QRCode(version=1, box_size=10, border=2)
        qr.add_data(texto)
        qr.make(fit=True)
        return qr.make_image(fill_color=self.color_qr, back_color=self.color_fondo).convert("RGB")

    def actualizar_previsualizacion(self, event=None):
        try:
            pil_img = self.obtener_imagen_qr()
            pil_img = pil_img.resize((250, 250), Image.Resampling.LANCZOS)
            self.img_preview = ImageTk.PhotoImage(pil_img)
            self.label_preview.config(image=self.img_preview)
        except: pass

    def generar_y_abrir(self):
        texto = self.entry_url.get().strip()
        if not texto:
            messagebox.showwarning("Atención", "Escribe algo antes de guardar.")
            return

        ruta_archivo = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[("Imagen PNG", "*.png"), ("Documento PDF", "*.pdf")],
            initialfile="mi_qr"
        )

        if ruta_archivo:
            try:
                img = self.obtener_imagen_qr()
                
                if ruta_archivo.lower().endswith(".pdf"):
                    img.save(ruta_archivo, "PDF", resolution=100.0)
                else:
                    img.save(ruta_archivo)

                # --- LIMPIEZA ---
                self.entry_url.delete(0, tk.END) # Limpia el texto
                self.actualizar_previsualizacion() # Resetea la vista previa

                if self.abrir_carpeta_var.get():
                    directorio = os.path.dirname(os.path.abspath(ruta_archivo))
                    if platform.system() == "Windows":
                        os.startfile(directorio)
                    else:
                        comando = "open" if platform.system() == "Darwin" else "xdg-open"
                        subprocess.Popen([comando, directorio])

                messagebox.showinfo("¡Éxito!", f"QR guardado correctamente.")
            except Exception as e:
                messagebox.showerror("Error", f"Ocurrió un error: {e}")

if __name__ == "__main__":
    root = tk.Tk()
    app = GeneradorQRPro(root)
    root.mainloop()