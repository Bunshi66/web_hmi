from abc import ABC, abstractmethod
from pydantic import BaseModel
from typing import Optional, AsyncGenerator
import base64
import zmq
import zmq.asyncio
import cv2
import numpy as np
import json
import time
import asyncio

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
    async def get_status(self) -> CameraStatus:
        """Получить текущий статус камеры"""
        ...

    @abstractmethod
    async def connect(self, ip: str) -> bool:
        """Подключиться к камере по IP"""
        ...

    @abstractmethod
    async def disconnect(self) -> bool:
        """Отключиться от камеры"""
        ...

    @abstractmethod
    async def stream(self) -> AsyncGenerator[bytes, None]:
        """Бесконечный генератор JPEG-кадров (MJPEG)."""
        ...

    @abstractmethod
    async def stream_raw(self) -> AsyncGenerator[dict, None]:
        """Бесконечный генератор словарей (кадр + телеметрия) для WebSocket."""
        ...

    @abstractmethod
    async def set_settings(self, exposure: Optional[float] = None, gain: Optional[float] = None) -> bool:
        """Применить настройки к камере"""
        ...

    @abstractmethod
    async def trigger_defect(self) -> bool:
        """Отправить аппаратный триггер дефекта"""
        ...

    @abstractmethod
    async def configure_io(self, line_name: str, output_name: str) -> bool:
        """Настроить IO вывод"""
        ...

    @abstractmethod
    async def set_io(self, state: bool, output_name: str) -> bool:
        """Включить/выключить IO вывод"""
        ...

class MockCamera(CameraService):
    """Заглушка для тестов и демо — не требует реальной камеры"""

    def __init__(self, connected: bool = False, ip: str = "192.168.1.100",
                 fps: float = 30.0, temperature: float = 42.0):
        self._connected = connected
        self._ip = ip
        self._fps = fps
        self._temperature = temperature

    async def get_status(self) -> CameraStatus:
        return CameraStatus(
            connected=self._connected,
            ip=self._ip if self._connected else None,
            fps=self._fps if self._connected else 0.0,
            temperature=self._temperature if self._connected else None,
            exposure=5000,
            gain=1.0
        )

    async def connect(self, ip: str) -> bool:
        self._connected = True
        self._ip = ip
        return True

    async def disconnect(self) -> bool:
        self._connected = False
        return True

    async def set_settings(self, exposure: Optional[float] = None, gain: Optional[float] = None) -> bool:
        return True

    async def trigger_defect(self) -> bool:
        print("[MOCK] Defect triggered!")
        return True

    async def configure_io(self, line_name: str, output_name: str) -> bool:
        print(f"[MOCK] Configured IO: {line_name} as {output_name}")
        return True

    async def set_io(self, state: bool, output_name: str) -> bool:
        print(f"[MOCK] Set IO {output_name} to {state}")
        return True

    async def stream_raw(self) -> AsyncGenerator[dict, None]:
        frame_id = 0
        while True:
            # Yield a tiny dummy JPEG to avoid cv2 deadlock in WSL docker
            dummy_jpeg = b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00H\x00H\x00\x00\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t\x08\n\x0c\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\x14\x1d\x1a\x1f\x1e\x1d\x1a\x1c\x1c $.\' ",#\x1c\x1c(7),01444\x1f\'9=82<.342\xff\xdb\x00C\x01\t\t\t\x0c\x0b\x0c\x18\r\r\x182!\x1c!22222222222222222222222222222222222222222222222222\xff\xc0\x00\x11\x08\x00\x01\x00\x01\x03\x01"\x00\x02\x11\x01\x03\x11\x01\xff\xc4\x00\x1f\x00\x00\x01\x05\x01\x01\x01\x01\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00\x01\x02\x03\x04\x05\x06\x07\x08\t\n\x0b\xff\xc4\x00\xb5\x10\x00\x02\x01\x03\x03\x02\x04\x03\x05\x05\x04\x04\x00\x00\x01}\x01\x02\x03\x00\x04\x11\x05\x12!1A\x06\x13Qa\x07"q\x142\x81\x91\xa1\x08#B\xb1\xc1\x15R\xd1\xf0$3br\x82\t\n\x16\x17\x18\x19\x1a%&\'()*456789:CDEFGHIJSTUVWXYZcdefghijstuvwxyz\x83\x84\x85\x86\x87\x88\x89\x8a\x92\x93\x94\x95\x96\x97\x98\x99\x9a\xa2\xa3\xa4\xa5\xa6\xa7\xa8\xa9\xaa\xb2\xb3\xb4\xb5\xb6\xb7\xb8\xb9\xba\xc2\xc3\xc4\xc5\xc6\xc7\xc8\xc9\xca\xd2\xd3\xd4\xd5\xd6\xd7\xd8\xd9\xda\xe1\xe2\xe3\xe4\xe5\xe6\xe7\xe8\xe9\xea\xf1\xf2\xf3\xf4\xf5\xf6\xf7\xf8\xf9\xfa\xff\xc4\x00\x1f\x01\x00\x03\x01\x01\x01\x01\x01\x01\x01\x01\x01\x00\x00\x00\x00\x00\x00\x01\x02\x03\x04\x05\x06\x07\x08\t\n\x0b\xff\xc4\x00\xb5\x11\x00\x02\x01\x02\x04\x04\x03\x04\x07\x05\x04\x04\x00\x01\x02w\x00\x01\x02\x03\x11\x04\x05!1\x06\x12AQ\x07aq\x13"2\x81\x08\x14B\x91\xa1\xb1\xc1\t#3R\xf0\x15br\xd1\n\x16$4\xe1%\xf1\x17\x18\x19\x1a&\'()*56789:CDEFGHIJSTUVWXYZcdefghijstuvwxyz\x82\x83\x84\x85\x86\x87\x88\x89\x8a\x92\x93\x94\x95\x96\x97\x98\x99\x9a\xa2\xa3\xa4\xa5\xa6\xa7\xa8\xa9\xaa\xb2\xb3\xb4\xb5\xb6\xb7\xb8\xb9\xba\xc2\xc3\xc4\xc5\xc6\xc7\xc8\xc9\xca\xd2\xd3\xd4\xd5\xd6\xd7\xd8\xd9\xda\xe2\xe3\xe4\xe5\xe6\xe7\xe8\xe9\xea\xf2\xf3\xf4\xf5\xf6\xf7\xf8\xf9\xfa\xff\xda\x00\x0c\x03\x01\x00\x02\x11\x03\x11\x00?\x00\xfd\xfc\xa8\xa2\x8a\x00\xff\xd9'
            yield {
                "image": dummy_jpeg, # Raw bytes
                "overlay_telemetry": {},
                "service_telemetry": {},
                "camera_temp": 42.0
            }

            frame_id += 1
            await asyncio.sleep(0.033)

    async def stream(self) -> AsyncGenerator[bytes, None]:
        async for frame_data in self.stream_raw():
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_data + b'\r\n')

from app.services.camera_sdk import HikrobotCamera

class RealHikrobotCamera(CameraService):
    """Directly communicates with Hikrobot Camera via SDK in the backend"""

    def __init__(self):
        self._cam = HikrobotCamera()
        self._connected = False
        self._ip = None
        self._fps = 30.0
        self._exposure = 5000
        self._gain = 1.0

    async def get_status(self) -> CameraStatus:
        if self._connected:
            is_alive = await asyncio.to_thread(self._cam.is_alive)
            if not is_alive:
                print("[WARNING] Physical connection lost. Disconnecting...")
                await self.disconnect()

        return CameraStatus(
            connected=self._connected,
            ip=self._ip if self._connected else None,
            fps=self._fps if self._connected else 0.0,
            temperature=await asyncio.to_thread(self._cam.get_temperature) if self._connected else 0.0,
            exposure=self._exposure,
            gain=self._gain
        )

    async def connect(self, ip: str) -> bool:
        if self._connected:
            return True
        try:
            success = await asyncio.to_thread(self._cam.connect, ip)
            if success:
                success = await asyncio.to_thread(self._cam.start_grabbing)
            self._connected = success
            self._ip = ip if success else None
            return success
        except Exception as e:
            print(f"[ERROR] Failed to connect: {e}")
            return False

    async def disconnect(self) -> bool:
        try:
            if self._connected:
                await asyncio.to_thread(self._cam.stop_grabbing)
                await asyncio.to_thread(self._cam.release)
                self._cam = HikrobotCamera()
                self._connected = False
                self._ip = None
            return True
        except Exception as e:
            print(f"[ERROR] Failed to disconnect: {e}")
            return False

    async def set_settings(self, exposure: Optional[float] = None, gain: Optional[float] = None) -> bool:
        success = True
        if exposure is not None:
            if await asyncio.to_thread(self._cam.set_exposure, exposure):
                self._exposure = exposure
            else:
                success = False
        if gain is not None:
            if await asyncio.to_thread(self._cam.set_gain, gain):
                self._gain = gain
            else:
                success = False
        return success

    async def trigger_defect(self) -> bool:
        return await asyncio.to_thread(self._cam.trigger_defect)

    async def configure_io(self, line_name: str, output_name: str) -> bool:
        return await asyncio.to_thread(self._cam.configure_io_output, line_name, output_name)

    async def set_io(self, state: bool, output_name: str) -> bool:
        return await asyncio.to_thread(self._cam.set_io_value, state, output_name)

    async def stream_raw(self) -> AsyncGenerator[dict, None]:
        while True:
            if self._connected:
                # Use to_thread to avoid blocking the asyncio event loop
                frame = await asyncio.to_thread(self._cam.get_frame, 1000)
                if frame is not None:
                    _, jpeg = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
                    metadata = {
                        "width": frame.shape[1],
                        "height": frame.shape[0],
                        "timestamp": time.time(),
                        "camera_temp": await asyncio.to_thread(self._cam.get_temperature),
                        "overlay_telemetry": {
                            "crosshair": {"x": frame.shape[1] // 2, "y": frame.shape[0] // 2},
                            "bboxes": []
                        },
                        "service_telemetry": {
                            "processing_time_ms": 12.5,
                            "capture_engine": "Hikrobot SDK Direct"
                        },
                        "image": jpeg.tobytes()
                    }
                    yield metadata
            await asyncio.sleep(0.033)

    async def stream(self) -> AsyncGenerator[bytes, None]:
        async for data_dict in self.stream_raw():
            img_bytes = data_dict["image"]
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + img_bytes + b'\r\n')
