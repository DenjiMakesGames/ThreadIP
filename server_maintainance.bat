@echo off
python main_server.py
if %errorlevel% neq 0 (
   echo Server crashed, restarting...
   timeout /t 5
   goto start
)