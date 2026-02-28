@echo off
echo Closing frontend and backend...

taskkill /FI "WINDOWTITLE eq VITE_DEV_SERVER" /F >nul 2>&1
taskkill /FI "WINDOWTITLE eq BOOKS_BACKEND" /F >nul 2>&1

echo Done.
pause
