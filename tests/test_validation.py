import pytest
from app.validation.verhoeff import validate_verhoeff, mask_aadhaar, mask_bank_account
from app.validation.rules import DomainValidator

def test_verhoeff_aadhaar_validation():
    # 20000000001 -> checksum digit is 3, resulting in valid 12-digit Aadhaar 200000000013
    assert validate_verhoeff("200000000013") is True
    # Altered last digit
    assert validate_verhoeff("200000000019") is False
    # Altered interior digit (transposition error detection)
    assert validate_verhoeff("200000000103") is False

def test_masking():
    assert mask_aadhaar("200000000018") == "XXXX-XXXX-0018"
    assert mask_bank_account("50100234567890") == "***7890"

def test_ifsc_validation():
    assert DomainValidator.validate_ifsc("HDFC0001234")[0] is True
    assert DomainValidator.validate_ifsc("SBIN0000301")[0] is True
    # 5th char not '0'
    assert DomainValidator.validate_ifsc("HDFCO001234")[0] is False
    # invalid length
    assert DomainValidator.validate_ifsc("HDFC0123")[0] is False

def test_pan_validation():
    assert DomainValidator.validate_pan("ABCDE1234F")[0] is True
    assert DomainValidator.validate_pan("ABCD12345F")[0] is False

def test_mobile_validation():
    assert DomainValidator.validate_mobile("9876543210")[0] is True
    assert DomainValidator.validate_mobile("+91 9876543210")[0] is True
    assert DomainValidator.validate_mobile("5876543210")[0] is False # Does not start with 6-9

def test_icd10_validation():
    assert DomainValidator.validate_icd10("K35.8")[0] is True
    assert DomainValidator.validate_icd10("J18.9")[0] is True
    assert DomainValidator.validate_icd10("INVALID_CODE")[0] is False

def test_date_parsing_and_normalization():
    # Indian locale day-first preference
    iso_d, err = DomainValidator.parse_and_normalize_date("12/03/2025")
    assert iso_d == "2025-03-12"

    iso_d2, _ = DomainValidator.parse_and_normalize_date("15-Jan-2025")
    assert iso_d2 == "2025-01-15"

def test_amount_parsing():
    # Indian formatting: 1,25,000.50
    amt, _ = DomainValidator.parse_indian_amount("Rs. 1,25,000.50 /-")
    assert amt == 125000.50

    amt2, _ = DomainValidator.parse_indian_amount("₹ 68,000")
    assert amt2 == 68000.0

def test_name_consistency():
    # Dr. Arjun Sharma vs Arjun Sharma vs Sharma Arjun
    assert DomainValidator.are_names_consistent("Dr. Arjun Sharma", "Arjun Sharma") is True
    assert DomainValidator.are_names_consistent("Sharma, Arjun", "Arjun Sharma") is True
    assert DomainValidator.are_names_consistent("Arjun Sharma", "Priya Nair") is False

def test_stay_dates_validation():
    is_valid, days, err = DomainValidator.validate_stay_dates("2025-02-10", "2025-02-14")
    assert is_valid is True
    assert days == 4

    # Impossible: admission after discharge
    is_valid2, _, err2 = DomainValidator.validate_stay_dates("2025-02-15", "2025-02-10")
    assert is_valid2 is False
    assert "after" in err2.lower()
