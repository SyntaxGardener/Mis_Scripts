import sys, os, traceback
from datetime import datetime

print("=== DIAGNÓSTICO ===")
print("Python:", sys.version)

# Buscar archivo xls en la carpeta actual
archivos = [f for f in os.listdir('.') if f.lower().endswith(('.xls','.xlsx','.csv'))]
print("Archivos Excel/CSV encontrados:", archivos)

if not archivos:
    print("ERROR: No hay ningún archivo xls/xlsx/csv en esta carpeta.")
    input("\nPulsa Enter para salir...")
    sys.exit(1)

archivo = archivos[0]
print(f"Usando: {archivo}")

try:
    import pandas as pd
    print("pandas OK")
except Exception as e:
    print("ERROR pandas:", e)
    input("\nPulsa Enter para salir...")
    sys.exit(1)

try:
    from pptx import Presentation
    print("python-pptx OK")
except Exception as e:
    print("ERROR python-pptx:", e)
    input("\nPulsa Enter para salir...")
    sys.exit(1)

try:
    from pptx.util import Emu, Pt
    from pptx.dml.color import RGBColor
    from pptx.enum.text import PP_ALIGN
    print("pptx imports OK")
except Exception as e:
    print("ERROR pptx imports:", e)
    input("\nPulsa Enter para salir...")
    sys.exit(1)

# Leer el archivo
try:
    ext = os.path.splitext(archivo)[1].lower()
    if ext == '.xls':
        df = pd.read_excel(archivo, engine='xlrd')
    else:
        df = pd.read_excel(archivo, engine='openpyxl')
    print(f"Archivo leído OK: {len(df)} filas, columnas: {list(df.columns)}")
except Exception as e:
    print("ERROR leyendo archivo:", e)
    traceback.print_exc()
    input("\nPulsa Enter para salir...")
    sys.exit(1)

# Intentar generar el pptx
try:
    # Importar funciones del script principal
    codigo = open('estadisticas_sauce.pyw', encoding='utf-8').read()
    # Quitar la parte GUI
    codigo_logica = codigo.split('# ── GUI')[0]
    codigo_logica = codigo_logica.replace('import tkinter as tk', '# import tkinter as tk')
    codigo_logica = codigo_logica.replace('from tkinter import ttk, filedialog, messagebox', '# tkinter')
    exec(codigo_logica, globals())
    print("Funciones cargadas OK")

    ref = datetime(2025, 9, 1)
    datos = procesar_listado(archivo, ref)
    print(f"Datos procesados: {datos['total']} alumnos, {datos['hombres']}H {datos['mujeres']}M")
    print("Grupos de edad:", list(datos['age_stats'].keys()))
    print("Nacionalidades:", list(datos['nat_stats'].keys()))

    salida = 'test_estadisticas.pptx'
    generar_pptx(datos, salida)
    print(f"\n✔ PPTX generado: {salida} ({os.path.getsize(salida)} bytes)")

except Exception as e:
    print("\nERROR generando PPTX:")
    traceback.print_exc()

input("\nPulsa Enter para salir...")
