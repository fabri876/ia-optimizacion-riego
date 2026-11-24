import os
import sys
import threading
import time
import webbrowser
import socket

# --- PARCHE ANTI-CRASH ---
if sys.stdout is None:
    sys.stdout = open(os.devnull, "w")
if sys.stderr is None:
    sys.stderr = open(os.devnull, "w")

import streamlit.web.cli as stcli

def obtener_puerto_libre():
    """Busca un puerto disponible en la computadora para evitar choques"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(('localhost', 0))
    puerto = sock.getsockname()[1]
    sock.close()
    return puerto

def resolver_ruta(ruta_relativa):
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, ruta_relativa)
    return os.path.join(os.path.abspath("."), ruta_relativa)

def abrir_navegador(puerto):
    time.sleep(3)
    webbrowser.open_new(f"http://localhost:{puerto}")

if __name__ == "__main__":
    if hasattr(sys, '_MEIPASS'):
        os.chdir(sys._MEIPASS)
    
    # Obtener un puerto que no esté siendo usado por nada más
    puerto_asignado = obtener_puerto_libre()
    
    # Pasamos el puerto al navegador
    threading.Thread(target=abrir_navegador, args=(puerto_asignado,), daemon=True).start()
    
    ruta_app = "src/app.py" if hasattr(sys, '_MEIPASS') else resolver_ruta(os.path.join("src", "app.py"))
    
    sys.argv = [
        "streamlit", 
        "run", 
        ruta_app, 
        "--global.developmentMode=false",
        "--server.headless=true",
        f"--server.port={puerto_asignado}" # Forzamos a Streamlit a usar el puerto libre
    ]
    
    sys.exit(stcli.main())