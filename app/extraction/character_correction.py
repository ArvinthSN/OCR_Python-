from typing import Tuple, List, Dict

# Character confusion maps
DIGIT_TO_LETTER = {
    "0": "O",
    "1": "I",
    "5": "S",
    "8": "B",
    "2": "Z",
}

LETTER_TO_DIGIT = {
    "O": "0",
    "o": "0",
    "I": "1",
    "l": "1",
    "i": "1",
    "S": "5",
    "s": "5",
    "B": "8",
    "Z": "2",
    "z": "2",
}

class ContextCharacterCorrector:
    @staticmethod
    def correct_numeric_field(raw_text: str) -> Tuple[str, List[Dict[str, str]]]:
        """
        Corrects common OCR letter-for-digit confusions strictly in numeric contexts
        (e.g., amounts, phone, age, bank account numbers).
        Audits every character replacement.
        """
        corrections: List[Dict[str, str]] = []
        result_chars = []

        for idx, ch in enumerate(raw_text):
            if ch in LETTER_TO_DIGIT:
                rep = LETTER_TO_DIGIT[ch]
                result_chars.append(rep)
                corrections.append({
                    "position": str(idx),
                    "original": ch,
                    "replacement": rep,
                    "rule": "letter_to_digit_in_numeric_field"
                })
            else:
                result_chars.append(ch)

        return "".join(result_chars), corrections

    @staticmethod
    def correct_ifsc_field(raw_text: str) -> Tuple[str, List[Dict[str, str]]]:
        """
        IFSC has strict layout: 4 Letters, 1 Zero, 6 Alphanumerics (usually letters/digits).
        e.g. HDFC0001234.
        Fifth character MUST be digit '0'. First 4 characters MUST be letters.
        """
        clean = raw_text.strip().replace(" ", "").upper()
        if len(clean) != 11:
            return raw_text, []

        corrections: List[Dict[str, str]] = []
        chars = list(clean)

        # First 4 chars must be letters
        for i in range(4):
            if chars[i] in DIGIT_TO_LETTER:
                rep = DIGIT_TO_LETTER[chars[i]]
                corrections.append({"position": str(i), "original": chars[i], "replacement": rep, "rule": "ifsc_prefix_must_be_letters"})
                chars[i] = rep

        # 5th char (index 4) must be zero '0'
        if chars[4] in ("O", "o"):
            corrections.append({"position": "4", "original": chars[4], "replacement": "0", "rule": "ifsc_5th_char_must_be_zero"})
            chars[4] = "0"

        return "".join(chars), corrections

    @staticmethod
    def correct_pan_field(raw_text: str) -> Tuple[str, List[Dict[str, str]]]:
        """
        PAN has strict layout: 5 Letters, 4 Digits, 1 Letter.
        e.g. ABCDE1234F.
        """
        clean = raw_text.strip().replace(" ", "").upper()
        if len(clean) != 10:
            return raw_text, []

        corrections: List[Dict[str, str]] = []
        chars = list(clean)

        # Positions 0-4: Letters
        for i in range(5):
            if chars[i] in DIGIT_TO_LETTER:
                rep = DIGIT_TO_LETTER[chars[i]]
                corrections.append({"position": str(i), "original": chars[i], "replacement": rep, "rule": "pan_prefix_letters"})
                chars[i] = rep

        # Positions 5-8: Digits
        for i in range(5, 9):
            if chars[i] in LETTER_TO_DIGIT:
                rep = LETTER_TO_DIGIT[chars[i]]
                corrections.append({"position": str(i), "original": chars[i], "replacement": rep, "rule": "pan_middle_digits"})
                chars[i] = rep

        # Position 9: Letter
        if chars[9] in DIGIT_TO_LETTER:
            rep = DIGIT_TO_LETTER[chars[9]]
            corrections.append({"position": "9", "original": chars[9], "replacement": rep, "rule": "pan_suffix_letter"})
            chars[9] = rep

        return "".join(chars), corrections
