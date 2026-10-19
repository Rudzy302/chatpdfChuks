import subprocess
import sys
import os
import time
import webbrowser
import shutil

def get_base_dir():
    # Si se ejecuta como .exe empaquetado por PyInstaller
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    # Si se ejecuta como script .py normal
    return os.path.dirname(os.path.abspath(__file__))

def find_python():
    # En runtime congelado, sys.executable es el .exe (chatpdf.exe), NO python.exe
    if not getattr(sys, 'frozen', False):
        return sys.executable
    
    # 1. Intentar encontrar python en el PATH del sistema
    py_path = shutil.which("python")
    if py_path and "WindowsApps" not in py_path:
        return py_path
        
    # 2. Rutas conocidas comunes en Windows
    candidates = [
        r"C:\Users\rdavi\AppData\Local\Python\pythoncore-3.14-64\python.exe",
        r"C:\Users\rdavi\AppData\Local\Python\bin\python.exe"
    ]
    for c in candidates:
        if os.path.exists(c):
            return c
            
    return py_path or "python"

def find_npm():
    npm_path = shutil.which("npm.cmd") or shutil.which("npm")
    if npm_path:
        return npm_path
    common_npm = r"C:\Program Files\nodejs\npm.cmd"
    if os.path.exists(common_npm):
        return common_npm
    return "npm.cmd" if os.name == "nt" else "npm"

def main():
    root_dir = get_base_dir()
    frontend_dir = os.path.join(root_dir, "frontend")
    
    py_bin = find_python()
    npm_bin = find_npm()
    
    # Flag para ocultar ventanas en Windows si corre en segundo plano
    creationflags = 0
    if os.name == "nt":
        creationflags = subprocess.CREATE_NO_WINDOW
        
    # Iniciar backend
    backend_proc = subprocess.Popen(
        [py_bin, "-m", "uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"],
        cwd=root_dir,
        creationflags=creationflags
    )
    
    # Iniciar frontend
    frontend_proc = subprocess.Popen(
        [npm_bin, "run", "dev", "--", "--port", "3000"],
        cwd=frontend_dir,
        creationflags=creationflags
    )
    
    time.sleep(2)
    webbrowser.open("http://localhost:3000")
    
    try:
        backend_proc.wait()
        frontend_proc.wait()
    except KeyboardInterrupt:
        backend_proc.terminate()
        frontend_proc.terminate()

if __name__ == "__main__":
    main()
