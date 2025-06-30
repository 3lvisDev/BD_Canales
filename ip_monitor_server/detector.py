import cv2
import time # Para posible logging de tiempo de detección

# --- Configuración del Modelo de Detección ---
# MODEL_TYPE = "simple_motion"
MODEL_TYPE = "cvlib_yolov4_tiny" # Opción ligera por defecto para CPU
# MODEL_TYPE = "pytorch_yolov5" # Opción más pesada, requiere torch, ultralytics

# --- Inicialización de Modelos (solo se cargan si se usan) ---
DETECTION_MODEL_INSTANCE = None
PREVIOUS_FRAMES_FOR_MOTION = {} # Usado solo si MODEL_TYPE es "simple_motion"

# --- Importaciones condicionales y carga de modelos ---
if MODEL_TYPE == "cvlib_yolov4_tiny":
    try:
        import cvlib
        # No se carga el modelo aquí, cvlib.detect_common_objects lo maneja internamente
        print("INFO: detector.py configurado para usar cvlib (YOLOv4-tiny).")
    except ImportError:
        print("ERROR: cvlib no está instalado. MODEL_TYPE='cvlib_yolov4_tiny' no funcionará.")
        print("Por favor, instale cvlib, tensorflow y opencv-python, o cambie MODEL_TYPE.")
        # Podríamos cambiar MODEL_TYPE a un fallback o dejar que falle al intentar usar cvlib.
        # Por ahora, se notificará el error y fallará si se intenta usar.

elif MODEL_TYPE == "pytorch_yolov5":
    try:
        import torch
        # El modelo se cargará en la primera llamada a detect_objects_pytorch
        print("INFO: detector.py configurado para usar PyTorch (YOLOv5).")
    except ImportError:
        print("ERROR: PyTorch no está instalado. MODEL_TYPE='pytorch_yolov5' no funcionará.")
        print("Por favor, instale PyTorch y ultralytics, o cambie MODEL_TYPE.")

elif MODEL_TYPE == "simple_motion":
    print("INFO: detector.py configurado para usar Detección de Movimiento Simple.")

else:
    print(f"ADVERTENCIA: MODEL_TYPE '{MODEL_TYPE}' no reconocido. La detección no funcionará.")


def _initialize_pytorch_model():
    """Carga el modelo YOLOv5 si aún no está cargado."""
    global DETECTION_MODEL_INSTANCE
    if DETECTION_MODEL_INSTANCE is None and MODEL_TYPE == "pytorch_yolov5":
        try:
            DETECTION_MODEL_INSTANCE = torch.hub.load('ultralytics/yolov5', 'yolov5n', pretrained=True) # Usar yolov5n (nano)
            # Opcional: configurar para detectar solo personas (clase 0 en COCO)
            # DETECTION_MODEL_INSTANCE.classes = [0]
            print("INFO: Modelo YOLOv5n (PyTorch Hub) cargado exitosamente.")
        except Exception as e:
            print(f"ERROR: Al cargar modelo YOLOv5n desde PyTorch Hub: {e}")
            print("Asegúrese de tener PyTorch, ultralytics instalados y conexión a internet para la primera descarga.")
            DETECTION_MODEL_INSTANCE = "error" # Marcar como error para no reintentar
    return DETECTION_MODEL_INSTANCE if DETECTION_MODEL_INSTANCE != "error" else None

def detect_objects_pytorch(frame):
    """Detecta objetos (personas) usando YOLOv5 (PyTorch). Devuelve True si se detectan personas."""
    model = _initialize_pytorch_model()
    if not model:
        return False, [] # No hay modelo, no hay detección

    results = model(frame)
    predictions = results.pandas().xyxy[0]

    detected_people_boxes = []
    for _, row in predictions.iterrows():
        if row['name'] == 'person' and row['confidence'] > 0.4: # Filtrar por clase 'person' y confianza
            xmin, ymin, xmax, ymax = int(row['xmin']), int(row['ymin']), int(row['xmax']), int(row['ymax'])
            detected_people_boxes.append({
                "box": [xmin, ymin, xmax, ymax],
                "confidence": row['confidence']
            })

    return len(detected_people_boxes) > 0, detected_people_boxes

def detect_objects_cvlib(frame):
    """Detecta objetos (personas) usando cvlib. Devuelve True si se detectan personas."""
    try:
        # confidence=0.4 es un umbral razonable. model='yolov4-tiny' es más rápido.
        bbox, label, conf = cvlib.detect_common_objects(frame, confidence=0.4, model='yolov4-tiny', enable_gpu=False)
    except NameError: # cvlib no importado
        print("ERROR: cvlib no está disponible (NameError). No se puede realizar la detección.")
        return False, []
    except Exception as e:
        print(f"ERROR: Durante la detección con cvlib: {e}")
        return False, []

    detected_people_boxes = []
    for l, c, b in zip(label, conf, bbox):
        if l == 'person':
            detected_people_boxes.append({
                "box": [b[0], b[1], b[2], b[3]], # xmin, ymin, xmax, ymax
                "confidence": c
            })

    return len(detected_people_boxes) > 0, detected_people_boxes

def detect_simple_motion(frame, camera_id):
    """Detección de movimiento simple. Devuelve True si se detecta movimiento significativo."""
    global PREVIOUS_FRAMES_FOR_MOTION

    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (21, 21), 0)

    if camera_id not in PREVIOUS_FRAMES_FOR_MOTION:
        PREVIOUS_FRAMES_FOR_MOTION[camera_id] = gray
        return False, [] # No hay frame anterior, no hay detección de movimiento

    frame_delta = cv2.absdiff(PREVIOUS_FRAMES_FOR_MOTION[camera_id], gray)
    thresh = cv2.threshold(frame_delta, 30, 255, cv2.THRESH_BINARY)[1] # Umbral más alto para movimiento
    thresh = cv2.dilate(thresh, None, iterations=2)

    contours, _ = cv2.findContours(thresh.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    PREVIOUS_FRAMES_FOR_MOTION[camera_id] = gray # Actualizar frame anterior

    motion_found = False
    detected_motion_areas = []
    min_area = 700 # Área mínima para considerar un contorno como movimiento relevante
    for contour in contours:
        if cv2.contourArea(contour) < min_area:
            continue
        motion_found = True
        (x, y, w, h) = cv2.boundingRect(contour)
        detected_motion_areas.append({"box": [x, y, x + w, y + h]}) # Aunque no es "persona", damos un box
        # No es necesario dibujar aquí, ya que no hay GUI.

    return motion_found, detected_motion_areas

def analyze_frame(frame, camera_id):
    """
    Función principal para analizar un frame y detectar personas o movimiento.
    No dibuja en el frame. Devuelve un booleano (detección sí/no) y una lista de detalles de detección.
    """
    start_time = time.time()
    detection_made = False
    detection_details = [] # Lista de dicts, cada dict representa una detección

    if MODEL_TYPE == "cvlib_yolov4_tiny":
        detection_made, detection_details = detect_objects_cvlib(frame)
    elif MODEL_TYPE == "pytorch_yolov5":
        detection_made, detection_details = detect_objects_pytorch(frame)
    elif MODEL_TYPE == "simple_motion":
        detection_made, detection_details = detect_simple_motion(frame, camera_id)
    else:
        # No hacer nada si el modelo no es reconocido
        pass

    end_time = time.time()
    # print(f"DEBUG: Detección en {camera_id} tomó {end_time - start_time:.4f}s. Detección: {detection_made}")

    return detection_made, detection_details


if __name__ == '__main__':
    print("Ejecutando prueba de detector.py (sin GUI)...")

    # Crear un frame de prueba
    test_frame = cv2.UMat(480, 640, cv2.CV_8UC3)
    test_frame.setTo(cv2.Scalar(100, 100, 100)) # Gris
    cv2.circle(test_frame, (320, 240), 50, (0, 0, 255), -1) # Círculo rojo
    frame_np = test_frame.get()

    test_camera_id = "test_cam_01"

    print(f"\nUsando MODEL_TYPE = {MODEL_TYPE}")

    if MODEL_TYPE == "simple_motion":
        # Para probar movimiento, necesitamos dos frames
        print("Probando detección de movimiento...")
        detected, details = analyze_frame(frame_np, test_camera_id)
        print(f"Intento 1 (sin frame previo): Detectado={detected}, Detalles={details}")

        # Modificar frame para el segundo intento
        cv2.circle(frame_np, (350, 260), 60, (0, 255, 0), -1) # Nuevo círculo verde
        detected, details = analyze_frame(frame_np, test_camera_id)
        print(f"Intento 2 (con frame previo): Detectado={detected}, Detalles={details}")

    elif MODEL_TYPE == "cvlib_yolov4_tiny":
        print("Probando detección con cvlib (YOLOv4-tiny)...")
        print("NOTA: Esto puede tardar si es la primera vez (descarga de modelo).")
        print("      Asegúrese de que cvlib y tensorflow estén instalados.")
        # Para una prueba real, necesitaría una imagen con una persona.
        # Este frame dummy probablemente no detecte nada.
        detected, details = analyze_frame(frame_np, test_camera_id)
        print(f"cvlib: Detectado={detected}, Detalles={details}")
        if not detected and not details:
             print("INFO: No se detectaron personas. Esto es esperado con un frame de prueba simple.")
             print("      Para una prueba real, use una imagen/video con personas.")


    elif MODEL_TYPE == "pytorch_yolov5":
        print("Probando detección con PyTorch (YOLOv5n)...")
        print("NOTA: Esto puede tardar si es la primera vez (descarga de modelo).")
        print("      Asegúrese de que torch y ultralytics estén instalados.")
        detected, details = analyze_frame(frame_np, test_camera_id)
        print(f"PyTorch/YOLOv5n: Detectado={detected}, Detalles={details}")
        if not detected and not details:
             print("INFO: No se detectaron personas. Esto es esperado con un frame de prueba simple.")
             print("      Para una prueba real, use una imagen/video con personas.")
    else:
        print(f"MODEL_TYPE '{MODEL_TYPE}' no tiene una rutina de prueba específica aquí.")

    print("\nPrueba de detector.py finalizada.")
