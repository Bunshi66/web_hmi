import time
import logging
import zmq
import threading
import base64

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class CameraCapture:
    def __init__(self):
        self._ip = None
        self._connected = False
        self._fps = 0.0
        self._temperature = None
        self._exposure = 0
        self._gain = 0.0

        self._frame_counter = 0

    def connect(self, ip: str) -> bool:
        try:
            self._connected = True
            self._ip = ip
            self._fps = 30.0
            self._temperature = 0.0
            self._exposure = 5000
            self._gain = 1.0
            return True
        except Exception as e:
            logger.error(f"Failed to connect to {ip}: {e}")
            return False

    def disconnect(self) -> bool:
        try:
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

    # def grab_frame(self) -> dict:
    #     if not self._connected:
    #         return {"image": None, "width": 0, "height": 0, "timestamp": 0}
    #     import numpy as np
    #     import cv2
    #     img = np.zeros((480, 640, 3), dtype=np.uint8)
    #     cv2.putText(img, "Capture Service", (150, 240),
    #                 cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
    #     _, jpeg = cv2.imencode('.jpg', img, [cv2.IMWRITE_JPEG_QUALITY, 50])
    #     return {
    #         "image": base64.b64encode(jpeg.tobytes()).decode("utf-8"),
    #         "width": 640,
    #         "height": 480,
    #         "timestamp": time.time()
    #     }

    def grab_frame(self) -> dict:
        if not self._connected:
            return {"image": None, "width": 0, "height": 0, "timestamp": 0}
        import numpy as np
        import cv2
        img = np.zeros((480, 640, 3), dtype=np.uint8)
        cv2.putText(img, f"Capture Service | Frame {self._frame_counter}", (100, 240),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
        self._frame_counter += 1
        _, jpeg = cv2.imencode('.jpg', img, [cv2.IMWRITE_JPEG_QUALITY, 50])
        return {
            "image": base64.b64encode(jpeg.tobytes()).decode("utf-8"),
            "width": 640,
            "height": 480,
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