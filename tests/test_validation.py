from __future__ import annotations

import pytest
from app.services.validation_service import ValidationService


class TestValidationService:

    def test_full_name_validation(self):
        # Valid names
        valid_names = ["Robyn Pears", "Madison XI", "Jean-Luc Picard", "O'Connor", " Prem Kumar "]
        for name in valid_names:
            val, err = ValidationService.validate_full_name(name)
            assert err is None
            assert val is not None
            assert val == name.strip()

        # Invalid names
        invalid_names = ["", "   ", "12345", None]
        for name in invalid_names:
            val, err = ValidationService.validate_full_name(name)
            assert err is not None
            assert val is None

    def test_date_of_birth_validation(self):
        # Valid dates in both formats
        val1, err1 = ValidationService.validate_date_of_birth("28.01.1960")
        assert err1 is None
        assert val1 is not None
        assert val1.year == 1960 and val1.month == 1 and val1.day == 28

        val2, err2 = ValidationService.validate_date_of_birth("12/09/1998")
        assert err2 is None
        assert val2 is not None
        assert val2.year == 1998 and val2.month == 9 and val2.day == 12

        # Invalid: Impossible calendar date (Nov 31)
        val3, err3 = ValidationService.validate_date_of_birth("31.11.2001")
        assert err3 is not None
        assert "Invalid calendar date" in err3

        # Invalid: Future date
        val4, err4 = ValidationService.validate_date_of_birth("19.10.2030")
        assert err4 is not None
        assert "cannot be in the future" in err4

        # Invalid format
        val5, err5 = ValidationService.validate_date_of_birth("not-a-date")
        assert err5 is not None

    def test_email_validation(self):
        # Valid emails
        valid_emails = [
            "robyn@gmail.com",
            "timd@smh.com.au",
            "Larry@hotmail.com",
            "prem@telstra.com",
            "gokul@infocare.com"
        ]
        for em in valid_emails:
            val, err = ValidationService.validate_email(em)
            assert err is None
            assert val == em

        # Invalid emails from test assignment
        # hunter@gmail has no domain TLD extension (.com, etc.)
        val_hunter, err_hunter = ValidationService.validate_email("hunter@gmail")
        assert err_hunter is not None
        assert val_hunter is None

        # Kris.wu.gmail.com has no @ symbol
        val_kris, err_kris = ValidationService.validate_email("Kris.wu.gmail.com")
        assert err_kris is not None
        assert val_kris is None

        # Empty / malformed
        for bad in ["", "   ", "@domain.com", "user@.com"]:
            _, err = ValidationService.validate_email(bad)
            assert err is not None

    def test_numeric_blood_measurements(self):
        # Valid values
        val_gluc, err_gluc = ValidationService.validate_numeric_metric(232, "Glucose", 10, 1000, "mg/dL")
        assert err_gluc is None
        assert val_gluc == 232.0

        # Clinically low Hb (7.6) is numerically valid and must be accepted
        val_hb, err_hb = ValidationService.validate_numeric_metric(7.6, "Haemoglobin", 1.0, 35.0, "g/dL")
        assert err_hb is None
        assert val_hb == 7.6

        # Non-numeric string
        _, err_str = ValidationService.validate_numeric_metric("invalid", "Cholesterol", 20, 1500, "mg/dL")
        assert err_str is not None

        # NaN and Infinity
        _, err_nan = ValidationService.validate_numeric_metric(float("nan"), "Glucose", 10, 1000, "mg/dL")
        assert err_nan is not None
        assert "cannot be NaN" in err_nan

        _, err_inf = ValidationService.validate_numeric_metric(float("inf"), "Glucose", 10, 1000, "mg/dL")
        assert err_inf is not None

    def test_multiple_errors_together_kris_wu(self):
        """
        Test 8 — Kris Wu has both an invalid future date and a malformed email.
        The validator must report both errors together without short-circuiting.
        """
        kris_payload = {
            "full_name": "Kris Wu",
            "date_of_birth": "19.10.2030",
            "email": "Kris.wu.gmail.com",
            "glucose": 79.0,
            "haemoglobin": 16.5,
            "cholesterol": 197.0
        }
        is_valid, errors, _ = ValidationService.validate_patient_payload(kris_payload)

        assert not is_valid
        assert "date_of_birth" in errors
        assert "email" in errors
        assert len(errors["date_of_birth"]) > 0
        assert len(errors["email"]) > 0
        assert "future" in errors["date_of_birth"][0].lower()
