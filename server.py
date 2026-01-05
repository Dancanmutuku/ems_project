# serve.py
from waitress import serve
from ems_project.wsgi import application  # Make sure 'ems_project' matches the folder containing wsgi.py

if __name__ == '__main__':
    serve(application, host='127.0.0.1', port=8000)