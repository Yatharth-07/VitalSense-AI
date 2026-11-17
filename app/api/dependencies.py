from __future__ import annotations

from fastapi import Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.repositories.patient_repository import PatientRepository
from app.services.health_insights_service import HealthInsightsService
from app.services.patient_service import PatientService


def get_patient_repository(db: Session = Depends(get_db)) -> PatientRepository:
    return PatientRepository(db)


def get_health_insights_service() -> HealthInsightsService:
    return HealthInsightsService()


def get_patient_service(
    repo: PatientRepository = Depends(get_patient_repository),
    insights: HealthInsightsService = Depends(get_health_insights_service)
) -> PatientService:
    return PatientService(repository=repo, insights_service=insights)
