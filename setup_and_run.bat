@echo off
cd /d "%~dp0"

if exist env (
    rmdir /s /q env
)

"C:\Program Files\Python313\python.exe" -m venv env
call env\Scripts\activate.bat
python -m pip install --upgrade pip setuptools wheel
python -m pip install -r requirements.txt
python -c "import django, widget_tweaks, xhtml2pdf, reportlab; print('Django', django.get_version()); print('xhtml2pdf ok'); print('reportlab', reportlab.__version__)"
python manage.py check
python manage.py runserver 0.0.0.0:8000
