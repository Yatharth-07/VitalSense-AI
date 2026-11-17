from __future__ import annotations

import json
import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
import httpx
from app.core.config import settings
from app.core.exceptions import AIServiceException
from app.schemas.patient import AIInsightsSchema

logger = logging.getLogger(__name__)


class BaseAIClient(ABC):
    """Abstract interface for AI health insight providers."""

    @abstractmethod
    def generate_health_insights(
        self,
        glucose: float,
        haemoglobin: float,
        cholesterol: float,
        age_years: Optional[int] = None
    ) -> AIInsightsSchema:
        """Generates structured health insights based strictly on numeric metrics."""
        pass


class MockAIHealthClient(BaseAIClient):
    """
    Deterministic mock provider for automated tests and offline local evaluation.
    Produces clinically cautious, structured remarks following the required schema.
    """

    def generate_health_insights(
        self,
        glucose: float,
        haemoglobin: float,
        cholesterol: float,
        age_years: Optional[int] = None
    ) -> AIInsightsSchema:
        observations: List[str] = []

        # Glucose evaluation (Standard reference: 70 - 99 mg/dL fasting, <140 mg/dL postprandial)
        if glucose > 200.0:
            observations.append(
                f"Elevated glucose ({glucose} mg/dL) exceeds typical physiological thresholds and may indicate marked hyperglycaemia warranting clinical evaluation."
            )
        elif glucose > 140.0:
            observations.append(
                f"Glucose level ({glucose} mg/dL) is above standard fasting reference ranges and warrants confirmatory testing."
            )
        elif glucose < 70.0:
            observations.append(
                f"Lower glucose measurement ({glucose} mg/dL) observed; evaluate for potential hypoglycaemia or fasting status."
            )
        else:
            observations.append(
                f"Glucose measurement ({glucose} mg/dL) appears within standard adult reference intervals."
            )

        # Haemoglobin evaluation (Typical adult reference: 12.0 - 17.5 g/dL depending on sex/age)
        if haemoglobin < 9.0:
            observations.append(
                f"Notably reduced haemoglobin ({haemoglobin} g/dL) detected; may warrant prompt evaluation for anaemia or blood loss."
            )
        elif haemoglobin < 12.0:
            observations.append(
                f"Haemoglobin measurement ({haemoglobin} g/dL) is on the lower threshold; clinical correlation advised."
            )
        elif haemoglobin > 18.0:
            observations.append(
                f"Haemoglobin ({haemoglobin} g/dL) is elevated; consider physiological adaptations, hydration status, or erythrocytosis."
            )
        else:
            observations.append(
                f"Haemoglobin ({haemoglobin} g/dL) aligns with typical adult reference standards."
            )

        # Cholesterol evaluation (Standard adult reference: <200 mg/dL desirable)
        if cholesterol >= 300.0:
            observations.append(
                f"Significantly elevated total cholesterol ({cholesterol} mg/dL) observed; comprehensive lipid profiling recommended."
            )
        elif cholesterol >= 200.0:
            observations.append(
                f"Borderline elevated total cholesterol ({cholesterol} mg/dL) noted; evaluation of HDL/LDL ratios recommended."
            )
        else:
            observations.append(
                f"Total cholesterol ({cholesterol} mg/dL) is within standard adult desirable parameters."
            )

        # Context summary
        age_context = f" for an individual approx {age_years} years of age" if age_years else ""
        summary = (
            f"Automated health overview{age_context}: "
            f"Review flagged measurements with a physician to contextualize against laboratory reference standards."
        )

        recommendation = (
            "Consult a registered medical professional for a comprehensive clinical assessment, "
            "complete blood count, and lipid profile. Do not alter diet or medication without physician oversight."
        )

        return AIInsightsSchema(
            summary=summary,
            observations=observations,
            recommendation=recommendation,
            disclaimer="EDUCATIONAL ONLY — NOT A MEDICAL DIAGNOSIS. Interpretation requires clinical history, laboratory-specific reference ranges, and direct physician assessment."
        )


class ExternalAIHealthClient(BaseAIClient):
    """
    Production AI Client communicating with external LLM APIs (e.g. Gemini REST or OpenAI-compatible).
    Adheres strictly to privacy principles: excludes patient PII (name, email).
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        api_url: Optional[str] = None,
        timeout: Optional[float] = None
    ):
        self.api_key = settings.AI_API_KEY if api_key is None else api_key
        self.api_url = api_url or settings.AI_API_URL
        self.timeout = timeout or settings.AI_REQUEST_TIMEOUT

    def _build_privacy_safe_prompt(
        self,
        glucose: float,
        haemoglobin: float,
        cholesterol: float,
        age_years: Optional[int]
    ) -> str:
        age_str = f"{age_years} years" if age_years is not None else "Unknown"
        return f"""You are an expert clinical laboratory data interpreter assisting healthcare providers.
Analyze the following objective blood test measurements:
- Glucose: {glucose} mg/dL
- Haemoglobin: {haemoglobin} g/dL
- Total Cholesterol: {cholesterol} mg/dL
- Approximate Age: {age_str}

CRITICAL MEDICAL AND SAFETY GUIDELINES:
1. Explain possible health concerns associated with these values.
2. Identify values that warrant further evaluation or physician review.
3. Explicitly state that interpretation depends on laboratory-specific reference ranges, age, sex, and clinical history.
4. DO NOT claim to diagnose a disease.
5. DO NOT prescribe medication or issue specific treatment instructions.
6. Conservative guidance: Recommend consulting a qualified healthcare professional.
7. Return your response STRICTLY as a valid JSON object with the following schema:
{{
  "summary": "Brief 1-2 sentence overview",
  "observations": [
    "Observation regarding glucose",
    "Observation regarding haemoglobin",
    "Observation regarding cholesterol"
  ],
  "recommendation": "General next-step guidance",
  "disclaimer": "This is an automated insight and not a medical diagnosis."
}}
Do NOT wrap the JSON in Markdown code fences. Return valid raw JSON only."""

    def generate_health_insights(
        self,
        glucose: float,
        haemoglobin: float,
        cholesterol: float,
        age_years: Optional[int] = None
    ) -> AIInsightsSchema:
        if not self.api_key:
            raise AIServiceException("AI API key is missing or not configured.", is_transient=False)

        prompt = self._build_privacy_safe_prompt(glucose, haemoglobin, cholesterol, age_years)

        # Gemini-compatible payload
        payload = {
            "contents": [
                {
                    "parts": [{"text": prompt}]
                }
            ],
            "generationConfig": {
                "temperature": 0.2,
                "responseMimeType": "application/json"
            }
        }

        url = f"{self.api_url}?key={self.api_key}" if "key=" not in self.api_url else self.api_url

        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(
                    url,
                    json=payload,
                    headers={"Content-Type": "application/json"}
                )

                if response.status_code == 401 or response.status_code == 403:
                    raise AIServiceException("AI API authentication failed: Invalid or expired API Key.", is_transient=False)
                elif response.status_code == 429:
                    raise AIServiceException("AI API rate limit exceeded. Please retry in a few moments.", is_transient=True)
                elif response.status_code >= 500:
                    raise AIServiceException(f"AI Provider service unavailable (HTTP {response.status_code}).", is_transient=True)
                elif response.status_code != 200:
                    raise AIServiceException(f"AI service request failed with HTTP {response.status_code}: {response.text}", is_transient=False)

                data = response.json()
                # Parse Gemini response structure
                candidates = data.get("candidates", [])
                if not candidates:
                    raise AIServiceException("AI provider returned empty candidates list.", is_transient=False)

                content_parts = candidates[0].get("content", {}).get("parts", [])
                if not content_parts:
                    raise AIServiceException("AI response contained empty content parts.", is_transient=False)

                raw_text = content_parts[0].get("text", "").strip()
                if not raw_text:
                    raise AIServiceException("AI provider returned blank text response.", is_transient=False)

                # Clean markdown fences if present
                if raw_text.startswith("```json"):
                    raw_text = raw_text[7:]
                if raw_text.startswith("```"):
                    raw_text = raw_text[3:]
                if raw_text.endswith("```"):
                    raw_text = raw_text[:-3]
                raw_text = raw_text.strip()

                parsed_json = json.loads(raw_text)
                return AIInsightsSchema.model_validate(parsed_json)

        except httpx.TimeoutException as exc:
            logger.error("AI service timed out after %s seconds: %s", self.timeout, exc)
            raise AIServiceException(f"AI API request timed out after {self.timeout}s.", is_transient=True) from exc
        except (json.JSONDecodeError, ValueError) as exc:
            logger.error("Failed to parse AI response as valid JSON: %s", exc)
            raise AIServiceException("AI provider returned malformed or unparseable JSON format.", is_transient=False) from exc
        except httpx.RequestError as exc:
            logger.error("Network error communicating with AI provider: %s", exc)
            raise AIServiceException(f"Network error contacting AI provider: {str(exc)}", is_transient=True) from exc


def get_ai_client() -> BaseAIClient:
    """Factory creating appropriate AI client based on configuration."""
    if settings.AI_PROVIDER.lower() == "gemini" and settings.AI_API_KEY:
        return ExternalAIHealthClient()
    return MockAIHealthClient()
