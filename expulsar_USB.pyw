import subprocess
import ctypes
import sys

def expulsar_seguro():
    try:
        # Comando de Windows para abrir el diálogo de extracción segura
        comando = 'rundll32.exe shell32.dll,Control_RunDLL hotplug.dll'
        subprocess.Popen(comando, shell=True)
    except Exception as e:
        # Si falla, muestra un mensaje de error básico de Windows
        ctypes.windll.user32.MessageBoxW(0, f"Error al intentar expulsar: {e}", "Error de Expulsión", 16)

if __name__ == "__main__":
    expulsar_seguro()