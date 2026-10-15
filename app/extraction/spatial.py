import re
from typing import List, Optional, Tuple
from app.models.ocr import OCRBox, BoundingBox

# Regex for internal template variable names (snake_case tokens like "claimed_amount")
_SNAKE_CASE_RE = re.compile(r'^[a-z][a-z0-9]*(_[a-z0-9]+)+$')

# Words that appear as field labels in blank forms and must never be treated as values
_FORM_LABEL_TOKENS = {
    "sla", "priority", "type", "standard", "urgent", "emergency",
    "tpa", "patient", "policy", "member", "claim", "hospital",
    "admission", "discharge", "diagnosis", "bank", "ifsc", "account",
    "doctor", "insurer", "rohini", "icd", "procedure", "bill",
    "amount", "date", "gender", "dob", "sex", "age", "name",
    "number", "id", "code", "record", "identity", "mandatory",
    "field", "preprocessing", "completed", "direct", "digital",
    "text", "or", "and", "card", "health", "use", "for", "the",
    "of", "only", "all", "data", "fictitious", "signature",
    "section", "details", "declaration", "original", "reg",
    "reimbursement", "summary", "proof",
}

# Known field label words that, when seen adjacent to a value candidate, should
# signal we have hit the next field's label column — stop collecting value words.
_LABEL_BREAKERS = {
    "policy", "member", "date", "age", "doctor", "priority",
    "total", "ifsc", "diagnosis", "hospital", "admission",
    "discharge", "claim", "bank", "account", "insurer", "tpa",
    "patient", "icd", "procedure", "bill", "rohini", "gender",
    "sex", "dob", "name", "number", "insurance", "section",
}


class SpatialExtractor:
    # ── Label detection ────────────────────────────────────────────────────────

    @staticmethod
    def _group_line_boxes(boxes: List[OCRBox]) -> List[List[OCRBox]]:
        """
        Clusters individual word-boxes into logical lines by y-center proximity.
        Returns list-of-lines, each line sorted left-to-right.
        """
        if not boxes:
            return []
        sorted_b = sorted(boxes, key=lambda b: (b.box.center[1], b.box.x_min))
        lines: List[List[OCRBox]] = []
        current: List[OCRBox] = []
        ref_y: float = -1.0

        for b in sorted_b:
            h = b.box.height or 20
            cy = b.box.center[1]
            if ref_y < 0 or abs(cy - ref_y) <= h * 0.7:
                current.append(b)
                ref_y = cy if ref_y < 0 else (ref_y + cy) / 2.0
            else:
                lines.append(sorted(current, key=lambda x: x.box.x_min))
                current = [b]
                ref_y = cy

        if current:
            lines.append(sorted(current, key=lambda x: x.box.x_min))
        return lines

    @classmethod
    def find_label_boxes(cls,
                         boxes: List[OCRBox],
                         label_aliases: List[str]) -> List[Tuple[OCRBox, str]]:
        """
        Locates the *last* box on a line whose cumulative line text matches an alias.

        Because PDF extraction splits labels into individual words
        (e.g. "Patient" and "Name" are two separate boxes), we:
          1. Group boxes into lines.
          2. Build the running text of each line left-to-right.
          3. Check whether any alias appears as a substring of that running text.
          4. When matched, return the rightmost box of the matched phrase so
             extract_spatial_value can look to the right of the whole label.
        """
        matches: List[Tuple[OCRBox, str]] = []
        lines = cls._group_line_boxes(boxes)

        # Estimate the page width from the rightmost box x_max
        page_width = max((b.box.x_max for b in boxes), default=800)
        label_col_limit = page_width * 0.65  # labels are in the left 65% of the page

        for line in lines:
            # Build cumulative text for the line left-to-right
            running = ""
            matched_this_line = False
            for i, box in enumerate(line):
                # Only consider boxes in the label column as potential label anchors
                if box.box.x_min > label_col_limit:
                    break  # rest of line is value column

                sep = " " if running else ""
                running += sep + box.text.strip().rstrip(":")

                running_lower = running.lower()
                if matched_this_line:
                    break  # already matched on this line
                for alias in label_aliases:
                    alias_clean = alias.lower().strip().rstrip(":")
                    if alias_clean in running_lower:
                        # anchor = current box (last word of the label phrase)
                        matches.append((box, alias))
                        matched_this_line = True
                        break

        return matches

    # ── Value retrieval ────────────────────────────────────────────────────────

    @staticmethod
    def get_candidate_boxes_right_of(label_box: OCRBox,
                                     all_boxes: List[OCRBox],
                                     max_horizontal_gap: int = 9999) -> List[OCRBox]:
        """
        Finds boxes on the same line to the RIGHT of label_box.

        Key design decisions:
        - max_horizontal_gap is intentionally very large (no pixel cap) because
          PDF-extracted coordinates are DPI-scaled and vary widely per document.
        - Instead, we stop collecting when we detect that the next word looks
          like a new field label (label_breakers) or has a colon suffix.
        - We DO enforce that candidates start strictly to the right of the
          label_box's x_max so we never pick up left-column labels.
        """
        ly_center = label_box.box.center[1]
        l_height = label_box.box.height or 25
        lx_max = label_box.box.x_max

        # All boxes on the same line, strictly to the right of the label anchor
        line_boxes = []
        for b in all_boxes:
            if b is label_box:
                continue
            by_center = b.box.center[1]
            bx_min = b.box.x_min
            if (abs(by_center - ly_center) <= l_height * 0.7
                    and bx_min > lx_max
                    and (bx_min - lx_max) <= max_horizontal_gap):
                line_boxes.append(b)

        line_boxes.sort(key=lambda b: b.box.x_min)

        candidates: List[OCRBox] = []
        prev_x_max = lx_max

        for b in line_boxes:
            txt = b.text.strip()
            txt_lower = txt.lower().rstrip(":")

            # Stop if the box is a new label (ends with ':', is a known field token)
            if txt.endswith(":"):
                break
            if txt_lower in _LABEL_BREAKERS:
                break

            # Allow large gaps between value words only when it's the first candidate
            # (to bridge the label-column ↔ value-column gap).
            # After the first value word, a wide gap means a new column — stop.
            if candidates:
                gap = b.box.x_min - prev_x_max
                # Use 2× the average word width as a reasonable inter-word gap ceiling
                avg_word_w = sum(c.box.width for c in candidates) / len(candidates)
                if gap > max(avg_word_w * 2, 40):
                    break

            candidates.append(b)
            prev_x_max = b.box.x_max

        return candidates

    @staticmethod
    def get_candidate_boxes_below(label_box: OCRBox,
                                  all_boxes: List[OCRBox],
                                  max_vertical_gap: int = 120) -> List[OCRBox]:
        """
        Finds boxes immediately below the label_box (stacked form layout).
        """
        lx_min = label_box.box.x_min
        lx_max = label_box.box.x_max
        ly_max = label_box.box.y_max

        candidates: List[OCRBox] = []
        for b in all_boxes:
            if b is label_box:
                continue
            bx_min = b.box.x_min
            bx_max = b.box.x_max
            by_min = b.box.y_min

            if by_min >= (ly_max - 5) and (by_min - ly_max) <= max_vertical_gap:
                overlap = max(0, min(lx_max, bx_max) - max(lx_min, bx_min))
                if overlap > 0 or abs(bx_min - lx_min) <= 60:
                    candidates.append(b)

        candidates.sort(key=lambda b: b.box.y_min)
        return candidates

    @classmethod
    def extract_spatial_value(cls,
                              label_box: OCRBox,
                              all_boxes: List[OCRBox]) -> Tuple[str, float, Optional[BoundingBox]]:
        """
        Associates value right-of or below the label.
        Returns (extracted_text, combined_confidence, combined_bounding_box).
        """
        right_candidates = cls.get_candidate_boxes_right_of(label_box, all_boxes)
        chosen = right_candidates if right_candidates else cls.get_candidate_boxes_below(label_box, all_boxes)

        if not chosen:
            return "", 0.0, None

        text = " ".join(b.text for b in chosen).strip().lstrip(":").strip()
        conf = sum(b.confidence for b in chosen) / len(chosen)

        # Reject junk / template label values
        if cls._is_junk_value(text):
            return "", 0.0, None

        combined_box = BoundingBox(
            x_min=min(b.box.x_min for b in chosen),
            y_min=min(b.box.y_min for b in chosen),
            x_max=max(b.box.x_max for b in chosen),
            y_max=max(b.box.y_max for b in chosen)
        )
        return text, conf, combined_box

    @staticmethod
    def _is_junk_value(text: str) -> bool:
        """
        Returns True when the extracted text looks like a form label / template
        variable rather than a real data value.
        """
        if not text:
            return True

        stripped = text.strip()

        # Reject values that start with punctuation-only tokens (e.g. '/ Health Card')
        if stripped.startswith('/'):
            return True

        words = stripped.lower().split()

        # Reject pure snake_case template tokens (e.g. "claimed_amount total_bill_amount")
        if all(_SNAKE_CASE_RE.match(w) for w in words):
            return True

        # Reject if every word is a known form-label token
        if all(w.strip("()[].,;:/") in _FORM_LABEL_TOKENS for w in words):
            return True

        # Reject very short all-caps single words that are likely column headers
        if len(words) == 1 and words[0].isupper() and len(words[0]) <= 5:
            return True

        return False
