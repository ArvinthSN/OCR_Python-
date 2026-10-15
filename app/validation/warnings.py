from typing import Optional, Tuple
from app.models.fields import FieldStatus

class WarningGenerator:
    @staticmethod
    def generate_field_warning(field_name: str,
                               status: FieldStatus,
                               candidate_val: Optional[str] = None,
                               quality_problem: Optional[str] = None,
                               validation_error: Optional[str] = None) -> Tuple[str, str]:
        """
        Generates a concise explanation and actionable recommendation for uncertain fields.
        Returns (explanation, recommended_action).
        """
        name_display = field_name.replace("_", " ").title()

        if status == FieldStatus.LOW_CONFIDENCE:
            if quality_problem == "blurred":
                return (
                    f"Low OCR confidence because the source image is blurred.",
                    f"Please verify against the original document or upload a sharper scan."
                )
            elif quality_problem == "rotated":
                return (
                    f"Extracted with low margin after orientation correction.",
                    f"Please confirm the extracted {name_display} value."
                )
            return (
                f"Low OCR confidence score on {name_display}.",
                f"Please verify this value against the source document."
            )

        elif status == FieldStatus.INVALID:
            err = validation_error or "Does not match expected format"
            return (
                f"A value '{candidate_val or ''}' was found but failed validation: {err}.",
                f"Please review and correct the {name_display} format."
            )

        elif status == FieldStatus.CONFLICT:
            return (
                f"Different documents show conflicting values for {name_display}.",
                f"Please select the verified value from the candidates list."
            )

        elif status == FieldStatus.UNREADABLE:
            return (
                f"{name_display} could not be recognized due to severe image degradation.",
                f"Please manually enter this field or upload a higher resolution document."
            )

        elif status == FieldStatus.MISSING:
            return (
                f"No entry found for {name_display} across uploaded documents.",
                f"Please manually enter {name_display} if required for your claim."
            )

        elif status == FieldStatus.NEEDS_REVIEW:
            return (
                f"{name_display} requires manual review ({validation_error or 'ambiguous text'}).",
                f"Please verify and confirm this entry."
            )

        return ("", "")
