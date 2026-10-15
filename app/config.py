import os
from pathlib import Path
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # App info
    APP_NAME: str = "Universal Health Claim OCR & Autofill System"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    # Directories
    BASE_DIR: Path = Path(__file__).resolve().parent.parent
    UPLOAD_DIR: Path = BASE_DIR / "data" / "uploads"
    PROCESSED_DIR: Path = BASE_DIR / "data" / "processed"
    MODELS_DIR: Path = BASE_DIR / "data" / "models"
    TEMP_DIR: Path = BASE_DIR / "data" / "temp"

    # Ingestion & Upload limits
    MAX_UPLOAD_SIZE_BYTES: int = 100 * 1024 * 1024  # 100 MB total upload
    MAX_FILE_SIZE_BYTES: int = 50 * 1024 * 1024    # 50 MB single file
    MAX_ZIP_EXTRACTED_BYTES: int = 250 * 1024 * 1024  # 250 MB decompressed limit (zip bomb defense)
    MAX_ZIP_NESTING_DEPTH: int = 3
    MAX_ARCHIVE_FILE_COUNT: int = 100
    ALLOWED_EXTENSIONS: set = {".zip", ".pdf", ".png", ".jpg", ".jpeg", ".tiff", ".tif"}

    # PDF Processing
    PDF_RENDER_DPI: int = 300
    PDF_TEXT_USABLE_MIN_CHAR_DENSITY: float = 0.05  # minimum chars per square inch to consider digital text usable

    # Image preprocessing limits & targets
    MAX_IMAGE_DIMENSION: int = 4096
    OPTIMAL_TEXT_HEIGHT_PIXELS: int = 32  # Target text height for OCR recognition
    BLUR_LAPLACIAN_THRESHOLD: float = 100.0
    CONTRAST_LOW_THRESHOLD: float = 40.0
    MAX_PREPROCESSING_RETRIES_PER_PAGE: int = 3
    PAGE_PROCESSING_TIMEOUT_SECONDS: int = 45

    # OCR configuration
    OCR_PRIMARY_ENGINE: str = "easyocr"
    OCR_LANGUAGES: list[str] = ["en"]
    OCR_USE_GPU: bool = True
    OCR_MODEL_DIR: str = str(Path.home() / ".EasyOCR" / "model")
    OCR_CONFIDENCE_THRESHOLD_ACCEPT: float = 0.70
    OCR_CONFIDENCE_THRESHOLD_REVIEW: float = 0.45

    # Target Claim Default Values & SLAs
    DEFAULT_SLA_DAYS_STANDARD: int = 7
    DEFAULT_SLA_DAYS_URGENT: int = 3
    DEFAULT_SLA_DAYS_EMERGENCY: int = 1

    # Security
    MASK_SENSITIVE_DATA: bool = True  # Mask Aadhaar, Bank Accounts on UI/logs

    class Config:
        env_prefix = "CLAIM_OCR_"

settings = Settings()

# Ensure directories exist
for directory in [settings.UPLOAD_DIR, settings.PROCESSED_DIR, settings.MODELS_DIR, settings.TEMP_DIR]:
    directory.mkdir(parents=True, exist_ok=True)
