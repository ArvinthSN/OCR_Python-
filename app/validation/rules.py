import re
from datetime import datetime, date
from typing import Optional, Tuple, List, Any
from dateutil import parser as date_parser
from rapidfuzz import fuzz

from app.validation.verhoeff import validate_verhoeff

# Regex patterns for health claim domain validation
IFSC_REGEX = re.compile(r"^[A-Z]{4}0[A-Z0-9]{6}$")
PAN_REGEX = re.compile(r"^[A-Z]{5}[0-9]{4}[A-Z]$")
MOBILE_REGEX = re.compile(r"^[6-9]\d{9}$")
EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")
ICD10_REGEX = re.compile(r"^[A-TV-Z][0-9][0-9AB](\.[0-9A-TV-Z]{1,4})?$", re.IGNORECASE)
BANK_ACCOUNT_REGEX = re.compile(r"^\d{9,18}$")

TITLE_PREFIXES = ["dr.", "dr", "mr.", "mr", "mrs.", "mrs", "ms.", "ms", "shri", "smt", "master", "baby"]

class DomainValidator:
    @staticmethod
    def parse_and_normalize_date(date_str: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Parses multi-format dates (DD/MM/YYYY, DD-MM-YYYY, YYYY-MM-DD, 12 Mar 2025, etc.)
        Normalizes to ISO format (YYYY-MM-DD).
        Prefers day-first (Indian locale convention: DD/MM/YYYY).
        Returns (iso_date_str, error_msg).
        """
        if not date_str:
            return None, "Empty date value"

        cleaned = date_str.strip().replace(".", "/")
        # Extract potential date pattern from surrounding noise
        match = re.search(r"(\d{1,4}[/\-\s]+[A-Za-z0-9]{1,4}[/\-\s]+\d{2,4})", cleaned)
        target = match.group(1) if match else cleaned

        try:
            # dayfirst=True is Indian standard
            parsed = date_parser.parse(target, dayfirst=True)
            # Sanity check year bounds
            if parsed.year < 1900 or parsed.year > 2100:
                return None, f"Year {parsed.year} out of plausible range"
            return parsed.strftime("%Y-%m-%d"), None
        except Exception as e:
            return None, f"Failed to parse date '{date_str}': {str(e)}"

    @staticmethod
    def parse_indian_amount(amount_str: str) -> Tuple[Optional[float], Optional[str]]:
        """
        Normalizes Indian (1,25,000.00) and International (125,000.00) amount formats.
        Strips currency symbols (Rs, INR, ₹, /-).
        Returns (float_val, error_msg).
        """
        if not amount_str:
            return None, "Empty amount string"

        cleaned = str(amount_str).strip()
        # Remove currency symbols and suffixes (including common OCR confusion R5 for Rs)
        cleaned = re.sub(r"(?i)(rs\.?|inr|₹|r5\.?|re\.?|/-)", "", cleaned).strip()
        # Remove extra whitespace
        cleaned = cleaned.replace(" ", "")

        # Remove commas
        cleaned = cleaned.replace(",", "")

        try:
            val = float(cleaned)
            if val < 0:
                return None, "Negative amount not allowed"
            return round(val, 2), None
        except Exception:
            return None, f"Invalid numeric amount format: '{amount_str}'"

    @staticmethod
    def validate_ifsc(ifsc: str) -> Tuple[bool, Optional[str]]:
        val = str(ifsc).strip().upper()
        if not IFSC_REGEX.match(val):
            return False, "IFSC must have 4 letters, followed by 0, followed by 6 alphanumeric characters"
        return True, None

    @staticmethod
    def validate_pan(pan: str) -> Tuple[bool, Optional[str]]:
        val = str(pan).strip().upper()
        if not PAN_REGEX.match(val):
            return False, "PAN must follow 5 uppercase letters, 4 digits, 1 uppercase letter"
        return True, None

    @staticmethod
    def validate_aadhaar(aadhaar: str) -> Tuple[bool, Optional[str]]:
        clean_num = "".join(filter(str.isdigit, str(aadhaar)))
        if len(clean_num) != 12:
            return False, "Aadhaar must be exactly 12 digits"
        if not validate_verhoeff(clean_num):
            return False, "Aadhaar Verhoeff checksum validation failed"
        return True, None

    @staticmethod
    def validate_bank_account(acc: str) -> Tuple[bool, Optional[str]]:
        clean_acc = "".join(filter(str.isdigit, str(acc)))
        if not BANK_ACCOUNT_REGEX.match(clean_acc):
            return False, "Bank account number must be between 9 and 18 digits"
        return True, None

    @staticmethod
    def validate_mobile(mobile: str) -> Tuple[bool, Optional[str]]:
        clean_mob = "".join(filter(str.isdigit, str(mobile)))
        # Strip leading +91 or 0
        if clean_mob.startswith("91") and len(clean_mob) == 12:
            clean_mob = clean_mob[2:]
        elif clean_mob.startswith("0") and len(clean_mob) == 11:
            clean_mob = clean_mob[1:]

        if not MOBILE_REGEX.match(clean_mob):
            return False, "Mobile must be a 10-digit number starting with 6, 7, 8, or 9"
        return True, None

    @staticmethod
    def validate_icd10(code: str) -> Tuple[bool, Optional[str]]:
        clean_code = str(code).strip().upper()
        if not ICD10_REGEX.match(clean_code):
            return False, f"'{code}' does not match standard ICD-10 pattern (e.g. A09, J18.9)"
        return True, None

    @staticmethod
    def normalize_name(name: str) -> str:
        """Normalizes names by stripping titles, dots, and converting to title case."""
        if not name:
            return ""
        tokens = name.strip().split()
        filtered = [t for t in tokens if t.lower().rstrip(".") not in TITLE_PREFIXES]
        clean_name = " ".join(filtered).title()
        return clean_name

    @classmethod
    def are_names_consistent(cls, name1: str, name2: str, threshold: float = 85.0) -> bool:
        """
        Fuzzy compares two names using RapidFuzz token_sort_ratio to accommodate
        reordered names (e.g. 'Sharma, Arjun' vs 'Arjun Sharma').
        """
        n1 = cls.normalize_name(name1)
        n2 = cls.normalize_name(name2)
        if not n1 or not n2:
            return False
        score = fuzz.token_sort_ratio(n1.lower(), n2.lower())
        return score >= threshold

    @staticmethod
    def validate_stay_dates(admission_iso: Optional[str], discharge_iso: Optional[str]) -> Tuple[bool, Optional[int], Optional[str]]:
        """
        Validates admission_date <= discharge_date and computes length of stay.
        """
        if not admission_iso or not discharge_iso:
            return True, None, None

        try:
            d_adm = datetime.strptime(admission_iso, "%Y-%m-%d").date()
            d_dis = datetime.strptime(discharge_iso, "%Y-%m-%d").date()
            if d_adm > d_dis:
                return False, None, f"Admission date ({admission_iso}) is after Discharge date ({discharge_iso})"
            length_of_stay = (d_dis - d_adm).days
            # Same day admission/discharge is 1 day or 0 day-care
            return True, max(1, length_of_stay), None
        except Exception as e:
            return False, None, str(e)
