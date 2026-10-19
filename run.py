import subprocess
import sys
import os
import time
import webbrowser

def main():
    root_dir = os.path.dirname(os.path.abspath(__file__))
    frontend_dir = os.path.join(root_dir, "frontend")
    
    print("=" * 60)
    print("      INICIANDO DOCUMENT STUDIO (FASTAPI + REACT)")
    print("=" * 60)
    
    # Iniciar backend
    print("[1/2] Iniciando Backend en http://localhost:8000 ...")
    backend_proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"],
        cwd=root_dir
    )
    
    # Iniciar frontend
    print("[2/2] Iniciando Frontend en http://localhost:3000 ...")
    npm_cmd = "npm.cmd" if os.name == "nt" else "npm"
    frontend_proc = subprocess.Popen(
        [npm_cmd, "run", "dev", "--", "--port", "3000"],
        cwd=frontend_dir
    )
    
    time.sleep(2)
    webbrowser.open("http://localhost:3000")
    
    print("\n[OK] Servicios corriendo:")
    print("   - Frontend: http://localhost:3000")
    print("   - Swagger API Docs: http://localhost:8000/docs")
    print("\nPresiona Ctrl+C para detener ambos servicios.")
    
    try:
        backend_proc.wait()
        frontend_proc.wait()
    except KeyboardInterrupt:
        print("\nDeteniendo servicios...")
        backend_proc.terminate()
        frontend_proc.terminate()

if __name__ == "__main__":
    main()
