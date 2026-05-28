import cv2
import os
import glob
import time


def cargar_usuarios(data_dir='data'):
    conocidos = {1: "Esli", 2: "Prueba"}
    for path in glob.glob(os.path.join(data_dir, 'User.*.*.jpg')):
        partes = os.path.basename(path).split('.')
        try:
            uid = int(partes[1])
            if uid not in conocidos:
                conocidos[uid] = f"Usuario_{uid:03d}"
        except ValueError:
            continue
    return conocidos


EVIDENCIA_DIR = 'evidencia'
os.makedirs(EVIDENCIA_DIR, exist_ok=True)


def _capturar_evidencia(frame, bbox, ts):
    rutas = []
    for i in range(4):
        x, y, w, h = bbox
        cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 0, 255), 2)
        cv2.putText(frame, "INTRUSO", (x, y - 8),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
        cv2.putText(frame, f"EVIDENCIA #{i+1}/4", (x + w + 10, y + 25),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)
        nombre = f"intruso_{ts}_{i}.jpg"
        ruta = os.path.join(EVIDENCIA_DIR, nombre)
        cv2.imwrite(ruta, frame)
        rutas.append(ruta)
        time.sleep(0.05)
    return rutas


def main():
    cascade_path = 'haarcascade_frontalface_default.xml'
    trainer_path = 'trainer.yml'
    umbral = 70.0

    face_cascade = cv2.CascadeClassifier(cascade_path)
    reconocedor = cv2.face.LBPHFaceRecognizer_create()
    reconocedor.read(trainer_path)
    usuarios = cargar_usuarios()

    print("=== DIAGNÓSTICO SMARTGATE ===")
    print(f"Cascade vacío? {face_cascade.empty()}")
    print(f"Umbral LBPH: {umbral}")
    print(f"Usuarios registrados: {usuarios}")
    print(f"Evidencia se guarda en: {EVIDENCIA_DIR}/")
    print("Abriendo cámara...")

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("ERROR: No se pudo abrir la cámara.")
        return

    print("Calentando cámara (3 frames)...")
    for _ in range(3):
        cap.read()
        time.sleep(0.1)

    ancho = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    alto = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    print(f"Resolución cámara: {ancho}x{alto}")
    print("Presiona 'q' para salir.\n")

    stats = {"frames": 0, "con_rostros": 0, "evidencias": 0}
    ultima_evidencia = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            continue

        stats["frames"] += 1
        frame = cv2.flip(frame, 1)
        gris = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        ecualizado = cv2.equalizeHist(gris)

        rostros = face_cascade.detectMultiScale(ecualizado, 1.3, 5)

        if len(rostros) > 0:
            stats["con_rostros"] += 1

        info_lines = [
            f"DIAGNOSTICO - SmartGate",
            f"Umbral: {umbral} | Rostros: {len(rostros)}",
            f"Detectados: {stats['con_rostros']}/{stats['frames']} frames",
            f"Evidencias capturadas: {stats['evidencias']}"
        ]

        for (x, y, w, h) in rostros:
            roi = ecualizado[y:y+h, x:x+w]
            id_user, distancia = reconocedor.predict(roi)
            porcentaje = max(0, min(100, 100 - distancia))
            supera_umbral = distancia < umbral

            if supera_umbral:
                nombre = usuarios.get(id_user, "Desconocido")
                estado = "RECONOCIDO"
                color = (0, 255, 0)
            else:
                nombre = "---"
                estado = "NO RECONOCIDO"
                color = (0, 0, 255)

            ahora = time.time()
            es_intruso = not supera_umbral and (ahora - ultima_evidencia) > 10

            cv2.rectangle(frame, (x, y), (x + w, y + h), color, 2)

            overlay = frame.copy()
            cv2.rectangle(overlay, (x, y - 90), (x + w, y), (20, 20, 20), -1)
            cv2.addWeighted(overlay, 0.7, frame, 0.3, 0, frame)

            cv2.putText(frame, f"ID:{id_user} | Distancia:{distancia:.1f}",
                        (x, y - 75), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (200, 200, 200), 1)
            cv2.putText(frame, f"Confianza:{porcentaje:.1f}% | Umbral:{umbral}",
                        (x, y - 55), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (200, 200, 200), 1)
            cv2.putText(frame, f"{nombre} -> {estado}",
                        (x, y - 35), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
            cv2.putText(frame, f"{'DENTRO' if supera_umbral else 'FUERA'} del umbral",
                        (x, y - 15), cv2.FONT_HERSHEY_SIMPLEX, 0.45, color, 1)

            if es_intruso:
                ts = int(ahora)
                rutas = _capturar_evidencia(frame, (x, y, w, h), ts)
                if rutas:
                    stats["evidencias"] += 1
                    ultima_evidencia = ahora
                    print(f"  [!] Intruso capturado -> {len(rutas)} fotos en evidencia/")

        for i, linea in enumerate(info_lines):
            cv2.putText(frame, linea, (10, 25 + i * 22),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)

        # Mostrar histograma ecualizado en una ventana auxiliar
        cv2.imshow('Diagnostico SmartGate - LBPH', frame)

        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break
        elif key == ord('r'):
            # Reset stats
            stats = {"frames": 0, "con_rostros": 0}
            print("Estadísticas reiniciadas.")

    cap.release()
    cv2.destroyAllWindows()
    print(f"\nResumen: {stats['con_rostros']}/{stats['frames']} frames con rostros detectados.")


if __name__ == '__main__':
    main()
