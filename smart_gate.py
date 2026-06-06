import json
import os
import time
import uuid

import cv2
import sqlite3
from database import DB_PATH


class SmartGate:
    _instance = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        self.face_cascade = cv2.CascadeClassifier(
            'haarcascade_frontalface_default.xml'
        )

        self.recognizer = cv2.face.LBPHFaceRecognizer_create()
        self.recognizer.read('trainer.yml')

        self.conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.cursor = self.conn.cursor()
        self._init_db()

        self.usuarios = {1: "Héctor", 2: "Prueba"}
        self.ultimo_registro = {}
        self.cooldown_segundos = 10.0
        self.ubicacion_actual = "Puerta Principal"
        self.umbral_confianza = 70

        self.snapshots_dir = "snapshots"
        os.makedirs(self.snapshots_dir, exist_ok=True)

    def _init_db(self):
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS eventos_acceso (
                id_evento     INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp     REAL    NOT NULL,
                usuario       TEXT,
                ubicacion     TEXT,
                confianza     REAL,
                tipo_evento   TEXT    NOT NULL DEFAULT 'acceso',
                accion_tomada TEXT,
                snapshots     TEXT    DEFAULT NULL
            )
        """)
        self.cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_timestamp
            ON eventos_acceso(timestamp)
        """)
        try:
            self.cursor.execute(
                "ALTER TABLE eventos_acceso ADD COLUMN snapshots TEXT DEFAULT NULL"
            )
        except sqlite3.OperationalError:
            pass
        self.conn.commit()

    def registrar_evento(self, usuario, ubicacion, confianza,
                         tipo_evento, accion_tomada):
        ts = time.time()
        self.cursor.execute("""
            INSERT INTO eventos_acceso
                (timestamp, usuario, ubicacion, confianza,
                 tipo_evento, accion_tomada)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (ts, usuario, ubicacion, confianza,
              tipo_evento, accion_tomada))
        self.conn.commit()
        return self.cursor.lastrowid

    def detectar_anomalia(self, usuario):
        self.cursor.execute("""
            SELECT ubicacion, timestamp
            FROM eventos_acceso
            WHERE usuario = ?
            ORDER BY id_evento DESC
            LIMIT 1
        """, (usuario,))
        ultimo = self.cursor.fetchone()
        if not ultimo:
            return False
        ultima_ubicacion, ultimo_timestamp = ultimo
        if (ultima_ubicacion != self.ubicacion_actual
                and (time.time() - ultimo_timestamp) < 15):
            return True
        return False

    def tomar_snapshots(self, camera_read, event_id, num_fotos=4):
        paths = []
        ts = time.strftime("%Y%m%d_%H%M%S")

        for i in range(num_fotos):
            ret, frame_captura = camera_read()
            if not ret:
                continue
            filename = f"desconocido_{ts}_{uuid.uuid4().hex[:6]}_{i}.jpg"
            filepath = os.path.join(self.snapshots_dir, filename)
            cv2.imwrite(filepath, frame_captura)
            paths.append(filepath)

        if paths:
            self.cursor.execute(
                "UPDATE eventos_acceso SET snapshots = ? WHERE id_evento = ?",
                (json.dumps(paths), event_id)
            )
            self.conn.commit()

    def procesar(self, frame, camera_read=None):
        gris = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        rostros = self.face_cascade.detectMultiScale(
            gris, scaleFactor=1.3, minNeighbors=5
        )

        snapshots_taken = False

        for (x, y, w, h) in rostros:
            roi = gris[y:y+h, x:x+w]
            id_user, error = self.recognizer.predict(roi)
            confianza = round(100 - error, 2)

            if error < self.umbral_confianza:
                usuario = self.usuarios.get(id_user, "Desconocido")
                color = (0, 255, 0)
                tipo_evento = "acceso"
                accion_tomada = "permitido"

                if self.detectar_anomalia(usuario):
                    tipo_evento = "anomalia"
                    accion_tomada = "denegado"
                    color = (0, 0, 255)
            else:
                usuario = "Desconocido"
                tipo_evento = "desconocido"
                accion_tomada = "denegado"
                color = (0, 0, 255)
                confianza = 0.0

            ahora = time.time()
            ultimo = self.ultimo_registro.get(usuario, 0)
            if ahora - ultimo > self.cooldown_segundos:
                event_id = self.registrar_evento(
                    usuario, self.ubicacion_actual, confianza,
                    tipo_evento, accion_tomada
                )
                self.ultimo_registro[usuario] = ahora

                if tipo_evento == "desconocido" and camera_read and not snapshots_taken:
                    self.tomar_snapshots(camera_read, event_id)
                    snapshots_taken = True

            cv2.rectangle(frame, (x, y), (x + w, y + h), color, 2)
            estado_texto = {
                "acceso": "Normal",
                "anomalia": "Anomalía: Viaje Imposible",
                "desconocido": "Intruso"
            }.get(tipo_evento, tipo_evento)
            cv2.putText(
                frame, f"{usuario} | {estado_texto}",
                (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX,
                0.7, color, 2
            )

        return frame
