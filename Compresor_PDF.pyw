import os
import subprocess
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from tkinterdnd2 import DND_FILES, TkinterDnD

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
GHOSTSCRIPT = os.path.join(BASE_DIR, "gs", "bin", "gswin64c.exe")

archivos = []
carpeta_salida = ""

def tamaño_mb(ruta):
    return os.path.getsize(ruta)/(1024*1024)

def seleccionar_archivos():
    global archivos

    archivos = filedialog.askopenfilenames(filetypes=[("PDF","*.pdf")])

    lista.delete(0, tk.END)

    for a in archivos:
        nombre = os.path.basename(a)
        tamaño = tamaño_mb(a)
        lista.insert(tk.END, f"{nombre}   ({tamaño:.1f} MB)")
def drop_archivos(event):

    archivos_drop = ventana.tk.splitlist(event.data)

    for a in archivos_drop:

        if a.lower().endswith(".pdf"):

            archivos.append(a)

            nombre = os.path.basename(a)
            tamaño = tamaño_mb(a)

            lista.insert(tk.END, f"{nombre}   ({tamaño:.1f} MB)")
def seleccionar_carpeta():
    global carpeta_salida

    carpeta_salida = filedialog.askdirectory()

    if carpeta_salida:
        etiqueta_carpeta.config(text=carpeta_salida)

def comprimir():

    if not archivos:
        messagebox.showerror("Error","Selecciona PDFs primero")
        return

    if not os.path.exists(GHOSTSCRIPT):
        messagebox.showerror("Error","No se encontró Ghostscript")
        return

    boton_comprimir.config(text="Comprimiendo...")
    ventana.update()

    total_original = 0
    total_final = 0

    progreso["maximum"] = len(archivos)
    progreso["value"] = 0

    calidad = calidad_var.get()

    for i,pdf in enumerate(archivos):

        nombre = os.path.basename(pdf)

        if carpeta_salida:
            salida = os.path.join(
                carpeta_salida,
                os.path.splitext(nombre)[0]+"_comprimido.pdf"
            )
        else:
            salida = os.path.splitext(pdf)[0]+"_comprimido.pdf"

        original = tamaño_mb(pdf)

        comando = [
            GHOSTSCRIPT,
            "-sDEVICE=pdfwrite",
            "-dCompatibilityLevel=1.4",
            f"-dPDFSETTINGS=/{calidad}",
            "-dNOPAUSE",
            "-dQUIET",
            "-dBATCH",
            f"-sOutputFile={salida}",
            pdf
        ]

        try:
            subprocess.run(
                comando,
                check=True,
                creationflags=subprocess.CREATE_NO_WINDOW
            )

            final = tamaño_mb(salida)

            total_original += original
            total_final += final

            reduccion_pdf = 100 - (final/original*100)

            lista.delete(i)
            lista.insert(
                i,
                f"{nombre}   {original:.1f} → {final:.1f} MB   (-{reduccion_pdf:.0f}%)"
            )

        except:
            pass

        progreso["value"] = i+1
        ventana.update_idletasks()

    reduccion = 100 - (total_final/total_original*100)

    boton_comprimir.config(text="Comprimir PDFs")

    messagebox.showinfo(
        "Terminado",
        f"Original: {total_original:.2f} MB\n"
        f"Final: {total_final:.2f} MB\n"
        f"Reducción: {reduccion:.1f}%"
    )

    if abrir_var.get():
        if carpeta_salida:
            os.startfile(carpeta_salida)
        else:
            os.startfile(os.path.dirname(archivos[0]))


ventana = TkinterDnD.Tk()
ventana.title("Compresor de PDFs")
ventana.geometry("500x420")

frame = tk.Frame(ventana,padx=10,pady=10)
frame.pack(fill="both",expand=True)

tk.Button(
    frame,
    text="Seleccionar o Arrastrar PDFs",
    command=seleccionar_archivos
).pack(fill="x")

lista = tk.Listbox(frame,height=10)
lista.pack(fill="both",expand=True,pady=5)
lista.drop_target_register(DND_FILES)
lista.dnd_bind('<<Drop>>', drop_archivos)
tk.Button(
    frame,
    text="Elegir carpeta de salida",
    command=seleccionar_carpeta
).pack(fill="x")

tk.Label(frame,text="Nivel de compresión").pack()

calidades={
    "Máxima compresión (70-90%)":"screen",
    "Equilibrado recomendado (40-70%)":"ebook",
    "Alta calidad (10-40%)":"printer",
    "Casi sin compresión":"prepress"
}

combo = ttk.Combobox(frame,values=list(calidades.keys()),state="readonly")
combo.current(1)
combo.pack()

calidad_var = tk.StringVar(value="ebook")

def cambiar_calidad(event):
    calidad_var.set(calidades[combo.get()])

combo.bind("<<ComboboxSelected>>",cambiar_calidad)

abrir_var = tk.BooleanVar()

tk.Checkbutton(
    frame,
    text="Abrir carpeta al terminar",
    variable=abrir_var
).pack(pady=5)

boton_comprimir = tk.Button(
    frame,
    text="Comprimir PDFs",
    height=2,
    command=comprimir
)
boton_comprimir.pack(pady=10)

progreso = ttk.Progressbar(frame)
progreso.pack(fill="x")

ventana.mainloop()