# -*- coding: utf-8 -*-
import os
import tkinter as tk
from tkinter import filedialog, messagebox
from pypdf import PdfWriter

# Guardaremos las rutas en una lista global que sincronizaremos con la interfaz
rutas_pdfs = []

def seleccionar_archivos():
    tipos = [("Archivos PDF", "*.pdf")]
    archivos = filedialog.askopenfilenames(title="Selecciona los PDFs", filetypes=tipos)
    if archivos:
        for f in archivos:
            if f not in rutas_pdfs: # Evitar duplicados
                rutas_pdfs.append(f)
        actualizar_lista()

def actualizar_lista():
    lista_visual.delete(0, tk.END)
    for i, f in enumerate(rutas_pdfs, 1):
        lista_visual.insert(tk.END, f"{i}. {os.path.basename(f)}")
    
    # Arreglo del botón: Si hay archivos, lo ponemos bonito y activo
    if rutas_pdfs:
        btn_unir.config(state="normal", bg="#8e44ad", fg="white", cursor="hand2")
    else:
        btn_unir.config(state="disabled", bg="#d7bde2", fg="#7d3c98")

def mover_arriba():
    seleccion = lista_visual.curselection()
    if not seleccion or seleccion[0] == 0:
        return
    idx = seleccion[0]
    # Intercambiamos en la lista lógica
    rutas_pdfs[idx], rutas_pdfs[idx-1] = rutas_pdfs[idx-1], rutas_pdfs[idx]
    actualizar_lista()
    lista_visual.selection_set(idx-1) # Mantener la selección en el archivo movido

def mover_abajo():
    seleccion = lista_visual.curselection()
    if not seleccion or seleccion[0] == len(rutas_pdfs) - 1:
        return
    idx = seleccion[0]
    rutas_pdfs[idx], rutas_pdfs[idx+1] = rutas_pdfs[idx+1], rutas_pdfs[idx]
    actualizar_lista()
    lista_visual.selection_set(idx+1)

def ejecutar_union():
    destino = filedialog.asksaveasfilename(
        title="Guardar como...",
        defaultextension=".pdf",
        initialfile="PDF_Unificado.pdf"
    )
    if not destino: return

    try:
        fusionador = PdfWriter()
        for pdf in rutas_pdfs:
            fusionador.append(pdf)
        with open(destino, "wb") as salida:
            fusionador.write(salida)
        fusionador.close()
        
        messagebox.showinfo("Éxito", "PDF unificado correctamente.")
        rutas_pdfs.clear()
        actualizar_lista()
    except Exception as e:
        messagebox.showerror("Error", str(e))

# --- Interfaz ---
app = tk.Tk()
app.title("Unificador de PDF")
ancho_ventana = 450
alto_ventana = 600
distancia_superior = 50

# USAR 'app' en lugar de 'ventana'
ancho_pantalla = app.winfo_screenwidth()

# Calcular la posición X para que esté centrada
posicion_x = (ancho_pantalla // 2) - (ancho_ventana // 2)

# Aplicar la geometría a 'app'
app.geometry(f"{ancho_ventana}x{alto_ventana}+{posicion_x}+{distancia_superior}")
app.configure(padx=20, pady=20)

tk.Label(app, text="1. Lista de archivos a unir:", font=("Arial", 10, "bold")).pack(anchor="w")

# Contenedor para lista y botones laterales
frame_lista = tk.Frame(app)
frame_lista.pack(fill="x", pady=10)

lista_visual = tk.Listbox(frame_lista, height=12, font=("Arial", 10), selectbackground="#3498db")
lista_visual.pack(side="left", fill="x", expand=True)

# Botones de orden al lado de la lista
frame_orden = tk.Frame(frame_lista)
frame_orden.pack(side="right", padx=5)

tk.Button(frame_orden, text="▲", command=mover_arriba, width=3).pack(pady=2)
tk.Button(frame_orden, text="▼", command=mover_abajo, width=3).pack(pady=2)
tk.Button(frame_orden, text="❌", command=lambda: [rutas_pdfs.pop(lista_visual.curselection()[0]), actualizar_lista()] if lista_visual.curselection() else None, fg="red").pack(pady=10)

# Botones principales
tk.Button(app, text="➕ Añadir Archivos", command=seleccionar_archivos).pack(fill="x", pady=5)

# Botón de unir con colores forzados para evitar el "gris invisible" de Windows
btn_unir = tk.Button(app, text="🔗 UNIR ARCHIVOS PDF", command=ejecutar_union,
                    font=("Arial", 11, "bold"), height=2,
                    state="disabled", bg="#d7bde2", fg="#7d3c98", 
                    disabledforeground="#7d3c98") # Esto fuerza el color del texto incluso desactivado
btn_unir.pack(fill="x", pady=20)

app.mainloop()