import cv2
import os
import time
import glob


class SmartGate:
    def __init__(self, cascade_path='haarcascade_frontalface_default.xml',
                 trainer_path='trainer.yml',
                 data_dir='data',
                 umbral_confianza=70.0,
                 cooldown_segundos=5):
        self.face_cascade = cv2.CascadeClassifier(cascade_path)
        self.reconocedor = cv2.face.LBPHFaceRecognizer_create()
        self.reconocedor.read(trainer_path)
        self.umbral = umbral_confianza
        self.cooldown = cooldown_segundos
        self.usuarios = self._cargar_usuarios(data_dir)
        self._ultimo_evento = {}

    def _cargar_usuarios(self, data_dir):
        conocidos = {1: "Esli", 2: "Prueba"}
        for path in glob.glob(os.path.join(data_dir, 'User.*.*.jpg')):
            basename = os.path.basename(path)
            partes = basename.split('.')
            raw_id = partes[1]
            try:
                uid = int(raw_id)
            except ValueError:
                continue
            if uid not in conocidos:
                conocidos[uid] = f"Usuario_{uid:03d}"
        return conocidos

    def en_cooldown(self, persona_id):
        ultimo = self._ultimo_evento.get(persona_id, 0)
        return (time.time() - ultimo) < self.cooldown

    def registrar_cooldown(self, persona_id):
        self._ultimo_evento[persona_id] = time.time()

    def procesar(self, frame):
        gris = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        rostros = self.face_cascade.detectMultiScale(gris, 1.3, 5)
        resultados = []

        for (x, y, w, h) in rostros:
            roi = gris[y:y+h, x:x+w]
            id_user, distancia = self.reconocedor.predict(roi)
            confianza = max(0, min(100, 100 - distancia))

            if distancia < self.umbral:
                persona_id = self.usuarios.get(id_user, "Desconocido")
                decision = 'ACCESO_PERMITIDO'
            else:
                persona_id = 'DESCONOCIDO'
                decision = 'ACCESO_DENEGADO'

            en_cd = self.en_cooldown(persona_id)
            if not en_cd:
                self.registrar_cooldown(persona_id)

            resultados.append({
                'persona_id': persona_id,
                'confianza': confianza,
                'decision': decision,
                'cooldown_activo': int(en_cd),
                'anomalia': 0,
                'bbox': (x, y, w, h)
            })

            if decision == 'ACCESO_PERMITIDO':
                color = (0, 255, 0)
            elif decision == 'ACCESO_DENEGADO':
                color = (0, 0, 255)
            else:
                color = (0, 165, 255)

            cv2.rectangle(frame, (x, y), (x + w, y + h), color, 2)
            cv2.putText(frame, f"{persona_id} ({int(confianza)}%)",
                        (x, y - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
            cv2.putText(frame, decision,
                        (x, y - 28), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)

        return frame, resultados
