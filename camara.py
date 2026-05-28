import cv2
import threading
import time


class CameraStream:
    _instance = None
    _singleton_lock = threading.Lock()

    def __new__(cls, source=0):
        if cls._instance is None:
            with cls._singleton_lock:
                if cls._instance is None:
                    instance = super().__new__(cls)
                    instance._initialized = False
                    cls._instance = instance
        return cls._instance

    def __init__(self, source=0):
        if self._initialized:
            return
        self._initialized = True
        self.source = source
        self.cap = None
        self.frame = None
        self._running = False
        self._thread = None
        self._frame_lock = threading.Lock()
        self._start_lock = threading.Lock()

    def start(self):
        with self._start_lock:
            if self._running:
                return True
            self.cap = cv2.VideoCapture(self.source)
            if not self.cap.isOpened():
                self.cap = None
                return False
            self._running = True
            self._thread = threading.Thread(target=self._capture_loop, daemon=True)
            self._thread.start()
            return True

    def _capture_loop(self):
        try:
            while self._running:
                ret, frame = self.cap.read()
                if ret:
                    with self._frame_lock:
                        self.frame = frame
                else:
                    time.sleep(0.005)
        finally:
            with self._start_lock:
                if self.cap is not None:
                    self.cap.release()
                    self.cap = None
                self._running = False

    def get_frame(self):
        with self._frame_lock:
            if self.frame is None:
                return None
            return self.frame.copy()

    def stop(self):
        self._running = False
        if self._thread is not None and self._thread.is_alive():
            self._thread.join(timeout=2)
