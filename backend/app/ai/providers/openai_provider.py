import logging
from datetime import datetime, timezone
import httpx
from pydantic import ValidationError

from app.ai.providers.base_provider import BaseAIProvider
from app.ai.schemas import AIAnalyticsContext, AIInsight
from app.ai.prompts import SYSTEM_PROMPT, build_user_prompt

logger = logging.getLogger("socialscope.ai")


class OpenAIProvider(BaseAIProvider):
    """OpenAI LLM provider using httpx Chat Completions API with structured JSON response."""

    def __init__(self, api_key: str = "", model_name: str = "gpt-4o-mini", api_base: str = "https://api.openai.com/v1"):
        self.api_key = api_key
        self.model_name = model_name
        self.api_base = api_base.rstrip("/")

    @property
    def provider_name(self) -> str:
        return "openai"

    def is_configured(self) -> bool:
        return bool(self.api_key and self.api_key.strip())

    def generate_insight(self, context: AIAnalyticsContext) -> AIInsight:
        if not self.is_configured():
            raise RuntimeError("OpenAI API key is missing or not configured.")

        url = f"{self.api_base}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": self.model_name,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": build_user_prompt(context)}
            ],
            "temperature": 0.2,
            "max_tokens": 1000
        }

        try:
            with httpx.Client(timeout=30.0) as client:
                res = client.post(url, headers=headers, json=payload)

            if res.status_code != 200:
                logger.error(f"OpenAI API request failed: HTTP {res.status_code} - {res.text}")
                raise RuntimeError(f"AI Provider HTTP error ({res.status_code}).")

            data = res.json()
            raw_content = data["choices"][0]["message"]["content"]
            
            # Parse and validate structured JSON response with Pydantic
            insight = AIInsight.model_validate_json(raw_content)
            insight.provider = f"openai ({self.model_name})"
            if not insight.generated_at:
                insight.generated_at = datetime.now(timezone.utc).isoformat()

            return insight

        except ValidationError as ve:
            logger.error(f"Failed to validate LLM JSON output against AIInsight schema: {ve}")
            raise RuntimeError("LLM output validation error.")
        except httpx.RequestError as re:
            logger.error(f"Network error connecting to OpenAI API: {re}")
            raise RuntimeError("Network failure connecting to AI Provider.")
        except Exception as e:
            logger.error(f"Unexpected error in OpenAI provider generation: {e}")
            raise RuntimeError("AI insight generation failed.")
