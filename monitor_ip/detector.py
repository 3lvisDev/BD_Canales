# Detección de personas/movimiento
import cv2
# import cvlib as cv # Descomentar cuando se vaya a usar cvlib
# import torch # Descomentar cuando se vaya a usar PyTorch (YOLOv5)

# Variable para cargar el modelo (ej. YOLOv5) una sola vez.
# Se inicializará en la primera llamada a detect_people si se usa un modelo global.
PERSON_DETECTION_MODEL = None

def initialize_model_pytorch():
    """
    Inicializa y devuelve el modelo YOLOv5 desde PyTorch Hub.
    Esta función es un placeholder y necesitará que el usuario tenga PyTorch y ultralytics instalados.
    """
    global PERSON_DETECTION_MODEL
    if PERSON_DETECTION_MODEL is None:
        try:
            # El usuario debe asegurarse de que 'ultralytics/yolov5' y 'yolov5s' (o 'yolov5n')
            # estén disponibles y que torch esté instalado.
            PERSON_DETECTION_MODEL = torch.hub.load('ultralytics/yolov5', 'yolov5s', pretrained=True)
            # Para un modelo más ligero: torch.hub.load('ultralytics/yolov5', 'yolov5n', pretrained=True)
            print("Modelo YOLOv5 (PyTorch Hub) cargado exitosamente.")
            # Configurar para detectar solo personas si es posible y necesario
            # model.classes = [0] # El índice 0 es 'person' en COCO
        except Exception as e:
            print(f"Error al cargar el modelo YOLOv5 desde PyTorch Hub: {e}")
            print("Asegúrese de tener PyTorch, ultralytics instalados y conexión a internet para la primera descarga.")
            PERSON_DETECTION_MODEL = None # Fallback
    return PERSON_DETECTION_MODEL

def initialize_model_cvlib():
    """
    Placeholder para inicializar cualquier cosa necesaria para cvlib si fuera más complejo
    que una simple llamada. Por ahora, cvlib.detect_common_objects no requiere
    inicialización explícita de un modelo global de esta manera.
    """
    # cvlib carga modelos internamente al llamar a detect_common_objects.
    # Esta función es más relevante si se usara un modelo DNN de OpenCV directamente.
    # print("cvlib no requiere inicialización de modelo global separada para detect_common_objects.")
    return True


# Elegir el tipo de modelo a utilizar (cambiar según preferencia)
# MODEL_TYPE = "pytorch_yolov5"  # Requiere: torch, torchvision, ultralytics
MODEL_TYPE = "cvlib_yolov4_tiny" # Opción más ligera para CPU. Requiere: cvlib, tensorflow, opencv-python
# MODEL_TYPE = "simple_motion" # Para la detección de movimiento básica. Requiere: opencv-python

# Importaciones condicionales para evitar errores si no todas las libs están instaladas por el usuario
if MODEL_TYPE == "pytorch_yolov5":
    try:
        import torch
    except ImportError:
        print("ADVERTENCIA: PyTorch no está instalado. MODEL_TYPE='pytorch_yolov5' no funcionará.")
        print("Por favor, instale PyTorch y ultralytics, o cambie MODEL_TYPE en detector.py.")
        # Podríamos cambiar MODEL_TYPE a un fallback aquí, o dejar que falle en la detección.
        # Por ahora, se dejará que falle en `initialize_model_pytorch` si no está.
elif MODEL_TYPE == "cvlib_yolov4_tiny":
    try:
        import cvlib as cv
    except ImportError:
        print("ADVERTENCIA: cvlib no está instalado. MODEL_TYPE='cvlib_yolov4_tiny' no funcionará.")
        print("Por favor, instale cvlib, tensorflow y opencv-python, o cambie MODEL_TYPE en detector.py.")


def detect_people_pytorch(frame, camera_id):
    """
    Detecta personas en un frame usando YOLOv5 (PyTorch).
    El usuario debe tener PyTorch y ultralytics instalados.
    """
    model = initialize_model_pytorch()
    if model is None:
        # Fallback a un frame sin detección si el modelo no carga
        return False, frame

    # Realizar inferencia
    results = model(frame)

    people_detected_count = 0
    # Procesar resultados
    # results.xyxy[0] contiene las detecciones para la primera (y única) imagen
    predictions = results.pandas().xyxy[0]
    people_boxes = []

    for index, row in predictions.iterrows():
        if row['name'] == 'person': # Filtrar solo la clase 'person'
            people_detected_count += 1
            xmin, ymin, xmax, ymax = int(row['xmin']), int(row['ymin']), int(row['xmax']), int(row['ymax'])
            confidence = row['confidence']
            people_boxes.append((xmin, ymin, xmax, ymax, confidence))

            # Dibujar bounding box y etiqueta
            label = f"Persona: {confidence:.2f}"
            cv2.rectangle(frame, (xmin, ymin), (xmax, ymax), (0, 255, 0), 2)
            cv2.putText(frame, label, (xmin, ymin - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

    return people_detected_count > 0, frame

def detect_people_cvlib(frame, camera_id):
    """
    Detecta personas en un frame usando cvlib (YOLOv4-tiny por defecto aquí).
    El usuario debe tener cvlib, tensorflow y opencv-python instalados.
    """
    # Usar yolov4-tiny para un rendimiento más rápido en CPU
    # El usuario debe asegurarse de que cvlib esté instalado.
    try:
        bbox, label, conf = cv.detect_common_objects(frame, confidence=0.4, model='yolov4-tiny', enable_gpu=False)
    except Exception as e:
        print(f"Error durante la detección con cvlib: {e}")
        print("Asegúrese de que cvlib, tensorflow y opencv-python estén instalados correctamente.")
        print("Si es la primera vez, cvlib podría estar descargando los pesos del modelo.")
        # Fallback a un frame sin detección si cvlib falla
        return False, frame

    people_detected_count = 0

    # Dibujar bounding box para personas detectadas
    for l, c, b in zip(label, conf, bbox):
        if l == 'person':
            people_detected_count += 1
            xmin, ymin, xmax, ymax = b[0], b[1], b[2], b[3]
            cv2.rectangle(frame, (xmin, ymin), (xmax, ymax), (0, 255, 0), 2)
            text = f"{l}: {c:.2f}"
            cv2.putText(frame, text, (xmin, ymin - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

    return people_detected_count > 0, frame

def detect_motion_simple(frame, camera_id, prev_frame_dict):
    """
    Detección de movimiento simple por diferencia de frames.
    Mantiene un frame anterior por cada `camera_id`.
    """
    # Convertir a escala de grises y aplicar blur
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (21, 21), 0)

    # Si es el primer frame para esta cámara, almacenarlo y retornar
    if camera_id not in prev_frame_dict:
        prev_frame_dict[camera_id] = gray
        return False, frame

    frame_delta = cv2.absdiff(prev_frame_dict[camera_id], gray)
    thresh = cv2.threshold(frame_delta, 25, 255, cv2.THRESH_BINARY)[1]

    # Dilatar la imagen umbralizada para llenar agujeros, luego encontrar contornos
    thresh = cv2.dilate(thresh, None, iterations=2)
    contours, _ = cv2.findContours(thresh.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    motion_detected = False
    min_area = 500 # Área mínima para considerar un contorno como movimiento

    for contour in contours:
        if cv2.contourArea(contour) < min_area:
            continue

        (x, y, w, h) = cv2.boundingRect(contour)
        cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 0, 255), 2)
        cv2.putText(frame, "Movimiento", (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
        motion_detected = True

    prev_frame_dict[camera_id] = gray # Actualizar el frame anterior
    return motion_detected, frame


# Diccionario para almacenar frames anteriores para detect_motion_simple
# La clave será camera_id
previous_frames = {}

def detect_people(frame, camera_id="cam"):
    """
    Función principal para detectar personas. Llama al método específico según MODEL_TYPE.
    """
    if MODEL_TYPE == "pytorch_yolov5":
        # El usuario debe tener PyTorch y ultralytics instalados
        # Esta es una dependencia pesada si no hay espacio/GPU.
        # print("Usando PyTorch YOLOv5 para detección.")
        return detect_people_pytorch(frame, camera_id)
    elif MODEL_TYPE == "cvlib_yolov4_tiny":
        # El usuario debe tener cvlib, TensorFlow y OpenCV instalados.
        # print("Usando cvlib (YOLOv4-tiny) para detección.")
        return detect_people_cvlib(frame, camera_id)
    elif MODEL_TYPE == "simple_motion":
        # print("Usando detección de movimiento simple.")
        return detect_motion_simple(frame, camera_id, previous_frames)
    else:
        print(f"Tipo de modelo de detección desconocido: {MODEL_TYPE}. No se realizará detección.")
        return False, frame


if __name__ == '__main__':
    # Este bloque es para pruebas directas del detector.py
    # El usuario necesitará tener OpenCV instalado para ejecutar esto.
    print("Ejecutando prueba de detector.py...")

    # Simular un frame (imagen negra)
    dummy_frame = cv2.UMat(600, 800, cv2.CV_8UC3) # Usar UMat para posible aceleración
    dummy_frame.setTo(0) # Frame negro

    # Crear un frame con algo de contenido para probar mejor
    cv2.circle(dummy_frame, (400,300), 50, (0,255,0), -1)
    cv2.putText(dummy_frame, "Prueba Detector", (50,50), cv2.FONT_HERSHEY_SIMPLEX, 1, (255,255,255), 2)

    frame_for_detection = dummy_frame.get() # Convertir UMat a Mat (numpy array) para los modelos

    print(f"Probando con MODEL_TYPE = {MODEL_TYPE}")

    if MODEL_TYPE == "pytorch_yolov5":
        print("Nota: La prueba de PyTorch YOLOv5 requiere que el usuario tenga PyTorch y ultralytics instalados.")
        print("Si es la primera vez, el modelo se descargará (requiere internet).")
        # Para probar YOLOv5, necesitarías una imagen con personas.
        # Podrías cargar una imagen de prueba aquí en lugar del dummy_frame si lo deseas.
        # Ejemplo: test_image = cv2.imread("path/to/test_image_with_people.jpg")
        # if test_image is not None:
        #     detected, result_frame = detect_people(test_image, "test_cam_pytorch")
        # else:
        #     print("Imagen de prueba no encontrada, usando frame dummy (probablemente no detecte nada).")
        #     detected, result_frame = detect_people(frame_for_detection, "test_cam_pytorch")
        detected, result_frame = detect_people(frame_for_detection, "test_cam_pytorch")


    elif MODEL_TYPE == "cvlib_yolov4_tiny":
        print("Nota: La prueba de cvlib requiere que el usuario tenga cvlib, TensorFlow y OpenCV instalados.")
        print("Si es la primera vez con YOLOv4-tiny, cvlib descargará los pesos del modelo (requiere internet).")
        # Al igual que con YOLOv5, una imagen real sería mejor para la prueba.
        detected, result_frame = detect_people(frame_for_detection, "test_cam_cvlib")

    elif MODEL_TYPE == "simple_motion":
        print("Probando detección de movimiento simple:")
        # Para probar motion, necesitamos simular dos frames diferentes
        prev_frame_sim = cv2.cvtColor(frame_for_detection, cv2.COLOR_BGR2GRAY)
        prev_frame_sim = cv2.GaussianBlur(prev_frame_sim, (21, 21), 0)
        previous_frames["test_motion_cam"] = prev_frame_sim

        # Crear un segundo frame ligeramente diferente
        frame_for_motion_2 = frame_for_detection.copy()
        cv2.circle(frame_for_motion_2, (450,350), 60, (0,0,255), -1) # Algo diferente

        detected, result_frame = detect_people(frame_for_motion_2, "test_motion_cam")
        print(f"Detección de movimiento simple: {detected}")
        # Una segunda llamada para ver si se actualiza el frame anterior
        frame_for_motion_3 = frame_for_motion_2.copy()
        cv2.rectangle(frame_for_motion_3, (100,100), (200,200), (255,0,0), 5)
        detected_again, result_frame_2 = detect_people(frame_for_motion_3, "test_motion_cam")
        print(f"Detección de movimiento (segunda vez): {detected_again}")
        result_frame = result_frame_2 # Mostrar el último

    else:
        print(f"MODEL_TYPE '{MODEL_TYPE}' no tiene una prueba específica implementada aquí.")
        detected = False
        result_frame = frame_for_detection

    if detected:
        print("¡Detección(es) realizada(s) en el frame de prueba!")
    else:
        print("No se detectó nada (o el modelo/prueba no fue concluyente con el frame dummy/simple).")

    # El usuario necesitará tener una GUI para ver esto si no está en un entorno como Colab.
    # cv2.imshow("Prueba Detector", result_frame)
    # print("Ventana de prueba del detector. Presiona cualquier tecla para cerrar.")
    # cv2.waitKey(0)
    # cv2.destroyAllWindows()
    print("Prueba de detector.py finalizada. Si se usó un modelo real, revise la salida.")
    print("Para ver la imagen resultante, el usuario debe descomentar las líneas de cv2.imshow/waitKey/destroyAllWindows.")
