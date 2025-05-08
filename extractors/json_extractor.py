

"""
json_extractor.py
-----------------

LLM‑powered utilities that convert unstructured ITDB fact‑sheet text into a
canonical JSON format using an Azure OpenAI deployment.

Typical use::

    from openai import AzureOpenAI
    from extractors.json_extractor import JSONExtractor

    client = AzureOpenAI(
        api_version="2024-12-01-preview",
        azure_endpoint="https://<your‑resource>.openai.azure.com/",
        api_key="<API‑KEY>",
    )

    extractor = JSONExtractor(client, "gpt-4o-mini")
    structured = extractor.extract(raw_text)
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict

from openai import AzureOpenAI

logger = logging.getLogger(__name__)


class JSONExtractor:
    """Extract structured data that adheres to a fixed schema."""

    # Canonical schema all extractions must follow.
    _SCHEMA: Dict[str, Any] = {
        "year": "integer ‑ 4‑digit year of the fact sheet",
        "total_incidents": "integer total number of incidents reported",
        "nuclear_material_incidents": "integer incidents involving nuclear material",
        "radioactive_material_incidents": "integer incidents involving other radioactive material",
        "incidents_by_material": {
            "uranium": "integer",
            "plutonium": "integer",
            "medical_isotopes": "integer",
        },
        "incidents_by_group": {
            "theft_or_loss": "integer",
            "unauthorized_activities": "integer",
            "other": "integer",
        },
    }

    def __init__(
        self,
        client: AzureOpenAI,
        deployment: str,
        *,
        temperature: float = 0.0,
        max_retries: int = 3,
        max_tokens: int = 1024,
    ) -> None:
        self._client = client
        self._deployment = deployment
        self._temperature = temperature
        self._max_retries = max_retries
        self._max_tokens = max_tokens

    # --------------------------------------------------------------------- #
    # Public API
    # --------------------------------------------------------------------- #

    def extract(self, raw_text: str) -> Dict[str, Any]:
        """
        Convert *raw_text* into the canonical JSON format.

        Raises
        ------
        RuntimeError
            If the model fails to return valid JSON after the configured
            number of retries.
        """
        prompt = self._build_prompt(raw_text)

        for attempt in range(1, self._max_retries + 1):
            try:
                response = self._client.chat.completions.create(
                    model=self._deployment,
                    messages=[
                        {
                            "role": "system",
                            "content": (
                                "You are a data‑extraction assistant. "
                                "Respond **only** with a JSON object matching the schema provided. "
                                "Do not output any explanatory text."
                            ),
                        },
                        {"role": "user", "content": prompt},
                    ],
                    max_tokens=self._max_tokens,
                    temperature=self._temperature,
                    top_p=1.0,
                )

                content = response.choices[0].message.content.strip()
                json_str = self._extract_json_block(content)
                return json.loads(json_str)

            except Exception as exc:  # pragma: no cover
                logger.exception("Attempt %s failed: %s", attempt, exc)

        raise RuntimeError(f"Failed to extract JSON after {self._max_retries} attempts")

    # --------------------------------------------------------------------- #
    # Internal helpers
    # --------------------------------------------------------------------- #

    def _build_prompt(self, raw_text: str) -> str:
        schema_str = json.dumps(self._SCHEMA, indent=2)
        return (
            "The following is an ITDB fact sheet. Parse its contents and output "
            "**only** a JSON object that matches this schema exactly—no additional "
            "keys and no prose:\n\n"
            f"{schema_str}\n\n"
            "--- BEGIN FACT SHEET ---\n"
            f"{raw_text}\n"
            "--- END FACT SHEET ---"
        )

    @staticmethod
    def _extract_json_block(text: str) -> str:
        """Return the first JSON object found in *text*, or raise if none."""
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1:
            raise ValueError("No JSON object found in the model response")
        return text[start : end + 1]


# ------------------------------------------------------------------------- #
# Functional helper
# ------------------------------------------------------------------------- #


def extract_json(
    raw_text: str,
    client: AzureOpenAI,
    deployment: str,
    *,
    temperature: float = 0.0,
) -> Dict[str, Any]:
    """Convenience wrapper around :class:`JSONExtractor`."""
    extractor = JSONExtractor(
        client=client,
        deployment=deployment,
        temperature=temperature,
    )
    return extractor.extract(raw_text)