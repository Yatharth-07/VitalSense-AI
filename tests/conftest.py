from __future__ import annotations

import os
from typing import Any, Dict, Generator, Optional
from urllib.parse import parse_qs, urlparse
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.routes.patients import (
    batch_import_records,
    create_patient,
    delete_patient,
    get_all_patients,
    get_dashboard_metrics,
    get_patient_by_id,
    regenerate_patient_insights,
    update_patient,
)
from app.core.database import Base
from app.core.exceptions import PatientNotFoundException, ValidationException
from app.integrations.ai_health_client import MockAIHealthClient
from app.repositories.patient_repository import PatientRepository
from app.services.health_insights_service import HealthInsightsService
from app.services.patient_service import PatientService

TEST_DATABASE_URL = "sqlite:///:memory:"

test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


class MockAPIResponse:
    def __init__(self, status_code: int, data: Any):
        self.status_code = status_code
        self._data = data

    def json(self) -> Any:
        return self._data


class DirectAPIClient:
    """
    High-performance synchronous test client that directly invokes FastAPI route handlers
    with realistic dependency injection, bypassing Starlette's Windows threadpool portal deadlock.
    """

    def __init__(self, service: PatientService):
        self.service = service

    def post(self, url: str, json: Any = None) -> MockAPIResponse:
        parsed = urlparse(url)
        path = parsed.path

        if path == "/api/patients" or path == "/api/patients/":
            try:
                result = create_patient(payload=json or {}, service=self.service)
                return MockAPIResponse(201, result.model_dump())
            except Exception as exc:
                if hasattr(exc, "status_code"):
                    return MockAPIResponse(exc.status_code, {"detail": exc.detail})
                raise exc

        elif path == "/api/patients/batch-import":
            result = batch_import_records(records=json or [], service=self.service)
            return MockAPIResponse(200, result.model_dump())

        elif path.startswith("/api/patients/") and path.endswith("/generate-insights"):
            patient_id = int(path.split("/")[3])
            try:
                result = regenerate_patient_insights(patient_id=patient_id, service=self.service)
                return MockAPIResponse(200, result.model_dump())
            except Exception as exc:
                if hasattr(exc, "status_code"):
                    return MockAPIResponse(exc.status_code, {"detail": exc.detail})
                raise exc

        return MockAPIResponse(404, {"detail": f"Path {path} not found"})

    def get(self, url: str) -> MockAPIResponse:
        parsed = urlparse(url)
        path = parsed.path
        query = parse_qs(parsed.query)

        search = query.get("search", [None])[0]
        skip = int(query.get("skip", [0])[0])
        limit = int(query.get("limit", [100])[0])

        if path == "/api/patients" or path == "/api/patients/":
            results = get_all_patients(search=search, skip=skip, limit=limit, service=self.service)
            return MockAPIResponse(200, [r.model_dump() for r in results])

        elif path == "/api/patients/metrics/dashboard":
            stats = get_dashboard_metrics(service=self.service)
            return MockAPIResponse(200, stats)

        elif path.startswith("/api/patients/"):
            parts = [p for p in path.split("/") if p]
            if len(parts) == 3 and parts[2].isdigit():
                patient_id = int(parts[2])
                try:
                    result = get_patient_by_id(patient_id=patient_id, service=self.service)
                    return MockAPIResponse(200, result.model_dump())
                except Exception as exc:
                    if hasattr(exc, "status_code"):
                        return MockAPIResponse(exc.status_code, {"detail": exc.detail})
                    raise exc

        return MockAPIResponse(404, {"detail": f"Path {path} not found"})

    def put(self, url: str, json: Any = None) -> MockAPIResponse:
        parsed = urlparse(url)
        path = parsed.path
        parts = [p for p in path.split("/") if p]
        if len(parts) == 3 and parts[2].isdigit():
            patient_id = int(parts[2])
            try:
                result = update_patient(patient_id=patient_id, payload=json or {}, service=self.service)
                return MockAPIResponse(200, result.model_dump())
            except Exception as exc:
                if hasattr(exc, "status_code"):
                    return MockAPIResponse(exc.status_code, {"detail": exc.detail})
                raise exc

        return MockAPIResponse(404, {"detail": f"Path {path} not found"})

    def delete(self, url: str) -> MockAPIResponse:
        parsed = urlparse(url)
        path = parsed.path
        parts = [p for p in path.split("/") if p]
        if len(parts) == 3 and parts[2].isdigit():
            patient_id = int(parts[2])
            try:
                result = delete_patient(patient_id=patient_id, service=self.service)
                return MockAPIResponse(200, result)
            except Exception as exc:
                if hasattr(exc, "status_code"):
                    return MockAPIResponse(exc.status_code, {"detail": exc.detail})
                raise exc

        return MockAPIResponse(404, {"detail": f"Path {path} not found"})


@pytest.fixture(scope="function")
def db_session() -> Generator[Session, None, None]:
    """Provides a fresh, isolated database schema for each test."""
    Base.metadata.create_all(bind=test_engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=test_engine)


@pytest.fixture(scope="function")
def client(db_session: Session) -> DirectAPIClient:
    """Fixture providing direct, fast API client injected with the test database."""
    repo = PatientRepository(db_session)
    insights = HealthInsightsService(ai_client=MockAIHealthClient())
    service = PatientService(repository=repo, insights_service=insights)
    return DirectAPIClient(service=service)


@pytest.fixture
def mock_ai_client() -> MockAIHealthClient:
    return MockAIHealthClient()


@pytest.fixture
def mock_insights_service(mock_ai_client: MockAIHealthClient) -> HealthInsightsService:
    return HealthInsightsService(ai_client=mock_ai_client)
