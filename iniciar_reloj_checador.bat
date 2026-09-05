@echo off
title Reloj Checador - Iniciando
cd /d "%~dp0"

echo Verificando Docker Desktop...
docker info >nul 2>&1
if not errorlevel 1 goto docker_ready

echo Docker Desktop no esta corriendo, iniciandolo...
start "" "C:\Program Files\Docker\Docker\Docker Desktop.exe"

echo Esperando a que Docker este listo (puede tardar 1-2 minutos)...
set /a tries=0
:wait_docker
ping -n 6 127.0.0.1 >nul
docker info >nul 2>&1
if not errorlevel 1 goto docker_ready
set /a tries+=1
if %tries% GEQ 30 (
    echo.
    echo Docker no respondio a tiempo. Abre Docker Desktop manualmente y
    echo vuelve a ejecutar este archivo.
    pause
    exit /b 1
)
goto wait_docker

:docker_ready
echo Docker listo.
echo.
echo Levantando el sistema (base de datos + backend + frontend)...
docker compose up -d
if errorlevel 1 (
    echo.
    echo Hubo un problema al iniciar los contenedores. Revisa el mensaje de arriba.
    pause
    exit /b 1
)

echo.
echo Esperando a que la pagina responda...
set /a webtries=0
:wait_web
curl -s -o nul http://localhost
if not errorlevel 1 goto web_ready
ping -n 3 127.0.0.1 >nul
set /a webtries+=1
if %webtries% GEQ 30 goto web_timeout
goto wait_web

:web_timeout
echo.
echo El sistema tardo mas de lo normal en responder. Abre http://localhost
echo manualmente en un rato, o vuelve a ejecutar este archivo.
pause
exit /b 1

:web_ready
echo.
echo ========================================================
echo  Reloj checador listo
echo  En esta computadora:    http://localhost
echo  Para el QR (celulares): revisa la pestana "Codigo QR"
echo                           dentro del panel de administracion
echo ========================================================
rundll32 url.dll,FileProtocolHandler http://localhost
ping -n 4 127.0.0.1 >nul
exit /b 0
