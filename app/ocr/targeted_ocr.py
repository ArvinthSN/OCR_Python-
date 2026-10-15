import cv2
import numpy as np
from typing import Optional, Tuple
from app.models.ocr import BoundingBox, OCRResult, ExtractionMethod
from app.ocr.engine import OCREngine
from app.preprocessing.deblur import ImageDeblurrer
from app.preprocessing.enhancement import ImageEnhancer
from app.config import settings

class TargetedFieldOCR:
    def __init__(self, ocr_engine: OCREngine):
        self.engine = ocr_engine
        self.deblurrer = ImageDeblurrer()
        self.enhancer = ImageEnhancer()

    def re_ocr_field_crop(self,
                          full_image: np.ndarray,
                          crop_box: BoundingBox,
                          field_type: str = "alphanumeric",
                          allowlist: Optional[str] = None) -> Optional[OCRResult]:
        """
        Extracts a localized crop for a specific field, enhances it, upscales to optimal text height,
        and re-runs OCR with constrained allowlists and profiles.
        """
        h, w = full_image.shape[:2]
        
        # Add slight margin padding around bounding box
        pad_x = int(crop_box.width * 0.15) + 5
        pad_y = int(crop_box.height * 0.20) + 5

        x0 = max(0, crop_box.x_min - pad_x)
        y0 = max(0, crop_box.y_min - pad_y)
        x1 = min(w, crop_box.x_max + pad_x)
        y1 = min(h, crop_box.y_max + pad_y)

        if x1 <= x0 or y1 <= y0:
            return None

        crop = full_image[y0:y1, x0:x1].copy()

        # Target height scaling: ensure crop text is at optimal height (~32px)
        crop_h, crop_w = crop.shape[:2]
        scale = max(1.0, float(settings.OPTIMAL_TEXT_HEIGHT_PIXELS) / max(12.0, float(crop_h)))
        if scale > 1.2:
            crop = cv2.resize(crop, (int(crop_w * scale), int(crop_h * scale)), interpolation=cv2.INTER_LANCZOS4)

        # Apply localized enhancement
        crop = self.enhancer.apply_clahe(crop, clip_limit=2.0)
        crop = self.deblurrer.unsharp_mask(crop, sigma=0.8, strength=1.2)

        profile = "field_crop_numeric" if field_type == "numeric" else "field_crop_alpha"
        default_allowlist = "0123456789.,/-:" if field_type == "numeric" else None
        used_allowlist = allowlist or default_allowlist

        try:
            res = self.engine.recognize(
                crop,
                profile=profile,
                allowlist=used_allowlist,
                extraction_method=ExtractionMethod.TARGETED_RE_OCR,
                enhancement_applied=["crop_upscale", "crop_clahe", "crop_sharpen"]
            )
            return res
        except Exception:
            return None
