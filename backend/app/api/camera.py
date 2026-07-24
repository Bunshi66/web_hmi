from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from functools import lru_cache  # <-- добавь

from app.services.camera import CameraService, CameraStatus, MockCamera, ZmqCamera
from app.core.config import settings
from pydantic import BaseModel

class ConnectRequest(BaseModel):
    ip: str

router = APIRouter(prefix="/camera", tags=["camera"])


@lru_cache(maxsize=1)  # <-- singleton
def get_camera_service() -> CameraService:
    """Фабрика: один экземпляр на всё приложение."""
    if settings.camera_mode == "zmq":
        return ZmqCamera(zmq_address=settings.zmq_camera_address)
    return MockCamera(connected=True)


@router.get("/status", response_model=CameraStatus)
async def get_status(camera: CameraService = Depends(get_camera_service)):
    return await camera.get_status()

@router.post("/connect")
async def connect_camera(request: ConnectRequest, camera: CameraService = Depends(get_camera_service)):
    success = await camera.connect(request.ip)
    return {"success": success}

@router.post("/disconnect")
async def disconnect_camera(camera: CameraService = Depends(get_camera_service)):
    success = await camera.disconnect()
    return {"success": success}

@router.get("/stream")
async def stream_camera(camera: CameraService = Depends(get_camera_service)):
    return StreamingResponse(
        camera.stream(),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )