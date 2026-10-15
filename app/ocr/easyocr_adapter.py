import os
import threading
import numpy as np
from typing import Optional, List, Dict, Any

from app.ocr.engine import OCREngine
from app.ocr.profiles import OCR_PROFILES
from app.models.ocr import OCRResult, OCRBox, BoundingBox, ExtractionMethod
from app.config import settings

class EasyOCRAdapter(OCREngine):
    _reader = None
    _lock = threading.Lock()

    def __init__(self,
                 languages: Optional[List[str]] = None,
                 gpu: Optional[bool] = None,
                 model_storage_directory: Optional[str] = None):
        self.languages = languages or settings.OCR_LANGUAGES
        self.gpu = gpu if gpu is not None else settings.OCR_USE_GPU
        self.model_dir = model_storage_directory or settings.OCR_MODEL_DIR

    def _get_reader(self):
        """Lazy thread-safe singleton initialization of easyocr.Reader."""
        if EasyOCRAdapter._reader is None:
            with EasyOCRAdapter._lock:
                if EasyOCRAdapter._reader is None:
                    import easyocr
                    EasyOCRAdapter._reader = easyocr.Reader(
                        lang_list=self.languages,
                        gpu=self.gpu,
                        model_storage_directory=self.model_dir,
                        download_enabled=False  # Do not download at request time
                    )
        return EasyOCRAdapter._reader

    def is_available(self) -> bool:
        if EasyOCRAdapter._reader is not None:
            return True
        try:
            import easyocr
            from pathlib import Path
            m_path = Path(self.model_dir)
            craft = m_path / "craft_mlt_25k.pth"
            return craft.exists() or Path(os.path.expanduser("~/.EasyOCR/model/craft_mlt_25k.pth")).exists()
        except Exception:
            return False

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
        """
        Executes EasyOCR recognition with profile parameters and returns sorted OCRResult.
        """
        reader = self._get_reader()
        profile_params = OCR_PROFILES.get(profile, OCR_PROFILES["default"]).copy()
        
        # Override with explicit kwargs
        if allowlist:
            profile_params["allowlist"] = allowlist
        if blocklist:
            profile_params["blocklist"] = blocklist
        profile_params.update(kwargs)

        # Call EasyOCR
        raw_results = reader.readtext(image, detail=1, **profile_params)

        ocr_boxes: List[OCRBox] = []
        confidences: List[float] = []

        for item in raw_results:
            poly, text, conf = item
            text_str = str(text).strip()
            if not text_str:
                continue

            # Polygon: [[x1, y1], [x2, y2], [x3, y3], [x4, y4]]
            poly_ints = [[int(pt[0]), int(pt[1])] for pt in poly]
            xs = [pt[0] for pt in poly_ints]
            ys = [pt[1] for pt in poly_ints]

            bbox = BoundingBox(
                x_min=min(xs),
                y_min=min(ys),
                x_max=max(xs),
                y_max=max(ys)
            )

            conf_val = float(conf)
            confidences.append(conf_val)

            ocr_boxes.append(
                OCRBox(
                    text=text_str,
                    confidence=conf_val,
                    polygon=poly_ints,
                    box=bbox,
                    page_number=page_number,
                    line_number=0
                )
            )

        # Sort boxes in natural reading order (top-to-bottom, left-to-right)
        # Cluster boxes into lines if y_centers are within ~0.5 box height
        sorted_boxes = self._cluster_into_lines(ocr_boxes)

        full_text = "\n".join(
            " ".join(b.text for b in line) for line in self._group_lines(sorted_boxes)
        )

        mean_conf = float(np.mean(confidences)) if confidences else 0.0
        low_conf_count = sum(1 for c in confidences if c < settings.OCR_CONFIDENCE_THRESHOLD_REVIEW)
        low_conf_ratio = float(low_conf_count / max(1, len(confidences)))

        return OCRResult(
            boxes=sorted_boxes,
            full_text=full_text,
            mean_confidence=mean_conf,
            low_confidence_ratio=low_conf_ratio,
            engine="easyocr",
            profile_used=profile,
            extraction_method=extraction_method,
            rotation_applied=rotation_applied,
            enhancement_applied=enhancement_applied or []
        )

    def _cluster_into_lines(self, boxes: List[OCRBox]) -> List[OCRBox]:
        """Sorts boxes by line and reading order."""
        if not boxes:
            return []

        # Sort primarily by y_min
        boxes_by_y = sorted(boxes, key=lambda b: (b.box.y_min, b.box.x_min))
        
        lines: List[List[OCRBox]] = []
        current_line: List[OCRBox] = []
        current_y = -1

        for box in boxes_by_y:
            box_height = box.box.height or 20
            box_center_y = box.box.center[1]

            if current_y == -1 or abs(box_center_y - current_y) <= (box_height * 0.6):
                current_line.append(box)
                current_y = (current_y + box_center_y) / 2.0 if current_y != -1 else box_center_y
            else:
                lines.append(sorted(current_line, key=lambda b: b.box.x_min))
                current_line = [box]
                current_y = box_center_y

        if current_line:
            lines.append(sorted(current_line, key=lambda b: b.box.x_min))

        # Flatten and assign line numbers
        flattened: List[OCRBox] = []
        for line_idx, line in enumerate(lines, start=1):
            for box in line:
                box.line_number = line_idx
                flattened.append(box)

        return flattened

    def _group_lines(self, boxes: List[OCRBox]) -> List[List[OCRBox]]:
        """Groups ordered boxes by line_number."""
        lines_dict: Dict[int, List[OCRBox]] = {}
        for b in boxes:
            lines_dict.setdefault(b.line_number, []).append(b)
        return [lines_dict[k] for k in sorted(lines_dict.keys())]
