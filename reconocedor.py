import cv2
import sqlite3
import time
from datetime import datetime

class SmartGate:
    def __init__(self):
        self.cap = cv2.VideoCapture(0) # Inicia la cámara
        time.sleep(2.0)
        self.face_cascade = cv2.CascadeClassifier("haarcascade_frontalface_default.xml")

        # Cargar la IA entrenada
        self.reconocedor = cv2.face.LBPHFaceRecognizer_create()
        self.reconocedor.read('trainer.yml')

        # Configuración de Base de Datos
        self.conn = sqlite3.connect('smart_gate.db')
        self.cursor = self.conn.cursor()
        self.cursor.execute(''' CREATE TABLE IF NOT EXISTS accesos
                            (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT, estado TEXT, fecha TEXT)''')
        self.conn.commit()

        # Diccionario de usuarios
        self.usuarios = {1: "Esli", 2: "Prueba"}

        # Variable de control
        self.ultimo_registro = 0
        self.cooldown = 10


    def registrar_acceso(self, nombre, estado):
        ahora = datetime.now().strftime("%d-m-%Y %H:%M:%S")
        self.cursor.execute("INSERT INTO accesos (nombre, estado, fecha) VALUES (?, ?, ?)", (nombre, estado, ahora))
        self.conn.commit()
        print(f"Acceso {estado} para {nombre} registrado a las {ahora}")

    def iniciar(self):
        while True:
            ret, frame = self.cap.read()

            if not ret or frame is None:
                print("Esperando frame de la cámara")
                continue

            frame = cv2.flip(frame, 1)
            gris = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            rostros = self.face_cascade.detectMultiScale(gris, 1.3, 5)

            for (x, y, w, h) in rostros:
                roi_gris = gris[y:y+h, x:x+w]

                id_user, error = self.reconocedor.predict(roi_gris)
                
                # Lógica de decisión (Umbral de confianza)
                if error < 70:
                    nombre = self.usuarios.get(id_user, "Desconocido")
                    color = (0, 255, 0)
                    estado = "Autorizado"
                else:
                    nombre = "Desconocido"
                    color = (0, 0, 255) # ROJO
                    estado = "Intruso"

                # Lógica cooldown
                if (time.time() - self.ultimo_registro) > self.cooldown:
                    self.registrar_acceso(nombre, estado)
                    self.ultimo_registro = time.time()

                # Dibujamos en la pantalla
                cv2.rectangle(frame, (x,y), (x+w, y+h), (color), 2)
                cv2.putText(frame, f"{nombre} - {estado}", (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)    
                
            cv2. imshow('Smart-Gate: Control de acceso', frame)

            if cv2.waitKey(1) & 0xFF == ord('q'):
                    break

        self.cap.release()
        cv2.destroyAllWindows()

if __name__ == "__main__":
    gate = SmartGate()
    gate.iniciar()