
@echo off
title ReCloset - Servidor
cd /d "%~dp0"

echo ==================================
echo        INICIANDO RECLOSET
echo ==================================

if not exist ".venv\Scripts\python.exe" (
    echo ERRO: Ambiente virtual nao encontrado.
    pause
    exit /b 1
)

cd /d "%~dp0BackEnd"

if not exist "..\.venv\Scripts\uvicorn.exe" (
    echo Instalando dependencias do projeto...
    "..\.venv\Scripts\python.exe" -m pip install -r requirements.txt
)

echo.
echo Iniciando servidor FastAPI...
echo Aguarde a mensagem: Uvicorn running
echo.

"..\.venv\Scripts\python.exe" -m uvicorn app.main:app --reload

echo.
echo O servidor foi encerrado.
pause
