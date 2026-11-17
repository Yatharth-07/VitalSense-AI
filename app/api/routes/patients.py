from __future__ import annotations

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from app.api.dependencies import get_patient_service
from app.core.exceptions import PatientNotFoundException, ValidationException
from app.schemas.patient import (
    ImportSummaryResponse,
    PatientCreate,
    PatientResponse,
    PatientUpdate,
)
from app.services.patient_service import PatientService

router = APIRouter(prefix="/patients", tags=["Patients"])


@router.get("", response_model=List[PatientResponse], status_code=status.HTTP_200_OK)
def get_all_patients(
    search: Optional[str] = Query(None, description="Search by full name or email address"),
    skip: int = Query(0, ge=0, description="Offset for pagination"),
    limit: int = Query(100, ge=1, le=500, description="Maximum number of records to return"),
    service: PatientService = Depends(get_patient_service),
):
    """Retrieve all patient records with optional search filter and pagination."""
    return service.get_all_patients(search=search, skip=skip, limit=limit)


@router.get("/metrics/dashboard", status_code=status.HTTP_200_OK)
def get_dashboard_metrics(
    service: PatientService = Depends(get_patient_service),
):
    """Returns dashboard statistics (total patients, with remarks, pending)."""
    return service.get_dashboard_summary()


@router.get("/{patient_id}", response_model=PatientResponse, status_code=status.HTTP_200_OK)
def get_patient_by_id(
    patient_id: int,
    service: PatientService = Depends(get_patient_service),
):
    """Retrieve an individual patient by their primary key ID."""
    try:
        return service.get_patient(patient_id)
    except PatientNotFoundException as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=exc.message
        ) from exc


@router.post("", response_model=PatientResponse, status_code=status.HTTP_201_CREATED)
def create_patient(
    payload: Dict[str, Any],
    service: PatientService = Depends(get_patient_service),
):
    """
    Register a new patient record:
    - Validates full name, calendar DOB, email syntax, and numeric blood measurements.
    - Generates AI remarks via external AI adapter (privacy-preserving, no PII sent).
    - Persists record in SQLite database.
    """
    try:
        return service.create_patient(payload)
    except ValidationException as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"message": exc.message, "errors": exc.errors}
        ) from exc


@router.put("/{patient_id}", response_model=PatientResponse, status_code=status.HTTP_200_OK)
def update_patient(
    patient_id: int,
    payload: Dict[str, Any],
    service: PatientService = Depends(get_patient_service),
):
    """
    Update an existing patient's details.
    - Validates updated fields.
    - Automatically re-evaluates AI remarks if blood test values change.
    """
    try:
        return service.update_patient(patient_id, payload)
    except PatientNotFoundException as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=exc.message
        ) from exc
    except ValidationException as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"message": exc.message, "errors": exc.errors}
        ) from exc


@router.delete("/{patient_id}", status_code=status.HTTP_200_OK)
def delete_patient(
    patient_id: int,
    service: PatientService = Depends(get_patient_service),
):
    """Delete a patient record permanently."""
    try:
        service.delete_patient(patient_id)
        return {
            "success": True,
            "message": f"Patient with ID {patient_id} was successfully deleted."
        }
    except PatientNotFoundException as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=exc.message
        ) from exc


@router.post("/{patient_id}/generate-insights", response_model=PatientResponse, status_code=status.HTTP_200_OK)
def regenerate_patient_insights(
    patient_id: int,
    service: PatientService = Depends(get_patient_service),
):
    """
    Manually trigger AI health insights re-generation for an existing patient record.
    Safely handles provider unavailability or retry requests.
    """
    try:
        return service.regenerate_insights(patient_id)
    except PatientNotFoundException as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=exc.message
        ) from exc


@router.post("/batch-import", response_model=ImportSummaryResponse, status_code=status.HTTP_200_OK)
def batch_import_records(
    records: List[Dict[str, Any]],
    service: PatientService = Depends(get_patient_service),
):
    """
    Controlled import endpoint for demonstration and batch testing.
    Processes all items, accepts valid entries, reports exact validation rejection reasons,
    and returns comprehensive statistics (Section 10 verification).
    """
    return service.import_controlled_records(records)
