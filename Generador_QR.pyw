import qrcode
import os
import tkinter as tk
from tkinter import messagebox, filedialog

def generar_qr():
    url = entry_url.get().strip()
    
    if not url:
        messagebox.showwarning("Atención", "Por favor, introduce un enlace o texto.")
        return

    # Preguntar dónde guardar el archivo
    ruta_archivo = filedialog.asksaveasfilename(
        defaultextension=".png",
        filetypes=[("Imagen PNG", "*.png")],
        title="Guardar QR como...",
        initialfile="mi_codigo_qr.png"
    )

    if ruta_archivo:
        try:
            # Configuración del QR (Alta corrección para el aula)
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_H,
                box_size=10,
                border=4,
            )
            qr.add_data(url)
            qr.make(fit=True)

            img = qr.make_image(fill_color="black", back_color="white")
            img.save(ruta_archivo)
            
            messagebox.showinfo("¡Éxito!", f"Código QR guardado en:\n{ruta_archivo}")
            entry_url.delete(0, tk.END) # Limpiar el campo para el siguiente
            
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo guardar: {e}")

# --- Configuración de la Ventana Gráfica ---
root = tk.Tk()
root.title("Generador de QR")
root.geometry("400x200")
root.resizable(False, False)

# Etiqueta de instrucciones
label = tk.Label(root, text="Pega aquí tu enlace o texto:", font=("Arial", 10))
label.pack(pady=20)

# Campo de entrada
entry_url = tk.Entry(root, width=50)
entry_url.pack(pady=5, padx=20)
entry_url.focus_set() # Poner el cursor listo para escribir

# Botón de generar
btn_generar = tk.Button(root, text="Generar y Guardar QR", command=generar_qr, 
                        bg="#4CAF50", fg="white", font=("Arial", 10, "bold"))
btn_generar.pack(pady=20)

root.mainloop()