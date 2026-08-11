from fastapi import FastAPI
from app.api.camera import router as camera_router, get_camera_service
from app.services.ml import YoloWorker
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
retention_worker = None
ml_worker = None
watchdog_task = None

import asyncio
from app.core.database import async_session
from app.models.models import ConnectionSettings
from sqlalchemy import select

async def connection_watchdog():
    camera = get_camera_service()
    while True:
        try:
            async with async_session() as session:
                result = await session.execute(select(ConnectionSettings).limit(1))
                settings = result.scalars().first()
                
                if settings and settings.auto_reconnect:
                    status = await camera.get_status()
                    if not status.connected:
                        print(f"Watchdog: Camera disconnected, attempting to connect to {settings.target_ip}...")
                        await camera.connect(settings.target_ip)
                        
                interval = settings.reconnect_interval if settings else 5
        except Exception as e:
            print(f"Error in watchdog: {e}")
            interval = 5
            
        await asyncio.sleep(interval)

@app.on_event("startup")
async def startup_event():
    global ml_worker, retention_worker, watchdog_task
    await init_db()
    
    # Simple migration for max_det column
    from sqlalchemy import text
    try:
        async with async_session() as session:
            await session.execute(text("ALTER TABLE app_settings ADD COLUMN max_det INTEGER DEFAULT 100"))
            await session.commit()
    except Exception:
        pass
        
    ml_worker = YoloWorker(get_camera_service())
    await ml_worker.start()
    
    retention_worker = RetentionWorker(retention_days=30, interval_hours=24)
    await retention_worker.start()
    
    watchdog_task = asyncio.create_task(connection_watchdog())

@app.on_event("shutdown")
async def shutdown_event():
    global ml_worker, retention_worker, watchdog_task
    if watchdog_task:
        watchdog_task.cancel()
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