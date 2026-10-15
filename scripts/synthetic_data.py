"""
Synthetic health insurance claim records for realistic benchmark generation.
"""

SYNTHETIC_CLAIMS = [
    {
        "claim_id": "CLM-SYN-001",
        "patient_name": "Arjun Sharma",
        "patient_age": 42,
        "patient_gender": "Male",
        "policy_number": "POL-8829104",
        "member_id": "MEM-55421",
        "hospital_name": "Apollo Hospitals Delhi",
        "admission_name": "Dr. Rajesh Gupta",
        "admission_date": "2025-02-10",
        "discharge_date": "2025-02-14",
        "diagnosis": "Acute Appendicitis",
        "icd10_code": "K35.8",
        "procedure_name": "Laparoscopic Appendectomy",
        "total_bill_amount": 125000.0,
        "claimed_amount": 125000.0,
        "priority_type": "Emergency",
        "ifsc_code": "HDFC0001234",
        "bank_account_number": "50100234567890",
        "line_items": [
            {"description": "Room Rent & Nursing Charges", "qty": 4, "rate": 5000.0, "amount": 20000.0},
            {"description": "Operation Theatre & Surgeon Charges", "qty": 1, "rate": 65000.0, "amount": 65000.0},
            {"description": "Pharmacy & Surgical Consumables", "qty": 1, "rate": 28000.0, "amount": 28000.0},
            {"description": "Diagnostic & Pathology Investigations", "qty": 1, "rate": 12000.0, "amount": 12000.0}
        ]
    },
    {
        "claim_id": "CLM-SYN-002",
        "patient_name": "Priya Nair",
        "patient_age": 35,
        "patient_gender": "Female",
        "policy_number": "HDF-772911",
        "member_id": "MED-99482",
        "hospital_name": "Fortis Memorial Research Institute",
        "admission_name": "Dr. Sunita Rao",
        "admission_date": "2025-03-01",
        "discharge_date": "2025-03-03",
        "diagnosis": "Bilateral Bronchopneumonia",
        "icd10_code": "J18.9",
        "procedure_name": "IV Antibiotic Therapy",
        "total_bill_amount": 68000.0,
        "claimed_amount": 68000.0,
        "priority_type": "Standard",
        "ifsc_code": "ICIC0000002",
        "bank_account_number": "000201567891",
        "line_items": [
            {"description": "Deluxe Room Charges", "qty": 2, "rate": 6000.0, "amount": 12000.0},
            {"description": "Physician Consultation & Visit", "qty": 2, "rate": 4000.0, "amount": 8000.0},
            {"description": "Medicines and IV Infusions", "qty": 1, "rate": 35000.0, "amount": 35000.0},
            {"description": "High Resolution Chest CT & Blood Work", "qty": 1, "rate": 13000.0, "amount": 13000.0}
        ]
    }
]
