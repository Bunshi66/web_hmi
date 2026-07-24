import time
import logging
import zmq
import threading
import base64
import cv2
# from camera_sdk import HikrobotCamera

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class CameraCapture:
    def __init__(self):
        self._cap = None
        self._ip = None
        self._connected = False
        self._fps = 0.0
        self._temperature = None
        self._exposure = 0
        self._gain = 0.0

    def connect(self, ip: str) -> bool:
        try:
            # 0 — дефолтная вебкамера ноутбука
            self._cap = cv2.VideoCapture(0)
            if not self._cap.isOpened():
                logger.error("Не удалось открыть веб-камеру (index 0)")
                return False

            self._connected = True
            self._ip = ip
            self._fps = self._cap.get(cv2.CAP_PROP_FPS) or 30.0
            self._temperature = 42.0  # Фейковая температура для телеметрии
            self._exposure = int(self._cap.get(cv2.CAP_PROP_EXPOSURE))
            self._gain = 1.0

            logger.info(f"Connected to local webcam (requested ip: {ip})")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to webcam: {e}")
            return False

    def disconnect(self) -> bool:
        try:
            if self._cap:
                self._cap.release()
                self._cap = None
            self._connected = False
            self._ip = None
            self._fps = 0.0
            self._temperature = None
            self._exposure = 0
            self._gain = 0.0
            return True
        except Exception as e:
            logger.error(f"Failed to disconnect: {e}")
            return False

    def get_status(self) -> dict:
        return {
            "connected": self._connected,
            "ip": self._ip if self._connected else None,
            "fps": self._fps if self._connected else 0.0,
            "temperature": self._temperature if self._connected else None,
            "exposure": self._exposure,
            "gain": self._gain
        }

    def grab_frame(self) -> dict:
        if not self._connected or self._cap is None:
            return {"image": None, "width": 0, "height": 0, "timestamp": 0}

        ret, frame = self._cap.read()
        if not ret or frame is None:
            return {"image": None, "width": 0, "height": 0, "timestamp": time.time()}

        # BGR → JPEG → base64
        _, jpeg = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
        return {
            "image": base64.b64encode(jpeg.tobytes()).decode("utf-8"),
            "width": frame.shape[1],
            "height": frame.shape[0],
            "timestamp": time.time()
        }

    def release(self) -> None:
        self.disconnect()

def main():
    camera = CameraCapture()
    context = zmq.Context()

    # REP сокет для команд
    cmd_socket = context.socket(zmq.REP)
    cmd_socket.bind("tcp://*:5555")
    logger.info("Command socket on tcp://*:5555")

    # PUB сокет для стриминга
    pub_socket = context.socket(zmq.PUB)
    pub_socket.bind("tcp://*:5556")
    logger.info("Stream socket on tcp://*:5556")

    def stream_loop():
        """Фоновый поток: шлёт кадры в PUB сокет"""
        while True:
            if camera._connected:
                frame = camera.grab_frame()
                pub_socket.send_json(frame)
            time.sleep(0.033)

    thread = threading.Thread(target=stream_loop, daemon=True)
    thread.start()

    try:
        while True:
            request = cmd_socket.recv_json()
            command = request.get("command")
            logger.info(f"Received command: {command}")

            if command == "status":
                response = camera.get_status()
            elif command == "connect":
                ip = request.get("ip", "")
                success = camera.connect(ip)
                response = {"success": success}
            elif command == "disconnect":
                success = camera.disconnect()
                response = {"success": success}
            else:
                response = {"success": False, "error": f"Unknown command: {command}"}

            cmd_socket.send_json(response)
    except KeyboardInterrupt:
        logger.info("Shutting down...")
    finally:
        camera.release()
        cmd_socket.close()
        pub_socket.close()
        context.term()
        logger.info("Capture Service stopped")


if __name__ == "__main__":
    main()