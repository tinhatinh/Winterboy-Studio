@echo off
echo Installing requirements...
pip install -r requirements.txt
pip install pyinstaller

rem Chi dung icon khi file icon co that (mac dinh repo khong kem app/resources/icon.ico)
set "ICONFLAG="
if exist "app\resources\icon.ico" set "ICONFLAG=--icon app/resources/icon.ico"

echo Building Winterboy Studio...
rem capcut_voices.json phai duoc copy vung _internal/app/services de engine doc duoc
pyinstaller --noconfirm --onedir --windowed %ICONFLAG% --name "WinterboyStudio" ^
  --add-data "app/services/capcut_voices.json;app/services" ^
  "main.py"

echo Build complete! Check the 'dist' folder.
pause
