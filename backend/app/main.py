from fastapi import FastAPI
from app.api.camera import router as camera_router, get_camera_service
from app.api.ws import router as ws_router

app = FastAPI(title="Web-HMI Camera Service")

app.include_router(camera_router)
app.include_router(ws_router)


@app.on_event("shutdown")
async def shutdown_event():
    camera = get_camera_service()
    if hasattr(camera, 'close'):
        camera.close()


@app.get("/")
async def root():
    return {"status": "ok"}