import re
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any

from app.models.document import DocumentType, ProcessedDocument, DocumentPage
from app.models.ocr import OCRResult, OCRBox, BoundingBox, ExtractionMethod
from app.models.fields import ExtractedField, FieldStatus, CandidateValue, LineItem
from app.models.claim import HealthClaimData, ClaimSummaryFields
from app.extraction.schemas import CLAIM_FIELD_SCHEMAS, FieldSchema
from app.extraction.spatial import SpatialExtractor
from app.extraction.table_extractor import TableExtractor
from app.extraction.character_correction import ContextCharacterCorrector
from app.validation.rules import DomainValidator
from app.validation.verhoeff import mask_aadhaar, mask_bank_account
from app.validation.warnings import WarningGenerator
from app.config import settings

class ClaimExtractor:
    def __init__(self):
        self.spatial = SpatialExtractor()
        self.table_extractor = TableExtractor()
        self.corrector = ContextCharacterCorrector()
        self.validator = DomainValidator()
        self.warner = WarningGenerator()

    def extract_from_documents(self,
                               documents: List[ProcessedDocument],
                               doc_ocr_results: Dict[str, List[Tuple[DocumentPage, Optional[OCRResult]]]]) -> HealthClaimData:
        """
        Extracts structured claim data from all processed documents and pages.
        """
        extracted_fields: Dict[str, ExtractedField] = {}
        all_line_items: List[LineItem] = []
        audit_records: List[Dict[str, Any]] = []

        # Iterate over defined schemas
        for field_name, schema in CLAIM_FIELD_SCHEMAS.items():
            candidates: List[CandidateValue] = []

            for doc in documents:
                pages_and_ocr = doc_ocr_results.get(doc.document_id, [])
                for page, ocr_res in pages_and_ocr:
                    if not ocr_res or not ocr_res.boxes:
                        continue

                    # Try spatial extraction
                    val, raw_val, conf, box, method, corrections = self._extract_single_candidate(
                        ocr_res, schema, page.source_filename, page.page_number
                    )

                    if val:
                        # Validate candidate
                        is_valid, norm_val, err_msg = self._validate_field_value(field_name, val, schema.field_type)
                        cand = CandidateValue(
                            value=norm_val if is_valid else val,
                            raw_value=raw_val,
                            confidence=conf,
                            source_filename=page.source_filename,
                            page_number=page.page_number,
                            bounding_box=box,
                            extraction_method=method,
                            engine=ocr_res.engine,
                            preprocessed_profile=ocr_res.profile_used,
                            validation_passed=is_valid,
                            validation_error=err_msg
                        )
                        candidates.append(cand)

            # Resolve best candidate for field
            field_obj = self._resolve_field(field_name, schema, candidates)
            extracted_fields[field_name] = field_obj

        # Extract table line items from final bills
        for doc in documents:
            pages_and_ocr = doc_ocr_results.get(doc.document_id, [])
            for page, ocr_res in pages_and_ocr:
                if ocr_res and doc.classification in (DocumentType.FINAL_BILL, DocumentType.PHARMACY_BILL, DocumentType.UNKNOWN):
                    items = self.table_extractor.extract_line_items(ocr_res)
                    if items:
                        all_line_items.extend(items)

        # Cross-field validations and derive summary
        summary = self._build_claim_summary(extracted_fields, all_line_items, documents)
        
        # Build warnings list
        warnings_list: List[str] = []
        for fn, fld in extracted_fields.items():
            if fld.warning_message:
                warnings_list.append(f"{fld.display_name}: {fld.warning_message}")

        now_str = datetime.utcnow().isoformat()
        return HealthClaimData(
            claim_id=f"CLM-{int(datetime.utcnow().timestamp())}",
            created_at=now_str,
            updated_at=now_str,
            summary=summary,
            fields=extracted_fields,
            line_items=all_line_items,
            warnings=warnings_list,
            mismatches=summary.flag_reasons,
            audit_trail=audit_records
        )

    def _extract_single_candidate(self,
                                  ocr_res: OCRResult,
                                  schema: FieldSchema,
                                  filename: str,
                                  page_num: int) -> Tuple[Optional[str], str, float, Optional[BoundingBox], ExtractionMethod, List[Dict[str, str]]]:
        """
        Attempts to extract a value for a schema field from OCRResult.
        """
        label_matches = self.spatial.find_label_boxes(ocr_res.boxes, schema.aliases)
        method = ocr_res.extraction_method

        for label_box, alias in label_matches:
            val_text, conf, bbox = self.spatial.extract_spatial_value(label_box, ocr_res.boxes)
            if val_text and len(val_text.strip()) > 0:
                raw_val = val_text.strip()
                corrections: List[Dict[str, str]] = []

                # Contextual corrections
                if schema.field_type in ("number", "currency"):
                    val_text, corrections = self.corrector.correct_numeric_field(raw_val)
                elif schema.field_name == "ifsc_code":
                    val_text, corrections = self.corrector.correct_ifsc_field(raw_val)
                elif schema.field_name in ("pan_number", "id_proof_number") and len(raw_val) == 10:
                    val_text, corrections = self.corrector.correct_pan_field(raw_val)

                return val_text, raw_val, conf, bbox, method, corrections

        # Regex fallback on full text if spatial match didn't yield a value
        regex_val, reg_box = self._extract_regex_fallback(schema.field_name, ocr_res.full_text, ocr_res.boxes)
        if regex_val:
            return regex_val, regex_val, 0.75, reg_box, method, []

        return None, "", 0.0, None, method, []

    def _extract_regex_fallback(self, field_name: str, full_text: str, boxes: List[OCRBox]) -> Tuple[Optional[str], Optional[BoundingBox]]:
        """Fallback regex search for structured patterns across all major claim fields."""
        DATE_PAT = r"(\d{1,2}[/\-.:]\d{1,2}[/\-.:]\d{2,4})"
        AMT_PAT  = r"(?:Rs\.?\s*)?([0-9,]+(?:\.[0-9]{1,2})?)"
        ID_PAT   = r"([A-Z0-9][A-Z0-9\-\/]{4,24})"
        patterns = {
            "ifsc_code":         r"\b([A-Z]{4}0[A-Z0-9]{6})\b",
            "icd10_code":        r"\b([A-TV-Z][0-9][0-9AB](?:\.[0-9A-TV-Z]{1,4})?)\b",
            "policy_number":     r"(?i)policy\s*(?:no\.?|number|#)?\s*[:\-]?\s*" + ID_PAT,
            "member_id":         r"(?i)member\s*(?:id|no\.?|number)?\s*[:\-]?\s*" + ID_PAT,
            "claim_number":      r"(?i)claim\s*(?:no\.?|number|id|ref)?\s*[:\-]?\s*" + ID_PAT,
            "bill_number":       r"(?i)(?:bill|invoice)\s*(?:no\.?|number)?\s*[:\-]?\s*" + ID_PAT,
            "rohini_id":         r"(?i)rohini\s*[:\-]?\s*" + ID_PAT,
            "admission_date":    r"(?i)(?:date\s*of\s*admission|admission\s*date|doa)\s*[:\-]?\s*" + DATE_PAT,
            "discharge_date":    r"(?i)(?:date\s*of\s*discharge|discharge\s*date|dod)\s*[:\-]?\s*" + DATE_PAT,
            "patient_dob":       r"(?i)(?:date\s*of\s*birth|dob|d\.o\.b)\s*[:\-]?\s*" + DATE_PAT,
            "total_bill_amount": r"(?i)(?:total\s*bill(?:ed)?\s*amount|total\s*amount|grand\s*total|net\s*payable)\s*[:\-]?\s*" + AMT_PAT,
            "claimed_amount":    r"(?i)(?:claimed\s*amount|amount\s*claimed)\s*[:\-]?\s*" + AMT_PAT,
            "patient_age":       r"(?i)\bage\b\s*[:\-]?\s*(\d{1,3})\s*(?:years?|yrs?)",
        }
        pat = patterns.get(field_name)
        if pat:
            m = re.search(pat, full_text)
            if m:
                return m.group(1), None
        return None, None

    def _validate_field_value(self, field_name: str, value: str, field_type: str) -> Tuple[bool, Any, Optional[str]]:
        """Validates candidate against domain rules."""
        if field_type == "date":
            iso_d, err = self.validator.parse_and_normalize_date(value)
            return (iso_d is not None), iso_d or value, err
        elif field_type == "currency":
            amt, err = self.validator.parse_indian_amount(value)
            return (amt is not None), amt, err
        elif field_type == "number":
            try:
                num = int("".join(filter(str.isdigit, value)))
                return True, num, None
            except Exception:
                return False, value, "Not a valid number"
        elif field_name == "ifsc_code":
            return self.validator.validate_ifsc(value) + (value,)
        elif field_name == "icd10_code":
            return self.validator.validate_icd10(value) + (value,)
        elif field_name == "id_proof_number":
            clean_digits = "".join(filter(str.isdigit, value))
            if len(clean_digits) == 12:
                is_v, err = self.validator.validate_aadhaar(clean_digits)
                return is_v, clean_digits, err
            elif len(value.strip()) == 10:
                is_v, err = self.validator.validate_pan(value.strip())
                return is_v, value.strip().upper(), err
            return True, value, None
        
        # Generic string
        return True, value.strip(), None

    def _resolve_field(self, field_name: str, schema: FieldSchema, candidates: List[CandidateValue]) -> ExtractedField:
        """Chooses best candidate and sets status and warnings."""
        if not candidates:
            exp, act = self.warner.generate_field_warning(field_name, FieldStatus.MISSING)
            return ExtractedField(
                field_name=field_name,
                display_name=schema.display_name,
                status=FieldStatus.MISSING if not schema.required else FieldStatus.NEEDS_REVIEW,
                warning_message=exp if schema.required else None,
                recommended_action=act if schema.required else None
            )

        # Pick candidate passing validation with highest confidence
        valid_candidates = [c for c in candidates if c.validation_passed]
        chosen = max(valid_candidates, key=lambda c: c.confidence) if valid_candidates else candidates[0]

        # Determine status
        status = FieldStatus.EXTRACTED
        if not chosen.validation_passed:
            status = FieldStatus.INVALID
        elif chosen.confidence < settings.OCR_CONFIDENCE_THRESHOLD_REVIEW:
            status = FieldStatus.LOW_CONFIDENCE
        elif chosen.confidence < settings.OCR_CONFIDENCE_THRESHOLD_ACCEPT:
            status = FieldStatus.NEEDS_REVIEW

        exp, act = self.warner.generate_field_warning(
            field_name, status, str(chosen.value), validation_error=chosen.validation_error
        )

        # Mask sensitive values
        display_val = str(chosen.value)
        if schema.is_sensitive and settings.MASK_SENSITIVE_DATA:
            if field_name == "bank_account_number":
                display_val = mask_bank_account(str(chosen.value))
            elif field_name == "id_proof_number" and len("".join(filter(str.isdigit, str(chosen.value)))) == 12:
                display_val = mask_aadhaar(str(chosen.value))

        return ExtractedField(
            field_name=field_name,
            display_name=schema.display_name,
            value=chosen.value,
            raw_value=chosen.raw_value,
            normalized_value=chosen.value,
            status=status,
            confidence=chosen.confidence,
            source_filename=chosen.source_filename,
            page_number=chosen.page_number,
            bounding_box=chosen.bounding_box,
            evidence_text=chosen.raw_value,
            extraction_method=chosen.extraction_method,
            warning_message=exp if status != FieldStatus.EXTRACTED else None,
            recommended_action=act if status != FieldStatus.EXTRACTED else None,
            candidates=candidates,
            is_masked=schema.is_sensitive,
            display_value=display_val
        )

    def _build_claim_summary(self,
                             fields: Dict[str, ExtractedField],
                             line_items: List[LineItem],
                             documents: List[ProcessedDocument]) -> ClaimSummaryFields:
        """
        Builds the summary fields specifically requested by the user:
        - name, ID, priority types, age, SLA
        - hospital name, admission name, admission date, discharge date
        - source, billed, flagged, stage status, assignee, received
        """
        flags: List[str] = []

        patient_name = fields.get("patient_name", ExtractedField(field_name="", display_name="")).value
        policy_no = fields.get("policy_number", ExtractedField(field_name="", display_name="")).value
        member_id = fields.get("member_id", ExtractedField(field_name="", display_name="")).value
        claimed_id = member_id or policy_no

        patient_age = fields.get("patient_age", ExtractedField(field_name="", display_name="")).value
        if isinstance(patient_age, str) and patient_age.isdigit():
            patient_age = int(patient_age)

        hospital_name = fields.get("hospital_name", ExtractedField(field_name="", display_name="")).value
        admission_name = fields.get("admission_name", ExtractedField(field_name="", display_name="")).value
        admission_date = fields.get("admission_date", ExtractedField(field_name="", display_name="")).value
        discharge_date = fields.get("discharge_date", ExtractedField(field_name="", display_name="")).value

        raw_billed = fields.get("total_bill_amount", ExtractedField(field_name="", display_name="")).value
        try:
            billed_amount = float(str(raw_billed).replace(",", "").replace("Rs.", "").strip()) if raw_billed else 0.0
        except Exception:
            billed_amount = 0.0

        raw_claimed = fields.get("claimed_amount", ExtractedField(field_name="", display_name="")).value
        try:
            claimed_amount = float(str(raw_claimed).replace(",", "").replace("Rs.", "").strip()) if raw_claimed else billed_amount
        except Exception:
            claimed_amount = billed_amount

        # Validate stay dates
        is_stay_valid, stay_days, stay_err = self.validator.validate_stay_dates(admission_date, discharge_date)
        if not is_stay_valid:
            flags.append(stay_err or "Invalid hospitalization dates")

        # Check line items sum vs billed amount
        if line_items and billed_amount > 0:
            sum_items = sum(item.amount for item in line_items)
            diff = abs(sum_items - billed_amount)
            # Flag if difference is more than 2% or 50 rupees
            if diff > max(50.0, billed_amount * 0.02):
                flags.append(f"Line items sum (Rs {sum_items:,.2f}) does not match Total Billed Amount (Rs {billed_amount:,.2f})")

        # Determine Priority Type and SLA
        explicit_priority = fields.get("priority_type", ExtractedField(field_name="", display_name="")).value
        priority = "Standard"
        sla_days = settings.DEFAULT_SLA_DAYS_STANDARD

        if explicit_priority and any(e in str(explicit_priority).lower() for e in ["emergency", "icu", "critical"]):
            priority = "Emergency"
            sla_days = settings.DEFAULT_SLA_DAYS_EMERGENCY
        elif explicit_priority and "urgent" in str(explicit_priority).lower():
            priority = "Urgent"
            sla_days = settings.DEFAULT_SLA_DAYS_URGENT
        elif billed_amount > 200000.0:  # High value claim escalated to Urgent SLA
            priority = "Urgent"
            sla_days = settings.DEFAULT_SLA_DAYS_URGENT

        sla_desc = f"{sla_days} Days ({priority} SLA)"

        # Check for unreadable/missing critical fields
        for req in ["patient_name", "hospital_name", "admission_date"]:
            f = fields.get(req)
            if not f or f.status in (FieldStatus.MISSING, FieldStatus.UNREADABLE):
                flags.append(f"Mandatory field '{f.display_name if f else req}' missing or unreadable")

        source_doc_names = ", ".join(d.original_filename for d in documents[:3])
        if len(documents) > 3:
            source_doc_names += f" (+{len(documents) - 3} more)"

        now_formatted = datetime.utcnow().strftime("%d %b %Y, %H:%M UTC")

        # Overall Status
        if flags:
            overall_status = "Flagged for Verification"
            stage_status = "Medical Adjudication Review"
        elif all(fields[k].status == FieldStatus.EXTRACTED for k in ["patient_name", "hospital_name", "admission_date", "discharge_date"] if k in fields):
            overall_status = "Auto-Accepted"
            stage_status = "Ready for Settlement"
        else:
            overall_status = "Pending Review"
            stage_status = "Extraction Completed"

        return ClaimSummaryFields(
            name=str(patient_name) if patient_name else None,
            id=str(claimed_id) if claimed_id else None,
            priority_type=priority,
            age=patient_age if isinstance(patient_age, int) else None,
            sla=sla_desc,
            sla_days_remaining=sla_days,
            hospital_name=str(hospital_name) if hospital_name else None,
            admission_name=str(admission_name) if admission_name else None,
            admission_date=str(admission_date) if admission_date else None,
            discharge_date=str(discharge_date) if discharge_date else None,
            source=source_doc_names or "Direct Upload",
            billed=float(billed_amount),
            claimed_amount=float(claimed_amount),
            flagged=len(flags) > 0,
            flag_reasons=flags,
            stage_status=stage_status,
            status=overall_status,
            assignee="TPA Medical Claims Officer",
            received=now_formatted
        )
