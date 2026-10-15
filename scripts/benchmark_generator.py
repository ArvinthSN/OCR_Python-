import os
import json
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from pathlib import Path
from typing import Dict, Any, List

from scripts.synthetic_data import SYNTHETIC_CLAIMS
from app.preprocessing.deskew import ImageDeskewer

class BenchmarkGenerator:
    def __init__(self, output_dir: str = "data/benchmark"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.deskewer = ImageDeskewer()

    def render_clean_document(self, claim: Dict[str, Any], doc_type: str = "final_bill") -> np.ndarray:
        """
        Renders a realistic synthetic health claim document (1000x1400 px).
        """
        w, h = 1000, 1400
        img = Image.new("RGB", (w, h), color=(255, 255, 255))
        draw = ImageDraw.Draw(img)

        # Draw Header
        draw.rectangle([30, 30, w - 30, 120], fill=(240, 245, 255), outline=(30, 64, 175), width=2)
        draw.text((50, 45), claim["hospital_name"].upper(), fill=(30, 64, 175))
        title = "INPATIENT FINAL BILL & DISCHARGE INVOICE" if doc_type == "final_bill" else "HOSPITAL DISCHARGE SUMMARY"
        draw.text((50, 70), title, fill=(15, 23, 42))
        draw.text((50, 95), "ROHINI ID: ROH-77821 | GSTIN: 07AAAAA0000A1Z5", fill=(100, 116, 139))

        # Patient Info Grid Box
        draw.rectangle([30, 140, w - 30, 360], outline=(200, 210, 225), width=2)
        y = 155
        draw.text((50, y), f"PATIENT NAME: {claim['patient_name']}", fill=(0, 0, 0))
        draw.text((520, y), f"POLICY NO: {claim['policy_number']}", fill=(0, 0, 0))
        y += 35
        draw.text((50, y), f"AGE / GENDER: {claim['patient_age']} YRS / {claim['patient_gender']}", fill=(0, 0, 0))
        draw.text((520, y), f"MEMBER ID: {claim['member_id']}", fill=(0, 0, 0))
        y += 35
        draw.text((50, y), f"DATE OF ADMISSION: {claim['admission_date']}", fill=(0, 0, 0))
        draw.text((520, y), f"DATE OF DISCHARGE: {claim['discharge_date']}", fill=(0, 0, 0))
        y += 35
        draw.text((50, y), f"TREATING DOCTOR: {claim['admission_name']}", fill=(0, 0, 0))
        draw.text((520, y), f"PRIORITY: {claim['priority_type'].upper()}", fill=(0, 0, 0))
        y += 35
        draw.text((50, y), f"DIAGNOSIS: {claim['diagnosis']} (ICD-10: {claim['icd10_code']})", fill=(0, 0, 0))
        draw.text((520, y), f"PROCEDURE: {claim['procedure_name']}", fill=(0, 0, 0))

        # Itemized Bill Table
        y_table = 380
        draw.rectangle([30, y_table, w - 30, y_table + 30], fill=(230, 235, 245))
        draw.text((50, y_table + 7), "SL", fill=(0, 0, 0))
        draw.text((100, y_table + 7), "DESCRIPTION", fill=(0, 0, 0))
        draw.text((600, y_table + 7), "QTY", fill=(0, 0, 0))
        draw.text((700, y_table + 7), "RATE (RS)", fill=(0, 0, 0))
        draw.text((830, y_table + 7), "AMOUNT (RS)", fill=(0, 0, 0))

        y_row = y_table + 40
        for idx, item in enumerate(claim.get("line_items", []), start=1):
            draw.text((50, y_row), str(idx), fill=(0, 0, 0))
            draw.text((100, y_row), item["description"], fill=(0, 0, 0))
            draw.text((600, y_row), str(item["qty"]), fill=(0, 0, 0))
            draw.text((700, y_row), f"{item['rate']:,.2f}", fill=(0, 0, 0))
            draw.text((830, y_row), f"{item['amount']:,.2f}", fill=(0, 0, 0))
            y_row += 30

        # Total Amount Box
        draw.rectangle([30, y_row + 15, w - 30, y_row + 65], fill=(245, 245, 250), outline=(200, 210, 225), width=2)
        draw.text((520, y_row + 28), "TOTAL BILL AMOUNT: ", fill=(0, 0, 0))
        draw.text((780, y_row + 28), f"Rs. {claim['total_bill_amount']:,.2f}", fill=(30, 64, 175))

        # Bank Info Footer
        y_foot = y_row + 85
        draw.rectangle([30, y_foot, w - 30, y_foot + 90], outline=(220, 220, 220))
        draw.text((50, y_foot + 15), f"BANK NAME: HDFC BANK | IFSC CODE: {claim['ifsc_code']}", fill=(50, 50, 50))
        draw.text((50, y_foot + 45), f"A/C NO: {claim['bank_account_number']} | A/C HOLDER: {claim['patient_name']}", fill=(50, 50, 50))

        # Convert PIL to OpenCV BGR
        np_img = np.array(img)
        return cv2.cvtColor(np_img, cv2.COLOR_RGB2BGR)

    def apply_degradation(self, image: np.ndarray, degradation_type: str, severity: Any) -> np.ndarray:
        """
        Applies controlled synthetic degradation:
        - rotation: 90, 180, 270, 7, 15, 30
        - gaussian_blur: sigma 1.5, 3.0, 5.0
        - motion_blur: length 9, 15
        - noise: variance
        - low_contrast
        - rotated_and_blurred
        """
        deg_img = image.copy()

        if degradation_type == "rotation":
            angle = float(severity)
            if angle in (90.0, 180.0, 270.0):
                if angle == 90.0:
                    deg_img = cv2.rotate(deg_img, cv2.ROTATE_90_CLOCKWISE)
                elif angle == 180.0:
                    deg_img = cv2.rotate(deg_img, cv2.ROTATE_180)
                elif angle == 270.0:
                    deg_img = cv2.rotate(deg_img, cv2.ROTATE_90_COUNTERCLOCKWISE)
            else:
                deg_img = self.deskewer.rotate_bound(deg_img, angle)

        elif degradation_type == "gaussian_blur":
            sigma = float(severity)
            ksize = int(2 * round(3 * sigma) + 1)
            deg_img = cv2.GaussianBlur(deg_img, (ksize, ksize), sigma)

        elif degradation_type == "motion_blur":
            length = int(severity)
            kernel = np.zeros((length, length))
            kernel[int((length - 1) / 2), :] = np.ones(length)
            kernel /= length
            deg_img = cv2.filter2D(deg_img, -1, kernel)

        elif degradation_type == "noise":
            noise_sigma = float(severity)
            gauss = np.random.normal(0, noise_sigma, deg_img.shape).astype(np.float32)
            noisy = deg_img.astype(np.float32) + gauss
            deg_img = np.clip(noisy, 0, 255).astype(np.uint8)

        elif degradation_type == "low_contrast":
            # Scale intensity range
            deg_img = (deg_img.astype(np.float32) * 0.4 + 100).astype(np.uint8)

        elif degradation_type == "rotated_and_blurred":
            # 90 degrees rotation + Gaussian blur
            deg_img = cv2.rotate(deg_img, cv2.ROTATE_90_CLOCKWISE)
            deg_img = cv2.GaussianBlur(deg_img, (7, 7), 2.0)

        return deg_img

    def generate_benchmark_suite(self) -> str:
        """
        Generates full test suite of degraded documents and ground-truth metadata.
        """
        manifest = []
        claim = SYNTHETIC_CLAIMS[0]
        clean_img = self.render_clean_document(claim)

        # Test conditions covering rotation (0, 15, 90, 180), defocus blur, motion blur, and combined
        conditions = [
            ("clean", 0),
            ("rotation", 90),
            ("rotation", 180),
            ("rotation", 15),
            ("gaussian_blur", 2.0),
            ("motion_blur", 9),
            ("rotated_and_blurred", 90),
        ]

        for deg_type, sev in conditions:
            degraded = self.apply_degradation(clean_img, deg_type, sev)
            filename = f"bench_{deg_type}_{str(sev).replace('.', '_')}.png"
            file_path = self.output_dir / filename
            cv2.imwrite(str(file_path), degraded)

            manifest.append({
                "filename": filename,
                "file_path": str(file_path),
                "degradation_type": deg_type,
                "severity": sev,
                "ground_truth": claim
            })

        manifest_path = self.output_dir / "benchmark_manifest.json"
        with open(manifest_path, "w") as f:
            json.dump(manifest, f, indent=2)

        return str(manifest_path)

if __name__ == "__main__":
    gen = BenchmarkGenerator()
    p = gen.generate_benchmark_suite()
    print(f"Benchmark suite generated at: {p}")
