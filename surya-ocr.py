import sys
import traceback
import subprocess
import os
import tempfile
from pathlib import Path

def instalar_python310():
    """Descarga e instala Python 3.10 portable y habilita site-packages."""
    print("-> Preparando entorno Python 3.10 totalmente aislado...")
    import urllib.request
    import zipfile
    
    url = "https://www.python.org/ftp/python/3.10.11/python-3.10.11-embed-amd64.zip"
    zip_path = os.path.join(tempfile.gettempdir(), "python310.zip")
    extract_path = Path(__file__).parent / "python310_engine"
    
    if not extract_path.exists():
        print("   Descargando Python 3.10 embebido...")
        urllib.request.urlretrieve(url, zip_path)
        
        print("   Descomprimiendo motor...")
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(extract_path)
        
        pth_file = list(extract_path.glob("*._pth"))
        if pth_file:
            with open(pth_file[0], "r") as f:
                content = f.read()
            content = content.replace("#import site", "import site")
            with open(pth_file[0], "w") as f:
                f.write(content)

        python_exe = str(extract_path / "python.exe")
        get_pip_path = str(extract_path / "get-pip.py")
        urllib.request.urlretrieve("https://bootstrap.pypa.io/get-pip.py", get_pip_path)
        subprocess.run([python_exe, get_pip_path], check=True)
    
    return str(extract_path / "python.exe")

def preparar_y_ejecutar():
    python310 = instalar_python310()
    python_dir = Path(python310).parent
    pip_exe = str(python_dir / "Scripts" / "pip.exe")

    flag_instalado = python_dir / "surya_ready.flag"
    
    if not flag_instalado.exists():
        print("-> Instalando paquetes exactos de Surya OCR...")
        paquetes = [
            "surya-ocr==0.4.14",
            "transformers==4.41.2",
            "pyperclip",
            "Pillow"
        ]
        resultado_pip = subprocess.run([pip_exe, "install"] + paquetes)
        if resultado_pip.returncode != 0:
            raise RuntimeError("Error durante la instalación de paquetes con pip.")
        open(flag_instalado, "w").close()

    print("-> Ejecutando análisis OCR con Surya...\n")
    comando = [python310, __file__, "--ejecutar_internal"] + [a for a in sys.argv[1:] if a != "--ejecutar_internal"]
    res = subprocess.run(comando)
    
    if res.returncode != 0:
        print("\n" + "="*60)
        print(f"EL SUBPROCESO FINALIZÓ CON CÓDIGO DE ERROR: {res.returncode}")
        print("="*60)

def main():
    import pyperclip
    from PIL import Image

    args_limpios = [a for a in sys.argv[1:] if a != "--ejecutar_internal"]

    if len(args_limpios) >= 1:
        ruta_str = args_limpios[0]
    else:
        print("Por favor, introduce o arrastra la ruta de la imagen:")
        ruta_str = input("> ").strip().strip('"').strip("'")

    if not ruta_str:
        print("Cancelado: No se especificó ninguna ruta de imagen.")
        return

    archivo_entrada = Path(ruta_str).resolve()
    if not archivo_entrada.exists():
        print(f"Error: No se encontró el archivo en {archivo_entrada}")
        return

    print(f"Procesando: {archivo_entrada.name}\n")

    print("-> Cargando Surya OCR en memoria...")
    from surya.ocr import run_ocr
    from surya.model.detection.segformer import load_model as load_det_model, load_processor as load_det_processor
    from surya.model.recognition.model import load_model as load_rec_model
    from surya.model.recognition.processor import load_processor as load_rec_processor

    det_model = load_det_model()
    det_processor = load_det_processor()
    rec_model = load_rec_model()
    rec_processor = load_rec_processor()

    imagen = Image.open(archivo_entrada)

    print("-> Extrayendo texto con Surya...")
    predictions = run_ocr([imagen], [["es", "en"]], det_model, det_processor, rec_model, rec_processor)

    lineas = []
    if predictions and len(predictions) > 0:
        for line in predictions[0].text_lines:
            lineas.append(line.text)

    texto = "\n".join(lineas).strip()

    if texto:
        pyperclip.copy(texto)
        print("\n" + "="*50)
        print(" ¡ÉXITO! Texto copiado al portapapeles.")
        print("="*50)
        print("\nTexto detectado por Surya:\n")
        print(texto)
    else:
        print("\nNo se detectó texto en la imagen.")

if __name__ == "__main__":
    try:
        if "--ejecutar_internal" in sys.argv or sys.version_info[:2] == (3, 10):
            main()
        else:
            preparar_y_ejecutar()
    except Exception as e:
        print("\n" + "="*60)
        print("ERROR EN EL SCRIPT PRINCIPAL:")
        print("="*60)
        traceback.print_exc()
    finally:
        print("\n" + "-"*60)
        input("Presiona Enter para cerrar esta ventana...")