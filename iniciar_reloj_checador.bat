@echo off
title Reloj Checador
cd /d "%~dp0"
echo Iniciando el Reloj Checador...
echo (Esta ventana debe quedar abierta mientras el sistema este en uso)
echo.
python server.py
echo.
echo El servidor se detuvo. Si esto fue un error, revisa el mensaje de arriba.
pause
