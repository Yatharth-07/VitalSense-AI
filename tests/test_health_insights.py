from __future__ import annotations

from datetime import date
import pytest
from app.integrations.ai_health_client import ExternalAIHealthClient, MockAIHealthClient
from app.schemas.patient import AIInsightsSchema
from app.services.health_insights_service import HealthInsightsService


class TestHealthInsights:

    def test_mock_ai_client_structured_output(self):
        client = MockAIHealthClient()
        insights = client.generate_health_insights(
            glucose=232.0,
            haemoglobin=13.5,
            cholesterol=180.0,
            age_years=64
        )

        assert isinstance(insights, AIInsightsSchema)
        assert len(insights.observations) == 3
        # Hyperglycaemia observation
        assert any("glucose" in obs.lower() for obs in insights.observations)
        # Disclaimer must not claim medical diagnosis
        assert "NOT A MEDICAL DIAGNOSIS" in insights.disclaimer

    def test_privacy_preservation_in_prompt_generation(self):
        """
        Security and Privacy Rule (Section 12):
        Never send patient names or email addresses to the AI provider.
        """
        ext_client = ExternalAIHealthClient(api_key="test-key", api_url="https://test.api")
        prompt = ext_client._build_privacy_safe_prompt(
            glucose=240.0,
            haemoglobin=18.6,
            cholesterol=326.0,
            age_years=32
        )

        # Check prompt contains numeric measurements
        assert "240.0 mg/dL" in prompt
        assert "18.6 g/dL" in prompt
        assert "326.0 mg/dL" in prompt
        assert "32 years" in prompt

        # Verify no PII placeholders exist
        assert "name" not in prompt.lower()
        assert "email" not in prompt.lower()
        assert "darryl" not in prompt.lower()

    def test_service_format_remarks(self, mock_insights_service: HealthInsightsService):
        remarks, raw_json, err = mock_insights_service.generate_remarks_for_patient(
            glucose=85.0,
            haemoglobin=7.6,
            cholesterol=163.0,
            date_of_birth=date(1998, 9, 12)
        )

        assert err is None
        assert remarks is not None
        assert "SUMMARY:" in remarks
        assert "OBSERVATIONS:" in remarks
        assert "RECOMMENDATION:" in remarks
        assert "DISCLAIMER:" in remarks
        assert raw_json is not None
