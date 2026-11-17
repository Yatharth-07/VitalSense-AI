from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session

from app.core.exceptions import PatientNotFoundException, ValidationException
from app.models.patient import Patient
from app.repositories.patient_repository import PatientRepository
from app.schemas.patient import (
    ImportSummaryResponse,
    PatientCreate,
    PatientResponse,
    PatientUpdate,
)
from app.services.health_insights_service import HealthInsightsService
from app.services.validation_service import ValidationService

logger = logging.getLogger(__name__)


class PatientService:
    """Core domain service for patient lifecycle management, validation, and insight generation."""

    def __init__(
        self,
        repository: PatientRepository,
        insights_service: Optional[HealthInsightsService] = None,
    ):
        self.repository = repository
        self.insights_service = insights_service or HealthInsightsService()

    def create_patient(self, payload: Dict[str, Any]) -> PatientResponse:
        """
        Validates payload, generates AI health remarks, and persists the patient.
        Raises ValidationException if input rules are violated.
        """
        is_valid, errors, cleaned = ValidationService.validate_patient_payload(payload)
        if not is_valid:
            raise ValidationException(errors)

        # Generate AI health insights strictly using anonymized metrics
        remarks, insights_json, _ = self.insights_service.generate_remarks_for_patient(
            glucose=cleaned["glucose"],
            haemoglobin=cleaned["haemoglobin"],
            cholesterol=cleaned["cholesterol"],
            date_of_birth=cleaned["date_of_birth"],
        )

        patient = Patient(
            full_name=cleaned["full_name"],
            date_of_birth=cleaned["date_of_birth"],
            email=cleaned["email"],
            glucose=cleaned["glucose"],
            haemoglobin=cleaned["haemoglobin"],
            cholesterol=cleaned["cholesterol"],
            remarks=remarks,
            ai_insights_json=insights_json,
        )

        saved = self.repository.create(patient)
        return PatientResponse.from_orm_patient(saved)

    def get_patient(self, patient_id: int) -> PatientResponse:
        """Retrieves patient by ID or raises PatientNotFoundException."""
        patient = self.repository.get_by_id(patient_id)
        if not patient:
            raise PatientNotFoundException(patient_id)
        return PatientResponse.from_orm_patient(patient)

    def get_all_patients(
        self,
        search: Optional[str] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[PatientResponse]:
        """Returns all patients matching optional query with pagination."""
        records = self.repository.get_all(search=search, skip=skip, limit=limit)
        return [PatientResponse.from_orm_patient(p) for p in records]

    def count_patients(self, search: Optional[str] = None) -> int:
        """Returns count of patients matching search."""
        return self.repository.count(search=search)

    def update_patient(self, patient_id: int, update_data: Dict[str, Any]) -> PatientResponse:
        """
        Updates patient fields with strict validation.
        Regenerates AI remarks if blood test values change.
        """
        patient = self.repository.get_by_id(patient_id)
        if not patient:
            raise PatientNotFoundException(patient_id)

        # Build full dictionary representing target state for validation
        target_state = {
            "full_name": update_data.get("full_name", patient.full_name),
            "date_of_birth": update_data.get("date_of_birth", patient.date_of_birth),
            "email": update_data.get("email", patient.email),
            "glucose": update_data.get("glucose", patient.glucose),
            "haemoglobin": update_data.get("haemoglobin", patient.haemoglobin),
            "cholesterol": update_data.get("cholesterol", patient.cholesterol),
        }

        is_valid, errors, cleaned = ValidationService.validate_patient_payload(target_state)
        if not is_valid:
            raise ValidationException(errors)

        # Check if any blood test metric changed to determine if AI remarks should be re-evaluated
        metrics_changed = (
            cleaned["glucose"] != patient.glucose
            or cleaned["haemoglobin"] != patient.haemoglobin
            or cleaned["cholesterol"] != patient.cholesterol
            or cleaned["date_of_birth"] != patient.date_of_birth
        )

        update_fields: Dict[str, Any] = {
            "full_name": cleaned["full_name"],
            "date_of_birth": cleaned["date_of_birth"],
            "email": cleaned["email"],
            "glucose": cleaned["glucose"],
            "haemoglobin": cleaned["haemoglobin"],
            "cholesterol": cleaned["cholesterol"],
        }

        if metrics_changed:
            remarks, insights_json, _ = self.insights_service.generate_remarks_for_patient(
                glucose=cleaned["glucose"],
                haemoglobin=cleaned["haemoglobin"],
                cholesterol=cleaned["cholesterol"],
                date_of_birth=cleaned["date_of_birth"],
            )
            update_fields["remarks"] = remarks
            update_fields["ai_insights_json"] = insights_json

        updated_patient = self.repository.update(patient, update_fields)
        return PatientResponse.from_orm_patient(updated_patient)

    def delete_patient(self, patient_id: int) -> bool:
        """Deletes patient by ID or raises PatientNotFoundException."""
        patient = self.repository.get_by_id(patient_id)
        if not patient:
            raise PatientNotFoundException(patient_id)
        return self.repository.delete(patient)

    def regenerate_insights(self, patient_id: int) -> PatientResponse:
        """Forces regeneration of AI remarks for an existing patient."""
        patient = self.repository.get_by_id(patient_id)
        if not patient:
            raise PatientNotFoundException(patient_id)

        remarks, insights_json, err = self.insights_service.generate_remarks_for_patient(
            glucose=patient.glucose,
            haemoglobin=patient.haemoglobin,
            cholesterol=patient.cholesterol,
            date_of_birth=patient.date_of_birth,
        )

        updated_patient = self.repository.update(
            patient,
            {"remarks": remarks, "ai_insights_json": insights_json}
        )
        return PatientResponse.from_orm_patient(updated_patient)

    def get_dashboard_summary(self) -> Dict[str, Any]:
        """Returns statistics for dashboard cards."""
        return self.repository.get_metrics_summary()

    def import_controlled_records(
        self,
        records: List[Dict[str, Any]]
    ) -> ImportSummaryResponse:
        """
        Imports a batch of patient records (e.g. the 10 assignment test cases)
        without silently correcting or discarding errors.
        Calculates exact validation metrics matching Section 10.
        """
        total_submitted = len(records)
        valid_records = 0
        invalid_records = 0
        accepted_duplicates = 0
        invalid_email_count = 0
        invalid_date_count = 0
        results: List[Dict[str, Any]] = []

        seen_signatures: set[str] = set()

        for idx, item in enumerate(records, start=1):
            name = item.get("full_name") or item.get("Full Name", "")
            dob = item.get("date_of_birth") or item.get("DOB", "")
            email = item.get("email") or item.get("Email", "")
            glucose = item.get("glucose") or item.get("Glucose", 0.0)
            hb = item.get("haemoglobin") or item.get("Hb", 0.0)
            chol = item.get("cholesterol") or item.get("Cholesterol", 0.0)

            payload = {
                "full_name": name,
                "date_of_birth": dob,
                "email": email,
                "glucose": glucose,
                "haemoglobin": hb,
                "cholesterol": chol,
            }

            is_valid, errors, cleaned = ValidationService.validate_patient_payload(payload)

            if not is_valid:
                invalid_records += 1
                if "email" in errors:
                    invalid_email_count += 1
                if "date_of_birth" in errors:
                    invalid_date_count += 1

                results.append({
                    "test_index": idx,
                    "full_name": name,
                    "status": "REJECTED",
                    "errors": errors,
                    "patient_id": None,
                })
            else:
                signature = f"{cleaned['full_name']}|{cleaned['date_of_birth']}|{cleaned['email']}"
                if signature in seen_signatures:
                    accepted_duplicates += 1
                seen_signatures.add(signature)

                created = self.create_patient(payload)
                valid_records += 1
                results.append({
                    "test_index": idx,
                    "full_name": name,
                    "status": "ACCEPTED",
                    "errors": {},
                    "patient_id": created.id,
                })

        return ImportSummaryResponse(
            total_submitted=total_submitted,
            valid_records=valid_records,
            invalid_records=invalid_records,
            accepted_duplicates=accepted_duplicates,
            invalid_email_count=invalid_email_count,
            invalid_date_count=invalid_date_count,
            results=results,
        )
