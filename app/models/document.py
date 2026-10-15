from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

class DocumentType(str, Enum):
    POLICY_SCHEDULE = "policy_schedule"
    CLAIM_FORM = "claim_form"
    PREAUTH_LETTER = "preauth_letter"
    DISCHARGE_SUMMARY = "discharge_summary"
    FINAL_BILL = "final_bill"
    PHARMACY_BILL = "pharmacy_bill"
    LAB_REPORT = "lab_report"
    PRESCRIPTION = "prescription"
    BANK_PROOF = "bank_proof"
    IDENTITY_DOCUMENT = "identity_document"
    UNKNOWN = "unknown"

class ProcessingStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"

class QualityMetrics(BaseModel):
    resolution: tuple[int, int] = (0, 0)
    estimated_text_height: float = 0.0
    sharpness_laplacian: float = 0.0
    sharpness_sobel: float = 0.0
    is_blurred: bool = False
    blur_type: str = "none"  # "none", "defocus", "motion"
    noise_variance: float = 0.0
    contrast_score: float = 0.0
    brightness_score: float = 0.0
    skew_angle: float = 0.0
    detected_rotation: int = 0  # 0, 90, 180, 270

class TransformationRecord(BaseModel):
    step: str
    details: Dict[str, Any] = Field(default_factory=dict)
    timestamp: Optional[str] = None

class DocumentPage(BaseModel):
    page_number: int
    source_filename: str
    original_image_path: Optional[str] = None
    enhanced_image_path: Optional[str] = None
    width: int = 0
    height: int = 0
    is_digital_pdf_page: bool = False
    quality_metrics: Optional[QualityMetrics] = None
    transformations_applied: List[TransformationRecord] = Field(default_factory=list)
    detected_rotation: int = 0
    deskew_angle: float = 0.0
    retry_count: int = 0
    ocr_profile_used: Optional[str] = None
    raw_text: str = ""
    status: ProcessingStatus = ProcessingStatus.PENDING
    error_message: Optional[str] = None

class ProcessedDocument(BaseModel):
    document_id: str
    original_filename: str
    sanitized_filename: str
    file_type: str
    mime_type: str
    file_size_bytes: int
    page_count: int = 0
    pages: List[DocumentPage] = Field(default_factory=list)
    classification: DocumentType = DocumentType.UNKNOWN
    classification_confidence: float = 0.0
    classification_evidence: List[str] = Field(default_factory=list)
    status: ProcessingStatus = ProcessingStatus.PENDING
    error_message: Optional[str] = None
