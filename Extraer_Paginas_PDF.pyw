# -*- coding: utf-8 -*-
import os
import tkinter as tk
from tkinter import filedialog, messagebox
from pypdf import PdfReader, PdfWriter

def seleccionar_archivo():
    archivo = filedialog.askopenfilename(title="Selecciona el PDF original", filetypes=[("Archivo PDF", "*.pdf")])
    if archivo:
        global ruta_origen, total_paginas
        ruta_origen = archivo
        reader = PdfReader(archivo)
        total_paginas = len(reader.pages)
        
        lbl_archivo.config(text=f"📄 {os.path.basename(archivo)}", fg="blue")
        lbl_info.config(text=f"Este documento tiene {total_paginas} páginas.")
        btn_extraer.config(state="normal")

def procesar_extraccion():
    rango_input = entrada_rango.get()
    if not rango_input:
        messagebox.showwarning("Atención", "Introduce las páginas (ej: 1-3, 5)")
        return

    # Pedir destino antes de procesar
    destino = filedialog.asksaveasfilename(
        title="Guardar como...",
        defaultextension=".pdf",
        filetypes=[("Archivo PDF", "*.pdf")],
        initialfile="Paginas_Extraidas.pdf"
    )
    
    if not destino:
        return

    try:
        reader = PdfReader(ruta_origen)
        paginas_a_extraer = set()
        
        # Lógica de procesamiento de rango (limpieza de espacios)
        partes = rango_input.replace(" ", "").split(",")
        for parte in partes:
            if "-" in parte:
                inicio, fin = map(int, parte.split("-"))
                for p in range(inicio, fin + 1):
                    if 1 <= p <= total_paginas:
                        paginas_a_extraer.add(p - 1)
            else:
                p = int(parte)
                if 1 <= p <= total_paginas:
                    paginas_a_extraer.add(p - 1)

        if not paginas_a_extraer:
            messagebox.showwarning("Error", "No se indicaron páginas válidas para este PDF.")
            return

        # Crear el nuevo PDF
        writer = PdfWriter()
        for p_index in sorted(list(paginas_a_extraer)):
            writer.add_page(reader.pages[p_index])
        
        with open(destino, "wb") as f_salida:
            writer.write(f_salida)
        
        if messagebox.askyesno("Éxito", f"¡Listo! Se han extraído {len(paginas_a_extraer)} páginas.\n\n¿Quieres abrir el archivo ahora?"):
            os.startfile(destino)

    except Exception as e:
        messagebox.showerror("Error", f"Ocurrió un problema: {e}")

# --- Interfaz Gráfica ---
app = tk.Tk()
app.title("Extractor de Páginas PDF")
# --- Configuración de dimensiones ---
ancho_ventana = 400
alto_ventana = 450
distancia_superior = 50

# USAR 'app' en lugar de 'ventana'
ancho_pantalla = app.winfo_screenwidth()

# Calcular la posición X para que esté centrada
posicion_x = (ancho_pantalla // 2) - (ancho_ventana // 2)

# Aplicar la geometría a 'app'
app.geometry(f"{ancho_ventana}x{alto_ventana}+{posicion_x}+{distancia_superior}")
app.configure(padx=20, pady=20)

# 1. Selección de archivo
tk.Label(app, text="1. Selecciona el PDF original:", font=("Arial", 10, "bold")).pack(anchor="w")
tk.Button(app, text="📂 Abrir PDF", command=seleccionar_archivo).pack(pady=5, fill="x")
lbl_archivo = tk.Label(app, text="Ningún archivo seleccionado", fg="gray", font=("Arial", 8, "italic"))
lbl_archivo.pack(anchor="w")

lbl_info = tk.Label(app, text="", font=("Arial", 9))
lbl_info.pack(pady=5)

# 2. Rango de páginas
tk.Label(app, text="\n2. Indica las páginas a extraer:", font=("Arial", 10, "bold")).pack(anchor="w")
tk.Label(app, text="Ejemplos: 1-5  |  1,3,8  |  1-3, 10, 12-15", fg="#666", font=("Arial", 8)).pack(anchor="w")
entrada_rango = tk.Entry(app, font=("Arial", 11))
entrada_rango.pack(pady=10, fill="x")

# 3. Acción
tk.Label(app, text="").pack()
btn_extraer = tk.Button(app, text="✂️ EXTRAER Y GUARDAR", command=procesar_extraccion,
                        bg="#e67e22", fg="white", font=("Arial", 11, "bold"), height=2, state="disabled")
btn_extraer.pack(fill="x")

app.mainloop()