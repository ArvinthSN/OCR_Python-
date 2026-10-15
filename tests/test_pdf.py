import pytest
import fitz
from pathlib import Path
from app.pdf.processor import PDFProcessor

def test_pdf_digital_text_and_rendering(tmp_path):
    # Create a synthetic digital PDF using PyMuPDF
    pdf_path = tmp_path / "digital_claim.pdf"
    doc = fitz.open()
    page = doc.new_page(width=595, height=842) # A4
    page.insert_text((50, 72), "PATIENT NAME: ARJUN SHARMA\nPOLICY NO: POL-882910\nHOSPITAL: APOLLO HOSPITAL\nTOTAL: 1,25,000", fontsize=12)
    doc.save(str(pdf_path))
    doc.close()

    processor = PDFProcessor(dpi=150)
    results = processor.process_pdf(str(pdf_path), "digital_claim.pdf")

    assert len(results) == 1
    doc_page, ocr_res = results[0]

    # Verify that usable digital text was extracted directly without needing heavy OCR
    assert doc_page.is_digital_pdf_page is True
    assert "ARJUN SHARMA" in doc_page.raw_text
    assert ocr_res is not None
    assert ocr_res.engine == "pymupdf_direct"
    assert len(ocr_res.boxes) > 0
    assert Path(doc_page.original_image_path).exists()
