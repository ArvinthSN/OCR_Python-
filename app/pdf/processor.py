import os
from pathlib import Path
from typing import List, Tuple, Optional
import fitz  # PyMuPDF
from PIL import Image

from app.config import settings
from app.models.document import DocumentPage, ProcessingStatus
from app.models.ocr import OCRResult, OCRBox, BoundingBox, ExtractionMethod

class PDFProcessor:
    def __init__(self, dpi: int = settings.PDF_RENDER_DPI):
        self.dpi = dpi

    def is_page_text_usable(self, page: fitz.Page) -> Tuple[bool, str, List[OCRBox]]:
        """
        Determines whether a PDF page has usable digital text.
        Returns (is_usable, full_text, list_of_ocr_boxes).
        """
        rect = page.rect
        page_area = (rect.width / 72.0) * (rect.height / 72.0)  # square inches
        if page_area <= 0:
            return False, "", []

        # Extract words with coordinates: (x0, y0, x1, y1, word, block_no, line_no, word_no)
        words = page.get_text("words")
        if not words:
            return False, "", []

        full_text = page.get_text("text").strip()
        non_whitespace_chars = sum(len(w[4]) for w in words)
        char_density = non_whitespace_chars / max(1.0, page_area)

        # Check for garbled text (high non-printable ratio or replacement characters)
        if len(full_text) > 0:
            unprintable_count = sum(1 for c in full_text if ord(c) < 32 and c not in '\n\r\t')
            replacement_count = full_text.count('\ufffd')
            if (unprintable_count + replacement_count) / max(1, len(full_text)) > 0.15:
                return False, "", []

        # If character density is high enough and words are present, consider it usable digital text
        if char_density < settings.PDF_TEXT_USABLE_MIN_CHAR_DENSITY or len(words) < 5:
            return False, "", []

        # Build OCRBox structures with coordinates scaled to target rendering DPI for consistency
        scale = self.dpi / 72.0
        ocr_boxes: List[OCRBox] = []
        for w in words:
            x0, y0, x1, y1, text, block_no, line_no, word_no = w
            box = BoundingBox(
                x_min=int(x0 * scale),
                y_min=int(y0 * scale),
                x_max=int(x1 * scale),
                y_max=int(y1 * scale)
            )
            polygon = [
                [box.x_min, box.y_min],
                [box.x_max, box.y_min],
                [box.x_max, box.y_max],
                [box.x_min, box.y_max],
            ]
            ocr_boxes.append(
                OCRBox(
                    text=text,
                    confidence=1.0,  # Digital text has 1.0 confidence
                    polygon=polygon,
                    box=box,
                    page_number=page.number + 1,
                    line_number=line_no
                )
            )

        return True, full_text, ocr_boxes

    def render_page_to_image(self, page: fitz.Page, output_path: str) -> Tuple[int, int]:
        """
        Renders a PDF page to a high-resolution PNG image at the configured DPI.
        Returns (width, height) of rendered image.
        """
        zoom = self.dpi / 72.0
        matrix = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=matrix, alpha=False)
        pix.save(output_path)
        return pix.width, pix.height

    def process_pdf(self, pdf_path: str, source_filename: str) -> List[Tuple[DocumentPage, Optional[OCRResult]]]:
        """
        Processes a PDF file page-by-page.
        For digital text pages, extracts text directly.
        For scanned/image-only pages, renders them to image files for subsequent OCR.
        """
        doc = fitz.open(pdf_path)
        results: List[Tuple[DocumentPage, Optional[OCRResult]]] = []

        output_dir = settings.PROCESSED_DIR / Path(source_filename).stem
        output_dir.mkdir(parents=True, exist_ok=True)

        for page_index in range(len(doc)):
            page = doc[page_index]
            page_num = page_index + 1
            rendered_image_path = str(output_dir / f"page_{page_num}_orig.png")

            # Always render the image for frontend preview and visual evidence
            w, h = self.render_page_to_image(page, rendered_image_path)

            is_usable, digital_text, ocr_boxes = self.is_page_text_usable(page)

            doc_page = DocumentPage(
                page_number=page_num,
                source_filename=source_filename,
                original_image_path=rendered_image_path,
                enhanced_image_path=rendered_image_path,
                width=w,
                height=h,
                is_digital_pdf_page=is_usable,
                raw_text=digital_text if is_usable else "",
                status=ProcessingStatus.COMPLETED if is_usable else ProcessingStatus.PENDING
            )

            ocr_res = None
            if is_usable:
                ocr_res = OCRResult(
                    boxes=ocr_boxes,
                    full_text=digital_text,
                    mean_confidence=1.0,
                    low_confidence_ratio=0.0,
                    engine="pymupdf_direct",
                    profile_used="direct_digital_text",
                    extraction_method=ExtractionMethod.DIRECT_PDF_TEXT,
                    rotation_applied=0,
                    enhancement_applied=[]
                )

            results.append((doc_page, ocr_res))

        doc.close()
        return results
