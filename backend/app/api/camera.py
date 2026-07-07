from fastapi import APIRouter, Depends
from app.services.camera import CameraService, CameraStatus

router = APIRouter(prefix="/camera", tags=["camera"])


# Внедрение зависимости: FastAPI сам создаст сервис и передаст сюда
def get_camera_service() -> CameraService:
    # Пока всегда возвращаем MockCamera
    # Позже заменим на ZmqCamera по условию (из конфига)
    from app.services.camera import MockCamera
    return MockCamera(connected=True)


@router.get("/status", response_model=CameraStatus)
async def get_status(camera: CameraService = Depends(get_camera_service)):
    """Получить текущий статус камеры"""
    return camera.get_status()