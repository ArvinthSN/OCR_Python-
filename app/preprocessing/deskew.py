import cv2
import numpy as np
from typing import Tuple

class ImageDeskewer:
    @staticmethod
    def estimate_skew_angle(image: np.ndarray) -> float:
        """
        Estimates skew angle between -45 and +45 degrees using Hough line transform
        and edge orientation statistics.
        """
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image.copy()

        # Edge detection with Canny
        edges = cv2.Canny(gray, 50, 150, apertureSize=3)

        # Probabilistic Hough Line Transform to detect text line baselines
        lines = cv2.HoughLinesP(edges, 1, np.pi / 180, threshold=100, minLineLength=50, maxLineGap=10)
        if lines is None or len(lines) == 0:
            return 0.0

        angles = []
        for line in lines:
            coords = line[0] if (hasattr(line, "ndim") and line.ndim > 1) else line
            if len(coords) < 4:
                continue
            x1, y1, x2, y2 = int(coords[0]), int(coords[1]), int(coords[2]), int(coords[3])
            dx = x2 - x1
            dy = y2 - y1
            if dx == 0:
                continue
            angle_rad = np.arctan2(dy, dx)
            angle_deg = np.degrees(angle_rad)
            # Only consider angles roughly near horizontal (-45 to 45 degrees)
            if -45.0 <= angle_deg <= 45.0:
                angles.append(angle_deg)

        if not angles:
            return 0.0

        # Use median angle to reject outliers
        median_angle = float(np.median(angles))
        # Ignore negligible skew (< 0.5 deg)
        if abs(median_angle) < 0.5:
            return 0.0

        return median_angle

    @staticmethod
    def rotate_bound(image: np.ndarray, angle: float) -> np.ndarray:
        """
        Rotates an image by an arbitrary angle while expanding the canvas
        so that no content is cropped.
        """
        if abs(angle) < 0.2:
            return image

        h, w = image.shape[:2]
        center = (w / 2.0, h / 2.0)

        # Rotation matrix
        rot_mat = cv2.getRotationMatrix2D(center, angle, 1.0)
        cos = np.abs(rot_mat[0, 0])
        sin = np.abs(rot_mat[0, 1])

        # Compute new bounding dimensions
        new_w = int((h * sin) + (w * cos))
        new_h = int((h * cos) + (w * sin))

        # Adjust the rotation matrix to take into account translation
        rot_mat[0, 2] += (new_w / 2.0) - center[0]
        rot_mat[1, 2] += (new_h / 2.0) - center[1]

        # Use white border for clean document background
        border_color = (255, 255, 255) if len(image.shape) == 3 else 255

        return cv2.warpAffine(
            image,
            rot_mat,
            (new_w, new_h),
            flags=cv2.INTER_CUBIC,
            borderMode=cv2.BORDER_CONSTANT,
            borderValue=border_color
        )
