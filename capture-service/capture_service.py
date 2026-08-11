import time
import logging
import zmq
import threading
import base64
import cv2
from camera_sdk import HikrobotCamera

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class CameraCapture:
    def __init__(self):
        self._cam = HikrobotCamera()
        self._connected = False
        self._ip = None
        self._fps = 30.0
        self._exposure = 5000
        self._gain = 1.0

    def connect(self, ip: str) -> bool:
        if self._connected:
            return True
        try:
            logger.info(f"Connecting to Hikrobot camera...")
            success = self._cam.connect(ip)
            if success:
                success = self._cam.start_grabbing()
            
            self._connected = success
            self._ip = ip if success else None
            return success
        except Exception as e:
            logger.error(f"Failed to connect: {e}")
            return False

    def disconnect(self) -> bool:
        try:
            if self._connected:
                self._cam.stop_grabbing()
                self._cam.release()
                self._cam = HikrobotCamera()
                self._connected = False
                self._ip = None
            return True
        except Exception as e:
            logger.error(f"Failed to disconnect: {e}")
            return False

    def get_status(self) -> dict:
        if self._connected:
            if not self._cam.is_alive():
                print("[WARNING] Physical connection lost. Disconnecting...")
                self.disconnect()

        return {
            "connected": self._connected,
            "ip": self._ip if self._connected else None,
            "fps": self._fps if self._connected else 0.0,
            "temperature": self._cam.get_temperature() if self._connected else 0.0,
            "exposure": self._exposure,
            "gain": self._gain
        }

    def grab_frame(self) -> tuple[dict | None, bytes | None]:
        if not self._connected:
            return None, None

        frame = self._cam.get_frame(timeout_ms=1000)
        if frame is None:
            return None, None

        # BGR → JPEG
        _, jpeg = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
        
        metadata = {
            "width": frame.shape[1],
            "height": frame.shape[0],
            "timestamp": time.time(),
            "camera_temp": self._cam.get_temperature(),
            "overlay_telemetry": {
                "crosshair": {"x": frame.shape[1] // 2, "y": frame.shape[0] // 2},
                "bboxes": []
            },
            "service_telemetry": {
                "processing_time_ms": 12.5,
                "capture_engine": "Hikrobot MvCameraSDK"
            }
        }
        return metadata, jpeg.tobytes()

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
        """Фоновый поток: шлёт кадры в PUB сокет Multipart"""
        while True:
            if camera._connected:
                meta, jpeg = camera.grab_frame()
                if meta and jpeg:
                    pub_socket.send_json(meta, flags=zmq.SNDMORE)
                    pub_socket.send(jpeg)
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
            elif command == "set_settings":
                exposure = request.get("exposure")
                gain = request.get("gain")
                success = True
                if exposure is not None:
                    if camera._cam.set_exposure(exposure):
                        camera._exposure = exposure
                    else:
                        
                        success = False
                if gain is not None:
                    if camera._cam.set_gain(gain):
                        camera._gain = gain
                    else:
                        success = False
                response = {"success": success}
            elif command == "trigger_defect":
                success = camera._cam.trigger_defect()
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