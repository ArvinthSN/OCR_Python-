"""
Verhoeff checksum algorithm for 12-digit Aadhaar number validation.
"""

# Multiplication table d
_D = [
    [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
    [1, 2, 3, 4, 0, 6, 7, 8, 9, 5],
    [2, 3, 4, 0, 1, 7, 8, 9, 5, 6],
    [3, 4, 0, 1, 2, 8, 9, 5, 6, 7],
    [4, 0, 1, 2, 3, 9, 5, 6, 7, 8],
    [5, 9, 8, 7, 6, 0, 4, 3, 2, 1],
    [6, 5, 9, 8, 7, 1, 0, 4, 3, 2],
    [7, 6, 5, 9, 8, 2, 1, 0, 4, 3],
    [8, 7, 6, 5, 9, 3, 2, 1, 0, 4],
    [9, 8, 7, 6, 5, 4, 3, 2, 1, 0],
]

# Permutation table p
_P = [
    [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
    [1, 5, 7, 6, 2, 8, 3, 0, 9, 4],
    [5, 8, 0, 3, 7, 9, 6, 1, 4, 2],
    [8, 9, 1, 6, 0, 4, 3, 5, 2, 7],
    [9, 4, 5, 3, 1, 2, 6, 8, 7, 0],
    [4, 2, 8, 6, 5, 7, 3, 9, 0, 1],
    [2, 7, 9, 3, 8, 0, 6, 4, 1, 5],
    [7, 0, 4, 6, 9, 1, 3, 2, 5, 8],
]

# Inverse table inv
_INV = [0, 4, 3, 2, 1, 5, 6, 7, 8, 9]

def generate_verhoeff(number_str: str) -> int:
    """Computes the Verhoeff checksum check digit for a given numeric prefix."""
    clean_num = "".join(filter(str.isdigit, number_str))
    c = 0
    for i, item in enumerate(reversed(clean_num)):
        c = _D[c][_P[(i + 1) % 8][int(item)]]
    return _INV[c]

def validate_verhoeff(number_str: str) -> bool:
    """
    Validates a number string using the Verhoeff checksum algorithm.
    Used for 12-digit Indian Aadhaar validation.
    """
    clean_num = "".join(filter(str.isdigit, number_str))
    if len(clean_num) != 12:
        return False

    c = 0
    reversed_digits = [int(x) for x in reversed(clean_num)]
    for i, digit in enumerate(reversed_digits):
        c = _D[c][_P[i % 8][digit]]

    return c == 0

def mask_aadhaar(aadhaar_str: str) -> str:
    """Masks Aadhaar number showing only last 4 digits (e.g. XXXX-XXXX-1234)."""
    clean_num = "".join(filter(str.isdigit, aadhaar_str))
    if len(clean_num) == 12:
        return f"XXXX-XXXX-{clean_num[-4:]}"
    return aadhaar_str

def mask_bank_account(acc_str: str) -> str:
    """Masks Bank Account number showing only last 4 digits."""
    clean_num = "".join(filter(str.isdigit, acc_str))
    if len(clean_num) >= 6:
        return f"***{clean_num[-4:]}"
    return acc_str
