import cv2
import numpy as np

class ImageEnhancer:
    @staticmethod
    def apply_clahe(image: np.ndarray, clip_limit: float = 2.0, tile_grid_size: tuple = (8, 8)) -> np.ndarray:
        """
        Applies Contrast Limited Adaptive Histogram Equalization.
        Enhances local contrast without over-amplifying noise.
        """
        clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=tile_grid_size)
        if len(image.shape) == 3:
            lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
            lab[:, :, 0] = clahe.apply(lab[:, :, 0])
            return cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)
        else:
            return clahe.apply(image)

    @staticmethod
    def normalize_illumination(image: np.ndarray) -> np.ndarray:
        """
        Normalizes uneven lighting and shadow using morphological background estimation and division.
        """
        is_color = len(image.shape) == 3
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if is_color else image

        # Morphological closing with large structuring element to approximate uneven background illumination
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (41, 41))
        background = cv2.morphologyEx(gray, cv2.MORPH_CLOSE, kernel)

        # Background division: (image / background) * 255
        divided = np.float32(gray) / (np.float32(background) + 1.0)
        norm_gray = np.clip(divided * 255.0, 0, 255).astype(np.uint8)

        if is_color:
            # Reconstruct color by applying illumination correction ratio to V channel in HSV
            hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
            hsv[:, :, 2] = norm_gray
            return cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)

        return norm_gray

    @staticmethod
    def denoise(image: np.ndarray, strength: float = 5.0) -> np.ndarray:
        """
        Applies bilateral filtering to suppress noise while keeping text boundaries sharp.
        """
        d = 7
        sigma_color = strength * 5.0
        sigma_space = strength * 5.0
        return cv2.bilateralFilter(image, d, sigma_color, sigma_space)

    @staticmethod
    def binarize_adaptive(image: np.ndarray) -> np.ndarray:
        """
        Adaptive Gaussian thresholding for high-contrast character segmentation.
        """
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
        return cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 21, 10
        )
