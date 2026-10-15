import os
from pathlib import Path
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from app.config import settings
from app.api.routes import router as api_router

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Universal OCR Document Extraction, Image Enhancement, and Autofill System for Health Insurance Claims"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API router
app.include_router(api_router)

# Mount processed files directory for secure preview
processed_path = settings.PROCESSED_DIR.resolve()
app.mount("/data/processed", StaticFiles(directory=str(processed_path)), name="processed_data")

# Frontend directory
frontend_dir = (settings.BASE_DIR / "frontend").resolve()
frontend_dir.mkdir(parents=True, exist_ok=True)

# Mount frontend static assets
app.mount("/static", StaticFiles(directory=str(frontend_dir)), name="static")

@app.get("/")
def serve_index():
    index_file = frontend_dir / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    return {"message": "Health Claim OCR Backend running. Frontend index.html not yet installed."}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=settings.DEBUG)
