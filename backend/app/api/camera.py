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

class SettingsRequest(BaseModel):
    exposure: float = None
    gain: float = None

@router.post("/settings")
async def apply_settings(request: SettingsRequest, camera: CameraService = Depends(get_camera_service)):
    # Assuming the camera service has a way to send settings.
    # In ZmqCamera, we can add a method or just use _send_command directly.
    # Let's add set_settings to CameraService.
    success = await camera.set_settings(exposure=request.exposure, gain=request.gain)
    return {"success": success}

@router.get("/stream")
async def stream_camera(camera: CameraService = Depends(get_camera_service)):
    return StreamingResponse(
        camera.stream(),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )

@router.get("/logs")
async def get_logs():
    return {
        "logs": [
            "[2026-08-10 12:00:01] INFO - Backend initialized",
            "[2026-08-10 12:00:05] INFO - Attempting connection...",
            "[2026-08-10 12:00:08] SUCCESS - ZMQ Connected",
        ]
    }