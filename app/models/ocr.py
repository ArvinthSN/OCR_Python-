from enum import Enum
from typing import List, Optional, Tuple
from pydantic import BaseModel, Field

class ExtractionMethod(str, Enum):
    DIRECT_PDF_TEXT = "direct_pdf_text"
    OCR = "ocr"
    OCR_AFTER_ENHANCEMENT = "ocr_after_enhancement"
    TARGETED_RE_OCR = "targeted_re_ocr"

class BoundingBox(BaseModel):
    x_min: int
    y_min: int
    x_max: int
    y_max: int

    @property
    def width(self) -> int:
        return max(0, self.x_max - self.x_min)

    @property
    def height(self) -> int:
        return max(0, self.y_max - self.y_min)

    @property
    def center(self) -> Tuple[float, float]:
        return ((self.x_min + self.x_max) / 2.0, (self.y_min + self.y_max) / 2.0)

class OCRBox(BaseModel):
    text: str
    confidence: float
    polygon: List[List[int]] = Field(default_factory=list)  # [[x1,y1], [x2,y2], [x3,y3], [x4,y4]]
    box: BoundingBox
    page_number: int = 1
    line_number: int = 0

class OCRResult(BaseModel):
    boxes: List[OCRBox] = Field(default_factory=list)
    full_text: str = ""
    mean_confidence: float = 0.0
    low_confidence_ratio: float = 0.0
    engine: str = "easyocr"
    profile_used: str = "default"
    extraction_method: ExtractionMethod = ExtractionMethod.OCR
    rotation_applied: int = 0
    enhancement_applied: List[str] = Field(default_factory=list)
