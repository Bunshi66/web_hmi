from abc import ABC, abstractmethod
from pydantic import BaseModel
from typing import Optional, Generator
import base64
import zmq
import cv2
import numpy as np
import json
import time

# Это контракт — что бы ни произошло, ответ всегда такой
class CameraStatus(BaseModel):
    connected: bool
    ip: Optional[str] = None
    fps: float = 0.0
    temperature: Optional[float] = None
    exposure: int = 0
    gain: float = 0.0


# Абстракция: любой сервис камеры должен уметь это
class CameraService(ABC):
    @abstractmethod
    def get_status(self) -> CameraStatus:
        """Получить текущий статус камеры"""
        ...

    @abstractmethod
    def connect(self, ip: str) -> bool:
        """Подключиться к камере по IP"""
        ...

    @abstractmethod
    def disconnect(self) -> bool:
        """Отключиться от камеры"""
        ...

    @abstractmethod
    def stream(self) -> Generator[bytes, None, None]:
        """Бесконечный генератор JPEG-кадров."""
        ...

class MockCamera(CameraService):
    """Заглушка для тестов и демо — не требует реальной камеры"""

    def __init__(self, connected: bool = False, ip: str = "192.168.1.100",
                 fps: float = 30.0, temperature: float = 42.0):
        self._connected = connected
        self._ip = ip
        self._fps = fps
        self._temperature = temperature

    def get_status(self) -> CameraStatus:
        return CameraStatus(
            connected=self._connected,
            ip=self._ip if self._connected else None,
            fps=self._fps if self._connected else 0.0,
            temperature=self._temperature if self._connected else None,
            exposure=5000,
            gain=1.0
        )

    def connect(self, ip: str) -> bool:
        self._connected = True
        self._ip = ip
        return True

    def disconnect(self) -> bool:
        self._connected = False
        return True

    def stream(self) -> Generator[bytes, None, None]:
        import cv2
        import numpy as np

        frame_id = 0
        while True:
            hue = (frame_id * 10) % 180
            img = np.zeros((480, 640, 3), dtype=np.uint8)
            img[:, :] = (hue, 200, 200)
            img = cv2.cvtColor(img, cv2.COLOR_HSV2BGR)

            cv2.putText(img, f"Mock Stream | Frame {frame_id}", (30, 240),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)

            _, jpeg = cv2.imencode('.jpg', img, [cv2.IMWRITE_JPEG_QUALITY, 80])
            frame_data = jpeg.tobytes()

            # MJPEG multipart формат
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_data + b'\r\n')

            frame_id += 1
            time.sleep(0.033)

class ZmqCamera(CameraService):
    """Общается с Capture Service через ZeroMQ REQ/REP"""

    def __init__(self, zmq_address: str = "tcp://localhost:5555"):
        self._cmd_address = zmq_address  # порт 5555
        self._stream_address = zmq_address.replace("5555", "5556")  # порт 5556
        self._context = zmq.Context()
        self._cmd_socket = None
        self._stream_socket = None
        self._connect_sockets()

    def _connect_sockets(self):
        self._cmd_socket = self._context.socket(zmq.REQ)
        self._cmd_socket.connect(self._cmd_address)
        self._cmd_socket.setsockopt(zmq.RCVTIMEO, 1000)
        self._cmd_socket.setsockopt(zmq.SNDTIMEO, 1000)

        # SUB сокет для стриминга
        self._stream_socket = self._context.socket(zmq.SUB)
        self._stream_socket.connect(self._stream_address)
        self._stream_socket.setsockopt_string(zmq.SUBSCRIBE, "")  # подписываемся на всё
        self._stream_socket.setsockopt(zmq.RCVTIMEO, 1000)

    def _send_command(self, command: str, **params) -> dict:
        """Отправить команду через cmd-сокет"""
        request = {"command": command, **params}
        self._cmd_socket.send_json(request)
        return self._cmd_socket.recv_json()

    def get_status(self) -> CameraStatus:
        try:
            data = self._send_command("status")
            return CameraStatus(**data)
        except zmq.Again:
            return CameraStatus(connected=False)

    def connect(self, ip: str) -> bool:
        try:
            response = self._send_command("connect", ip=ip)
            return response.get("success", False)
        except zmq.Again:
            return False

    def disconnect(self) -> bool:
        try:
            response = self._send_command("disconnect")
            return response.get("success", False)
        except zmq.Again:
            return False

    def stream(self) -> Generator[bytes, None, None]:
        while True:
            try:
                data = self._stream_socket.recv_json()
                if data.get("image") is not None:
                    img_bytes = base64.b64decode(data["image"])
                    if isinstance(img_bytes, str):
                        img_bytes = img_bytes.encode()
                    yield (b'--frame\r\n'
                           b'Content-Type: image/jpeg\r\n\r\n' + img_bytes + b'\r\n')
            except zmq.Again:
                pass
            time.sleep(0.033)

    def close(self):
        if self._cmd_socket:
            self._cmd_socket.close()
        if self._stream_socket:
            self._stream_socket.close()
        self._context.term()