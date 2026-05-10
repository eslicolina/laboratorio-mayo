import cv2
import sqlite3
from datetime import datetime

class VisionEngine:
    """Algoritmos de procesamiento de imagenes"""

    def __init__(self):
        # 0 (Cámara por defecto. 1 ó 2 para externas)
        self.cap = cv2.VideoCapture(0)

        # 1 Cargar el calsificador (El Cerebro)
        self.face_cascade = cv2.CascadeClassifier('haarcascade_frontalface_default.xml')

        # 2 Conecta base de datos (La memoria)
        self.conn = sqlite3.connect('vision_guard.db')
        self.cursor = self.conn.cursor()
        self.cursor.execute(''' CREATE TABLE IF NOT EXISTS registros
                            (id INTEGER PRIMARY KEY AUTOINCREMENT, fecha TEXT, evento TEXT)''')
        self.conn.commit()

        if not self.cap.isOpened():
            print("Error no se pudo acceder a la cámara")
            exit()

    def registrar_evento(self):
        """Guarda la detección en la base de datos"""
        ahora = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
        self.cursor.execute("INSERT INTO registros (fecha, evento) VALUES (?, ?)", (ahora, "Rostro Detectado"))
        self.conn.commit()
        print(f"Log generado: {ahora}")

    def iniciar_transmision(self):
        print("Iniciando visión artificial... Presiona 'q' para salir.")

        # El bucle del FRAME: Aquí es donde ocurre los 33.3ms
        while True:
            # 1. INGESTA: Captura el frame actual
            ret, frame = self.cap.read()

            if not ret:
                break

            # 2. Algoritmo Espejo (Flip): Invertir horizontalmente
            frame_espejo = cv2.flip(frame, 1)

            # 3. Conversión a gris
            gris = cv2.cvtColor(frame_espejo, cv2.COLOR_BGR2GRAY)

            # 4. Filtro de suavizado (GaussianBlur)
            desenfocado = cv2.GaussianBlur(gris, (7, 7), 0)

            # Detección de rostros
            rostros = self.face_cascade.detectMultiScale(desenfocado, 1.3, 5)

            # Dibujar recuadro y registar
            for (x, y, w, h) in rostros:
                # Dibujamos sobre el frame
                cv2.rectangle(frame_espejo, (x, y), (x+w, y+h), (0,255,0), 2)
                self.registrar_evento()

            # 5. Renderizado: mostrar las ventanas
            # Ventana 1: lo que ve el humano (color)
            cv2. imshow('Vision-Guard: Original (RGB)', frame_espejo)

            # Salida Segura: Esperar 1ms y detectar si se presiona la 'q'

            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

        self.liberar_recursos()

    def liberar_recursos(self):
        """Cerrar procesos y limpiar memoria"""
        self.cap.release()
        self.conn.close() # Cerramos la conexión a la BD
        cv2.destroyAllWindows()
        print("Recursos liberados. Apagando sistema. Feliz día. :)")

# Ejecución principal
if __name__ == "__main__":
    motor = VisionEngine()
    motor.iniciar_transmision()