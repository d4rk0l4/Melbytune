@echo off
REM Gera o MelbyTune.exe no seu PC (precisa de Python instalado so aqui, uma vez).
pip install -r requirements.txt
pyinstaller --noconfirm --onefile --windowed --uac-admin --icon assets\icon.ico --add-data "assets;assets" --collect-all customtkinter --name MelbyTune main.py
echo.
echo Pronto! O executavel esta em dist\MelbyTune.exe
pause
