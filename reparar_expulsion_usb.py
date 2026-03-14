"""
Script para reparar problemas de expulsión de dispositivos USB en Windows
Se autoeleva a administrador si es necesario - Versión sin colores ANSI
"""

import os
import sys
import ctypes
import subprocess
import time
from typing import List, Tuple

def es_administrador() -> bool:
    """Verifica si el script se ejecuta como administrador"""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def ejecutar_como_administrador():
    """Reinicia el script como administrador"""
    script = os.path.abspath(sys.argv[0])
    ctypes.windll.shell32.ShellExecuteW(
        None, "runas", sys.executable, script, None, 1
    )
    sys.exit()

def ejecutar_comando(comando: List[str]) -> Tuple[str, str, int]:
    """Ejecuta un comando y retorna stdout, stderr y código de retorno"""
    try:
        proceso = subprocess.Popen(
            comando,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=True,
            text=True
        )
        stdout, stderr = proceso.communicate()
        return stdout, stderr, proceso.returncode
    except Exception as e:
        return "", str(e), -1

def desinstalar_controladores_usb() -> int:
    """Desinstala controladores USB usando pnputil"""
    print("[Paso 1/3] Desinstalando controladores USB...")
    
    stdout, stderr, code = ejecutar_comando(['pnputil', '/enum-devices', '/class', 'USB'])
    contador = 0
    
    if code == 0:
        lineas = stdout.split('\n')
        for linea in lineas:
            if 'Instance ID' in linea:
                instancia = linea.split(':')[-1].strip()
                if instancia:
                    print(f"  Desinstalando: {instancia}")
                    ejecutar_comando(['pnputil', '/remove-device', instancia])
                    contador += 1
                    time.sleep(0.5)
    
    print(f"  → Total: {contador} controladores desinstalados")
    return contador

def desinstalar_unidades_usb() -> int:
    """Desinstala unidades de disco USB"""
    print("[Paso 2/3] Desinstalando unidades USB...")
    
    stdout, stderr, code = ejecutar_comando(['pnputil', '/enum-devices', '/class', 'DiskDrive'])
    contador = 0
    
    if code == 0:
        lineas = stdout.split('\n')
        instancias = []
        nombres = []
        
        for i, linea in enumerate(lineas):
            if 'Instance ID' in linea:
                instancia = linea.split(':')[-1].strip()
                nombre = "Unidad USB"
                for j in range(max(0, i-5), i):
                    if 'Device Description' in lineas[j]:
                        nombre = lineas[j].split(':')[-1].strip()
                        break
                
                if 'USB' in nombre or 'usb' in nombre:
                    instancias.append((instancia, nombre))
        
        for instancia, nombre in instancias:
            print(f"  Desinstalando: {nombre}")
            ejecutar_comando(['pnputil', '/remove-device', instancia])
            contador += 1
            time.sleep(0.5)
    
    print(f"  → Total: {contador} unidades desinstaladas")
    return contador

def limpiar_registro():
    """Limpia entradas de registro de dispositivos montados"""
    print("[Paso 3/3] Limpiando configuración residual...")
    
    comando = ['reg', 'delete', 'HKLM\\SYSTEM\\MountedDevices', '/va', '/f']
    stdout, stderr, code = ejecutar_comando(comando)
    
    if code == 0:
        print("  ✓ Configuración de montaje limpiada")
    else:
        print("  ℹ No se pudo limpiar el registro (no crítico)")

def reiniciar_equipo(segundos: int = 10):
    """Reinicia el equipo después de X segundos"""
    print(f"\nReiniciando en {segundos} segundos...")
    print("Guarda tu trabajo!")
    ejecutar_comando(['shutdown', '/r', '/t', str(segundos)])

def main():
    """Función principal"""
    # Verificar administrador y autoelevar si es necesario
    if not es_administrador():
        print("Solicitando permisos de administrador...")
        ejecutar_como_administrador()
        return
    
    # Cabecera
    print("========================================")
    print("  REPARACIÓN DE PROBLEMAS DE EXPULSIÓN USB")
    print("========================================")
    print()
    
    print("Este script realizará las siguientes acciones:")
    print("  • Desinstalar controladores USB")
    print("  • Desinstalar unidades de disco USB")
    print("  • Limpiar configuración de montaje")
    print("  • Requerir reinicio del sistema")
    print()
    
    # Confirmación
    respuesta = input("¿Quieres continuar? (S/N): ")
    if respuesta.upper() != 'S':
        print("Operación cancelada")
        input("\nPresiona Enter para salir...")
        sys.exit(0)
    
    print()
    
    # Ejecutar pasos
    controladores = desinstalar_controladores_usb()
    unidades = desinstalar_unidades_usb()
    limpiar_registro()
    
    # Resumen
    print("\n========================================")
    print("RESUMEN DE LA OPERACIÓN:")
    print(f"  Controladores USB desinstalados: {controladores}")
    print(f"  Unidades USB desinstaladas: {unidades}")
    print()
    
    print("✅ PROCESO COMPLETADO")
    print("⚠️  IMPORTANTE: Debes REINICIAR el ordenador")
    print()
    
    # Preguntar por reinicio
    respuesta = input("¿Deseas reiniciar ahora? (S/N): ")
    if respuesta.upper() == 'S':
        reiniciar_equipo()
    else:
        print("Recuerda reiniciar manualmente para aplicar los cambios")
        input("\nPresiona Enter para salir...")

if __name__ == "__main__":
    main()