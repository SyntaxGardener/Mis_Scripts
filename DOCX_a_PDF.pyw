# -*- coding: utf-8 -*-
import os
import tkinter as tk
from tkinter import filedialog, messagebox
import win32com.client
import pythoncom
import subprocess # Para abrir la carpeta en Windows

def seleccionar_archivos():
    tipos = [("Documentos Word", "*.docx")]
    archivos = filedialog.askopenfilenames(title="Selecciona los documentos Word", filetypes=tipos)
    if archivos:
        global rutas_word
        rutas_word = archivos
        lista_visual.delete(0, tk.END)
        for f in archivos:
            lista_visual.insert(tk.END, os.path.basename(f))

def seleccionar_destino():
    global carpeta_destino
    carpeta_destino = filedialog.askdirectory(title="Carpeta donde se guardarán los PDF")
    if carpeta_destino:
        lbl_destino.config(text=f"📂 Destino: ...{carpeta_destino[-30:]}", fg="blue")
        btn_abrir.pack_forget() # Ocultar botón de abrir si cambiamos ruta

def abrir_carpeta():
    if 'carpeta_destino' in globals() and os.path.exists(carpeta_destino):
        os.startfile(carpeta_destino)

def ejecutar_conversion():
    if not 'rutas_word' in globals() or not rutas_word:
        messagebox.showwarning("Paso 1", "Primero selecciona archivos .docx")
        return
    
    if not 'carpeta_destino' in globals() or not carpeta_destino:
        messagebox.showwarning("Paso 2", "Selecciona una carpeta de destino.")
        return

    pythoncom.CoInitialize()
    word = None
    exitos = 0
    errores = []

    try:
        btn_convertir.config(state="disabled", text="Convertiendo... espere")
        app.update()

        word = win32com.client.DispatchEx("Word.Application")
        word.Visible = False
        word.DisplayAlerts = 0

        for ruta_docx in rutas_word:
            try:
                abs_docx = os.path.abspath(ruta_docx)
                nombre_base = os.path.splitext(os.path.basename(ruta_docx))[0]
                abs_pdf = os.path.abspath(os.path.join(carpeta_destino, f"{nombre_base}.pdf"))

                doc = word.Documents.Open(abs_docx, ReadOnly=1)
                doc.ExportAsFixedFormat(abs_pdf, 17) 
                doc.Close(0)
                exitos += 1
            except Exception as e:
                errores.append(f"{nombre_base}: {str(e)}")

        word.Quit()
        
        if exitos > 0:
            btn_abrir.pack(pady=5, fill="x") # Mostrar botón de abrir carpeta
            if messagebox.askyesno("Éxito", f"¡Convertidos {exitos} archivos!\n\n¿Quieres abrir la carpeta de destino ahora?"):
                abrir_carpeta()
            lista_visual.delete(0, tk.END)

    except Exception as e:
        messagebox.showerror("Error", f"Fallo al conectar con Word: {e}")
    finally:
        pythoncom.CoUninitialize()
        btn_convertir.config(state="normal", text="🚀 CONVERTIR A PDF")

# --- Interfaz ---
app = tk.Tk()
app.title("Word a PDF")

# --- Configuración de dimensiones ---
ancho_ventana = 400
alto_ventana = 550
distancia_superior = 50

# USAR 'app' en lugar de 'ventana'
ancho_pantalla = app.winfo_screenwidth()

# Calcular la posición X para que esté centrada
posicion_x = (ancho_pantalla // 2) - (ancho_ventana // 2)

# Aplicar la geometría a 'app'
app.geometry(f"{ancho_ventana}x{alto_ventana}+{posicion_x}+{distancia_superior}")
app.configure(padx=20, pady=20)

# Paso 1
tk.Label(app, text="1. Documentos a convertir:", font=("Arial", 10, "bold")).pack(anchor="w")
tk.Button(app, text="➕ Buscar .docx", command=seleccionar_archivos).pack(pady=5, fill="x")
lista_visual = tk.Listbox(app, height=6, font=("Arial", 9), bg="#fdfdfd")
lista_visual.pack(fill="x", pady=5)

# Paso 2
tk.Label(app, text="\n2. Carpeta de salida:", font=("Arial", 10, "bold")).pack(anchor="w")
tk.Button(app, text="📁 Elegir Carpeta", command=seleccionar_destino).pack(pady=5, fill="x")
lbl_destino = tk.Label(app, text="Selección pendiente...", fg="red", font=("Arial", 8, "italic"))
lbl_destino.pack(anchor="w")

# Paso 3
tk.Label(app, text="").pack()
btn_convertir = tk.Button(app, text="🚀 CONVERTIR A PDF", command=ejecutar_conversion,
                         bg="#c0392b", fg="white", font=("Arial", 12, "bold"), height=2)
btn_convertir.pack(fill="x", pady=10)

# Botón extra (oculto hasta que termine)
btn_abrir = tk.Button(app, text="📂 Abrir Carpeta de Resultados", command=abrir_carpeta, bg="#eee")

app.mainloop()