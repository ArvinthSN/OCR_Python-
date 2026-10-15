"""
Script to pre-download EasyOCR models for offline and production usage.
"""
import os
from pathlib import Path
import easyocr
from app.config import settings

def download_models():
    model_dir = Path(settings.OCR_MODEL_DIR)
    model_dir.mkdir(parents=True, exist_ok=True)
    print(f"Checking and downloading EasyOCR models to: {model_dir}")

    # Initialize easyocr with download_enabled=True to ensure models are present
    reader = easyocr.Reader(['en'], gpu=settings.OCR_USE_GPU, model_storage_directory=str(model_dir), download_enabled=True)
    print("EasyOCR models downloaded and verified successfully!")
    print(f"Files in {model_dir}: {os.listdir(model_dir)}")

if __name__ == "__main__":
    download_models()
