from fastapi import APIRouter, Depends
from app.services.camera import CameraService, CameraStatus, MockCamera, ZmqCamera
from app.core.config import settings
from pydantic import BaseModel

class ConnectRequest(BaseModel):
    ip: str

router = APIRouter(prefix="/camera", tags=["camera"])


def get_camera_service() -> CameraService:
    """Фабрика: возвращает реализацию CameraService в зависимости от конфига."""
    if settings.camera_mode == "zmq":
        return ZmqCamera(zmq_address=settings.zmq_camera_address)
    return MockCamera(connected=True)


@router.get("/status", response_model=CameraStatus)
async def get_status(camera: CameraService = Depends(get_camera_service)):
    """Получить текущий статус камеры"""
    return camera.get_status()

@router.post("/connect")
async def connect_camera(request: ConnectRequest, camera: CameraService = Depends(get_camera_service)):
    """Подключиться к камере по IP"""
    success = camera.connect(request.ip)
    return {"success": success}


@router.post("/disconnect")
async def disconnect_camera(camera: CameraService = Depends(get_camera_service)):
    """Отключиться от камеры"""
    success = camera.disconnect()
    return {"success": success}