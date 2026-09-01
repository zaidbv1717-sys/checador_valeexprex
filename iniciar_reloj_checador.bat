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
timeout /t 5 /nobreak >nul
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
echo ========================================================
echo  Reloj checador listo
echo  En esta computadora:    http://localhost
echo  Para el QR (celulares): revisa la pestana "Codigo QR"
echo                           dentro del panel de administracion
echo ========================================================
timeout /t 8
exit /b 0
