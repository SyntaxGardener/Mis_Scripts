@echo off
:: 1. DETECCION DEL MOTOR
set MOTOR_USB="%~dp0..\Python_Motor\WPy64-31700\python\python.exe"

if exist %MOTOR_USB% (
    set PY_EXE=%MOTOR_USB%
) else (
    set PY_EXE=python
)

:: 2. EJECUCION
%PY_EXE% "%~dp0%~n0.py"

pause
exit
