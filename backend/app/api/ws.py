import json
import asyncio
import base64
import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.api.camera import get_camera_service
from app.core.database import get_db
from app.models.models import Event
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Set

logger = logging.getLogger(__name__)
router = APIRouter()
# Tracks active connections by type (video, telemetry)
subscriptions: Dict[str, Set] = {}

@router.websocket("/camera/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    
    # Initialize connection tracking for this client
    subscriptions["video"] = set()
    subscriptions["telemetry"] = set()
    subscriptions["events"] = set()
    
    async with get_db() as db:
        try:
            event = Event(event_type="connection", message=f"Client connected from {websocket.client}")
            db.add(event)
            await db.commit()
            
            # Send initial state and capabilities to the client
            init_msg = json.dumps({
                "action": "init",
                "capabilities": ["video", "telemetry", "events"],
                "subscriptions": list(subscriptions.keys())
            })
            await websocket.send_json(init_msg)
            
            # Create a queue to buffer frames in case of backpressure
            frame_queue = asyncio.Queue()
            telemetry_queue = asyncio.Queue()
            
            async def push_frames():
                camera = get_camera_service()
                try:
                    for frame in camera.stream():
                        # Deserialize the MJPEG multipart frame from bytes to JSON structure
                        payload = {
                            "action": "video",
                            "frame": base64.b64encode(frame).decode('utf-8'),
                            "timestamp": asyncio.get_event_loop().time()
                        }
                        await frame_queue.put(payload)
                except Exception as e:
                    logger.error(f"Frame push error: {e}")
            
            async def send_frames():
                while True:
                    try:
                        payload = await asyncio.wait_for(frame_queue.get(), timeout=5.0)
                        if "video" in subscriptions and len(subscriptions["video"]) > 0:
                            # Broadcast to all subscribed clients (simplified for demo)
                            conn = await websocket.receive_text()  # Placeholder - would use actual client store
                    except asyncio.TimeoutError:
                        continue
                    except Exception as e:
                        logger.error(f"Send error: {e}")
                        break
            
                    try:
                        telemetry = {"action": "telemetry", "temperature": get_camera().get_status()}
                        await telemetry_queue.put(telemetry)
                    except Exception as e:
                        logger.error(f"Telemetry capture failed: {e}")
                    
            push_task = asyncio.create_task(push_frames())
            send_task = asyncio.create_task(send_frames())
            
            try:
                while True:
                    data = await websocket.receive_text()
                    message = json.loads(data)
                    action = message.get("action")
                    
                    if action == "subscribe":
                        types = message.get("types", [])
                        for t in types:
                            subscriptions[t].add(websocket)
                        await websocket.send_json({
                            "action": "subscribed",
                            "active": list(subscriptions.keys())
                        })
                    elif action == "unsubscribe":
                        types = message.get("types", [])
                        for t in types:
                            subscriptions[t].discard(websocket)
                    
            except WebSocketDisconnect:
                logger.info("Client disconnected")
                
            finally:
                push_task.cancel()
                send_task.cancel()
                try:
                    await push_task
                except asyncio.CancelledError:
                    pass
                try:
                    await send_task
                except asyncio.CancelledError:
                    pass
                    
        except WebSocketDisconnect:
            event = Event(event_type="disconnection", message=f"Client {websocket.client} disconnected")
            db.add(event)
            await db.commit()