@echo off
echo Installing requirements...
pip install -r requirements.txt
pip install pyinstaller

echo Building Winterboy Studio...
pyinstaller --noconfirm --onedir --windowed --icon "app/resources/icon.ico" --name "WinterboyStudio"  "main.py"

echo Build complete! Check the 'dist' folder.
pause
