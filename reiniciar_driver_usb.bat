@echo off
title Limpieza de Sistema y Reactivacion USB
echo ========================================
echo Limpiando archivos temporales...
echo ========================================

:: Borrar temporales de usuario
del /s /f /q %temp%\*.*
rd /s /q %temp%
md %temp%

:: Borrar temporales del sistema
del /s /f /q C:\Windows\Temp\*.*
rd /s /q C:\Windows\Temp
md C:\Windows\Temp

:: Limpiar cache de Prefetch
del /s /f /q C:\Windows\Prefetch\*.*

echo ========================================
echo Reiniciando controladores de USB...
echo ========================================
:: Esto obliga al sistema a buscar cambios de hardware
pnputil /scan-devices

echo ========================================
echo Limpieza completada. 
echo Intenta conectar tu USB ahora.
echo ========================================
pause