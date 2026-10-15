from typing import Optional, List, Dict, Any
import numpy as np
from app.ocr.engine import OCREngine
from app.models.ocr import OCRResult, OCRBox, BoundingBox, ExtractionMethod

class MockOCREngine(OCREngine):
    """
    Mock OCR engine for fast unit and integration testing without downloading or loading models.
    Can be primed with deterministic text responses or reads predefined test text.
    """
    def __init__(self, predefined_text: Optional[str] = None):
        self.predefined_text = predefined_text

    def is_available(self) -> bool:
        return True

    def recognize(self,
                  image: np.ndarray,
                  profile: str = "default",
                  allowlist: Optional[str] = None,
                  blocklist: Optional[str] = None,
                  page_number: int = 1,
                  extraction_method: ExtractionMethod = ExtractionMethod.OCR,
                  rotation_applied: int = 0,
                  enhancement_applied: Optional[List[str]] = None,
                  **kwargs: Any) -> OCRResult:
        
        text = self.predefined_text or "PATIENT NAME: ARJUN SHARMA\nPOLICY NO: POL-882910\nHOSPITAL: APOLLO HOSPITAL\nTOTAL AMOUNT: 1,25,000"
        lines = text.split("\n")
        boxes: List[OCRBox] = []

        y_offset = 50
        for line_idx, line in enumerate(lines, start=1):
            words = line.split(" ")
            x_offset = 50
            for w in words:
                w_len = len(w) * 12
                bbox = BoundingBox(
                    x_min=x_offset,
                    y_min=y_offset,
                    x_max=x_offset + w_len,
                    y_max=y_offset + 25
                )
                boxes.append(OCRBox(
                    text=w,
                    confidence=0.98,
                    polygon=[
                        [bbox.x_min, bbox.y_min],
                        [bbox.x_max, bbox.y_min],
                        [bbox.x_max, bbox.y_max],
                        [bbox.x_min, bbox.y_max]
                    ],
                    box=bbox,
                    page_number=page_number,
                    line_number=line_idx
                ))
                x_offset += w_len + 15
            y_offset += 35

        return OCRResult(
            boxes=boxes,
            full_text=text,
            mean_confidence=0.98,
            low_confidence_ratio=0.0,
            engine="mock_ocr",
            profile_used=profile,
            extraction_method=extraction_method,
            rotation_applied=rotation_applied,
            enhancement_applied=enhancement_applied or []
        )
