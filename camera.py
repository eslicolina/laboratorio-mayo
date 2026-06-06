import cv2
import threading


class CameraStream:
    _instance = None
    _singleton_lock = threading.Lock()

    def __init__(self):
        self.cap = cv2.VideoCapture(0)
        self.read_lock = threading.Lock()

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            with cls._singleton_lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def read(self):
        with self.read_lock:
            return self.cap.read()
