import os
import shutil
import ctypes
import tkinter as tk
from tkinter import messagebox

def limpiar_sistema():
    root = tk.Tk()
    root.withdraw()
    
    # 1. Definir rutas temporales
    # %TEMP% suele ser C:\Users\Nombre\AppData\Local\Temp
    ruta_temp = os.environ.get('TEMP')
    
    confirmacion = messagebox.askyesno("Limpieza", "¿Deseas limpiar archivos temporales y vaciar la papelera?")
    if not confirmacion:
        return

    borrados = 0
    errores = 0

    # 2. Limpiar Carpeta Temp
    if os.path.exists(ruta_temp):
        for elemento in os.listdir(ruta_temp):
            ruta_completa = os.path.join(ruta_temp, elemento)
            try:
                if os.path.isfile(ruta_completa) or os.path.islink(ruta_completa):
                    os.unlink(ruta_completa) # Borra archivo o enlace
                elif os.path.isdir(ruta_completa):
                    shutil.rmtree(ruta_completa) # Borra carpeta entera
                borrados += 1
            except Exception:
                # Es normal que algunos archivos estén "en uso" y no se dejen borrar
                errores += 1

    # 3. Vaciar Papelera de Reciclaje (Uso de librería de Windows)
    try:
        # SHEmptyRecycleBinW: 0 = Todo, 1 = Sin confirmar, 2 = Sin sonido, 4 = Sin progreso
        ctypes.windll.shell32.SHEmptyRecycleBinW(None, None, 1 | 2 | 4)
    except Exception:
        errores += 1

    messagebox.showinfo("Limpieza Completada", 
                        f"Proceso finalizado.\n\nElementos eliminados: {borrados}\n"
                        f"Elementos en uso (no borrados): {errores}\n\n"
                        "La papelera ha sido vaciada.")
    root.destroy()

if __name__ == "__main__":
    limpiar_sistema()