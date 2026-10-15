from typing import Dict, List, Any, Optional
from datetime import datetime
from app.models.claim import HealthClaimData
from app.models.fields import ExtractedField, CandidateValue, FieldStatus
from app.models.document import DocumentType
from app.validation.rules import DomainValidator

# Source document priority rankings (higher ranking = higher priority)
SOURCE_PRIORITIES: Dict[str, Dict[DocumentType, int]] = {
    "admission_date": {
        DocumentType.DISCHARGE_SUMMARY: 100,
        DocumentType.FINAL_BILL: 80,
        DocumentType.CLAIM_FORM: 60,
    },
    "discharge_date": {
        DocumentType.DISCHARGE_SUMMARY: 100,
        DocumentType.FINAL_BILL: 80,
        DocumentType.CLAIM_FORM: 60,
    },
    "policy_number": {
        DocumentType.POLICY_SCHEDULE: 100,
        DocumentType.PREAUTH_LETTER: 80,
        DocumentType.CLAIM_FORM: 60,
    },
    "total_bill_amount": {
        DocumentType.FINAL_BILL: 100,
        DocumentType.CLAIM_FORM: 70,
    },
    "patient_name": {
        DocumentType.IDENTITY_DOCUMENT: 100,
        DocumentType.POLICY_SCHEDULE: 90,
        DocumentType.DISCHARGE_SUMMARY: 85,
        DocumentType.CLAIM_FORM: 70,
    },
    "admission_name": {
        DocumentType.DISCHARGE_SUMMARY: 100,
        DocumentType.PRESCRIPTION: 90,
        DocumentType.CLAIM_FORM: 60,
    }
}

class DocumentMerger:
    def __init__(self):
        self.validator = DomainValidator()

    def merge_claims(self, claim: HealthClaimData, doc_types_map: Dict[str, DocumentType]) -> HealthClaimData:
        """
        Applies source-priority rules and checks for cross-document identity consistency.
        Flags incompatible values without silently discarding evidence.
        """
        audit_entries = claim.audit_trail or []
        mismatches = list(claim.mismatches) or []

        # 1. Apply source priorities to resolve candidates
        for field_name, field in claim.fields.items():
            if len(field.candidates) > 1 and field_name in SOURCE_PRIORITIES:
                priority_map = SOURCE_PRIORITIES[field_name]
                
                # Sort candidates by document priority first, then confidence
                def get_cand_score(c: CandidateValue):
                    dtype = doc_types_map.get(c.source_filename, DocumentType.UNKNOWN)
                    p_score = priority_map.get(dtype, 10)
                    valid_boost = 50 if c.validation_passed else 0
                    return (valid_boost + p_score, c.confidence)

                sorted_candidates = sorted(field.candidates, key=get_cand_score, reverse=True)
                top_cand = sorted_candidates[0]

                if top_cand.value != field.value:
                    old_val = field.value
                    field.value = top_cand.value
                    field.normalized_value = top_cand.value
                    field.raw_value = top_cand.raw_value
                    field.confidence = top_cand.confidence
                    field.source_filename = top_cand.source_filename
                    field.page_number = top_cand.page_number
                    field.bounding_box = top_cand.bounding_box
                    field.extraction_method = top_cand.extraction_method

                    audit_entries.append({
                        "action": "source_priority_resolution",
                        "field": field_name,
                        "old_value": old_val,
                        "new_value": top_cand.value,
                        "source": top_cand.source_filename,
                        "reason": f"Preferred higher authority document: {doc_types_map.get(top_cand.source_filename, 'unknown')}",
                        "timestamp": datetime.utcnow().isoformat()
                    })

        # 2. Check for cross-document identity conflicts
        # Patient Name consistency across multiple documents
        patient_field = claim.fields.get("patient_name")
        if patient_field and len(patient_field.candidates) > 1:
            unique_names = list(set(str(c.value) for c in patient_field.candidates if c.value and c.validation_passed))
            if len(unique_names) > 1:
                # Compare each pair using fuzzy matching
                for i in range(len(unique_names)):
                    for j in range(i + 1, len(unique_names)):
                        if not self.validator.are_names_consistent(unique_names[i], unique_names[j]):
                            msg = f"Patient name mismatch between documents: '{unique_names[i]}' vs '{unique_names[j]}'"
                            if msg not in mismatches:
                                mismatches.append(msg)
                            patient_field.status = FieldStatus.CONFLICT
                            patient_field.warning_message = "Different documents show conflicting patient names."
                            patient_field.recommended_action = "Please select the correct patient name from the uploaded documents."

        # Update claim object
        claim.audit_trail = audit_entries
        claim.mismatches = mismatches
        if mismatches:
            claim.summary.flagged = True
            for m in mismatches:
                if m not in claim.summary.flag_reasons:
                    claim.summary.flag_reasons.append(m)
            claim.summary.status = "Flagged for Verification"

        return claim
