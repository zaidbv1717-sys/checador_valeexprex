@echo off
title Reloj Checador
cd /d "%~dp0"
echo Iniciando el Reloj Checador...
echo (Esta ventana debe quedar abierta mientras el sistema este en uso)
echo.

echo Levantando la base de datos (Docker)...
docker compose up -d
if errorlevel 1 (
    echo No se pudo iniciar Docker. Asegurate de que Docker Desktop este abierto.
    pause
    exit /b 1
)

if not exist "backend\venv\Scripts\activate.bat" (
    echo No se encontro el entorno virtual del backend.
    echo Ejecuta primero: cd backend ^&^& python -m venv venv ^&^& venv\Scripts\activate ^&^& pip install -r requirements.txt
    pause
    exit /b 1
)

if not exist "frontend\dist\index.html" (
    echo Aviso: el frontend no esta compilado todavia.
    echo Ejecuta: cd frontend ^&^& npm install ^&^& npm run build
)

call backend\venv\Scripts\activate.bat
cd backend
uvicorn app.main:app --port 8000

echo.
echo El servidor se detuvo. Si esto fue un error, revisa el mensaje de arriba.
pause
