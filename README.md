# EMS Project

Employee Management System built with Django.

## Requirements

- Python 3.13
- Windows 10/11
- Git

## 1) Clone and open the project

```bash
cd C:\Users\dancan.mbuvi
git clone <your-repo-url>
cd ems_project
```

## 2) Create a virtual environment

From the project root:

```cmd
C:\Program Files\Python313\python.exe -m venv env
```

## 3) Activate the environment

In Command Prompt:

```cmd
cd C:\Users\dancan.mbuvi\ems_project
venv\Scripts\activate.bat
```

## 4) Install dependencies

```cmd
python -m pip install --upgrade pip setuptools wheel
python -m pip install -r requirements.txt
```

## 5) Verify the environment works

```cmd
python -c "import django, widget_tweaks, xhtml2pdf, reportlab; print('Django', django.get_version()); print('xhtml2pdf ok'); print('reportlab', reportlab.__version__)"
```

## 6) Run database migrations

```cmd
python manage.py migrate
```

## 7) Start the app

```cmd
python manage.py runserver 0.0.0.0:8000
```

Then open:

```text
http://127.0.0.1:8000/
ttp://127.0.0.1:8000/hr/login/
http://127.0.0.1:8000/admin/

## Optional: create a superuser

```cmd
python manage.py createsuperuser
```

## Notes

- If the environment is broken, delete the `env` folder and recreate it.
- Use Python 3.13 for compatibility with the current dependency set.
- If you see missing package errors, rerun:

```cmd
python -m pip install -r requirements.txt
```

## Common troubleshooting

### Missing Django or package errors

```cmd
rmdir /s /q env
C:\Program Files\Python313\python.exe -m venv env
env\Scripts\activate.bat
python -m pip install --upgrade pip setuptools wheel
python -m pip install -r requirements.txt
```

### Port already in use

Use another port:

```cmd
python manage.py runserver 0.0.0.0:8080
```
