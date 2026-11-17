from __future__ import annotations

from datetime import date, datetime
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, ConfigDict, Field
from app.utils.date_utils import format_date_display


class AIInsightsSchema(BaseModel):
    """Structured AI health insight schema required by Section 7."""
    summary: str = Field(..., description="Brief health insight summary")
    observations: List[str] = Field(..., description="Observations regarding glucose, haemoglobin, and cholesterol")
    recommendation: str = Field(..., description="General next-step guidance")
    disclaimer: str = Field(
        default="This is an automated educational insight and is not a medical diagnosis. Please consult a qualified healthcare professional.",
        description="Non-diagnostic medical disclaimer"
    )

    model_config = ConfigDict(from_attributes=True)


class PatientBase(BaseModel):
    full_name: str = Field(..., description="Full name of patient", min_length=1)
    date_of_birth: Union[str, date] = Field(..., description="Date of birth in DD/MM/YYYY or DD.MM.YYYY format")
    email: str = Field(..., description="Valid email address")
    glucose: float = Field(..., description="Blood glucose level (mg/dL)")
    haemoglobin: float = Field(..., description="Haemoglobin level (g/dL)")
    cholesterol: float = Field(..., description="Total cholesterol level (mg/dL)")


class PatientCreate(PatientBase):
    pass


class PatientUpdate(BaseModel):
    full_name: Optional[str] = None
    date_of_birth: Optional[Union[str, date]] = None
    email: Optional[str] = None
    glucose: Optional[float] = None
    haemoglobin: Optional[float] = None
    cholesterol: Optional[float] = None


class PatientResponse(BaseModel):
    id: int
    full_name: str
    date_of_birth: date
    date_of_birth_display: str
    email: str
    glucose: float
    haemoglobin: float
    cholesterol: float
    remarks: Optional[str] = None
    ai_insights_json: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def from_orm_patient(cls, patient: Any) -> "PatientResponse":
        return cls(
            id=patient.id,
            full_name=patient.full_name,
            date_of_birth=patient.date_of_birth,
            date_of_birth_display=format_date_display(patient.date_of_birth),
            email=patient.email,
            glucose=patient.glucose,
            haemoglobin=patient.haemoglobin,
            cholesterol=patient.cholesterol,
            remarks=patient.remarks,
            ai_insights_json=patient.ai_insights_json,
            created_at=patient.created_at,
            updated_at=patient.updated_at
        )


class PatientValidationResult(BaseModel):
    is_valid: bool
    errors: Dict[str, List[str]] = Field(default_factory=dict)
    cleaned_data: Optional[Dict[str, Any]] = None


class ImportSummaryResponse(BaseModel):
    total_submitted: int
    valid_records: int
    invalid_records: int
    accepted_duplicates: int
    invalid_email_count: int
    invalid_date_count: int
    results: List[Dict[str, Any]]
