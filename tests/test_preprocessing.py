import cv2
import numpy as np
import pytest
from app.preprocessing.quality import ImageQualityAssessor
from app.preprocessing.orientation import OrientationCorrector
from app.preprocessing.deskew import ImageDeskewer
from app.preprocessing.deblur import ImageDeblurrer
from app.preprocessing.enhancement import ImageEnhancer
from app.preprocessing.pipeline import PreprocessingPipeline

def create_synthetic_test_image():
    # 400x600 image with clear horizontal text-like black bars on white background
    img = np.ones((600, 400, 3), dtype=np.uint8) * 255
    for y in range(80, 500, 50):
        cv2.putText(img, "PATIENT CLAIM RECORD 12345", (30, y), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)
    return img

def test_quality_assessment():
    clean_img = create_synthetic_test_image()
    assessor = ImageQualityAssessor()
    clean_metrics = assessor.assess(clean_img)

    assert clean_metrics.is_blurred is False
    assert clean_metrics.sharpness_laplacian > 100.0

    # Blur the image and re-assess
    blurred = cv2.GaussianBlur(clean_img, (15, 15), 4.0)
    blurred_metrics = assessor.assess(blurred)
    assert blurred_metrics.is_blurred is True
    assert blurred_metrics.sharpness_laplacian < clean_metrics.sharpness_laplacian

def test_coarse_orientation():
    base_img = create_synthetic_test_image()
    # Rotate by 90 degrees
    rot_90 = cv2.rotate(base_img, cv2.ROTATE_90_CLOCKWISE)

    angle, details = OrientationCorrector.detect_coarse_orientation(rot_90)
    assert angle in (90, 270)  # Distinctly identifies vertical vs horizontal axis

def test_fine_deskew_no_cropping():
    base_img = create_synthetic_test_image()
    deskewer = ImageDeskewer()

    # Rotate 15 degrees
    rotated = deskewer.rotate_bound(base_img, 15.0)

    # Canvas should have expanded to avoid clipping
    assert rotated.shape[0] >= base_img.shape[0]
    assert rotated.shape[1] >= base_img.shape[1]

def test_deblur_and_enhancement():
    base_img = create_synthetic_test_image()
    deblurrer = ImageDeblurrer()
    enhancer = ImageEnhancer()

    # Unsharp mask
    sharpened = deblurrer.unsharp_mask(base_img, sigma=1.0, strength=1.5)
    assert sharpened.shape == base_img.shape

    # Wiener deconvolution
    wiener = deblurrer.wiener_deconvolution(base_img, kernel_size=5)
    assert wiener.shape == base_img.shape

    # CLAHE
    clahe = enhancer.apply_clahe(base_img, clip_limit=2.0)
    assert clahe.shape == base_img.shape

    # Illumination normalization
    norm = enhancer.normalize_illumination(base_img)
    assert norm.shape == base_img.shape

def test_pipeline_execution(tmp_path):
    base_img = create_synthetic_test_image()
    img_path = tmp_path / "test_sample.png"
    cv2.imwrite(str(img_path), base_img)

    pipeline = PreprocessingPipeline()
    enhanced, metrics, records = pipeline.process_image(str(img_path))

    assert enhanced is not None
    assert metrics is not None
    assert len(records) > 0
    assert any(r.step == "exif_orientation" for r in records)
