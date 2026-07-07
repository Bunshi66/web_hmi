from abc import ABC, abstractmethod
from pydantic import BaseModel
from typing import Optional

import zmq
import json

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