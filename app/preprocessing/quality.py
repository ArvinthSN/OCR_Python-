import cv2
import numpy as np
from app.models.document import QualityMetrics
from app.config import settings

class ImageQualityAssessor:
    @staticmethod
    def assess(image: np.ndarray) -> QualityMetrics:
        """
        Computes multiple image quality metrics:
        - Sharpness: Laplacian variance and Tenengrad (Sobel energy)
        - Blur type: Directional gradient anisotropy (motion blur vs defocus blur)
        - Noise level: Local variance of difference from Gaussian smoothed image
        - Contrast: RMS contrast
        - Brightness: Mean intensity
        """
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image.copy()

        h, w = gray.shape

        # 1. Sharpness: Variance of Laplacian
        laplacian = cv2.Laplacian(gray, cv2.CV_64F)
        var_laplacian = float(laplacian.var())

        # 2. Tenengrad gradient energy (Sobel-based)
        sobel_x = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
        sobel_y = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
        grad_mag_sq = sobel_x**2 + sobel_y**2
        tenengrad = float(np.mean(grad_mag_sq))

        # 3. Blur type estimation via Directional Gradient Anisotropy
        # Motion blur has strong gradient perpendicular to motion and weak gradient parallel to motion
        mean_gx2 = float(np.mean(sobel_x**2))
        mean_gy2 = float(np.mean(sobel_y**2))
        max_g = max(mean_gx2, mean_gy2)
        min_g = max(1e-5, min(mean_gx2, mean_gy2))
        anisotropy_ratio = max_g / min_g

        is_blurred = var_laplacian < settings.BLUR_LAPLACIAN_THRESHOLD
        blur_type = "none"
        if is_blurred:
            # If gradients in one direction dominate significantly (> 2.5), classify as motion blur
            blur_type = "motion" if anisotropy_ratio > 2.5 else "defocus"

        # 4. Noise variance estimation
        # High-frequency noise estimated from difference with bilateral/gaussian filter
        blurred_gray = cv2.GaussianBlur(gray, (5, 5), 0)
        noise_diff = gray.astype(np.float32) - blurred_gray.astype(np.float32)
        noise_variance = float(np.var(noise_diff))

        # 5. Contrast and Brightness
        contrast_score = float(gray.std())
        brightness_score = float(gray.mean())

        return QualityMetrics(
            resolution=(w, h),
            sharpness_laplacian=var_laplacian,
            sharpness_sobel=tenengrad,
            is_blurred=is_blurred,
            blur_type=blur_type,
            noise_variance=noise_variance,
            contrast_score=contrast_score,
            brightness_score=brightness_score,
            skew_angle=0.0,
            detected_rotation=0
        )
