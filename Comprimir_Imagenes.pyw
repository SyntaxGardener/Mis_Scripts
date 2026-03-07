import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image
import os

def seleccionar_archivos():
    tipos = [("Imágenes", "*.jpg *.jpeg *.png *.webp")]
    archivos = filedialog.askopenfilenames(title="Selecciona imágenes", filetypes=tipos)
    if archivos:
        lista_visual.delete(0, tk.END)
        global rutas_completas
        rutas_completas = archivos
        for f in archivos:
            lista_visual.insert(tk.END, os.path.basename(f))

def seleccionar_destino():
    global carpeta_destino
    carpeta_destino = filedialog.askdirectory()
    if carpeta_destino:
        lbl_destino.config(text=f"📂 Guardar en: ...{carpeta_destino[-25:]}", fg="blue")

def procesar():
    if not 'rutas_completas' in globals() or not rutas_completas:
        messagebox.showwarning("Paso 1", "Selecciona las fotos primero.")
        return
    
    if not 'carpeta_destino' in globals() or not carpeta_destino:
        messagebox.showwarning("Paso 2", "Selecciona dónde quieres guardar las fotos.")
        return

    calidad = slider_calidad.get()
    exitos = 0
    
    for ruta in rutas_completas:
        try:
            nombre_archivo = os.path.basename(ruta)
            nombre_sin_ext = os.path.splitext(nombre_archivo)[0]
            # Ahora usamos la carpeta elegida
            nueva_ruta = os.path.join(carpeta_destino, f"{nombre_sin_ext}_reducida.jpg")
            
            img = Image.open(ruta).convert("RGB")
            img.save(nueva_ruta, "JPEG", optimize=True, quality=calidad)
            exitos += 1
        except Exception as e:
            print(f"Error con {ruta}: {e}")

    messagebox.showinfo("Éxito", f"¡Listo! {exitos} imágenes guardadas en:\n{carpeta_destino}")

# --- Interfaz Mejorada ---
app = tk.Tk()
app.title("Compresor de Imágenes")
app.geometry("400x520")
app.configure(padx=20, pady=15)

# 1. Selección de Archivos
tk.Label(app, text="1. Selecciona las fotos originales", font=("Arial", 10, "bold")).pack(anchor="w")
tk.Button(app, text="➕ Añadir Archivos", command=seleccionar_archivos, bg="#f0f0f0").pack(pady=5, fill="x")
lista_visual = tk.Listbox(app, height=5, font=("Arial", 9))
lista_visual.pack(fill="x", pady=5)

# 2. Carpeta de Destino (LO NUEVO)
tk.Label(app, text="\n2. ¿Dónde las guardamos?", font=("Arial", 10, "bold")).pack(anchor="w")
tk.Button(app, text="📁 Seleccionar Carpeta de Destino", command=seleccionar_destino).pack(pady=5, fill="x")
lbl_destino = tk.Label(app, text="No has seleccionado carpeta", fg="red", font=("Arial", 8, "italic"))
lbl_destino.pack(anchor="w")

# 3. Calidad
tk.Label(app, text="\n3. Calidad de compresión", font=("Arial", 10, "bold")).pack(anchor="w")
slider_calidad = tk.Scale(app, from_=10, to=100, orient="horizontal")
slider_calidad.set(70)
slider_calidad.pack(fill="x")

# 4. Botón Ejecutar
tk.Label(app, text="").pack()
btn_go = tk.Button(app, text="🚀 EMPEZAR COMPRESIÓN", command=procesar, 
                   bg="#27ae60", fg="white", font=("Arial", 11, "bold"), height=2)
btn_go.pack(fill="x")

app.mainloop()