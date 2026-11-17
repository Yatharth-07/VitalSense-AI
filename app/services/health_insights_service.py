from __future__ import annotations

import json
import logging
from datetime import date
from typing import Any, Dict, Optional, Tuple
from app.core.exceptions import AIServiceException
from app.integrations.ai_health_client import BaseAIClient, get_ai_client
from app.schemas.patient import AIInsightsSchema

logger = logging.getLogger(__name__)


class HealthInsightsService:
    """
    Orchestrates generation, formatting, and persistence of AI-powered health insights.
    Maintains strict clinical safety, error resilience, and non-identifying privacy boundaries.
    """

    def __init__(self, ai_client: Optional[BaseAIClient] = None):
        self.ai_client = ai_client or get_ai_client()

    @staticmethod
    def calculate_age_years(dob: Optional[date]) -> Optional[int]:
        """Calculates rough age in years from date of birth without including PII."""
        if not dob:
            return None
        today = date.today()
        return today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))

    @staticmethod
    def format_human_readable_remarks(insights: AIInsightsSchema) -> str:
        """Formats the structured AI response into clean, professional human-readable text."""
        obs_bullets = "\n".join(f"• {obs}" for obs in insights.observations)
        return (
            f"SUMMARY:\n{insights.summary}\n\n"
            f"OBSERVATIONS:\n{obs_bullets}\n\n"
            f"RECOMMENDATION:\n{insights.recommendation}\n\n"
            f"DISCLAIMER:\n{insights.disclaimer}"
        )

    def generate_remarks_for_patient(
        self,
        glucose: float,
        haemoglobin: float,
        cholesterol: float,
        date_of_birth: Optional[date] = None
    ) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """
        Generates remarks safely.

        Returns:
            (human_readable_remarks, json_serialized_insights, error_message_if_any)

        Safety guarantee:
            Never raises unhandled exceptions. If AI fails, returns pending remarks note and error details.
        """
        age_years = self.calculate_age_years(date_of_birth)

        try:
            insights_schema = self.ai_client.generate_health_insights(
                glucose=glucose,
                haemoglobin=haemoglobin,
                cholesterol=cholesterol,
                age_years=age_years
            )
            human_remarks = self.format_human_readable_remarks(insights_schema)
            json_insights = insights_schema.model_dump_json()
            return human_remarks, json_insights, None

        except AIServiceException as exc:
            logger.warning("AI integration error encountered: %s", exc.message)
            error_note = (
                f"AI Remarks Pending: External AI service error ({exc.message}). "
                "The patient record has been saved safely. You may retry AI generation from the dashboard."
            )
            return error_note, None, exc.message

        except Exception as exc:
            logger.error("Unexpected error in health insights generation: %s", exc, exc_info=True)
            error_note = (
                "AI Remarks Pending: An unexpected service exception occurred. "
                "Record saved successfully; please retry generation."
            )
            return error_note, None, str(exc)
