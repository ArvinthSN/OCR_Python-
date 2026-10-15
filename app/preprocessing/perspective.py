import cv2
import numpy as np
from typing import Optional, Tuple

class PerspectiveCorrector:
    @staticmethod
    def order_points(pts: np.ndarray) -> np.ndarray:
        """Orders points: top-left, top-right, bottom-right, bottom-left."""
        rect = np.zeros((4, 2), dtype="float32")
        s = pts.sum(axis=1)
        rect[0] = pts[np.argmin(s)]
        rect[2] = pts[np.argmax(s)]

        diff = np.diff(pts, axis=1)
        rect[1] = pts[np.argmin(diff)]
        rect[3] = pts[np.argmax(diff)]
        return rect

    @classmethod
    def correct_perspective(cls, image: np.ndarray) -> Tuple[np.ndarray, bool]:
        """
        Attempts to detect quadrilateral document contour and warp to top-down view.
        Returns (transformed_image, was_corrected).
        """
        h, w = image.shape[:2]
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image

        # Gaussian blur + edge detection
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        edged = cv2.Canny(blurred, 75, 200)

        # Find contours
        contours, _ = cv2.findContours(edged, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
        contours = sorted(contours, key=cv2.contourArea, reverse=True)[:5]

        doc_contour = None
        for c in contours:
            peri = cv2.arcLength(c, True)
            approx = cv2.approxPolyDP(c, 0.02 * peri, True)
            # If 4 points and area covers at least 30% of image area, accept as document
            if len(approx) == 4 and cv2.contourArea(c) > (0.30 * h * w):
                doc_contour = approx
                break

        if doc_contour is None:
            return image, False

        # Apply perspective transform
        pts = doc_contour.reshape(4, 2)
        rect = cls.order_points(pts)
        (tl, tr, br, bl) = rect

        # Width of new image
        width_a = np.sqrt(((br[0] - bl[0]) ** 2) + ((br[1] - bl[1]) ** 2))
        width_b = np.sqrt(((tr[0] - tl[0]) ** 2) + ((tr[1] - tl[1]) ** 2))
        max_width = max(int(width_a), int(width_b))

        # Height of new image
        height_a = np.sqrt(((tr[0] - br[0]) ** 2) + ((tr[1] - br[1]) ** 2))
        height_b = np.sqrt(((tl[0] - bl[0]) ** 2) + ((tl[1] - bl[1]) ** 2))
        max_height = max(int(height_a), int(height_b))

        if max_width < 100 or max_height < 100:
            return image, False

        dst = np.array([
            [0, 0],
            [max_width - 1, 0],
            [max_width - 1, max_height - 1],
            [0, max_height - 1]
        ], dtype="float32")

        matrix = cv2.getPerspectiveTransform(rect, dst)
        warped = cv2.warpPerspective(image, matrix, (max_width, max_height), flags=cv2.INTER_CUBIC)
        return warped, True
