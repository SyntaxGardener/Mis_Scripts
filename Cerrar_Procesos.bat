@echo off
title Limpiador de Trabajo y Chrome - Raquel
echo Finalizando procesos de Citrix...
taskkill /F /IM SelfServicePlugin.exe /T
taskkill /F /IM Citrix* /T
echo.
echo Finalizando procesos de Python...
taskkill /F /IM python* /T
echo.
echo Cerrando Google Chrome para liberar RAM...
taskkill /F /IM chrome.exe /T
echo.
echo Limpiando archivos temporales...
del /s /f /q %temp%\*.*
echo.
echo ------------------------------------------
echo PROCESO FINALIZADO: Tu portatil ya esta fresco.
echo ------------------------------------------
pause