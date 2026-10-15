import os
import cv2
import numpy as np
from datetime import datetime
from pathlib import Path
from typing import Tuple, List, Optional, Dict, Any

from app.models.document import QualityMetrics, TransformationRecord
from app.preprocessing.quality import ImageQualityAssessor
from app.preprocessing.orientation import OrientationCorrector
from app.preprocessing.deskew import ImageDeskewer
from app.preprocessing.perspective import PerspectiveCorrector
from app.preprocessing.deblur import ImageDeblurrer
from app.preprocessing.enhancement import ImageEnhancer
from app.config import settings

class PreprocessingPipeline:
    def __init__(self):
        self.assessor = ImageQualityAssessor()
        self.orientation = OrientationCorrector()
        self.deskewer = ImageDeskewer()
        self.perspective = PerspectiveCorrector()
        self.deblurrer = ImageDeblurrer()
        self.enhancer = ImageEnhancer()

    def process_image(self,
                      image_path: str,
                      ocr_fn=None,
                      estimated_text_height: float = 0.0) -> Tuple[np.ndarray, QualityMetrics, List[TransformationRecord]]:
        """
        Executes the layered orientation and enhancement pipeline on a working copy.
        Returns:
            - enhanced_image (numpy array)
            - quality_metrics (QualityMetrics)
            - transformations_applied (List of TransformationRecord)
        """
        records: List[TransformationRecord] = []

        # Step 1: Load image with EXIF orientation
        img = self.orientation.fix_exif_orientation(image_path)
        if img is None:
            raise ValueError(f"Could not read image file at {image_path}")

        records.append(TransformationRecord(
            step="exif_orientation",
            details={"action": "loaded_with_exif"},
            timestamp=datetime.utcnow().isoformat()
        ))

        # Initial quality assessment
        metrics = self.assessor.assess(img)

        # Step 2: Coarse orientation detection (0, 90, 180, 270)
        coarse_angle, angle_details = self.orientation.detect_coarse_orientation(img, ocr_fn=ocr_fn)
        if coarse_angle != 0:
            img = self.orientation.rotate_image_cardinal(img, coarse_angle)
            metrics.detected_rotation = coarse_angle
            records.append(TransformationRecord(
                step="coarse_rotation",
                details={"rotation_degrees": coarse_angle, "evaluation": angle_details},
                timestamp=datetime.utcnow().isoformat()
            ))

        # Step 3: Fine deskew (about ±45 degrees)
        skew_angle = self.deskewer.estimate_skew_angle(img)
        if abs(skew_angle) > 0.5:
            img = self.deskewer.rotate_bound(img, -skew_angle)
            metrics.skew_angle = skew_angle
            records.append(TransformationRecord(
                step="fine_deskew",
                details={"skew_angle_corrected": float(-skew_angle)},
                timestamp=datetime.utcnow().isoformat()
            ))

        # Step 4: Perspective correction (if photographed document)
        warped, was_warped = self.perspective.correct_perspective(img)
        if was_warped:
            img = warped
            records.append(TransformationRecord(
                step="perspective_warp",
                details={"corrected_quadrilateral": True},
                timestamp=datetime.utcnow().isoformat()
            ))

        # Step 5: Adaptive rescaling if low resolution text
        if estimated_text_height > 0 and estimated_text_height < settings.OPTIMAL_TEXT_HEIGHT_PIXELS:
            img = self.deblurrer.adaptive_rescale_text(img, estimated_text_height)
            records.append(TransformationRecord(
                step="adaptive_rescaling",
                details={"original_text_height": estimated_text_height, "target": settings.OPTIMAL_TEXT_HEIGHT_PIXELS},
                timestamp=datetime.utcnow().isoformat()
            ))

        # Step 6: Selective deblurring based on measured metrics
        if metrics.is_blurred:
            if metrics.blur_type == "motion":
                img = self.deblurrer.motion_deblur(img, length=9, angle=0.0)
                records.append(TransformationRecord(
                    step="motion_deblur",
                    details={"kernel_length": 9},
                    timestamp=datetime.utcnow().isoformat()
                ))
            elif metrics.blur_type == "defocus":
                img = self.deblurrer.wiener_deconvolution(img, kernel_size=5)
                records.append(TransformationRecord(
                    step="wiener_deconvolution",
                    details={"psf_kernel_size": 5},
                    timestamp=datetime.utcnow().isoformat()
                ))
            else:
                img = self.deblurrer.unsharp_mask(img, sigma=1.0, strength=1.4)
                records.append(TransformationRecord(
                    step="unsharp_mask",
                    details={"strength": 1.4},
                    timestamp=datetime.utcnow().isoformat()
                ))

        # Step 7: Selective contrast enhancement and illumination flattening
        if metrics.contrast_score < settings.CONTRAST_LOW_THRESHOLD:
            img = self.enhancer.apply_clahe(img, clip_limit=2.5)
            records.append(TransformationRecord(
                step="clahe_contrast",
                details={"clip_limit": 2.5},
                timestamp=datetime.utcnow().isoformat()
            ))

        # Step 8: Denoising if noise variance is significant
        if metrics.noise_variance > 25.0:
            img = self.enhancer.denoise(img, strength=4.0)
            records.append(TransformationRecord(
                step="bilateral_denoise",
                details={"noise_variance": metrics.noise_variance},
                timestamp=datetime.utcnow().isoformat()
            ))

        return img, metrics, records
