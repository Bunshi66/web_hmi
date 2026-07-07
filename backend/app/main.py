from fastapi import FastAPI
from app.api.camera import router as camera_router

app = FastAPI(title="Web-HMI Camera Service")

app.include_router(camera_router)


@app.get("/")
async def root():
    return {"status": "ok"}


