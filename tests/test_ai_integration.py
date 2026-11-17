from __future__ import annotations

import json
from unittest.mock import MagicMock, patch
import httpx
import pytest
from app.core.exceptions import AIServiceException
from app.integrations.ai_health_client import ExternalAIHealthClient
from app.services.health_insights_service import HealthInsightsService


class TestAIIntegrationFailures:

    def test_missing_api_key_raises_exception(self):
        client = ExternalAIHealthClient(api_key="")
        with pytest.raises(AIServiceException) as exc_info:
            client.generate_health_insights(100.0, 14.0, 180.0)
        assert "API key is missing" in exc_info.value.message

    @patch("httpx.Client.post")
    def test_invalid_api_key_401_handled(self, mock_post: MagicMock):
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_post.return_value = mock_response

        client = ExternalAIHealthClient(api_key="invalid-key")
        with pytest.raises(AIServiceException) as exc_info:
            client.generate_health_insights(100.0, 14.0, 180.0)
        assert "authentication failed" in exc_info.value.message.lower()
        assert not exc_info.value.is_transient

    @patch("httpx.Client.post")
    def test_rate_limit_429_handled(self, mock_post: MagicMock):
        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_post.return_value = mock_response

        client = ExternalAIHealthClient(api_key="valid-key")
        with pytest.raises(AIServiceException) as exc_info:
            client.generate_health_insights(100.0, 14.0, 180.0)
        assert "rate limit" in exc_info.value.message.lower()
        assert exc_info.value.is_transient

    @patch("httpx.Client.post")
    def test_api_timeout_handled(self, mock_post: MagicMock):
        mock_post.side_effect = httpx.TimeoutException("Connection timed out")

        client = ExternalAIHealthClient(api_key="valid-key", timeout=2.0)
        with pytest.raises(AIServiceException) as exc_info:
            client.generate_health_insights(100.0, 14.0, 180.0)
        assert "timed out" in exc_info.value.message.lower()
        assert exc_info.value.is_transient

    @patch("httpx.Client.post")
    def test_malformed_json_response_handled(self, mock_post: MagicMock):
        mock_response = MagicMock()
        mock_response.status_code = 200
        # Return invalid JSON text in candidate part
        mock_response.json.return_value = {
            "candidates": [
                {
                    "content": {
                        "parts": [{"text": "Not valid JSON at all! {broken"}]
                    }
                }
            ]
        }
        mock_post.return_value = mock_response

        client = ExternalAIHealthClient(api_key="valid-key")
        with pytest.raises(AIServiceException) as exc_info:
            client.generate_health_insights(100.0, 14.0, 180.0)
        assert "malformed" in exc_info.value.message.lower()

    @patch("httpx.Client.post")
    def test_empty_candidates_response_handled(self, mock_post: MagicMock):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"candidates": []}
        mock_post.return_value = mock_response

        client = ExternalAIHealthClient(api_key="valid-key")
        with pytest.raises(AIServiceException) as exc_info:
            client.generate_health_insights(100.0, 14.0, 180.0)
        assert "empty candidates" in exc_info.value.message.lower()

    @patch("httpx.Client.post")
    def test_patient_data_saved_when_ai_fails(self, mock_post: MagicMock):
        """
        Guarantee: If AI fails, the patient record is NOT lost.
        A pending note is placed in remarks allowing user retry.
        """
        mock_post.side_effect = httpx.TimeoutException("AI timeout")
        failing_client = ExternalAIHealthClient(api_key="key", timeout=1.0)
        service = HealthInsightsService(ai_client=failing_client)

        remarks, json_data, err = service.generate_remarks_for_patient(232.0, 13.5, 180.0)

        assert remarks is not None
        assert "AI Remarks Pending" in remarks
        assert json_data is None
        assert err is not None
