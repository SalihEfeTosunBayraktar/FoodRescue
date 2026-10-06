@echo off
rem Starts the local test server (installs requirements on first run).
cd /d "%~dp0"
py -3 -c "import fastapi, sqlalchemy, jwt, qrcode, multipart" 2>nul || py -3 -m pip install -r requirements.txt
py -3 run.py %*
