from __future__ import annotations

from typing import Any, Dict, List, Optional
from sqlalchemy import or_
from sqlalchemy.orm import Session
from app.models.patient import Patient, utc_now


class PatientRepository:
    """Repository handling all database persistence operations for Patient entities."""

    def __init__(self, db: Session):
        self.db = db

    def create(self, patient: Patient) -> Patient:
        """Persists a new patient record to SQLite."""
        self.db.add(patient)
        self.db.commit()
        self.db.refresh(patient)
        return patient

    def get_by_id(self, patient_id: int) -> Optional[Patient]:
        """Fetches an individual patient by ID."""
        return self.db.query(Patient).filter(Patient.id == patient_id).first()

    def get_all(
        self,
        search: Optional[str] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[Patient]:
        """Fetches all patient records, supporting search by name or email, ordered by id descending."""
        query = self.db.query(Patient)
        if search:
            search_pattern = f"%{search.strip()}%"
            query = query.filter(
                or_(
                    Patient.full_name.ilike(search_pattern),
                    Patient.email.ilike(search_pattern)
                )
            )
        return query.order_by(Patient.id.desc()).offset(skip).limit(limit).all()

    def count(self, search: Optional[str] = None) -> int:
        """Returns total count of patients matching optional search filter."""
        query = self.db.query(Patient)
        if search:
            search_pattern = f"%{search.strip()}%"
            query = query.filter(
                or_(
                    Patient.full_name.ilike(search_pattern),
                    Patient.email.ilike(search_pattern)
                )
            )
        return query.count()

    def update(self, patient: Patient, update_dict: Dict[str, Any]) -> Patient:
        """
        Updates fields on an existing patient entity without overwriting unrelated fields.
        Updates the updated_at timestamp.
        """
        for field, value in update_dict.items():
            if hasattr(patient, field) and value is not None:
                setattr(patient, field, value)

        patient.updated_at = utc_now()
        self.db.commit()
        self.db.refresh(patient)
        return patient

    def delete(self, patient: Patient) -> bool:
        """Deletes a patient record permanently."""
        self.db.delete(patient)
        self.db.commit()
        return True

    def get_metrics_summary(self) -> Dict[str, Any]:
        """Calculates dashboard metrics: total count, records with AI remarks, etc."""
        total = self.db.query(Patient).count()
        with_remarks = self.db.query(Patient).filter(
            Patient.remarks.isnot(None),
            Patient.remarks != ""
        ).count()
        return {
            "total_patients": total,
            "patients_with_remarks": with_remarks,
            "pending_remarks": total - with_remarks
        }
