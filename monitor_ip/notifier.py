# Sistema de alertas
import datetime

LOG_FILE = "monitor_ip/detection_alerts.log"

def log_alert(message):
    """
    Registra un mensaje de alerta con timestamp en la consola y en un archivo de log.
    """
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_message_console = f"ALERTA [{timestamp}]: {message}"
    log_message_file = f"{timestamp} - {message}\n"

    print(log_message_console)

    try:
        with open(LOG_FILE, 'a') as f:
            f.write(log_message_file)
    except Exception as e:
        print(f"Error al escribir en el archivo de log ({LOG_FILE}): {e}")

# Opcional: Funciones para alertas sonoras o GUI (requerirían dependencias adicionales)
# from playsound import playsound # El usuario necesitaría instalar playsound: pip install playsound

def play_alert_sound(sound_file="path/to/alert_sound.mp3"):
    """
    Reproduce un sonido de alerta.
    El usuario debe tener 'playsound' instalado y el archivo de sonido.
    """
    try:
        # playsound(sound_file)
        print(f"Simulación: Reproduciendo sonido de alerta desde {sound_file} (playsound no está activo por defecto).")
        print("Para habilitar, instale 'playsound' y descomente la llamada a playsound() en notifier.py.")
    except Exception as e:
        # print(f"Error al reproducir sonido ({sound_file}) con playsound: {e}")
        # print("Asegúrese de que 'playsound' esté instalado y el archivo de sonido sea válido.")
        print(f"Error simulado al reproducir sonido ({sound_file}): {e}. Verifique la dependencia 'playsound'.")


# Para popups con PyQt5, la integración sería más compleja e implicaría
# manejar un loop de aplicación Qt, lo cual podría ser excesivo para alertas simples
# y mejor gestionado si todo el sistema tuviera una GUI principal en PyQt5.

if __name__ == '__main__':
    # Pruebas para el notificador
    print("Ejecutando prueba de notifier.py...")

    log_alert("Prueba de alerta de detección de persona en Cámara X.")
    log_alert("Otra alerta de prueba desde el Pasillo Y.")

    print(f"\nLos mensajes de alerta deberían haber aparecido arriba y también estar en el archivo: {LOG_FILE}")

    print("\nProbando simulación de alerta sonora (requiere que el usuario instale 'playsound' para funcionar realmente):")
    play_alert_sound("monitor_ip/example_alert_sound.mp3") # Asumir que existe un sonido de ejemplo

    print("\nPrueba de notifier.py finalizada.")
