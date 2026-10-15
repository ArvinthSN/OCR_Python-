import re
from typing import Tuple, List, Dict
from app.models.document import DocumentType

DOCUMENT_KEYWORD_RULES: Dict[DocumentType, List[str]] = {
    DocumentType.POLICY_SCHEDULE: [
        "policy schedule", "certificate of insurance", "sum insured", "policy number",
        "period of insurance", "health card", "e-card", "uhid", "tpa id", "valid from",
        "policyholder", "proposer", "cumulative bonus", "premium paid"
    ],
    DocumentType.CLAIM_FORM: [
        "claim form", "part a", "part b", "details of primary insured",
        "details of insurance history", "details of insured person hospitalized",
        "claim intimation", "tpa claim form", "declaration by the insured"
    ],
    DocumentType.PREAUTH_LETTER: [
        "pre-authorization", "preauthorization", "cashless approval", "initial authorization",
        "enhancement approval", "authorized amount", "tpa approval", "pre-auth", "provisional approval"
    ],
    DocumentType.DISCHARGE_SUMMARY: [
        "discharge summary", "discharge card", "date of admission", "date of discharge",
        "clinical summary", "chief complaints", "history of present illness",
        "course in hospital", "condition at discharge", "discharge advice", "treating consultant"
    ],
    DocumentType.FINAL_BILL: [
        "final bill", "tax invoice", "bill of supply", "inpatient bill", "summary bill",
        "total bill amount", "room rent", "nursing charges", "ot charges", "doctor charges",
        "investigation charges", "amount payable", "hospital bill"
    ],
    DocumentType.PHARMACY_BILL: [
        "pharmacy", "medical store", "chemist", "druggist", "rx bill", "batch no",
        "mfg date", "exp date", "medicine bill", "hsn code", "gstin"
    ],
    DocumentType.LAB_REPORT: [
        "laboratory report", "diagnostic report", "pathology report", "radiology",
        "biochemistry", "haematology", "urine analysis", "reference range", "observed value",
        "specimen", "investigation report"
    ],
    DocumentType.PRESCRIPTION: [
        "prescription", "dr.", "doctor prescription", "rx", "consultation note",
        "opd consultation", "dosage", "tablet", "capsule", "syrup", "sos", "od", "bd", "tid"
    ],
    DocumentType.BANK_PROOF: [
        "cancelled cheque", "bank passbook", "account number", "ifsc code", "micr code",
        "bank branch", "savings account", "current account", "rtgs/neft", "bank statement"
    ],
    DocumentType.IDENTITY_DOCUMENT: [
        "aadhaar", "unique identification authority of india", "income tax department",
        "permanent account number", "pan card", "election commission of india",
        "voter id", "driving licence", "passport", "republic of india"
    ],
}

class DocumentClassifier:
    def classify(self, text: str) -> Tuple[DocumentType, float, List[str]]:
        """
        Classifies document based on extracted text using keyword and pattern evidence.
        Returns:
            - DocumentType
            - confidence (0.0 to 1.0)
            - evidence list (keywords found)
        Never forces an unknown document into a type.
        """
        if not text or len(text.strip()) < 10:
            return DocumentType.UNKNOWN, 0.0, ["Insufficient text for classification"]

        text_lower = text.lower()
        scores: Dict[DocumentType, List[str]] = {}

        for doc_type, keywords in DOCUMENT_KEYWORD_RULES.items():
            matched_keywords = []
            for kw in keywords:
                # Word boundary match for short keywords, substring for multi-word phrases
                if " " in kw:
                    if kw in text_lower:
                        matched_keywords.append(kw)
                else:
                    if re.search(r'\b' + re.escape(kw) + r'\b', text_lower):
                        matched_keywords.append(kw)

            if matched_keywords:
                scores[doc_type] = matched_keywords

        if not scores:
            return DocumentType.UNKNOWN, 0.0, ["No specific domain keywords matched"]

        # Sort by number of matched keywords
        best_type = max(scores, key=lambda k: len(scores[k]))
        matched_list = scores[best_type]

        # Require at least 2 distinct keywords or 1 strong multi-word key phrase to classify
        if len(matched_list) == 1 and len(matched_list[0].split()) == 1:
            return DocumentType.UNKNOWN, 0.25, [f"Weak match only: '{matched_list[0]}'"]

        # Confidence heuristic: bounded between 0.50 and 0.98 based on evidence depth
        confidence = min(0.98, 0.50 + (len(matched_list) * 0.10))

        return best_type, confidence, matched_list
