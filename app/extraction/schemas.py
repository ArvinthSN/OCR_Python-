from typing import Dict, List, Any, Optional
from pydantic import BaseModel
from app.models.document import DocumentType

class FieldSchema(BaseModel):
    field_name: str
    display_name: str
    field_type: str  # "string", "number", "date", "currency", "id"
    required: bool = False
    aliases: List[str]  # Label keywords to search for spatially
    allowed_sources: List[DocumentType] = []
    is_sensitive: bool = False

CLAIM_FIELD_SCHEMAS: Dict[str, FieldSchema] = {
    # Patient & Policyholder
    "patient_name": FieldSchema(
        field_name="patient_name",
        display_name="Patient Name",
        field_type="string",
        required=True,
        aliases=["patient name", "name of patient", "patient's name", "insured name",
                 "name of insured person", "beneficiary name", "patient name:",
                 "patient :", "name of insured"],
        allowed_sources=[DocumentType.DISCHARGE_SUMMARY, DocumentType.CLAIM_FORM, DocumentType.FINAL_BILL, DocumentType.POLICY_SCHEDULE]
    ),
    "patient_age": FieldSchema(
        field_name="patient_age",
        display_name="Patient Age",
        field_type="number",
        required=False,
        aliases=["age", "age / gender", "patient age", "yrs", "years", "age / sex"],
        allowed_sources=[DocumentType.DISCHARGE_SUMMARY, DocumentType.CLAIM_FORM, DocumentType.FINAL_BILL]
    ),
    "patient_gender": FieldSchema(
        field_name="patient_gender",
        display_name="Gender",
        field_type="string",
        required=False,
        aliases=["gender", "sex", "male / female"],
        allowed_sources=[DocumentType.DISCHARGE_SUMMARY, DocumentType.CLAIM_FORM, DocumentType.FINAL_BILL]
    ),
    "patient_dob": FieldSchema(
        field_name="patient_dob",
        display_name="Date of Birth",
        field_type="date",
        required=False,
        aliases=["dob", "date of birth", "birth date", "d.o.b"],
        allowed_sources=[DocumentType.POLICY_SCHEDULE, DocumentType.CLAIM_FORM, DocumentType.IDENTITY_DOCUMENT]
    ),

    # Policy details
    "policy_number": FieldSchema(
        field_name="policy_number",
        display_name="Policy Number",
        field_type="id",
        required=True,
        aliases=["policy number", "policy no", "policy #", "certificate no", "policy no.", "pol no"],
        allowed_sources=[DocumentType.POLICY_SCHEDULE, DocumentType.CLAIM_FORM, DocumentType.PREAUTH_LETTER]
    ),
    "member_id": FieldSchema(
        field_name="member_id",
        display_name="Member ID / Health Card ID",
        field_type="id",
        required=False,
        aliases=["member id", "member id / health card", "health card no", "card id",
                 "uhid", "tpa id", "membership no", "insured id", "member no"],
        allowed_sources=[DocumentType.POLICY_SCHEDULE, DocumentType.CLAIM_FORM, DocumentType.DISCHARGE_SUMMARY]
    ),
    "insurer_name": FieldSchema(
        field_name="insurer_name",
        display_name="Insurance Company",
        field_type="string",
        required=False,
        aliases=["insurance company", "insurer name", "insurance co.", "underwritten by",
                 "insured by", "name of insurance"],
        allowed_sources=[DocumentType.POLICY_SCHEDULE, DocumentType.CLAIM_FORM]
    ),
    "tpa_name": FieldSchema(
        field_name="tpa_name",
        display_name="TPA Name",
        field_type="string",
        required=False,
        aliases=["tpa name", "third party administrator", "serviced by",
                 "tpa name:", "managed by tpa"],
        allowed_sources=[DocumentType.POLICY_SCHEDULE, DocumentType.CLAIM_FORM, DocumentType.PREAUTH_LETTER]
    ),

    # Claim & Priority
    "claim_number": FieldSchema(
        field_name="claim_number",
        display_name="Claim Number",
        field_type="id",
        required=False,
        aliases=["claim number", "claim no", "claim id", "ccn", "claim ref"],
        allowed_sources=[DocumentType.CLAIM_FORM, DocumentType.PREAUTH_LETTER]
    ),
    "claimed_amount": FieldSchema(
        field_name="claimed_amount",
        display_name="Claimed Amount",
        field_type="currency",
        required=True,
        aliases=["claimed amount", "amount claimed", "total claim", "reimbursement claim"],
        allowed_sources=[DocumentType.CLAIM_FORM, DocumentType.FINAL_BILL]
    ),
    "priority_type": FieldSchema(
        field_name="priority_type",
        display_name="Priority Type",
        field_type="string",
        required=False,
        aliases=["priority type", "case priority", "admission type", "claim priority",
                 "priority:", "type of claim"],
        allowed_sources=[DocumentType.CLAIM_FORM, DocumentType.DISCHARGE_SUMMARY, DocumentType.PREAUTH_LETTER]
    ),

    # Hospitalization details
    "hospital_name": FieldSchema(
        field_name="hospital_name",
        display_name="Hospital Name",
        field_type="string",
        required=True,
        aliases=["hospital name", "name of hospital", "nursing home", "clinic name", "healthcare institute", "hospital :"],
        allowed_sources=[DocumentType.DISCHARGE_SUMMARY, DocumentType.FINAL_BILL, DocumentType.CLAIM_FORM]
    ),
    "admission_name": FieldSchema(
        field_name="admission_name",
        display_name="Admission Name / Treating Doctor",
        field_type="string",
        required=False,
        aliases=["treating doctor", "consultant name", "admitting doctor", "doctor name", "dr.", "treating consultant", "physician"],
        allowed_sources=[DocumentType.DISCHARGE_SUMMARY, DocumentType.PRESCRIPTION, DocumentType.CLAIM_FORM]
    ),
    "admission_date": FieldSchema(
        field_name="admission_date",
        display_name="Admission Date",
        field_type="date",
        required=True,
        aliases=["date of admission", "admission date", "doa", "admitted on", "adm date", "d.o.a"],
        allowed_sources=[DocumentType.DISCHARGE_SUMMARY, DocumentType.FINAL_BILL, DocumentType.CLAIM_FORM]
    ),
    "discharge_date": FieldSchema(
        field_name="discharge_date",
        display_name="Discharge Date",
        field_type="date",
        required=True,
        aliases=["date of discharge", "discharge date", "dod", "discharged on", "dis date", "d.o.d"],
        allowed_sources=[DocumentType.DISCHARGE_SUMMARY, DocumentType.FINAL_BILL, DocumentType.CLAIM_FORM]
    ),
    "hospital_registration_or_rohini_id": FieldSchema(
        field_name="hospital_registration_or_rohini_id",
        display_name="ROHINI / Hospital Reg ID",
        field_type="id",
        required=False,
        aliases=["rohini id", "rohini", "hospital reg no", "hospital registration"],
        allowed_sources=[DocumentType.FINAL_BILL, DocumentType.DISCHARGE_SUMMARY]
    ),

    # Medical & Diagnosis
    "diagnosis": FieldSchema(
        field_name="diagnosis",
        display_name="Provisional / Final Diagnosis",
        field_type="string",
        required=False,
        aliases=["final diagnosis", "provisional diagnosis", "diagnosis", "clinical diagnosis", "indication"],
        allowed_sources=[DocumentType.DISCHARGE_SUMMARY, DocumentType.PRESCRIPTION, DocumentType.CLAIM_FORM]
    ),
    "icd10_code": FieldSchema(
        field_name="icd10_code",
        display_name="ICD-10 Code",
        field_type="id",
        required=False,
        aliases=["icd 10", "icd10", "icd code", "icd-10 code", "icd-10"],
        allowed_sources=[DocumentType.DISCHARGE_SUMMARY, DocumentType.FINAL_BILL, DocumentType.CLAIM_FORM]
    ),
    "procedure_name": FieldSchema(
        field_name="procedure_name",
        display_name="Procedure / Surgery Done",
        field_type="string",
        required=False,
        aliases=["procedure performed", "surgery done", "procedure done", "operation", "surgical procedure"],
        allowed_sources=[DocumentType.DISCHARGE_SUMMARY, DocumentType.FINAL_BILL]
    ),

    # Billing details
    "bill_number": FieldSchema(
        field_name="bill_number",
        display_name="Bill / Invoice Number",
        field_type="id",
        required=False,
        aliases=["bill no", "invoice no", "bill number", "invoice number", "bill #", "invoice #"],
        allowed_sources=[DocumentType.FINAL_BILL, DocumentType.PHARMACY_BILL]
    ),
    "total_bill_amount": FieldSchema(
        field_name="total_bill_amount",
        display_name="Total Billed Amount",
        field_type="currency",
        required=True,
        aliases=["total bill amount", "net payable", "grand total", "total amount", "net amount", "invoice total", "bill total", "total (rs)"],
        allowed_sources=[DocumentType.FINAL_BILL, DocumentType.CLAIM_FORM]
    ),

    # Bank details
    "account_holder_name": FieldSchema(
        field_name="account_holder_name",
        display_name="Bank Account Holder",
        field_type="string",
        required=False,
        aliases=["account holder name", "account name", "beneficiary name", "name in bank"],
        allowed_sources=[DocumentType.BANK_PROOF, DocumentType.CLAIM_FORM]
    ),
    "bank_account_number": FieldSchema(
        field_name="bank_account_number",
        display_name="Bank Account Number",
        field_type="id",
        required=False,
        aliases=["account no", "account number", "a/c no", "bank a/c", "bank account no"],
        allowed_sources=[DocumentType.BANK_PROOF, DocumentType.CLAIM_FORM],
        is_sensitive=True
    ),
    "ifsc_code": FieldSchema(
        field_name="ifsc_code",
        display_name="IFSC Code",
        field_type="id",
        required=False,
        aliases=["ifsc code", "ifsc", "rtgs/neft ifsc"],
        allowed_sources=[DocumentType.BANK_PROOF, DocumentType.CLAIM_FORM]
    ),
    "bank_name": FieldSchema(
        field_name="bank_name",
        display_name="Bank Name",
        field_type="string",
        required=False,
        aliases=["bank name", "bank", "name of bank"],
        allowed_sources=[DocumentType.BANK_PROOF, DocumentType.CLAIM_FORM]
    ),

    # Identity details
    "id_proof_number": FieldSchema(
        field_name="id_proof_number",
        display_name="ID Proof Number",
        field_type="id",
        required=False,
        aliases=["aadhaar no", "pan no", "voter id", "passport no", "aadhaar number", "pan number", "identity number"],
        allowed_sources=[DocumentType.IDENTITY_DOCUMENT, DocumentType.CLAIM_FORM],
        is_sensitive=True
    )
}
