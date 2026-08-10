from fastapi import APIRouter, Depends, Request, Body
from fastapi.responses import StreamingResponse
from functools import lru_cache
from pydantic import BaseModel
import datetime

from app.services.camera import CameraService, CameraStatus, MockCamera, ZmqCamera
from app.core.config import settings

router = APIRouter(prefix="/camera", tags=["camera"])

# In-memory log store
SYSTEM_LOGS = [
    f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] INFO - Backend initialized"
]

@lru_cache(maxsize=1)
def get_camera_service() -> CameraService:
    """Фабрика: один экземпляр на всё приложение."""
    if settings.camera_mode == "zmq":
        return ZmqCamera(zmq_address=settings.zmq_camera_address)
    return MockCamera(connected=True)

@router.get("/status", response_model=CameraStatus)
async def get_status(camera: CameraService = Depends(get_camera_service)):
    return await camera.get_status()

@router.post("/connect")
async def connect_camera(request: Request, body: dict = Body(...), camera: CameraService = Depends(get_camera_service)):
    ip = body.get("ip", "127.0.0.1")
    success = await camera.connect(ip)
    
    client_ip = request.client.host
    timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    SYSTEM_LOGS.append(f"[{timestamp}] INFO - [IP: {client_ip}] Attempted to connect to {ip}. Success: {success}")
    if len(SYSTEM_LOGS) > 100: SYSTEM_LOGS.pop(0)
    
    return {"success": success}

@router.post("/disconnect")
async def disconnect_camera(request: Request, camera: CameraService = Depends(get_camera_service)):
    success = await camera.disconnect()
    
    client_ip = request.client.host
    timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    SYSTEM_LOGS.append(f"[{timestamp}] INFO - [IP: {client_ip}] Disconnected camera.")
    if len(SYSTEM_LOGS) > 100: SYSTEM_LOGS.pop(0)
    
    return {"success": success}

class SettingsRequest(BaseModel):
    exposure: float = None
    gain: float = None

@router.post("/settings")
async def apply_settings(request: Request, body: SettingsRequest, camera: CameraService = Depends(get_camera_service)):
    success = await camera.set_settings(exposure=body.exposure, gain=body.gain)
    
    client_ip = request.client.host
    timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    SYSTEM_LOGS.append(f"[{timestamp}] INFO - [IP: {client_ip}] Changed settings (Exposure: {body.exposure}, Gain: {body.gain}). Success: {success}")
    if len(SYSTEM_LOGS) > 100: SYSTEM_LOGS.pop(0)
        
    return {"success": success}

@router.get("/stream")
async def stream_camera(camera: CameraService = Depends(get_camera_service)):
    return StreamingResponse(
        camera.stream(),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )

class LogMessage(BaseModel):
    message: str

@router.post("/log")
async def add_log(request: Request, log_msg: LogMessage):
    client_ip = request.client.host
    timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    log_entry = f"[{timestamp}] INFO - [IP: {client_ip}] {log_msg.message}"
    SYSTEM_LOGS.append(log_entry)
    if len(SYSTEM_LOGS) > 100: SYSTEM_LOGS.pop(0)
    return {"success": True}

@router.get("/logs")
async def get_logs():
    return {"logs": SYSTEM_LOGS}