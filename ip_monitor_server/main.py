import uvicorn
from fastapi import FastAPI
import json
import os # Para construir rutas de archivo de forma segura
from contextlib import asynccontextmanager

from ip_monitor_server.camera_handler import CameraHandler
import ip_monitor_server.alert_queue as alert_queue_module # Importar el módulo

# --- Variables Globales ---
CONFIG_FILE_PATH = os.path.join(os.path.dirname(__file__), "config.json")
camera_threads = []
app_state = {"cameras_loaded": False, "camera_handlers": []}


# --- Funciones de Configuración ---
def load_camera_config(config_path=CONFIG_FILE_PATH):
    """Carga la configuración de las cámaras desde un archivo JSON."""
    if not os.path.exists(config_path):
        print(f"ERROR: El archivo de configuración {config_path} no fue encontrado.")
        return []
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
        print(f"INFO: Configuración de cámaras cargada desde {config_path}")
        return config
    except json.JSONDecodeError:
        print(f"ERROR: El archivo de configuración {config_path} no es un JSON válido.")
        return []
    except Exception as e:
        print(f"ERROR: Error inesperado al cargar {config_path}: {e}")
        return []

# --- Lógica de Inicio y Parada de la Aplicación (FastAPI lifespan) ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Código a ejecutar al inicio (startup)
    print("INFO: Iniciando servidor de monitoreo IP...")
    cameras_config = load_camera_config()

    if not cameras_config:
        print("WARN: No se encontraron configuraciones de cámaras o el archivo es inválido.")
        app_state["cameras_loaded"] = False
    else:
        print(f"INFO: Se encontraron {len(cameras_config)} cámaras en la configuración.")
        app_state["cameras_loaded"] = True
        for cam_info in cameras_config:
            if not cam_info.get("url"):
                print(f"WARN: Cámara '{cam_info.get('nombre', 'ID Desconocido')}' no tiene URL. Omitiendo.")
                continue

            # Usar el módulo alert_queue directamente
            handler = CameraHandler(cam_info, alert_queue_module, processing_interval=1.0) # Procesar cada 1 seg
            app_state["camera_handlers"].append(handler)
            handler.start()
            print(f"INFO: Hilo para cámara {cam_info.get('nombre', cam_info.get('id'))} iniciado.")

        if not app_state["camera_handlers"]:
            print("WARN: Ningún hilo de cámara pudo ser iniciado (verifique URLs en config.json).")
            app_state["cameras_loaded"] = False # Actualizar si ninguna cámara arrancó

    yield # El servidor está activo aquí

    # Código a ejecutar al apagar (shutdown)
    print("INFO: Deteniendo servidor de monitoreo IP...")
    for handler in app_state["camera_handlers"]:
        if handler.is_alive():
            print(f"INFO: Deteniendo hilo para cámara {handler.camera_name}...")
            handler.stop()
            # handler.join(timeout=5) # Esperar a que el hilo termine
            # Quitado el join aquí para un apagado más rápido, los hilos son daemon.
            # Si se necesita un apagado más grácil donde cada frame actual termine,
            # se podría re-añadir el join con un timeout.
    print("INFO: Todos los hilos de cámara han recibido la señal de detención.")

app = FastAPI(lifespan=lifespan)

# --- Rutas de la API ---
@app.get("/")
async def root():
    num_active_handlers = sum(1 for h in app_state["camera_handlers"] if h.is_alive())
    return {
        "status": "IP Monitor Server running",
        "cameras_configured_and_loaded": app_state["cameras_loaded"],
        "active_camera_threads": num_active_handlers,
        "total_camera_handlers_initialized": len(app_state["camera_handlers"]),
        "alert_queue_max_size": alert_queue_module.MAX_ALERTS_IN_MEMORY,
        "current_alerts_in_queue": len(alert_queue_module.recent_alerts)
    }

@app.get("/api/alertas")
async def get_alerts(limit: int = 20):
    """
    Devuelve las 'limit' alertas más recientes.
    Por defecto, las últimas 20.
    """
    if limit <= 0:
        limit = 20 # Reset a valor por defecto si es inválido

    alerts = alert_queue_module.get_all_alerts_sorted(limit=limit)
    return {"alerts": alerts, "count": len(alerts)}

@app.get("/api/alertas/all")
async def get_all_alerts_in_memory():
    """
    Devuelve todas las alertas actualmente en la memoria de la cola (hasta MAX_ALERTS_IN_MEMORY).
    """
    alerts = alert_queue_module.get_all_alerts_sorted() # Sin límite explícito, tomará todas en deque
    return {"alerts": alerts, "count": len(alerts)}


if __name__ == "__main__":
    print("INFO: Lanzando servidor FastAPI con Uvicorn...")
    print(f"      Configuración de cámaras esperada en: {CONFIG_FILE_PATH}")
    print(f"      API de alertas disponible en: http://localhost:8000/api/alertas")
    print(f"      Estado del servidor en: http://localhost:8000/")

    # Asegurarse de que la ruta del config sea correcta si se ejecuta main.py directamente
    # Esto es más para desarrollo. En producción, uvicorn se llamaría desde la raíz del proyecto.
    # Ejemplo: uvicorn ip_monitor_server.main:app --reload

    # Para que uvicorn encuentre la app correctamente cuando se ejecuta este script directamente:
    # es mejor ejecutarlo desde la raíz del proyecto como:
    # python -m uvicorn ip_monitor_server.main:app --host 0.0.0.0 --port 8000 --reload
    # O simplemente:
    # uvicorn ip_monitor_server.main:app --host 0.0.0.0 --port 8000

    # Si se ejecuta `python ip_monitor_server/main.py`, uvicorn.run necesita el nombre del módulo.
    # Esto puede ser complicado si el CWD no es la raíz del proyecto.
    # La forma estándar es `uvicorn module:app`.

    # Para simplificar la ejecución directa de ESTE archivo para pruebas rápidas:
    uvicorn.run(app, host="0.0.0.0", port=8000)

    # NOTA: Si se ejecuta `python ip_monitor_server/main.py`, los imports relativos como
    # `from ip_monitor_server.camera_handler...` podrían fallar si Python no considera
    # el directorio padre como parte de sys.path.
    # Ejecutar con `python -m ip_monitor_server.main` (desde el directorio que contiene `ip_monitor_server`)
    # o usar `uvicorn ip_monitor_server.main:app` es más robusto.
    # La inclusión de `os.path.join(os.path.dirname(__file__), ...)` ayuda con la ruta del config.json.
