@echo off
REM Starts the full ChangeGraph stack: Postgres (Docker), backend (uvicorn), frontend (Vite).
REM Backend and frontend each open in their own window so their logs stay visible;
REM close those windows (or Ctrl+C in them) to stop them.

setlocal
set ROOT=%~dp0

echo === ChangeGraph: checking Docker ===
docker info >nul 2>&1
if errorlevel 1 (
    echo Docker engine not responding -- launching Docker Desktop...
    start "" "C:\Program Files\Docker\Docker\Docker Desktop.exe"
    echo Waiting for Docker engine to come up...
    :waitdocker
    timeout /t 5 >nul
    docker info >nul 2>&1
    if errorlevel 1 goto waitdocker
)
echo Docker is up.

echo === ChangeGraph: starting Postgres ===
docker start changegraph-postgres >nul 2>&1
if errorlevel 1 (
    echo Container "changegraph-postgres" not found -- creating it...
    docker run -d --name changegraph-postgres ^
        -e POSTGRES_USER=changegraph ^
        -e POSTGRES_PASSWORD=changegraph ^
        -e POSTGRES_DB=changegraph ^
        -p 55432:5432 ^
        postgres:16-alpine
)
echo Postgres is up on localhost:55432.

echo === ChangeGraph: starting backend (http://127.0.0.1:8000) ===
start "ChangeGraph Backend" cmd /k "cd /d "%ROOT%backend" && .venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload"

echo === ChangeGraph: starting frontend (http://127.0.0.1:5173) ===
start "ChangeGraph Frontend" cmd /k "cd /d "%ROOT%frontend" && npm run dev"

echo.
echo All services launching. Backend and frontend logs are in their own windows.
echo   Frontend: http://127.0.0.1:5173
echo   Backend:  http://127.0.0.1:8000/docs
endlocal
