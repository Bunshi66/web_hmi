from fastapi import APIRouter, Depends, Request, Body
from fastapi.responses import StreamingResponse
from functools import lru_cache
from pydantic import BaseModel
import datetime

from app.services.camera import CameraService, CameraStatus, MockCamera, RealHikrobotCamera
from app.core.config import settings
from app.core.database import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.models.models import SystemLog

router = APIRouter(prefix="/camera", tags=["camera"])

@lru_cache(maxsize=1)
def get_camera_service() -> CameraService:
    """Фабрика: один экземпляр на всё приложение."""
    if settings.camera_mode == "real":
        return RealHikrobotCamera()
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

class IOConfigureRequest(BaseModel):
    line_name: str
    output_name: str

@router.post("/io/configure")
async def configure_io(request: Request, body: IOConfigureRequest, camera: CameraService = Depends(get_camera_service), db: AsyncSession = Depends(get_db)):
    success = await camera.configure_io(line_name=body.line_name, output_name=body.output_name)
    
    client_ip = request.client.host
    log = SystemLog(level="INFO", ip_address=client_ip, message=f"Configured IO {body.line_name} as {body.output_name}. Success: {success}")
    db.add(log)
    await db.commit()
    
    return {"success": success}

class IOSetRequest(BaseModel):
    state: bool
    output_name: str

@router.post("/io/set")
async def set_io(request: Request, body: IOSetRequest, camera: CameraService = Depends(get_camera_service), db: AsyncSession = Depends(get_db)):
    success = await camera.set_io(state=body.state, output_name=body.output_name)
    
    client_ip = request.client.host
    log = SystemLog(level="INFO", ip_address=client_ip, message=f"Set IO {body.output_name} to {body.state}. Success: {success}")
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
    formatted_logs = [
        {
            "timestamp": log.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            "level": log.level,
            "ip_address": log.ip_address,
            "message": log.message
        }
        for log in logs
    ]
    return {"logs": formatted_logs[::-1]}

@router.delete("/logs/clear")
async def clear_logs(db: AsyncSession = Depends(get_db)):
    try:
        from sqlalchemy import delete
        await db.execute(delete(SystemLog))
        await db.commit()
        return {"success": True, "message": "Logs cleared successfully"}
    except Exception as e:
        await db.rollback()
        return {"success": False, "error": str(e)}

from app.models.models import Defect
from sqlalchemy import desc

@router.get("/defects")
async def get_defects(limit: int = 10, offset: int = 0, time_range: str = "all", db: AsyncSession = Depends(get_db)):
    query = select(Defect)
    
    if time_range != "all":
        now = datetime.datetime.now(datetime.timezone.utc)
        if time_range == "shift":
            start_time = now - datetime.timedelta(hours=8)
        elif time_range == "day":
            start_time = now - datetime.timedelta(days=1)
        elif time_range == "week":
            start_time = now - datetime.timedelta(days=7)
        else:
            start_time = now
            
        query = query.where(Defect.timestamp >= start_time)
        
    result = await db.execute(
        query.order_by(desc(Defect.timestamp)).limit(limit).offset(offset)
    )
    defects = result.scalars().all()
    
    # Count total with same filter
    count_query = select(func.count()).select_from(Defect)
    if time_range != "all":
        count_query = count_query.where(Defect.timestamp >= start_time)
        
    total_result = await db.execute(count_query)
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

from sqlalchemy import delete
import os

@router.delete("/defects")
async def clear_defects(db: AsyncSession = Depends(get_db)):
    try:
        # Get all records first to know which files to delete
        result = await db.execute(select(Defect))
        defects = result.scalars().all()

        # Delete all records from database
        await db.execute(delete(Defect))
        await db.commit()
        
        # Clear the images directory safely
        import logging
        defects_dir = "/app/data/defects"
        for defect in defects:
            if defect.image_path:
                file_path = os.path.join(defects_dir, defect.image_path)
                try:
                    if os.path.exists(file_path) and os.path.isfile(file_path):
                        os.unlink(file_path)
                except Exception as e:
                    logging.warning(f"Error deleting file {file_path}: {e}")
                    
        return {"success": True, "message": "Archive cleared successfully"}
    except Exception as e:
        await db.rollback()
        return {"success": False, "error": str(e)}

import zipfile
from io import BytesIO
from fastapi.responses import StreamingResponse
from app.models.models import ConnectionSettings
from pydantic import BaseModel
from sqlalchemy import select

@router.get("/defects/export")
async def export_defects(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Defect))
    defects = result.scalars().all()
    
    # Create an in-memory zip file
    zip_buffer = BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        # Create CSV manifest
        csv_lines = ["id,timestamp,defect_type,confidence,image_path"]
        for d in defects:
            csv_lines.append(f"{d.id},{d.timestamp.isoformat()},{d.defect_type},{d.confidence},{d.image_path}")
            
            # Add image to zip if it exists
            img_path = f"/app/data/defects/{d.image_path}"
            if os.path.exists(img_path):
                zip_file.write(img_path, arcname=f"images/{d.image_path}")
                
        # Add manifest to zip
        zip_file.writestr("manifest.csv", "\n".join(csv_lines))
        
    zip_buffer.seek(0)
    return StreamingResponse(
        zip_buffer, 
        media_type="application/zip", 
        headers={"Content-Disposition": "attachment; filename=defects_archive.zip"}
    )

class ConnectionSettingsUpdate(BaseModel):
    target_ip: str
    auto_reconnect: bool
    reconnect_interval: int

@router.get("/settings/connection")
async def get_connection_settings(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(ConnectionSettings).limit(1))
    settings = result.scalars().first()
    if not settings:
        settings = ConnectionSettings()
        db.add(settings)
        await db.commit()
        await db.refresh(settings)
    return {
        "target_ip": settings.target_ip,
        "auto_reconnect": bool(settings.auto_reconnect),
        "reconnect_interval": settings.reconnect_interval
    }

@router.post("/settings/connection")
async def update_connection_settings(data: ConnectionSettingsUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(ConnectionSettings).limit(1))
    settings = result.scalars().first()
    if not settings:
        settings = ConnectionSettings()
        db.add(settings)
        
    settings.target_ip = data.target_ip
    settings.auto_reconnect = 1 if data.auto_reconnect else 0
    settings.reconnect_interval = data.reconnect_interval
    await db.commit()
    return {"success": True}

from app.models.models import AppSettings

class AppSettingsUpdate(BaseModel):
    active_ml_model: str
    confidence_threshold: float = 0.5
    iou_threshold: float = 0.45
    max_det: int = 100

@router.get("/settings/app")
async def get_app_settings(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(AppSettings).limit(1))
    settings = result.scalars().first()
    if not settings:
        settings = AppSettings()
        db.add(settings)
        await db.commit()
        await db.refresh(settings)
    return {
        "active_ml_model": settings.active_ml_model,
        "confidence_threshold": settings.confidence_threshold,
        "iou_threshold": settings.iou_threshold,
        "max_det": settings.max_det
    }

@router.post("/settings/app")
async def update_app_settings(data: AppSettingsUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(AppSettings).limit(1))
    settings = result.scalars().first()
    if not settings:
        settings = AppSettings()
        db.add(settings)
        
    settings.active_ml_model = data.active_ml_model
    settings.confidence_threshold = data.confidence_threshold
    settings.iou_threshold = data.iou_threshold
    settings.max_det = data.max_det
    await db.commit()
    return {"success": True}

from app.services.ml import trigger_manual_save

@router.post("/manual-defect")
async def trigger_manual_defect():
    trigger_manual_save()
    return {"success": True}