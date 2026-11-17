from __future__ import annotations

import math
import re
from datetime import date
from typing import Any, Dict, List, Optional, Tuple, Union
from app.core.config import settings
from app.utils.date_utils import parse_date_string


class ValidationService:
    """
    Centralized, reusable validation service implementing strict domain rules
    specified in Section 6. Returns clear, accumulated field-specific errors.
    """

    # Comprehensive email pattern verifying valid username, @ symbol, domain name, and TLD (>=2 chars)
    EMAIL_REGEX = re.compile(
        r"^[a-zA-Z0-9.!#$%&'*+/=?^_`{|}~-]+@[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)+$"
    )

    @classmethod
    def validate_full_name(cls, name_raw: Any) -> Tuple[Optional[str], Optional[str]]:
        """
        Validates Full Name:
        - Required, non-empty after trimming
        - Reject names consisting only of numbers
        - Supports spaces, letters, hyphens, periods, apostrophes, Roman numerals (e.g. Madison XI)
        """
        if name_raw is None:
            return None, "Full name is required."

        if not isinstance(name_raw, str):
            name_raw = str(name_raw)

        cleaned = name_raw.strip()
        if not cleaned:
            return None, "Full name cannot be empty."

        if cleaned.isdigit():
            return None, "Full name cannot consist exclusively of numbers."

        # Ensure name contains at least one alphabetic character
        if not any(c.isalpha() for c in cleaned):
            return None, "Full name must contain at least one alphabetic letter."

        return cleaned, None

    @classmethod
    def validate_date_of_birth(cls, dob_raw: Any) -> Tuple[Optional[date], Optional[str]]:
        """
        Validates Date of Birth:
        - Required, valid calendar date (rejects 31.11.2001)
        - Not in future (rejects 19.10.2030)
        - Accepts DD/MM/YYYY and DD.MM.YYYY notation
        """
        return parse_date_string(dob_raw)

    @classmethod
    def validate_email(cls, email_raw: Any) -> Tuple[Optional[str], Optional[str]]:
        """
        Validates Email:
        - Required, trimmed
        - Rejects malformed addresses such as 'hunter@gmail' (missing TLD) or 'Kris.wu.gmail.com' (missing @)
        - Does not silently modify or correct invalid addresses
        """
        if email_raw is None:
            return None, "Email address is required."

        if not isinstance(email_raw, str):
            return None, "Email must be a string."

        cleaned = email_raw.strip()
        if not cleaned:
            return None, "Email address cannot be empty."

        # Check syntax using standard robust regex
        if not cls.EMAIL_REGEX.match(cleaned):
            return None, f"Invalid email address format: '{cleaned}'."

        # Ensure top level domain has at least 2 characters (rejects e.g. .c)
        domain_parts = cleaned.split("@")[-1].split(".")
        if len(domain_parts) < 2 or len(domain_parts[-1]) < 2:
            return None, f"Invalid email domain structure: '{cleaned}'."

        return cleaned, None

    @classmethod
    def validate_numeric_metric(
        cls,
        value_raw: Any,
        field_name: str,
        min_limit: float,
        max_limit: float,
        unit: str
    ) -> Tuple[Optional[float], Optional[str]]:
        """
        Validates blood test metrics:
        - Required numeric value
        - Rejects NaN, Infinity, strings that cannot be parsed as float
        - Validates within configurable limits without rejecting clinically abnormal but valid values
        """
        if value_raw is None or value_raw == "":
            return None, f"{field_name} is required."

        try:
            val = float(value_raw)
        except (ValueError, TypeError):
            return None, f"{field_name} must be a valid numeric measurement."

        if math.isnan(val) or math.isinf(val):
            return None, f"{field_name} cannot be NaN or Infinite."

        if val < min_limit or val > max_limit:
            return None, f"{field_name} value ({val} {unit}) is outside permitted measurement boundaries ({min_limit} - {max_limit} {unit})."

        return round(val, 2), None

    @classmethod
    def validate_patient_payload(cls, data: Dict[str, Any]) -> Tuple[bool, Dict[str, List[str]], Dict[str, Any]]:
        """
        Validates all submitted patient fields together.
        Accumulates all errors across fields (e.g. Kris Wu gets both DOB and Email errors).
        """
        errors: Dict[str, List[str]] = {}
        cleaned_data: Dict[str, Any] = {}

        # 1. Full Name
        name_val, name_err = cls.validate_full_name(data.get("full_name"))
        if name_err:
            errors.setdefault("full_name", []).append(name_err)
        else:
            cleaned_data["full_name"] = name_val

        # 2. Date of Birth
        dob_val, dob_err = cls.validate_date_of_birth(data.get("date_of_birth"))
        if dob_err:
            errors.setdefault("date_of_birth", []).append(dob_err)
        else:
            cleaned_data["date_of_birth"] = dob_val

        # 3. Email
        email_val, email_err = cls.validate_email(data.get("email"))
        if email_err:
            errors.setdefault("email", []).append(email_err)
        else:
            cleaned_data["email"] = email_val

        # 4. Glucose
        gluc_val, gluc_err = cls.validate_numeric_metric(
            data.get("glucose"),
            "Glucose",
            settings.GLUCOSE_MIN,
            settings.GLUCOSE_MAX,
            "mg/dL"
        )
        if gluc_err:
            errors.setdefault("glucose", []).append(gluc_err)
        else:
            cleaned_data["glucose"] = gluc_val

        # 5. Haemoglobin
        hb_val, hb_err = cls.validate_numeric_metric(
            data.get("haemoglobin"),
            "Haemoglobin",
            settings.HAEMOGLOBIN_MIN,
            settings.HAEMOGLOBIN_MAX,
            "g/dL"
        )
        if hb_err:
            errors.setdefault("haemoglobin", []).append(hb_err)
        else:
            cleaned_data["haemoglobin"] = hb_val

        # 6. Cholesterol
        chol_val, chol_err = cls.validate_numeric_metric(
            data.get("cholesterol"),
            "Cholesterol",
            settings.CHOLESTEROL_MIN,
            settings.CHOLESTEROL_MAX,
            "mg/dL"
        )
        if chol_err:
            errors.setdefault("cholesterol", []).append(chol_err)
        else:
            cleaned_data["cholesterol"] = chol_val

        is_valid = len(errors) == 0
        return is_valid, errors, cleaned_data
