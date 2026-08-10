import asyncio
import time
import random
import os
import zmq
import zmq.asyncio
from app.services.camera import CameraService
from app.core.config import settings
from app.core.database import SessionLocal
from app.models.models import Defect
import datetime

class MockYoloWorker:
    def __init__(self, camera: CameraService):
        self.camera = camera
        self.running = False
        self._task = None
        self._context = zmq.asyncio.Context()
        self._sub_socket = None

    async def start(self):
        self.running = True
        
        # Connect to ZMQ stream independently
        self._sub_socket = self._context.socket(zmq.SUB)
        stream_addr = settings.zmq_camera_address.replace("5555", "5556")
        self._sub_socket.connect(stream_addr)
        self._sub_socket.setsockopt_string(zmq.SUBSCRIBE, "")
        
        self._task = asyncio.create_task(self._loop())

    async def stop(self):
        self.running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        if self._sub_socket:
            self._sub_socket.close()

    async def _loop(self):
        print("[ML WORKER] Started mocking YOLO inference.")
        
        os.makedirs("/app/data/defects", exist_ok=True)
        
        while self.running:
            try:
                metadata = await self._sub_socket.recv_json()
                if self._sub_socket.getsockopt(zmq.RCVMORE):
                    jpeg_bytes = await self._sub_socket.recv()
                else:
                    continue # Skip if no bytes
                
                # Mock ML: 1% chance per frame (since it's running 30fps)
                if random.random() < 0.005:
                    confidence = 0.85 + random.random()*0.14
                    print(f"[ML WORKER] Defect detected! Confidence: {confidence:.2f}")
                    
                    # 1. Trigger hardware
                    success = await self.camera.trigger_defect()
                    
                    # 2. Save image to disk
                    timestamp_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")
                    filename = f"defect_{timestamp_str}.jpg"
                    filepath = os.path.join("/app/data/defects", filename)
                    with open(filepath, "wb") as f:
                        f.write(jpeg_bytes)
                        
                    # 3. Save to DB
                    bbox = {"x": random.randint(100, 500), "y": random.randint(100, 300), "w": 100, "h": 100}
                    async with SessionLocal() as session:
                        defect = Defect(
                            defect_type="Tear",
                            confidence=confidence,
                            bbox_data=bbox,
                            image_path=filename
                        )
                        session.add(defect)
                        await session.commit()
                        
            except zmq.Again:
                pass
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"[ML WORKER ERROR] {e}")
                await asyncio.sleep(1)
