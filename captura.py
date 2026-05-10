import cv2
import os

face_cascade = cv2.CascadeClassifier("haarcascade_frontalface_default.xml")
cap = cv2.VideoCapture(0)

user_id = input("Ingrese ID númerico: ")
count = 0

while True:
    ret, frame = cap.read()
    frame = cv2.flip(frame, 1)
    gris = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    rostros = face_cascade.detectMultiScale(gris, 1.3, 5)

    for (x, y, w, h) in rostros:
        count += 1
        # Guardamos el recorte en la carpeta data
        cv2.imwrite(f"data/User.{user_id}.{count}.jpg", gris[y:y+h, x:x+w])
        cv2.rectangle(frame, (x,y), (x+w, y+h), (0,255,0), 2)

    cv2.imshow('Capturando Rostro', frame)

    if cv2.waitKey(1) & 0xFF == ord('q') or count >= 50:
        break

cap.release()
cv2.destroyAllWindows()