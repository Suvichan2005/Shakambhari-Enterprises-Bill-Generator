@echo off
echo Starting Invoice Generator local server...
start "" http://127.0.0.1:5000/
python app.py
pause
