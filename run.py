import subprocess
import sys
import os
import time
import webbrowser
import shutil
import urllib.request

def get_base_dir():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

def find_python():
    if not getattr(sys, 'frozen', False):
        return sys.executable
    
    py_path = shutil.which("python")
    if py_path and "WindowsApps" not in py_path:
        return py_path
        
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

def kill_proc_tree(pid):
    """Termina de forma forzosa un proceso y todos sus subprocesos hijos en Windows."""
    try:
        subprocess.run(["taskkill", "/F", "/T", "/PID", str(pid)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        pass

def is_backend_alive():
    try:
        req = urllib.request.urlopen("http://127.0.0.1:8008/api/documents", timeout=2)
        return req.status == 200
    except Exception:
        return False

def main():
    root_dir = get_base_dir()
    frontend_dir = os.path.join(root_dir, "frontend")
    
    py_bin = find_python()
    npm_bin = find_npm()
    
    creationflags = 0
    if os.name == "nt":
        creationflags = subprocess.CREATE_NO_WINDOW
        
    # Iniciar backend en puerto 8008 con host 127.0.0.1
    backend_proc = subprocess.Popen(
        [py_bin, "-m", "uvicorn", "backend.main:app", "--host", "127.0.0.1", "--port", "8008"],
        cwd=root_dir,
        creationflags=creationflags
    )
    
    # Iniciar frontend en puerto 4173 con host 127.0.0.1 (evita error EACCES de Windows en 5173)
    frontend_proc = subprocess.Popen(
        [npm_bin, "run", "dev", "--", "--host", "127.0.0.1", "--port", "4173"],
        cwd=frontend_dir,
        creationflags=creationflags
    )
    
    # Dar tiempo a que Node y FastAPI inicialicen
    time.sleep(3)
    webbrowser.open("http://127.0.0.1:4173")
    
    # Monitor de ciclo de vida
    consecutive_failures = 0
    try:
        while True:
            time.sleep(2)
            if backend_proc.poll() is not None:
                break
            if not is_backend_alive():
                consecutive_failures += 1
                if consecutive_failures >= 3:
                    break
            else:
                consecutive_failures = 0
    except KeyboardInterrupt:
        pass
    finally:
        # 6. Tumbar absolutamente todo para no dejar nada consumiendo recursos en segundo plano
        if backend_proc.poll() is None:
            kill_proc_tree(backend_proc.pid)
        if frontend_proc.poll() is None:
            kill_proc_tree(frontend_proc.pid)

if __name__ == "__main__":
    main()
