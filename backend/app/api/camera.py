from fastapi import APIRouter, Depends, Request, Body
from fastapi.responses import StreamingResponse
from functools import lru_cache
from pydantic import BaseModel
import datetime

from app.services.camera import CameraService, CameraStatus, MockCamera, ZmqCamera
from app.core.config import settings
from app.core.database import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.models.models import SystemLog

router = APIRouter(prefix="/camera", tags=["camera"])

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
async def connect_camera(request: Request, body: dict = Body(...), camera: CameraService = Depends(get_camera_service), db: AsyncSession = Depends(get_db)):
    ip = body.get("ip", "127.0.0.1")
    success = await camera.connect(ip)
    
    client_ip = request.client.host
    log = SystemLog(level="INFO", ip_address=client_ip, message=f"Attempted to connect to {ip}. Success: {success}")
    db.add(log)
    await db.commit()
    
    return {"success": success}

@router.post("/disconnect")
async def disconnect_camera(request: Request, camera: CameraService = Depends(get_camera_service), db: AsyncSession = Depends(get_db)):
    success = await camera.disconnect()
    
    client_ip = request.client.host
    log = SystemLog(level="INFO", ip_address=client_ip, message="Disconnected camera.")
    db.add(log)
    await db.commit()
    
    return {"success": success}

class SettingsRequest(BaseModel):
    exposure: float = None
    gain: float = None

@router.post("/settings")
async def apply_settings(request: Request, body: SettingsRequest, camera: CameraService = Depends(get_camera_service), db: AsyncSession = Depends(get_db)):
    success = await camera.set_settings(exposure=body.exposure, gain=body.gain)
    
    client_ip = request.client.host
    log = SystemLog(level="INFO", ip_address=client_ip, message=f"Changed settings (Exposure: {body.exposure}, Gain: {body.gain}). Success: {success}")
    db.add(log)
    await db.commit()
        
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
async def add_log(request: Request, log_msg: LogMessage, db: AsyncSession = Depends(get_db)):
    client_ip = request.client.host
    log = SystemLog(level="INFO", ip_address=client_ip, message=log_msg.message)
    db.add(log)
    await db.commit()
    return {"success": True}

@router.get("/logs")
async def get_logs(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(SystemLog).order_by(SystemLog.timestamp.desc()).limit(100))
    logs = result.scalars().all()
    formatted_logs = [f"[{log.timestamp.strftime('%Y-%m-%d %H:%M:%S')}] {log.level} - [IP: {log.ip_address}] {log.message}" for log in logs]
    return {"logs": formatted_logs[::-1]}

from app.models.models import Defect
from sqlalchemy import desc

@router.get("/defects")
async def get_defects(limit: int = 50, offset: int = 0, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Defect).order_by(desc(Defect.timestamp)).limit(limit).offset(offset)
    )
    defects = result.scalars().all()
    
    total_result = await db.execute(select(func.count()).select_from(Defect))
    total = total_result.scalar()
    
    return {
        "items": [
            {
                "id": d.id,
                "timestamp": d.timestamp.isoformat(),
                "defect_type": d.defect_type,
                "confidence": d.confidence,
                "bbox_data": d.bbox_data,
                "image_url": f"/data/defects/{d.image_path}"
            } for d in defects
        ],
        "total": total
    }