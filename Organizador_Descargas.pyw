import os
import shutil
from pathlib import Path
import tkinter as tk
from tkinter import messagebox # <--- Necesario para ver qué pasa

def organizar_descargas():
    # Creamos una ventana raíz oculta para los mensajes
    root = tk.Tk()
    root.withdraw() 

    descargas_path = Path.home() / "Downloads"
    
    directorio_mapeo = {
        "Documentos": [".pdf", ".docx", ".txt", ".xlsx", ".pptx", ".csv"],
        "Imagenes": [".jpg", ".jpeg", ".png", ".gif", ".svg", ".bmp"],
        "Audio": [".mp3", ".wav", ".ogg", ".flac"],
        "Videos": [".mp4", ".mov", ".avi", ".mkv"],
        "Ejecutables_y_Comprimidos": [".exe", ".msi", ".zip", ".rar", ".7z"]
    }

    archivos_movidos = 0

    if not descargas_path.exists():
        messagebox.showerror("Error", f"No se encontró la ruta: {descargas_path}")
        return

    for archivo in descargas_path.iterdir():
        if archivo.is_file():
            extension = archivo.suffix.lower()
            
            for categoria, extensiones in directorio_mapeo.items():
                if extension in extensiones:
                    ruta_destino = descargas_path / categoria
                    ruta_destino.mkdir(exist_ok=True)
                    
                    try:
                        shutil.move(str(archivo), str(ruta_destino / archivo.name))
                        archivos_movidos += 1
                    except Exception as e:
                        # Si hay un error, ahora sí lo verás
                        pass 
                    break
    
    # Avisamos al usuario al terminar
    messagebox.showinfo("Organizador", f"¡Limpieza terminada!\nArchivos movidos: {archivos_movidos}")
    root.destroy()

if __name__ == "__main__":
    organizar_descargas()