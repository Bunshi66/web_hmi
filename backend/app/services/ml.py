import asyncio
import time
import datetime
import random
import os
import zmq
import zmq.asyncio
from app.services.camera import CameraService
from app.core.config import settings
from app.core.database import async_session
from app.models.models import Defect, AppSettings
from sqlalchemy import select

# Global state for current telemetry overlay (read by ws.py)
current_ml_telemetry = {
    "model": "detection",
    "data": {"bboxes": []}
}

manual_defect_trigger = False

def trigger_manual_save():
    global manual_defect_trigger
    manual_defect_trigger = True

import cv2
import numpy as np
import colorsys

def get_color_by_class(cls_id: int, alpha: float = 1.0) -> str:
    """Generate a distinct RGBA color based on class ID using golden ratio hue progression."""
    # Golden ratio conjugate ensures distinct hues
    hue = (cls_id * 0.618033988749895) % 1.0
    # Saturation and lightness fixed to ensure bright, visible colors
    saturation = 0.85
    lightness = 0.55
    r, g, b = colorsys.hls_to_rgb(hue, lightness, saturation)
    return f"rgba({int(r*255)}, {int(g*255)}, {int(b*255)}, {alpha})"

class YoloWorker:
    def __init__(self, camera: CameraService):
        self.camera = camera
        self.running = False
        self._task = None
        self._context = zmq.asyncio.Context()
        self._sub_socket = None
        
        # We will lazy-load the ultralytics models
        self.active_model_name = None
        self.model = None

    async def start(self):
        self.running = True
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

    async def _get_app_settings(self):
        try:
            async with async_session() as session:
                result = await session.execute(select(AppSettings).limit(1))
                app_settings = result.scalars().first()
                if app_settings:
                    return app_settings.active_ml_model, app_settings.confidence_threshold, app_settings.iou_threshold, app_settings.max_det
        except Exception as e:
            print(f"Error fetching active ML model: {e}")
        return "detection", 0.5, 0.45, 100

    def _load_model(self, model_type):
        from ultralytics import YOLO
        if model_type == "detection":
            return YOLO("yolo11n.pt")
        elif model_type == "segmentation":
            return YOLO("yolo11n-seg.pt")
        elif model_type == "electronic_segmentation":
            # Attempt to load custom electronic components model
            model_path = "electronic_seg.pt"
            if not os.path.exists(model_path):
                print(f"[ML WORKER] Custom model {model_path} not found! Falling back to yolo11n-seg.pt")
                model_path = "yolo11n-seg.pt"
            return YOLO(model_path)
        elif model_type == "classification":
            return YOLO("yolo11n-cls.pt")
        return None

    async def _loop(self):
        print("[ML WORKER] Started real YOLO11 inference.")
        os.makedirs("/app/data/defects", exist_ok=True)
        global current_ml_telemetry, manual_defect_trigger
        
        frame_counter = 0

        while self.running:
            try:
                metadata = await self._sub_socket.recv_json()
                if self._sub_socket.getsockopt(zmq.RCVMORE):
                    jpeg_bytes = await self._sub_socket.recv()
                else:
                    continue
                
                frame_counter += 1
                
                # Only run inference every N frames to avoid queuing up too much if inference is slow
                # In production, we'd use a queue with maxsize=1 to drop frames.
                if frame_counter % 3 != 0:
                    continue
                
                active_model, conf_thresh, iou_thresh, max_det = await self._get_app_settings()
                
                # Check if model changed and needs reloading
                if self.active_model_name != active_model or self.model is None:
                    print(f"[ML WORKER] Loading model for {active_model}...")
                    self.active_model_name = active_model
                    # This might block the event loop temporarily (model download/load), which is acceptable for a prototype.
                    self.model = self._load_model(active_model)
                    
                current_ml_telemetry["model"] = active_model
                
                if self.model is None:
                    continue
                    
                # Decode image
                np_arr = np.frombuffer(jpeg_bytes, np.uint8)
                img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
                if img is None:
                    continue

                # Run inference
                # To prevent blocking the async loop entirely, we should theoretically run this in an executor, 
                # but Ultralytics might be fast enough on n-models, or we just accept the jitter.
                results = await asyncio.to_thread(self.model, img, conf=conf_thresh, iou=iou_thresh, max_det=max_det, verbose=False)
                result = results[0]
                
                inf_time = result.speed.get("inference", 0.0)
                current_ml_telemetry["inference_time_ms"] = inf_time

                is_critical_defect = False
                
                if active_model == "detection":
                    bboxes = []
                    if result.boxes is not None:
                        for box in result.boxes:
                            x1, y1, x2, y2 = box.xyxy[0].tolist()
                            conf = box.conf[0].item()
                            cls_id = int(box.cls[0].item())
                            label = f"{result.names[cls_id]} {conf*100:.0f}%"
                            color = get_color_by_class(cls_id)
                            bboxes.append({
                                "x": x1, "y": y1, "w": x2 - x1, "h": y2 - y1, 
                                "label": label, "color": color
                            })
                            # Trigger condition: if any box has very high confidence
                            if conf > 0.90:
                                is_critical_defect = True
                                
                    current_ml_telemetry["data"] = {"bboxes": bboxes}
                    
                elif active_model in ("segmentation", "electronic_segmentation"):
                    polygons = []
                    if result.masks is not None and result.boxes is not None:
                        for mask, box in zip(result.masks.xy, result.boxes):
                            conf = box.conf[0].item()
                            cls_id = int(box.cls[0].item())
                            label = f"{result.names[cls_id]} {conf*100:.0f}%"
                            color_fill = get_color_by_class(cls_id, alpha=0.5)
                            color_stroke = get_color_by_class(cls_id, alpha=1.0)
                            # Convert array of [x, y] to string "x,y x,y"
                            points = " ".join([f"{p[0]},{p[1]}" for p in mask])
                            polygons.append({
                                "points": points,
                                "color": color_fill,
                                "stroke": color_stroke,
                                "label": label
                            })
                            if conf > 0.90:
                                is_critical_defect = True
                                
                    current_ml_telemetry["data"] = {"polygons": polygons}
                    
                elif active_model == "classification":
                    if result.probs is not None:
                        top1_id = result.probs.top1
                        top1_conf = result.probs.top1conf.item()
                        top1_label = result.names[top1_id]
                        
                        current_ml_telemetry["data"] = {
                            "classification": {
                                "label": top1_label,
                                "confidence": top1_conf,
                                "color": "#10b981" if top1_conf > 0.8 else "#ef4444"
                            }
                        }
                        if top1_conf < 0.5: # Example threshold for defect
                            is_critical_defect = True
                
                # Defect saving (Manual Trigger)
                if manual_defect_trigger:
                    manual_defect_trigger = False
                    print(f"[ML WORKER] Manual save triggered! Saving to DB.")
                    await self.camera.trigger_defect()
                    
                    timestamp_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")
                    filename = f"defect_{timestamp_str}.jpg"
                    filepath = os.path.join("/app/data/defects", filename)
                    with open(filepath, "wb") as f:
                        f.write(jpeg_bytes)
                        
                    # Extract actual class and confidence from telemetry
                    def_type = "Manual Save"
                    def_conf = 1.0
                    data = current_ml_telemetry.get("data", {})
                    
                    if active_model == "detection" and data.get("bboxes"):
                        label = data["bboxes"][0]["label"]
                        parts = label.rsplit(" ", 1)
                        if len(parts) == 2:
                            def_type = parts[0]
                            try:
                                def_conf = float(parts[1].replace("%", "")) / 100.0
                            except:
                                pass
                    elif active_model in ("segmentation", "electronic_segmentation") and data.get("polygons"):
                        label = data["polygons"][0].get("label", "")
                        if label:
                            parts = label.rsplit(" ", 1)
                            if len(parts) == 2:
                                def_type = parts[0]
                                try:
                                    def_conf = float(parts[1].replace("%", "")) / 100.0
                                except:
                                    pass
                    elif active_model == "classification" and data.get("classification"):
                        def_type = data["classification"]["label"]
                        def_conf = data["classification"]["confidence"]

                    async with async_session() as session:
                        defect = Defect(
                            defect_type=def_type,
                            confidence=def_conf,
                            bbox_data=current_ml_telemetry["data"],
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
