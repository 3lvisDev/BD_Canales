import cv2
import threading
import time
import datetime # Para timestamps en alertas
from ip_monitor_server.detector import analyze_frame
from ip_monitor_server.alert_queue import add_alert

class CameraHandler(threading.Thread):
    def __init__(self, camera_info, alert_queue_module, processing_interval=0.5):
        super().__init__()
        self.camera_id = camera_info.get("id", "unknown_id")
        self.camera_name = camera_info.get("nombre", "Unknown Camera")
        self.camera_url = camera_info.get("url", None)
        self.alert_queue = alert_queue_module # Referencia al módulo alert_queue.py

        self.processing_interval = processing_interval # Segundos entre análisis de frames
        self.running = False
        self.cap = None
        self.daemon = True # El hilo terminará si el programa principal termina

        if not self.camera_url:
            print(f"ERROR [{self.camera_name}]: URL de cámara no proporcionada.")
            # No se puede iniciar sin URL, pero el hilo podría no hacer nada o terminar.
            # Por ahora, se marcará como no corriendo.
            self.running = False
            return

        print(f"INFO [{self.camera_name}]: Hilo de cámara inicializado para URL: {self.camera_url}")

    def _connect(self):
        print(f"INFO [{self.camera_name}]: Intentando conectar a {self.camera_url}...")
        self.cap = cv2.VideoCapture(self.camera_url)
        if not self.cap.isOpened():
            print(f"ERROR [{self.camera_name}]: No se pudo abrir el stream de video.")
            self.cap = None
            return False
        print(f"INFO [{self.camera_name}]: Conexión exitosa.")
        return True

    def run(self):
        self.running = True

        if not self.camera_url:
            print(f"ERROR [{self.camera_name}]: No hay URL para procesar. Terminando hilo.")
            self.running = False
            return

        if not self._connect():
            # Intentar reconectar después de un tiempo si la conexión inicial falla
            print(f"WARN [{self.camera_name}]: Conexión inicial fallida. Reintentando en 10 segundos...")
            time.sleep(10)
            if not self._connect(): # Segundo intento
                print(f"ERROR [{self.camera_name}]: Conexión fallida después de reintento. Terminando hilo.")
                self.running = False
                return

        last_processed_time = time.time()

        while self.running:
            if self.cap is None: # Si perdimos la conexión
                print(f"WARN [{self.camera_name}]: Conexión perdida. Intentando reconectar en 10 segundos...")
                time.sleep(10)
                if not self._connect():
                    print(f"ERROR [{self.camera_name}]: Falla al reconectar. Esperando otros 30s antes de reintentar.")
                    time.sleep(30) # Espera más larga antes del próximo ciclo de reconexión
                    continue # Vuelve al inicio del while self.running para reintentar conexión
                else:
                    last_processed_time = time.time() # Resetear tiempo de procesamiento

            ret, frame = self.cap.read()

            if not ret:
                print(f"WARN [{self.camera_name}]: No se pudo leer el frame. Stream podría haber terminado o hay un problema.")
                if self.cap:
                    self.cap.release()
                self.cap = None # Marcar para reconexión
                continue # Ir al siguiente ciclo para intentar reconectar

            current_time = time.time()
            if (current_time - last_processed_time) >= self.processing_interval:
                # Procesar frame
                try:
                    detection_made, details = analyze_frame(frame, self.camera_id)
                    if detection_made:
                        alert_message = f"Actividad detectada en {self.camera_name}"
                        if details: # Si hay detalles (ej. bounding boxes)
                            # Por ahora, solo un mensaje genérico. Se podrían añadir los detalles si es necesario.
                            # alert_message += f" Detalles: {details}" # Esto podría ser muy verboso para la alerta simple
                            pass

                        self.alert_queue.add_alert(
                            camera_id=self.camera_id,
                            camera_name=self.camera_name,
                            alert_details=alert_message
                        )
                        # print(f"DEBUG [{self.camera_name}]: Alerta enviada a la cola: {alert_message}")

                except Exception as e:
                    print(f"ERROR [{self.camera_name}]: Excepción durante analyze_frame: {e}")

                last_processed_time = current_time

            # Pequeña pausa para ceder el control, especialmente si el processing_interval es muy bajo
            # o si la lectura de frames es más rápida que el intervalo.
            # Esto evita un bucle muy ajustado si el intervalo es grande.
            time.sleep(0.01)

        if self.cap:
            self.cap.release()
        print(f"INFO [{self.camera_name}]: Hilo de cámara terminado.")

    def stop(self):
        print(f"INFO [{self.camera_name}]: Solicitud de detención recibida.")
        self.running = False

if __name__ == '__main__':
    # Prueba básica para CameraHandler
    print("Probando CameraHandler (esto intentará conectarse a la URL de ejemplo)...")

    # Crear un módulo de cola de alertas simulado para la prueba
    class MockAlertQueue:
        def __init__(self):
            self.alerts = []
        def add_alert(self, camera_id, camera_name, alert_details):
            timestamp = datetime.datetime.now().isoformat()
            alert = f"[{timestamp}] CAM: {camera_name} ({camera_id}) - {alert_details}"
            self.alerts.append(alert)
            print(f"MockAlertQueue: {alert}")
        def get_all_alerts_sorted(self, limit=5):
            return self.alerts[-limit:]

    mock_queue_module = MockAlertQueue()

    # URL de un stream público de prueba (puede no estar siempre activo o no tener personas)
    # Sustituir con una URL de prueba local si es posible.
    # Esta URL es de ejemplo y puede no funcionar.
    test_cam_info = {
        "id": "test_cam_001",
        "nombre": "Cámara de Prueba (Stream Público)",
        # "url": "rtsp://wowzaec2demo.streamlock.net/vod/mp4:BigBuckBunny_115k.mov" # Ejemplo RTSP
        "url": "http://pendelcam.kip.uni-heidelberg.de/mjpg/video.mjpg" # Ejemplo MJPEG stream público
    }

    # Si se quiere probar con el detector.py usando cvlib y un frame local (sin conexión real)
    # se necesitaría modificar la prueba para alimentar frames manualmente.
    # Por ahora, esta prueba se centra en la conexión y el bucle.

    handler = CameraHandler(test_cam_info, mock_queue_module, processing_interval=2)

    if not test_cam_info["url"]:
        print("Prueba no puede continuar sin una URL de ejemplo funcional.")
    else:
        handler.start()
        print("Hilo de prueba iniciado. Se ejecutará durante 15 segundos...")
        print("Observar los logs para ver intentos de conexión y procesamiento.")
        print(f"Usando MODEL_TYPE='{analyze_frame.__globals__.get('MODEL_TYPE', 'No definido en detector')}' para detección.")

        try:
            time.sleep(15) # Dejar que el hilo se ejecute por un tiempo
        except KeyboardInterrupt:
            print("Interrupción de teclado recibida.")
        finally:
            print("Deteniendo hilo de prueba...")
            handler.stop()
            handler.join(timeout=5) # Esperar a que el hilo termine
            print("Hilo de prueba detenido.")

        print("\nAlertas capturadas en la cola simulada:")
        for alert_msg in mock_queue_module.get_all_alerts_sorted():
            print(alert_msg)

    print("\nPrueba de CameraHandler finalizada.")
