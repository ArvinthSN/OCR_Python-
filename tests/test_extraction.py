import pytest
from app.extraction.character_correction import ContextCharacterCorrector
from app.extraction.spatial import SpatialExtractor
from app.extraction.table_extractor import TableExtractor
from app.extraction.claim_extractor import ClaimExtractor
from app.models.ocr import OCRBox, OCRResult, BoundingBox, ExtractionMethod
from app.models.document import ProcessedDocument, DocumentPage, DocumentType

def test_context_character_correction():
    corrector = ContextCharacterCorrector()

    # Digits with letter O and l
    corrected, audit = corrector.correct_numeric_field("l25OOO")
    assert corrected == "125000"
    assert len(audit) == 4

    # IFSC code: HDFCO001234 -> HDFC0001234
    ifsc_corr, ifsc_audit = corrector.correct_ifsc_field("HDFCO001234")
    assert ifsc_corr == "HDFC0001234"
    assert len(ifsc_audit) == 1

def test_spatial_extraction():
    # Label: "PATIENT NAME:" at x=50, y=100
    # Value: "ARJUN SHARMA" at x=250, y=100 (same line, to the right)
    label_box = OCRBox(
        text="PATIENT NAME:",
        confidence=0.99,
        box=BoundingBox(x_min=50, y_min=90, x_max=220, y_max=120)
    )
    val_box_1 = OCRBox(
        text="ARJUN",
        confidence=0.98,
        box=BoundingBox(x_min=240, y_min=90, x_max=320, y_max=120)
    )
    val_box_2 = OCRBox(
        text="SHARMA",
        confidence=0.97,
        box=BoundingBox(x_min=330, y_min=90, x_max=430, y_max=120)
    )

    all_boxes = [label_box, val_box_1, val_box_2]
    val, conf, bbox = SpatialExtractor.extract_spatial_value(label_box, all_boxes)

    assert val == "ARJUN SHARMA"
    assert conf > 0.95
    assert bbox.x_min == 240
    assert bbox.x_max == 430

def test_table_line_items_extraction():
    # Table rows with description and amount
    boxes = [
        OCRBox(text="1", confidence=0.99, box=BoundingBox(x_min=50, y_min=200, x_max=70, y_max=225), line_number=1),
        OCRBox(text="Room Rent Charges", confidence=0.99, box=BoundingBox(x_min=100, y_min=200, x_max=350, y_max=225), line_number=1),
        OCRBox(text="20000.00", confidence=0.99, box=BoundingBox(x_min=500, y_min=200, x_max=600, y_max=225), line_number=1),

        OCRBox(text="2", confidence=0.99, box=BoundingBox(x_min=50, y_min=250, x_max=70, y_max=275), line_number=2),
        OCRBox(text="Surgeon Consultation", confidence=0.99, box=BoundingBox(x_min=100, y_min=250, x_max=350, y_max=275), line_number=2),
        OCRBox(text="15000.00", confidence=0.99, box=BoundingBox(x_min=500, y_min=250, x_max=600, y_max=275), line_number=2),
    ]

    ocr_res = OCRResult(boxes=boxes, full_text="", mean_confidence=0.99)
    items = TableExtractor.extract_line_items(ocr_res)

    assert len(items) == 2
    assert "Room Rent" in items[0].description
    assert items[0].amount == 20000.0
    assert "Surgeon Consultation" in items[1].description
    assert items[1].amount == 15000.0

def test_full_claim_extraction_summary():
    extractor = ClaimExtractor()

    # Mock OCR result containing key health claim labels and values
    text_boxes = [
        OCRBox(text="PATIENT NAME:", confidence=0.99, box=BoundingBox(x_min=50, y_min=50, x_max=200, y_max=80), line_number=1),
        OCRBox(text="ARJUN SHARMA", confidence=0.98, box=BoundingBox(x_min=220, y_min=50, x_max=380, y_max=80), line_number=1),

        OCRBox(text="POLICY NUMBER:", confidence=0.99, box=BoundingBox(x_min=50, y_min=100, x_max=200, y_max=130), line_number=2),
        OCRBox(text="POL-8829104", confidence=0.98, box=BoundingBox(x_min=220, y_min=100, x_max=380, y_max=130), line_number=2),

        OCRBox(text="HOSPITAL NAME:", confidence=0.99, box=BoundingBox(x_min=50, y_min=150, x_max=200, y_max=180), line_number=3),
        OCRBox(text="APOLLO HOSPITALS", confidence=0.98, box=BoundingBox(x_min=220, y_min=150, x_max=420, y_max=180), line_number=3),

        OCRBox(text="TREATING DOCTOR:", confidence=0.99, box=BoundingBox(x_min=50, y_min=200, x_max=200, y_max=230), line_number=4),
        OCRBox(text="DR. RAJESH GUPTA", confidence=0.98, box=BoundingBox(x_min=220, y_min=200, x_max=420, y_max=230), line_number=4),

        OCRBox(text="ADMISSION DATE:", confidence=0.99, box=BoundingBox(x_min=50, y_min=250, x_max=200, y_max=280), line_number=5),
        OCRBox(text="10/02/2025", confidence=0.98, box=BoundingBox(x_min=220, y_min=250, x_max=350, y_max=280), line_number=5),

        OCRBox(text="DISCHARGE DATE:", confidence=0.99, box=BoundingBox(x_min=50, y_min=300, x_max=200, y_max=330), line_number=6),
        OCRBox(text="14/02/2025", confidence=0.98, box=BoundingBox(x_min=220, y_min=300, x_max=350, y_max=330), line_number=6),

        OCRBox(text="TOTAL BILL AMOUNT:", confidence=0.99, box=BoundingBox(x_min=50, y_min=350, x_max=240, y_max=380), line_number=7),
        OCRBox(text="1,25,000.00", confidence=0.98, box=BoundingBox(x_min=260, y_min=350, x_max=390, y_max=380), line_number=7),
    ]

    ocr_res = OCRResult(boxes=text_boxes, full_text="", mean_confidence=0.98)
    doc = ProcessedDocument(
        document_id="doc1",
        original_filename="final_bill.png",
        sanitized_filename="final_bill.png",
        file_type="png",
        mime_type="image/png",
        file_size_bytes=1000,
        classification=DocumentType.FINAL_BILL
    )
    page = DocumentPage(page_number=1, source_filename="final_bill.png")

    claim_data = extractor.extract_from_documents([doc], {"doc1": [(page, ocr_res)]})

    # Verify that summary and all requested fields are cleanly populated
    s = claim_data.summary
    assert s.name == "ARJUN SHARMA"
    assert s.id == "POL-8829104"
    assert s.hospital_name == "APOLLO HOSPITALS"
    assert s.admission_name == "DR. RAJESH GUPTA"
    assert s.admission_date == "2025-02-10"
    assert s.discharge_date == "2025-02-14"
    assert s.billed == 125000.0
    assert s.priority_type in ("Standard", "Urgent")
    assert s.stage_status is not None
    assert s.assignee is not None
    assert s.received is not None
