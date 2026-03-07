@echo off
set "BASE_DIR=%~dp0"

:: 1. Definir rutas posibles del script (subcarpeta o misma carpeta)
if exist "%BASE_DIR%Mis_Scripts\menu.pyw" (
    set "SCRIPT=%BASE_DIR%Mis_Scripts\menu.pyw"
) else (
    set "SCRIPT=%BASE_DIR%menu.pyw"
)

:: 2. Intentar usar WinPython 
set "WINPY=%BASE_DIR%Python_Motor\WPy64-31700\python\pythonw.exe"

if exist "%WINPY%" (
    start "" "%WINPY%" "%SCRIPT%"
    exit
)

:: 3. Si no hay WinPython, usar el Python del PC
where pythonw >nul 2>nul
if %errorlevel% equ 0 (
    start "" pythonw "%SCRIPT%"
    exit
)

msg * "No se encontro Python ni el Script."