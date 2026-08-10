from fastapi import FastAPI
from app.api.camera import router as camera_router, get_camera_service
from app.services.ml import MockYoloWorker
from app.services.retention import RetentionWorker
from app.api.ws import router as ws_router
from app.core.database import init_db
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse

app = FastAPI(title="Web-HMI Camera Service")

app.include_router(camera_router)
app.include_router(ws_router)

# Mount static files for the Web HMI frontend
app.mount("/static", StaticFiles(directory="static"), name="static")

import os
os.makedirs("/app/data", exist_ok=True)
app.mount("/data", StaticFiles(directory="/app/data"), name="data")

# Global worker instances
ml_worker = None
retention_worker = None

@app.on_event("startup")
async def startup_event():
    global ml_worker, retention_worker
    await init_db()
    ml_worker = MockYoloWorker(get_camera_service())
    await ml_worker.start()
    
    retention_worker = RetentionWorker(retention_days=30, interval_hours=24)
    await retention_worker.start()

@app.on_event("shutdown")
async def shutdown_event():
    global ml_worker, retention_worker
    if ml_worker:
        await ml_worker.stop()
    if retention_worker:
        await retention_worker.stop()
    camera = get_camera_service()
    if hasattr(camera, 'close'):
        camera.close()


@app.get("/")
async def root():
    return RedirectResponse(url="/static/index.html")