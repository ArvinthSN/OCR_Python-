from enum import Enum
from typing import Optional, List, Any, Dict
from pydantic import BaseModel, Field
from app.models.ocr import BoundingBox, ExtractionMethod

class FieldStatus(str, Enum):
    EXTRACTED = "extracted"
    LOW_CONFIDENCE = "low_confidence"
    UNREADABLE = "unreadable"
    MISSING = "missing"
    INVALID = "invalid"
    CONFLICT = "conflict"
    NEEDS_REVIEW = "needs_review"

class CandidateValue(BaseModel):
    value: Any
    raw_value: str
    confidence: float
    source_filename: str
    page_number: int
    bounding_box: Optional[BoundingBox] = None
    extraction_method: ExtractionMethod = ExtractionMethod.OCR
    engine: str = "easyocr"
    preprocessed_profile: Optional[str] = None
    validation_passed: bool = True
    validation_error: Optional[str] = None

class LineItem(BaseModel):
    item_id: Optional[str] = None
    description: str
    category: Optional[str] = None  # e.g. Pharmacy, Room, Lab, Procedure
    quantity: float = 1.0
    unit_rate: float = 0.0
    amount: float = 0.0
    confidence: float = 1.0
    status: FieldStatus = FieldStatus.EXTRACTED

class ExtractedField(BaseModel):
    field_name: str
    display_name: str
    value: Any = None
    raw_value: Optional[str] = None
    normalized_value: Any = None
    status: FieldStatus = FieldStatus.MISSING
    confidence: float = 0.0
    source_filename: Optional[str] = None
    page_number: Optional[int] = None
    bounding_box: Optional[BoundingBox] = None
    evidence_text: Optional[str] = None
    extraction_method: Optional[ExtractionMethod] = None
    character_corrections: List[Dict[str, str]] = Field(default_factory=list)
    warning_message: Optional[str] = None
    recommended_action: Optional[str] = None
    candidates: List[CandidateValue] = Field(default_factory=list)
    is_masked: bool = False
    display_value: Optional[str] = None
