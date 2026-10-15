import numpy as np
import pytest
from app.ocr.mock_adapter import MockOCREngine
from app.ocr.targeted_ocr import TargetedFieldOCR
from app.models.ocr import BoundingBox

def test_mock_ocr_engine():
    engine = MockOCREngine()
    assert engine.is_available() is True

    dummy_img = np.ones((300, 300, 3), dtype=np.uint8) * 255
    res = engine.recognize(dummy_img)

    assert res.engine == "mock_ocr"
    assert "ARJUN SHARMA" in res.full_text
    assert len(res.boxes) > 0
    assert res.mean_confidence > 0.90

def test_targeted_field_ocr():
    engine = MockOCREngine()
    targeted = TargetedFieldOCR(engine)

    dummy_img = np.ones((500, 500, 3), dtype=np.uint8) * 255
    crop_box = BoundingBox(x_min=50, y_min=50, x_max=200, y_max=100)

    res = targeted.re_ocr_field_crop(dummy_img, crop_box, field_type="numeric")
    assert res is not None
    assert "crop_upscale" in res.enhancement_applied
