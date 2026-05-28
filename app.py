import os
import time
import cv2
from flask import Flask, render_template, Response, jsonify, request
from camara import CameraStream
from smartgate import SmartGate
from database import Database

EVIDENCIA_DIR = 'evidencia'
os.makedirs(EVIDENCIA_DIR, exist_ok=True)

app = Flask(__name__)

camara = CameraStream()
smart_gate = SmartGate()
db = Database()

_intruso_activo = False


def _capturar_evidencia(bbox):
    global _intruso_activo
    if _intruso_activo:
        return []
    _intruso_activo = True

    ts = int(time.time())
    rutas = []
    try:
        for i in range(4):
            frame = camara.get_frame()
            if frame is None:
                continue
            x, y, w, h = bbox
            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 0, 255), 2)
            cv2.putText(frame, "INTRUSO", (x, y - 8),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
            nombre = f"intruso_{ts}_{i}.jpg"
            ruta = os.path.join(EVIDENCIA_DIR, nombre)
            cv2.imwrite(ruta, frame)
            rutas.append(ruta)
            time.sleep(0.05)
    finally:
        _intruso_activo = False
    return rutas


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/video_feed')
def video_feed():
    def generar():
        try:
            while True:
                frame = camara.get_frame()
                if frame is None:
                    continue
                frame, resultados = smart_gate.procesar(frame)
                for r in resultados:
                    if not r['cooldown_activo']:
                        r['timestamp'] = time.time()
                        if r['persona_id'] == 'DESCONOCIDO':
                            rutas = _capturar_evidencia(r['bbox'])
                            r['frame_path'] = ','.join(rutas) if rutas else None
                        db.insertar_evento(r)
                ret, buffer = cv2.imencode('.jpg', frame)
                if not ret:
                    continue
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' +
                       buffer.tobytes() + b'\r\n')
        except GeneratorExit:
            pass
    return Response(generar(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')


@app.route('/api/logs')
def api_logs():
    limite = request.args.get('limite', 10, type=int)
    logs = db.obtener_logs_frontend(limite=limite)
    return jsonify(logs)


@app.route('/api/eventos')
def api_eventos():
    minutos = request.args.get('minutos', 60, type=int)
    eventos = db.obtener_ultimos(ventana_minutos=minutos)
    return jsonify(eventos)


@app.route('/api/stats')
def api_stats():
    minutos = request.args.get('minutos', 60, type=int)
    stats = db.obtener_stats(ventana_minutos=minutos)
    return jsonify(stats)


@app.route('/health')
def health():
    return jsonify({'status': 'ok', 'timestamp': time.time()})


if __name__ == '__main__':
    camara.start()
    app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)
