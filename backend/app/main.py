from fastapi import FastAPI
from app.api.camera import router as camera_router, get_camera_service
from app.api.ws import router as ws_router
from app.core.database import init_db
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse

app = FastAPI(title="Web-HMI Camera Service")

app.include_router(camera_router)
app.include_router(ws_router)

# Mount static files for the Web HMI frontend
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.on_event("startup")
async def startup_event():
    await init_db()

@app.on_event("shutdown")
async def shutdown_event():
    camera = get_camera_service()
    if hasattr(camera, 'close'):
        camera.close()


@app.get("/")
async def root():
    return RedirectResponse(url="/static/index.html")