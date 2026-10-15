import cv2
import numpy as np
from PIL import Image, ImageOps
from typing import Tuple, List, Dict, Any, Optional

CLAIM_KEYWORDS = [
    "patient", "policy", "hospital", "admission", "discharge", "claim",
    "total", "date", "amount", "doctor", "diagnosis", "bill", "name",
    "tpa", "insured", "sum", "receipt", "rupees", "rs", "inr"
]

class OrientationCorrector:
    @staticmethod
    def fix_exif_orientation(image_path: str) -> Optional[np.ndarray]:
        """Loads image applying EXIF orientation metadata."""
        try:
            with Image.open(image_path) as img:
                img_exif = ImageOps.exif_transpose(img)
                # Convert PIL to OpenCV BGR
                rgb = img_exif.convert("RGB")
                np_img = np.array(rgb)
                return cv2.cvtColor(np_img, cv2.COLOR_RGB2BGR)
        except Exception:
            return cv2.imread(image_path)

    @staticmethod
    def rotate_image_cardinal(image: np.ndarray, angle: int) -> np.ndarray:
        """Rotates image by 0, 90, 180, or 270 degrees clockwise."""
        if angle == 90:
            return cv2.rotate(image, cv2.ROTATE_90_CLOCKWISE)
        elif angle == 180:
            return cv2.rotate(image, cv2.ROTATE_180)
        elif angle == 270:
            return cv2.rotate(image, cv2.ROTATE_90_COUNTERCLOCKWISE)
        return image

    @classmethod
    def detect_coarse_orientation(cls, image: np.ndarray, ocr_fn=None) -> Tuple[int, Dict[str, Any]]:
        """
        Detects 0, 90, 180, 270 degrees orientation.
        Uses downscaled image and evaluates text line horizontal structure + keyword hits if ocr_fn is provided.
        Returns (best_angle, evaluation_details).
        """
        h, w = image.shape[:2]
        # Downscale to max 800px on long edge for fast evaluation
        scale = 800.0 / max(h, w)
        if scale < 1.0:
            small_img = cv2.resize(image, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)
        else:
            small_img = image

        scores = {0: 0.0, 90: 0.0, 180: 0.0, 270: 0.0}

        # 1. Structural horizontal vs vertical text projection analysis
        # Horizontal lines of text produce sharp variance in horizontal projection profiles
        for angle in [0, 90]:
            rot = cls.rotate_image_cardinal(small_img, angle)
            gray = cv2.cvtColor(rot, cv2.COLOR_BGR2GRAY) if len(rot.shape) == 3 else rot
            # Sobel horizontal gradients
            grad_y = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
            # Horizontal projection profile of edges
            profile = np.sum(np.abs(grad_y), axis=1)
            # Higher variance indicates distinct horizontal text lines
            line_score = float(np.var(profile))
            if angle == 0:
                scores[0] += line_score
                scores[180] += line_score * 0.95  # 180 has similar horizontal lines, distinguished by OCR
            else:
                scores[90] += line_score
                scores[270] += line_score * 0.95

        # 2. OCR keyword verification if an OCR function is available
        if ocr_fn:
            for angle in [0, 90, 180, 270]:
                rot = cls.rotate_image_cardinal(small_img, angle)
                try:
                    ocr_res = ocr_fn(rot)
                    text_lower = ocr_res.full_text.lower()
                    kw_hits = sum(1 for kw in CLAIM_KEYWORDS if kw in text_lower)
                    # Significant boost for domain keyword recovery
                    scores[angle] += kw_hits * 1000.0 + (ocr_res.mean_confidence * 50.0)
                except Exception:
                    pass

        best_angle = max(scores, key=scores.get)
        margin = scores[best_angle] - sorted(scores.values())[-2] if len(scores) > 1 else 0

        details = {
            "angles_evaluated": scores,
            "chosen_angle": best_angle,
            "confidence_margin": margin,
            "low_margin": margin < 100.0
        }

        return best_angle, details
