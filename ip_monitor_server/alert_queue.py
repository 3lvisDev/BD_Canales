import queue
import datetime
from collections import deque

MAX_ALERTS_IN_MEMORY = 100  # Mantener un historial de las últimas N alertas

# Usaremos una deque con tamaño máximo para las alertas recientes para la API
# y una queue.Queue para la comunicación entre threads si fuera necesario desacoplar más,
# pero para obtener las "últimas N", una deque es más directa.
# Por simplicidad y eficiencia para "últimas N", usaremos deque directamente.
# Si el productor y consumidor fueran muy dispares en velocidad, queue.Queue sería mejor.

# Esta deque almacenará las alertas para ser consultadas por la API.
# Es thread-safe para appends y pops de ambos lados, pero el acceso concurrente
# para obtener las "N últimas" debe ser manejado con cuidado si hay muchas escrituras.
# Sin embargo, para este caso de uso (lectura de API no tan frecuente como detecciones),
# debería ser suficiente.
recent_alerts = deque(maxlen=MAX_ALERTS_IN_MEMORY)

def add_alert(camera_id, camera_name, alert_details="Persona detectada"):
    """
    Añade una nueva alerta a la cola de alertas recientes.
    """
    timestamp = datetime.datetime.now().isoformat()
    alert_event = {
        "timestamp": timestamp,
        "camera_id": camera_id,
        "camera_name": camera_name,
        "details": alert_details
    }
    recent_alerts.append(alert_event)

    # También podríamos imprimir en consola o loggear desde aquí si se desea centralizar
    # print(f"ALERTA REGISTRADA: {alert_event}")

def get_recent_alerts(count=10):
    """
    Obtiene las 'count' alertas más recientes.
    Devuelve una lista de alertas, la más reciente primero.
    """
    # Deque se llena por la derecha (append) y las más antiguas se caen por la izquierda.
    # Para obtener las más recientes, tomamos los últimos N elementos.
    # Convertir a lista para devolver una copia y evitar problemas de modificación concurrente.
    return list(recent_alerts)[-count:]

def get_all_alerts_sorted(limit=None):
    """
    Obtiene todas las alertas almacenadas, ordenadas de la más reciente a la más antigua.
    Se puede aplicar un límite.
    """
    alerts_copy = list(recent_alerts)
    alerts_copy.reverse() # Deque se itera de más antiguo a más nuevo, invertimos para más nuevo primero
    if limit:
        return alerts_copy[:limit]
    return alerts_copy


if __name__ == "__main__":
    # Pruebas
    print("Probando alert_queue...")
    add_alert("cam_01", "Entrada Principal", "Movimiento detectado")
    add_alert("cam_02", "Pasillo", "Persona cruzando")

    import time
    time.sleep(1)
    add_alert("cam_01", "Entrada Principal", "Objeto sospechoso")

    print("\nÚltimas 2 alertas:")
    for alert in get_recent_alerts(2):
        print(alert)

    print("\nTodas las alertas (más recientes primero):")
    for alert in get_all_alerts_sorted():
        print(alert)

    print(f"\nLlenando hasta el máximo de {MAX_ALERTS_IN_MEMORY + 5} para probar el límite...")
    for i in range(MAX_ALERTS_IN_MEMORY + 5):
        add_alert(f"cam_test_{i}", f"Cámara Test {i}", f"Evento de prueba {i}")
        if i < 5: # Imprimir las primeras para ver que se añaden
            print(f"Añadida alerta de cam_test_{i}")

    print(f"\nTotal de alertas almacenadas: {len(recent_alerts)}") # Debería ser MAX_ALERTS_IN_MEMORY

    print("\nÚltimas 5 alertas después de llenar la cola:")
    last_5 = get_all_alerts_sorted(limit=5)
    for alert in last_5:
        print(alert)

    # Verificar que la primera alerta ("cam_01", "Movimiento detectado") ya no esté
    all_current_alerts = get_all_alerts_sorted()
    initial_alert_present = any(a['details'] == "Movimiento detectado" for a in all_current_alerts)
    print(f"\n¿La alerta inicial 'Movimiento detectado' sigue presente?: {initial_alert_present}") # Debería ser False

    print("\nPrueba de alert_queue finalizada.")
