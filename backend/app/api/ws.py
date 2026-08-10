import json
import asyncio
import base64
import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from app.api.camera import get_camera_service
from app.core.database import get_db
from app.models.models import Event
from sqlalchemy.ext.asyncio import AsyncSession
from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)
router = APIRouter()

@asynccontextmanager
async def get_db_context():
    async for session in get_db():
        yield session

@router.websocket("/camera/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    
    send_lock = asyncio.Lock()
    
    async def safe_send_json(data):
        async with send_lock:
            await websocket.send_json(data)
            
    # Subscriptions for THIS client
    active_subs = set()
    
    #try:
    #    async with get_db_context() as db:
    #        event = Event(event_type="connection", message=f"Client connected from {websocket.client}")
    #        db.add(event)
    #        await db.commit()
    #except Exception as e:
    #    logger.error(f"Failed to log connection: {e}")
        
    init_msg = json.dumps({
        "action": "init",
        "capabilities": ["video", "telemetry", "events"],
        "subscriptions": list(active_subs)
    })
    async with send_lock:
        await websocket.send_text(init_msg)
    
    async def send_video_frames():
        camera = get_camera_service()
        frame_count = 0
        try:
            async for frame_data in camera.stream_raw():
                if "video" in active_subs:
                    frame_count += 1
                    # Frame skipping: send every 3rd frame (~10 FPS for UI)
                    if frame_count % 3 != 0:
                        continue
                        
                    img_bytes = frame_data.pop("image", b"")
                    payload = {
                        "action": "video",
                        "width": frame_data.get("width", 640),
                        "height": frame_data.get("height", 480),
                        "camera_temp": frame_data.get("camera_temp", 0.0),
                        "overlay_telemetry": frame_data.get("overlay_telemetry", {}),
                        "service_telemetry": frame_data.get("service_telemetry", {}),
                        "timestamp": frame_data.get("timestamp", asyncio.get_event_loop().time())
                    }
                    
                    meta_json = json.dumps(payload).encode('utf-8')
                    len_bytes = len(meta_json).to_bytes(4, byteorder='little')
                    
                    if isinstance(img_bytes, str):
                        img_bytes = base64.b64decode(img_bytes)
                        
                    blob = len_bytes + meta_json + img_bytes
                    async with send_lock:
                        await websocket.send_bytes(blob)
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Frame push error: {e}")
    
    async def send_telemetry():
        camera = get_camera_service()
        try:
            while True:
                if "telemetry" in active_subs:
                    status = (await camera.get_status()).model_dump()
                    telemetry = {"action": "telemetry", "status": status}
                    await safe_send_json(telemetry)
                await asyncio.sleep(1.0)
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Telemetry capture failed: {e}")
            
    video_task = asyncio.create_task(send_video_frames())
    telemetry_task = asyncio.create_task(send_telemetry())
    
    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            action = message.get("action")
            
            if action == "subscribe":
                types = message.get("types", [])
                for t in types:
                    active_subs.add(t)
                await safe_send_json({
                    "action": "subscribed",
                    "active": list(active_subs)
                })
            elif action == "unsubscribe":
                types = message.get("types", [])
                for t in types:
                    active_subs.discard(t)
                    
    except WebSocketDisconnect:
        logger.info("Client disconnected")
    except Exception as e:
        logger.error(f"WS loop error: {e}")
    finally:
        video_task.cancel()
        telemetry_task.cancel()
        
        #try:
        #    async with get_db_context() as db:
        #        event = Event(event_type="disconnection", message=f"Client {websocket.client} disconnected")
        #        db.add(event)
        #        await db.commit()
        #except Exception as e:
        #    logger.error(f"Failed to log disconnection: {e}")