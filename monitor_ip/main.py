# Lógica principal del sistema
import cv2
import json
import time
from detector import detect_people # Asumiendo que detector.py tendrá esta función
from notifier import log_alert # Asumiendo que notifier.py tendrá esta función

def load_camera_config(config_path="monitor_ip/config.json"):
    """Carga la configuración de las cámaras desde un archivo JSON."""
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
        return config
    except FileNotFoundError:
        print(f"Error: El archivo de configuración {config_path} no fue encontrado.")
        return []
    except json.JSONDecodeError:
        print(f"Error: El archivo de configuración {config_path} no es un JSON válido.")
        return []

def process_camera(camera_info):
    """
    Procesa el stream de una cámara: captura frames, detecta personas y notifica.
    Esta función está diseñada para ser ejecutada en un hilo por cada cámara.
    """
    print(f"Iniciando procesamiento para: {camera_info['nombre']} ({camera_info['id']}) en URL: {camera_info['url']}")
    cap = cv2.VideoCapture(camera_info['url'])

    if not cap.isOpened():
        print(f"Error al abrir el stream de la cámara: {camera_info['nombre']}")
        return

    while True:
        ret, frame = cap.read()
        if not ret:
            print(f"Error al leer el frame de la cámara: {camera_info['nombre']}. Reintentando conexión...")
            cap.release()
            time.sleep(5) # Esperar antes de reintentar
            cap = cv2.VideoCapture(camera_info['url'])
            if not cap.isOpened():
                print(f"No se pudo restablecer la conexión con la cámara: {camera_info['nombre']}. Terminando thread.")
                break
            continue

        # Aquí llamaremos a la función de detección de personas
        people_detected, frame_with_detections = detect_people(frame, camera_info['id'])

        # Simulación de detección para prueba inicial - YA NO ES NECESARIO
        # people_detected = False # Cambiar esto cuando detect_people esté implementado
        # frame_with_detections = frame # Usar frame original hasta que detect_people devuelva el modificado

        if people_detected:
            # El detector.py ya podría estar dibujando, pero la alerta es responsabilidad del main.
            log_alert(f"Alerta: Actividad/Persona detectada en {camera_info['nombre']} ({camera_info['id']})")
            # Aquí se podrían añadir más acciones de notificación (sonido, pop-up, etc.)

        # Mostrar el frame (opcional, principalmente para depuración)
        cv2.imshow(camera_info['nombre'], frame_with_detections)
        if cv2.waitKey(1) & 0xFF == ord('q'): # Presionar 'q' para cerrar esta ventana específica
            break

        # Pequeña pausa para no sobrecargar la CPU si el stream es muy rápido o está vacío
        # Ajustar según sea necesario
        # time.sleep(0.01) # Comentado para permitir que waitKey maneje el flujo

    cap.release()
    cv2.destroyWindow(camera_info['nombre']) # Destruir ventana específica si se usó imshow
    print(f"Procesamiento terminado para: {camera_info['nombre']}")

if __name__ == "__main__":
    cameras = load_camera_config()
    if not cameras:
        print("No se cargaron cámaras. Terminando.")
    else:
        print(f"Cámaras cargadas: {len(cameras)}")

        # Para esta etapa inicial, procesaremos solo la primera cámara como ejemplo
        # La gestión multihilo se implementará en una etapa posterior.
        if cameras:
            print("\n--- Iniciando prueba de conexión con la primera cámara ---")
            first_camera = cameras[0]
            cap = cv2.VideoCapture(first_camera['url'])
            if cap.isOpened():
                print(f"Conexión exitosa con {first_camera['nombre']} ({first_camera['url']})")
                ret, frame = cap.read()
                if ret:
                    print(f"Frame leído exitosamente. Dimensiones: {frame.shape}")
                    cv2.imshow(f"Test Frame - {first_camera['nombre']}", frame)
                    print("Presiona cualquier tecla en la ventana del frame para continuar...")
                    cv2.waitKey(0)
                    cv2.destroyAllWindows()
                else:
                    print(f"Error al leer frame de {first_camera['nombre']}.")
                cap.release()
            else:
                print(f"Error al abrir el stream de la cámara: {first_camera['nombre']} ({first_camera['url']})")
            print("--- Prueba de conexión finalizada ---\n")

        print("Para iniciar el monitoreo de la primera cámara (con visualización y detección según 'detector.py'):")
        print("Descomente la línea `process_camera(cameras[0])` al final de este script y ejecútelo.")
        print("Asegúrese de tener las dependencias necesarias instaladas (ver requirements.txt).")
        print("El modelo de detección por defecto en detector.py es cvlib con YOLOv4-tiny.")

        # Ejemplo de cómo se llamaría para una cámara:
        # if cameras:
        #    print(f"\nIniciando monitoreo para la cámara: {cameras[0]['nombre']}. Presione 'q' en la ventana de la cámara para detener.")
        #    process_camera(cameras[0])
        # else:
        #    print("No hay cámaras configuradas para iniciar el monitoreo.")

        print("\nSistema de monitoreo listo para pruebas de una sola cámara (descomentando la llamada a process_camera).")
        print("La funcionalidad multihilo para múltiples cámaras se añadirá en la Etapa 5.")
        print("El usuario debe encargarse de instalar las dependencias listadas en requirements.txt.")
