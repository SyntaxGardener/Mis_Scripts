@echo off
title Limpiador - Raquel
color 0B

echo 1. Finalizando procesos de Citrix y Python...
taskkill /F /IM SelfServicePlugin.exe /T 2>nul
taskkill /F /IM Citrix* /T 2>nul
taskkill /F /IM python* /T 2>nul

echo 2. Limpiando procesos "fantasma" de Office y PDF...
:: Esto solo cierra los programas si se quedaron bloqueados en memoria
taskkill /F /IM WINWORD.EXE /T 2>nul
taskkill /F /IM EXCEL.EXE /T 2>nul
taskkill /F /IM POWERPNT.EXE /T 2>nul
taskkill /F /IM AcroRd32.exe /T 2>nul
taskkill /F /IM Acrobat.exe /T 2>nul
taskkill /F /IM AdobeCollabSync.exe /T 2>nul

echo 3. Liberando Chrome y reiniciando Explorador...
taskkill /F /IM chrome.exe /T 2>nul
:: Reiniciar el explorador es el "toque maestro" para soltar el USB
taskkill /F /IM explorer.exe /T 2>nul
start explorer.exe

echo 4. Borrando temporales...
del /s /f /q %temp%\*.* 2>nul

echo.