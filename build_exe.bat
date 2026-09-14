@echo off
python -m pip install -r requirements-build.txt
python -m PyInstaller --noconfirm --clean --onefile --windowed --name TianFuYuanRunMonitor house_monitor.py
echo Build complete: dist\TianFuYuanRunMonitor.exe
