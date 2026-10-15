import re
from typing import List, Dict, Any, Optional
from app.models.ocr import OCRBox, OCRResult
from app.models.fields import LineItem, FieldStatus
from app.validation.rules import DomainValidator

class TableExtractor:
    @staticmethod
    def extract_line_items(ocr_result: OCRResult) -> List[LineItem]:
        """
        Reconstructs itemized bill tables by clustering OCR boxes into rows and columns.
        Extracts description, quantity, rate, and amount for each line item.
        """
        if not ocr_result.boxes:
            return []

        # Find candidate table rows: lines containing a description and an amount at the end
        lines_dict: Dict[int, List[OCRBox]] = {}
        for b in ocr_result.boxes:
            lines_dict.setdefault(b.line_number, []).append(b)

        line_items: List[LineItem] = []
        item_counter = 1

        for line_no, boxes in sorted(lines_dict.items()):
            boxes_sorted = sorted(boxes, key=lambda b: b.box.x_min)
            line_text = " ".join(b.text for b in boxes_sorted)

            # Skip header lines
            lower_text = line_text.lower()
            if any(h in lower_text for h in ["description", "particulars", "sl no", "qty", "rate", "subtotal", "total amount"]):
                continue

            # Look for numeric amounts (e.g., at end of line)
            # Find numbers with decimals or commas
            tokens = line_text.split()
            if len(tokens) < 2:
                continue

            # Try parsing the last token or second to last token as amount
            amount_val = None
            rate_val = 0.0
            qty_val = 1.0
            desc_tokens = []

            for i in range(len(tokens) - 1, -1, -1):
                val, err = DomainValidator.parse_indian_amount(tokens[i])
                if val is not None and val > 0 and amount_val is None:
                    amount_val = val
                elif val is not None and val > 0 and amount_val is not None and rate_val == 0.0:
                    rate_val = val
                else:
                    desc_tokens = tokens[:i + 1]
                    break

            if amount_val is not None and desc_tokens:
                desc = " ".join(desc_tokens).strip()
                # Clean leading serial numbers (e.g. "1. ", "2) ")
                desc = re.sub(r"^\d+[\.\)\-]\s*", "", desc)

                if len(desc) >= 3 and not re.match(r"^(total|grand total|net amount|sub total)", desc, re.I):
                    line_items.append(
                        LineItem(
                            item_id=f"ITEM-{item_counter:03d}",
                            description=desc,
                            quantity=qty_val,
                            unit_rate=rate_val or amount_val,
                            amount=amount_val,
                            confidence=sum(b.confidence for b in boxes_sorted) / len(boxes_sorted),
                            status=FieldStatus.EXTRACTED
                        )
                    )
                    item_counter += 1

        return line_items
