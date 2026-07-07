from fastapi import FastAPI

app = FastAPI(title="Web-HMI Camera Service")

@app.get("/")
async def root():
	return {"status": "ok"}


