from __future__ import annotations

from typing import Any, Dict, List, Optional


class VitalSenseBaseException(Exception):
    """Base exception class for all domain errors in VitalSense AI."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}


class ValidationException(VitalSenseBaseException):
    """Raised when one or more patient data validation rules fail."""
    def __init__(self, errors: Dict[str, List[str]]):
        super().__init__("Patient validation failed", details={"errors": errors})
        self.errors = errors


class PatientNotFoundException(VitalSenseBaseException):
    """Raised when a patient ID does not exist in the database."""
    def __init__(self, patient_id: int):
        super().__init__(f"Patient with ID {patient_id} was not found", details={"patient_id": patient_id})
        self.patient_id = patient_id


class DatabaseOperationException(VitalSenseBaseException):
    """Raised when a database query or commit fails unexpectedly."""
    pass


class AIServiceException(VitalSenseBaseException):
    """Raised when an external AI provider fails or responds unexpectedly."""
    def __init__(self, message: str, is_transient: bool = True):
        super().__init__(message, details={"is_transient": is_transient})
        self.is_transient = is_transient
