import pytest
from app.merging.merger import DocumentMerger
from app.models.claim import HealthClaimData, ClaimSummaryFields
from app.models.fields import ExtractedField, CandidateValue, FieldStatus
from app.models.document import DocumentType

def test_source_priority_resolution():
    merger = DocumentMerger()

    # Field with two candidates:
    # 1. From Claim Form with date 2025-02-11
    # 2. From Discharge Summary with date 2025-02-10
    cand_claim_form = CandidateValue(
        value="2025-02-11",
        raw_value="11/02/2025",
        confidence=0.92,
        source_filename="claim_form.pdf",
        page_number=1
    )
    cand_discharge_summary = CandidateValue(
        value="2025-02-10",
        raw_value="10/02/2025",
        confidence=0.95,
        source_filename="discharge_summary.pdf",
        page_number=1
    )

    adm_field = ExtractedField(
        field_name="admission_date",
        display_name="Admission Date",
        value="2025-02-11",
        candidates=[cand_claim_form, cand_discharge_summary]
    )

    claim = HealthClaimData(
        claim_id="CLM-001",
        created_at="2025-02-15",
        updated_at="2025-02-15",
        fields={"admission_date": adm_field}
    )

    doc_types = {
        "claim_form.pdf": DocumentType.CLAIM_FORM,
        "discharge_summary.pdf": DocumentType.DISCHARGE_SUMMARY
    }

    merged = merger.merge_claims(claim, doc_types)

    # Discharge summary has higher priority for admission_date, so 2025-02-10 should be selected
    assert merged.fields["admission_date"].value == "2025-02-10"
    assert len(merged.audit_trail) > 0
    assert merged.audit_trail[0]["action"] == "source_priority_resolution"

def test_cross_document_identity_mismatch_flag():
    merger = DocumentMerger()

    cand1 = CandidateValue(
        value="Arjun Sharma",
        raw_value="Arjun Sharma",
        confidence=0.98,
        source_filename="discharge_summary.pdf",
        page_number=1
    )
    cand2 = CandidateValue(
        value="Priya Nair",  # Totally different patient name
        raw_value="Priya Nair",
        confidence=0.98,
        source_filename="invoice_bill.pdf",
        page_number=1
    )

    patient_field = ExtractedField(
        field_name="patient_name",
        display_name="Patient Name",
        value="Arjun Sharma",
        candidates=[cand1, cand2]
    )

    claim = HealthClaimData(
        claim_id="CLM-002",
        created_at="2025-02-15",
        updated_at="2025-02-15",
        fields={"patient_name": patient_field}
    )

    merged = merger.merge_claims(claim, {})

    # Incompatible names must trigger mismatch flag and set status to CONFLICT
    assert merged.fields["patient_name"].status == FieldStatus.CONFLICT
    assert merged.summary.flagged is True
    assert any("mismatch" in m.lower() for m in merged.mismatches)
