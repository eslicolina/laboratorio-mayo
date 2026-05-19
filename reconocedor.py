import cv2
import sqlite3
import time
from datetime import datetime
from flask import Flask, render_template, Response, jsonify

app = Flask(__name__)

class SmartGateWeb:
    def __init__(self):
        # Inicialización de la cámara (0 suele ser la integrada)
        self.cap = cv2.VideoCapture(0)
        time.sleep(2.0)
        
        # Clasificadores e IA entrenada
        self.face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
        self.reconocedor = cv2.face.LBPHFaceRecognizer_create()
        self.reconocedor.read('trainer.yml')

        # Diccionario de usuarios autorizados
        self.usuarios = {1: "Esli", 2: "Prueba"}
        
        # Variables de control de estado y simulaciones de red
        self.ultimo_registro = 0
        self.cooldown = 10
        self.db_name = 'smart_gate.db'
        self.ubicacion_actual = "Laboratorio Central"  # Ubicación asignada a este nodo/cámara

        self.inicializar_db()

    def inicializar_db(self):
        """Crea la tabla bajo los nuevos requerimientos de ciberseguridad."""
        with sqlite3.connect(self.db_name) as conn:
            cursor = conn.cursor()
            cursor.execute(''' 
                CREATE TABLE IF NOT EXISTS eventos_acceso (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, 
                    usuario TEXT, 
                    ubicacion TEXT, 
                    score_confianza REAL, 
                    estado TEXT, 
                    timestamp REAL, 
                    fecha TEXT
                )
            ''')
            conn.commit()

    def evaluar_anomalia_temporal(self, usuario):
        """
        Analiza si el usuario cambió de ubicación en un lapso menor a 15 segundos.
        Retorna 'Anomalía: Viaje Imposible' si se viola la restricción, de lo contrario 'Normal'.
        """
        with sqlite3.connect(self.db_name) as conn:
            cursor = conn.cursor()
            # Buscamos el último registro exitoso o previo de este usuario específico
            cursor.execute('''
                SELECT ubicacion, timestamp FROM eventos_acceso 
                WHERE usuario = ? 
                ORDER BY id DESC LIMIT 1
            ''', (usuario,))
            resultado = cursor.fetchone()

        if resultado:
            ultima_ubicacion, ultimo_timestamp = resultado
            tiempo_transcurrido = time.time() - ultimo_timestamp
            
            # Alerta si cambió de nodo/puerta en menos de 15 segundos
            if ultima_ubicacion != self.ubicacion_actual and tiempo_transcurrido < 15:
                return "Anomalía: Viaje Imposible"
                
        return "Normal"

    def registrar_evento(self, usuario, score, estado):
        """Inserta el log de auditoría en la base de datos."""
        ahora = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
        ts = time.time()
        
        with sqlite3.connect(self.db_name) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO eventos_acceso (usuario, ubicacion, score_confianza, estado, timestamp, fecha) 
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (usuario, self.ubicacion_actual, round(score, 2), estado, ts, ahora))
            conn.commit()
        print(f"[{estado}] - Registro generado para {usuario} en {self.ubicacion_actual}")

    def generar_frames(self):
        """Generador de streaming MJPEG optimizado para Flask."""
        while True:
            ret, frame = self.cap.read()
            if not ret or frame is None:
                continue

            frame = cv2.flip(frame, 1)
            gris = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            rostros = self.face_cascade.detectMultiScale(gris, 1.3, 5)

            for (x, y, w, h) in rostros:
                roi_gris = gris[y:y+h, x:x+w]
                id_user, distancia = self.reconocedor.predict(roi_gris)
                
                # El score de confianza en LBPH se mide en distancia (a menor distancia, mayor certeza)
                # Mapeamos una métrica porcentual legible para el dashboard basada en la distancia obtenida
                porcentaje_confianza = max(0, min(100, 100 - distancia))

                if distancia < 70:
                    nombre = self.usuarios.get(id_user, "Desconocido")
                    
                    # Ejecutar validación espacio-temporal
                    estado = self.evaluar_anomalia_temporal(nombre)
                    
                    if estado.startswith("Anomalía"):
                        color = (0, 165, 255)  # Naranja para anomalías de sistema
                    else:
                        color = (0, 255, 0)    # Verde para accesos normales
                else:
                    nombre = "Desconocido"
                    estado = "Intruso"
                    color = (0, 0, 255)        # Rojo para intrusiones críticas

                # Lógica de Cooldown para evitar inundación (Spam) de la base de datos
                if (time.time() - self.ultimo_registro) > self.cooldown:
                    self.registrar_evento(nombre, porcentaje_confianza, estado)
                    self.ultimo_registro = time.time()

                # Dibujado del HUD de Ciberseguridad sobre el Frame de video
                cv2.rectangle(frame, (x, y), (x + w, y + h), color, 2)
                cv2.putText(frame, f"{nombre} ({int(porcentaje_confianza)}%)", (x, y - 28), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
                cv2.putText(frame, estado, (x, y - 8), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)

            # Codificación del frame a formato JPEG para transmisión HTTP
            ret, buffer = cv2.imencode('.jpg', frame)
            if not ret:
                continue
            
            frame_bytes = buffer.tobytes()
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

    def obtener_ultimos_logs(self):
        """Extrae los últimos 10 eventos estructurados en formato apto para JSON."""
        with sqlite3.connect(self.db_name) as conn:
            conn.row_factory = sqlite3.Row  # Permite mapear por nombres de columna
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, usuario, ubicacion, score_confianza, estado, fecha 
                FROM eventos_acceso 
                ORDER BY id DESC LIMIT 10
            ''')
            rows = cursor.fetchall()
            
        return [dict(row) for row in rows]

# Instancia global del motor de análisis de IA
gate_sistema = SmartGateWeb()

# --- RUTAS DE FLASK ---

@app.route('/')
def index():
    """Renderiza el dashboard de control perimetral."""
    return render_template('index.html')

@app.route('/video_feed')
def video_feed():
    """Ruta streaming para la etiqueta img de HTML."""
    return Response(gate_sistema.generar_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/api/logs')
def api_logs():
    """Endpoint REST de consumo rápido para el setInterval del frontend."""
    logs = gate_sistema.obtener_ultimos_logs()
    return jsonify(logs)

if __name__ == '__main__':
    # threaded=True permite atender las peticiones de la API de logs sin pausar el flujo de video
    app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)