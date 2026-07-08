from fastapi import APIRouter, Depends
from app.services.camera import CameraService, CameraStatus, MockCamera, ZmqCamera
from app.core.config import settings

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