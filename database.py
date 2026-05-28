import sqlite3
import time
from datetime import datetime


class Database:
    def __init__(self, db_path='eventos_acceso.db', ubicacion='GATE_01'):
        self.db_path = db_path
        self.ubicacion = ubicacion
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS eventos_acceso (
                    id             INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp      REAL     NOT NULL,
                    persona_id     TEXT     NOT NULL,
                    ubicacion      TEXT     DEFAULT 'GATE_01',
                    confianza      REAL,
                    decision       TEXT     NOT NULL,
                    anomalia       INTEGER  DEFAULT 0,
                    cooldown_activo INTEGER DEFAULT 0,
                    frame_path     TEXT
                )
            ''')

    def insertar_evento(self, evento):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                INSERT INTO eventos_acceso
                    (timestamp, persona_id, ubicacion, confianza, decision,
                     anomalia, cooldown_activo, frame_path)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                evento.get('timestamp', time.time()),
                evento['persona_id'],
                evento.get('ubicacion', self.ubicacion),
                evento.get('confianza'),
                evento['decision'],
                evento.get('anomalia', 0),
                evento.get('cooldown_activo', 0),
                evento.get('frame_path')
            ))

    def obtener_ultimos(self, limite=50, ventana_minutos=60):
        desde = time.time() - (ventana_minutos * 60)
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute('''
                SELECT * FROM eventos_acceso
                WHERE timestamp > ?
                ORDER BY timestamp DESC
                LIMIT ?
            ''', (desde, limite)).fetchall()
        return [dict(r) for r in rows]

    def obtener_stats(self, ventana_minutos=60):
        desde = time.time() - (ventana_minutos * 60)
        with sqlite3.connect(self.db_path) as conn:
            total = conn.execute(
                'SELECT COUNT(*) FROM eventos_acceso WHERE timestamp > ?',
                (desde,)
            ).fetchone()[0]
            permitidos = conn.execute(
                "SELECT COUNT(*) FROM eventos_acceso WHERE timestamp > ?"
                " AND decision = 'ACCESO_PERMITIDO'",
                (desde,)
            ).fetchone()[0]
            denegados = conn.execute(
                "SELECT COUNT(*) FROM eventos_acceso WHERE timestamp > ?"
                " AND decision = 'ACCESO_DENEGADO'",
                (desde,)
            ).fetchone()[0]
            anomalias = conn.execute(
                'SELECT COUNT(*) FROM eventos_acceso WHERE timestamp > ?'
                ' AND anomalia = 1',
                (desde,)
            ).fetchone()[0]
        return {
            'total': total,
            'permitidos': permitidos,
            'denegados': denegados,
            'anomalias': anomalias,
            'ventana_minutos': ventana_minutos
        }

    def obtener_logs_frontend(self, limite=10):
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute('''
                SELECT id, persona_id, ubicacion, confianza, decision,
                       timestamp
                FROM eventos_acceso
                ORDER BY id DESC
                LIMIT ?
            ''', (limite,)).fetchall()
        return [
            {
                'id': r['id'],
                'usuario': r['persona_id'],
                'ubicacion': r['ubicacion'],
                'score_confianza': round(r['confianza'], 1) if r['confianza'] is not None else 0.0,
                'confianza': f"{round(r['confianza'], 1)}%" if r['confianza'] is not None else "0%",
                'estado': r['decision'],
                'fecha': datetime.fromtimestamp(r['timestamp']).strftime("%d-%m-%Y %H:%M:%S")
            }
            for r in rows
        ]
