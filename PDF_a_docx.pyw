# -*- coding: utf-8 -*-
import os
import tkinter as tk
from tkinter import filedialog, messagebox
from pdf2docx import Converter

def seleccionar_archivos():
    tipos = [("Archivos PDF", "*.pdf")]
    archivos = filedialog.askopenfilenames(title="Selecciona los PDF", filetypes=tipos)
    if archivos:
        global rutas_pdf
        rutas_pdf = archivos
        lista_visual.delete(0, tk.END)
        for f in archivos:
            lista_visual.insert(tk.END, os.path.basename(f))

def seleccionar_destino():
    global carpeta_destino
    carpeta_destino = filedialog.askdirectory(title="Carpeta para guardar los Word (.docx)")
    if carpeta_destino:
        lbl_destino.config(text=f"📂 Guardar en: ...{carpeta_destino[-30:]}", fg="blue")
        btn_abrir.pack_forget()

def abrir_carpeta():
    if 'carpeta_destino' in globals() and os.path.exists(carpeta_destino):
        os.startfile(carpeta_destino)

def ejecutar_conversion():
    if not 'rutas_pdf' in globals() or not rutas_pdf:
        messagebox.showwarning("Paso 1", "Primero selecciona los archivos PDF.")
        return
    
    if not 'carpeta_destino' in globals() or not carpeta_destino:
        messagebox.showwarning("Paso 2", "Selecciona una carpeta de destino.")
        return

    exitos = 0
    errores = []

    try:
        # Bloqueamos el botón para evitar clics dobles mientras procesa
        btn_convertir.config(state="disabled", text="Convirtiendo... (esto puede tardar)")
        app.update()

        for ruta_pdf in rutas_pdf:
            try:
                nombre_base = os.path.splitext(os.path.basename(ruta_pdf))[0]
                ruta_docx = os.path.join(carpeta_destino, f"{nombre_base}.docx")
                
                # Motor de conversión pdf2docx
                cv = Converter(ruta_pdf)
                cv.convert(ruta_docx, start=0, end=None)
                cv.close()
                
                exitos += 1
            except Exception as e:
                errores.append(f"{nombre_base}: {str(e)}")

        if exitos > 0:
            btn_abrir.pack(pady=5, fill="x")
            if messagebox.askyesno("Éxito", f"¡Hecho! {exitos} archivos convertidos a Word.\n\n¿Quieres ver los archivos ahora?"):
                abrir_carpeta()
            lista_visual.delete(0, tk.END)

        if errores:
            messagebox.showwarning("Aviso", f"Hubo problemas con {len(errores)} archivos.")

    except Exception as e:
        messagebox.showerror("Error Crítico", f"Ocurrió un error inesperado: {e}")
    finally:
        btn_convertir.config(state="normal", text="📝 CONVERTIR A WORD (.DOCX)")

# --- Interfaz Gráfica ---
app = tk.Tk()
app.title("PDF a Word")
app.geometry("400x550")
app.configure(padx=20, pady=20)

# 1. Selección de PDF
tk.Label(app, text="1. Selecciona los PDF originales:", font=("Arial", 10, "bold")).pack(anchor="w")
tk.Button(app, text="➕ Añadir PDFs", command=seleccionar_archivos).pack(pady=5, fill="x")
lista_visual = tk.Listbox(app, height=6, font=("Arial", 9), bg="#f9f9f9")
lista_visual.pack(fill="x", pady=5)

# 2. Destino
tk.Label(app, text="\n2. Carpeta de salida:", font=("Arial", 10, "bold")).pack(anchor="w")
tk.Button(app, text="📁 Seleccionar Carpeta", command=seleccionar_destino).pack(pady=5, fill="x")
lbl_destino = tk.Label(app, text="No has seleccionado destino", fg="red", font=("Arial", 8, "italic"))
lbl_destino.pack(anchor="w")

# 3. Acción
tk.Label(app, text="").pack()
btn_convertir = tk.Button(app, text="📝 CONVERTIR A WORD (.DOCX)", command=ejecutar_conversion,
                         bg="#2980b9", fg="white", font=("Arial", 11, "bold"), height=2)
btn_convertir.pack(fill="x", pady=10)

# Botón extra oculto
btn_abrir = tk.Button(app, text="📂 Abrir Carpeta de Resultados", command=abrir_carpeta, bg="#eee")

app.mainloop()