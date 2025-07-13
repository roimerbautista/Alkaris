import cv2
import mediapipe as mp
import threading
import time
import math

class ControlGestual:
    def __init__(self, espotify):
        self.espotify = espotify  # Referencia a la clase principal para controlar Spotify
        self.mp_hands = mp.solutions.hands
        self.hands = self.mp_hands.Hands(min_detection_confidence=0.7, min_tracking_confidence=0.5)
        self.mp_draw = mp.solutions.drawing_utils
        self.mp_face_detection = mp.solutions.face_detection  # Modelo de detección de rostros
        self.face_detection = self.mp_face_detection.FaceDetection(min_detection_confidence=0.7)  # Instancia de detección de rostro

        # Diccionario de acciones por gesto
        self.gestos_acciones = {
            "mano_frente": self.espotify.pausar_reproduccion,
            "dedo_labios": self.espotify.pausar_reproduccion,  # Silenciar
            "mov_derecha": self.espotify.siguiente_cancion,
            "mov_izquierda": self.espotify.anterior_cancion,
            "es_pellizco_y_deslizamiento_arriba": self.espotify.subir_volumen,  # Subir volumen
            "es_pellizco_y_deslizamiento_abajo": self.espotify.bajar_volumen,  # Bajar volumen
            "puño_cerrado": self.espotify.reanudar_reproduccion,  # Reanudar reproducción
        }

        self.cooldown_global = 3  # Cooldown en segundos para evitar repeticiones rápidas
        self.ultimo_gesto_time = 0  # Tiempo del último gesto ejecutado
        self.gesto_actual = None  # Gesto actualmente detectado
        self.frames_gesto = 0  # Contador de frames que detectan el mismo gesto
        self.frames_requeridos = 5  # Número de frames necesarios para confirmar el gesto
        self.gesto_en_ejecucion = False  # Bandera para determinar si hay un gesto en proceso
        self.mano_ultima_pos = None  # Última posición de la mano para detectar movimiento
        self.cara_detectada = False  # Bandera para verificar si hay una cara detectada
        self.rostro_frontal = False  # Bandera para verificar si el rostro está de frente

        self.activado = False  # Bandera para controlar si el reconocimiento gestual está activo
        self.stop_event = threading.Event()  # Evento para detener el hilo

    def detectar_gestos(self, frame):
        # Reflejar la imagen horizontalmente para efecto espejo
        frame = cv2.flip(frame, 1)
        img_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        # 1. Detección de rostro y orientación
        puntos_rostro = self.detectar_rostro(frame)  # Recoge los puntos faciales

        # Solo procesar gestos si el rostro está detectado y de frente
        if not self.cara_detectada or not self.rostro_frontal:
            return frame

        # 2. Si hay rostro detectado y de frente, procesar gestos
        results = self.hands.process(img_rgb)
        if results.multi_hand_landmarks and not self.gesto_en_ejecucion:
            for hand_landmarks, handedness in zip(results.multi_hand_landmarks, results.multi_handedness):
                self.mp_draw.draw_landmarks(frame, hand_landmarks, self.mp_hands.HAND_CONNECTIONS)
                puntos_mano = [(int(p.x * frame.shape[1]), int(p.y * frame.shape[0])) for p in hand_landmarks.landmark]
                mano = handedness.classification[0].label  # 'Left' o 'Right'

                # Identificar el gesto basado en los puntos de la mano y rostro
                gesto_detectado = self.identificar_gesto(puntos_mano, mano, puntos_rostro)

                if gesto_detectado:
                    if self.verificar_gesto_consistente(gesto_detectado):
                        current_time = time.time()
                        if current_time - self.ultimo_gesto_time > self.cooldown_global:
                            print(f"Gesto detectado: {gesto_detectado}")
                            self.gesto_en_ejecucion = True  # Establecer bandera para ejecutar
                            threading.Thread(target=self.ejecutar_gesto, args=(gesto_detectado,)).start()
                            self.ultimo_gesto_time = current_time
                            self.gesto_actual = None
                            self.frames_gesto = 0
                        else:
                            print("Gesto ignorado debido al cooldown global.")
                else:
                    self.gesto_actual = None
                    self.frames_gesto = 0

        return frame

    def detectar_rostro(self, frame):
        """Detecta si un rostro está presente en el cuadro y si está de frente."""
        img_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        resultado_rostro = self.face_detection.process(img_rgb)

        puntos_rostro = {}
        if resultado_rostro.detections:
            for detection in resultado_rostro.detections:
                self.mp_draw.draw_detection(frame, detection)
                self.cara_detectada = True
                bbox = detection.location_data.relative_bounding_box
                bbox_central = bbox.xmin + bbox.width / 2

                # Si está de frente, capturamos los puntos de referencia relevantes
                if 0.4 < bbox_central < 0.6:
                    self.rostro_frontal = True
                    # Usamos el cuadro delimitador para estimar la posición de los labios y la nariz
                    puntos_rostro['labios_inferiores'] = (int(bbox.xmin * frame.shape[1]), int((bbox.ymin + bbox.height * 0.7) * frame.shape[0]))
                    puntos_rostro['nariz'] = (int((bbox.xmin + bbox.width / 2) * frame.shape[1]), int((bbox.ymin + bbox.height * 0.3) * frame.shape[0]))
                else:
                    self.rostro_frontal = False
                return puntos_rostro  # Devuelve los puntos faciales
        self.cara_detectada = False
        self.rostro_frontal = False
        return None  # Si no se detecta el rostro, devuelve None

    def verificar_gesto_consistente(self, gesto_detectado):
        """Verifica si el gesto detectado es consistente a lo largo de varios frames."""
        if gesto_detectado == self.gesto_actual:
            self.frames_gesto += 1
        else:
            self.gesto_actual = gesto_detectado
            self.frames_gesto = 1

        # Aumentar el umbral para gestos de movimiento
        if gesto_detectado in ["mov_derecha", "mov_izquierda"]:
            return self.frames_gesto >= 5  # Se requiere más consistencia para movimientos
        return self.frames_gesto >= self.frames_requeridos + 2  # Más consistencia para otros gestos

    def identificar_gesto(self, puntos_mano, mano, puntos_rostro):
        if self.es_mano_frente(puntos_mano):
            return "mano_frente"
        if puntos_rostro and self.es_dedo_labios(puntos_mano, puntos_rostro):  # Asegurarse de pasar los puntos faciales aquí
            return "dedo_labios"
        if self.es_mov_derecha(puntos_mano):
            return "mov_derecha"
        if self.es_mov_izquierda(puntos_mano):
            return "mov_izquierda"
        if self.es_pellizco_y_deslizamiento_arriba(puntos_mano):
            return "es_pellizco_y_deslizamiento_arriba"
        if self.es_pellizco_y_deslizamiento_abajo(puntos_mano):
            return "es_pellizco_y_deslizamiento_abajo"
        if self.es_puno_cerrado(puntos_mano):
            return "puño_cerrado"
        return None

    def es_mano_frente(self, puntos_mano):
        pulgar = puntos_mano[4]
        muñeca = puntos_mano[0]

        # Thresholds for open palm detection
        indices_dedos = [8, 12, 16, 20]
        umbral_abierto = 50  # The threshold to consider the hand as open

        # Check distances from each finger to the wrist
        for i in indices_dedos:
            dedo = puntos_mano[i]
            distancia = abs(dedo[1] - muñeca[1])

            if distancia < umbral_abierto:  # If any finger is too close to the wrist, it's not an open hand
                return False

        # Additional check for thumb position
        return abs(pulgar[1] - muñeca[1]) < 50

    def es_pellizco(self, puntos_mano):
        pulgar = puntos_mano[4]
        indice = puntos_mano[8]

        # Detect if the thumb and index are close enough for a pinch
        distancia = math.dist(pulgar, indice)

        # Distance threshold for pinch detection
        return distancia < 30  # Adjust this value as needed

    def es_pellizco_y_deslizamiento_arriba(self, puntos_mano):
        muñeca = puntos_mano[0]

        if self.es_pellizco(puntos_mano):
            if self.mano_ultima_pos is None:
                self.mano_ultima_pos = muñeca
                self.frames_deslizamiento_arriba = 0
                return False

            if muñeca[1] < self.mano_ultima_pos[1] - 20:
                self.frames_deslizamiento_arriba += 1

                if self.frames_deslizamiento_arriba >= 3:  # Ensure consistent detection
                    self.mano_ultima_pos = None
                    self.frames_deslizamiento_arriba = 0
                    return True
            else:
                self.frames_deslizamiento_arriba = 0

        self.mano_ultima_pos = muñeca
        return False

    def es_dedo_labios(self, puntos_mano, puntos_rostro):
        # Puntos de la mano y la cara
        indice = puntos_mano[8]  # Punto del dedo índice
        muñeca = puntos_mano[0]  # Muñeca, para medir el tamaño general de la mano
        pulgar = puntos_mano[4]  # Pulgar, para medir proximidad relativa

        # Usar puntos faciales proporcionados
        labios_inferiores = puntos_rostro['labios_inferiores']
        nariz = puntos_rostro['nariz']

        # Escalar el umbral de distancia según el tamaño de la mano (proximidad relativa)
        tamano_mano = math.dist(muñeca, indice)  # Tamaño de la mano basado en muñeca e índice
        umbral_distancia = tamano_mano * 0.4  # Ajustar según el tamaño de la mano (un 40% del tamaño)

        # Verificar que el dedo índice esté en la región correcta (cerca de los labios y no de la nariz u ojos)
        distancia_labios = math.dist(indice, labios_inferiores)
        distancia_nariz = math.dist(indice, nariz)

        # Verificar que el dedo índice esté más cerca de los labios que de la nariz
        if distancia_labios > distancia_nariz:
            return False

        # Verificar orientación del dedo: El índice debe estar más cerca de los labios que el pulgar
        if math.dist(indice, labios_inferiores) > math.dist(pulgar, labios_inferiores):
            return False

        # Verificar si el índice está lo suficientemente cerca de los labios en función del tamaño de la mano
        if distancia_labios > umbral_distancia:
            return False

        # Si todas las condiciones se cumplen, el dedo índice está en los labios
        return True

    def es_mov_derecha(self, puntos_mano):
        if self.mano_ultima_pos:
            distancia = puntos_mano[0][0] - self.mano_ultima_pos[0]
            if distancia > 100:  # Distancia suficiente para considerar movimiento
                current_time = time.time()
                tiempo_transcurrido = current_time - self.ultimo_gesto_time
                if tiempo_transcurrido > 0:
                    velocidad = distancia / tiempo_transcurrido  # Calcular velocidad
                    print(f"Movimiento a la derecha, distancia: {distancia}, velocidad: {velocidad}")
                    # Umbrales de detección: distancia mayor a 100 y velocidad mayor a 200
                    if velocidad > 200:
                        self.mano_ultima_pos = puntos_mano[0]
                        return True
        self.mano_ultima_pos = puntos_mano[0]
        return False

    def es_mov_izquierda(self, puntos_mano):
        if self.mano_ultima_pos:
            distancia = self.mano_ultima_pos[0] - puntos_mano[0][0]
            if distancia > 100:  # Distancia suficiente para considerar movimiento
                current_time = time.time()
                tiempo_transcurrido = current_time - self.ultimo_gesto_time
                if tiempo_transcurrido > 0:
                    velocidad = distancia / tiempo_transcurrido  # Calcular velocidad
                    print(f"Movimiento a la izquierda, distancia: {distancia}, velocidad: {velocidad}")
                    # Umbrales de detección: distancia mayor a 100 y velocidad mayor a 200
                    if velocidad > 200:
                        self.mano_ultima_pos = puntos_mano[0]
                        return True
        self.mano_ultima_pos = puntos_mano[0]
        return False

    def es_pellizco_y_deslizamiento_abajo(self, puntos_mano):
        muñeca = puntos_mano[0]

        if self.es_pellizco(puntos_mano):
            # Si es la primera vez que detectamos el pellizco, inicializamos la posición de la muñeca
            if self.mano_ultima_pos is None:
                self.mano_ultima_pos = muñeca
                self.frames_deslizamiento_abajo = 0  # Inicializamos contador de frames
                return False

            # Verificar si la muñeca ha bajado desde la última posición por más de un umbral (movimiento significativo)
            if muñeca[1] > self.mano_ultima_pos[1] + 20:  # Umbral ajustable para evitar pequeños movimientos
                self.frames_deslizamiento_abajo += 1  # Incrementar contador si hay movimiento hacia abajo

                # Si hemos detectado el movimiento durante varios frames consecutivos, confirmar el deslizamiento
                if self.frames_deslizamiento_abajo >= 3:  # Aseguramos consistencia en al menos 3 frames
                    self.mano_ultima_pos = None  # Reiniciar la posición después de confirmar el gesto
                    self.frames_deslizamiento_abajo = 0  # Reiniciar contador
                    return True
            else:
                self.frames_deslizamiento_abajo = 0  # Reiniciar contador si no se mantiene el movimiento

        # Actualizamos la posición de la muñeca solo si es un pellizco
        self.mano_ultima_pos = muñeca
        return False

    def es_puno_cerrado(self, puntos_mano):
        pulgar = puntos_mano[4]
        indice = puntos_mano[8]
        medio = puntos_mano[12]
        anular = puntos_mano[16]
        meñique = puntos_mano[20]
        return (pulgar[1] > indice[1] and pulgar[1] > medio[1] and pulgar[1] > anular[1]
                and pulgar[1] > meñique[1])

    def ejecutar_gesto(self, gesto_detectado):
        try:
            if gesto_detectado in self.gestos_acciones:
                self.gestos_acciones[gesto_detectado]()
            else:
                print(f"Gesto no reconocido: {gesto_detectado}")
        finally:
            self.gesto_en_ejecucion = False

    def iniciar_control(self):
        """Inicia la captura de video y el procesamiento de gestos."""
        try:
            cap = cv2.VideoCapture(1)  # Asegúrate de usar el índice correcto de tu cámara
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

            while not self.stop_event.is_set():
                if not self.activado:
                    # Si no está activado, esperar un momento y continuar
                    time.sleep(0.1)
                    continue

                ret, frame = cap.read()
                if not ret:
                    print("No se pudo leer del dispositivo de video.")
                    break

                frame = self.detectar_gestos(frame)

                cv2.imshow("Control Gestual", frame)
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    self.desactivar()
                    break

        except Exception as e:
            print(f"Error en la captura de video: {e}")
        finally:
            cap.release()
            cv2.destroyAllWindows()

    def activar(self):
        """Activa el control gestual."""
        if not self.activado:
            self.activado = True
            self.stop_event.clear()  # Asegúrate de que el evento de parada no esté activo
            print("Control gestual activado.")

            # Iniciar un nuevo hilo para el control gestual solo si no existe uno
            threading.Thread(target=self.iniciar_control, daemon=True).start()

    def desactivar(self):
        """Desactiva el control gestual."""
        if self.activado:
            self.activado = False
            self.stop_event.set()  # Activa el evento de parada para detener el hilo
            print("Control gestual desactivado.")