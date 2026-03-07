@echo off
title EXPULSAR USB (CON PRIVILEGIOS)

:: --- TRUCO PARA AUTO-ELEVAR A ADMINISTRADOR ---
>nul 2>&1 "%SYSTEMROOT%\system32\cacls.exe" "%SYSTEMROOT%\system32\config\system"
if '%errorlevel%' NEQ '0' (
    echo Solicitando permisos de administrador...
    goto UACPrompt
) else ( goto gotAdmin )
:UACPrompt
    echo Set UAC = CreateObject^("Shell.Application"^) > "%temp%\getadmin.vbs"
    echo UAC.ShellExecute "%~s0", "", "", "runas", 1 >> "%temp%\getadmin.vbs"
    "%temp%\getadmin.vbs"
    exit /B
:gotAdmin
    if exist "%temp%\getadmin.vbs" ( del "%temp%\getadmin.vbs" )
    pushd "%cd%"
    CD /D "%~dp0"
:: ----------------------------------------------

echo ===========================================
echo       HERRAMIENTA DE EXPULSION SEGURA
echo ===========================================
echo.

set /p letra=Introduce la letra del USB (ejemplo: D, E, F): 

echo Intentando expulsar unidad %letra%...
:: -L reintenta, -f fuerza la expulsion
removedrive %letra%: -L -f

echo.
echo Proceso finalizado.
pause
exit