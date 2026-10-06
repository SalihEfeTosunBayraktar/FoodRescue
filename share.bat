@echo off
rem Shares the local test server through a temporary Cloudflare link. Ctrl+C stops everything.
cd /d "%~dp0"
py -3 -c "import fastapi, sqlalchemy, jwt, qrcode, multipart" 2>nul || py -3 -m pip install -r requirements.txt
py -3 tools\share.py %*
