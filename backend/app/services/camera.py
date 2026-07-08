from abc import ABC, abstractmethod
from pydantic import BaseModel
from typing import Optional, Generator

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
        frame_id = 0
        while True:
            # Синтетический кадр с меняющимся цветом и номером
            hue = (frame_id * 10) % 180
            img = np.zeros((480, 640, 3), dtype=np.uint8)
            img[:, :] = (hue, 200, 200)
            img = cv2.cvtColor(img, cv2.COLOR_HSV2BGR)

            # Текст с информацией
            cv2.putText(img, f"Mock Stream | Frame {frame_id}", (30, 240),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
            cv2.putText(img, f"FPS: ~30", (30, 280),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1)

            _, jpeg = cv2.imencode('.jpg', img, [cv2.IMWRITE_JPEG_QUALITY, 80])
            yield jpeg.tobytes()

            frame_id += 1
            time.sleep(0.033)  # ~30 FPS

class ZmqCamera(CameraService):
    """Общается с Capture Service через ZeroMQ REQ/REP"""

    def __init__(self, zmq_address: str = "tcp://localhost:5555"):
        self._address = zmq_address
        self._context = zmq.Context()
        self._socket: zmq.Socket | None = None
        self._connect_socket()

    def _connect_socket(self):
        """Создать и подключить REQ-сокет"""
        self._socket = self._context.socket(zmq.REQ)
        self._socket.connect(self._address)
        # Таймаут 1 секунда — чтобы не виснуть, если сервер не отвечает
        self._socket.setsockopt(zmq.RCVTIMEO, 1000)
        self._socket.setsockopt(zmq.SNDTIMEO, 1000)

    def _send_command(self, command: str, **params) -> dict:
        """Отправить команду и получить ответ"""
        request = {"command": command, **params}
        self._socket.send_json(request)
        return self._socket.recv_json()

    def get_status(self) -> CameraStatus:
        try:
            data = self._send_command("status")
            return CameraStatus(**data)
        except zmq.Again:
            # Таймаут — камера не отвечает
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

    def close(self):
        """Закрыть сокет (вызывать при завершении)"""
        if self._socket:
            self._socket.close()
        self._context.term()

    def stream(self) -> Generator[bytes, None, None]:
        while True:
            try:
                data = self._send_command("grab")
                if data.get("image") is not None:
                    yield data["image"]
            except zmq.Again:
                pass
            time.sleep(0.033)